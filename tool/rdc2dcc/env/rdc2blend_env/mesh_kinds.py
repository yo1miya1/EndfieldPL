# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.
"""Which kind of mesh a draw call is: skinned, static, or an effect.

Three kinds, all decided from what the *pass* does and what the draw's own
streams look like - never from one game's naming:

  ``fx``       the draw belongs to a pass in which most of the draws do not
               write depth.  Semi-transparent effect geometry is submitted that
               way, and the effect part of a frame is a *pass*, not one draw:
               deciding per draw would pick up the opaque bits an effect pass
               also binds.  Measured over the pass, so an emitter that spawns an
               animated (skinned) effect mesh is still an effect - skinning is
               deliberately not part of this test.
  ``skinned``  the draw carries a real skin stream and belongs to the character
               instance the selector found.
  ``static``   what is left that is worth exporting: it writes depth, carries no
               usable skin stream, and is more than a billboard - more than
               ``min_vertices`` vertices and more than ``min_triangles``
               triangles.  That is what a scene's own geometry looks like, and
               what a full-screen quad or a 4-vertex helper card does not.

Every threshold lives in ``profile.mesh_kinds``; nothing here knows an event id,
a resource id or a game.  The module is pure python and imports nothing from the
package, so the head-less driver can load it inside qrenderdoc and the offline
solver can load it outside, and both decide the same thing.
"""

#: The kinds, in the order a report or a menu should show them.
KINDS = ("skinned", "static", "fx", "ui")

#: Chinese labels, so the front ends and the log agree on what to call them.
KIND_LABELS = {"skinned": "蒙皮网格", "static": "静态网格", "fx": "特效网格",
               "ui": "界面网格"}

#: Kinds a run may ask for, and the default when nothing is said.
KIND_ALIASES = {
    "skin": "skinned", "skinning": "skinned", "mesh": "skinned",
    "skeletal": "skinned", "蒙皮": "skinned", "蒙皮网格": "skinned",
    "scene": "static", "world": "static", "level": "static",
    "静态": "static", "静态网格": "static", "场景": "static",
    "effect": "fx", "effects": "fx", "vfx": "fx", "particle": "fx",
    "particles": "fx", "transparent": "fx",
    "特效": "fx", "特效网格": "fx", "粒子": "fx",
    "hud": "ui", "overlay": "ui", "widget": "ui", "gui": "ui",
    "界面": "ui", "界面网格": "ui", "ui网格": "ui",
}

#: The knobs, with the values this tool was fitted against.  A profile overrides
#: any of them; `mesh_kinds` in the profile is merged one level deep.
DEFAULTS = {
    # ---- which kinds a run exports -----------------------------------------
    "skinned": True,
    "static": True,
    "fx": True,
    # The UI layer, off by default: it is flat, screen-space and does not belong
    # in a scene of world geometry.  See `ui_from_eid` for how it is found.
    "ui": False,
    # ---- what counts as static ---------------------------------------------
    "static_min_vertices": 6,       # "more than": a quad (4) is not scene geometry
    "static_min_triangles": 2,      # "more than": one quad's worth
    # ---- what counts as an effect pass --------------------------------------
    "fx_depth_write_ratio": 0.75,   # of the pass's draws, this many write no depth
    "fx_min_draws": 1,              # a pass of one draw is still a pass
    # Whether a draw that *blends* also counts towards that ratio.  "Writes no
    # depth" is the sharper signal where it holds - it is what a depth-sorted
    # transparent pass does - but an engine that sorts its transparency against
    # the opaque geometry in one layer also puts alpha-tested, depth-writing
    # draws in there, and those drag the ratio under the threshold and take the
    # whole layer with them.  Blending is the property that layer actually has,
    # so counting either one measures it without moving the threshold.
    "fx_count_blended": False,
    # Which fields an *effect* pass is keyed by.  `None` means "the same ones the
    # character selection uses" (`select.group_by`), which is the right answer for
    # an engine that gives its transparency a depth target of its own.  An engine
    # that does not - one depth target and one viewport for the whole scene, the
    # opaque and the blended draws told apart by the colour target alone - needs
    # the colour target in here as well, or its effect geometry is measured
    # together with the opaque draws it is interleaved with and never reaches the
    # ratio below.
    "fx_group_by": None,
    # A pass that holds the character is never reclassified as an effect: the
    # character cuts out with alpha in some engines, and losing it to the effect
    # set would silently drop the very thing the run was started for.
    "fx_exempt_character_pass": True,
    # ---- where the 3D frame ends and the interface begins -------------------
    # A game draws its scene into a texture and then composites to the
    # backbuffer; everything the engine submits *after* that point is the
    # interface - the HUD, menus, the loading spinner - and none of it is world
    # geometry no matter what its depth state says.  The boundary is the same
    # event id the vertical flip changes at (`profile.flip_y_before_eid`, Unity
    # flips the projection's Y for the texture pass and not for the backbuffer),
    # so it is read from there unless this says otherwise.  Without a boundary
    # there is nothing to go on and no draw is called UI: the depth-write rule
    # classifies the overlay pass as effects, which is what it looks like from
    # the outside.
    "ui_from_eid": None,
    "ui_gets_scene_geometry": False,   # keep world-sized draws after the boundary
    # ---- how much of each kind to take --------------------------------------
    "max_parts": {"skinned": 64, "static": 4096, "fx": 4096, "ui": 512},
    # Every kind but the character may legitimately have no normals at all; the
    # skinned one never does, and a missing normal there is a real error.
    "require_normal": {"skinned": True, "static": False, "fx": False, "ui": False},
    # How far the fit may miss before a part is left out; `None` means "use the
    # run's `verify.accept_pose_rms`".
    "accept_rms": {"skinned": None, "static": 0.001, "fx": 0.001, "ui": None},
}


