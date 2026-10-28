# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.

"""Per-game adapters: the seam between the generic solver and one engine's rules.

Everything that is likely to differ between games lives on an Adapter:

    camera()               where the view-projection is and how to read it
    palette_candidates()   where the bone palette base comes from
    model_transform()      object -> world
    classify_attributes()  which vertex stream is a UV / normal / tangent

`solve.py` only does the mathematics (skinning, least squares, world placement);
it asks the adapter for anything engine specific.  Adding a game means adding a
class here and naming it in the profile - the pipeline never changes.
"""
import math
import re
import struct

from .util import decode_packed_normal, norm3, read_comps, unit3


# ------------------------------------------------------- naming the unnameable

#: RenderDoc auto-names an input whose shader gave it no semantic `_inputN`.
_ANON_NAME = re.compile(r"^_input\d+$", re.I)

#: Descriptor types that can hold a structured bone palette.
BUFFER_DESCRIPTORS = ("DescriptorType.Buffer", "DescriptorType.TypedBuffer",
                      "DescriptorType.ReadWriteBuffer",
                      "DescriptorType.ReadWriteTypedBuffer")


def is_anonymous(inputs):
    """True when the capture reports no semantic names at all.

    A stripped vertex shader leaves RenderDoc with nothing but ``_input0``,
    ``_input1`` ... - every name-based lookup then fails even though the data is
    perfectly readable.
    """
    named = [i for i in (inputs or [])
             if i.get("name") and not _ANON_NAME.match(str(i["name"]))]
    return bool(inputs) and not named


def _ctype(inp):
    return str(inp.get("ctype", "")).lower()


def _is_float(inp):
    return _ctype(inp).endswith("float")


def _is_uint(inp):
    return _ctype(inp).endswith("uint")


def _size(inp):
    return max(1, int(inp.get("comps", 1))) * max(1, int(inp.get("cbyte", 4)))


def _order(inp):
    """Stream position: the order the data actually sits in the buffers."""
    return (int(inp.get("slot", 0)), int(inp.get("off", 0)))


def _cb_slot(cbs, sel):
    """Which dumped constant buffer a profile selector names, or None.

    A profile may address a block by index or by the shader's own name; the
    named form is what survives a draw that declares its constant pool on a
    different slot, so it is the one the newer profiles use.
    """
    if hasattr(cbs, "slot"):
        return cbs.slot(sel)
    try:
        return int(sel)
    except (TypeError, ValueError):
        return None


