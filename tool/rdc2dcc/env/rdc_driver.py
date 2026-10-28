# -*- coding: utf-8 -*-
"""Head-less RenderDoc driver.

Run as:  qrenderdoc --python driver.py        (with RDC2BLEND_TASK=<config.json>)

qrenderdoc runs `--python` before it opens its main UI, so this script can open a
capture, replay it, dump everything and terminate with os._exit() without a window
ever appearing.  That is the *only* way this tool talks to RenderDoc - there is no
extension, no queue watcher and no pointer file, so a machine with nothing but
RenderDoc installed can run every stage.

`stage` in the config says how far to go:

    "survey"  enumerate the draw calls -> <work>/survey.json, then stop
    "probe"   dump the draws chosen from an existing survey.json
    "all"     both, in one process launch (what `collect` uses)

Writes into <work>:
    survey.json          every draw call + the chosen character pass
    raw/probe.json       per-draw dump manifest (paths stored relative to <work>)
    raw/eid-<N>/*        vertex buffers, index buffer, constant buffers, shader
    raw/bone.bin         the shared bone palette buffer
    raw/depth_eid<N>.png the pass depth target, for verification
    raw/rt<N>_eid<N>.png the same draw's colour targets - the game's own picture
                         of the pass, to compare our render against

With `matex` in the config, none of the above is what happens.  That flag takes
a SECOND COLLECTION PATH (`matex_pass`), for the material library rather than
for a scene: every draw in the event range instead of the one character instance
the scene selector picks, and per draw the shader identity, the constant buffers
with their reflection and the texture bindings with their resource ids.  Its
output goes to `raw/mat/` and is described there.  The two paths share the
survey only; nothing else, and no switch - the scene pipeline's `textures` flag
and this one mean different things and must not be confused.
"""
import hashlib
import importlib
import json
import os
import struct
import sys
import traceback

CONFIG = os.environ.get("RDC2BLEND_TASK")
if not CONFIG or not os.path.exists(CONFIG):
    sys.stderr.write("RDC2BLEND_TASK is not set to an existing config file\n")
    os._exit(2)

with open(CONFIG, encoding="utf-8-sig") as f:
    CFG = json.load(f)

STAGE = str(CFG.get("stage") or "all").lower()
WORK = CFG["work"]
CAPTURE = CFG["capture"]
EIDS = CFG.get("eids")
EID_MIN = CFG.get("eid_min")
EID_MAX = CFG.get("eid_max")
PAD = int(CFG.get("pad", 1024))
MIN_BONE = int(CFG.get("min_bone_bytes", 262144))
WANT_MESH = bool(CFG.get("mesh", True))
WANT_TEXTURES = bool(CFG.get("textures", False))
WANT_DEPTH = bool(CFG.get("depth", True))
WANT_RT = bool(CFG.get("rt", True))
MAX_DRAWS = int(CFG.get("max_draws", 8000))
# ---- Matex: the material export.  A SEPARATE COLLECTION PATH, and separate on
# purpose.  `textures` above belongs to the old scene pipeline (it saves whatever
# SRV happens to sit at slot N and names the file after N); this one keeps the
# binding, the resource id and the slice, which is what a material needs.  The
# two must never share a switch or a directory - a name that means two things is
# how a run ends up exporting the wrong one.
WANT_MATEX = bool(CFG.get("matex", False))
RAW = os.path.join(WORK, "raw")
os.makedirs(RAW, exist_ok=True)
#: Where Matex dumps, when it is asked for at all.
MAT = os.path.join(RAW, "mat")

SURVEY_PATH = os.path.join(WORK, "survey.json")
RESULT = {"ok": False, "stage": STAGE}
RESULT_PATH = os.path.join(WORK, "collect_result.json")


def finish(code=0):
    """Write the result and *always* kill this process.

    qrenderdoc is running us from inside itself, so returning control would hand
    the user a full RenderDoc window holding the replayed device - several GB of
    video memory that then makes the *next* run fail with VK_ERROR_OUT_OF_DEVICE_MEMORY.
    Nothing below may raise before the os._exit.
    """
    try:
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(RESULT, f, ensure_ascii=False, default=str)
    except Exception:
        pass
    finally:
        try:
            sys.stdout.flush()
        except Exception:
            pass
        os._exit(code)


def rel(p):
    return os.path.relpath(p, WORK)


PROGRESS = os.path.join(RAW, "progress.log")


