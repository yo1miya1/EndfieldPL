# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.

"""Small pure-python helpers: linear algebra, binary mesh IO, run logging.

Deliberately dependency free - the system interpreter has no numpy, and the
solve stage is the part that must stay iterable without Blender around.
"""

import array
import json
import math
import os
import struct
import subprocess
import sys
import time


def utf8_console():
    """Make this process's own stdout/stderr carry UTF-8 whatever the code page.

    The tool's messages are Chinese.  On a console that is not set to 65001 -
    an English install, or a run redirected into a file - a stream that is not
    attached to a real console defaults to the locale code page, so those
    messages come out as `?`, or as mojibake in whatever reads the file next.
    The launchers do `chcp 65001`, but the tool must not depend on having been
    started by its own launcher.

    A real Windows console ignores this (it writes through WriteConsoleW and
    the console decides how to draw it); a pipe or a file honours it and gets
    the same UTF-8 the log files already use.  `errors="replace"` on top: one
    unprintable character is never worth losing a finished run over.
    """
    seen = []
    for name in ("stdout", "stderr", "__stdout__", "__stderr__"):
        stream = getattr(sys, name, None)
        if stream is None or any(stream is s for s in seen):
            continue
        seen.append(stream)
        try:
            # `reconfigure` is 3.7; on 3.6 there is nothing to call and the
            # console code page stands, which is what the launcher's
            # `chcp 65001` is for.
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# --------------------------------------------------------------------- algebra


def solve_ls(rows, rhs, n):
    """Least squares via normal equations.  `rows` is m x n, `rhs` is m.

    Gaussian elimination with partial pivoting; returns None when singular.
    """
    M = [[0.0] * n for _ in range(n)]
    v = [0.0] * n
    for r in range(len(rows)):
        row = rows[r]
        br = rhs[r]
        for i in range(n):
            ai = row[i]
            if ai == 0.0:
                continue
            v[i] += ai * br
            for k in range(i, n):
                M[i][k] += ai * row[k]
    for i in range(n):
        for k in range(i):
            M[i][k] = M[k][i]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i]))
        if abs(M[p][i]) < 1e-14:
            return None
        M[i], M[p] = M[p], M[i]
        v[i], v[p] = v[p], v[i]
        pv = M[i][i]
        for k in range(i, n):
            M[i][k] /= pv
        v[i] /= pv
        for r in range(n):
            if r != i and M[r][i] != 0.0:
                f = M[r][i]
                for k in range(i, n):
                    M[r][k] -= f * M[i][k]
                v[r] -= f * v[i]
    return v


def matmul4(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inv4(m):
    n = 4
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[p][i]) < 1e-14:
            raise ValueError("singular 4x4")
        a[i], a[p] = a[p], a[i]
        pv = a[i][i]
        a[i] = [v / pv for v in a[i]]
        for r in range(n):
            if r != i and a[r][i] != 0.0:
                f = a[r][i]
                a[r] = [a[r][k] - f * a[i][k] for k in range(2 * n)]
    return [row[n:] for row in a]