def infer_semantics(inputs, profile=None):
    """role -> layout entry, recovered from the *shape* of the vertex layout.

    Shipped builds often strip the vertex shader, so RenderDoc can only report
    its inputs as ``_input0``, ``_input1`` ... with no semantic name.  The roles
    the layout alone identifies are:

    * ``POSITION``      - three floats at the head of the first stream
    * ``NORMAL``        - whatever sits immediately behind position in that same
                          stream: the packed 10:10:10:2 word the vertex shader
                          expands (:func:`util.decode_packed_normal`),
                          or three plain floats
    * ``BLENDWEIGHTS``  - four normalised components in a per-vertex stream
    * ``BLENDINDICES``  - four integer components beside them, same stream
    * ``TEXCOORDn``     - the two-component floats, in stream order
    * ``TANGENT_SPACE`` - the four-component SNORM carrier of a tangent frame

    Everything else is deliberately *not* guessed: this layout holds several
    four-byte formats that are ambiguous, and a wrong guess exports wrong data
    instead of a mesh honestly missing a channel.

    A stride-0 stream is skipped throughout: that binding is the constant one
    the shader reads the same bytes from for every vertex (the ``cbuffer``
    stand-in some engines use), not per-vertex data.
    """
    used = [i for i in (inputs or []) if int(i.get("comps", 0)) > 0]
    if not used:
        return {}
    out = {}

    # POSITION
    cands = [i for i in used if i.get("comps") == 3 and _is_float(i)
             and int(i.get("off", 0)) == 0 and int(i.get("stride", 0)) > 0]
    if not cands:
        cands = [i for i in used if i.get("comps") == 3 and _is_float(i)]
    if not cands:
        return out
    pos = min(cands, key=_order)
    out["POSITION"] = pos

    # NORMAL - immediately behind position, same stream
    same = [i for i in used if i is not pos
            and int(i.get("slot", 0)) == int(pos.get("slot", 0))]
    behind = int(pos.get("off", 0)) + _size(pos)
    for want in (1, 3):
        hit = [i for i in same if int(i.get("off", 0)) == behind
               and i.get("comps") == want and _is_float(i)]
        if hit:
            out["NORMAL"] = min(hit, key=_order)
            break

    # BLENDWEIGHTS / BLENDINDICES - one per-vertex stream holding both a
    # four-component integer and a four-component normalised neighbour
    for slot in sorted(set(int(i.get("slot", 0)) for i in used)):
        if slot == int(pos.get("slot", 0)):
            continue
        grp = [i for i in used if int(i.get("slot", 0)) == slot]
        if not grp or max(int(i.get("stride", 0)) for i in grp) <= 0:
            continue
        idx = [i for i in grp if i.get("comps") == 4 and _is_uint(i)
               and int(i.get("cbyte", 4)) <= 4]
        wts = [i for i in grp if i.get("comps") == 4 and not _is_uint(i)]
        if idx and wts:
            out["BLENDWEIGHTS"] = min(wts, key=_order)
            out["BLENDINDICES"] = min(idx, key=_order)
            break

    # TEXCOORDn / TANGENT_SPACE - the remaining floats, in stream order
    claimed = set(id(v) for v in out.values())
    uvs, seen = [], set()
    ts = None
    for i in sorted(used, key=_order):
        if id(i) in claimed:
            continue
        key = (i.get("slot"), i.get("off"), i.get("fmt"))
        if i.get("comps") == 4 and "snorm" in _ctype(i):
            if ts is None and int(i.get("stride", 0)) > 0:
                ts = i
            continue
        if i.get("comps") != 2 or _is_uint(i):
            continue
        if key in seen:
            continue
        seen.add(key)
        uvs.append(i)
    if ts is not None:
        out["TANGENT_SPACE"] = ts
    for n, i in enumerate(uvs[:8]):
        out["TEXCOORD%d" % n] = i
    return out


def position_declaration(inputs):
    """(components, ctype) of the stream entry that carries position, or None.

    This is the *shape* of a draw's position stream, which is what tells two
    objects apart when an engine draws them through different pipeline states
    inside one render pass: all the parts of one character are submitted with one
    layout, and something else drawn between them carries its own.
    """
    hit = next((i for i in (inputs or [])
                if str(i.get("name", "")).upper() == "POSITION"), None)
    if hit is None:
        hit = infer_semantics(inputs).get("POSITION")
    if not hit:
        return None
    return (int(hit.get("comps", 0)), str(hit.get("ctype", "")))


def skin_attributes(inputs, profile=None):
    """(weights, indices) for this draw - by semantic name, else by layout shape.

    Returns ``(None, None)`` when the draw carries no usable skin stream, which
    is the normal case for rigid parts (weapons, attachments) that are drawn in
    the same pass.
    """
    amap = dict((k.upper(), str(v).upper())
                for k, v in (getattr(profile, "attribute_map", None) or {}).items() if v)

    def find(name):
        want = amap.get(name.upper(), name).upper()
        return next((i for i in inputs or []
                     if str(i.get("name", "")).upper() == want), None)

    w, ix = find("BLENDWEIGHTS"), find("BLENDINDICES")
    if w is not None and ix is not None:
        return w, ix
    inf = infer_semantics(inputs, profile)
    return inf.get("BLENDWEIGHTS"), inf.get("BLENDINDICES")


