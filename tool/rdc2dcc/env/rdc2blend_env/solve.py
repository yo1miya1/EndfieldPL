# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.

"""Offline solve: palette, pose, camera, attributes, world placement.

This is the CPU half of the pipeline - the part that gets iterated on when a new
game shows up.  It reads what the probe stage dumped and never talks to
RenderDoc.

The palette search is deliberately residual driven: the least squares residual of
"skin the mesh, fit a projective camera, compare with the observed clip
positions" separates a correct palette (~1e-7) from a wrong one (~1e-2) by five
orders of magnitude, so the tool can *find* the palette rather than be told it.
"""

import json
import math
import os
import struct

from . import mesh_kinds
from . import util
from .adapters import get_adapter, position_declaration
from .profile import CBView, cb_names
from .util import (FLAG_ALT, FLAG_TS, as_mat4, decode_packed_normal, frame_apply,
                   frame_matrix, inv3, inv4, is_affine, load_json, mat4_apply,
                   mat4_from3, mat4_mul, mat4_transpose, norm3, normalise_affine,
                   read_comps, scene_matrix, save_json, solve_ls, transform_ok,
                   unit3, write_mesh)

# The one place a solve is hot enough to be worth leaving Python for.  numpy is
# not assumed: the tool is meant to run on whatever interpreter is to hand, and
# the machine this was developed on has one without it.  Everything below has a
# pure-Python path that produces the same answer; numpy only decides how long it
# takes.  `RDC2BLEND_NO_NUMPY=1` forces the slow one, which is how the two are
# held against each other.
try:
    import numpy as _np
except Exception:                                                # pragma: no cover
    _np = None

ACCEPT_RMS_DEFAULT = 1.0e-3


def have_numpy():
    """True when the fast path is in use - for the self-check and the log line."""
    return _np is not None and not os.environ.get("RDC2BLEND_NO_NUMPY")


class NotThisCamera(RuntimeError):
    """The draw was not rendered with the camera this run recovered.

    A capture holds more than the frame's own view: shadow maps, reflections,
    thumbnails, a second camera.  Every draw in it can be fitted - the solver
    fits whatever it is given - but only the ones sharing the recovered
    view-projection can be placed in the scene the .blend is a reconstruction
    of.  See `util.is_affine` for how that is told apart from a real object.
    """


def is_screen_space(posed, tol=0.05, reach=4.0):
    """True when a draw's clip coordinates *are* the picture.

    Some draws never reach the world at all: a full-screen effect, a UI blit, a
    post-process tap.  The engine submits a vertex or two and the vertex shader
    invents the rest, or the vertices it does submit already carry screen
    coordinates - so every one of them lands inside the normalised device range
    with `w` at 1, and there is no world matrix to recover.

    That is exactly the shape that makes `VP^-1 . A` come out projective, so the
    two cases have to be told apart: a *different* view-projection (a shadow map)
    also fails the affine test, but its coordinates are world-scaled and land
    nowhere near NDC.

    The `w` test is the sharp one - an orthographic pass is the only other thing
    that has `w` at 1 everywhere, and it is the coordinates that separate them.
    `reach` is deliberately loose: the usual full-screen *triangle* is submitted
    as (-1,-1), (3,-1), (-1,3) precisely so its corners fall outside the frame,
    and a tight bound would have rejected the very draws this is for.
    """
    if not posed:
        return False
    for v in posed:
        w = v[3]
        if w <= 0.0 or abs(w - 1.0) > tol:
            return False
        if abs(v[0] / w) > reach or abs(v[1] / w) > reach:
            return False
    return True


# ============================================================ character selection


#: Which render pass a draw belongs to.  Lives in mesh_kinds because the
#: classifier needs the very same grouping to call a pass an effect pass, and two
#: copies of "what makes a pass" is how a draw ends up in two sets at once.
_FIELD_ALIASES = mesh_kinds._FIELD_ALIASES


def _pass_key(d, sel):
    return mesh_kinds.pass_key(d, sel)


def split_instances(parts):
    """Split a pass into per-character-instance runs.

    A capture may draw the same character many times (an animation preview, a
    turntable, several characters).  Because the parts of one instance are drawn
    with distinct index counts, a signature that repeats marks the start of the
    next instance.
    """
    out, cur, seen = [], [], set()
    for d in parts:
        sig = (int(d["numIndices"]), int(d.get("numInstances", 1)))
        if sig in seen:
            out.append(cur)
            cur, seen = [], set()
        cur.append(d)
        seen.add(sig)
    if cur:
        out.append(cur)
    return out