def resolve_kind(name):
    """Canonical kind for what a user typed, or the name unchanged."""
    key = str(name or "").strip().lower()
    if not key:
        return ""
    if key in KINDS:
        return key
    return KIND_ALIASES.get(key, key)


def parse_kinds(text):
    """``"skinned,static"`` (or a list, or None) -> an ordered list of kinds.

    Unknown names are returned as-is so the caller can say *which* one it did
    not recognise, rather than silently dropping a typo and exporting nothing.
    """
    if text is None:
        return list(KINDS)
    if isinstance(text, str):
        parts = [p for p in text.replace(";", ",").replace(" ", ",").split(",")]
    else:
        parts = list(text)
    out = []
    for p in parts:
        k = resolve_kind(p)
        if k and k not in out:
            out.append(k)
    return out


def label_for(kind):
    return KIND_LABELS.get(kind) or str(kind)


def config(profile):
    """The ``mesh_kinds`` block, defaults filled in."""
    cfg = dict(DEFAULTS)
    got = getattr(profile, "mesh_kinds", None)
    if isinstance(got, dict):
        for key, value in got.items():
            if key not in DEFAULTS:
                continue
            if isinstance(DEFAULTS[key], dict) and isinstance(value, dict):
                merged = dict(DEFAULTS[key])
                merged.update(value)
                cfg[key] = merged
            else:
                cfg[key] = value
    return cfg


def enabled(cfg):
    """The kinds this run was asked for, in KINDS order."""
    return [k for k in KINDS if cfg.get(k)]


def set_enabled(profile, kinds):
    """Record the chosen kinds on a profile's ``mesh_kinds`` block."""
    want = set(parse_kinds(kinds))
    block = dict(getattr(profile, "mesh_kinds", None) or {})
    for k in KINDS:
        block[k] = k in want
    profile.mesh_kinds = block
    return block


def accept_rms(cfg, kind, default):
    """How far a part of this kind may miss before it is left out."""
    got = (cfg.get("accept_rms") or {}).get(kind)
    try:
        return float(got) if got is not None else float(default)
    except (TypeError, ValueError):
        return float(default)


# ------------------------------------------------------------------ pass grouping

#: The survey records the depth target as ``depth``; profiles shipped against an
#: earlier version ask for ``depth_target``.
_FIELD_ALIASES = {"depth_target": "depth"}


def pass_key_of(draw, keys):
    """Which render pass a draw belongs to, keyed by an explicit field list."""
    return tuple(str(draw.get(_FIELD_ALIASES.get(k, k))) for k in keys)


def pass_key(draw, sel):
    """Which render pass a draw belongs to: its depth target and its viewport.

    Two passes that share a viewport - a shadow pass and the main one, say -
    stay apart because the depth target differs, which is why that field is in
    the key even though it is the less obvious of the two.  This is the key the
    *character selection* uses; an effect pass may be keyed differently, see
    `fx_pass_keys`.
    """
    return pass_key_of(draw, (sel or {}).get("group_by", ["depth_target", "viewport"]))