class Adapter:
    """The built-in rules - the solver the tool was first fitted on: 终末地.

    Subclass and override what differs.  The values are the ones that were found
    to work on the captures this tool was developed against; they are *not* a
    statement about one particular game.  Any engine that puts the palette base
    in a per-instance constant-buffer record and the view-projection in four
    consecutive rows fits them, and `profile.discover` widens the search when it
    does not.
    """

    name = "endfield"
    label = "终末地"
    description = ("终末地: palette base from a per-instance cb record "
                   "(cb2[inst*16+5]), camera from cb0[32..35]")

    #: How the four float4s of the view-projection block are laid out.  The
    #: built-in engines store the *columns*, which is why the four rows below
    #: have to be gathered one component from each; an engine whose shader reads
    #: them with `dp4 oPos.x, v, cb[i]` stores the rows instead, and then the
    #: four float4s are already the matrix.
    vp_layout = "column_major"

    # ------------------------------------------------------------- camera
    def camera(self, cb0: bytes, profile, res=None):
        """Recover the camera from the view-projection block.

        The shader computes clip.k = cb0[32].k*wx + ... + cb0[35].k, so the rows
        of the world->clip matrix are the *columns* of that constant-buffer block.
        With P0/P1/P3 the x/y/w rows:

            b = -P3.xyz                       (backward axis)
            VP0.xyz = fx*r - cx*b   ->  cx = -VP0.xyz . b,  fx = sqrt(|VP0|^2-cx^2)
            P3.w = b.C ,  VP0.w = -fx*(r.C) + cx*(b.C) ,  VP1.w = -fy*(u.C) + cy*(b.C)

        which pins the camera position C too - no assumption that the camera sits
        at the world origin.
        """
        def f4(i):
            return list(struct.unpack_from("<4f", cb0, i * 16))

        vi = list(profile.vp_rows["indices"])
        A0, A1, A2, A3 = f4(vi[0]), f4(vi[1]), f4(vi[2]), f4(vi[3])
        P = ([[c for c in A0], [c for c in A1], [c for c in A2], [c for c in A3]]
             if self.vp_layout == "row_major" else
             [[A0[k], A1[k], A2[k], A3[k]] for k in range(4)])
        P0, P1, P3 = P[0], P[1], P[3]

        b = unit3([-c for c in P3[:3]])
        cx = -sum(P0[k] * b[k] for k in range(3))
        cy = -sum(P1[k] * b[k] for k in range(3))
        fx = math.sqrt(max(0.0, sum(c * c for c in P0[:3]) - cx * cx))
        fy = math.sqrt(max(0.0, sum(c * c for c in P1[:3]) - cy * cy))
        r = unit3([P0[k] + cx * b[k] for k in range(3)])
        u = unit3([P1[k] + cy * b[k] for k in range(3)])

        bc = P3[3]
        rc = (cx * bc - P0[3]) / fx if fx else 0.0
        uc = (cy * bc - P1[3]) / fy if fy else 0.0
        C = [rc * r[k] + uc * u[k] + bc * b[k] for k in range(3)]

        rw, rh = (res or [0, 0])[:2]
        aspect = (float(rw) / float(rh)) if (rw and rh) else None
        return {
            "location": C,
            "basis": {"x": r, "y": u, "z": b},
            "fx": fx, "fy": fy, "cx": cx, "cy": cy,
            "lens_mm": 36.0 * fx / 2.0,
            "sensor_width_mm": 36.0,
            "pixel_aspect_y": (aspect * fx / fy) if (aspect and fy) else 1.0,
            "shift_x": -cx / 2.0,
            "shift_y": cy / 2.0,
            "res": [int(rw), int(rh)] if (rw and rh) else None,
            "vp": P,
            "adapter": self.name,
        }

    def camera_view(self, cbs, profile, meta=None):
        """One draw's camera, from every constant buffer the draw binds.

        `camera` reads a single block; *which* block is the profile's business,
        and the answer is an index for the built-in engines and a block name for
        an engine that declares its constant pool on a different slot every
        draw.  A subclass overrides this when the block has to be searched for,
        or when something inside it can confirm the reading.
        """
        res = list(meta.get("viewport") or [0, 0, 0, 0])[2:4] if meta else None
        return self.camera(cbs.get(profile.vp_rows.get("cb", 0), b""), profile,
                           res=res)

    def keep_draw(self, draw, family, profile):
        """Whether a draw found in the character's event range belongs to it.

        The selection expands from the skinned parts to every draw the same pass
        issued between the first and the last of them, because the rigid pieces of
        a character - a weapon, a tassel - carry no skin stream of their own and
        would otherwise be missed.  That range also holds whatever else the engine
        drew in between, and this is where an engine gets to say how to tell them
        apart: `family` is the position declaration the skinned parts share.  The
        base rule keeps everything, which is what this tool has always exported.
        """
        return True

    def check_camera(self, cam):
        """Sanity check that the block really looks like a perspective projection."""
        P = cam["vp"]
        nw, nx, ny = norm3(P[3][:3]), norm3(P[0][:3]), norm3(P[1][:3])
        if not (0.5 < nw < 1.5):
            return False, "w row length %.4f is not 1 (not a view axis)" % nw
        if nx < 0.05 or ny < 0.05:
            return False, "focal rows are degenerate (|x|=%.4f |y|=%.4f)" % (nx, ny)
        if abs(sum(P[0][k] * P[3][k] for k in range(3))) / (nx * nw) > 0.2:
            return False, "the x row and the w row are not orthogonal"
        # The w row's constant is the camera's own reach along its backward axis,
        # so it is bounded by how far the camera sits from the world origin - and
        # a game that works in millimetres legitimately carries a constant in the
        # tens of thousands.  The cut-off therefore scales with the camera the
        # block itself implies rather than being one number for every engine.
        reach = max(abs(v) for v in cam["location"])
        if abs(P[3][3]) > 1e4 + 2.0 * reach:
            return False, "w row constant %.3g is implausible" % P[3][3]
        return True, ""

    # ------------------------------------------------------------ palette
    def palette_candidates(self, profile, cbs: dict, bone: bytes, exhaustive: bool,
                           log=None):
        """Ordered (label, base_float4) palette candidates."""
        out, seen = [], set()

        def add(label, base):
            if base is None or base < 0 or base in seen:
                return
            seen.add(base)
            out.append((label, int(base)))

        offsets = [int(profile.palette_header_offset)]
        if exhaustive:
            offsets = list(dict.fromkeys(
                offsets + list(profile.discover.get("header_offsets", [0, 3]))))
        # Which constant buffer holds the per-instance record differs between
        # engines - the profile names the one this tool was fitted on, and the
        # same record shape is then tried in every other buffer the draw binds.
        # Reading one u32 out of eight buffers costs nothing next to a residual
        # that decides anyway, and a capture whose record sits elsewhere still
        # gets a correct palette out of the cheap pass.
        named = _cb_slot(cbs, profile.palette_base[0]["cb"])
        slots = [named] if named is not None else []
        if not exhaustive or profile.discover.get("scan_cbuffer_slots", True):
            slots += [s for s in sorted(cbs) if s not in slots]
        n4 = len(bone) // 16
        priors = []
        for slot in slots:
            for spec in profile.palette_base:
                v = profile.record_u32(cbs, slot, spec["stride"], spec["index"],
                                       spec["component"])
                if v is not None and 0 < v < n4:
                    priors.append((slot, spec, v))
        for slot, spec, v in priors:
            sel = spec["cb"] if isinstance(spec["cb"], str) else "cb%d" % slot
            for off in offsets:
                add("%s[%d].%s+%d" % (sel, spec["index"], spec["component"], off),
                    off + v)
        if not exhaustive:
            return out
        if profile.discover.get("swap_palettes") and len(out) > 1:
            out = out[1:] + out[:1]
        if profile.discover.get("scan_cbuffer_values"):
            for label, base in self._cb_record_candidates(profile, cbs, len(bone)):
                add(label, base)
        if profile.discover.get("scan_matrix_runs"):
            for start in self.matrix_runs(bone):
                add("matrix-run@%d" % start, start)
        if log:
            log.info("palette candidates", n=len(out))
        return out

    def _cb_record_candidates(self, profile, cbs, bone_len):
        out = []
        spec = profile.palette_base[0]
        cb, stride = _cb_slot(cbs, spec["cb"]), int(spec["stride"])
        raw = cbs.get(cb) if cb is not None else None
        if raw is None:
            return out
        n4 = bone_len // 16
        for lane in range(4):
            for k in range(stride):
                off = k * 16 + lane * 4
                if off + 4 > len(raw):
                    break
                v = struct.unpack_from("<I", raw, off)[0]
                if 0 < v < n4:
                    for h in profile.discover.get("header_offsets", [0, 3]):
                        out.append(("scan cb%d[%d].%d+%d" % (cb, k, lane, h), h + v))
        return out

    def matrix_runs(self, bone: bytes, limit=64, min_len=8):
        """Starts of runs of well formed rigid 3x4 blocks - palette candidates."""
        n4 = len(bone) // 16
        good = bytearray(n4)
        for i in range(n4 - 3):
            a = struct.unpack_from("<4f", bone, i * 16)
            b = struct.unpack_from("<4f", bone, (i + 1) * 16)
            c = struct.unpack_from("<4f", bone, (i + 2) * 16)
            if (abs(norm3(a[:3]) - 1) > 0.02 or abs(norm3(b[:3]) - 1) > 0.02
                    or abs(norm3(c[:3]) - 1) > 0.02):
                continue
            if (abs(sum(a[k] * b[k] for k in range(3))) > 0.02
                    or abs(sum(a[k] * c[k] for k in range(3))) > 0.02
                    or abs(sum(b[k] * c[k] for k in range(3))) > 0.02):
                continue
            good[i] = 1
        runs, i = [], 0
        while i < n4 - 3:
            if good[i]:
                j = i
                while j < n4 - 3 and good[j]:
                    j += 1
                if j - i >= min_len:
                    runs.append((j - i, i))
                i = j
            else:
                i += 1
        runs.sort(reverse=True)
        return [start for _, start in runs[:limit]]

    def skin_hypothesis(self, flag, profile):
        """True when this draw uses the skinned path rather than a rigid one."""
        if flag is None:
            return True
        spec = profile.skin_flag
        return ((flag & int(spec["mask"])) != 0
                and (flag & int(spec["clear_mask"])) != 0)

    # -------------------------------------------------------------- model
    def model_transform(self, sol, profile):
        """Model = VP^-1 . A.

        The solver fitted A: model -> clip.  Composing with the inverse
        view-projection gives the object's own transform, whatever produced it -
        including parts whose object matrix does not come from the per-draw
        constant buffer at all.
        """
        from .util import inv4, matmul4
        return matmul4(inv4(sol["vp"]), sol["A"])

    # --------------------------------------------------------- attributes
    #: A semantic name that carries texture coordinates.  `TEXCOORD` on its own
    #: is a real spelling - Unity's shaders declare `TEXCOORD` with no index when
    #: there is only one - and looking only for `TEXCOORD0..7` silently found no
    #: UV set at all on every draw that used it, which is why the scene geometry
    #: came out with a UV layer of nothing but zeroes.
    _TEXCOORD_RE = re.compile(r"^TEXCOORD(\d*)$", re.I)

    def _texcoord_inputs(self, inputs):
        """Every TEXCOORD input, in the order its own name says.

        A bare `TEXCOORD` counts as set 0.  Inputs RenderDoc gave no name are
        left out here - they are recovered from the layout shape instead, and
        that path numbers them itself.
        """
        out = []
        for i, inp in enumerate(inputs or []):
            m = self._TEXCOORD_RE.match(str(inp.get("name", "")).strip())
            if not m:
                continue
            out.append((int(m.group(1)) if m.group(1) else 0, i, inp))
        out.sort(key=lambda t: (t[0], t[1]))
        return [inp for _n, _i, inp in out]

    def classify_attributes(self, inputs, profile=None):
        """Split the declared layout into UV sets, extra streams and tangents.

        The test is what the shader does with the stream, not its semantic name:
        a 3-component TEXCOORD is a position carrier, a 4-component SNORM one is a
        tangent-space direction.  When the capture reports no names at all -
        every input is ``_inputN`` - the roles are recovered from the layout
        shape instead (:func:`infer_semantics`); a capture with real semantics is
        never affected.
        """
        inputs = inputs or []
        amap = dict((k.upper(), str(v).upper())
                    for k, v in (getattr(profile, "attribute_map", None) or {}).items() if v)

        def find(name):
            want = amap.get(name.upper(), name).upper()
            return next((i for i in inputs
                         if str(i.get("name", "")).upper() == want), None)

        anonymous = is_anonymous(inputs)
        inf = infer_semantics(inputs, profile) if anonymous else {}

        uvs, seen = [], set()
        alt = None
        packed_ts = None
        cands = self._texcoord_inputs(inputs)
        if anonymous:
            cands += [inf["TEXCOORD%d" % k] for k in range(8)
                      if inf.get("TEXCOORD%d" % k)]
        for a in cands:
            if not a or a.get("stride", 0) <= 0:
                continue
            key = (a["slot"], a["off"], a["fmt"])
            ct = a["ctype"].lower()
            name = a.get("name") or "_input"
            comps = int(a.get("comps", 0))
            if comps == 3:
                # three components is a position carrier, whatever it is called
                if alt is None and key not in seen:
                    alt = a
                continue
            if comps == 4 and "snorm" in ct:
                packed_ts = packed_ts or a
                continue
            if comps == 4 and ("float" in ct or "norm" in ct):
                # Four plain floats under a TEXCOORD name is a `float4` uv - the
                # first two are the coordinates, the rest is whatever else the
                # shader wanted to carry alongside them.  Reading them as "not a
                # UV" is what left effect meshes with an empty uv layer.
                comps = 2
            if comps == 2 and "uint" not in ct and "sint" not in ct:
                if key not in seen:
                    seen.add(key)
                    uvs.append((name, a))
        if anonymous and packed_ts is None:
            packed_ts = inf.get("TANGENT_SPACE")
        nrm = find("NORMAL") or inf.get("NORMAL")
        tan = find("TANGENT")
        tan_real = bool(tan) and tan.get("stride", 0) > 0
        return {"uvs": uvs, "alt": alt, "packed_ts": packed_ts, "normal": nrm,
                "tangent": tan if tan_real else None,
                "tangent_constant": bool(tan) and not tan_real}

    def decode_normal(self, raw, off, spec, packing="auto"):
        """Return (normal, handedness) for one vertex.

        `packing` mirrors the export dialog: auto/xyz10 decode the 10:10:10:2
        octahedral word, raw_float reads three floats, none yields no normal.
        """
        if packing == "none":
            return None, 1.0
        if packing == "raw_float" or (packing == "auto" and spec["comps"] >= 3):
            v = read_comps(raw, off, spec)
            n = norm3(v[:3]) or 1.0
            return (v[0] / n, v[1] / n, v[2] / n), 1.0
        if spec["comps"] < 3:
            return decode_packed_normal(raw, off)
        v = read_comps(raw, off, spec)
        n = norm3(v[:3]) or 1.0
        return (v[0] / n, v[1] / n, v[2] / n), 1.0