def select_draws(survey: dict, profile, log=None, want_eids=None):
    """Pick the draw calls of one character instance.

    Character draws are the ones with skin attributes backed by real per-vertex
    streams and a large structured buffer on the vertex shader.  They are grouped
    by render pass (depth + viewport), split into instances, and the largest
    instance is expanded to *every* draw of that pass inside its event range -
    rigid parts of the same character do not carry usable skin weights and would
    otherwise be missed.
    """
    sel = profile.select
    draws = [d for d in survey.get("draws", []) if not d.get("error")]
    if want_eids:
        keep = {int(e) for e in want_eids}
        parts = [d for d in draws if int(d["eid"]) in keep]
        parts.sort(key=lambda d: int(d["eid"]))
        if log:
            log.info("using explicit eids", n=len(parts))
        return parts

    min_bone = int(sel.get("min_bone_buffer_bytes", 262144))
    skin = [d for d in draws if d.get("has_skin")
            and max([int(b["size"]) for b in d.get("buffers", [])] or [0]) >= min_bone]
    if not skin:
        return []
    groups = {}
    for d in skin:
        groups.setdefault(_pass_key(d, sel), []).append(d)
    key, parts = max(groups.items(), key=lambda kv: sum(p["numIndices"] for p in kv[1]))
    parts.sort(key=lambda d: int(d["eid"]))
    insts = split_instances(parts)
    best = max(insts, key=lambda ins: (sum(p["numIndices"] for p in ins), -ins[0]["eid"]))
    lo, hi = int(best[0]["eid"]), int(best[-1]["eid"])
    if log:
        log.info("character pass", pass_draws=len(parts), instances=len(insts),
                 sizes=[len(i) for i in insts][:12])
        log.info("chosen instance", first=lo, last=hi, parts=len(best))
    # The range holds every draw of the pass, including any the engine issued for
    # something other than this character; the adapter gets to say which of them
    # are not it (see Adapter.keep_draw).  Both ends of the range are kept whatever
    # it answers - they are the skinned parts the range was taken from.
    family = position_declaration(best[0].get("inputs"))
    adapter = get_adapter(profile)
    chosen, dropped = [], []
    for d in draws:
        if _pass_key(d, sel) != key or not (lo <= int(d["eid"]) <= hi):
            continue
        (chosen if adapter.keep_draw(d, family, profile) else dropped).append(d)
    if dropped and log:
        log.info("draws in the range that are not this character's mesh family",
                 eids=[int(d["eid"]) for d in dropped])
    chosen.sort(key=lambda d: int(d["eid"]))
    if len(chosen) > int(sel.get("max_parts", 64)):
        chosen = chosen[:int(sel.get("max_parts", 64))]
    return chosen


def select_meshes(survey: dict, profile, log=None, want_eids=None):
    """Every draw call the run was asked for, split by kind.

    Returns ``{kind: [draw, ...]}`` for the kinds `profile.mesh_kinds` switches
    on, in `mesh_kinds.KINDS` order.  The three sets are disjoint by
    construction:

    * the character instance is found exactly as it always was (`select_draws`);
    * every draw it claimed is removed from the other two, so a character's rigid
      parts - a weapon, a tassel - are not also exported as "scene geometry";
    * the classifier then sorts the rest into static and effect draws.

    Picking only some kinds therefore picks exactly those, which is what the
    front ends offer: static alone exports no skinning at all, and skinning alone
    exports no scene.
    """
    cfg = mesh_kinds.config(profile)
    wanted = mesh_kinds.enabled(cfg)
    out = dict((k, []) for k in mesh_kinds.KINDS)
    if not wanted:
        return out

    # the character is found first even when it is not wanted: its draws have to
    # be excluded from the other sets either way
    character = select_draws(survey, profile, log=log, want_eids=want_eids)
    claimed = set(int(d["eid"]) for d in character)
    if want_eids:
        # an explicit list is the user pointing at draws, not a survey to be
        # classified: take them as the character and stop
        if "skinned" in wanted:
            out["skinned"] = character
        return out

    kinds_by_eid = mesh_kinds.classify_survey(survey, profile, character_eids=claimed)
    draws = [d for d in (survey.get("draws") or []) if not d.get("error")]
    for d in sorted(draws, key=lambda x: int(x["eid"])):
        eid = int(d["eid"])
        kind = kinds_by_eid.get(str(eid))
        if kind is None or kind not in wanted:
            continue
        out[kind].append(d)

    for kind in mesh_kinds.KINDS:
        cap = int((cfg.get("max_parts") or {}).get(kind, 64))
        if cap and len(out[kind]) > cap:
            if log:
                log.info("%s capped" % mesh_kinds.label_for(kind),
                         kept=cap, of=len(out[kind]))
            out[kind] = out[kind][:cap]
    if log:
        for kind in mesh_kinds.KINDS:
            if kind in wanted:
                log.info("%s: %d 个 drawcall" % (mesh_kinds.label_for(kind), len(out[kind])))
        for kind in mesh_kinds.KINDS:
            if out[kind]:
                log.dim("   %s eids: %s"
                        % (kind, _ranges([int(d["eid"]) for d in out[kind]])))
    return out


