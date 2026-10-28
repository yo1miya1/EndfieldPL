"""A serial, file-queued MCP session for iterative analysis without reopening a large capture.

Run: python rdc_probe.py serve --dir <ASCII work directory> [--exe ...]
Submit numbered *.request.json files into <dir>/jobs. Each contains a list of
{name, args?, stage?, timeout?}. Results are immediately persisted in raw/ and
<request>.result.json. Use a request with name "__stop__" to close the session.
This is a local single-writer queue, not a network service.
"""
import argparse
import json
import os
from pathlib import Path
import time
import shutil
import hashlib

from rdc_analyze import DEFAULT_EXE, Session


def serve(directory, exe, idle_timeout=1800):
    root = Path(directory).resolve()
    jobs = root / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    sess = Session(exe, raw_dir=root / "raw")
    try:
        sess.initialize()
        tools = sess.list_tools()
        (root / "tools.json").write_text(json.dumps(tools, ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "ready.json").write_text(json.dumps({"pid": os.getpid(), "server": sess.server}), encoding="utf-8")
        last = time.monotonic()
        while time.monotonic() - last < idle_timeout:
            pending = [p for p in sorted(jobs.glob("*.request.json"))
                       if not p.with_suffix(".result.json").exists()]
            if not pending:
                time.sleep(0.2)
                continue
            for path in pending:
                calls = json.loads(path.read_text(encoding="utf-8-sig"))
                results = []
                stop = False
                for call in calls:
                    if call["name"] == "__stop__":
                        stop = True
                        break
                    sess.call(call.get("stage", "probe"), call["name"], call.get("args", {}),
                              timeout=call.get("timeout", 600))
                    rec = sess.calls[-1]
                    result = rec.get("result")
                    if rec["ok"] and call["name"].startswith("export_") and isinstance(result, dict):
                        source = result.get("path") or call.get("args", {}).get("outputPath")
                        if source and Path(source).is_file():
                            destination = root / "artifacts" / ("%03d_%s" % (rec["idx"], Path(source).name))
                            destination.parent.mkdir(exist_ok=True)
                            shutil.copy2(source, destination)
                            with destination.open("rb") as stream:
                                digest = hashlib.file_digest(stream, "sha256").hexdigest()
                            entry = {"callIndex": rec["idx"], "tool": call["name"], "args": call.get("args", {}),
                                     "path": str(destination), "bytes": destination.stat().st_size, "sha256": digest}
                            with (root / "assets.jsonl").open("a", encoding="utf-8") as stream:
                                stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    results.append(rec)
                    path.with_suffix(".progress.json").write_text(
                        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
                    if sess.client._closed:
                        break
                path.with_suffix(".result.json").write_text(
                    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
                last = time.monotonic()
                if stop or sess.client._closed:
                    return
    finally:
        if not sess.client._closed:
            sess.call("P6", "close_capture", {}, timeout=30)
        sess.close()
        (root / "closed.json").write_text(json.dumps({"calls": len(sess.calls)}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve"])
    parser.add_argument("--dir", required=True)
    parser.add_argument("--exe", default=DEFAULT_EXE)
    parser.add_argument("--idle-timeout", type=float, default=1800)
    args = parser.parse_args()
    serve(args.dir, args.exe, args.idle_timeout)
