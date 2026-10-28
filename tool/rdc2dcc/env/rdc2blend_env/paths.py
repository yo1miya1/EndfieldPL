# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.
"""Every path, and every external executable, is resolved here - never written
into the code.

Importing this module pulls in nothing but the standard library, so it loads
from the CLI, from the Tkinter front end and from inside qrenderdoc alike.

Package directory
    Derived from this file's own location, so renaming the folder, moving it to
    another drive, or installing under a different user account all just work.
    The package *name* is read off that same directory instead of being written
    down, which is what lets ``rdc2blend`` and ``rdc2blenderGUI`` sit side by
    side without colliding.

Inside the package
    ``profiles/``, ``scripts/`` and the head-less driver are all located
    relative to the package directory, never by absolute path.

User configuration
    ``%APPDATA%\\rdc2blend\\settings.json`` (``$XDG_CONFIG_HOME`` elsewhere),
    holding the remembered output folder, Blender path and so on.  It lives in
    the config directory rather than next to the code so that a shared or
    read-only install still works.

External tools
    RenderDoc and Blender are *located*, never assumed:

        qrenderdoc.exe   explicit -> $RDC2BLEND_QRENDERDOC -> running host
                         -> registry / App Paths -> usual install roots -> PATH
        blender.exe      explicit -> $RDC2BLEND_BLENDER -> registry / App Paths
                         -> usual install roots -> PATH

    "usual install roots" includes both ``<root>/Blender Foundation/Blender 5.2/``
    and a Blender unpacked straight into ``<root>/Blender/``, at any drive - the
    two layouts people actually end up with.
"""

import glob
import json
import os
import re
import shutil
import string
import subprocess
import sys
from typing import Optional

# --------------------------------------------------------------- package folder

#: directory holding this package (…/rdc2blend or …/rdc2blenderGUI)
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

#: its parent - what goes on sys.path so `-m <name>` and the driver can import us
PACKAGE_ROOT = os.path.dirname(PACKAGE_DIR)

#: "rdc2blend" or "rdc2blenderGUI" - the product name, taken from the directory
PACKAGE_NAME = os.path.basename(PACKAGE_DIR)

PROFILES_DIR = os.path.join(PACKAGE_ROOT, "profiles")
SCRIPTS_DIR = os.path.join(PACKAGE_DIR, "scripts")
DRIVER = os.path.join(PACKAGE_DIR, "rdc_driver.py")

#: Blender releases this tool is written against; older ones are reported but not
#: refused, because the FBX/engine differences are already adapted for per call.
MIN_BLENDER = (4, 2)

_ENV_QRENDERDOC = "RDC2BLEND_QRENDERDOC"
_ENV_BLENDER = "RDC2BLEND_BLENDER"
_ENV_OUT = "RDC2BLEND_OUT"
_ENV_PROFILE = "RDC2BLEND_PROFILE"


# ------------------------------------------------------------------- config dir

def config_dir() -> str:
    """Per-user config directory - created on demand, never inside the package.

    One directory for both front ends, deliberately: the remembered output
    folder and Blender path are about the machine, not about which face of the
    tool you happen to have opened.  The name is fixed for the same reason the
    ``RDC2BLEND_*`` variables are - it is a location users may have pointed at
    before, not a label this build gets to rename.
    """
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "rdc2blend")


def config_file() -> str:
    return os.path.join(config_dir(), "settings.json")