def _ranges(eids):
    """[1,2,3,7,9,10] -> "1-3,7,9-10" - a survey can hold thousands of draws."""
    out, i = [], 0
    while i < len(eids):
        j = i
        while j + 1 < len(eids) and eids[j + 1] == eids[j] + 1:
            j += 1
        out.append(str(eids[i]) if j == i else "%d-%d" % (eids[i], eids[j]))
        i = j + 1
    return ",".join(out)


def classify(survey: dict, profile, character_eids=(), want=None):
    """{eid str: kind} for a survey - the classifier, with the profile's knobs."""
    return mesh_kinds.classify_survey(survey, profile, character_eids=character_eids,
                                      want=want)


def load_inputs(d):
    """One draw's dump, whichever of the two shapes the probe left behind.

    `inputs.bin` is what this build writes; `inputs.json` is what it used to, and
    is still read so that a run collected by an older build - or by hand - solves
    without being probed again.  Both come back in the same shape, so nothing
    below this line has to know which it got.
    """
    path = os.path.join(d, "inputs.bin")
    if os.path.exists(path):
        return util.read_inputs(path)
    return load_json(os.path.join(d, "inputs.json"))


def behind_the_eye(meta):
    """True when the frame this capture was taken from cannot show this draw.

    A vertex with w <= 0 is behind the eye and gets clipped, so a draw whose
    *every* vertex is behind the eye is submitted and rasterizes nothing at all.
    Engines hand the GPU whole objects the camera has already turned away from -
    this capture has eighteen such draws, sitting 40 000 units behind the eye of
    a view whose subject is 900 units across.  They have no place in a .blend that
    is meant to be this frame's character: the game never drew them, and the
    silhouette check compares the export against a depth buffer that cannot
    contain them either.

    Reads only `posed`, which the probe already dumped, so a run can re-decide
    this offline without opening the capture again.
    """
    d = meta["dir"]
    try:
        path = os.path.join(d, "inputs.bin")
        if os.path.exists(path):
            # just the one block, straight out of the file: this runs for every
            # draw in the run and only ever looks at w
            posed = util.read_posed(path)
            return len(posed) >= 4 and all(posed[i] <= 0.0
                                           for i in range(3, len(posed), 4))
        posed = load_json(os.path.join(d, "inputs.json"))["posed"]
    except Exception:
        return False
    return bool(posed) and all(v[3] <= 0.0 for v in posed)


# ================================================================= linear algebra


def _fit(X, posed, rows, posed_np=None):
    """Fit model -> clip.  `X` is compact (one entry per element of `rows`),
    `posed` is indexed by the original vertex index.

    This is where a solve spends its time, and the reason is the alignment
    search in `solve_draw`: it refits the camera once per candidate shift, which
    on a real capture is a hundred thousand fits.  Each one is a 16-unknown
    least-squares problem - but a *block diagonal* one, because output component
    `k` reads only `[x, y, z, 1]` and writes only its own four unknowns.  So the
    normal equations `solve_ls` would assemble are four independent 4x4 systems,
    and with numpy the sums move into C and the four go to LAPACK in one call.

    The pure-Python path below is not decoration: it is what runs wherever numpy
    is missing, and the two agree to the precision the answer is read at.  The
    singular cases still come back as `None`, which is what tells the search a
    hypothesis produced nothing rather than something enormous.
    """
    m = len(rows)
    # Only where the fit is *over*-determined.  Each row writes four equations
    # and the fit has sixteen unknowns, so five rows is the first that leaves a
    # degree of freedom; at four or fewer the system is exactly determined and
    # the residual is zero for every hypothesis that is not singular.  Which of
    # those a shift is happens to be is a knife-edge that LAPACK and the
    # elimination below do not always call the same way, and the whole answer
    # hangs on it - so below five rows the original solver runs, exactly.  That
    # is a few hundred fits over four vertices, against the hundreds of thousands
    # of sixty-row fits this is here for.
    if _np is not None and m > 4 and not os.environ.get("RDC2BLEND_NO_NUMPY"):
        D = _np.empty((m, 4), dtype=float)
        D[:, :3] = X if isinstance(X, _np.ndarray) else _np.asarray(X, dtype=float)
        D[:, 3] = 1.0
        B = posed_np[rows] if posed_np is not None else \
            _np.asarray([posed[i] for i in rows], dtype=float)
        M = D.T @ D
        try:
            sol = _np.linalg.solve(M, D.T @ B)
        except _np.linalg.LinAlgError:
            # the same "this hypothesis produced nothing" answer `solve_ls`
            # gives when its pivot collapses
            return None, None
        if not _np.all(_np.isfinite(sol)):
            return None, None
        resid = D @ sol - B
        per = _np.sqrt((resid * resid).sum(axis=0) / m)
        return sol.T.tolist(), float(_np.sqrt((per * per).sum() / 4.0))

    eq, rhs = [], []
    for pos, i in enumerate(rows):
        x, y, z = X[pos]
        for k in range(4):
            r = [0.0] * 16
            r[k * 4 + 0] = x
            r[k * 4 + 1] = y
            r[k * 4 + 2] = z
            r[k * 4 + 3] = 1.0
            eq.append(r)
            rhs.append(posed[i][k])
    sol = solve_ls(eq, rhs, 16)
    if sol is None:
        return None, None
    A = [sol[0:4], sol[4:8], sol[8:12], sol[12:16]]
    per = []
    for k in range(4):
        s = 0.0
        for pos, i in enumerate(rows):
            x, y, z = X[pos]
            s += (A[k][0] * x + A[k][1] * y + A[k][2] * z + A[k][3] - posed[i][k]) ** 2
        per.append(math.sqrt(s / len(rows)))
    return A, math.sqrt(sum(p * p for p in per) / 4)