class GenericAdapter(Adapter):
    """Same rules, but always willing to fall back to the residual search."""

    name = "generic"
    label = "通用"
    description = "unknown engine: find the palette by scanning and score with the residual"

    def palette_candidates(self, profile, cbs, bone, exhaustive, log=None):
        return Adapter.palette_candidates(self, profile, cbs, bone, True, log)


ADAPTERS = {}
ADAPTER_LABELS = {}
ADAPTER_DESCRIPTIONS = {}


def _bases():
    """What a pack's `solver.py` is handed before it runs.

    Handed rather than imported: the package is called `rdc2blend` on one machine
    and `rdc2blenderGUI` on the next (the name is read off the folder), so a pack
    that imported this module by name would stop loading the moment somebody
    renamed the folder.
    """
    return {
        "Adapter": Adapter,
        "GenericAdapter": GenericAdapter,
        "position_declaration": position_declaration,
        "infer_semantics": infer_semantics,
        "skin_attributes": skin_attributes,
        "cb_slot": _cb_slot,
        "BUFFER_DESCRIPTORS": BUFFER_DESCRIPTORS,
    }


def _load_solvers():
    """Every solver pack under `solvers/`, as name -> class.

    `endfield` and `generic` are always here: the first is the built-in rules,
    which a pack may replace but not remove, and the second is what an engine
    nobody has written rules for falls back to.  A pack that will not load is a
    pack that is not offered, rather than an import error that takes the whole
    tool down with it - the point of the folder is that a half-finished solver
    can sit in it without breaking anyone else's run.
    """
    try:
        from . import solverpack
    except Exception:
        solverpack = None
    reg = {Adapter.name: Adapter, GenericAdapter.name: GenericAdapter}
    labels = dict((c.name, c.label) for c in (Adapter, GenericAdapter))
    descs = dict((c.name, c.description) for c in (Adapter, GenericAdapter))
    if solverpack is None:
        return reg, labels, descs
    bases = _bases()
    base_by_name = {"Adapter": Adapter, "GenericAdapter": GenericAdapter}
    for pack in solverpack.pack_names():
        try:
            table = solverpack.read_table(pack)
            cls = solverpack.load_solver_class(pack, bases)
            if cls is None or not isinstance(cls, type):
                cls = base_by_name.get(str(table.get("base") or "Adapter"), Adapter)
            if cls in (Adapter, GenericAdapter):
                # A table-only pack gets a class of its own rather than the base
                # itself: two packs must never share one class object, or the
                # label one of them sets lands on the other as well.
                cls = type(str(pack).title().replace("_", "") + "Solver", (cls,), {})
            cls.name = str(table.get("name") or pack)
            cls.label = str(table.get("label") or pack)
            cls.description = str(table.get("description") or "")
            reg[cls.name] = cls
            labels[cls.name] = cls.label
            descs[cls.name] = cls.description
        except Exception:
            continue
    return reg, labels, descs


