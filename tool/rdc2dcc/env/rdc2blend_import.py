# -*- coding: utf-8 -*-
"""Assemble a scene in Blender from a neutral description file.

This script is the OTHER HALF of the description format: `emit-scene` writes the
file, this reads it.  It knows nothing about RenderDoc, about palettes, about
bone fits or about this project's manifest - it knows that a scene is a list of
parts, that each part is a geometry file plus a place to put it, and that some
parts are already in world space.

Run it with:

    blender --background --python rdc2blend_import.py -- <scene.rdc2scene> [options]

Options:
    --report FILE     write a JSON report of what was assembled
    --no-camera       skip the camera even when the description carries one
    --save FILE       save a .blend
    --dump FILE       write every object's world bounds, for comparisons
    --dry-run         read and validate the description, import nothing

It deliberately does NOT write a .blend: that is a separate, explicit step, so a
script that assembles a scene can be run to check its input without producing a
file.  `--save FILE` does it when wanted.
"""

import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector


def parse_args(argv):
    """Everything after `--`, as a plain dict plus positionals."""
    opts = {"files": []}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            key = a[2:]
            if key in ("no-camera", "dry-run"):
                opts[key] = True
                i += 1
                continue
            if i + 1 >= len(argv):
                raise SystemExit("option %s needs a value" % a)
            opts[key] = argv[i + 1]
            i += 2
            continue
        opts["files"].append(a)
        i += 1
    return opts


def fail(msg):
    print("RDC2BLEND_ERROR " + msg)
    raise SystemExit(1)


# ------------------------------------------------------------------ the format
#
# The magic and the version are checked BEFORE anything is interpreted.  A reader
# that guesses at a format it does not know is how a half-understood file becomes
# wrong geometry, and wrong geometry looks exactly like right geometry until
# somebody measures it.

MAGIC = "rdc2blend.scene"
SUPPORTED = 1


def load_description(path):
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, dict):
        fail("%s: not a JSON object" % path)
    if doc.get("magic") != MAGIC:
        fail("%s: magic is %r, expected %r" % (path, doc.get("magic"), MAGIC))
    version = doc.get("version")
    if not isinstance(version, int) or version <= 0:
        fail("%s: missing or non-positive version" % path)
    if version > SUPPORTED:
        fail("%s: version %d is newer than this script understands (%d)"
             % (path, version, SUPPORTED))
    parts = doc.get("parts")
    if not isinstance(parts, list):
        fail("%s: 'parts' is not a list" % path)
    # Paths are RELATIVE TO THE DESCRIPTION FILE, which is what makes the output
    # movable.  Resolving them is this reader's job, so no caller has to know the
    # rule.
    base = os.path.dirname(os.path.abspath(path))
    for p in parts:
        g = p.get("geometry") or ""
        if not g:
            fail("%s: part %r has no geometry" % (path, p.get("eid")))
        if not os.path.isabs(g):
            g = os.path.normpath(os.path.join(base, g))
        p["_geometry_abs"] = g
    doc["_base"] = base
    return doc