class _Palette:
    """Lazy reader for 3x4 bone matrices inside the structured palette buffer."""

    def __init__(self, bone: bytes, base: int, stride_f4: int = 3):
        self.bone = bone
        self.base = base
        self.stride = stride_f4
        self.n = len(bone) // 16
        self.cache = {}

    def rows(self, bone_index):
        M = self.cache.get(bone_index)
        if M is None:
            k = self.base + self.stride * bone_index
            if k < 0 or k + 3 > self.n:
                M = False
            else:
                M = tuple(struct.unpack_from("<4f", self.bone, (k + t) * 16) for t in range(3))
            self.cache[bone_index] = M
        return M


def _lbs(bind, bidx, wts, pal: _Palette, rows):
    out = []
    for i in rows:
        p = bind[i]
        ax = ay = az = 0.0
        for j, w in enumerate(wts[i]):
            if w <= 1e-7:
                continue
            M = pal.rows(int(bidx[i][j]))
            if not M:
                continue
            r0, r1, r2 = M
            ax += w * (r0[0] * p[0] + r0[1] * p[1] + r0[2] * p[2] + r0[3])
            ay += w * (r1[0] * p[0] + r1[1] * p[1] + r1[2] * p[2] + r1[3])
            az += w * (r2[0] * p[0] + r2[1] * p[1] + r2[2] * p[2] + r2[3])
        out.append((ax, ay, az))
    return out


# ================================================================ camera model


# ================================================================== one draw


