# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.

"""Per-engine profile: every constant that is not derivable from the capture.

The defaults below are the values this tool was fitted against - a UE-style
renderer that keeps the bone palette in a per-instance constant-buffer record
and the view-projection in four consecutive rows.  A capture from a different
engine gets its own JSON file (`rdc2blend profile --write mygame.json`, then
`--profile mygame.json`).  Nothing in the rest of the tool hard-codes these
values.

Where a value can be discovered at run time the field is documented as such and
`auto` blocks control the fallback search.
"""

import copy
import json
import os
from typing import Optional

from .util import load_json, save_json


class Struct(object):
    """Named fields with defaults - the small part of `dataclasses` we used.

    Spelled out by hand because this module is imported *inside* qrenderdoc, by
    whatever Python that build embeds: `dataclasses` only exists from 3.7, and
    an install carrying 3.6 would otherwise fail to start before doing anything
    at all.  `_FIELDS` is (name, default); a default that is a list or a dict is
    copied per instance so two profiles never share one.
    """

    _FIELDS = ()

    def __init__(self, **kw):
        for name, default in self._FIELDS:
            setattr(self, name, copy.deepcopy(default)
                    if isinstance(default, (list, dict)) else default)
        for name, value in kw.items():
            if not hasattr(self, name):
                raise TypeError("%s has no field %r" % (type(self).__name__, name))
            setattr(self, name, value)

    def to_dict(self):
        out = {}
        for name, _ in self._FIELDS:
            v = getattr(self, name)
            out[name] = copy.deepcopy(v) if isinstance(v, (list, dict)) else v
        return out


class CBView(dict):
    """Dumped constant buffers, addressable by slot *or* by the shader's name.

    `cbN.bin` is named after the binding RenderDoc enumerates, and an engine that
    hands one constant pool out to several slots in whatever order a shader
    declares them puts the same block on a different N from draw to draw.  The
    block's own name is what stays put, so a profile may say either
    `{"cb": 2}` (the built-in engines) or `{"cb": "PerCanvasStep"}`.  `probe`
    records the name next to each dump; the map below is what turns one into the
    other.
    """

    def __init__(self, raw=None, names=None):
        dict.__init__(self, raw or {})
        self.names = dict(names or {})

    def slot(self, sel):
        """The dumped slot a selector means, or None when it names nothing."""
        if isinstance(sel, str):
            sel = self.names.get(sel, sel)
            try:
                return int(sel)
            except (TypeError, ValueError):
                return None
        return int(sel)

    def get(self, sel, default=None):
        s = self.slot(sel)
        return dict.get(self, s, default) if s is not None else default

    def __contains__(self, sel):
        s = self.slot(sel)
        return s is not None and dict.__contains__(self, s)


def cb_names(cbuffers: dict) -> dict:
    """{block name: dumped slot} from a probe's `cbuffers` record."""
    out = {}
    for slot, info in (cbuffers or {}).items():
        try:
            name = str((info or {}).get("name") or "")
        except Exception:
            continue
        if name:
            out[name] = slot
    return out


def cb_slot(cbuffers: dict, sel, default=None):
    """Which dumped cb a profile selector names - by index or by block name."""
    if not isinstance(sel, str):
        return str(int(sel))
    return cb_names(cbuffers).get(sel, default)


class Record(Struct):
    """A per-draw constant-buffer record: cb[instance * stride + index]."""
    _FIELDS = (
        ("cb", 2),                     # constant buffer slot
        ("stride", 16),                # float4 per instance record
        ("index", 0),                  # float4 index inside the record
        ("component", "x"),            # which lane carries the value
    )