def clear_scene():
    """An empty scene, so a second run does not stack on the first."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection_for(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def import_geometry(path):
    """Import one geometry file and return the objects it created.

    `bake_space_transform` is ON, and it is the difference between a scene that
    is right and one that is silently rotated.

    Blender's FBX importer applies its own axis conversion on the way in and puts
    it on the imported object's matrix (`matrix_is_identity: false`).  This
    tool's writer has ALREADY rotated the payload `(x,y,z) -> (x,z,-y)` to match
    the file's declared Y-up axes, so the importer's conversion turns it a second
    time - and the object ends up carrying a rotation on top of the placement
    that is applied afterwards.

    With `bake_space_transform` the importer leaves the vertices as they are in
    the file, which is the frame the description's `matrix_scene` is expressed
    in.  Measured: an imported part's local bounds then equal its `.world2`
    bounds exactly, and the world bounds come out at the reference's to 1e-5.

    Verified against the reference tool's own `.fbx` as well, so this is a
    property of the file format and Blender, not of this writer.
    """
    before = set(bpy.data.objects.keys())
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path, bake_space_transform=True)
    elif ext in (".obj",):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        fail("no importer for %s (extension %s)" % (path, ext))
    return [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]


def fit_camera_clip(cam, objects):
    """Put the camera's clip range around the geometry it is meant to look at.

    Blender's `clip_start` 0.1 and `clip_end` 100 are in BLENDER UNITS, and a
    capture's world is in whatever the game authored it in.  逆水寒 works in
    centimetres: the recovered camera sits 26464 units from the origin and the
    character 22762 of them in front of it, so every triangle is past the far
    plane and a CORRECT camera renders the background and nothing else.  Measured
    on long3 - pure white - and the reader concludes the export is empty, which is
    the wrong diagnosis of a right export.

    Measured from the camera to the geometry, not from one object's own size: a
    character is imported as dozens of parts and the largest of them says nothing
    about how far away the character is.
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