def solve_draw(eid, meta, profile, camera=None, adapter=None, log=None, kind=None):
    """Recover the palette, the skinning hypothesis and model -> clip for one draw."""
    adapter = adapter or get_adapter(profile)
    d = meta["dir"]
    cbs = CBView({int(slot): open(info["path"], "rb").read()
                  for slot, info in (meta.get("cbuffers") or {}).items()},
                 cb_names(meta.get("cbuffers")))
    # A rigid part - a weapon, an attachment - carries no skin stream of its own
    # and is drawn with no palette bound.  It is still part of the character, so
    # the fit below simply falls back to a single rigid transform for it.
    bone_info = meta.get("bone")
    bone = b""
    if bone_info:
        with open(bone_info["path"], "rb") as f:
            bone = f.read()[int(bone_info.get("off") or 0):]

    inp = load_inputs(d)
    n, need = inp["n"], inp["need"]
    bind, posed, bidx, wts, idx = (inp["bind"], inp["posed"], inp["bidx"],
                                   inp["wts"], inp["idx"])
    stride_f4 = int(profile.bone_stride_f4)
    accept = float(profile.verify.get("accept_pose_rms", ACCEPT_RMS_DEFAULT))
    max_delta = int(profile.discover.get("max_align_delta", 600))

    # The search below fits the camera once per candidate shift, so anything it
    # touches per call has to be cheap.  The row sets never change and the clip
    # positions never change, so both are turned into arrays once here rather
    # than rebuilt a hundred thousand times.
    _fast = have_numpy()
    if _fast:
        scan_rows = _np.arange(0, need, max(1, need // 60))[:60]
        full_rows = _np.arange(0, need, max(1, need // 4000))
        all_rows = _np.arange(need)
        posed_np = _np.asarray(posed, dtype=float)
        try:
            bind_np = _np.asarray(bind, dtype=float)
        except Exception:
            # a ragged dump - the rigid shift search falls back to the list
            bind_np = None
    else:
        scan_rows = list(range(0, need, max(1, need // 60)))[:60]
        full_rows = list(range(0, need, max(1, need // 4000)))
        all_rows = list(range(need))
        posed_np = bind_np = None

    def evaluate(base, mode, rows, delta=0):
        if mode == "rigid":
            X = (bind_np[rows + delta] if bind_np is not None
                 else [bind[i + delta] for i in rows])
        else:
            X = _lbs(bind, bidx, wts, _Palette(bone, base, stride_f4),
                     [i + delta for i in rows])
        return _fit(X, posed, rows, posed_np=posed_np)

    cheap = (adapter.palette_candidates(profile, cbs, bone, exhaustive=False)
             if bone else [])
    if not cheap and bone:
        raise RuntimeError("eid %s: the profile produced no palette candidate "
                           "(constant buffer %s not bound?)"
                           % (eid, profile.palette_base[0]["cb"]))

    best = (float("inf"), "none", None, "skin", 0)
    for label, base in cheap:
        A, rms = evaluate(base, "skin", scan_rows, 0)
        if rms is not None and rms < best[0]:
            best = (rms, label, base, "skin", 0)
    A, rms = evaluate(None, "rigid", scan_rows, 0)
    if rms is not None and rms < best[0]:
        best = (rms, "rigid", None, "rigid", 0)

    if best[0] > accept:
        wide = adapter.palette_candidates(profile, cbs, bone, exhaustive=True,
                                          log=log)
        for label, base in wide:
            A, rms = evaluate(base, "skin", scan_rows, 0)
            if rms is not None and rms < best[0]:
                best = (rms, label, base, "skin", 0)
        if log:
            log.info("eid %d exhaustive search done" % eid, rms="%.3g" % best[0])

    # RenderDoc's post-VS array can start at a vertex id it never reports, so
    # every shift is tried until one of them fits.  The search stops at the first
    # shift that reaches `accept`, and that is not only a saving: a small effect
    # mesh is fitted from as few as four rows, and four rows write sixteen
    # equations for sixteen unknowns, so *every* shift that is not singular fits
    # it exactly.  Comparing those residuals against each other compares rounding
    # noise, and the shift that wins is whichever one the arithmetic happened to
    # favour - so the search would place such a mesh somewhere arbitrary and
    # differently on a different machine.  Stopping at the first shift that clears
    # `accept` is the same threshold the rest of the run judges a fit by, and it
    # makes the answer a property of the capture rather than of the float unit.
    if best[0] > accept:
        for delta in range(1, min(max_delta, n - need) + 1):
            for label, base in (cheap if best[0] > accept else cheap[:2]):
                A, rms = evaluate(base, "skin", scan_rows, delta)
                if rms is not None and rms < best[0]:
                    best = (rms, label, base, "skin", delta)
            A, rms = evaluate(None, "rigid", scan_rows, delta)
            if rms is not None and rms < best[0]:
                best = (rms, "rigid", None, "rigid", delta)
            if best[0] <= accept:
                break
        if log:
            log.info("eid %d alignment search done" % eid,
                     delta=best[4], rms="%.3g" % best[0])

    # No hypothesis fitted at all: fall back to the rigid one rather than read a
    # palette that never produced a finite residual, so what surfaces is the
    # fit's own "singular" complaint instead of a None base a few lines later.
    if best[0] == float("inf"):
        best = (float("inf"), "rigid", None, "rigid", 0)

    _, label, base, mode, delta = best
    pal = _Palette(bone, base, stride_f4) if mode != "rigid" else None

    def make_x(rows):
        if mode == "rigid":
            return (bind_np[rows + delta] if bind_np is not None
                    else [bind[i + delta] for i in rows])
        return _lbs(bind, bidx, wts, pal, [i + delta for i in rows])

    Xs = make_x(full_rows)
    A, rms = _fit(Xs, posed, full_rows, posed_np=posed_np)
    if A is None:
        raise RuntimeError("eid %s: camera fit is singular" % eid)
    # the exported geometry, as a plain list: everything downstream of here -
    # `frame_apply`, `write_mesh` - indexes vertices as sequences, and a numpy
    # row is not one
    X = [tuple(p[:3]) for p in make_x(all_rows)]

    vp = (camera or {}).get("vp")
    if vp is None:
        vp = adapter.camera_view(cbs, profile, meta)["vp"]
    Model = adapter.model_transform({"vp": vp, "A": A}, profile)
    screen_space = False
    if not is_affine(Model):
        if is_screen_space(posed):
            # Not in the world at all - it is in the picture.  `build_scene`
            # hangs it off the camera instead of placing it in the scene, so it
            # is kept and marked rather than dropped.
            screen_space = True
        else:
            # Composing the inverse of *this* camera with a fit made under
            # another view-projection leaves a projective matrix, and an object
            # placed by one ends up somewhere arbitrary.  Saying so here rather
            # than writing it out is the difference between a scene with a few
            # parts missing and a scene with a few parts in the wrong place.
            raise NotThisCamera(
                "eid %s was not drawn with the recovered camera (its object "
                "matrix came out projective: last row %s)"
                % (eid, [round(v, 4) for v in Model[3]]))
    if not screen_space:
        Model = normalise_affine(Model)
    return {"eid": eid, "n": need, "nidx": len(idx), "mode": mode, "base": base,
            "label": label, "rms": rms, "align_delta": delta,
            "X": X, "A": A, "model": Model, "vp": vp, "camera": camera,
            "kind": kind or (meta.get("kind") or "skinned"),
            "screen_space": screen_space,
            "_inputs": inp, "_meta": meta}


# =========================================================== attribute decoding


def generate_tangents(pos, nrm, uv, idx):
    """Per-vertex tangents accumulated from UV0 and orthonormalised."""
    n = len(pos)
    tan = [[0.0, 0.0, 0.0] for _ in range(n)]
    bit = [[0.0, 0.0, 0.0] for _ in range(n)]
    for t in range(0, len(idx) - 2, 3):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        e1 = [pos[i1][k] - pos[i0][k] for k in range(3)]
        e2 = [pos[i2][k] - pos[i0][k] for k in range(3)]
        du1, dv1 = uv[i1][0] - uv[i0][0], uv[i1][1] - uv[i0][1]
        du2, dv2 = uv[i2][0] - uv[i0][0], uv[i2][1] - uv[i0][1]
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-12:
            continue
        r = 1.0 / det
        sd = [(e1[k] * dv2 - e2[k] * dv1) * r for k in range(3)]
        td = [(e2[k] * du1 - e1[k] * du2) * r for k in range(3)]
        for i in (i0, i1, i2):
            for k in range(3):
                tan[i][k] += sd[k]
                bit[i][k] += td[k]
    out = []
    for i in range(n):
        nn = nrm[i]
        t = tan[i]
        d = sum(nn[k] * t[k] for k in range(3))
        t = [t[k] - nn[k] * d for k in range(3)]
        ln = norm3(t)
        if ln < 1e-8:
            a = (0.0, 0.0, 1.0) if abs(nn[2]) < 0.9 else (1.0, 0.0, 0.0)
            t = [a[1] * nn[2] - a[2] * nn[1], a[2] * nn[0] - a[0] * nn[2],
                 a[0] * nn[1] - a[1] * nn[0]]
            ln = norm3(t) or 1.0
        t = [c / ln for c in t]
        b = [nn[1] * t[2] - nn[2] * t[1], nn[2] * t[0] - nn[0] * t[2],
             nn[0] * t[1] - nn[1] * t[0]]
        w = 1.0 if sum(bit[i][k] * b[k] for k in range(3)) >= 0.0 else -1.0
        out.append((t[0], t[1], t[2], w))
    return out


def attr_requirements(profile, kind):
    """What a draw of this kind must have for its attributes to be decodable.

    The character is drawn with a normal stream by definition, and a character
    without one means the layout was misread - that is worth stopping for.  Scene
    geometry and effect meshes are not: an unlit decal or a particle ribbon
    legitimately carries no normal at all, and refusing to export it because of
    that would be the tool inventing a requirement the game never had.  Blender
    computes what is missing from the geometry, and the report says so.
    """
    cfg = mesh_kinds.config(profile)
    return bool((cfg.get("require_normal") or {}).get(kind, kind == "skinned"))


def decode_attributes(sol, profile, out_dir, adapter=None, log=None):
    """Decode every vertex stream for one draw, in the solver's vertex order."""
    adapter = adapter or get_adapter(profile)
    meta, inp = sol["_meta"], sol["_inputs"]
    inputs = meta["inputs"]
    d = meta["dir"]
    kind = sol.get("kind") or "skinned"
    stride_by_slot = {i["slot"]: i.get("stride", 0) for i in inputs}
    raw = {}
    for i in inputs:
        s = i["slot"]
        if s in raw or stride_by_slot.get(s, 0) <= 0:
            continue
        p = os.path.join(d, "vb%d.bin" % s)
        if os.path.exists(p):
            raw[s] = open(p, "rb").read()

    cls = adapter.classify_attributes(inputs, profile)
    nrm_s, tan_s = cls["normal"], cls["tangent"]
    if nrm_s is None and attr_requirements(profile, kind):
        raise RuntimeError("eid %s: no NORMAL attribute" % sol["eid"])
    delta = int(sol["align_delta"])
    n = sol["n"]
    X = sol["X"]

    def attr(spec, i, decode=True):
        s = spec["slot"]
        st = stride_by_slot.get(s, 0)
        buf = raw.get(s)
        if not buf or st <= 0:
            return None
        off = (i + delta) * st + spec["off"]
        if off + max(1, spec["comps"]) * spec["cbyte"] > len(buf):
            return None
        return read_comps(buf, off, spec)

    nrm_packed = bool(nrm_s) and nrm_s["comps"] < 3
    P, N, T = list(X), [], [None] * n
    UV = [[] for _ in cls["uvs"]]
    ALT, TS = [], []
    for i in range(n):
        nn, hand = (0.0, 0.0, 1.0), 1.0
        if nrm_s is None:
            # no normal stream at all: a placeholder the .blend throws away, and
            # the flag below tells build_scene to let Blender derive the real
            # ones from the geometry.  The other streams are still decoded.
            N.append(nn)
        else:
            s = nrm_s["slot"]
            st = stride_by_slot[s]
            nn, hand = adapter.decode_normal(raw[s], (i + delta) * st + nrm_s["off"],
                                             nrm_s, profile.normal_packing)
            if nn is None:                  # normal_packing == "none"
                nn = (0.0, 0.0, 1.0)
            N.append(nn)
        if tan_s is not None:
            v = attr(tan_s, i)
            if v:
                t = [c / (norm3(v[:3]) or 1.0) for c in v[:3]]
                d0 = sum(nn[k] * t[k] for k in range(3))
                t = [t[k] - nn[k] * d0 for k in range(3)]
                ln = norm3(t)
                T[i] = ([c / ln for c in t] + [v[3] if len(v) > 3 else hand]) if ln > 1e-4 else None
        for k, (_, spec) in enumerate(cls["uvs"]):
            v = attr(spec, i)
            UV[k].append((v[0], v[1]) if v else (0.0, 0.0))
        if cls["alt"]:
            v = attr(cls["alt"], i)
            ALT.append(tuple(v[:3]) if v else (0.0, 0.0, 0.0))
        if cls["packed_ts"]:
            v = attr(cls["packed_ts"], i)
            TS.append((v[0], v[1]) if v else (0.0, 0.0))

    if any(t is None for t in T):
        # Tangents have to be built from *some* uv set, and a mesh that declares
        # none gets a flat one for the length of this call only - invented,
        # used, and thrown away.  Writing it out as a real layer of zeroes is how
        # a part ends up in Blender with a UV map that is one point, which looks
        # like a broken export rather than an honest "this mesh has no uvs".
        synth = UV[0] if UV else [(0.0, 0.0)] * n
        gen = generate_tangents(P, N, synth, sol["_inputs"]["idx"])
        T = [T[i] if T[i] is not None else gen[i] for i in range(n)]
        tan_source = "vertex buffer + generated" if tan_s is not None else "generated from UV0"
    else:
        tan_source = "vertex buffer"

    # how much to trust the game's normal stream: a packed decode that goes wrong
    # shows up immediately as non-unit normals.  A draw that never had a normal
    # stream is not a stream that decoded badly - it is reported as "no normal",
    # which is what tells build_scene to compute them instead.
    unit = sum(1 for v in N if abs(norm3(v) - 1.0) < 1e-3)
    normals_ok = bool(nrm_s) and ((unit / float(n)) > 0.999 if n else False)

    flags = (FLAG_ALT if ALT else 0) | (FLAG_TS if TS else 0)
    path = os.path.join(out_dir, "eid-%d.mesh2" % sol["eid"])
    write_mesh(path, n, len(UV), flags, P, N, T, UV, ALT, TS, sol["_inputs"]["idx"])
    return {"path": path, "uv_sets": [nm for nm, _ in cls["uvs"]], "nuv": len(UV),
            "flags": flags,
            "normal": ("none" if nrm_s is None else
                       "packed 10:10:10:2" if nrm_packed else "float3"),
            "normals_ok": normals_ok, "normals_unit_fraction": unit / float(n) if n else 0.0,
            "tangent": tan_source, "alt": bool(ALT), "ts": bool(TS)}


# ============================================================== world placement


def place_world(sol, profile, mesh2_path, out_dir, adapter=None, log=None):
    """Give one solved draw its place in the Blender scene.

    Two things are decided here and nowhere else, which is what keeps them
    consistent across a whole run:

    *The object's own matrix.*  The fit recovered ``A: model -> clip``, so
    ``Model = VP^-1 . A`` is the transform the draw was really submitted with -
    including for the parts whose object matrix never came from the constant
    buffer, because the fit absorbed whatever they used.  Writing it onto the
    object rather than into the vertices is what lets a scene and a character
    exported from the same capture stay in one another's coordinates, and lets a
    person move one part in Blender without the rest following.

    *The scene matrix.*  ``util.scene_matrix`` says where the captured world sits
    in Blender - the axis frame, the unit scale, the nudge - and the camera is
    placed through the very same one.  A mesh placed by one matrix and a camera
    by another is how a scene stops looking like the frame it came from.

    Geometry is written through the mirror rather than the transform carrying it,
    so no object ends up with a negative determinant, which Blender would draw
    inside out.  The two shapes are equivalent vertex for vertex: for every ``x``,
    ``(S . Model . F^-1) . (F . x) == S . Model . x``.

    With ``profile.scene["object_transforms"]`` off, everything is baked exactly
    as this tool has always baked it and every object comes out at the identity.
    It is on by default - the scene is *built* from world matrices and the camera
    is placed into it, rather than everything being expressed relative to a
    camera that the engine has already rebased the world onto.
    """
    from .util import read_mesh

    mesh = read_mesh(mesh2_path)
    Model = sol.get("model")
    F = frame_matrix(profile)
    F4 = mat4_from3(F)
    S = scene_matrix(profile)
    object_transforms = bool((getattr(profile, "scene", None) or {})
                             .get("object_transforms", True))
    rejected = False
    if sol.get("screen_space"):
        # Screen coordinates, not world ones.  `build_scene` puts the object in
        # the camera's own space, where the frame matrix has no business - and
        # the object matrix would be the inverse of the projection, which is not
        # an object transform at all.
        pos = [tuple(p[:3]) for p in mesh["pos"]]
        nrm = [tuple(v) for v in mesh["nrm"]]
        tan = [tuple(t) for t in mesh["tan"]]
        alt = [tuple(p) for p in mesh["alt"]] if mesh["flags"] & FLAG_ALT else []
        matrix = None
        path = os.path.join(out_dir, "eid-%d.world2" % sol["eid"])
        write_mesh(path, mesh["n"], mesh["nuv"], mesh["flags"], pos, nrm, tan,
                   mesh["uvs"], alt, mesh["ts"], mesh["idx"])
        return {"path": os.path.basename(path), "n": mesh["n"], "nidx": mesh["nidx"],
                "nuv": mesh["nuv"], "flags": mesh["flags"], "rms": sol["rms"],
                "mode": sol["mode"], "kind": sol.get("kind") or "skinned",
                "screen_space": True, "baked": True, "matrix": None}
    if object_transforms:
        candidate = mat4_mul(S, mat4_mul(as_mat4(Model), mat4_transpose(F4)))
        if not transform_ok(candidate):
            # The fit could not pin this draw's transform - too few well-spread
            # vertices, usually - and a degenerate matrix is not something an
            # object can carry.  Baking it leaves the part where the baked output
            # has always put it, which is at least the same place every run.
            object_transforms = False
            rejected = True
    if object_transforms:
        # The mirror moves off the transform and onto the geometry.  The mesh is
        # written as F.x rather than x, so the matrix that puts it back where the
        # baked output had it is S . Model . F^-1 - and because F is orthogonal,
        # F^-1 is F transposed, and the translation passes through untouched.
        # The determinant works out positive (S carries the mirror, F^-1 takes
        # it back out), which is what keeps Blender from drawing the object
        # inside out - the whole reason for moving the mirror rather than leaving
        # it in the object's matrix.
        pos = [frame_apply(F, p) for p in mesh["pos"]]
        nrm = [frame_apply(F, v) for v in mesh["nrm"]]
        tan = []
        for t in mesh["tan"]:
            d = frame_apply(F, t[:3])
            n = norm3(d) or 1.0
            tan.append((d[0] / n, d[1] / n, d[2] / n, t[3]))
        alt = [frame_apply(F, p) for p in mesh["alt"]] if mesh["flags"] & FLAG_ALT else []
        # S . Model . F^-1: the mirror taken back out of the transform, so the
        # object's own matrix stays proper and Blender keeps the faces the right
        # way round
        matrix = mat4_mul(S, mat4_mul(as_mat4(Model), mat4_transpose(F4)))
    else:
        us = float(getattr(profile, "unit_scale", 1.0) or 1.0)
        off = [float(v) for v in list((getattr(profile, "scene", None) or {})
                                      .get("offset") or [])[:3]]
        off = (off + [0.0, 0.0, 0.0])[:3]
        M3 = [row[:3] for row in Model[:3]]
        NM = [[inv3(M3)[j][i] for j in range(3)] for i in range(3)]

        def point(p):
            q = frame_apply(F, mat4_apply(Model, p))
            return (q[0] * us + off[0], q[1] * us + off[1], q[2] * us + off[2])

        def direction(v, mat):
            d = [sum(mat[i][j] * v[j] for j in range(3)) for i in range(3)]
            n = norm3(d) or 1.0
            return frame_apply(F, [c / n for c in d])

        pos = [point(p) for p in mesh["pos"]]
        nrm = [direction(v, NM) for v in mesh["nrm"]]
        tan = []
        for t in mesh["tan"]:
            d = direction(t[:3], M3)
            tan.append((d[0], d[1], d[2], t[3]))
        alt = [point(p) for p in mesh["alt"]] if mesh["flags"] & FLAG_ALT else []
        matrix = None

    path = os.path.join(out_dir, "eid-%d.world2" % sol["eid"])
    write_mesh(path, mesh["n"], mesh["nuv"], mesh["flags"], pos, nrm, tan,
               mesh["uvs"], alt, mesh["ts"], mesh["idx"])
    # the name only - a run has to survive being copied or renamed - and the
    # matrix rounded hard: it is a placement, and a run file that grows by a
    # thousand digits per part is a run file nobody can diff.
    return {"path": os.path.basename(path), "n": mesh["n"], "nidx": mesh["nidx"],
            "nuv": mesh["nuv"], "flags": mesh["flags"], "rms": sol["rms"],
            "mode": sol["mode"],
            "kind": sol.get("kind") or "skinned",
            "baked": rejected or matrix is None,
            "matrix": ([[round(v, 9) for v in row] for row in matrix]
                       if matrix else None)}