def note(msg):
    """Progress for the parent process.

    qrenderdoc redirects Python's stdout into its own log pane, so a pipe is not
    reliable - append to a file the parent tails instead (and still try stdout).
    """
    try:
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    try:
        sys.stdout.write(msg + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def save(path, blob):
    with open(path, "wb") as f:
        f.write(blob)
    return rel(path)


def _output_targets(pipe):
    """The colour targets the current event draws into.

    This one lives on the pipeline state, next to `GetDepthTarget`, and not on
    the controller - checked against the module rather than guessed, because
    getting it wrong is silent: the save simply never happens.  Some builds take
    the stage to consider and some take nothing, so both call forms are tried.
    An empty list is a normal answer for a depth-only pass, not an error.
    """
    fn = getattr(pipe, "GetOutputTargets", None)
    if fn is None:
        return []
    for call in (fn, lambda: fn(rd.ShaderStage.Pixel)):
        try:
            return list(call() or [])
        except Exception:
            continue
    return []


def _png_width(path):
    """Width off a PNG's IHDR header, or 0 when the file is not one.

    Used to tell a pass's own render target from the smaller helper targets the
    same draw also binds.  Reading the header is enough - no image library is
    available inside qrenderdoc, and none is needed for two integers.
    """
    size = _png_size(path)
    return size[0] if size else 0


def _png_size(path):
    """(width, height) off a PNG's IHDR, or None.

    This is where a Matex texture's dimensions come from, and that is not a
    workaround - it is the right source.  The file was just written from mip 0,
    so its size is the size the material will actually sample, which is not
    necessarily the size of the base mip; and the API that would have said so
    does not exist on the objects a driver script is handed.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", head[16:24])
    except Exception:
        return None


def walk(actions, out):
    for a in actions:
        out.append(a)
        walk(a.children, out)


# ------------------------------------------------- the tool's own pure python

def pkg(name):
    """Import one module of this tool's package.

    The driver runs *inside* qrenderdoc, whose embedded Python knows nothing
    about the tool's folder - the config carries both halves of what an import
    needs: where to import from (`package_root`) and under what name
    (`package_name`).  The name is read back from the folder, so a copy of the
    tool renamed to anything at all still imports itself.
    """
    pkg_name = CFG.get("package_name")
    if not pkg_name:
        raise RuntimeError("the config does not name the package to import")
    root = CFG.get("package_root")
    if root and root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(pkg_name + "." + name)


_PROFILE = []


def profile():
    """The profile this run uses, loaded once and shared by both passes."""
    if not _PROFILE:
        _PROFILE.append(pkg("profile").load_profile(CFG.get("profile")))
    return _PROFILE[0]


_UTIL = []


def util():
    """This tool's `util` module.

    Reached through `pkg` like every other package module: this file is run from
    inside qrenderdoc, which imports it by path and knows nothing about the rest
    of the package, so a plain `import util` at the top would not resolve.  It is
    a function rather than a module-level binding for the same reason `profile`
    is - nothing of the tool's may be touched before `pkg` has put its folder on
    `sys.path`.
    """
    if not _UTIL:
        _UTIL.append(pkg("util"))
    return _UTIL[0]


def buffer_bindings(pipe, rd):
    """Every buffer descriptor the vertex shader can read, in either direction.

    The bone palette is frequently bound as a *read-write* (UAV) structured
    buffer rather than an SRV, so both lists have to be walked - looking only at
    GetReadOnlyResources finds nothing on such a capture.
    """
    types = pkg("adapters").BUFFER_DESCRIPTORS
    out, seen = [], set()
    for getter in (pipe.GetReadOnlyResources, pipe.GetReadWriteResources):
        try:
            res = getter(rd.ShaderStage.Vertex, False)
        except Exception:
            continue
        for s in res:
            d = s.descriptor
            if str(d.type) not in types:
                continue
            key = (str(d.resource), int(d.byteOffset), int(d.byteSize))
            if key in seen:
                continue
            seen.add(key)
            out.append({"res": str(d.resource), "off": int(d.byteOffset),
                        "size": int(d.byteSize),
                        "elem": int(getattr(d, "elementByteSize", 0) or 0),
                        # kept for the caller: reading it back needs the id itself,
                        # and it survives the JSON round trip as `res`
                        "rid": d.resource})
    return out


def rank_buffers(bindings):
    """A draw's buffers, the ones that could be a palette first.

    A bone palette is a `Buffer<float4>` - a 16 byte element stride, read as the
    rows of a 3x4 matrix - so a buffer whose element size says exactly that
    comes first.  The order is stable, so within each group the descriptor list
    keeps its own order: a capture with a single candidate still dumps exactly
    the buffer it always did.
    """
    return sorted(bindings,
                  key=lambda b: 0 if int(b.get("elem") or 0) == 16 else 1)


def _first_call(obj, names, args=()):
    """The first of `names` this object actually has, called - or None.

    RenderDoc renames its state getters between versions: the depth state is
    `GetDepthTestState()` in the builds this tool runs against and has been
    `GetDepthState()` in others, and a capture whose blending is read from the
    wrong one reports "no state" for every draw, which reads exactly like a
    capture with no transparency in it.  Trying the names in order costs one
    `getattr` and removes the guess.
    """
    for name in names:
        fn = getattr(obj, name, None)
        if fn is None:
            continue
        try:
            return fn(*args)
        except Exception:
            continue
    return None


def depth_state(pipe):
    """(writes_depth, depth_enabled) for the current draw, or (None, None).

    `None` means this build would not say, and every caller treats that as "it
    writes depth": an unknown pass then stays opaque instead of being handed to
    the effect set, which is the failure that would cost the *most* - a whole
    frame classified as one effect.
    """
    st = _first_call(pipe, ("GetDepthTestState", "GetDepthState"))
    if st is None:
        return None, None
    writes = getattr(st, "depthWrites", None)
    if writes is None:
        writes = getattr(st, "depthWrite", None)
    enabled = getattr(st, "depthEnable", None)
    return (None if writes is None else bool(writes),
            None if enabled is None else bool(enabled))


def blending_state(pipe):
    """True when the current draw blends, False when it does not, None unknown.

    Read from the per-target colour blends, which is where a modern engine
    actually puts it; `IsIndependentBlendingEnabled` says whether the targets may
    differ, not whether any of them blends.
    """
    blends = _first_call(pipe, ("GetColorBlends", "GetBlendState"))
    if blends is None:
        return None
    # RenderDoc hands back its own array type, which prints like a list and is
    # not one - so this asks whether it can be walked, not what it is.
    try:
        each = list(blends)
    except TypeError:
        v = getattr(blends, "blendEnable", None)
        return None if v is None else bool(v)
    if not each:
        return False
    for b in each:
        on = getattr(b, "enabled", None)
        if on is None:
            # no `enabled`: a blend that is not (One, Zero) is still a blend
            src = str(getattr(b, "source", "")).rsplit(".", 1)[-1]
            dst = str(getattr(b, "destination", "")).rsplit(".", 1)[-1]
            on = not (src == "One" and dst == "Zero")
        if on:
            return True
    return False


def raster_state(pipe):
    """The cull mode as a plain string, or None."""
    st = _first_call(pipe, ("GetRasterState", "GetRasterizerState"))
    if st is None:
        return None
    mode = getattr(st, "cullMode", None)
    return None if mode is None else str(mode).rsplit(".", 1)[-1]


def describe_layout(pipe, vi):
    """One vertex input attribute, in the shape the offline solver expects."""
    vbs = pipe.GetVBuffers()
    slot = int(vi.vertexBuffer)
    return {
        "name": vi.name, "slot": slot, "off": int(vi.byteOffset),
        "fmt": vi.format.Name(), "comps": int(vi.format.compCount),
        "cbyte": int(vi.format.compByteWidth),
        "ctype": str(vi.format.compType),
        "stride": int(vbs[slot].byteStride) if slot < len(vbs) else 0,
    }


# ------------------------------------------------------------------ pass one

def survey_pass(rd, controller):
    """Enumerate every draw call with the facts needed to pick the character."""
    every = []
    walk(controller.GetRootActions(), every)
    by_eid = dict((int(a.eventId), a) for a in every)
    draws = [a for a in every if int(a.flags) & int(rd.ActionFlags.Drawcall)]
    if EID_MIN is not None:
        draws = [a for a in draws if int(a.eventId) >= int(EID_MIN)]
    if EID_MAX is not None:
        draws = [a for a in draws if int(a.eventId) <= int(EID_MAX)]
    if len(draws) > MAX_DRAWS:
        draws = draws[:MAX_DRAWS]

    survey = {"draws": [], "total_actions": len(every), "notes": []}
    note("surveying %d draw call(s) of %d action(s)" % (len(draws), len(every)))
    prof = profile()
    skin_attributes = pkg("adapters").skin_attributes
    anonymous = 0

    for n, a in enumerate(draws):
        eid = int(a.eventId)
        e = {"eid": eid, "numIndices": int(a.numIndices),
             "numInstances": int(a.numInstances)}
        try:
            controller.SetFrameEvent(eid, True)
            pipe = controller.GetPipelineState()
            vp = pipe.GetViewport(0)
            e["viewport"] = [float(vp.x), float(vp.y), float(vp.width), float(vp.height)]
            try:
                e["depth"] = str(pipe.GetDepthTarget().resource)
            except Exception:
                e["depth"] = None
            vbs = pipe.GetVBuffers()
            inputs = [describe_layout(pipe, vi) for vi in pipe.GetVertexInputs()]
            e["inputs"] = inputs
            # note: VertexInputAttribute.genericValue reads True for every
            # attribute on some builds, so the stream stride is the usable signal
            if pkg("adapters").is_anonymous(inputs):
                anonymous += 1
                e["anonymous_layout"] = True
            w, b = skin_attributes(inputs, prof)
            e["has_skin"] = (w is not None and b is not None
                             and int(w.get("stride", 0)) > 0
                             and int(b.get("stride", 0)) > 0)
            if WANT_MATEX:
                # A material run classifies nothing: it takes every draw in the
                # range, so the fields the classifier keys on are not read.  The
                # buffer walk below is the most expensive thing in a survey - it
                # enumerates every bound buffer of every draw to look for a bone
                # palette - and on a full frame that is minutes spent producing
                # numbers nobody will open.
                survey["draws"].append(e)
                if (n + 1) % 50 == 0:
                    note("  surveyed %d/%d" % (n + 1, len(draws)))
                continue
            e["buffers"] = buffer_bindings(pipe, rd)
            # The three states that tell an effect pass from an opaque one, and
            # a piece of scene geometry from a helper card.  They are read here
            # because this is the only place a pipeline state is available at
            # all; the offline half never sees the capture.
            #
            # `None` everywhere means "this build would not say", and every
            # consumer treats that as the conservative answer - an unknown pass
            # stays opaque rather than being handed to the effects.
            e["depth_writes"], e["depth_enable"] = depth_state(pipe)
            e["blend"] = blending_state(pipe)
            e["cull"] = raster_state(pipe)
            try:
                e["rt"] = [str(t.resource) for t in _output_targets(pipe)]
                # ... and the first of them on its own.  A profile that tells one
                # pass from another by which colour target it is building wants
                # that, not the whole array: an engine is free to bind a fifth
                # target for part of a layer and not the rest of it, and keying
                # on the array then splits one layer into two passes that each
                # look half transparent.  A survey written before this field
                # existed simply has no `rt0`, and a group key of `None` for
                # every draw puts the caller back on the depth target alone.
                e["rt0"] = e["rt"][0] if e["rt"] else None
            except Exception:
                e["rt"] = []
                e["rt0"] = None
        except Exception as ex:
            e["error"] = str(ex)
        survey["draws"].append(e)
        if (n + 1) % 50 == 0:
            note("  surveyed %d/%d" % (n + 1, len(draws)))

    if anonymous:
        survey["notes"].append(
            "%d of %d draw(s) report no vertex semantics (the shader was shipped "
            "stripped, so RenderDoc names every input _inputN); their roles were "
            "recovered from the layout shape" % (anonymous, len(draws)))
        note("  %d draw(s) have no vertex semantics - roles inferred from layout"
             % anonymous)
    with open(SURVEY_PATH, "w", encoding="utf-8") as f:
        json.dump(survey, f, ensure_ascii=False, default=str)
    return survey, by_eid


class _Note(object):
    """The `log` shape `solve` asks for, answered by the progress file.

    The selection and classification rules live in the package's pure-python
    half and want to say what they decided; inside qrenderdoc the only way out is
    `note()`, and a full RunLog would be a file nobody is reading.  This is the
    two methods they call.
    """

    def info(self, msg, **kv):
        extra = ("  " + " ".join("%s=%s" % (k, v) for k, v in kv.items())) if kv else ""
        note("  " + msg + extra)

    def dim(self, msg):
        note(msg)

    def warn(self, msg):
        note("  ! " + msg)


def choose_both(survey, want_eids=None):
    """Every draw to dump, split by kind, decided by the package's own rules.

    Returns ``(draws_by_kind, plan)`` where `plan` is the flat, eid-ordered
    ``[(eid, kind)]`` the probe walks.  `--eids` still short-circuits the whole
    thing: a person naming event ids is pointing at draws, not asking to have
    them classified.

    `want_eids` is the same short circuit for a caller that computed the list
    itself - an event RANGE, which is a person pointing at draws in exactly the
    same way.  Named distinctly from the module-level `EIDS` so the two cannot be
    confused: one comes from the config, the other from the caller.
    """
    solve = pkg("solve")
    kinds = pkg("mesh_kinds")
    named = EIDS or want_eids
    if named:
        got = solve.select_draws(survey, profile(), want_eids=named)
        return ({"skinned": got}, [(int(d["eid"]), "skinned") for d in got])
    chosen = solve.select_meshes(survey, profile(), log=_Note())
    plan = []
    for kind in kinds.KINDS:
        for d in chosen.get(kind) or []:
            plan.append((int(d["eid"]), kind))
    plan.sort(key=lambda t: t[0])
    return chosen, plan


def why_no_mesh(survey):
    """Say *why* nothing was selected, and which knob to turn.

    Two separate questions, so they are answered separately: whether a character
    was there at all (the selection wants skinned draws backed by a large
    structured buffer, and naming the threshold that rejected them beats an empty
    result), and whether any kind of mesh was switched on to begin with.
    """
    kinds = pkg("mesh_kinds")
    prof = profile()
    cfg = kinds.config(prof)
    want = kinds.enabled(cfg)
    sel = prof.select
    min_bone = int(sel.get("min_bone_buffer_bytes", 262144))
    draws = [d for d in (survey.get("draws") or []) if not d.get("error")]
    skinned = [d for d in draws if d.get("has_skin")]
    big = [d for d in skinned
           if max([int(b["size"]) for b in (d.get("buffers") or [])] or [0]) >= min_bone]
    out = ["  mesh kinds asked for: %s"
           % (", ".join("%s(%s)" % (kinds.label_for(k), k) for k in want) or "(none)")]
    out.append("  looked at %d draw call(s): %d carry a skin stream, %d of those"
               " bind a buffer of at least %d bytes"
               % (len(draws), len(skinned), len(big), min_bone))
    if not want:
        out.append("  every kind is switched off - tick at least one (--mesh-types,"
                   " or the GUI's checkboxes)")
        return "\n".join(out)
    if not draws:
        out.append("  the survey found no draw call at all: check --eid-min/--eid-max"
                   " and --max-draws")
        return "\n".join(out)
    hits, _detail = kinds.effect_passes(draws, sel, cfg)
    fx_keys = kinds.fx_pass_keys(sel, cfg)
    if hits:
        out.append("  %d effect pass(es) found - those draws are the fx set"
                   % len(hits))
    if "static" in want:
        block = cfg
        statics = [d for d in draws
                   if kinds.classify_draw(d, kinds.pass_key_of(d, fx_keys) in hits,
                                          block) == "static"]
        out.append("  %d draw(s) classify as static geometry" % len(statics))
    if skinned and not big:
        sizes = sorted(set(max([int(b["size"]) for b in (d.get("buffers") or [])]
                               or [0]) for d in skinned))
        out.append("  largest vertex-shader buffer(s): %s - lower"
                   " 'min_bone_buffer_bytes' in the profile if the palette is one"
                   " of them" % ", ".join(str(s) for s in sizes[-4:]))
    elif not skinned:
        out.append("  no draw has both a four-component integer and a normalised"
                   " four-component stream - the capture may not contain a skinned"
                   " character, or its palette lives somewhere this tool does not"
                   " look")
    out.append("  if the pass is there but nothing was picked, --mesh-types can"
               " narrow or widen what is wanted, and --eids names draws outright")
    return "\n".join(out)


def pass_ends(survey, plan):
    """The last eid of each (render pass, mesh kind) among the draws to dump.

    A depth buffer accumulates over the pass it belongs to, so its final state -
    the only state worth saving - is the one at that pass's last draw.  The kind
    is in the key because a pass and a kind are not the same thing: an engine can
    draw its character, its scene and a later overlay into one depth target
    without ever changing the viewport, and the depth at the *last* of those
    holds far more than the frame the character's camera was recovered from.  The
    silhouette check has to be given the character's own, so the character's own
    end is saved separately.
    """
    kinds = pkg("mesh_kinds")
    sel = profile().select
    by_eid = dict((int(d["eid"]), d) for d in (survey.get("draws") or []))
    last = {}
    for eid, kind in plan:
        d = by_eid.get(int(eid))
        if d is None:
            continue
        key = (kinds.pass_key(d, sel), kind)
        if key not in last or int(eid) > last[key]:
            last[key] = int(eid)
    return sorted(last.values())


# ------------------------------------------------------------------ pass two

def _view_bytes(controller, vbs, slot, offset, want):
    """Read from a bound vertex buffer, trimmed to what the view covers.

    `offset` is measured from the start of the view.  Asking for more than is
    left of it is how the replay gets handed a range it cannot satisfy, so the
    length is cut to the room that is actually there and an empty read is
    returned rather than raised - a short stream is a fact about the capture,
    and the caller's own length checks are what report it.
    """
    room = int(vbs[slot].byteSize) - int(offset)
    if room <= 0 or want <= 0:
        return b""
    return bytes(controller.GetBufferData(vbs[slot].resourceId,
                                          int(vbs[slot].byteOffset) + int(offset),
                                          min(int(want), room)))


def _decode(spec, vbs, controller, base_vertex, count):
    """Read one vertex attribute stream, honouring its declared format."""
    st = int(vbs[spec["slot"]].byteStride)
    raw = _view_bytes(controller, vbs, spec["slot"],
                      spec["off"] + base_vertex * st, st * count)
    cw, ct, nc = spec["cbyte"], spec["ctype"].lower(), spec["comps"]
    vals = []
    for i in range(count):
        ch = raw[i * st:(i + 1) * st]
        row = []
        for k in range(nc):
            o = k * cw
            if o + cw > len(ch):
                row.append(0)
                continue
            if "unorm" in ct:
                row.append(ch[o] / 255.0 if cw == 1 else
                           struct.unpack_from("<H", ch, o)[0] / 65535.0)
            elif "snorm" in ct:
                row.append(max(struct.unpack_from("<b", ch, o)[0] / 127.0, -1.0)
                           if cw == 1 else
                           max(struct.unpack_from("<h", ch, o)[0] / 32767.0, -1.0))
            elif "uint" in ct:
                row.append({1: lambda b: b[0],
                            2: lambda b: struct.unpack_from("<H", b, 0)[0],
                            4: lambda b: struct.unpack_from("<I", b, 0)[0]}[cw]
                           (ch[o:o + cw]))
            elif "sint" in ct:
                row.append({1: lambda b: struct.unpack_from("<b", b, 0)[0],
                            2: lambda b: struct.unpack_from("<h", b, 0)[0],
                            4: lambda b: struct.unpack_from("<i", b, 0)[0]}[cw]
                           (ch[o:o + cw]))
            else:
                row.append(struct.unpack_from("<e", ch, o)[0] if cw == 2
                           else struct.unpack_from("<f", ch, o)[0])
        vals.append(row)
    return vals


def probe_pass(rd, controller, by_eid, eids, kinds=None, depth_eids=None):
    """Dump everything the offline solver needs, for the chosen draws.

    `kinds` maps an eid to what the selector called it - skinned, static or fx -
    and is recorded per draw so the offline half knows which rules to hold each
    one to (an effect mesh is allowed to have no normal stream; a character is
    not) without having to classify anything a second time.

    `depth_eids` are the draws whose depth target is worth saving: the last draw
    of each render pass, because a depth buffer accumulates over its pass.  A
    character capture has one pass and one image; a scene export has several, and
    the silhouette check has to be given the one belonging to the pass the camera
    was recovered from - which is a decision the offline half makes, so the
    images for all of them are kept.
    """
    kinds = kinds or {}
    depth_eids = set(int(e) for e in (depth_eids or ())) or {int(eids[-1])}
    report = {"data": {}, "bone": []}
    bone_done = {}
    want_tex = {}
    want_rt = {}
    depth_px = {}
    for step, eid in enumerate(eids, 1):
        d = os.path.join(RAW, "eid-%d" % eid)
        os.makedirs(d, exist_ok=True)
        e = {"kind": kinds.get(eid, "skinned")}
        note("dumping %s %d/%d (eid %d)"
             % (e["kind"], step, len(eids), eid))
        try:
            controller.SetFrameEvent(eid, True)
            pipe = controller.GetPipelineState()
            a = by_eid.get(eid)
            if a is None:
                report["data"][str(eid)] = {"skip": "action not found"}
                continue
            vp = pipe.GetViewport(0)
            e["viewport"] = [float(vp.x), float(vp.y), float(vp.width), float(vp.height)]
            e["numIndices"] = int(a.numIndices)
            e["numInstances"] = int(a.numInstances)
            try:
                e["depth"] = str(pipe.GetDepthTarget().resource)
            except Exception:
                e["depth"] = None

            vbs = pipe.GetVBuffers()
            inputs = [describe_layout(pipe, vi) for vi in pipe.GetVertexInputs()]
            e["inputs"] = inputs
            prof = profile()
            inf = pkg("adapters").infer_semantics(inputs, prof)
            pos = (next((i for i in inputs if i["name"].upper() == "POSITION"), None)
                   or inf.get("POSITION"))
            bw, bi = pkg("adapters").skin_attributes(inputs, prof)
            # a stream RenderDoc reports with stride 0 is the *constant* one - the
            # shader reads the same four bytes for every vertex, so it holds no
            # per-vertex weights no matter what it is named
            if (bw is None or bi is None
                    or int(bw.get("stride", 0)) <= 0 or int(bi.get("stride", 0)) <= 0):
                bw = bi = None
            if not pos:
                # Two different things, and they read very differently to whoever
                # is looking for a missing mesh.  A draw with *no inputs at all*
                # has nothing to export: the vertex shader invents the geometry
                # from the vertex id, which is how a full-screen effect, a UI
                # blit and a post-process tap are submitted.  A draw with inputs
                # but no position stream is a layout this tool did not recognise.
                report["data"][str(eid)] = {
                    "skip": ("procedural: the shader builds this draw, there is no "
                             "vertex buffer to export" if not inputs
                             else "no POSITION stream")}
                continue

            md = controller.GetPostVSData(0, 0, rd.MeshDataStage.VSOut)
            istride = int(md.indexByteStride)
            # The indices come from the mesh's own copy: RenderDoc already sliced
            # this draw out of the index buffer (its `indexOffset` is spent), so
            # they are the draw's indices as written, counted from zero.
            nidx = int(md.numIndices)
            ioff = int(md.indexByteOffset)
            if istride:
                iraw = bytes(controller.GetBufferData(md.indexResourceId, ioff,
                                                      istride * nidx))
                nidx = len(iraw) // istride
                save(os.path.join(d, "ib.bin"), iraw)
                idx = (list(struct.unpack_from("<%dH" % nidx, iraw, 0)) if istride == 2
                       else list(struct.unpack_from("<%dI" % nidx, iraw, 0)))
            else:
                # No index buffer at all: the draw is `Draw(n, 0)`, so its
                # vertices are 0..n-1 in order.  Effect meshes - ribbons,
                # trails, particle quads - are very often submitted this way,
                # and the older code reported them as "empty index buffer" and
                # dropped them.  RenderDoc reports the vertex count in
                # `numIndices` for a non-indexed draw, which is the only place
                # the number lives.
                nidx = int(md.numIndices or getattr(a, "numIndices", 0) or 0)
                idx = list(range(nidx))
                save(os.path.join(d, "ib.bin"), b"")
            need = (max(idx) + 1) if idx else 0
            # ... but the draw call, not the mesh, is the authority on which
            # vertex index 0 is: this engine writes the real base vertex into the
            # action and leaves the mesh format's copy at zero, which silently
            # shifts the whole part for every draw that does not begin at vertex
            # 0.  That is why the action is asked first and the mesh only falls
            # back.  (`a.indexOffset` needs no use - the copy above is already
            # sliced; it is recorded only to say so.)
            base_vertex = int(getattr(a, "baseVertex", 0) or 0) or int(md.baseVertex)
            e["postvs"] = {"vstride": int(md.vertexByteStride), "istride": istride,
                           "numIndices": nidx, "indexOffset": ioff,
                           "drawIndexOffset": int(getattr(a, "indexOffset", 0) or 0),
                           "baseVertex": base_vertex, "need": need,
                           "indexed": bool(istride)}

            if need == 0:
                report["data"][str(eid)] = {"skip": "empty index buffer"}
                continue

            # Constant buffers first, and deliberately: the camera is recovered
            # from them by the offline half, and *every* draw needs one before
            # anything can be solved.  A draw's mesh, by contrast, is its own
            # business - a layout this tool does not recognise, or a bug in
            # unpacking it, should cost that one part.  Dumping the meshes first
            # made the two share a fate, and a failure in the mesh path surfaced
            # as "no probed draw carries a view-projection", which points at the
            # profile's `vp_rows` and at nothing to do with the real cause.
            cbs = {}
            refl = None
            try:
                refl = pipe.GetShaderReflection(rd.ShaderStage.Vertex)
            except Exception:
                pass
            for slot in range(8):
                try:
                    dd = pipe.GetConstantBlock(rd.ShaderStage.Vertex, slot, 0).descriptor
                except Exception:
                    break
                if int(dd.byteSize) <= 0:
                    continue
                blob = bytes(controller.GetBufferData(dd.resource, int(dd.byteOffset),
                                                      int(dd.byteSize)))
                # `cbN.bin` is named after the binding RenderDoc enumerates, and
                # an engine that hands its constant pool out to several slots in
                # whatever order the shader happens to declare them puts the same
                # block on a different N from draw to draw.  The block's own name
                # is what stays put, so it is recorded next to the dump.
                name, bind = "", None
                try:
                    cb = refl.constantBlocks[slot]
                    name = str(cb.name)
                    bind = getattr(cb, "fixedBindNumber", None)
                except Exception:
                    pass
                cbs[str(slot)] = {"path": save(os.path.join(d, "cb%d.bin" % slot), blob),
                                  "res": str(dd.resource), "off": int(dd.byteOffset),
                                  "size": int(dd.byteSize), "name": name,
                                  "bind": bind}
            e["cbuffers"] = cbs

            if WANT_MESH:
                pstride = int(md.vertexByteStride)
                praw = bytes(controller.GetBufferData(md.vertexResourceId,
                                                      int(md.vertexByteOffset), pstride * need))
                save(os.path.join(d, "postvs.bin"), praw)
                posed = [list(struct.unpack_from("<4f", praw, i * pstride))
                         for i in range(need)]

                nattr = need + PAD
                vstride = int(vbs[pos["slot"]].byteStride)
                vraw = _view_bytes(controller, vbs, pos["slot"],
                                   pos["off"] + base_vertex * vstride,
                                   vstride * nattr)
                nattr = len(vraw) // vstride if vstride else 0
                # The bind position is read the same way as every other stream,
                # by its *declared* format: a game that packs it as half floats
                # would otherwise be handed 32-bit pairs of the first two halves
                # and fitted against positions in the tens of billions.
                bind = [r[:3] for r in _decode(pos, vbs, controller, base_vertex,
                                               nattr)]

                bidx = _decode(bi, vbs, controller, base_vertex, nattr) if bi \
                    else [[0] * 4] * nattr
                wts = _decode(bw, vbs, controller, base_vertex, nattr) if bw \
                    else [[1, 0, 0, 0]] * nattr
                # What the dump has to hold is what the *shader* will read, and
                # the two engines disagree about the fourth weight: a plain
                # four-weight dot wants the four floats to sum to one, while a
                # shader that recomputes the fourth as `1 - (w0+w1+w2)` - this
                # game's does, and never reads the stored fourth value, which is
                # sometimes a stale 1.0 - wants it put back by that same rule.
                # Scaling instead silently halves every weight of such a vertex.
                rule = str(getattr(prof, "skin_weight", "") or "renormalize").lower()
                for i, w in enumerate(wts):
                    if rule.startswith("remainder") or rule.startswith("rest"):
                        wts[i] = [w[0], w[1], w[2], 1.0 - (w[0] + w[1] + w[2])]
                        continue
                    s = sum(w)
                    if s > 1e-6 and abs(s - 1.0) > 0.02:
                        wts[i] = [x / s for x in w]

                # Binary, not JSON.  These blocks are a few million numbers and
                # the probe writes one set per draw: formatting every float as
                # text was the single largest piece of Python time in the collect
                # phase - about a fifth of it on a 2 GB capture - and none of it
                # was ever read by a person.  `util.read_inputs` hands the solver
                # back the same shapes the JSON did, so nothing downstream knows.
                util().write_inputs(os.path.join(d, "inputs.bin"), eid, nattr, need,
                                    pstride, vstride, bind, posed, bidx, wts, idx)

                slots = sorted({i["slot"] for i in inputs if i["stride"] > 0})
                for s in slots:
                    top = max([i["off"] + max(1, i["comps"]) * i["cbyte"]
                               for i in inputs if i["slot"] == s] or [0])
                    st = int(vbs[s].byteStride)
                    # The dump has to start where the draw's vertex 0 starts, so
                    # that record i of the file is `bind[i]` and the offline
                    # reader needs no notion of a base vertex at all.
                    blob = _view_bytes(controller, vbs, s, base_vertex * st,
                                       st * (need + PAD) + top + 64)
                    if not blob:
                        continue
                    save(os.path.join(d, "vb%d.bin" % s), blob)

            # constant buffers were dumped above, before the mesh, so that the
            # camera survives a draw whose geometry this tool cannot unpack

            if bi and bw:
                for bd in rank_buffers(buffer_bindings(pipe, rd)):
                    if int(bd["size"]) < MIN_BONE:
                        continue
                    key = (bd["res"], int(bd["off"]), int(bd["size"]))
                    if key in bone_done:
                        e["bone"] = bone_done[key]
                        break
                    blob = bytes(controller.GetBufferData(bd["rid"], int(bd["off"]),
                                                          int(bd["size"])))
                    # The dump goes next to the draw that needed it, and the later
                    # draws that bind the same buffer point back at *that* file:
                    # one name per pool, or the second pool of a capture silently
                    # replaces the first and every earlier draw is solved against
                    # the wrong bones.
                    info = {"path": save(os.path.join(d, "bone.bin"), blob),
                            "res": bd["res"], "off": int(bd["off"]),
                            "size": int(bd["size"]), "elem": int(bd["elem"])}
                    bone_done[key] = info
                    e["bone"] = info
                    break

            sh = pipe.GetShaderReflection(rd.ShaderStage.Vertex)
            if sh is not None:
                e["shader"] = str(sh.resourceId)
                try:
                    with open(os.path.join(d, "vs.dxbc"), "wb") as f:
                        f.write(bytes(sh.rawBytes))
                    e["disasm"] = rel(os.path.join(d, "vs.dxbc"))
                except Exception:
                    pass

            if WANT_TEXTURES:
                try:
                    for i, s in enumerate(pipe.GetReadOnlyResources(rd.ShaderStage.Pixel,
                                                                    False)):
                        dd = s.descriptor
                        if str(dd.type) not in ("DescriptorType.Image",
                                                "DescriptorType.Texture"):
                            continue
                        tp = os.path.join(d, "tex%d.png" % i)
                        sv = rd.TextureSave()
                        sv.resourceId = dd.resource
                        sv.mip = 0
                        sv.slice.sliceIndex = 0
                        sv.alpha = rd.AlphaMapping.Preserve
                        sv.destType = rd.FileType.PNG
                        sv.channelExtract = -1
                        sv.typeCast = rd.CompType.Typeless
                        controller.SaveTexture(sv, tp)
                        if os.path.exists(tp):
                            want_tex.setdefault(str(eid), []).append(rel(tp))
                except Exception as ex:
                    e["texture_error"] = str(ex)
                note("  saved %d texture(s) for eid %d"
                     % (len(want_tex.get(str(eid), [])), eid))
            e["textures"] = want_tex.get(str(eid), [])

            is_pass_end = eid in depth_eids
            e["pass_end"] = is_pass_end
            if WANT_DEPTH and is_pass_end:
                try:
                    dt = pipe.GetDepthTarget()
                    if int(dt.resource) != 0:
                        sv = rd.TextureSave()
                        sv.resourceId = dt.resource
                        sv.mip = 0
                        sv.slice.sliceIndex = 0
                        sv.alpha = rd.AlphaMapping.Preserve
                        sv.destType = rd.FileType.PNG
                        sv.channelExtract = -1
                        sv.typeCast = rd.CompType.Typeless
                        dp = os.path.join(RAW, "depth_eid%d.png" % eid)
                        controller.SaveTexture(sv, dp)
                        if os.path.exists(dp):
                            e["depth_png"] = rel(dp)
                            depth_px[eid] = _png_width(dp)
                except Exception as ex:
                    e["depth_error"] = str(ex)

            if WANT_RT and is_pass_end:
                # The same draw again, in colour, saved beside the depth target
                # above.  The depth is what the silhouette check measures against,
                # but a depth image cannot answer "which way up is this?" - it is
                # a grey blob, and a reader has to take the orientation on trust.
                # With the colour target as well, "did we get the frame right?"
                # becomes a question anyone can settle by looking at two pictures.
                #
                # All of them are kept and the order is preserved, because which
                # one is the lit image is a property of the engine's g-buffer and
                # not something decidable from here: on a deferred renderer the
                # debug fill, the albedo plane, the normal plane, the emissive
                # pass and the final image are all the same size and all bound by
                # the same draw.  Picking one by index would be a guess that
                # misleads exactly when the reader most needs to trust it; the
                # consumer shows the strip and names the order instead.
                try:
                    for i, rt in enumerate(_output_targets(pipe)):
                        if int(rt.resource) == 0:
                            continue
                        sv = rd.TextureSave()
                        sv.resourceId = rt.resource
                        sv.mip = 0
                        sv.slice.sliceIndex = 0
                        sv.alpha = rd.AlphaMapping.Preserve
                        sv.destType = rd.FileType.PNG
                        sv.channelExtract = -1
                        sv.typeCast = rd.CompType.Typeless
                        rp = os.path.join(RAW, "rt%d_eid%d.png" % (i, eid))
                        controller.SaveTexture(sv, rp)
                        if os.path.exists(rp):
                            want_rt.setdefault(str(eid), []).append(rp)
                except Exception as ex:
                    e["render_target_error"] = str(ex)
                targets = want_rt.get(str(eid)) or []
                if targets:
                    # the depth target the draw also bound is the one thing they
                    # are all guaranteed to share, so it is what tells a target of
                    # *this* pass - and therefore this part's pose - from a
                    # screen-sized leftover
                    e["rt_all"] = [rel(p) for p in targets]
                    e["rt_same_size_as_depth"] = [
                        rel(p) for p in targets
                        if depth_px.get(eid) and _png_width(p) == depth_px[eid]]
                note("  saved %d render target(s) for eid %d"
                     % (len(targets), eid))

            report["data"][str(eid)] = e
        except Exception:
            report["data"][str(eid)] = {"error": traceback.format_exc()}

    report["bone"] = list(bone_done.values())[:1]
    with open(os.path.join(RAW, "probe.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, default=str)
    return report


# ------------------------------------------------------------------ Matex
#
# A SECOND COLLECTION PATH, for material reconstruction rather than for a scene.
#
# It deliberately shares nothing with `probe_pass` except the file-writing
# helpers.  The scene pipeline asks "which draws are the character" and dumps
# those; that question has a right answer for a scene and the wrong one for a
# material library, because the answer is reached by DISCARDING draws - the
# instance split keeps the largest character instance and drops the rest, the
# classifier drops everything that is not the character, and each kind is capped.
# A material run wants every draw, so that a draw call count and a mesh count
# still agree at the end.  So this walks the survey instead of the selection.
#
# What it records is also different in kind.  The scene pipeline needs geometry
# and a bone palette; a material needs to know WHICH SHADER drew this, WHAT the
# constant buffers said, and WHICH texture sat at which binding - and all three
# have to survive as references, because the offline half has to be able to say
# "this texture, in this slot, of this shader" without having the capture.

#: The descriptor type a texture arrives as.
#:
#: NOT the texture's own type.  RenderDoc reports every texture binding as
#: `DescriptorType.Image`, so asking for "Texture2D" finds nothing at all - and
#: finds it silently, which is how the first version of this collected six
#: constants and shaders per draw and not one texture.  The texture's real type
#: (2D, array, cube) comes from the RESOURCE, not from the binding.
MATEX_TEXTURE_DESCRIPTOR = "DescriptorType.Image"

#: Texture kinds a material can use.  Render targets and depth targets are
#: deliberately absent: they are the frame being built, not an asset, and the
#: old `rt` switch is a different question asked by a different pipeline.
MATEX_TEXTURE_TYPES = ("Texture2D", "Texture2DArray", "TextureCube",
                       "TextureCubeArray")

#: Cube faces, in RenderDoc's own slice order, so the offline half can say which
#: face a file is without re-deriving it.
MATEX_CUBE_FACES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")


def _int_field(obj, name, default=0):
    """One integer off a RenderDoc struct, or `default` when it will not say.

    RenderDoc's python bindings expose these per version and not always by the
    same name; a missing attribute is a fact about the build rather than an
    error, and guessing zero is what makes the offline half report "unknown"
    instead of quietly inventing a size.
    """
    try:
        return int(getattr(obj, name))
    except Exception:
        return default


def _texture_type(dd):
    """The descriptor's texture type as a bare word, or "" when not a texture."""
    return str(getattr(dd, "type", "")).split(".")[-1]


def _hash_bytes(blob):
    return hashlib.sha1(blob).hexdigest()


def _save_shader(d, stage, sh):
    """One stage's bytecode on disk, plus the identity the binding file keys on.

    THE HASH IS THE IDENTITY, not `ResourceId`.  A resource id is a handle into
    one replay session - it is not stable across captures, across RenderDoc
    versions or across draws in a way anything outside can rely on - whereas the
    bytecode is the same bytes every time the same shader is used.  The key a
    semantic template is written against has to outlive the capture it was
    learned from, so it is built from this and not from the handle.
    """
    if sh is None:
        return None
    raw = bytes(getattr(sh, "rawBytes", b"") or b"")
    entry = {"id": str(getattr(sh, "resourceId", "")),
             "entry": str(getattr(sh, "entryPoint", "") or ""),
             "sha1": _hash_bytes(raw) if raw else "",
             "bytes": len(raw)}
    if raw:
        rel_path = save(os.path.join(d, "%s-%s.dxbc" % (stage, entry["sha1"][:16])), raw)
        entry["file"] = rel_path
    return entry


def _cbuffer_dump(rd, controller, pipe, d, stage_name, stage):
    """Every constant block bound to one shader stage, bytes and reflection.

    The bytes are what the shader actually read; the reflection is what names
    them.  Both are needed and neither is sufficient: the reflection gives the
    variable names and types but - for DXBC - no byte offset inside a struct, so
    "g_Material.Diffuse" can be named without the layout being recoverable from
    it.  That is why a variable's offset is recorded as `inferred` and carries
    `certain: false` rather than being presented as a reading.  A consumer that
    needs certainty can match the disassembly's `cbN[off]` against it; one that
    only needs the values has them.
    """
    out = []
    refl = None
    try:
        refl = pipe.GetShaderReflection(stage)
    except Exception:
        return out
    if refl is None:
        return out
    for slot in range(16):
        try:
            blk = refl.constantBlocks[slot]
        except Exception:
            break
        try:
            dd = pipe.GetConstantBlock(stage, slot, 0).descriptor
        except Exception:
            continue
        size = _int_field(dd, "byteSize")
        if size <= 0:
            continue
        blob = bytes(controller.GetBufferData(dd.resource,
                                              _int_field(dd, "byteOffset"), size))
        if not blob:
            continue
        name = save(os.path.join(d, "cb-%s-%d.bin" % (stage_name, slot)), blob)
        variables = []
        try:
            for var in blk.variables:
                one = {"name": str(getattr(var, "name", "") or ""),
                       "type": str(getattr(var, "type", "") or ""),
                       "rows": _int_field(var, "rows", 1),
                       "cols": _int_field(var, "columns", 1),
                       "array": _int_field(var, "arraySize", 1),
                       "bind_point": _int_field(var, "bindPoint")}
                # `type.members` is how a struct is named; the reflection does not
                # carry where each member sits, so a struct is flattened to its
                # members' names and flagged rather than given invented offsets.
                members = []
                try:
                    for m in (getattr(getattr(var, "type", None), "members", None) or []):
                        members.append({"name": str(getattr(m, "name", "") or ""),
                                        "type": str(getattr(m, "type", "") or "")})
                except Exception:
                    members = []
                if members:
                    one["members"] = members
                    one["certain"] = False
                variables.append(one)
        except Exception:
            pass
        out.append({"stage": stage_name, "slot": slot, "file": name,
                    "name": str(getattr(blk, "name", "") or ""),
                    "bind": _int_field(blk, "fixedBindNumber", -1),
                    "size": size, "bytes": len(blob),
                    "variables": variables})
    return out


def _texture_dump(rd, controller, pipe, d, stage_name, stage, seen, stats, wrong_types,
                  targets, viewports):
    """One stage's texture bindings, saved as PNG, one file per slice or face.

    ARRAYS AND CUBES ARE SPLIT, and each slice gets its own file and its own
    binding entry.  A DCC material samples a 2D image; handing it an array would
    mean every consumer re-implementing the same slicing, and the whole point of
    the binding file is that the offline half can build the material without
    knowing what a texture array is.  The slice index is in the name and in the
    binding record, so the association is not something anyone has to guess.

    Read-only resources are walked FIRST and read-write ones only for names: a
    render target is not an asset, so it is recorded (so a binding can point at
    it and be visibly unresolved) but never saved.  The old `textures` switch
    saves the read-write side too - which is one more reason the two switches are
    separate.
    """
    out = []
    # ---- what the SHADER declares, independently of what is bound ----------
    #
    # This is the half that made textures findable at all.  `GetReadOnlyResources`
    # on this engine returns constant buffers and nothing else, so a walk of it
    # finds zero textures however right the type filter is - and a filter that is
    # never reached looks exactly like a capture with no textures in it.  The
    # reflection is the shader's own statement of what it reads, and it carries
    # the binding NAME, which is the thing a semantic template is written
    # against.  Reported whether or not the binding resolves, because "the shader
    # declares four textures and none of them is bound" is a different fact from
    # "the shader declares none" and both are worth having.
    srv_slots = []
    srv_name = {}
    srv_type = {}
    srv_desc = {}
    try:
        refl = pipe.GetShaderReflection(stage)
        for bp, r in enumerate(getattr(refl, "readOnlyResources", None) or []):
            rtype = str(getattr(r, "type", "") or "").split(".")[-1]
            fmt = getattr(r, "format", None)
            # The format, by whichever of its names answers.  A `ResourceFormat`
            # carries a compiled `name` and a `type`; the plain-string case is
            # there for a build that hands one out instead.  It is recorded
            # because it is the only thing that says whether the pixels are
            # sRGB-encoded, and a normal map read as sRGB is a specific and
            # recognisable kind of wrong that no amount of looking fixes.
            fmt_name = ""
            if isinstance(fmt, str):
                fmt_name = fmt
            elif fmt is not None:
                for attr in ("name", "type", "compCount"):
                    got = getattr(fmt, attr, None)
                    if got is not None and attr != "compCount":
                        fmt_name = str(got)
                        break
            srv_desc[bp] = {"type": rtype,
                            "array": _int_field(r, "arraySize", 1),
                            "format": fmt_name.split(".")[-1]}
            if not getattr(r, "isTexture", False):
                continue
            name = str(getattr(r, "name", "") or "") or ("t%d" % bp)
            srv_name[bp] = name
            # `TextureType.Texture2D` -> `Texture2D`, and `Unknown` stays
            # `Unknown` so the caller can tell "not a texture kind this tool
            # exports" from "the reflection did not say".
            ttype = str(getattr(r, "textureType", "") or "").split(".")[-1]
            if ttype and ttype != "Unknown":
                srv_type[bp] = ttype
            srv_slots.append({"bind_point": bp, "name": name, "type": ttype,
                              "array": srv_desc[bp]["array"],
                              "format": srv_desc[bp]["format"]})
    except Exception:
        pass
    stats["srv_declared"] = stats.get("srv_declared", 0) + len(srv_slots)

    lists = []
    for writable in (False, True):
        try:
            got = list(pipe.GetReadOnlyResources(stage, writable) or [])
        except Exception as ex:
            got = []
            wrong_types["%s/%s raised %s" % (stage_name, writable, type(ex).__name__)] = 1
        if not got:
            stats["stages_empty"] += 1
        # What came back, by type AND by resource id, so a binding that resolves
        # to the wrong thing is visible rather than merely absent.  The
        # reflection above says the shader reads a texture; this says whether the
        # walk found it, and the two together are the whole answer.
        listed = stats.setdefault("listed", {})
        for s in got:
            dd = getattr(s, "descriptor", None)
            key = "%s/%s/%s" % (stage_name, "ro" if not writable else "rw",
                                "none" if dd is None else str(getattr(dd, "type", "")))
            entry = listed.setdefault(key, {"count": 0, "sample": []})
            entry["count"] += 1
            if len(entry["sample"]) < 4:
                entry["sample"].append("%s %s" % (getattr(dd, "resource", "?"),
                                                  getattr(s, "name", "")))
        lists.append((writable, got))
    for writable, resources in lists:
        # The read-write walk is a FALLBACK, not a second pass.
        #
        # This engine returns the same image bindings from both lists, so walking
        # both recorded every texture twice - once with its file and once with
        # `files: []`, because the second pass saw `writable: True` and treated it
        # as a render target.  Two entries for one binding, one of them claiming
        # there is no file, is the kind of duplication a consumer resolves
        # silently and wrongly.  So the read-write list is consulted only when the
        # read-only one told us nothing; when it did, the duplicates are dropped.
        if writable and any(True for _w, r in lists if not _w and r):
            continue
        for bind_point, s in enumerate(resources):
            dd = getattr(s, "descriptor", None)
            if dd is None or str(getattr(dd, "type", "")) != MATEX_TEXTURE_DESCRIPTOR:
                stats["not_texture"] += 1
                # The name of what it IS, not just that it was rejected.  The
                # first version of this counted six rejections per draw without
                # saying what they were, and "RenderDoc calls textures
                # DescriptorType.Image rather than Texture2D" took a probe and a
                # second look to find; one dictionary answers it from the log.
                kind = "no-descriptor" if dd is None else str(getattr(dd, "type", ""))
                wrong_types[kind] = wrong_types.get(kind, 0) + 1
                continue
            # ---- describe the resource, without an accessor that exists ------
            #
            # This is the one place in the driver where the obvious API call had
            # to be abandoned rather than corrected.  There is no
            # `GetResourceDescription` on a ReplayController and no `GetTexture`
            # either, and neither is on the PipeState; all four spellings were
            # tried and all four raised AttributeError.  A version of this that
            # swallowed that exception reported "this capture has no textures"
            # for a capture whose shaders plainly declare `texture0` - the exact
            # failure the project's notes describe, where a reader that says
            # nothing looks like a reader that found nothing.
            #
            # So the description is assembled from what DOES answer:
            #
            #   the binding name and the SRV's own type  <- the shader reflection
            #   the resource id                           <- the descriptor
            #   the dimensions                            <- the PNG it just wrote
            #
            # The dimensions come from the file rather than from an API because
            # the file is written from the mip the material will sample, so its
            # size IS the size that matters - not the base mip's.
            ttype = srv_type.get(bind_point, "")
            if ttype and ttype not in MATEX_TEXTURE_TYPES:
                stats["wrong_type"] += 1
                wrong_types[ttype] = wrong_types.get(ttype, 0) + 1
                continue
            if not ttype:
                # The reflection said nothing for this slot.  Its type is then
                # unknown rather than wrong, and a cube bound where a cube is
                # expected would be sliced once instead of six times - so the
                # export says it does not know instead of guessing.
                stats["unknown_type"] += 1
            # The resource ID, taken as an object rather than as text.  Saving
            # wants the object; `str()` on it gives "ResourceId::94852", which is
            # what goes in the binding file.
            resid_obj = getattr(dd, "resource", None)
            resid = str(resid_obj)
            bind_name = srv_name.get(bind_point, "") or str(getattr(s, "name", "") or "")
            stats["bindings"] += 1
            entry = {"stage": stage_name, "bind_point": bind_point, "type": ttype,
                     "resource": resid, "shader_name": bind_name, "writable": writable,
                     "resource_name": "", "size": None, "mips": None,
                     "array_size": None, "format": srv_desc.get(bind_point, {}).get("format", ""),
                     "ms_quality": 0, "sample_count": 1}
            # ---- is this the FRAME rather than an asset? --------------------
            #
            # TWO tests, because either alone has been wrong in practice.
            #
            #   by resource id  a resource that is a target ANYWHERE in the
            #                   capture.  This is the precise test, and it is
            #                   the one that catches a later pass sampling an
            #                   earlier pass's colour target - at that draw the
            #                   target is an ordinary read-only binding and
            #                   nothing on it says "target".
            #   by dimensions   a texture whose size equals a viewport in this
            #                   capture.  The frame is the size of the frame;
            #                   an authored asset that happens to be exactly
            #                   1506x846 is possible and would be a false
            #                   positive, which is why this is a SECOND test
            #                   and why the count is reported - a person can
            #                   see an asset disappear and say so.
            #
            # Measured on 提丰.rdc before this: 13 library textures were the
            # frame itself (1506x846 ten times, 377x212 twice).  The user found
            # it by looking at the pictures, which is the only way it was going
            # to be found.
            entry["is_target"] = resid in targets
            size = entry.get("size")
            by_size = bool(size) and (int(size[0]), int(size[1])) in viewports
            if by_size:
                entry["is_target"] = True
                entry["target_reason"] = ("its dimensions equal a viewport in this "
                                          "capture (%dx%d)" % (int(size[0]), int(size[1])))
                stats["target_by_size"] = stats.get("target_by_size", 0) + 1
            if writable or entry["is_target"]:
                # Recorded so a binding can point at it and be visibly
                # unresolved, never saved.  The frame being built is not an asset.
                stats["writable" if writable else "target"] += 1
                entry["files"] = []
                out.append(entry)
                continue
            # How many slices to take: six for a cube, one for a 2D texture, and
            # for an array it is not known until it is read - an array is a set
            # of slices and the descriptor does not say how many, so what the
            # shader declared is what is used, and any slice past the end simply
            # fails to write a file rather than being skipped in silence.
            per_slice = 6 if ttype.startswith("TextureCube") else 1
            slices = per_slice * max(1, srv_desc.get(bind_point, {}).get("array", 1) or 1)
            entry["face_names"] = list(MATEX_CUBE_FACES) if per_slice == 6 else None

            # SLICE 0 IS SAVED FIRST, and its PNG header is where the dimensions
            # come from.  The dimension test has to run before the rest of the
            # slices are written, or the frame is already on disk by the time it
            # is recognised; and this is the only source of a texture's size on a
            # build where the reflection reports no format and no dimensions.
            # A cube's first face is the same size as the other five, so asking
            # the file costs nothing and decides everything.
            files = []
            base = os.path.join(d, "tex")
            os.makedirs(base, exist_ok=True)
            stem = resid.replace("::", "_")

            def save_slice(index):
                path = os.path.join(base, "%s[%d].png" % (stem, index))
                sv = rd.TextureSave()
                sv.resourceId = resid_obj
                sv.mip = 0
                sv.slice.sliceIndex = index
                try:
                    sv.slice.sliceMask = 1 << index
                except Exception:
                    pass
                sv.alpha = rd.AlphaMapping.Preserve
                sv.destType = rd.FileType.PNG
                sv.channelExtract = -1
                sv.typeCast = rd.CompType.Typeless
                try:
                    controller.SaveTexture(sv, path)
                except Exception as ex:
                    entry.setdefault("errors", []).append(str(ex))
                    stats["save_refused"] += 1
                    return None
                if not os.path.exists(path):
                    # SaveTexture returning without raising and without writing a
                    # file is the one failure that leaves no trace anywhere else,
                    # so it is counted on its own.
                    stats["save_refused"] += 1
                    return None
                return path

            first = save_slice(0)
            if first is not None:
                size = _png_size(first)
                if size:
                    entry["size"] = list(size)
                    files.append(rel(first))
                    stats["saved"] += 1
                    seen.setdefault((resid, 0), rel(first))

            # ---- is this the FRAME rather than an asset? --------------------
            #
            # TWO tests, because either alone has been wrong in practice.
            #
            #   by resource id  a resource that is a target ANYWHERE in the
            #                   capture.  This is the precise one, and it is what
            #                   catches a later pass sampling an earlier pass's
            #                   colour target: at THAT draw the target is an
            #                   ordinary read-only binding and nothing on it says
            #                   "target".
            #   by dimensions   a texture whose size equals a viewport in this
            #                   capture.  The frame is the size of the frame.  An
            #                   authored asset that is exactly 1506x846 is
            #                   possible and would be a false positive - which is
            #                   why it is a SECOND test and why the count is
            #                   reported, so a person can see an asset disappear
            #                   and say so.
            #
            # Measured on 提丰.rdc before this: 13 library textures were the frame
            # itself (1506x846 ten times, 377x212 twice).  The user found it by
            # looking at the pictures, which was the only way it was going to be
            # found.
            size = entry.get("size")
            by_size = bool(size) and (int(size[0]), int(size[1])) in viewports
            if resid in targets:
                entry["is_target"] = True
            elif by_size:
                entry["is_target"] = True
                entry["target_reason"] = (
                    "its dimensions equal a viewport in this capture (%dx%d)"
                    % (int(size[0]), int(size[1])))
                stats["target_by_size"] = stats.get("target_by_size", 0) + 1
            if entry["is_target"]:
                # The frame, not an asset.  What was written a moment ago is
                # removed rather than left: recognising it only after writing it
                # is one wasted write, and leaving the file would put the frame
                # in the library anyway, which is the whole thing being fixed.
                stats["writable" if writable else "target"] += 1
                for f in files:
                    try:
                        os.remove(os.path.join(WORK, f))
                    except Exception:
                        pass
                stats["saved"] -= len(files)
                entry["files"] = []
                out.append(entry)
                continue

            for i in range(1, slices):
                path = save_slice(i)
                if path is None:
                    continue
                files.append(rel(path))
                stats["saved"] += 1
                seen.setdefault((resid, i), rel(path))
            entry["files"] = files
            out.append(entry)
    # What the shader said it reads, kept beside what was actually found.  When
    # the two disagree the reason is in this record, and when they agree and
    # there are no files the reason is the type filter - which is the whole
    # diagnostic value of writing both down.
    if srv_slots:
        declared = stats.setdefault("srv_by_stage", {})
        declared.setdefault(stage_name, []).append(srv_slots)
    return out


def _mesh_dump(rd, controller, d, action, vbs, inputs, pos):
    """The vertex data of one draw, in the layout the offline reader already knows.

    Same files as the scene pipeline (`vb<N>.bin`, `ib.bin`, `inputs.bin`),
    because reading them back is a solved problem and a second reader for the
    same bytes would be a second set of bugs.

    What is NOT here is as important as what is: no palette is searched for, no
    fit is run, no placement is decided and no alignment is inferred.  A material
    run wants the bindings a shader had and the geometry they were drawn over;
    the pose belongs to whoever solves the scene, and solving it here would make
    this path depend on a game's rules - which is exactly what it must not do.

    Alignment is the one place the missing fit shows up.  The scene pipeline pads
    its reads by `PAD` and searches for the offset because a post-VS array does
    not always start where the action claims.  With no residual to check a
    candidate against, searching would be guessing, so the dump is written from
    vertex zero, exactly as the draw says, and the offline half is told so.
    """
    md = controller.GetPostVSData(0, 0, rd.MeshDataStage.VSOut)
    wanted = int(md.numIndices or getattr(action, "numIndices", 0) or 0)
    istride = int(md.indexByteStride)
    if istride:
        raw = bytes(controller.GetBufferData(md.indexResourceId,
                                             int(md.indexByteOffset),
                                             istride * wanted))
        wanted = len(raw) // istride
        save(os.path.join(d, "ib.bin"), raw)
        idx = (list(struct.unpack_from("<%dH" % wanted, raw, 0)) if istride == 2
               else list(struct.unpack_from("<%dI" % wanted, raw, 0)))
    else:
        # A draw with no index buffer is `Draw(n, 0)`: vertices 0..n-1 in order.
        # RenderDoc reports n in `numIndices`, which is the only place it lives.
        idx = list(range(wanted))
        save(os.path.join(d, "ib.bin"), b"")
    if not idx:
        return None
    need = max(idx) + 1
    base_vertex = int(getattr(action, "baseVertex", 0) or 0) or int(md.baseVertex)
    pstride = int(md.vertexByteStride)
    praw = bytes(controller.GetBufferData(md.vertexResourceId,
                                          int(md.vertexByteOffset), pstride * need))
    posed = [list(struct.unpack_from("<4f", praw, i * pstride))
             for i in range(need)]

    nattr = need
    vstride = int(vbs[pos["slot"]].byteStride)
    vraw = _view_bytes(controller, vbs, pos["slot"],
                       pos["off"] + base_vertex * vstride, vstride * nattr)
    nattr = len(vraw) // vstride if vstride else 0
    if nattr == 0:
        return None
    bind = [r[:3] for r in _decode(pos, vbs, controller, base_vertex, nattr)]

    # One rigid row per vertex.  The scene pipeline needs real weights because it
    # solves a pose; this path never reads them, and inventing a skinning stream
    # would tell the offline half a draw is skinned when nothing established it.
    bidx = [[0] * 4] * nattr
    wts = [[1, 0, 0, 0]] * nattr

    util().write_inputs(os.path.join(d, "inputs.bin"), int(action.eventId), nattr,
                        need, pstride, vstride, bind, posed, bidx, wts, idx)

    # Every stream the draw declares, with the size the layout says it needs, so
    # the offline half reads whole attributes - a stream trimmed to the vertex
    # count and nothing more loses the last vertex's tail and the reader's own
    # bounds check refuses the file rather than reading past it.
    slots = sorted({i["slot"] for i in inputs if i["stride"] > 0})
    for s in slots:
        top = max([i["off"] + max(1, i["comps"]) * i["cbyte"]
                   for i in inputs if i["slot"] == s] or [0])
        st = int(vbs[s].byteStride)
        blob = _view_bytes(controller, vbs, s, base_vertex * st,
                           st * nattr + top + 64)
        if blob:
            save(os.path.join(d, "vb%d.bin" % s), blob)
    return {"nverts": nattr, "nidx": len(idx), "need": need, "vstride": vstride,
            "pstride": pstride, "base_vertex": base_vertex,
            "indexed": bool(istride), "slots": slots,
            "aligned": False,
            "note": "dumped from vertex zero as the action states it; no "
                    "alignment search was run because no fit was done"}


def matex_pass(rd, controller, survey, by_eid):
    """One dump per draw call, for the material library.

    THE SELECTION IS THE DIFFERENCE.  The scene pipeline reaches its draw list
    through `select_meshes`, which finds the one character instance the run is
    about and drops everything else - another instance of the same model, a
    second character, anything the classifier does not recognise.  That is
    correct for a scene and wrong for a material library, where the count of
    meshes has to still agree with the count of draw calls.  So every draw in the
    survey is taken, and the only thing that narrows it is the event range, which
    is the user's own choice.

    A draw is skipped only when there is nothing to export: no vertex input at
    all means the shader builds the geometry from the vertex id (a full-screen
    pass, a blit, a post-process tap), and an FBX of it would be a file with no
    mesh in it.  Those are counted and named, not silently dropped.
    """
    draws = [d for d in (survey.get("draws") or []) if not d.get("error")]
    draws.sort(key=lambda d: int(d["eid"]))
    note("matex collecting %d draw call(s)" % len(draws))
    if not draws:
        return
    # ---- every resource this capture ever renders INTO ---------------------
    #
    # A RENDER TARGET IS NOT ONLY WHAT THE CURRENT DRAW WRITES.  The per-draw
    # test - "is this one of MY output or depth targets" - is what the rule was
    # originally written as, and it is not enough: a later pass samples an
    # earlier pass's colour target, and at THAT draw the target is an ordinary
    # read-only texture binding that nothing marks as a target.
    #
    # Measured on 提丰.rdc: 13 textures in the library had dimensions equal to a
    # viewport (1506x846 ten of them, 377x212 two) - the frame itself, exported
    # as if it were an asset.  The user caught it by looking at the pictures.
    #
    # So the set is built once, over EVERY draw, before any texture is saved: a
    # resource that is a target anywhere in the capture is the frame, and the
    # frame is not a material input.
    targets_global = set()
    viewports = set()
    for sd in draws:
        d0 = str(sd.get("depth") or "")
        if d0:
            targets_global.add(d0)
        for t in (sd.get("rt") or []):
            targets_global.add(str(t))
        v = sd.get("viewport")
        if isinstance(v, (list, tuple)) and len(v) == 4:
            try:
                w_, h_ = int(v[2]), int(v[3])
                if w_ > 0 and h_ > 0:
                    viewports.add((w_, h_))
            except Exception:
                pass
    note("  matex: %d resource(s) are render targets somewhere, %d viewport size(s)"
         % (len(targets_global), len(viewports)))
    # ---- telemetry, and it is not decoration ------------------------------
    #
    # The first run of this collected 3359 files of shaders and constant buffers
    # and NOT ONE texture, and from the outside "this capture binds no textures"
    # and "the texture code never ran" are the same picture.  A counter per
    # reason is what tells them apart without a second sixty-minute run, and the
    # reasons are the ones that can actually happen: a stage that binds nothing,
    # a resource that is not a texture, one that is a type this tool does not
    # export (a render target), and a SaveTexture that refused.
    stats = {"stages_empty": 0, "not_texture": 0, "wrong_type": 0, "no_resource": 0,
             "unknown_type": 0, "writable": 0, "target": 0, "save_refused": 0,
             "saved": 0, "bindings": 0}
    #: Which types were rejected, by name and count.  A count alone says the
    #: filter fired; the names say whether the filter is right - and the first
    #: version of this rejected all six of a draw's bindings without saying what
    #: they were, which is a dead end for whoever reads it next.
    wrong_types = {}
    report = {"data": {}, "skipped": [], "stats": stats, "wrong_types": wrong_types}
    seen_tex = {}
    note("matex collecting %d draw call(s)" % len(draws))
    for step, sd in enumerate(draws, 1):
        eid = int(sd["eid"])
        d = os.path.join(MAT, "eid-%d" % eid)
        os.makedirs(d, exist_ok=True)
        action = by_eid.get(eid)
        if action is None:
            report["skipped"].append({"eid": eid, "reason": "action not found"})
            continue
        try:
            controller.SetFrameEvent(eid, True)
            pipe = controller.GetPipelineState()
        except Exception as ex:
            report["skipped"].append({"eid": eid, "reason": "SetFrameEvent: %s" % ex})
            continue
        entry = {"eid": eid, "numIndices": int(sd.get("numIndices") or 0),
                 "numInstances": int(sd.get("numInstances") or 0),
                 "viewport": sd.get("viewport"), "depth": sd.get("depth")}
        try:
            entry["shaders"] = {
                "vs": _save_shader(d, "vs", pipe.GetShaderReflection(rd.ShaderStage.Vertex)),
                "ps": _save_shader(d, "ps", pipe.GetShaderReflection(rd.ShaderStage.Pixel)),
            }
        except Exception as ex:
            entry["shader_error"] = str(ex)
        try:
            entry["cbuffers"] = (
                _cbuffer_dump(rd, controller, pipe, d, "vs", rd.ShaderStage.Vertex) +
                _cbuffer_dump(rd, controller, pipe, d, "ps", rd.ShaderStage.Pixel))
        except Exception as ex:
            entry["cbuffer_error"] = traceback.format_exc()
        # The target test is NOT done here any more.  It used to be per draw -
        # "is this one of MY output or depth targets" - and that misses the case
        # that mattered: a later pass samples an earlier pass's colour target, and
        # at that draw the target is an ordinary read-only binding.  The set is
        # built once, over every draw, before any texture is saved.
        try:
            entry["textures"] = (
                _texture_dump(rd, controller, pipe, d, "vs", rd.ShaderStage.Vertex,
                              seen_tex, stats, wrong_types, targets_global,
                              viewports) +
                _texture_dump(rd, controller, pipe, d, "ps", rd.ShaderStage.Pixel,
                              seen_tex, stats, wrong_types, targets_global,
                              viewports))
        except Exception as ex:
            entry["texture_error"] = traceback.format_exc()
        try:
            inputs = [describe_layout(pipe, vi) for vi in pipe.GetVertexInputs()]
            entry["inputs"] = inputs
            vbs = pipe.GetVBuffers()
            pos = next((i for i in inputs
                        if i["name"].upper() == "POSITION" and i["stride"] > 0), None)
            if pos is None:
                entry["skip"] = ("procedural: the shader builds this draw, "
                                 "there is no vertex buffer to export"
                                 if not inputs else "no POSITION stream")
                report["skipped"].append({"eid": eid, "reason": entry["skip"]})
            else:
                entry["mesh"] = _mesh_dump(rd, controller, d, action, vbs, inputs, pos)
                if entry["mesh"] is None:
                    entry["skip"] = "no vertex data"
                    report["skipped"].append({"eid": eid, "reason": "no vertex data"})
        except Exception as ex:
            entry["mesh_error"] = traceback.format_exc()
            report["skipped"].append({"eid": eid, "reason": "mesh: %s" % ex})
        report["data"][str(eid)] = entry
        # THE PER-DRAW DETAIL GOES BESIDE ITS OWN BYTES, not into the manifest.
        #
        # The first version put all of it in one document, and on a 352-draw
        # scene that document reached ~180 MB: every draw's full input layout,
        # every constant buffer's variable list and every texture binding, with
        # the per-slice `files` arrays repeated in full for each of the draws
        # that bound the same texture.  It was truncated mid-write on the way to
        # the disk, which is a failure that looks like a corrupt file rather than
        # like a design mistake - and the manifest is the one document a person
        # opens by hand, so making it the bulk store was wrong twice.
        #
        # `matex.json` is now the index: one entry per draw, enough to know what
        # is there and where.  The rest is in `draw.json` in the draw's own
        # directory, which is where the constant buffers and the vertex buffers
        # already are.
        try:
            dpath = os.path.join(d, "draw.json")
            with open(dpath, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, default=str)
            report["data"][str(eid)] = {
                "eid": eid,
                "dir": rel(d),
                "detail": rel(dpath),
                "kinds": entry.get("kind"),
                "shaders": {"vs": (entry.get("shaders") or {}).get("vs", {}).get("sha1", ""),
                            "ps": (entry.get("shaders") or {}).get("ps", {}).get("sha1", "")},
                "cbuffers": len(entry.get("cbuffers") or []),
                "textures": len(entry.get("textures") or []),
                "skip": entry.get("skip"),
            }
        except Exception as ex:
            report["skipped"].append({"eid": eid, "reason": "draw.json: %s" % ex})
        if step % 25 == 0:
            note("  matex dumped %d/%d" % (step, len(draws)))
    note("matex: %d draw(s) dumped, %d skipped, %d texture slice(s); "
         "stages empty %d, not-a-texture %d, wrong type %d, render targets %d, "
         "save refused %d, saved %d"
         % (len(report["data"]), len(report["skipped"]), len(seen_tex),
            stats["stages_empty"], stats["not_texture"], stats["wrong_type"],
            stats["writable"], stats["save_refused"], stats["saved"]))
    with open(os.path.join(MAT, "matex.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, default=str)
    return report


# ----------------------------------------------------------------------- main

def main():
    import renderdoc as rd

    # the package is used for the pure-python character selection
    pkg_root = CFG.get("package_root")
    if pkg_root and pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)

    cap = rd.OpenCaptureFile()
    if cap.OpenFile(CAPTURE, "", None) != rd.ResultCode.Succeeded:
        raise RuntimeError("RenderDoc could not open %s" % CAPTURE)
    if cap.LocalReplaySupport() != rd.ReplaySupport.Supported:
        raise RuntimeError("this capture cannot be replayed locally (%s)"
                           % cap.LocalReplaySupport())
    status, controller = cap.OpenCapture(rd.ReplayOptions(), None)
    if controller is None:
        raise RuntimeError("replay failed: %s" % status)

    try:
        if STAGE == "probe":
            # the survey already exists - reuse it rather than walking the
            # capture's draw calls a second time
            with open(SURVEY_PATH, encoding="utf-8-sig") as f:
                survey = json.load(f)
            every = []
            walk(controller.GetRootActions(), every)
            by_eid = dict((int(a.eventId), a) for a in every)
        else:
            survey, by_eid = survey_pass(rd, controller)

        if STAGE == "survey":
            RESULT["survey"] = {"draws": len(survey.get("draws") or []),
                                "total_actions": survey.get("total_actions")}
            # The survey stage stops before dumping, but saying what *would* be
            # dumped is the whole point of asking for a survey on a new capture.
            try:
                _chosen, preview = choose_both(survey)
                counts = {}
                for _e, k in preview:
                    counts[k] = counts.get(k, 0) + 1
                RESULT["kinds"] = dict((str(e), k) for e, k in preview)
                note("would export: %s"
                     % (", ".join("%s=%d" % (k, counts[k]) for k in sorted(counts))
                        or "(nothing)"))
            except Exception as ex:
                note("  ! could not classify this survey: %s" % ex)
            RESULT["ok"] = True
            return

        # ---- Matex: a different question, so a different pass ---------------
        #
        # Checked BEFORE the scene selection, and `return`s: the two must not
        # both run.  Asking the scene selector to pick a character and then
        # dumping every draw anyway would cost the selection time and then throw
        # its answer away, and - worse - would leave a run whose log says "59
        # parts" next to a directory holding 3000 of them.
        if WANT_MATEX:
            report = matex_pass(rd, controller, survey, by_eid)
            stats = report.get("stats") or {}
            RESULT["matex"] = {"dumps": len(report["data"]),
                               "skipped": len(report["skipped"]),
                               # Every one of these is a way for the count to be
                               # lower than a person expects, and each says which
                               # - which is the difference between "this capture
                               # binds no textures" and "the export is broken".
                               "bindings": stats.get("bindings", 0),
                               "textures_saved": stats.get("saved", 0),
                               "not_a_texture": stats.get("not_texture", 0),
                               "wrong_type": stats.get("wrong_type", 0),
                               "render_targets": stats.get("writable", 0),
                               "save_refused": stats.get("save_refused", 0),
                               "wrong_types_seen": report.get("wrong_types", {})}
            RESULT["survey"] = {"draws": len(survey.get("draws") or [])}
            RESULT["ok"] = True
            return

        # AN EVENT RANGE IS AN EXPLICIT CHOICE HERE TOO, not only a Matex one.
        #
        # Without this, a scene read of `--eid-min 572 --eid-max 2723` still went
        # through `select_meshes`, which found ONE CHARACTER INSTANCE and its
        # drop-the-rest rules: 36 draws dumped out of the 91 in that range.  The
        # consequence only showed up in Matex - the solver could pose and place 26
        # parts, so a Matex library built from a `solve` covered the character and
        # left the rest of the scene in its bind pose at the origin.
        #
        # A range given by hand is a person pointing at draws, and `--eids`
        # already means exactly that: take them as they are, classify nothing,
        # drop nothing.  So the range is passed through as that list.
        want = None
        if EID_MIN is not None or EID_MAX is not None:
            lo = int(EID_MIN) if EID_MIN is not None else 0
            hi = int(EID_MAX) if EID_MAX is not None else 1 << 30
            want = [int(d["eid"]) for d in (survey.get("draws") or [])
                    if lo <= int(d["eid"]) <= hi]
            note("event range %d..%d: taking all %d draw(s) as named, not selecting"
                 % (lo, hi, len(want)))

        chosen, plan = choose_both(survey, want_eids=want)
        if not plan:
            raise RuntimeError("no mesh to export in %s\n%s"
                               % (CAPTURE, why_no_mesh(survey)))
        eids = [eid for eid, _kind in plan]
        kind_of = dict(plan)
        RESULT["selected"] = eids
        RESULT["kinds"] = dict((str(e), k) for e, k in plan)
        counts = {}
        for _e, k in plan:
            counts[k] = counts.get(k, 0) + 1
        note("selected %d draw(s): %s"
             % (len(eids), ", ".join("%s=%d" % (k, counts[k]) for k in sorted(counts))))
        note("   eids %s" % eids)

        report = probe_pass(rd, controller, by_eid, eids, kind_of,
                            depth_eids=pass_ends(survey, plan))
        RESULT["probed"] = list(report["data"].keys())
        RESULT["survey"] = {"draws": len(survey.get("draws") or [])}
        RESULT["ok"] = True
    finally:
        try:
            controller.Shutdown()
        except Exception:
            pass
        try:
            cap.Shutdown()
        except Exception:
            pass


try:
    main()
    finish(0)
except BaseException:                        # including SystemExit/KeyboardInterrupt
    RESULT["error"] = traceback.format_exc()
    finish(1)