def fx_pass_keys(sel, cfg):
    """The fields an *effect* pass is keyed by, for this profile.

    Most engines submit their transparent geometry as a pass of its own, on its
    own depth target, and then `select.group_by` is exactly the right key.  Some
    do not: 逆水寒 keeps one depth target and one viewport for the whole scene and
    separates the opaque from the blended draws with the *colour* target,
    submitting both interleaved through the same pass.  Measured over the depth
    target alone such a pass is half opaque, the ratio below never fires, and the
    effect geometry is filed as scene geometry - or, carrying a skin stream as it
    does, as nothing at all.

    Naming the extra fields here splits those sub-passes apart.  It deliberately
    does *not* change `select.group_by`, because how a character is found and
    which draws are its effects are separate questions with separate answers, and
    moving the first one changes which instance every run picks.
    """
    keys = (cfg or {}).get("fx_group_by")
    if not keys:
        keys = (sel or {}).get("group_by") or ["depth_target", "viewport"]
    return list(keys)


def _int(draw, key, default=0):
    try:
        return int(draw.get(key, default) or 0)
    except (TypeError, ValueError):
        return default


def group_passes(draws, sel):
    """{pass key: [draws]} for a survey's draw calls, in first-seen order."""
    groups = {}
    for d in draws:
        groups.setdefault(pass_key(d, sel), []).append(d)
    return groups


def group_passes_by(draws, keys):
    """`group_passes`, keyed by an explicit field list rather than by `sel`."""
    groups = {}
    for d in draws:
        groups.setdefault(pass_key_of(d, keys), []).append(d)
    return groups


def pass_writes_no_depth(draw):
    """Whether a draw has depth writes switched off.

    ``None`` means the capture did not report the depth state at all (an older
    survey, or a build that will not answer); that is treated as "writes depth",
    so an unknown pass stays opaque rather than being handed to the effects.
    """
    return draw.get("depth_writes") is False


def pass_is_transparent(draw, cfg):
    """Whether a draw belongs to a transparent layer, by the run's own rule.

    Always true for a draw that writes no depth, and - when `fx_count_blended` is
    on - also for one that blends while still writing depth.  `None` for either
    state means the build would not say, and is read as "opaque": an unknown pass
    must stay opaque rather than being handed to the effect set whole.
    """
    if pass_writes_no_depth(draw):
        return True
    return bool((cfg or {}).get("fx_count_blended")) and draw.get("blend") is True


def effect_passes(draws, sel, cfg, keys=None):
    """The keys of the passes that are effect passes, with their ratios.

    Returns ``({key: ratio}, {key: (n_draws, n_transparent)})`` so a report can
    show *why* a pass was called an effect pass - a bare boolean here is exactly
    the kind of thing that is impossible to argue with later.  `keys` overrides
    the grouping; left out, it comes from `fx_pass_keys`.
    """
    keys = list(keys) if keys else fx_pass_keys(sel, cfg)
    ratio_min = float(cfg.get("fx_depth_write_ratio", 0.75))
    min_draws = int(cfg.get("fx_min_draws", 1))
    hits, detail = {}, {}
    for key, group in group_passes_by(draws, keys).items():
        n = len(group)
        no_depth = sum(1 for d in group if pass_is_transparent(d, cfg))
        ratio = (float(no_depth) / float(n)) if n else 0.0
        detail[key] = (n, no_depth)
        if n >= min_draws and ratio >= ratio_min:
            hits[key] = ratio
    return hits, detail


# ------------------------------------------------------------------ one draw

