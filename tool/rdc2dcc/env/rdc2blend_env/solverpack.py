# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# VENDORED - do not edit here.
#
# Copied from F:\Project\BlenderImport\tools\rdc2blenderGUI\rdc2blenderGUI
# by `rdc2blendCpp/env/vendor.py`.  Edit the original and re-run that script.
#
# Kept under the name `rdc2blend_env` rather than the reference's own name, so that a
# release carries what it runs and does not depend on another installation.
"""Solver packs: one folder per engine, and the only place a game lives.

A *solver* is everything this tool has to know about one game's renderer: where
the bone palette is, how the camera is stored, which way the world's axes point,
how the skinning shader reads its weights, and - when the table cannot say it -
a little code.  All of it lives in one folder:

    solvers/<name>/
        solver.json     the format table: identity + every constant
        solver.py       optional: only the hooks the table cannot express

Adding a game is dropping a folder in.  Nothing in `solve.py`, `pipeline.py`,
`rdc_driver.py` or either front end learns a new name, and the two solvers that
ship with the tool are ordinary packs - `solvers/endfield` and
`solvers/nishuihan` - so the format is exercised by the thing it replaces.

Why the code half is loaded the way it is
-----------------------------------------
A pack's `solver.py` is executed as a module with the base classes already in its
namespace, so it never imports this package by name::

    class Solver(Adapter):
        vp_layout = "row_major"

That is deliberate.  The package is called `rdc2blend` on one machine and
`rdc2blenderGUI` on the next - the name is read off the folder - and a pack that
wrote `from rdc2blenderGUI.adapters import Adapter` would stop loading the moment
somebody renamed the folder.  The names it is handed are:

    Adapter, GenericAdapter     the base classes to subclass
    Profile, Record, CBView     the profile types, for a hook that reads one
    util                        this tool's pure-python helpers

`solver.py` may define `Solver`; if it does not, `base` in the table says which
built-in class to use and the pack is constants only.
"""
import importlib.util
import json
import os
import sys
from typing import Optional

from . import paths


def packs_dir() -> str:
    return os.path.join(paths.PACKAGE_DIR, "solvers")


def pack_names() -> list:
    """Every solver pack shipped next to the code, sorted, template excluded."""
    try:
        names = os.listdir(packs_dir())
    except Exception:
        return []
    out = []
    for n in sorted(names):
        if n.startswith("_") or n.startswith("."):
            continue
        if os.path.isfile(pack_path(n)):
            out.append(n)
    return out


def pack_path(name: str) -> str:
    return os.path.join(packs_dir(), str(name), "solver.json")


def pack_exists(name: str) -> bool:
    return bool(name) and os.path.isfile(pack_path(name))


def pack_label(name: str) -> str:
    """The solver's display name, straight out of its table."""
    data = read_table(name)
    return str(data.get("label") or "") or str(name)


def read_table(name: str) -> dict:
    """The raw solver.json, or {} when there is no such pack."""
    p = pack_path(name)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_solver_class(name: str, bases: dict):
    """The Adapter subclass a pack provides, or None when it is table-only.

    `bases` is what goes into the module's namespace before it runs - see the
    module docstring for why the code half is handed its imports rather than
    importing them.
    """
    src = os.path.join(packs_dir(), str(name), "solver.py")
    if not os.path.isfile(src):
        return None
    mod_name = "_rdc2blend_solver_%s" % str(name).replace("-", "_")
    spec = importlib.util.spec_from_file_location(mod_name, src)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__.update(bases)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    cls = getattr(mod, "Solver", None)
    if cls is None:
        cls = getattr(mod, "ADAPTER", None)
    return cls


def table_profile_path(name: str) -> Optional[str]:
    """The `solver.json` to load a Profile from, or None."""
    p = pack_path(name)
    return p if os.path.isfile(p) else None