ADAPTERS, ADAPTER_LABELS, ADAPTER_DESCRIPTIONS = _load_solvers()

# Other spellings of a solver's name.
#
# The built-in solver answers to `default` as well as `endfield`: it is the
# profile a build without one falls back to, older profiles and remembered
# settings call it that, and renaming a solver must not invalidate them.  The
# display names are accepted too, so a front end can offer 终末地 / 逆水寒 and
# hand whatever the user picked straight back to `resolve_adapter_name`.
ADAPTER_ALIASES = {
    "builtin": Adapter.name,
    "auto": Adapter.name,
    "default": Adapter.name,
    # The built-in solver was called `tifeng` before it was called `endfield`,
    # and that name is written into every profile saved before the rename.  It is
    # not decoration: without it a remembered `.json` that says
    # `"adapter": "tifeng"` cannot start a run at all.
    "tifeng": Adapter.name,
    # an engine we have no rules for: the scanning adapter, which never trusts
    # the profile's hint and scores every candidate by the residual
    "unknown": GenericAdapter.name,
    "none": GenericAdapter.name,
    "nsh": "nishuihan",
}
ADAPTER_ALIASES.update((str(label).lower(), name)
                       for name, label in ADAPTER_LABELS.items())


def resolve_adapter_name(name) -> str:
    """Canonical adapter name for `name`, or the built-in one when unset.

    A trailing `.json` is dropped first: the two front ends offer a solver by
    name and a profile by file, and a caller who has just typed
    `--profile nishuihan.json` will reasonably try `--adapter nishuihan.json` too.
    """
    key = str(name or "").strip().lower()
    if not key:
        return Adapter.name
    if key.endswith(".json"):
        key = key[:-5]
    if key in ADAPTERS:
        return key
    return ADAPTER_ALIASES.get(key, key)