def inv3(m):
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    A = e * i - f * h
    B = -(d * i - f * g)
    C = d * h - e * g
    det = a * A + b * B + c * C
    if abs(det) < 1e-20:
        return [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    return [[A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
            [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
            [C / det, -(a * h - b * g) / det, (a * e - b * d) / det]]


def norm3(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def unit3(v):
    n = norm3(v) or 1.0
    return [v[0] / n, v[1] / n, v[2] / n]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


# ---------------------------------------------------------------- output frame

def frame_matrix(profile):
    """Game frame -> the frame everything is written in, as a 3x3.

    Two conventions a capture cannot state for itself, both profile settings:

      * ``left_handed`` - a D3D world mirrored on one axis is the right-handed
        world Blender draws in;
      * ``up_axis`` - Blender's up is +Z, so a Y-up or X-up engine needs a
        quarter turn.  It is a rotation rather than a sign flip, which is why
        this returns a matrix and not three multipliers: a rotation has to be
        applied to directions (normals, tangents, the camera's own axes) and
        positions alike, and it cannot be spelled as one sign per axis.

    Both defaults together (left-handed, Z-up) come out as the plain mirror on
    Y - the same transform this tool has always applied - so the settings are a
    way to adapt to the next engine, not a change of behaviour.  It is returned
    once, here, and every writer of geometry or camera data goes through it;
    a second copy of the mirror elsewhere is how the .blend camera and the mesh
    drift apart.
    """
    fl = (1.0, -1.0, 1.0) if getattr(profile, "left_handed", True) else (1.0, 1.0, 1.0)
    flip = [[fl[0], 0.0, 0.0], [0.0, fl[1], 0.0], [0.0, 0.0, fl[2]]]
    up = (getattr(profile, "up_axis", "z") or "z").strip().lower()
    if up == "y":                       # +Y becomes +Z: (x, y, z) -> (x, -z, y)
        rot = [[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]
    elif up == "x":                     # +X becomes +Z: (x, y, z) -> (-y, x, z)
        rot = [[0.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]
    else:                               # "z", or anything unrecognised: Blender's own up
        rot = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    return [[sum(rot[i][k] * flip[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


def frame_apply(mat, v):
    """A point or direction through `frame_matrix` - both use the same product;
    the translation is applied by the caller, before this, in the game frame."""
    return (sum(mat[0][j] * v[j] for j in range(3)),
            sum(mat[1][j] * v[j] for j in range(3)),
            sum(mat[2][j] * v[j] for j in range(3)))


# --------------------------------------------------------------- 4x4 plumbing
#
# Written out by hand rather than pulled from a library: this module is imported
# by the head-less driver inside qrenderdoc, which has nothing but the standard
# library, and by the CLI, which deliberately carries no dependencies either.


def mat4_identity():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def mat4_from3(m3, translate=(0.0, 0.0, 0.0)):
    """A 3x3 rotation/scale plus a translation, as one 4x4."""
    return [[m3[i][0], m3[i][1], m3[i][2], float(translate[i])] for i in range(3)] + \
           [[0.0, 0.0, 0.0, 1.0]]


def as_mat4(m):
    """Anything matrix-shaped -> a 4x4.

    `Adapter.model_transform` hands back a 4x4 and always has; a 3x4 is what a
    caller assembling one by hand tends to write, and the difference is a bottom
    row no multiplication can miss.  Accepting both here is cheaper than a rule
    about which one is allowed.
    """
    rows = [[float(v) for v in row[:4]] for row in m[:4]]
    if len(rows) == 3:
        return rows + [[0.0, 0.0, 0.0, 1.0]]
    if len(rows) == 4:
        for row in rows:
            while len(row) < 4:
                row.append(0.0)
        rows[3][3] = 1.0
        return rows
    raise ValueError("not a matrix: %r" % (m,))


def mat4_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
            for i in range(4)]


def mat4_transpose(m):
    return [[m[j][i] for j in range(4)] for i in range(4)]


def mat4_apply(m, v):
    """A point through a 4x4 (w is assumed to be 1 and is not divided out)."""
    return tuple(sum(m[i][k] * v[k] for k in range(3)) + m[i][3] for i in range(3))


def mat4_apply_dir(m, v):
    """A direction through a 4x4 - the translation is ignored."""
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def mat4_scale_translate(scale, translate=(0.0, 0.0, 0.0)):
    m = mat4_identity()
    for i in range(3):
        m[i][i] = float(scale)
        m[i][3] = float(translate[i])
    return m


def is_proper(m, tol=1e-6):
    """True when a 4x4 has no mirror in it - what Blender needs of an object."""
    a = [[m[i][j] for j in range(3)] for i in range(3)]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
           - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    return det > tol


def is_affine(m, tol=1e-6):
    """True when a 4x4 maps points to points - no projective division left in it.

    This is how a draw that was *not* rendered with the camera this run recovered
    is caught.  The solver gets an object's transform as ``VP^-1 . A``, where `A`
    is what the fit found maps the mesh to the positions the vertex shader wrote.
    When both came from the same view-projection the result is the object's own
    affine transform, whatever it is - scaled, sheared, mirrored, anything.  When
    they did not - a shadow pass drawn under the light's matrix, a reflection, a
    thumbnail render - the inverse of one projection is multiplied into the other
    and the answer is a projective matrix: its last row picks up entries in the
    first three columns, and there is no object transform in there to recover.

    The last *component* is a different matter.  A matrix ``k.M`` is the same map
    as ``M`` - the homogeneous divide cancels the k - so a last row of
    ``[0, 0, 0, k]`` is an ordinary object transform wearing a scale it does not
    need, and `normalise_affine` takes it off.  Requiring 1 here instead made the
    tool reject a whole frame's worth of perfectly good geometry the first time it
    met a shader that wrote its clip positions pre-scaled.
    """
    return (abs(m[3][0]) <= tol and abs(m[3][1]) <= tol and abs(m[3][2]) <= tol
            and abs(m[3][3]) > tol)


def normalise_affine(m):
    """`m` with its last component scaled away, so the bottom row is [0, 0, 0, 1]."""
    k = m[3][3]
    if not k or abs(k - 1.0) <= 1e-12:
        return [list(row) for row in m]
    return [[v / k for v in row] for row in m]


def transform_ok(m, tol=1e-6):
    """True when a 4x4 is a usable object transform.

    Two things make one unusable, and both happen: every number has to be finite,
    and the matrix must not be degenerate.  A degenerate one comes out of the
    least-squares fit when a draw has too few well-spread vertices for the fit to
    pin a scale - a two-triangle effect card, say - and a zero in the scale is
    not something Blender or an FBX node can carry: the object collapses, and in
    the FBX the collapse is written as a `Lcl Scaling` of zero that no reader
    recovers from.  Such a part is better baked than placed.
    """
    for row in m:
        for v in row:
            if not math.isfinite(v):
                return False
    a = [[m[i][j] for j in range(3)] for i in range(3)]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
           - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    n = max(norm3(a[0]), norm3(a[1]), norm3(a[2]))
    return n > tol and abs(det) > tol * n * n * n


def conj4(frame, m):
    """``frame . m . frame^-1`` - the same transform, expressed in a frame
    reached by applying `frame` first.

    A frame that mirrors - and the usual left-handed-to-Blender one does - cannot
    be folded into an object's own matrix without giving that object a negative
    determinant, which Blender draws with the faces turned inside out.  Mirroring
    the *geometry* instead and conjugating the transform by the mirror leaves the
    product identical: ``F.M.x == (F.M.F^-1).(F.x)``.  Every matrix on the way
    then keeps the determinant the game gave it, so an object transform stays
    something Blender is happy with.  `frame` must be orthogonal, which
    `frame_matrix` always is - that is what makes its transpose its inverse, and
    the translation survives the conjugation untouched.
    """
    f = as_mat4(frame)
    return mat4_mul(mat4_mul(f, as_mat4(m)), mat4_transpose(f))


# ------------------------------------------------------------- scene placement

def scene_matrix(profile):
    """Game world -> the Blender scene, as a 4x4.

    The one matrix that says where the captured world sits in Blender: the axis
    frame (`frame_matrix`), the unit scale, and an optional nudge.  It is applied
    to every exported object *and* to the camera, from one place - which is the
    whole point, because a mesh placed by one matrix and a camera by another is
    how a scene stops looking like the frame it was recovered from.

    ``profile.scene["matrix"]``, when set, replaces the derived one outright: a
    capture whose world wants a transform this tool cannot guess gets to say so,
    and nothing else has to change.
    """
    scene = getattr(profile, "scene", None) or {}
    custom = scene.get("matrix")
    if custom and len(custom) == 4 and all(len(row) >= 4 for row in custom):
        return [[float(v) for v in row[:4]] for row in custom]
    us = float(getattr(profile, "unit_scale", 1.0) or 1.0)
    off = [float(v) for v in list(scene.get("offset") or [])[:3]]
    off = (off + [0.0, 0.0, 0.0])[:3]
    # translation last: the frame turns the world, the scale sets its size, and
    # the offset then moves the result - so an offset typed by a user means the
    # same thing whatever the capture's own axes are.
    return mat4_mul(mat4_scale_translate(us, off),
                    mat4_from3(frame_matrix(profile)))


def decompose4(m):
    """(translation, euler_xyz_degrees, scale, shear) for a 4x4.

    Gram-Schmidt, because the only consumer is the FBX writer, whose Model node
    can carry a translation, an XYZ Euler rotation and a per-axis scale and
    nothing else.  `shear` is how much of the matrix that decomposition cannot
    represent, measured against each column's own length; a caller that finds it
    non-zero has to bake the matrix into the vertices rather than drop it
    silently.
    """
    t = [float(m[i][3]) for i in range(3)]
    cols = [[float(m[i][j]) for i in range(3)] for j in range(3)]
    shear = 0.0
    axes, scales = [], []
    for j in range(3):
        c = cols[j]
        for k in range(j):
            d = sum(axes[k][i] * c[i] for i in range(3))
            shear = max(shear, abs(d))
            c = [c[i] - d * axes[k][i] for i in range(3)]
        n = norm3(c) or 1.0
        axes.append([v / n for v in c])
        scales.append(n)
    det = (axes[0][0] * (axes[1][1] * axes[2][2] - axes[1][2] * axes[2][1])
           - axes[0][1] * (axes[1][0] * axes[2][2] - axes[1][2] * axes[2][0])
           + axes[0][2] * (axes[1][0] * axes[2][1] - axes[1][1] * axes[2][0]))
    if det < 0.0:
        # a mirror.  FBX can only say that as one negative axis, and one is
        # exactly what it is.
        axes[2] = [-v for v in axes[2]]
        scales[2] = -scales[2]
    r = [[axes[j][i] for j in range(3)] for i in range(3)]
    # R = Rz(g).Ry(b).Rx(a): what FBX's RotationOrder 0 means, and what
    # Blender's Euler((a, b, g), "XYZ").to_matrix() builds
    if abs(r[2][0]) < 1.0 - 1e-9:
        b = math.asin(max(-1.0, min(1.0, -r[2][0])))
        a = math.atan2(r[2][1], r[2][2])
        g = math.atan2(r[1][0], r[0][0])
    else:                                   # gimbal lock: fold g into a
        b = math.pi / 2.0 if r[2][0] <= -1.0 else -math.pi / 2.0
        a = math.atan2(-r[1][2], r[1][1])
        g = 0.0
    return t, [math.degrees(a), math.degrees(b), math.degrees(g)], scales, shear


# ------------------------------------------------------- child process hygiene

def no_console():
    """Keyword arguments that keep a child process from owning a console.

    On Windows a console program started by a program that has no console of its
    own - and the launcher starts the GUI with `pythonw`, so it has none - gets a
    brand new console allocated for it.  That is a black window appearing behind
    the tool, and closing it is not harmless: Windows sends CTRL_CLOSE_EVENT, and
    the child dies with `0xC000013A` (STATUS_CONTROL_C_EXIT) halfway through
    whatever it was doing.  A run that fails this way looks like a Blender crash
    and is really somebody tidying up a stray window.

    `CREATE_NO_WINDOW` says "run this without a console at all", which is what
    every child this tool starts wants: they are all either piped
    (`capture_output`) or windowless by design.
    """
    if os.name != "nt":
        return {}
    return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}


#: Windows NTSTATUS values that are not failures of the program but of the way it
#: was started or stopped.  Worth naming, because the number alone says nothing.
_EXIT_NOTES = {
    3221225786: "0xC000013A: killed by Ctrl+C, or the console window it had was "
                "closed.  Children are started with CREATE_NO_WINDOW so this "
                "should not happen - if it does, something else is signalling it",
    3221225725: "0xC00000FD: ran out of stack - a mesh with an absurd number of "
                "vertices?",
    3221225477: "0xC0000005: access violation inside the program",
    3221226505: "0xC0000409: stack buffer overrun / fail-fast",
}


def exit_note(code):
    """A sentence about a process exit code, or "" when it speaks for itself."""
    try:
        return _EXIT_NOTES.get(int(code), "")
    except (TypeError, ValueError):
        return ""


# ---------------------------------------------------------- per-draw dump files
#
# What the probe hands the solver about one draw call.  It used to be JSON, and
# JSON was the single most expensive thing in the collect phase: a 218-draw run
# wrote 31 MB of it, one text-formatted number at a time, and the solver then
# parsed all 31 MB back into lists before it could fit anything.
#
# The layout below is fixed-width, little-endian and self-describing enough to
# read back in one pass.  `w` counts nothing - it is padding, so the header is a
# round 40 bytes and the blocks start aligned.
#
#   header  4s "RDCI" | u32 version | u32 n | u32 need | u32 pstride
#           u32 vstride | u32 nidx | u32 reserved
#   bind    f32 [n][3]        the model-space position, read as declared
#   posed   f32 [need][4]     what the vertex shader wrote (clip space)
#   bidx    u32 [need][4]     the four bone indices
#   wts     f32 [need][4]     the four weights, as the shader will read them
#   idx     u32 [nidx]        the draw's own indices, counted from zero

INPUTS_MAGIC = b"RDCI"
INPUTS_VERSION = 1
_INPUTS_HDR = "<4sIIIIIII"


def _f32(values):
    a = array.array("f", values)
    if sys.byteorder != "little":
        a.byteswap()
    return a.tobytes()


def _f64(values):
    a = array.array("d", values)
    if sys.byteorder != "little":
        a.byteswap()
    return a.tobytes()


def _u32(values):
    a = array.array("I", values)
    if sys.byteorder != "little":
        a.byteswap()
    return a.tobytes()


def _flat(rows):
    out = []
    for r in rows:
        out.extend(r)
    return out


def write_inputs(path, eid, n, need, pstride, vstride, bind, posed, bidx, wts, idx):
    """Write one draw's dump.  Returns the path.

    The blocks are packed with `array`, which converts a list of numbers to bytes
    in C - the difference against `json.dump` is most of the collect phase's
    Python time, because the alternative formats every float as text.

    `n` and `need` are not the same number and the layout depends on both: the
    per-vertex blocks (`bind`, `bidx`, `wts`) hold one row for every vertex the
    probe dumped - `n`, which is `need` plus the pad that lets a draw read a
    whole attribute past its last vertex - while `posed` holds only the vertices
    the draw actually uses, and the indices are their own count.  Reading them
    back with the wrong one walks off the end of a block into the next.

    The width of a skin row is *not* fixed either, so it is written down.  A
    four-bone skin is the common shape but a two-bone one is just as legal - the
    solver reads however many weights a vertex has, and indexes the bone array
    with the same count - and assuming four there made a two-bone draw's rows
    four wide on the way back in, which is a block that no longer lines up with
    anything after it.

    The floats are stored at full width, not as the 32-bit values they mostly
    came from.  Some of them no longer are: a weight is renormalised on the way
    out of the vertex buffer, and a `unorm` attribute is a division, so both
    carry bits a float32 would round away - and the palette search compares
    residuals five orders of magnitude apart, so it is not a rounding error
    anywhere but in the one place it decides something.
    """
    cols = len(bidx[0]) if len(bidx) else 4
    # A ragged block would be written flat and read back sliced, so the file
    # would be internally consistent and wrong.  Refusing here costs one draw and
    # names it; the alternative costs a solve that walks off the end of `wts`.
    for name, rows in (("bind", bind), ("bidx", bidx), ("wts", wts)):
        widths = sorted(set(len(r) for r in rows))
        if len(widths) > 1:
            raise ValueError("draw %s: %s rows have %s elements - a block has to "
                             "be one width to be read back" % (eid, name, widths))
        if name != "bind" and rows and widths[0] != cols:
            raise ValueError("draw %s: %s rows are %d wide but bidx is %d - the "
                             "skin columns have to match"
                             % (eid, name, widths[0], cols))
    head = struct.pack(_INPUTS_HDR, INPUTS_MAGIC, INPUTS_VERSION, int(n), int(need),
                       int(pstride), int(vstride), len(idx), cols)
    with open(path, "wb") as f:
        f.write(head)
        f.write(_f64(_flat(bind)))
        f.write(_f64(_flat(posed)))
        f.write(_u32(_flat(bidx)))
        f.write(_f64(_flat(wts)))
        f.write(_u32(list(idx)))
    return path


def _read_blocks(f, count, per, code):
    a = array.array(code)
    want = int(count) * int(per)
    if want <= 0:
        return []
    a.frombytes(f.read(want * a.itemsize))
    if sys.byteorder != "little":
        a.byteswap()
    return a


def _rows(flat, per):
    """Slice a flat block into per-vertex rows.

    The slice is taken in C, so shaping a whole draw costs well under a
    millisecond per hundred thousand numbers - far less than the nested Python
    lists `json.load` builds for the same data, and a fraction of the memory.
    """
    return [flat[i:i + per] for i in range(0, len(flat), per)]


def read_inputs(path):
    """One draw's dump, in exactly the shape `inputs.json` used to have.

    Every block is a list of rows - `bind[i]` is three floats, `posed[i]` and
    `wts[i]` are four - so the solver indexes it the same way whichever of the
    two files it was handed.  Only `idx` stays flat, as it always was.
    """
    with open(path, "rb") as f:
        head = f.read(struct.calcsize(_INPUTS_HDR))
        magic, ver, n, need, pstride, vstride, nidx, cols = \
            struct.unpack(_INPUTS_HDR, head)
        if magic != INPUTS_MAGIC:
            raise ValueError("not a draw dump: %s" % path)
        if ver != INPUTS_VERSION:
            raise ValueError("draw dump version %d, expected %d"
                             % (ver, INPUTS_VERSION))
        # a dump written before the column count was recorded is four-wide, which
        # is what every engine seen so far uses and what the reader used to assume
        cols = int(cols) or 4
        bind = _rows(_read_blocks(f, n, 3, "d"), 3)
        posed = _rows(_read_blocks(f, need, 4, "d"), 4)
        # `n`, not `need`: the skin streams carry the padding rows too, and the
        # weights of a vertex past the last index are still read by the shader
        bidx = _rows(_read_blocks(f, n, cols, "I"), cols)
        wts = _rows(_read_blocks(f, n, cols, "d"), cols)
        idx = _read_blocks(f, nidx, 1, "I")
    return {"n": int(n), "need": int(need), "pstride": int(pstride),
            "vstride": int(vstride), "bind": bind, "posed": posed,
            "bidx": bidx, "wts": wts, "idx": idx, "skin_cols": cols}


def read_posed(path):
    """Just the clip-space block - what `behind_the_eye` needs, and nothing else."""
    with open(path, "rb") as f:
        head = f.read(struct.calcsize(_INPUTS_HDR))
        magic, _ver, n, need, _ps, _vs, _ni, _ = struct.unpack(_INPUTS_HDR, head)
        if magic != INPUTS_MAGIC:
            raise ValueError("not a draw dump: %s" % path)
        f.seek(struct.calcsize(_INPUTS_HDR) + int(n) * 3 * 8)
        return _read_blocks(f, need, 4, "d")


# ------------------------------------------------------------------- raw bytes


def read_f4(path):
    """Return (raw, [float4, ...]) for a dumped constant buffer."""
    raw = open(path, "rb").read()
    return raw, [struct.unpack_from("<4f", raw, i * 16) for i in range(len(raw) // 16)]


def u32(raw, off):
    return struct.unpack_from("<I", raw, off)[0]


# ------------------------------------------------------- packed normal decoding

PACKED_SCALE = 2.0 / 1023.0


def signed10(v):
    v &= 0x3FF
    return v - 1024 if v >= 512 else v


def octahedral_decode(x, y):
    if (1.0 - abs(x)) - abs(y) < 0.0:
        x = (1.0 - abs(y)) * (1.0 if x >= 0.0 else -1.0)
        y = (1.0 - abs(x)) * (1.0 if y >= 0.0 else -1.0)
    z2 = 1.0 - x * x - y * y
    return (x, y, math.sqrt(z2) if z2 > 0.0 else 0.0)


def decode_packed_normal(raw, off):
    """10:10:10:2 little endian octahedral word -> (normal, handedness)."""
    word = struct.unpack_from("<I", raw, off)[0]
    z = signed10(word) * PACKED_SCALE
    x = signed10(word >> 10) * PACKED_SCALE
    y = signed10(word >> 20) * PACKED_SCALE
    n = octahedral_decode(x, y)
    return n, (1.0 if (word >> 31) & 1 else -1.0)


def read_comps(raw, off, spec):
    """Read one vertex attribute per its declared format."""
    cw, nc, ct = spec["cbyte"], spec["comps"], spec["ctype"].lower()
    out = []
    for k in range(nc):
        o = off + k * cw
        if o + cw > len(raw):
            out.append(0.0)
            continue
        if "unorm" in ct:
            out.append(raw[o] / 255.0 if cw == 1
                       else struct.unpack_from("<H", raw, o)[0] / 65535.0)
        elif "snorm" in ct:
            out.append(max(struct.unpack_from("<b", raw, o)[0] / 127.0, -1.0) if cw == 1
                       else max(struct.unpack_from("<h", raw, o)[0] / 32767.0, -1.0))
        elif "uint" in ct:
            out.append({1: lambda b: b[0],
                        2: lambda b: struct.unpack_from("<H", b, 0)[0],
                        4: lambda b: struct.unpack_from("<I", b, 0)[0]}[cw](raw[o:o + cw]))
        elif "sint" in ct:
            out.append({1: lambda b: struct.unpack_from("<b", b, 0)[0],
                        2: lambda b: struct.unpack_from("<h", b, 0)[0],
                        4: lambda b: struct.unpack_from("<i", b, 0)[0]}[cw](raw[o:o + cw]))
        else:
            out.append(struct.unpack_from("<e", raw, o)[0] if cw == 2
                       else struct.unpack_from("<f", raw, o)[0])
    return out


# ------------------------------------------------------------------ mesh files
#
#   u32 nverts, nidx, nuv, flags
#   f32 pos[3n]
#   f32 nrm[3n]
#   f32 tan[4n]                 xyz + handedness
#   f32 uv[nuv][2n]
#   f32 alt[3n]                 if flags & 1   (secondary position stream)
#   f32 ts[2n]                  if flags & 2   (game tangent-space direction)
#   u32 idx[nidx]

FLAG_ALT = 1
FLAG_TS = 2


def write_mesh(path, n, nuv, flags, pos, nrm, tan, uvs, alt, ts, idx):
    with open(path, "wb") as f:
        f.write(struct.pack("<IIII", n, len(idx), nuv, flags))
        f.write(struct.pack("<%df" % (3 * n), *[c for p in pos for c in p]))
        f.write(struct.pack("<%df" % (3 * n), *[c for v in nrm for c in v]))
        f.write(struct.pack("<%df" % (4 * n), *[c for v in tan for c in v]))
        for layer in uvs:
            f.write(struct.pack("<%df" % (2 * n), *[c for v in layer for c in v]))
        if flags & FLAG_ALT:
            f.write(struct.pack("<%df" % (3 * n), *[c for v in alt for c in v]))
        if flags & FLAG_TS:
            f.write(struct.pack("<%df" % (2 * n), *[c for v in ts for c in v]))
        f.write(struct.pack("<%dI" % len(idx), *idx))


def read_mesh(path):
    with open(path, "rb") as f:
        n, nidx, nuv, flags = struct.unpack("<IIII", f.read(16))

        def arr(cnt, per):
            return [struct.unpack("<%df" % per, f.read(4 * per)) for _ in range(cnt)]

        pos = arr(n, 3)
        nrm = arr(n, 3)
        tan = arr(n, 4)
        uvs = [arr(n, 2) for _ in range(nuv)]
        alt = arr(n, 3) if flags & FLAG_ALT else []
        ts = arr(n, 2) if flags & FLAG_TS else []
        idx = list(struct.unpack("<%dI" % nidx, f.read(4 * nidx)))
    return {"n": n, "nidx": nidx, "nuv": nuv, "flags": flags, "pos": pos, "nrm": nrm,
            "tan": tan, "uvs": uvs, "alt": alt, "ts": ts, "idx": idx}


# ------------------------------------------------------------------ run logging


class RunLog:
    """Console + text file + JSON report for one command.

    Every line goes through `_emit`, which can:
      * print it (stdout - deliberately not stderr, so a redirecting front end
        never misses a warning),
      * tag it with a level marker the GUI strips to colour the line,
      * append it to a plain text log next to the output.
    """

    # set by the GUI: when true each line carries a "\x01<LEVEL>" prefix
    tag_levels = False
    LEVEL_TAG = {"step": "\x01S", "ok": "\x01O", "warn": "\x01W", "err": "\x01E",
                 "dim": "\x01D", "info": ""}

    def __init__(self, path=None, quiet=False, text_path=None):
        self.path = path
        self.quiet = quiet
        self.data = {}
        self.t0 = time.time()
        self.text_path = text_path
        self._fh = None
        if text_path:
            d = os.path.dirname(os.path.abspath(text_path))
            if d:
                os.makedirs(d, exist_ok=True)
            self._fh = open(text_path, "a", encoding="utf-8", buffering=1)
            from . import paths
            self._write_raw("# %s log  %s"
                            % (paths.PACKAGE_NAME, time.strftime("%Y-%m-%d %H:%M:%S")))

    # ------------------------------------------------------------------ output
    def _write_raw(self, text):
        if self._fh:
            self._fh.write(text + "\n")

    def _emit(self, text, level="info"):
        if self.tag_levels and level != "info":
            print(self.LEVEL_TAG.get(level, "") + text)
        elif not self.quiet:
            print(text)
        stamp = time.strftime("%H:%M:%S")
        self._write_raw("[%s] %s" % (stamp, text))

    def section(self, name):
        self._emit("== %s ==" % name, "step")

    def info(self, msg, **kv):
        extra = ("  " + " ".join("%s=%s" % (k, v) for k, v in kv.items())) if kv else ""
        self._emit("   %s%s" % (msg, extra))

    def dim(self, msg):
        self._emit(msg, "dim")

    def ok(self, msg, **kv):
        extra = ("  " + " ".join("%s=%s" % (k, v) for k, v in kv.items())) if kv else ""
        self._emit("   + %s%s" % (msg, extra), "ok")

    def warn(self, msg):
        self._emit("   ! %s" % msg, "warn")

    def fail(self, msg):
        self._emit("   x %s" % msg, "err")
        raise RuntimeError(msg)

    def put(self, key, value):
        self.data[key] = value

    def close(self):
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data["_elapsed_s"] = round(time.time() - self.t0, 2)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1, default=str)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def relpath(base, path):
    """Store paths inside a run relative to the run, so the run can be moved."""
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return path


def resolve(base, path):
    """Inverse of relpath.

    Absolute paths from an older or relocated run are re-rooted under `base` by
    matching their longest suffix that actually exists there, so copying a run
    elsewhere does not break it.
    """
    if not path:
        return path
    if not os.path.isabs(path):
        return os.path.normpath(os.path.join(base, path))
    if os.path.exists(path):
        return path
    parts = os.path.normpath(path).split(os.sep)
    for k in range(len(parts), 0, -1):
        cand = os.path.join(base, *parts[-k:])
        if os.path.exists(cand):
            return cand
    return path


def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
