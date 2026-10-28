# -*- coding: utf-8 -*-
"""Turn a Matex material library into Blender objects and materials.

WHAT IT READS.  The three documents `matexport` writes, and nothing else: it
never opens a capture, never asks RenderDoc anything and does not know what a
draw call's constant buffer looked like before it was decoded.  That is the
whole reason the library exists as files - the collection needs RenderDoc and
minutes per capture, and building the materials does not.

    <library>/matex.json      what was exported, and what failed
    <library>/binding.json    every texture binding, keyed by shader and slot
    <library>/fbx/eid-N.fbx   one mesh per draw call, vertices unplaced

WHAT IT BUILDS, per draw call:

    * the FBX, imported as it is.  Vertices are the capture's own and the mesh
      sits at the origin, because the placement is a solver's to decide and not
      this script's - see the note in `matex_fbx.h` about the frame.
    * one material, with a Principled BSDF at its root and one Image Texture node
      per binding, wired up by SEMANTIC where the semantic says something this
      script understands and left as a named, unwired node where it does not.

TWO RULES FROM THIS PROJECT'S OWN NOTES ARE FOLLOWED HERE, and both are the kind
of thing that looks right and is not:

    1. `alpha_mode = 'CHANNEL_PACKED'`.  The default for a new image is
       `STRAIGHT`, which makes Blender multiply the alpha into RGB - so a game
       texture that carries a mask in A arrives at about half brightness, and it
       looks like the capture was dark rather than like a setting.
    2. Nodes are found by `type`, never by name.  A Principled BSDF is called
       something else in a Chinese interface, and `nodes['Principled BSDF']` is
       the standard way to write this and the standard way for it to break.

COLOUR SPACE.  Whether a texture's pixels are sRGB-encoded is a property of the
texture, read from the format the capture reported, and it is set per image.  A
normal map or a mask read as sRGB is a specific and recognisable kind of wrong,
and it is not fixable by eye.  Image datablocks are therefore keyed by
(path, colour space): one file is one image, unless two materials genuinely
sample it two ways.

NOTHING IS HIDDEN BY DEFAULT.  An earlier version hid every part more than ten
times the library's median size, which made a character render legible on a
91-draw capture and hid 235 of 588 objects on a 609-draw one.  A project whose
contents depend on an invented threshold is not a faithful export, so the
oversized parts are now REPORTED (`oversized_unplaced`) and `--hide-helpers`
restores the old behaviour for whoever wants a clean character render.

Run:
    blender --background --python rdc2blend_matex.py -- <library-dir> [options]

Options:
    --report FILE   write a JSON report of what was built.  Written AFTER the
                    save, so it describes the file that exists
    --save FILE     save a .blend (a separate, explicit step, as in the other
                    bridge script: assembling a scene and writing a file are
                    different acts).  Every image is packed into it.
    --hide-helpers  hide the oversized parts, in a `matex_helpers` collection.
                    Off by default - see above
    --no-camera     do not build the camera the solve left in the library.  On by
                    default: a render from the capture's own seat is the only way
                    to see whether a part was placed at all
    --helper-factor R  what "oversized" means, as a multiple of the median part
                    (default 10)
    --limits R      how big the largest mesh is made, in Blender units (default
                    2.0; 0 leaves every mesh at its own scale).  The library is
                    a set of ASSETS, so they are all scaled by one factor - a
                    per-mesh fit would make a pebble the same size as a building
                    and hide the one thing the library is for.  SKIPPED when the
                    parts carry solve placements: they are already the right size
    --force-limits  normalise even then
    --dry-run       read and validate everything, import nothing
"""

import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

MAGIC_BINDING = "matex.binding"
SUPPORTED = 1


def parse_args(argv):
    opts = {"library": "", "limits": 2.0}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--dry-run":
            opts["dry-run"] = True
            i += 1
            continue
        if a == "--force-limits":
            opts["force_limits"] = True
            i += 1
            continue
        if a.startswith("--"):
            key = a[2:]
            if i + 1 >= len(argv):
                raise SystemExit("option %s needs a value" % a)
            opts[key] = argv[i + 1]
            i += 2
            continue
        if not opts["library"]:
            opts["library"] = a
        i += 1
    return opts


