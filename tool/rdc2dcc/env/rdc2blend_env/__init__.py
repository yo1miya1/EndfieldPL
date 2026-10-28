"""The Python half of rdc2blendCpp's `read` stage, vendored.

qrenderdoc runs a Python script; that script needs the reference tool's
profile reader, constant-buffer table, attribute decoder and solver.  This
package is a copy of exactly those modules, under a name of its own, so a
release runs what it ships.

Refresh with `rdc2blendCpp/env/vendor.py`; do not edit the modules here.
"""

__version__ = "0.1.0"
