# Translating rdc2blendCpp

Everything this tool says to a person can be replaced without touching the code.
This folder is where you replace it.

## How it works

* **The English lives in the code**, at the point the message is produced:

  ```cpp
  log.info(T("solve.palette_chosen", "eid {eid}: palette {name}", {"eid", ...}));
  ```

* **`en.json` is generated from the code** by `rdc2blendCpp/tools/lang_dump.py`.
  It is a reference and a starting point, not something the tool needs: with no
  language file the English in the code is what gets printed.
* **A language file overrides by key.** Any key you leave out falls back to
  English, so a half-finished translation is a usable one - you can translate the
  twenty messages you see most and stop.
* **A key with the wrong spelling is reported.** `doctor` compares your file with
  `en.json` and says how many entries are not keys of this build. Without that
  check the mistake is silent: the entry is simply never used and the message
  keeps coming out in English.

## Doing a translation pass

1. Copy `en.json` to `<code>.json`, where `<code>` is whatever you want to call
   it - `zh`, `de`, `ja`. The name is the `--lang` value.

   ```
   copy en.json zh.json
   ```

   `zh.json` is a sample with a dozen entries filled in. It is a starting point,
   not a translation - replacing it wholesale is expected.

2. Edit the right-hand side of each line. **Keep the keys and the `{...}`
   placeholders exactly as they are** - they are filled in by the code, and a
   placeholder that has been translated or removed comes out as `{0}` on screen.

3. Run with `--lang zh`, or set `RDC2BLEND_LANG=zh` once and forget it.

   ```
   rdc2blendCppCli.exe run --capture X.rdc --lang zh
   ```

4. To check your work:

   ```
   rdc2blendCppCli.exe --lang zh doctor     # says how many keys are unknown
   python rdc2blendCpp/tools/lang_dump.py --check   # says if en.json is stale
   ```

## Notes on the messages

* **Keys are named after what the message is, not where it is.** `solve.palette_*`
  is the palette search, `fbx.*` and `scene.*` are writing files, `cmd.*` is the
  `run` command's own progress, `help.*` is the usage screens.
* **Some text is deliberately NOT translatable**: JSON field names, flag names,
  file extensions, stage names, and the `done`/`failed` values in `handoff.json`
  and the `status` table. Those are the machine interface - an agent or a UI reads
  them, and `status`'s column has to agree with the file it is reporting on.
  Changing them would break callers rather than help readers.
* **Two messages can share English and have different keys** (`cmd.cannot_create`
  and `cmd.cannot_create_2`). That is intentional: the same words in two places
  may want different translations later, and merging them would make that
  impossible to undo.
* **Long messages are one entry**, even though the source writes them one clause
  per line. The line breaks you see in the C++ are for the programmer.
* **The usage screens are one entry each** (`help.usage`, `help.run`,
  `help.status`, `help.components`, `help.inspect`). They are a layout, not prose:
  the flags are one column and the descriptions another, held in line by spaces.
  The `\n` between lines is written as `\n` in the file, and the spacing is yours
  to arrange - a translation is free to widen a column if its words are longer.
* **Every message ends without a newline**; the tool adds it. The usage screens
  are the one exception and already contain theirs.