def ui_boundary(profile):
    """The event id at which the frame stops being 3D and becomes interface.

    Read from `mesh_kinds.ui_from_eid` when it is set, and otherwise from the
    event id the vertical flip changes at - they are the same moment seen from
    two sides, because both are "the engine stopped rendering into a texture and
    started compositing to the backbuffer".  `None` means the boundary is not
    known, and then nothing is called UI.
    """
    cfg = config(profile)
    for value in (cfg.get("ui_from_eid"), getattr(profile, "flip_y_before_eid", None)):
        try:
            if value not in (None, "", 0):
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def classify_draw(draw, is_effect_pass, cfg, exact_vertices=None, is_ui=False):
    """The kind of one draw that is **not** part of the chosen character.

    `exact_vertices` is the vertex count read off the draw's index buffer when
    the caller has it (the probe does); the survey does not, and passes the
    index count instead - an upper bound, so the survey keeps a superset and the
    exact count is applied again offline.

    `is_ui` is the engine's own answer to "is this the interface": true for
    everything submitted after the frame was composited to the backbuffer.  That
    answer beats every rule below it, because a HUD quad writes no depth and has
    more than two triangles, and without this it would be filed as an effect -
    a flat panel pinned into the middle of a 3D scene.

    A draw that carries a skin stream but is not the character the selector
    settled on is *neither*: it is another character, an NPC, a crowd member, and
    calling it "scene geometry" would export a posed figure with its skinning
    stripped, standing in the middle of the scene.  Asking for it is a job for a
    separate run, or for `--eids`.
    """
    if draw.get("error"):
        return None
    if is_ui:
        return "ui"
    if is_effect_pass:
        return "fx"
    if draw.get("has_skin"):
        return None
    if not draw.get("depth_writes", True):
        # neither an effect pass nor opaque: a one-off transparent draw, which
        # belongs to no set this tool can name
        return None
    n = _int(draw, "numIndices")
    if exact_vertices is not None:
        n = int(exact_vertices)
    if n <= int(cfg.get("static_min_vertices", 6)):
        return None
    if (n // 3) <= int(cfg.get("static_min_triangles", 2)):
        return None
    return "static"


def classify_survey(survey, profile, character_eids=(), want=None):
    """{eid str: kind} for every draw of a survey.

    `character_eids` are the draws the skinned selector already claimed - the one
    character instance this run is about.  They are always ``skinned``, and -
    when ``fx_exempt_character_pass`` is on - the pass they were found in is not
    allowed to become an effect pass, so a character that cuts out with alpha
    cannot be swallowed by the effect set.

    Everything submitted after the frame was composited to the backbuffer is the
    interface, and is called that before any other rule gets a look at it: it is
    flat, it is not in the world, and the pass it arrives in looks exactly like an
    effect pass from the outside.
    """
    cfg = config(profile)
    sel = getattr(profile, "select", None) or {}
    draws = [d for d in (survey.get("draws") or []) if not d.get("error")]
    claimed = set(int(e) for e in (character_eids or ()))
    # The pass keys below are all built with the *effect* grouping, so the
    # exemption and the detection are talking about the same passes.  With the
    # default grouping the two are the same list and nothing here can tell.
    fx_keys = fx_pass_keys(sel, cfg)
    exempt = set()
    if cfg.get("fx_exempt_character_pass", True) and claimed:
        for d in draws:
            if _int(d, "eid") in claimed:
                exempt.add(pass_key_of(d, fx_keys))
    hits, _detail = effect_passes(draws, sel, cfg, keys=fx_keys)
    for key in exempt:
        hits.pop(key, None)

    boundary = ui_boundary(profile)
    keep_world = bool(cfg.get("ui_gets_scene_geometry", False))
    out = {}
    for d in draws:
        eid = _int(d, "eid")
        if eid in claimed:
            out[str(eid)] = "skinned"
            continue
        is_ui = boundary is not None and eid >= boundary
        if is_ui and keep_world:
            # A caller can ask for world-sized geometry after the boundary too -
            # an engine that draws a 3D HUD prop, or a capture whose boundary is
            # a guess.  Small draws are still the interface.
            is_ui = _int(d, "numIndices") <= int(cfg.get("static_min_vertices", 6)) * 8
        kind = classify_draw(d, pass_key_of(d, fx_keys) in hits, cfg, is_ui=is_ui)
        if kind is None:
            continue
        out[str(eid)] = kind
    wanted = enabled(cfg) if want is None else list(want)
    return dict((e, k) for e, k in out.items() if k in wanted)


def summarise(kinds_by_eid, survey=None, profile=None):
    """A short, printable account of a classification, for the log."""
    counts = {}
    for kind in kinds_by_eid.values():
        counts[kind] = counts.get(kind, 0) + 1
    lines = ["  ".join("%s=%d" % (label_for(k), counts.get(k, 0)) for k in KINDS)]
    if survey is not None and profile is not None:
        cfg = config(profile)
        sel = getattr(profile, "select", None) or {}
        draws = [d for d in (survey.get("draws") or []) if not d.get("error")]
        _hits, detail = effect_passes(draws, sel, cfg)
        for key, (n, no_depth) in sorted(detail.items(), key=lambda kv: -kv[1][0]):
            if n and float(no_depth) / float(n) >= float(cfg.get("fx_depth_write_ratio", 0.75)):
                lines.append("  特效 pass %s: %d/%d 个 drawcall 不写深度"
                             % ("|".join(str(k)[:12] for k in key), no_depth, n))
    lines.append("  特效 pass 按 %s 分组"
                 % ",".join(fx_pass_keys(getattr(profile, "select", None) or {}, config(profile))))
    return "\n".join(lines)