def load_config() -> dict:
    """Remembered settings, or an empty dict.  Never raises."""
    try:
        with open(config_file(), encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(**values) -> dict:
    """Merge `values` into the remembered settings.  Never raises."""
    cfg = load_config()
    cfg.update(dict((k, v) for k, v in values.items() if v is not None))
    try:
        os.makedirs(config_dir(), exist_ok=True)
        with open(config_file(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return cfg


def config_value(key, default=None):
    """One remembered setting, with an environment override for scripted runs."""
    env = {"out": _ENV_OUT, "profile": _ENV_PROFILE}.get(key)
    if env:
        v = (os.environ.get(env) or "").strip()
        if v:
            return v
    return load_config().get(key, default)


# ------------------------------------------------------------- default targets

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_stem(name: str) -> str:
    """Make a capture's file name usable as a file/folder stem."""
    stem = _ILLEGAL.sub("_", (name or "").strip()).strip(" .")
    return stem or ""


def default_out_dir(capture: Optional[str] = None, remembered: bool = True) -> str:
    """Where a run writes when the user did not say.

    Next to the capture, named after it - derived from the input rather than
    written down, so it is right on any machine and for any capture.  Without a
    capture, a folder in the user's home.  `remembered=False` ignores the saved
    preference, for the caller that wants "what would this capture get".
    """
    if remembered:
        saved = config_value("out")
        if saved:
            return os.path.abspath(os.path.expanduser(saved))
    if capture:
        cap = os.path.abspath(capture)
        stem = safe_stem(os.path.splitext(os.path.basename(cap))[0])
        if stem:
            return os.path.join(os.path.dirname(cap), stem + "_out")
    return os.path.join(os.path.expanduser("~"), PACKAGE_NAME + "-out")


def default_blend_name(capture: Optional[str] = None) -> str:
    """The .blend file name, following the capture instead of a fixed label.

    No suffix: what this tool writes is a 3D scene, so `_posed3d` was saying the
    obvious and getting in the way of every reference to the file afterwards.
    """
    stem = safe_stem(os.path.splitext(os.path.basename(capture or ""))[0])
    return "%s.blend" % stem if stem else "scene.blend"


def default_profile_path() -> Optional[str]:
    """The solver table this build falls back to, or None when there is none.

    A solver is a folder under `solvers/` holding its identity and its constants
    together; the built-in one is `solvers/endfield/solver.json`.  `profiles/` is
    where a *user's* overrides live and is not consulted here - one shipped copy
    of the constants, in the pack, is the whole point.
    """
    p = os.path.join(PACKAGE_DIR, "solvers", "endfield", "solver.json")
    return p if os.path.exists(p) else None


def profile_names() -> list:
    """Every solver shipped next to the code, as bare names."""
    out = []
    d = os.path.join(PACKAGE_DIR, "solvers")
    try:
        for n in sorted(os.listdir(d)):
            if n.startswith("_") or n.startswith("."):
                continue
            if os.path.isfile(os.path.join(d, n, "solver.json")):
                out.append(n)
    except Exception:
        pass
    return out


def profile_for_adapter(adapter: Optional[str]) -> Optional[str]:
    """The solver table shipped for a solver, or None when there is no such pack.

    A solver is half code and half constants, and picking one without the other
    gets a camera read out of the wrong block - so a front end that offers the
    solver list offers the table that goes with it.  The built-in one keeps the
    name it has always answered to.
    """
    from .adapters import Adapter, resolve_adapter_name
    name = resolve_adapter_name(adapter)
    names = [name] if name != Adapter.name else ["endfield", "default"]
    for n in names:
        for cand in (os.path.join(PACKAGE_DIR, "solvers", n, "solver.json"),
                     os.path.join(PROFILES_DIR, "%s.json" % n)):
            if os.path.exists(cand):
                return cand
    return None


def ensure(path: str) -> str:
    """mkdir -p, returning the path.  Never raises."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


# --------------------------------------------------------- executable plumbing

def _app_paths(exe_name: str) -> list:
    """Windows `App Paths\\<exe>` registrations - what the installers write."""
    if os.name != "nt":
        return []
    try:
        import winreg
    except Exception:
        return []
    sub = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s" % exe_name
    out = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (0, getattr(winreg, "KEY_WOW64_32KEY", 0),
                     getattr(winreg, "KEY_WOW64_64KEY", 0)):
            try:
                with winreg.OpenKey(hive, sub, 0,
                                    winreg.KEY_READ | view) as k:
                    val = winreg.QueryValue(k, None)
            except Exception:
                continue
            if val:
                out.append(os.path.expandvars(val.strip('"')))
    return out


_DRIVE_CACHE = None


def drive_roots() -> list:
    """Existing drive roots, discovered - never a fixed list of letters."""
    global _DRIVE_CACHE
    if _DRIVE_CACHE is not None:
        return _DRIVE_CACHE
    if os.name != "nt":
        _DRIVE_CACHE = ["/"]
        return _DRIVE_CACHE
    roots = []
    for letter in string.ascii_uppercase:
        if letter in "AB":               # floppy letters can block for seconds
            continue
        root = "%s:\\" % letter
        try:
            if os.path.isdir(root):
                roots.append(root)
        except Exception:
            continue
    _DRIVE_CACHE = roots
    return roots


def install_roots() -> list:
    """Places an application is likely to have been unpacked into."""
    out = []
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)",
                "ProgramFiles(x86)", "SystemDrive"):
        v = os.environ.get(var)
        if v:
            out.append(v if v.endswith(os.sep) else v + os.sep)
    out.append(r"C:\Program Files")
    out.append(r"C:\Program Files (x86)")
    out.extend(drive_roots())
    seen, uniq = set(), []
    for r in out:
        r = os.path.normpath(r)
        if r.lower() not in seen and os.path.isdir(r):
            seen.add(r.lower())
            uniq.append(r)
    return uniq


def _glob_candidates(patterns, roots) -> list:
    found = []
    for root in roots:
        for pat in patterns:
            try:
                found.extend(glob.glob(os.path.join(root, pat)))
            except (OSError, re.error):
                # an unreadable directory, or a malformed pattern: neither says
                # anything about the other roots, so keep looking.  Anything
                # else is a bug here and must not be swallowed - a missing
                # import once made every search return nothing, silently.
                continue
    return [os.path.normpath(p) for p in found if os.path.isfile(p)]


def _dedupe(paths) -> list:
    seen, out = set(), []
    for p in paths:
        if not p:
            continue
        p = os.path.abspath(os.path.expanduser(p))
        key = os.path.normcase(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# ------------------------------------------------------------------- renderdoc

QRENDERDOC_PATTERNS = (
    "RenderDoc/qrenderdoc.exe",
    "Program Files/RenderDoc/qrenderdoc.exe",
    "Program Files (x86)/RenderDoc/qrenderdoc.exe",
    "Tool/RenderDoc/qrenderdoc.exe",
    "qrenderdoc.exe",
)


def find_qrenderdoc(explicit: Optional[str] = None) -> Optional[str]:
    """Absolute path of qrenderdoc.exe, or None when it cannot be located."""
    for c in (explicit, os.environ.get(_ENV_QRENDERDOC)):
        if c and os.path.isfile(c):
            return os.path.abspath(c)

    # running inside qrenderdoc: the host interpreter *is* qrenderdoc
    exe = sys.executable or ""
    if os.path.basename(exe).lower() in ("qrenderdoc.exe", "qrenderdoc"):
        return exe

    for c in _app_paths("qrenderdoc.exe") + _app_paths("qrenderdoc"):
        if os.path.isfile(c):
            return c

    try:
        which = shutil.which("qrenderdoc.exe") or shutil.which("qrenderdoc")
        if which:
            return which
    except Exception:
        pass

    found = _glob_candidates(QRENDERDOC_PATTERNS, install_roots())
    return sorted(found, key=_rank_qrenderdoc)[0] if found else None


def _rank_qrenderdoc(path: str):
    """Order for picking between several installed RenderDoc builds.

    A machine can easily carry more than one - the installer's own `RenderDoc/`
    plus a versioned or vendor-named copy beside it.  The plain folder is the
    one the user installed and the one this tool is fitted against, so it wins;
    the rest keep a stable alphabetical order behind it rather than whichever
    the filesystem happened to return first.
    """
    parent = os.path.basename(os.path.dirname(path)).lower()
    return (0 if parent == "renderdoc" else 1, os.path.normcase(path))


def qrenderdoc_python(exe: Optional[str] = None) -> str:
    """The Python version that qrenderdoc runs scripts with, e.g. ``3.6``.

    RenderDoc ships its interpreter beside the executable - ``python38.zip``,
    ``python36.zip`` - and that interpreter, not the one that launched this
    tool, is what imports `rdc_driver.py`.  Which one you get is decided by
    which RenderDoc is installed, so it is worth being able to read it off
    before a run rather than after one.  Returns "" when nothing indicates it
    (a statically linked build, or RenderDoc not found at all).
    """
    exe = exe or find_qrenderdoc()
    if not exe:
        return ""
    try:
        names = os.listdir(os.path.dirname(os.path.abspath(exe)))
    except Exception:
        return ""
    found = []
    for n in names:
        m = re.match(r"^python(\d)(\d+)\.zip$", n, re.I)
        if m:
            found.append((int(m.group(1)), m.group(2)))
    if not found:
        return ""
    found.sort()
    major, minor = found[-1]
    return "%d.%s" % (major, minor)


# --------------------------------------------------------------------- blender

BLENDER_PATTERNS = (
    "Blender Foundation/Blender */blender.exe",
    "Blender Foundation/Blender/blender.exe",
    "Program Files/Blender Foundation/Blender */blender.exe",
    "Program Files/Blender Foundation/Blender/blender.exe",
    "Blender/blender.exe",
    "Blender/*/blender.exe",
    "Tool/Blender/blender.exe",
    "Tool/Blender/*/blender.exe",
    "Program Files/Blender */blender.exe",
    "Program Files/Blender/blender.exe",
    "Blender Foundation/*/blender.exe",
)


def _version_key(path: str):
    """Sort key: newest version first, and a folder without one last.

    The version is read off the folder the executable sits in, which is what
    every Blender layout puts it in - `Blender 5.2`, `5.2.2`, `Blender
    Foundation/Blender 4.5`.  A build in a folder with no version at all is a
    vendor or a nightly ("goo-engine-stable" is one of each), and those are
    reached for deliberately rather than by default, so they sort behind every
    numbered install instead of landing in front of one by accident - which is
    what a plain `shutil.which` result used to do.
    """
    nums = [int(n) for n in re.findall(r"\d+", os.path.basename(os.path.dirname(path)))
            if n.isdigit()]
    if not nums:
        return (1, ())
    return (0, tuple(-n for n in nums[:3]))


def find_blenders(explicit: Optional[str] = None) -> list:
    """Every plausible blender.exe on this machine, best candidate first.

    What the caller *asked* for always wins: `--blender`, then
    `$RDC2BLEND_BLENDER`.  Everything else - the PATH, the installer's registry
    entry, what was found on disk - is one pool sorted by version, newest first.
    A PATH entry must not outrank a newer install, which is exactly what happens
    on a machine that also has an old vendor build exported from its shell.
    """
    direct = [c for c in (explicit, os.environ.get(_ENV_BLENDER)) if c
              and os.path.isfile(c)]
    try:
        which = shutil.which("blender.exe") or shutil.which("blender")
    except Exception:
        which = None
    registered = [c for c in _app_paths("blender.exe") if os.path.isfile(c)]
    scanned = _glob_candidates(BLENDER_PATTERNS, install_roots())
    pool = sorted(_dedupe(registered + [which] + scanned), key=_version_key)
    return _dedupe(direct + pool)


def find_blender(explicit: Optional[str] = None) -> str:
    """The blender.exe to use.  Raises when there is none."""
    found = find_blenders(explicit)
    if not found:
        raise RuntimeError(
            "no Blender found.  Install Blender %d.%d or newer, pass --blender, "
            "or set %s to the executable."
            % (MIN_BLENDER[0], MIN_BLENDER[1], _ENV_BLENDER))
    return found[0]


def blender_version(exe: str) -> str:
    """`blender --version` first line, or "" - used by doctor."""
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=30)
        for line in ((out.stdout or "") + (out.stderr or "")).splitlines():
            if line.strip():
                return line.strip()
    except Exception:
        pass
    return ""


def tool_version(exe: str) -> str:
    """First line of `--version` for qrenderdoc, which prints to either stream."""
    return blender_version(exe)


def version_tuple(text: str):
    """(major, minor) pulled out of a version banner, or None."""
    m = re.search(r"(\d+)\.(\d+)", text or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


# ------------------------------------------------------------------- reporting

def describe() -> dict:
    """Path summary, for logs and for `doctor`."""
    return {
        "package": PACKAGE_DIR,
        "name": PACKAGE_NAME,
        "profiles": PROFILES_DIR,
        "config": config_file(),
        "qrenderdoc": find_qrenderdoc() or "(not found)",
        "blender": (find_blenders() or ["(not found)"])[0],
    }


if __name__ == "__main__":          # python paths.py -> show what resolves where
    for key, value in describe().items():
        print("%-11s %s" % (key, value))
    print()
    print("blender candidates:")
    for p in find_blenders():
        print("   %s  %s" % (p, blender_version(p)))
