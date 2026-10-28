rdc2blendCpp 0.1
=================

Run:      rdc2blendCppUi.exe                     the window (pick a capture)
          rdc2blendCppUi.exe <capture.rdc>       the window, with one preloaded
          rdc2blendCppCli.exe run --capture X.rdc   the command line
Check:    rdc2blendCppCli.exe doctor
          rdc2blendCppCli.exe selftest
Help:     rdc2blendCppCli.exe --help
          rdc2blendCppCli.exe <command> --help

Layout
------
  rdc2blendCppUi.exe  the UI; it drives rdc2blendCppCli.exe, which must sit
                      beside it.  Release settings -> "Scene origin: character
                      flow" builds the frame around the character's own origin
                      and creates the camera the capture was rendered with.
  component/<game>/   one folder per game: its component - if it needs one - and
                      its solver pack.  `--solver <game>` names one of these
                      folders, and works with no other setup:
                          endfield, nishuihan
  env/                the Python the tool runs (RenderDoc driver, Blender bridge,
                      language maps); nothing here is compiled into the exe
  workspace/          created on first run: bin/ imi/ tmp/

Into Blender
------------
  blender --background --python env/rdc2blend_import.py -- <scene.rdc2scene> \
          --report report.json --save scene.blend

Materials (Matex)
-----------------
  The scene pipeline keeps ONE instance of each model and drops the draws it
  cannot fit, which is right for a scene and wrong for a material library.  Matex
  is a second collection path that keeps every draw call, with its shader, its
  constant buffers and reflection, its texture bindings and its mesh:

    rdc2blendCppCli.exe read --capture X.rdc --workspace W --task T \
                        --solver <game> --matex [--eid-min A] [--eid-max B]
    rdc2blendCppCli.exe matexport W\imi\T\read --workspace W [--steps all]
    blender --background --python env/rdc2blend_matex.py -- W\bin\matex

  The second step needs no RenderDoc at all, so a different channel order or a
  different semantic template costs a re-run of that step rather than another
  walk over the capture.  `--save <file>.blend` writes a scene as well, with every
  texture PACKED INTO IT - the library is made to be handed to somebody, and a
  .blend that only points at `tex/` is one whose materials are missing their
  textures the moment it is copied anywhere.  The library lands in `W/bin/matex`:

    binding.json    which texture sat in which slot of which shader, keyed by
                    shader bytecode hash and binding name - not by slot index,
                    which moves between draws, and not by resource id, which does
                    not outlive the replay it came from
    matex.json      what was exported and what failed
    fbx/eid-N.fbx   one per draw call, vertices unplaced at the origin
    tex/            the processed textures, once per resource id
    tex-raw/        the same images as the capture showed them, before channels

  `--swizzle` takes exactly four letters from r,g,b,a (`bgra`, `rrrr`, `aabr`);
  `xyzw` is refused, because that is a shader's spelling of a component rather
  than a texture's channel name.

  A draw's vertex stream does not always hold world positions - the same layout
  carries the full-screen quad a post pass scales into clip space - so a triangle
  with a vertex outside `--pos-limit` (default 1000000 units, or a NaN) is
  dropped, and a mesh left with none contributes its material and not its
  geometry.  Measured on a 609-draw whole-map capture: 6 such draws, and reading
  them as geometry had taken the project's bounding box with it.

  The library carries the SOLVE'S CAMERA (`camera.json`, written when `--world2`
  names a solve that has one), and the bridge builds it, because "is this model
  right?" is answered by looking at it from where the game looked from - 507 of
  582 meshes in that same capture carry no placement at all, and the difference
  only shows from the right seat.  `--no-camera` leaves it out.

  WHICHEVER PIPELINE YOU FINISHED, IT LEAVES A SCRIPT YOU CAN DOUBLE-CLICK:

    <workspace>/BuildScene.bat    after `emit-scene`
    <workspace>/BuildMatex.bat    after `matexport` (or `run --matex`)

  Each one is rooted at its own folder - the batch idiom for "the directory this
  file is in" - so the workspace can be copied anywhere; each verifies the paths it
  recorded and searches under its own root when they have moved; each finds Blender
  by version-named directory, by PATH, or by `--blender`.  They exist because the
  last step of every pipeline is a command line, and that command line used to live
  only in this file.

  `W/matex/templates.json` names bindings the capture cannot - an engine that
  ships its shaders stripped calls every texture `texture0`, `texture1`, ... and
  only a person looking at the pictures knows which is which.  Rules match on the
  shader hash, the binding name or the resource id, `*` and `?` are wildcards,
  and the first match wins, so a narrow rule goes above a broad one.

Language
--------
  Everything the tool says to a person can be replaced without touching the exe.
  Copy env/lang/en.json - the complete English list, generated from the code - to
  env/lang/<code>.json, translate the right-hand side and leave the keys alone,
  then run with --lang <code> or set RDC2BLEND_LANG=<code>.  A key you leave out
  falls back to English, so a half-finished translation is a usable one.
  `rdc2blendCppCli.exe --lang <code> doctor` says how many of your keys this
  build does not know, which is the one mistake that is otherwise silent.
  See env/lang/README.md.

Requirements
------------
  Windows x64.  Nothing else for the tool itself - the C runtime is linked in,
  so there is no Visual C++ redistributable to install.  The UI draws with
  Direct3D 11 (it falls back to the software rasteriser) and takes its Chinese
  labels from a font in the Windows font directory.
  `read` also needs RenderDoc's qrenderdoc.exe (found on PATH, in Program Files,
  or named with --qrenderdoc).  The Blender step needs Blender.

A .rdc from another machine works as long as it was captured with a RenderDoc
whose replay this build can open.
