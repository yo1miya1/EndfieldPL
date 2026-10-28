# -*- coding: utf-8 -*-
"""<游戏名> - the code half of the `<name>` solver pack.

**Only fill this in if `solver.json` cannot say it.**  The table covers the
palette, the camera, the axes, the units, the skin weights and every threshold;
this file is for the search and the filtering that are genuinely code.

`Adapter`, `GenericAdapter`, `position_declaration`, `infer_semantics`,
`skin_attributes`, `cb_slot` and `BUFFER_DESCRIPTORS` are already in this
module's namespace when it runs - **do not import them**, and do not import this
package by name.  The package is called `rdc2blend` on one machine and
`rdc2blenderGUI` on the next (the name is read off the folder), so a pack that
wrote an import would stop loading the moment somebody renamed the folder.

Delete this file entirely for a table-only solver.
"""


class Solver(Adapter):
    """<游戏名>: what the table cannot say."""

    #: How the four float4s of the view-projection block are laid out.
    #:   "column_major" - the shader does `dp4` against them, so they ARE the rows
    #:   "row_major"    - the four rows are stored one component per float4
    #: Override only if it is not the built-in default.
    # vp_layout = "column_major"

    # ---------------------------------------------------------------- camera
    # Uncomment and fill in when the camera block has to be *found* rather than
    # read: an engine that renumbers its constant-buffer slots per draw, or one
    # that keeps several matrices in one block and needs a tie-breaker.
    #
    # def camera_view(self, cbs, profile, meta=None):
    #     """Pick the block that really holds the view-projection."""
    #     res = list(meta.get("viewport") or [0, 0, 0, 0])[2:4] if meta else None
    #     named = cb_slot(cbs, profile.vp_rows.get("cb", 0))
    #     for slot in ([named] if named is not None else []) + sorted(cbs):
    #         raw = cbs.get(slot)
    #         if not raw:
    #             continue
    #         cam = self.camera(raw, profile, res=res)
    #         ok, why = self.check_camera(cam)
    #         if ok:
    #             cam["cb_slot"] = slot
    #             return cam
    #     raise RuntimeError("no constant buffer of this draw is a camera "
    #                        "(bound: %s)" % (sorted(cbs) or "none"))

    # ---------------------------------------------------------------- draws
    # Uncomment and fill in when the character's event range holds geometry that
    # is not the character.  `family` is the position declaration the skinned
    # parts share - see `position_declaration`.
    #
    # def keep_draw(self, draw, family, profile):
    #     """Keep the character's mesh family; drop whatever else shares its range."""
    #     if draw.get("has_skin") or not family:
    #         return True
    #     return position_declaration(draw.get("inputs")) in (None, family)

    # ------------------------------------------------------------ attributes
    # Uncomment and fill in when a stream has to be read as something other than
    # what its name or its shape says.
    #
    # def classify_attributes(self, inputs, profile=None):
    #     cls = Adapter.classify_attributes(self, inputs, profile)
    #     return cls
    #
    # def decode_normal(self, raw, off, spec, packing="auto"):
    #     return Adapter.decode_normal(self, raw, off, spec, packing)