def fail(msg):
    # Blender's background mode returns 0 even when a script raises, so the
    # caller's only reliable signal is the report file or this line.  Both are
    # written: the line is for a person reading the log, the file for a script.
    print("MATEX_ERROR " + msg)
    raise SystemExit(1)


def read_json(path, what):
    if not os.path.isfile(path):
        fail("%s is not there: %s" % (what, path))
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except ValueError as ex:
            fail("%s will not parse: %s" % (what, ex))


# --------------------------------------------------------------------- nodes

def principled_of(material):
    """The Principled BSDF node, found by TYPE.

    Never by name: the node is called something else in a localized interface,
    and this project has already been bitten by looking one up by name.
    """
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def ensure_principled(material):
    node = principled_of(material)
    if node is not None:
        return node
    node = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    node.location = (0, 0)
    out = None
    for n in material.node_tree.nodes:
        if n.type == "OUTPUT_MATERIAL":
            out = n
            break
    if out is None:
        out = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        out.location = (320, 0)
    material.node_tree.links.new(node.outputs["BSDF"], out.inputs["Surface"])
    return node


def is_srgb(format_name):
    return "_SRGB" in (format_name or "").upper()


#: image cache: (real path, colour space) -> the Image datablock for it.
#:
#: WHY THIS EXISTS RATHER THAN `check_existing=True`.  That flag is supposed to do
#: exactly this job - reuse the datablock that already has this path - and on a
#: real library it does not: measured on `long.rdc`, 231 texture files became 789
#: image datablocks, one file reaching 60 copies, 558 of them with no user at all.
#: The FBX importer makes an image per texture node per imported FILE, so the same
#: PNG arrives once for every one of the 588 FBX files that mention it, and the
#: lookups did not recognise those as the same file.
#:
#: The cost is not only size.  Those copies carried the importer's own colour
#: space, so 55 files were present at BOTH `sRGB` and `Non-Color` in one project -
#: the same pixels read two ways, decided by which material you happened to open.
#:
#: The key is (path, colours) and not path alone: whether a texture is sRGB is a
#: property of how the shader SAMPLES it, so two materials that genuinely sample
#: one resource differently need two datablocks.  What they must not need is two
#: per material.
_IMAGES = {}


def add_image(material, tex, path, y, colorspace):
    """One texture as an Image Texture node, named and wired as far as it goes.

    `tex` is the entry from binding.json's `textures` list, so this has the
    resource id, the slice and the size.  `colorspace` comes from the BINDING,
    not from the image: whether the pixels are sRGB-encoded is a property of the
    texture, the capture did not report a format for it, and the binding is where
    that uncertainty - or a template's answer - is written down.
    """
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.location = (-560, y)
    label = tex.get("semantic") or os.path.basename(path)
    node.label = label
    node.name = label
    # `sRGB` unless a template said otherwise - the literal reading of "no
    # information", and the safe one for the maps most damaged by the other
    # choice.  It is what the node's label leaves visible: the question was left
    # open rather than answered.
    want = "sRGB" if colorspace == "srgb" else "Non-Color"
    key = (os.path.normcase(os.path.abspath(path)), want)
    image = _IMAGES.get(key)
    if image is None:
        try:
            image = bpy.data.images.load(path, check_existing=False)
        except RuntimeError as ex:
            return None, "cannot load %s: %s" % (path, ex)
        # The rule from this project's own notes.  STRAIGHT would multiply the
        # alpha into RGB and darken every texture whose A channel is a mask -
        # which is most of them in a game capture.
        image.alpha_mode = "CHANNEL_PACKED"
        image.colorspace_settings.name = want
        _IMAGES[key] = image
    node.image = image
    return node, ""