def mat4_from(rows):
    """A description matrix as a Blender 4x4.

    Blender's Matrix constructor takes ROWS, and the description stores rows, so
    this is a straight copy - but it is written out rather than passed through,
    because a transposed placement is a bug that produces a plausible scene.
    """
    m = Matrix.Identity(4)
    for i in range(4):
        for j in range(4):
            m[i][j] = float(rows[i][j])
    return m


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = parse_args(argv)
    if not opts["files"]:
        fail("usage: rdc2blend_import.py -- <scene.rdc2scene>")

    scene_path = opts["files"][0]
    doc = load_description(scene_path)
    units = doc.get("units") or {}
    frame = units.get("frame") or "blender"

    # The parts' geometry is already in the frame Blender uses - the conversion
    # happened on the way out and the file's own header declares the axes.  A
    # reader that converted AGAIN would produce parts that are right in every way
    # except which way up they are, so the claim is checked rather than obeyed
    # blindly.
    if frame != "blender":
        fail("%s: parts are in the %r frame; this script only assembles the "
             "'blender' frame" % (scene_path, frame))

    parts = doc["parts"]
    print("RDC2BLEND_SCENE %s: %d part(s), unit_scale=%s up_axis=%s frame=%s"
          % (os.path.basename(scene_path), len(parts), units.get("unit_scale"),
             units.get("up_axis"), frame))

    if opts.get("dry-run"):
        missing = [p["_geometry_abs"] for p in parts
                   if not os.path.exists(p["_geometry_abs"])]
        print("RDC2BLEND_DRYRUN " + json.dumps(
            {"parts": len(parts), "missing": missing[:20], "missing_count": len(missing)}))
        return

    clear_scene()

    report = {"scene": os.path.abspath(scene_path), "parts": [], "by_kind": {},
              "verts": 0, "tris": 0, "uv_layers": 0, "placed": 0, "baked": 0,
              "screen_space": [], "screened": 0, "missing": [], "failed": []}

    # ---- where the scene is expressed from --------------------------------
    #
    # `world` means the numbers in the file are used as they stand.  `character`
    # means they were written around the character's own origin, and then this
    # script must move EVERYTHING - every part, the baked ones included, and the
    # camera - by the same amount.  Moving only the PLACED parts is the mistake
    # worth naming out loud: the baked ones are the majority on every capture
    # measured (44 of 60 here), each carries its world position in its vertices,
    # and the result of moving the others would be a scene whose props and
    # character stand in different places.
    origin_doc = doc.get("origin") or {}
    origin_kind = origin_doc.get("kind") or "world"
    origin = Vector((0.0, 0.0, 0.0))
    if origin_kind == "character":
        point = origin_doc.get("point") or [0.0, 0.0, 0.0]
        origin = Vector((float(point[0]), float(point[1]), float(point[2])))
    shift = Matrix.Translation(-origin)
    report["origin_kind"] = origin_kind
    report["origin"] = [origin.x, origin.y, origin.z]

    for p in parts:
        eid = p.get("eid")
        gpath = p["_geometry_abs"]
        kind = p.get("kind") or "skinned"
        if not os.path.exists(gpath):
            report["missing"].append({"eid": eid, "geometry": gpath})
            continue
        try:
            made = import_geometry(gpath)
        except SystemExit:
            raise
        except Exception as ex:
            report["failed"].append({"eid": eid, "why": "%s: %s" % (type(ex).__name__, ex)})
            continue
        meshes = [o for o in made if o.type == "MESH"]
        if not meshes:
            report["failed"].append({"eid": eid, "why": "no mesh object was created"})
            continue

        # `placed` and the matrix answer DIFFERENT questions.  When the geometry
        # was baked it is already in world space and the object stays at the
        # origin; when it was not, the object carries the placement.  Applying a
        # matrix to a baked part would place it twice.
        #
        # A SCREEN-SPACE part is neither.  Its vertices are the picture, so
        # there is no world matrix to apply and applying the recorded one puts
        # the quad somewhere arbitrary.  Positioning it means putting it in front
        # of a camera, and 0.1 does not build a camera - so it is imported,
        # reported, and left at the origin where its wrongness is visible rather
        # than hidden behind a plausible-looking transform.
        screen_space = bool(p.get("screen_space"))
        placed = bool(p.get("placed")) and not screen_space
        if screen_space:
            report["screen_space"].append(eid)
        if placed:
            matrix = mat4_from(p["matrix_scene"])
            for o in made:
                o.matrix_world = matrix
            report["placed"] += 1
        else:
            report["baked"] += 1

        for o in meshes:
            col = collection_for(kind)
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
            o["source_eid"] = int(eid) if eid is not None else -1
            o["mesh_kind"] = kind
            if p.get("mode"):
                o["solve_mode"] = p["mode"]
            if p.get("rms") is not None:
                o["solve_rms"] = p["rms"]
            report["verts"] += len(o.data.vertices)
            report["tris"] += len(o.data.polygons)
            report["uv_layers"] += len(o.data.uv_layers)

        report["by_kind"][kind] = report["by_kind"].get(kind, 0) + 1
        report["screened"] = len(report["screen_space"])
        report["parts"].append({"eid": eid, "kind": kind, "objects": len(made),
                                "placed": placed, "screen_space": screen_space,
                                "verts": sum(len(o.data.vertices) for o in meshes)})

    # Objects and single-user meshes only: an orphan mesh is data with nothing
    # pointing at it, and it inflates every count a person reads afterwards.
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # ---- the origin, applied to everything that is already in the scene -----
    if origin_kind == "character":
        moved = 0
        for ob in bpy.data.objects:
            if ob.type == "MESH":
                ob.matrix_world = shift @ ob.matrix_world
                moved += 1
        print("RDC2BLEND_ORIGIN %s: moved %d object(s) by (%.4f, %.4f, %.4f)"
              % (origin_kind, moved, -origin.x, -origin.y, -origin.z))

    # ---- the camera --------------------------------------------------------
    #
    # Built from the description, where `solve` recorded it after inverting the
    # run's view-projection.  Three things about this are deliberate:
    #
    #   * the FOV comes from the projection, not from a guess: `half_fov_x_deg`
    #     is the angle the capture's own frustum has, and the lens is derived
    #     from it against a 36 mm sensor with the fit set HORIZONTAL - so the
    #     framing of a render matches the framing of the frame it came from.
    #   * the sensor fit is HORIZONTAL because the angle that was recovered is
    #     the horizontal one.  Left on AUTO, Blender applies it to the LARGER
    #     dimension, which is the horizontal one only while the render is wider
    #     than it is tall.
    #   * `shift` is applied here too.  A camera is a part of the scene like any
    #     other, and a rebased scene that moved everything except the camera is a
    #     scene with no camera in it where the picture was taken.
    cam_doc = doc.get("camera")
    report["camera"] = None
    if cam_doc and opts.get("no-camera"):
        print("RDC2BLEND_CAMERA skipped: --no-camera (the description carries one)")
    elif cam_doc:
        rows = cam_doc.get("matrix")
        if not rows:
            print("RDC2BLEND_CAMERA the description's camera has no matrix")
        else:
            half_fov = float(cam_doc.get("half_fov_x_deg") or 0.0)
            cam_data = bpy.data.cameras.new("rdc2blend_camera")
            cam_data.sensor_fit = "HORIZONTAL"
            cam_data.sensor_width = 36.0
            if half_fov > 0.0:
                cam_data.lens = (0.5 * cam_data.sensor_width /
                                 math.tan(math.radians(half_fov)))
            cam = bpy.data.objects.new("rdc2blend_camera", cam_data)
            collection_for("camera").objects.link(cam)
            cam.matrix_world = shift @ mat4_from(rows)
            bpy.context.scene.camera = cam

            # THE CLIP RANGE IS SET FROM THE SCENE, because Blender's default is a
            # default in BLENDER UNITS and a game world is not authored in them.
            #
            # `clip_start` 0.1 and `clip_end` 100 are 10 cm and 1 m.  A game that
            # works in centimetres - 逆水寒 does, `unit_scale: 0.01` - puts the
            # recovered camera 26464 of them from the origin and the character
            # 22762 of them in front of it, so EVERY triangle is past the far plane
            # and a perfectly correct camera renders the background and nothing
            # else.  Measured on long3: pure white until this was set, and the
            # reader's conclusion is "the export is empty", which is the wrong
            # diagnosis of a right export.
            #
            # Measured from the camera to the geometry rather than from the objects'
            # own sizes: one object's `dimensions` is the size of ONE part of a
            # character, which says nothing about how far away the character is.
            fit_camera_clip(cam, [o for o in bpy.data.objects if o.type == "MESH"])

            # THE RENDER'S SHAPE COMES FROM THE PROJECTION, not from the viewport
            # the reference draw happened to render into.  On 陈-1 that draw wrote
            # into a 1024x1024 target while the projection is 16:9, and setting a
            # square render from it would have made the horizontal field of view
            # right and the vertical one wrong - a picture that looks like an odd
            # capture rather than like a bug.  `aspect` is the projection's own
            # tangent ratio, so it is the frame the camera was built for.
            aspect = float(cam_doc.get("aspect") or 0.0)
            vw = cam_doc.get("viewport_w")
            vh = cam_doc.get("viewport_h")
            if aspect > 0.01:
                width = 1920
                bpy.context.scene.render.resolution_x = width
                bpy.context.scene.render.resolution_y = int(round(width / aspect))

            report["camera"] = {
                "name": cam.name,
                "lens_mm": round(cam_data.lens, 3),
                "half_fov_x_deg": half_fov,
                "aspect": round(aspect, 4),
                "reference_eid": cam_doc.get("reference_eid"),
                "flipped_y": bool(cam_doc.get("flipped_y")),
                # "rebased" means the capture's vertices were relative to the
                # camera, so the camera's recorded position is that space's
                # origin rather than a distance along an axis.
                "rebased": bool(cam_doc.get("rebased")),
                "location": [round(v, 5) for v in cam.matrix_world.translation],
                "reference_viewport": [vw, vh],
                "render": [bpy.context.scene.render.resolution_x,
                           bpy.context.scene.render.resolution_y],
            }
            print("RDC2BLEND_CAMERA at (%.3f, %.3f, %.3f) lens=%.2fmm half-fov=%.2fdeg"
                  % (cam.matrix_world.translation.x, cam.matrix_world.translation.y,
                     cam.matrix_world.translation.z, cam_data.lens, half_fov))

    # ---- in-process world dump -------------------------------------------
    #
    # Taken HERE, before any save.  A saved `.blend` stores parent-relative
    # transforms and Blender recomputes world matrices on load, and for a part
    # whose matrix carries a very small uniform scale that round trip does not
    # return what went in - measured: an object whose `matrix_basis` keeps
    # `scale = 0.0024` comes back from a save/load with `matrix_world` scaling by
    # 1.0.  Comparing saved files therefore measures Blender's save path as much
    # as this tool's placement, so the comparison is taken from live objects.
    if opts.get("dump"):
        worlds = {}
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            key = None
            if "source_eid" in ob.keys():
                key = str(int(ob["source_eid"]))
            elif ob.name.startswith("eid-"):
                key = ob.name[4:].split(".")[0]
            if key is None:
                continue
            mw = ob.matrix_world
            xs = [mw @ v.co for v in ob.data.vertices]
            e = worlds.setdefault(key, {"verts": 0, "polys": 0, "objects": 0,
                                        "matrix_translation": [round(v, 6) for v in mw.translation]})
            e["verts"] += len(ob.data.vertices)
            e["polys"] += len(ob.data.polygons)
            e["objects"] += 1
            # BOTH bounds, because they are not the same number and only one of
            # them is comparable.
            #
            # `corner_min` transforms the object's eight local bounding-box
            # corners; `vertex_min` transforms every vertex.  For an object with
            # no rotation they agree exactly.  For a ROTATED one the
            # corner-derived box is looser - it is the box around a box - so
            # comparing one against the other reports a difference that is purely
            # a difference of method.  A consumer that only ever sees one of them
            # will not notice; a comparison must use the same one on both sides.
            corners = [mw @ Vector(c) for c in ob.bound_box]
            e.setdefault("corner_min", [min(p[i] for p in corners) for i in range(3)])
            e.setdefault("corner_max", [max(p[i] for p in corners) for i in range(3)])
            if xs:
                lo = [min(p[i] for p in xs) for i in range(3)]
                hi = [max(p[i] for p in xs) for i in range(3)]
                if "vertex_min" in e:
                    e["vertex_min"] = [min(a, b) for a, b in zip(e["vertex_min"], lo)]
                    e["vertex_max"] = [max(a, b) for a, b in zip(e["vertex_max"], hi)]
                else:
                    e["vertex_min"] = lo
                    e["vertex_max"] = hi
        for e in worlds.values():
            for k in ("corner_min", "corner_max", "vertex_min", "vertex_max"):
                e[k] = [round(v, 5) for v in e[k]]
        # `world_min`/`world_max` keep the corner form, which is what a scene
        # builder reports and therefore what a comparison has to use.
        for e in worlds.values():
            e["world_min"] = e["corner_min"]
            e["world_max"] = e["corner_max"]
        with open(opts["dump"], "w", encoding="utf-8") as f:
            json.dump({"scene": os.path.abspath(scene_path), "parts": worlds}, f,
                      ensure_ascii=False, indent=1)
        print("RDC2BLEND_DUMP %s parts=%d" % (opts["dump"], len(worlds)))

    if opts.get("save"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(opts["save"]))

    if opts.get("report"):
        with open(opts["report"], "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    print("RDC2BLEND_RESULT " + json.dumps(
        {k: v for k, v in report.items() if k != "parts"}))
    # A part that failed to import or to place is the difference between "the
    # scene assembled" and "the scene assembled and one part is at the origin",
    # and the second looks exactly like the first until somebody counts.  Said
    # out loud so a caller cannot report success over an empty `failed` list that
    # it never read.
    if report["failed"] or report["missing"]:
        print("RDC2BLEND_INCOMPLETE failed=%d missing=%d"
              % (len(report["failed"]), len(report["missing"])))
        for f in report["failed"][:5]:
            print("  failed eid %s: %s" % (f.get("eid"), f.get("why")))


main()