def solver_label(name) -> str:
    """The solver's display name - 终末地, 逆水寒 - for a menu or a log line."""
    key = resolve_adapter_name(name)
    return ADAPTER_LABELS.get(key) or str(name or "")


def solver_choices() -> list:
    """Every solver, as the strings a picker should show, best known first.

    The built-in one leads, then the packs in the order they ship, then whatever
    else is registered - so the list a person sees is the folder listing under
    `solvers/`, and dropping a pack in adds it to the menu with no code change.
    """
    from . import solverpack
    order = [Adapter.name] + [n for n in solverpack.pack_names()]
    order += [GenericAdapter.name]
    seen, out = set(), []
    for n in order + sorted(ADAPTERS):
        if n in seen or n not in ADAPTERS:
            continue
        seen.add(n)
        out.append(solver_label(n))
    return out


def solver_key(choice) -> str:
    """Back from what a picker showed to the name a profile records."""
    return resolve_adapter_name(choice)


def get_adapter(profile):
    name = getattr(profile, "adapter", None) or Adapter.name
    name = resolve_adapter_name(name)
    cls = ADAPTERS.get(name)
    if cls is None:
        raise RuntimeError("unknown adapter %r; available: %s"
                           % (name, ", ".join(sorted(ADAPTERS))))
    return cls()