def wire(material, node, principled, semantic):
    """Connect a texture by what its semantic says it is.

    ONLY WHERE THE SEMANTIC IS KNOWN.  A texel that means nothing to this script
    is left as a named, unwired node with its colour space already correct: that
    is a material a person finishes in ten seconds, whereas a guess - "the second
    texture is the normal map" - is right often enough to be believed and wrong
    often enough to be worse than no answer at all.  The naming comes from the
    shader's own binding name or from the user's template, so the node a person
    sees is the node the capture named.

    EVERY INPUT IS LOOKED UP BY NAME WITH A GUARD, because Blender renamed
    several of them between 4.x and 5.x (`Emission` became `Emission Color`,
    `Specular` became `Specular IOR Level`) and an unguarded assignment raises
    rather than doing nothing.  A missing socket means the material loses one
    connection, which is visible; an exception means the whole import stops.
    """
    links = material.node_tree.links
    inputs = principled.inputs

    def link(output, name):
        if name in inputs:
            links.new(output, inputs[name])
            return True
        return False

    s = (semantic or "").lower()
    if "basecolor" in s or "base_color" in s or "diffuse" in s or "albedo" in s:
        link(node.outputs["Color"], "Base Color")
        link(node.outputs["Alpha"], "Alpha")
        return "base_color"
    if "normal" in s:
        nmap = material.node_tree.nodes.new("ShaderNodeNormalMap")
        nmap.location = (-260, -180)
        nmap.label = "normal"
        links.new(node.outputs["Color"], nmap.inputs["Color"])
        link(nmap.outputs["Normal"], "Normal")
        return "normal"
    if "orm" in s or "arm" in s or "roughness" in s or "metallic" in s or "specular" in s:
        # A packed metallic/roughness/occlusion map.  Split so the channels are
        # addressable rather than guessing which of them is which - the engines
        # disagree about the order, and a wrong guess produces a
        # plausible-looking material, which is the worst kind of wrong.
        sep = material.node_tree.nodes.new("ShaderNodeSeparateColor")
        sep.location = (-260, -420)
        sep.label = (semantic or "packed") + " (r/g/b)"
        links.new(node.outputs["Color"], sep.inputs["Color"])
        link(sep.outputs["Green"], "Roughness")
        link(sep.outputs["Blue"], "Metallic")
        return "packed"
    if "emissive" in s or "emission" in s:
        link(node.outputs["Color"], "Emission Color")
        return "emission"
    if "opacity" in s or "alpha" in s or "transparen" in s:
        link(node.outputs["Alpha"], "Alpha")
        return "alpha"
    return "unwired"


# ------------------------------------------------------------------- import

def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    added = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in added if o.type == "MESH"]
    return added, meshes


def scale_objects(objects, factor):
    for ob in objects:
        ob.scale = (ob.scale[0] * factor, ob.scale[1] * factor, ob.scale[2] * factor)


