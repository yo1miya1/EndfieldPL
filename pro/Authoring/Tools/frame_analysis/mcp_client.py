#!/usr/bin/env python3
"""Minimal MCP (stdio) client for renderdoc-mcp 0.3.1.

Usage:
    python mcp_client.py --exe <renderdoc-mcp.exe> --capture <a.rdc> [--out <dir>]

Writes a JSON transcript to <out>/e2e-<timestamp>.json and prints a compact summary.
No third-party dependencies: JSON-RPC over the child process stdin/stdout.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import queue
import threading
from collections import deque

PROTOCOL_VERSION = "2025-03-26"  # renderdoc-mcp 0.3.1 rejects other versions with -32602


class McpClient:
    def __init__(self, exe):
        command = [os.fspath(exe)] if isinstance(exe, (str, os.PathLike)) else list(exe)
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.next_id = 0
        self.transcript = []
        self._stdout = queue.Queue()
        self._stderr = deque(maxlen=100)
        self._closed = False
        self._readers = [
            threading.Thread(target=self._pump_stdout, daemon=True),
            threading.Thread(target=self._pump_stderr, daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def _pump_stdout(self):
        try:
            for line in self.proc.stdout:
                self._stdout.put(line)
        finally:
            self._stdout.put(None)

    def _pump_stderr(self):
        for line in self.proc.stderr:
            self._stderr.append(line[-4000:])

    def _send(self, payload):
        if self._closed:
            raise RuntimeError("MCP session is closed; create a new session after a timeout")
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _read_result(self, want_id, timeout=1800):
        deadline = time.monotonic() + timeout
        while True:
            try:
                line = self._stdout.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                self.close(kill=True)
                raise TimeoutError("no response for id=%s within %ss; server terminated" % (want_id, timeout))
            if line is None:
                self.close(kill=True)
                raise RuntimeError("server closed stdout; stderr=%s" % "".join(self._stderr)[-4000:])
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            self.transcript.append(msg)
            if msg.get("id") == want_id:
                return msg

    def request(self, method, params=None, timeout=1800):
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            payload["params"] = params
        t0 = time.time()
        self._send(payload)
        msg = self._read_result(self.next_id, timeout)
        elapsed = round(time.time() - t0, 2)
        return msg, elapsed

    def notify(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def initialize(self):
        return self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "renderdoc-mcp-e2e", "version": "0.1"},
            },
        )

    def call(self, name, args=None, timeout=1800):
        return self.request("tools/call", {"name": name, "arguments": args or {}}, timeout)

    def close(self, kill=False):
        if self._closed:
            return
        self._closed = True
        if kill and self.proc.poll() is None:
            self.proc.kill()
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
            self.proc.wait(timeout=10)
        for reader in self._readers:
            reader.join(timeout=1)
        for pipe in (self.proc.stdout, self.proc.stderr):
            pipe.close()


def summarize(result):
    if result.get("error"):
        return {"ERROR": result["error"]}
    r = result.get("result", {})
    if r.get("isError"):
        return {"IS_ERROR": r.get("content")}
    content = r.get("content") or []
    if content and content[0].get("type") == "text":
        text = content[0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text[:800]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--out", default=".")
    ap.add_argument("--full", action="store_true", help="run deep probes (pipeline/cbuffer/export)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    capture = os.path.abspath(args.capture)
    steps = []
    client = McpClient(args.exe)
    try:
        msg, elapsed = client.initialize()
        steps.append({"step": "initialize", "elapsed_s": elapsed, "server": msg.get("result")})
        client.notify("notifications/initialized")

        calls = [("open_capture", {"path": capture})]
        if args.full:
            calls += [
                ("get_capture_info", {}),
                ("get_stats", {}),
                ("list_passes", {}),
                ("get_pass_statistics", {}),
                ("get_pass_deps", {}),
                ("list_draws", {"limit": 10}),
                ("get_shader", {"stage": "ps", "mode": "reflect"}),
            ]
        for name, a in calls:
            try:
                msg, elapsed = client.call(name, a)
                summary = summarize(msg)
                if isinstance(summary, (dict, list)):
                    size = len(json.dumps(summary, ensure_ascii=False))
                    preview = json.dumps(summary, ensure_ascii=False)[:1500]
                else:
                    size = len(str(summary))
                    preview = str(summary)[:1500]
                steps.append(
                    {
                        "step": name,
                        "args": a,
                        "elapsed_s": elapsed,
                        "ok": not msg.get("error"),
                        "payload_bytes": size,
                        "preview": preview,
                    }
                )
                print("[%s] %ss bytes=%s" % (name, elapsed, size), flush=True)
                if name == "list_draws" and isinstance(summary, dict):
                    draws = summary.get("draws") or []
                    if draws:
                        first = draws[0]
                        eid = first.get("eventId", first.get("eid", first.get("eventID")))
                        if isinstance(eid, int):
                            deep = [
                                ("goto_event", {"eventId": eid}),
                                ("get_pipeline_state", {}),
                                ("get_bindings", {}),
                                ("list_cbuffers", {"stage": "ps"}),
                                ("get_cbuffer_contents", {"stage": "ps", "index": 0}),
                                ("get_shader", {"stage": "ps", "mode": "disasm"}),
                                ("export_render_target", {"index": 0}),
                            ]
                            for dname, dargs in deep:
                                try:
                                    m2, e2 = client.call(dname, dargs)
                                    s2 = summarize(m2)
                                    p2 = json.dumps(s2, ensure_ascii=False) if isinstance(s2, (dict, list)) else str(s2)
                                    steps.append(
                                        {
                                            "step": dname,
                                            "args": dargs,
                                            "elapsed_s": e2,
                                            "ok": not m2.get("error"),
                                            "payload_bytes": len(p2),
                                            "preview": p2[:2500],
                                        }
                                    )
                                    print("[%s@%s] %ss bytes=%s" % (dname, eid, e2, len(p2)), flush=True)
                                except Exception as exc:  # noqa: BLE001
                                    steps.append({"step": dname, "args": dargs, "error": repr(exc)})
                                    print("[%s@%s] EXCEPTION %r" % (dname, eid, exc), flush=True)
            except Exception as exc:  # noqa: BLE001
                steps.append({"step": name, "args": a, "error": repr(exc)})
                print("[%s] EXCEPTION %r" % (name, exc), flush=True)
    finally:
        client.close()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_path = os.path.join(args.out, "e2e-%s.json" % stamp)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(
            {"exe": args.exe, "capture": capture, "steps": steps, "transcript": client.transcript},
            fh,
            ensure_ascii=False,
            indent=2,
        )
    print("\nTRANSCRIPT=%s" % out_path)
    for s in steps:
        print("- %-22s %s" % (s.get("step"), "OK" if s.get("ok") else s.get("error", "FAILED")))


if __name__ == "__main__":
    main()