class Profile(Struct):
    _FIELDS = (
        ("name", "default"),
        ("notes", "built-in defaults (UE-style palette + view-projection rows)"),
        # which Adapter implements this engine's palette / camera / attribute rules:
        # "endfield" (终末地, the built-in rules) or "nishuihan" (逆水寒)
        ("adapter", "endfield"),

        # ---- bone palette location ---------------------------------------------
        # base_float4 = header_offset + u32(cb[base.cb][inst*base.stride+base.index].<lane>)
        ("palette_base", [
            {"cb": 2, "stride": 16, "index": 5, "component": "x"},
            {"cb": 2, "stride": 16, "index": 5, "component": "y"},
        ]),
        ("palette_header_offset", 3),
        ("bone_stride_f4", 3),        # float4 per bone matrix (3 rows)

        # palette A is used when cb[.. index].component < less_than, else palette B
        ("palette_select", {
            "cb": 2, "stride": 16, "index": 10, "component": "x", "less_than": 1.0,
        }),

        # skinning is used when (flag & mask) != 0 and (flag & clear_mask) != 0
        ("skin_flag", {
            "cb": 2, "stride": 16, "index": 4, "component": "w",
            "mask": 32, "clear_mask": 0xFFFFFFCF,
        }),

        # object -> world: rows taken from the same per-draw record
        ("model_rows", [0, 1, 2]),
        ("model_translation", 3),
        # world = model*object + (object_translation - cb[origin.cb][origin.index].xyz)
        ("origin_rebase", {"cb": 0, "index": 44}),

        # ---- camera / projection -----------------------------------------------
        ("view_rows", {"cb": 0, "indices": [4, 5, 6, 7]}),
        ("vp_rows", {"cb": 0, "indices": [32, 33, 34, 35]}),
        ("fx", {"cb": 0, "index": 8, "component": "x"}),
        ("fy", {"cb": 0, "index": 9, "component": "y", "negate": True}),
        ("near", {"cb": 0, "index": 11, "component": "z"}),
        ("reverse_z_infinite", True),      # z_ndc = near / depth

        # ---- mesh data shaping --------------------------------------------------
        # "auto" | "xyz10" (10:10:10:2 octahedral) | "raw_float" | "none"
        ("normal_packing", "auto"),
        # how the skinning shader reads the four weights, which is what the dump
        # has to hand the solver: "renormalize" (scale all four to sum to one -
        # the safe default for a plain four-weight dot) or "remainder" (keep the
        # first three as stored and compute the fourth as 1 - their sum, for a
        # shader that ignores the stored fourth weight)
        ("skin_weight", "renormalize"),
        # role -> attribute name override, e.g. {"NORMAL": "TEXCOORD3"}
        ("attribute_map", {}),

        # ---- geometry -----------------------------------------------------------
        # Both feed `util.frame_matrix`, which is the frame every writer goes
        # through: the meshes, the camera in the .blend, the FBX.
        #
        # The built-in engine is Unity, so the world is Y-up and the turn into
        # Blender is `(x, y, z) -> (x, -z, y)`.  That is a proper rotation, which
        # is why `left_handed` is *off*: the handedness difference between the
        # two worlds shows up in which way each calls "forward" (+Z against -Y),
        # not in a mirror.  Turning the Y mirror on as well would mirror the
        # model and stand it on its head - and the silhouette check cannot see
        # either, because it renders with the very camera it grades.
        ("left_handed", False),    # mirror one axis on the way into Blender
        ("up_axis", "y"),          # world up: "z" | "y" | "x"

        # Unity flips the projection's Y when it renders into a render *texture*
        # rather than the backbuffer - it is what makes the texture sample the
        # right way up later.  A character pass renders into an RT, so the
        # view-projection this tool recovers has that flip baked into it: rebuild
        # the camera from it naively and the frame comes out upside down, while
        # the captured target is stored bottom-up to match.  The two agree with
        # each other, which is why the silhouette check cannot see it - it renders
        # with the very camera it grades - and why this is a setting rather than
        # something to be discovered from the numbers.
        ("flip_camera_y", True),

        # ... and the flip is not a property of the capture, it is a property of
        # *where in the frame you are*: a game renders the scene into a texture
        # (flipped), then composites to the backbuffer (not), so there is one
        # event id at which the convention changes and it is different for every
        # game and every frame.  Set this to that event id and everything below
        # it is mirrored, everything at and above it is not - camera, depth
        # target and colour targets alike, decided per draw rather than once for
        # the run.  Left null, `flip_camera_y` above answers for the whole
        # capture, which is right when the run only touches one side of the
        # change.
        ("flip_y_before_eid", None),

        # ... and the *targets* the capture left behind are a third question.
        # `flip_camera_y` above says the engine's projection is Y-mirrored, and
        # that is undone on the camera.  A game whose world this tool has to
        # mirror on the way into Blender (`left_handed`) ends up needing the
        # opposite treatment for the pictures: the reconstructed view and the
        # stored target are then the same way up as each other, and flipping the
        # target would break the very comparison that is meant to check the view.
        # Which way up a capture's targets are stored is a fact about the engine
        # and cannot be derived from the world frame - measured on 逆水寒, the two
        # do come apart - so it is stated.  `null` follows `flip_at`, which is
        # what every solver did before this key existed.
        ("capture_flip_y", None),

        # Blender units per game world unit.  1.0 exports the capture's own
        # numbers, which is what a game authored in metres wants; one authored in
        # centimetres wants 0.01, and then a 3 m creature measures 3 units in
        # Blender instead of 300.  Unlike the two settings above this is a scale,
        # not a frame: it is applied to positions on their way out of the game
        # frame (solve.place_world) and to the camera with them, so the recovered
        # view is unchanged - only the numbers in Blender's transform panel are.
        # Directions are renormalised after the frame change, so they are untouched.
        ("unit_scale", 1.0),

        # ---- what to export ------------------------------------------------------
        # Four kinds of mesh, and the rules that decide which draw call is which
        # - see mesh_kinds.py.  The four booleans are this run's answer to "what
        # do I want out of the capture"; the rest are the thresholds.  They live
        # here rather than on the command line because the head-less driver only
        # ever sees the profile, and it is the driver that decides which draws are
        # worth dumping - so the choice has to reach it.
        ("mesh_kinds", {
            "skinned": True,          # the character, solved through its palette
            "static": True,           # opaque scene geometry
            "fx": True,               # the depth-write-off pass: effects
            "ui": False,              # the interface, after the frame is composited
            "ui_from_eid": None,      # defaults to `flip_y_before_eid`
            "ui_gets_scene_geometry": False,
            "static_min_vertices": 6,      # "more than": a quad is not scene geometry
            "static_min_triangles": 2,
            "fx_depth_write_ratio": 0.75,  # of a pass's draws, this many write no depth
            "fx_min_draws": 1,
            "fx_exempt_character_pass": True,
            "max_parts": {"skinned": 64, "static": 4096, "fx": 4096, "ui": 512},
            "require_normal": {"skinned": True, "static": False, "fx": False,
                               "ui": False},
            # How far the fit may miss before a part is left out.  The character
            # is judged by `verify.accept_pose_rms` (null means "use that"), which
            # is the skinning fit's own error bar.  The other two are fitted
            # rigidly, and a good rigid fit lands at ~1e-7 - so the threshold is
            # really a filter for geometry the vertex buffer does not describe at
            # all: a billboard, a ribbon or a particle quad is expanded by the
            # shader from a handful of corner ids, and the mesh that comes back
            # out is a degenerate card in the wrong place.  Exporting one is worse
            # than leaving it out, and the run says how many it left out.
            "accept_rms": {"skinned": None, "static": 0.001, "fx": 0.001,
                           "ui": None},
        }),

        # ---- where the world sits in Blender -------------------------------------
        # On by default: every object carries the world matrix the solve recovered
        # for it and the geometry stays in model space, so the scene is *built*
        # from world matrices and the camera is then one more object placed by the
        # same one - rather than the camera being the thing everything else is
        # expressed relative to.  That matters because the game rebases its world
        # onto the camera (`- cb0[44]`), so in the capture's own coordinates the
        # camera sits at the origin by construction - which is the whole reason
        # the objects, and not the camera, are what the scene is built from.
        #
        # `fit` is where Blender's origin goes *in the .blend*, and it defaults to
        # keeping the capture's own coordinates: the scene is the reconstructed
        # world, and the character stands where the world puts it.  "character"
        # moves the origin onto the character instead (every part of one
        # character shares a world transform, so its translation is the
        # character's position), and "all" centres the whole export's bounding
        # box.  All three move the camera by the same amount, so the view is
        # untouched and only the numbers in the transform panel change.
        #
        # The .fbx files are a separate question and have their own answer in
        # `fbx` below, because a single part opened on its own usually wants its
        # own origin rather than the scene's.
        ("scene", {
            "object_transforms": True,
            "fit": "keep",            # keep | character | all
            "offset": [0.0, 0.0, 0.0],     # extra Blender-space translation
            "matrix": None,                # explicit world -> scene 4x4, or null
            "fbx": "local",           # local | world - see `emit.emit_fbx`
        }),

        # ---- discovery fallbacks ------------------------------------------------
        ("discover", {
            # when the profile rule fails, also try these before giving up
            "header_offsets": [0, 3],
            "swap_palettes": True,
            "scan_cbuffer_values": True,   # every u32 in the record as a candidate base
            "scan_bone_stride": [3, 4],
            "scan_matrix_runs": True,      # runs of orthonormal 3x4 in the bone buffer
            "max_align_delta": 600,        # post-VS vs vertex buffer offset search
        }),

        # ---- character selection ------------------------------------------------
        ("select", {
            "min_bone_buffer_bytes": 262144,
            "require_skin_attributes": True,
            "group_by": ["depth_target", "viewport"],
            "max_parts": 64,
        }),

        # ---- verification -------------------------------------------------------
        ("verify", {
            "min_iou": 0.95,
            "accept_pose_rms": 1.0e-3,
            "reference_eid": "last",   # depth is captured at the last draw of the pass
        }),
    )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def load(path: Optional[str]) -> "Profile":
        p = Profile()
        if path:
            data = load_json(path)
            if not data:
                raise RuntimeError("profile not found or empty: %s" % path)
            p.merge(data)
        return p

    def merge(self, data: dict) -> None:
        for k, v in (data or {}).items():
            if k.startswith("_"):
                continue
            if not hasattr(self, k):
                continue
            cur = getattr(self, k)
            if isinstance(cur, dict) and isinstance(v, dict):
                merged = copy.deepcopy(cur)
                merged.update(v)
                setattr(self, k, merged)
            else:
                setattr(self, k, v)

    def save(self, path: str) -> None:
        save_json(path, self.to_dict())

    # field accessors used by the solver -------------------------------------
    def cb_lane(self, raw_cbs: dict, spec: dict, default=None):
        """Read one lane out of a dumped constant buffer.

        `raw_cbs` maps cb slot -> raw bytes; `spec` is e.g. {"cb":0,"index":8,
        "component":"x"}.  Returns None when the slot is missing.
        """
        raw = raw_cbs.get(spec["cb"])
        if raw is None:
            return default
        off = int(spec["index"]) * 16 + "xyzw".index(spec["component"]) * 4
        if off + 4 > len(raw):
            return default
        import struct
        v = struct.unpack_from("<f", raw, off)[0]
        if spec.get("negate"):
            v = -v
        return v

    def cb_u32(self, raw_cbs: dict, spec: dict, default=None):
        raw = raw_cbs.get(spec["cb"])
        if raw is None:
            return default
        off = int(spec["index"]) * 16 + "xyzw".index(spec["component"]) * 4
        if off + 4 > len(raw):
            return default
        import struct
        return struct.unpack_from("<I", raw, off)[0]

    def record_u32(self, raw_cbs: dict, cb, stride: int, index: int, lane: str,
                   inst: int = 0):
        raw = raw_cbs.get(cb)
        if raw is None:
            return None
        off = (inst * int(stride) + int(index)) * 16 + "xyzw".index(lane) * 4
        if off + 4 > len(raw):
            return None
        import struct
        return struct.unpack_from("<I", raw, off)[0]