def fit_camera_clip(cam, objects):
    """Put the camera's clip range around the geometry it is meant to look at.

    Blender's `clip_start` 0.1 and `clip_end` 100 are in BLENDER UNITS, and a
    capture's world is in whatever the game authored it in.  逆水寒 works in
    centimetres: the solve's camera sits 26386 units from the origin and the
    character is tens of thousands of them in front of it, so every mesh is past
    the far plane and a CORRECT camera shows an empty viewport.  Since the camera
    is put in this library precisely so a person can see whether the export is
    right, a camera that shows nothing is worse than no camera at all.

    Measured from the camera to the geometry, not from one object's own size: the
    library holds one object per draw call and the largest of them says nothing
    about how far away the scene is.
    """
    lo = [1e30] * 3
    hi = [-1e30] * 3
    counted = 0
    for ob in objects:
        if ob.type != "MESH":
            continue
        counted += 1
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    if not counted:
        return
    centre = Vector([(lo[i] + hi[i]) / 2.0 for i in range(3)])
    radius = (Vector(hi) - Vector(lo)).length / 2.0
    distance = (centre - cam.matrix_world.translation).length
    near = distance - radius
    cam.data.clip_start = max(1e-3, near * 1e-2 if near > 0 else 1e-3)
    cam.data.clip_end = max(distance + radius * 2.0, 1.0) * 4.0


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = parse_args(argv)
    if not opts["library"]:
        fail("usage: ... -- <library-dir> [--report FILE] [--save FILE]")
    library = os.path.abspath(opts["library"])

    # AN EMPTY SCENE FIRST, the way `rdc2blend_import.py` does it.
    #
    # Without this the file carries whatever Blender opens with - the default
    # cube, its camera and its light, and a material called `Material` that
    # belongs to none of them.  A library whose object count does not match its
    # mesh count is a library somebody has to clean before using, and the stray
    # objects look exactly like something the export produced.
    bpy.ops.wm.read_factory_settings(use_empty=True)

    binding = read_json(os.path.join(library, "binding.json"), "binding.json")
    if not isinstance(binding, dict):
        fail("binding.json is not an object")
    index = read_json(os.path.join(library, "matex.json"), "matex.json")
    if not isinstance(index, dict):
        fail("matex.json is not an object")
    # The camera is OPTIONAL and its absence is normal: it is written when
    # `matexport` was given a `--world2` whose manifest carried one.  Absence is
    # reported rather than invented - a library with no camera in it is a library
    # with no camera, and defaulting to a Blender camera at the origin would put
    # the viewer somewhere the capture never was.
    camera_doc = None
    camera_path = os.path.join(library, "camera.json")
    if os.path.isfile(camera_path):
        camera_doc = read_json(camera_path, "camera.json")
        if not isinstance(camera_doc, dict):
            camera_doc = None

    bindings = binding.get("bindings") or []
    textures = binding.get("textures") or []
    # The library's own index, from `binding.json`.  NOT `matex.json`'s `draws`,
    # which is a COUNT: taking that one and iterating it raises
    # "'int' object is not iterable", and the guard below would not have caught
    # it because a count is not `None`.  Checked by type for that reason.
    draws = binding.get("draws")
    if not isinstance(draws, list):
        draws = index.get("draws")
    if not isinstance(draws, list):
        fail("neither binding.json nor matex.json carries a list of draws")

    # resource id + slice -> the file it was written to.  A binding names a
    # texture; this is how the name becomes a path.
    tex_file = {}
    for t in textures:
        tex_file["%s#%s" % (t.get("resource"), t.get("slice"))] = t

    # Which textures each eid's shaders bound, so the material for a draw can be
    # assembled from the binding list rather than from the FBX's own slots - the
    # FBX carries at most two, and the binding file is the authority.
    by_eid = {}
    for b in bindings:
        by_eid.setdefault(int(b.get("eid", -1)), []).append(b)

    report = {"library": library, "draws": 0, "imported": 0, "materials": 0,
              "textures": 0, "unwired": [], "missing_fbx": [], "failed": []}

    if opts.get("dry-run"):
        print("MATEX_DRYRUN draws=%d bindings=%d textures=%d"
              % (len(draws), len(bindings), len(textures)))
        return

    fbx_files = []
    for d in draws:
        eid = int(d.get("eid", -1))
        mesh = d.get("mesh")
        if not mesh:
            continue
        report["draws"] += 1
        fbx_files.append((eid, os.path.join(library, mesh)))

    before_all = set(bpy.data.objects)
    placed = 0
    #: which library textures ended up in a material, so the ones that did not can
    #: be named.  A texture nothing uses is not an error - the library is a store
    #: keyed by resource id and holds everything the capture had - but it is a
    #: question ("why is 35072 not in the file?") that should have an answer in
    #: the report rather than in somebody's afternoon.
    built = set()
    for eid, path in fbx_files:
        if not os.path.isfile(path):
            report["missing_fbx"].append(path)
            continue
        try:
            _added, meshes = import_fbx(path)
        except RuntimeError as ex:
            report["failed"].append("%s: %s" % (path, ex))
            continue
        report["imported"] += 1

        # THE WORLD PLACEMENT, when a solve provided one.
        #
        # `binding.json`'s `world_matrix` is already in BLENDER'S frame - the
        # solve wrote it there, and `rdc2blend_import.py` reads the same field
        # the same way.  So it goes straight onto `matrix_world` and NOTHING here
        # converts it: a second `(x,y,z) -> (x,-z,y)` would put every part through
        # the frame change twice, which is a model that is right in every way
        # except that it lies on its side.
        #
        # Absent, it stays absent.  The meshes are the capture's own vertices
        # unplaced, so they sit at the origin and the library is a set of assets
        # rather than an arrangement - which is what the field being null means
        # and why it is not defaulted to the identity.
        world = None
        for d in draws:
            if int(d.get("eid", -1)) == eid:
                world = d.get("world_matrix")
                break
        applied = False
        if isinstance(world, list) and len(world) == 4:
            try:
                m = Matrix([list(row) for row in world])
            except (TypeError, ValueError) as ex:
                report["failed"].append("eid %d: bad world_matrix: %s" % (eid, ex))
                m = None
            if m is not None:
                for ob in meshes:
                    # The FBX importer has already put Blender's own axis
                    # conversion on these objects; the placement is a property of
                    # the part in the world, so it is pre-multiplied rather than
                    # replacing what the importer did.
                    ob.matrix_world = m @ ob.matrix_world
                applied = True
                placed += 1

        for ob in meshes:
            material = bpy.data.materials.new(name="matex_eid-%d" % eid)
            material.use_nodes = True
            principled = ensure_principled(material)
            ob.data.materials.clear()
            ob.data.materials.append(material)
            report["materials"] += 1

            y = 0
            for b in by_eid.get(eid, []):
                key = "%s#%s" % (b.get("resource"), b.get("slice"))
                tex = tex_file.get(key)
                if tex is None or b.get("writable"):
                    # A render target is bound, not authored; it is recorded in
                    # the binding file so a person can see that something was
                    # there, and there is no file to build a node from.
                    continue
                rel = tex.get("file")
                if not rel:
                    continue
                built.add(key)
                node, err = add_image(material, dict(tex, semantic=b.get("semantic")),
                                      os.path.join(library, rel), y,
                                      b.get("colorspace") or tex.get("colorspace") or "")
                if node is None:
                    report["failed"].append(err)
                    continue
                report["textures"] += 1
                kind = wire(material, node, principled, b.get("semantic"))
                if kind == "unwired":
                    report["unwired"].append(
                        {"eid": eid, "semantic": b.get("semantic"),
                         "resource": b.get("resource"), "file": rel})
                y -= 300

    # One scale for the whole library, and ONLY when the library is not a scene.
    #
    # WHY PLACEMENT TURNS IT OFF.  This normalises everything into a 2-unit box,
    # which is right for a shelf of loose assets: they come from different draws
    # with no relationship to each other, and a person wants to see them all.
    #
    # It is WRONG the moment the parts carry a solve's placements, and the
    # failure is quiet - the translations stay exactly where `binding.json` says
    # and every rotation is right, so the scene LOOKS assembled, while every
    # object is 29x too small for where it is.  Measured on 提丰: an object placed
    # at (-1.2297, 1.9605, -0.8388) correct to the sixth decimal, with a scale of
    # 0.0343 instead of 1.0.
    #
    # A placed part is in the CAPTURE's units, and the rest of the scene - the
    # parts this command could not place, the camera, whatever the user adds - is
    # in those same units.  Scaling a subset of them breaks the only thing the
    # placement was for.
    added = [o for o in bpy.data.objects if o not in before_all]
    limit = float(opts.get("limits") or 0.0)
    if placed and limit > 0 and not opts.get("force_limits"):
        report["scale"] = 1.0
        report["scale_skipped"] = ("%d part(s) carry a solve placement; normalising "
                                   "would put them at the right position and the "
                                   "wrong size.  --limits N still normalises if the "
                                   "placements are not wanted." % placed)
        limit = 0.0
    if limit > 0 and added:
        lo = Vector((1e30, 1e30, 1e30))
        hi = Vector((-1e30, -1e30, -1e30))
        for ob in added:
            for c in ob.bound_box:
                w = ob.matrix_world @ Vector(c)
                for i in range(3):
                    lo[i] = min(lo[i], w[i])
                    hi[i] = max(hi[i], w[i])
        span = max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
        if span > 0:
            scale_objects(added, limit / span)
            report["scale"] = limit / span

    report["objects"] = len(added)
    report["placed"] = placed

    # ---- what is where, without hiding anything ---------------------------
    #
    # A capture's draw list contains geometry that is not part of what anybody
    # wants to look at: a 50-unit sphere over the whole scene, a 48-unit
    # four-vertex card.  On 提丰 - 91 draws, one character - the library's median
    # part is 0.347 across and its 90th percentile is 1.94, while four of them are
    # 32 to 50, and hiding those four made a render from the recovered camera
    # legible.  That measurement was taken on a CHARACTER capture and the rule it
    # produced was `median * 10`.
    #
    # It does not survive a whole-map capture, and the failure is silent.  On
    # `long.rdc` - 609 draws over an event range the user asked for in full - the
    # median part is 8.25 and the same rule hid 235 of 588 objects, 40% of the
    # project, because in a scene of small props the median says nothing about
    # what is a helper.  A project whose contents depend on an invented threshold
    # is not a faithful export of the capture; a person who asks for every draw
    # call and gets 353 of them visible has been misled by the tool, not by the
    # capture.
    #
    # So nothing is hidden by default.  What is still worth saying is which parts
    # are much larger than the typical one AND carry no placement - that is the
    # list a person would want if they DO want a legible character render, and it
    # is a list, not an edit.  `--hide-helpers` restores the old behaviour for
    # whoever wants it, and says in the report that it did.
    #
    # THEY ARE NEVER DROPPED either way.  They carry material bindings like
    # anything else, and a person looking for a sky texture needs to find it.
    factor = float(opts.get("helper_factor") or 10.0)
    hide = bool(opts.get("hide_helpers"))
    oversized = []
    if added and factor > 0:
        sizes = [max(ob.dimensions[0], ob.dimensions[1], ob.dimensions[2])
                 for ob in added]
        ordered = sorted(s for s in sizes if s > 0)
        median = ordered[len(ordered) // 2] if ordered else 0.0
        if median > 0:
            cutoff = median * factor
            coll = None
            if hide:
                coll = bpy.data.collections.new("matex_helpers")
                bpy.context.scene.collection.children.link(coll)
            for ob in added:
                dim = max(ob.dimensions[0], ob.dimensions[1], ob.dimensions[2])
                if dim <= cutoff:
                    continue
                oversized.append({"name": ob.name, "max_dim": round(dim, 3),
                                  "placed": bool(any(
                                      abs(ob.matrix_world[i][3]) > 1e-6
                                      for i in range(3)))})
                if coll is None:
                    continue
                for c in list(ob.users_collection):
                    c.objects.unlink(ob)
                coll.objects.link(ob)
                # Hidden for BOTH: `hide_viewport` is what the viewport hides,
                # `hide_render` is what a render skips, and an object hidden one
                # way still shows up the other.
                ob.hide_viewport = True
                ob.hide_render = True
            report["oversized_median_dim"] = round(median, 4)
            report["oversized_cutoff"] = round(cutoff, 4)
            report["oversized_unplaced"] = [h for h in oversized
                                            if not h["placed"]]
            if coll is not None:
                report["helper_collection"] = "matex_helpers"
                report["hidden_helpers"] = oversized
                print("MATEX_HELPERS %d oversized part(s) hidden in "
                      "'matex_helpers' (median %.3f, cutoff %.3f): %s"
                      % (len(oversized), median, cutoff,
                         ", ".join(h["name"] for h in oversized[:8])))
            elif oversized:
                print("MATEX_OVERSIZED %d part(s) are more than %.1fx the median "
                      "size (%.3f); none hidden - pass --hide-helpers to hide them"
                      % (len(oversized), factor, median))

    # A SELF-CHECK ON THE PLACEMENT, because getting it wrong is invisible.
    #
    # WHAT IS MEASURED IS THE SPREAD OF THE PARTS' CENTRES, not the size of the
    # box they occupy.  The first version compared the bounding box against the
    # largest single part and reported a failure on a character whose longest limb
    # IS longer than the cluster it belongs to - a false alarm on 陈, whose parts
    # spread over 0.47 x 0.50 x 1.03 while its largest part is 1.76 across.  A
    # check that fires on a correct result is worse than no check: it teaches the
    # reader to ignore it.
    #
    # Centres separate the two cases that matter.  Parts that carry their
    # placements are spread through the scene; parts whose placements were
    # dropped - or whose library was normalised, which was the real bug this
    # guards - all sit at one point, and their centres coincide however large
    # each one is.
    if placed > 1:
        centres = []
        for ob in added:
            if ob.hide_viewport:
                continue
            if not any(abs(ob.matrix_world[i][3]) > 1e-4 for i in range(3)):
                continue
            c = [ob.matrix_world @ Vector(x) for x in ob.bound_box]
            centres.append([sum(p[i] for p in c) / 8.0 for i in range(3)])
        if len(centres) > 1:
            spread = max(max(c[i] for c in centres) - min(c[i] for c in centres)
                         for i in range(3))
            report["placed_centre_spread"] = round(spread, 4)
            if spread < 1e-3:
                report["failed"].append(
                    "%d part(s) carry a placement but their centres coincide "
                    "(spread %.6f): the placements were lost, which is what a "
                    "library that was normalised looks like" % (len(centres), spread))
    # ---- the camera --------------------------------------------------------
    #
    # WHY A MATERIAL LIBRARY NEEDS ONE.  Every part here is a mesh with a
    # material, and a mesh on its own cannot be checked: "is this model right?" is
    # answered by looking at it from where the game looked from.  Without a camera
    # a person opens the file, sees hundreds of objects and has no way to tell a
    # part that was never placed from one that was placed wrongly - measured on
    # `long.rdc`, where 507 of 582 meshes carry no placement at all.
    #
    # The camera comes from `solve` (via `matexport`, which copies it into the
    # library) and is in the SAME frame as the `world2` meshes, so it is applied
    # as it stands and nothing converts it.  The three rules are the scene
    # bridge's, deliberately - one camera, one way of building it:
    #
    #   * the FOV comes from the projection: `half_fov_x_deg` is the angle the
    #     capture's own frustum has, and the lens is derived from it against a
    #     36 mm sensor with the fit set HORIZONTAL, so a render's framing matches
    #     the frame it came from;
    #   * HORIZONTAL and not AUTO, because the recovered angle is the horizontal
    #     one and AUTO would apply it to the larger dimension;
    #   * the render's shape comes from the PROJECTION's aspect, not from the
    #     viewport the reference draw happened to render into (a 1024x1024 target
    #     with a 16:9 projection is a real case in these captures).
    report["camera"] = None
    if camera_doc is None:
        print("MATEX_CAMERA none: the library has no camera.json "
              "(matexport writes one when --world2 names a solve with a camera)")
    elif opts.get("no-camera"):
        print("MATEX_CAMERA skipped: --no-camera")
    else:
        rows = camera_doc.get("matrix")
        if not rows:
            print("MATEX_CAMERA the library's camera has no matrix")
        else:
            half_fov = float(camera_doc.get("half_fov_x_deg") or 0.0)
            cam_data = bpy.data.cameras.new("matex_camera")
            cam_data.sensor_fit = "HORIZONTAL"
            cam_data.sensor_width = 36.0
            if half_fov > 0.0:
                cam_data.lens = 0.5 * cam_data.sensor_width / math.tan(math.radians(half_fov))
            cam = bpy.data.objects.new("matex_camera", cam_data)
            bpy.context.scene.collection.objects.link(cam)
            cam.matrix_world = Matrix([list(row) for row in rows])
            bpy.context.scene.camera = cam
            # See `fit_camera_clip`: the default clip range is 100 Blender units,
            # and a scene authored in centimetres is thousands of them away.
            fit_camera_clip(cam, [ob for ob in bpy.context.scene.objects
                                  if ob.type == "MESH"])
            report["camera_clip"] = [round(cam_data.clip_start, 4),
                                     round(cam_data.clip_end, 2)]

            aspect = float(camera_doc.get("aspect") or 0.0)
            if aspect > 0.01:
                bpy.context.scene.render.resolution_x = 1920
                bpy.context.scene.render.resolution_y = int(round(1920 / aspect))

            report["camera"] = {
                "name": cam.name,
                "lens_mm": round(cam_data.lens, 3),
                "half_fov_x_deg": half_fov,
                "aspect": round(aspect, 4),
                "reference_eid": camera_doc.get("reference_eid"),
                "flipped_y": bool(camera_doc.get("flipped_y")),
                "rebased": bool(camera_doc.get("rebased")),
                "location": [round(v, 5) for v in cam.matrix_world.translation],
                "render": [bpy.context.scene.render.resolution_x,
                           bpy.context.scene.render.resolution_y],
            }
            print("MATEX_CAMERA at (%.3f, %.3f, %.3f) lens=%.2fmm half-fov=%.2fdeg "
                  "render=%dx%d"
                  % (cam.matrix_world.translation.x, cam.matrix_world.translation.y,
                     cam.matrix_world.translation.z, cam_data.lens, half_fov,
                     bpy.context.scene.render.resolution_x,
                     bpy.context.scene.render.resolution_y))

    if opts.get("save"):
        # THE IMPORTER'S LEFTOVERS GO FIRST, before anything is packed.
        #
        # Each `import_fbx` brings the file's own material and its image
        # datablocks along.  The material is then replaced by this script's, so
        # what is left of them is a set of images nothing points at - except that
        # Blender keeps them alive as long as the material that named them exists,
        # so the count of "images with no user" is zero at the moment a naive
        # check would look, and 558 at the moment the file is written.  Measured:
        # 789 image datablocks for 231 texture files, and 55 of those files
        # present at TWO colour spaces at once.
        #
        # The size was NOT the cost, and saying so matters: the same project went
        # from 27.6 MB to 26.9 MB when the datablocks went from 789 to 230, so
        # Blender was already storing the packed bytes once.  What was wrong was
        # the count, the 558 datablocks with no user, and a texture being read as
        # sRGB or as Non-Color depending on which material you opened.
        #
        # Removing the MATERIALS is what makes the images orphans, so the two
        # removals are one step and in this order.
        stale_materials = [m for m in bpy.data.materials if m.users == 0]
        for material in stale_materials:
            bpy.data.materials.remove(material)
        orphans = [i for i in bpy.data.images
                   if i.users == 0 and not i.use_fake_user]
        for image in orphans:
            bpy.data.images.remove(image)
        report["importer_materials_removed"] = len(stale_materials)
        report["importer_images_removed"] = len(orphans)

        # EVERY IMAGE IS PACKED INTO THE FILE, and this is not a preference.
        #
        # An image loaded from `tex/305234[0].png` is a REFERENCE: the .blend
        # points at a path, and it renders only while that path resolves.  A
        # library is made to be handed to somebody - copied to another machine,
        # dropped in a project folder, mailed - and a file that carries fifteen
        # megabytes of geometry plus a list of paths into a directory the
        # recipient does not have is a file whose materials are all missing
        # textures.  Measured before this: 142 of 144 images were external.
        #
        # The cost is that the .blend grows by the size of the textures, which
        # is the size of the thing it is supposed to be.
        for image in bpy.data.images:
            if image.source != "FILE":
                continue
            image.alpha_mode = "CHANNEL_PACKED"
            try:
                image.pack()
            except RuntimeError as ex:
                report["failed"].append("cannot pack %s: %s" % (image.name, ex))

        # Deliberately last and deliberately explicit: assembling a scene and
        # writing a file are separate acts, and a bridge that always wrote one
        # would leave a stale file behind every time it was run to check its
        # input.
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opts["save"]))

        # WHAT IS REPORTED IS THE STATE AFTER THE SAVE, not how many `pack()`
        # calls were made.  Counting the calls is what reported "packed: 0" on a
        # file whose 142 images were all packed and byte-complete - `pack()` is a
        # no-op when Blender has already packed the file image during the save,
        # so the counter measured nothing while the outcome was perfect.  A
        # number that can be right about the work and wrong about the result is
        # worse than no number, because it is believed.
        report["packed_images"] = sum(
            1 for i in bpy.data.images if i.source == "FILE" and i.packed_file)
        report["external_images"] = sum(
            1 for i in bpy.data.images if i.source == "FILE" and not i.packed_file)

    # THE REPORT IS WRITTEN LAST, after the save.  It used to be written before
    # it, which is how a report came to be missing `packed_images` and
    # `orphan_images_removed` entirely while the file it described was perfectly
    # packed: the fields were added to the dictionary after the dictionary had
    # been serialised.  A report that silently omits the facts it was extended to
    # carry is worse than no report, because the reader concludes there was
    # nothing to say.
    report["images"] = len(bpy.data.images)
    # Named, not counted: a texture in the library that no material uses is
    # almost always a draw that was collected and then had no geometry to attach
    # it to, and the id is what lets a person check that.
    report["unused_textures"] = sorted(k for k in tex_file if k not in built)
    report["unused_texture_count"] = len(report["unused_textures"])
    if opts.get("report"):
        with open(opts["report"], "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)

    print("MATEX_DONE %d draw(s), %d object(s), %d material(s), %d texture(s), "
          "%d unwired, %d placed, %d packed, %d image datablock(s), %d failed%s"
          % (report["draws"], report["objects"], report["materials"],
             report["textures"], len(report["unwired"]), placed,
             report.get("packed_images", 0), report["images"],
             len(report["failed"]),
             (", %d image(s) still external" % report["external_images"])
             if report.get("external_images") else ""))
    if report["unused_texture_count"]:
        print("MATEX_UNUSED %d library texture(s) no material uses: %s"
              % (report["unused_texture_count"],
                 ", ".join(report["unused_textures"][:8])))


main()