def default_profile_path() -> str:
    """The profile used when --profile is not given, or "" for none.

    Resolved through paths.py so an install can drop in its own default without
    editing code; a bare checkout picks up profiles/default.json.
    """
    from . import paths
    return paths.default_profile_path()


def resolve_profile_path(name: Optional[str]) -> Optional[str]:
    """Turn what the user typed into a file, or return it unchanged.

    `--profile nishuihan` means that solver's own table - `solvers/nishuihan/
    solver.json` - and a user's override in `profiles/` of the same name wins
    over it, because that is the one they wrote.  A path that already exists -
    absolute, relative, anything - is left alone, so nothing that worked before
    resolves differently now.

    A name that is another spelling of the *built-in* solver falls back to the
    shipped table: that solver answers to `endfield`, `tifeng`, `default` and
    `builtin`, and `--profile tifeng` has to keep working for a caller who learnt
    the tool under the older name.
    """
    if not name or os.path.exists(name):
        return name
    from . import paths
    stem = name[:-5] if name.lower().endswith(".json") else name
    for cand in (os.path.join(paths.PROFILES_DIR, stem + ".json"),
                 os.path.join(paths.PACKAGE_DIR, "solvers", stem, "solver.json")):
        if os.path.exists(cand):
            return cand
    try:
        from .adapters import Adapter, resolve_adapter_name
        if resolve_adapter_name(stem) == Adapter.name:
            d = paths.default_profile_path()
            if d:
                return d
    except Exception:
        pass
    return name


def load_profile(path: Optional[str]) -> Profile:
    """Load the named profile, falling back to the built-in defaults."""
    if path is None:
        path = default_profile_path() or None
    else:
        path = resolve_profile_path(path)
    return Profile.load(path)
