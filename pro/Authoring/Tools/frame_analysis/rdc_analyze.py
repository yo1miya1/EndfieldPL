#!/usr/bin/env python3
r"""RenderDoc frame-analysis harness for renderdoc-mcp 0.3.1 (59 tools).

This is the executable counterpart of:
    pro/skills/renderdoc-frame-analysis/SKILL.md

It drives the fixed pipeline P0 (environment) -> P1 (skeleton) -> P2 (target)
-> P3 (shaders/constants) -> P4 (asset export), records every MCP call with
arguments, elapsed time and raw result, and renders Markdown tables from the
*actual* field names returned by the server.

Usage (from the workspace root):
    python pro/tools/rdc_analyze.py run \
        --capture "E:\path\to\frame.rdc" \
        --out "%TEMP%\rdc\analysis\frame" --assets pro/examples/assets \
        --report-dir pro/examples [--eid 16 --reason "..."]

    python pro/tools/rdc_analyze.py tools --out "%TEMP%/rdc/analysis/tools.json"

Notes:
  * protocol version is fixed to 2025-03-26 (0.3.1 rejects others with -32602);
  * export_* tools derive their output directory from the capture path, so a
    capture with a non-ASCII path is copied once to %TEMP%/rdc/<name>.rdc
    (ASCII) before opening; the source file is never modified;
  * every value written into a report comes from a tool result. Missing values
    are rendered as "未获取" and never guessed.
"""
import argparse
import ctypes
import json
import os
import re
import shutil
import sys
import time
import hashlib
from pathlib import Path
from collections import Counter, OrderedDict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import McpClient, summarize  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXE = os.environ.get("RENDERDOC_MCP_EXE", str(PACKAGE_ROOT / "bin" / "renderdoc-mcp.exe"))
if not Path(DEFAULT_EXE).is_file() and not os.environ.get("RENDERDOC_MCP_EXE"):
    DEFAULT_EXE = str(Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) /
                      "vendor_imports" / "renderdoc-mcp" / "bin" / "renderdoc-mcp.exe")
DEFAULT_DLL = str(Path(DEFAULT_EXE).parent / "renderdoc.dll")
PROTOCOL_VERSION = "2025-03-26"

REQUIRED_TOOLS = [
    "open_capture", "get_capture_info", "list_passes", "get_pass_statistics",
    "get_pass_deps", "list_draws", "goto_event", "get_pipeline_state",
    "get_bindings", "list_cbuffers", "get_cbuffer_contents", "get_shader",
    "export_render_target", "export_texture",
]

STAGE_ORDER = ["vs", "hs", "ds", "gs", "ps", "cs"]

MISSING = "未获取"


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_ascii(text):
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def safe_name(text, limit=80):
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text or "").strip("_")
    return (text or "x")[:limit]


def md_cell(value):
    if value is None:
        return "未获取"
    if value == "":
        return "（空）"
    return str(value).replace("|", "\\|").replace("\n", " ")


def display_path(path):
    """Hide the sandbox-specific temp root in reports; keep the path meaningful."""
    if not path:
        return MISSING
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        try:
            p = os.path.abspath(path)
            t = os.path.abspath(temp)
            if p.lower().startswith(t.lower() + os.sep):
                return "%TEMP%" + p[len(t):]
        except Exception:
            pass
    return path


def file_version(path):
    """Return the fixed file version of a Windows PE, or None."""
    if not os.path.exists(path):
        return None
    try:
        size = ctypes.windll.version.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        data = ctypes.create_string_buffer(size)
        if not ctypes.windll.version.GetFileVersionInfoW(path, 0, size, data):
            return None
        ptr = ctypes.c_void_p()
        length = ctypes.c_uint()
        if not ctypes.windll.version.VerQueryValueW(data, "\\", ctypes.byref(ptr), ctypes.byref(length)):
            return None
        fixed = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_uint32 * 13)).contents
        ms, ls = fixed[2], fixed[3]
        return "%d.%d.%d.%d" % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)
    except Exception:
        return None


def classify_error(text):
    low = (text or "").lower()
    rules = [
        ("version", "incompatible version"),
        ("cross_vendor", "mapping memory on replay"),
        ("cross_vendor", "captured on"),
        ("unicode_path", "no mapping for the unicode character"),
        ("unicode_path", "multi-byte code page"),
        ("access_denied", "access is denied"),
        ("access_denied", "permission denied"),
        ("file_io", "file i/o failed"),
        ("no_marker", "no marker"),
        ("no_shader", "no shader bound"),
        ("not_implemented", "not implemented"),
        ("unsupported", "unsupported"),
    ]
    for kind, needle in rules:
        if needle in low:
            return kind
    return "unknown"


def flatten_result(result):
    if isinstance(result, dict) and "IS_ERROR" in result:
        return json.dumps(result["IS_ERROR"], ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


def values_of(var):
    for key in ("floatValues", "intValues", "uintValues"):
        if key in var and var[key] is not None:
            return key, var[key]
    return None, None


# --------------------------------------------------------------------------- #
# MCP session with evidence capture
# --------------------------------------------------------------------------- #
class Session:
    def __init__(self, exe, timeout=900, raw_dir=None):
        self.exe = exe
        self.timeout = timeout
        self.client = McpClient(exe)
        self.calls = []
        self.tools = []
        self.server = None
        self.capture_open = None
        self.raw_dir = Path(raw_dir) if raw_dir else None
        if self.raw_dir:
            self.raw_dir.mkdir(parents=True, exist_ok=True)

    def record(self, rec):
        rec["idx"] = len(self.calls)
        self.calls.append(rec)
        if self.raw_dir:
            path = self.raw_dir / ("%03d_%s.json" % (rec["idx"], safe_name(rec["name"])))
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

    def initialize(self):
        msg, elapsed = self.client.initialize()
        self.server = (msg.get("result") or {}).get("serverInfo")
        if msg.get("error"):
            raise RuntimeError("MCP initialize failed: %s" % msg["error"])
        self.record({
            "idx": 0, "stage": "P0", "name": "initialize", "args": {"protocolVersion": PROTOCOL_VERSION},
            "elapsed_s": elapsed, "ok": True, "error": None,
            "result": (msg.get("result") or {}),
        })
        self.client.notify("notifications/initialized")
        return elapsed

    def list_tools(self):
        msg, elapsed = self.client.request("tools/list", {})
        self.tools = (msg.get("result") or {}).get("tools") or []
        if msg.get("error") or not self.tools:
            raise RuntimeError("MCP tools/list failed or empty")
        self.record({
            "idx": 0, "stage": "P0", "name": "tools/list", "args": {},
            "elapsed_s": elapsed, "ok": not bool(msg.get("error")), "error": None,
            "result": {"count": len(self.tools), "names": [t["name"] for t in self.tools]},
        })
        return self.tools

    def call(self, stage, name, args=None, timeout=None, quiet=False):
        args = args or {}
        t0 = time.time()
        result, ok, err, elapsed = None, False, None, 0.0
        try:
            msg, elapsed = self.client.call(name, args, timeout or self.timeout)
            result = summarize(msg)
            if msg.get("error"):
                ok = False
                err = json.dumps(msg["error"], ensure_ascii=False)
            elif isinstance(result, dict) and result.get("IS_ERROR"):
                ok = False
                err = flatten_result(result)
            else:
                ok = True
        except Exception as exc:  # noqa: BLE001
            elapsed = round(time.time() - t0, 2)
            err = repr(exc)
            result = None
        rec = {
            "idx": len(self.calls), "stage": stage, "name": name, "args": args,
            "elapsed_s": elapsed, "ok": ok, "error": err, "result": result,
        }
        self.record(rec)
        if not quiet:
            status = "OK" if ok else "FAIL(%s)" % classify_error(err)
            print("  [%s] %-24s %6.2fs %s" % (stage, name, elapsed, status), flush=True)
        return result, ok, err, elapsed

    def close(self):
        self.client.close()

    def stage_elapsed(self, stage):
        return round(sum(c["elapsed_s"] for c in self.calls if c["stage"] == stage), 2)


# --------------------------------------------------------------------------- #
# stage implementations
# --------------------------------------------------------------------------- #
def ensure_ascii_capture(capture, scratch=None):
    """Use an isolated, content-verified copy: exports must not touch the input directory."""
    capture = os.path.abspath(capture)
    source = Path(capture)
    if not source.is_file():
        raise FileNotFoundError(capture)
    temp = os.environ.get("TEMP") or os.environ.get("TMP") or r"C:\Windows\Temp"
    work = os.path.abspath(scratch or os.path.join(temp, "rdc"))
    if not is_ascii(work):
        raise ValueError("Capture scratch directory must have an ASCII path")
    os.makedirs(work, exist_ok=True)
    with source.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    target = os.path.join(work, digest[:20] + ".rdc")
    if os.path.normcase(target) == os.path.normcase(capture):
        raise ValueError("Scratch copy must differ from the original capture")
    valid = False
    if os.path.exists(target) and os.path.getsize(target) == source.stat().st_size:
        with open(target, "rb") as fh:
            valid = hashlib.file_digest(fh, "sha256").hexdigest() == digest
    if not valid:
        t0 = time.time()
        partial = target + ".partial"
        shutil.copy2(capture, partial)
        with open(partial, "rb") as fh:
            if hashlib.file_digest(fh, "sha256").hexdigest() != digest:
                raise IOError("Capture copy hash mismatch")
        os.replace(partial, target)
        copy_s = round(time.time() - t0, 2)
    else:
        copy_s = 0.0
    note = ("使用独立 ASCII 工作副本（%d 字节，复制 %.2fs，SHA256=%s）。源目录只读。"
            % (os.path.getsize(capture), copy_s, digest))
    return target, note


def stage_p0(sess, tools, capture_open, capture_source, runtime_dll):
    required_missing = [n for n in REQUIRED_TOOLS if n not in [t["name"] for t in tools]]
    if required_missing:
        return {"ok": False, "error": "Required tools missing: " + ", ".join(required_missing),
                "required_missing": required_missing}
    info, ok, err, _ = sess.call("P0", "open_capture", {"path": capture_open})
    if not ok:
        return {"ok": False, "error": err, "kind": classify_error(err),
                "required_missing": required_missing}
    sess.call("P0", "get_capture_info", {})
    status, _, _, _ = sess.call("P0", "session_status", {})
    return {
        "ok": bool(info and info.get("totalEvents", 0) > 0 and (status or {}).get("isOpen")),
        "info": info,
        "session": status,
        "required_missing": required_missing,
        "runtime_version": file_version(runtime_dll),
        "capture_source": capture_source,
        "capture_open": capture_open,
        "tool_count": len(tools),
    }


def stage_p1(sess, detailed=False, draw_limit=100000):
    info, _, _, _ = sess.call("P1", "get_capture_info", {})
    stats, _, _, _ = sess.call("P1", "get_stats", {})
    passes, _, _, _ = sess.call("P1", "list_passes", {})
    large = bool(sess.capture_open and os.path.getsize(sess.capture_open) > 500 * 1024 * 1024)
    pass_stats, deps = {}, {}
    skipped = []
    if detailed or not large:
        pass_stats, _, _, _ = sess.call("P1", "get_pass_statistics", {})
        deps, _, _, _ = sess.call("P1", "get_pass_deps", {})
    else:
        skipped = ["get_pass_statistics", "get_pass_deps"]
    draws, ok, err, _ = sess.call("P1", "list_draws", {"limit": draw_limit})
    if not ok:
        raise RuntimeError(err)
    if (draws or {}).get("count", 0) >= draw_limit:
        raise RuntimeError("Draw list may be truncated; increase --draw-limit")
    return {
        "info": info or {},
        "stats": stats or {},
        "passes": (passes or {}).get("passes") or [],
        "pass_stats": (pass_stats or {}).get("passes") or [],
        "deps": (deps or {}).get("edges") or [],
        "draws": (draws or {}).get("draws") or [],
        "skipped": skipped,
    }


def draw_score(draw):
    return (draw.get("numIndices") or 0) * (draw.get("numInstances") or 1)


def stage_p2(sess, draws, explicit_eid, reason):
    if not draws:
        raise RuntimeError("No draw candidates returned")
    if explicit_eid is not None and explicit_eid not in {d["eventId"] for d in draws}:
        raise ValueError("Target event is not in the complete draw list")
    ranked = sorted(draws, key=draw_score, reverse=True)
    candidates = []
    seen = set()
    if explicit_eid is not None:
        candidates.append(explicit_eid)
        seen.add(explicit_eid)
    for d in ranked[:5]:
        if d["eventId"] not in seen:
            candidates.append(d["eventId"])
            seen.add(d["eventId"])
    rows = []
    for eid in candidates:
        pipeline, _, _, _ = sess.call("P2", "get_pipeline_state", {"eventId": eid})
        bindings, _, _, _ = sess.call("P2", "get_bindings", {"eventId": eid})
        dinfo, _, _, _ = sess.call("P2", "get_draw_info", {"eventId": eid})
        rows.append({"eventId": eid, "pipeline": pipeline or {}, "bindings": bindings or {},
                     "draw_info": dinfo or {}})
    target_eid = explicit_eid if explicit_eid is not None else candidates[0]
    if reason is None:
        d = next((x for x in draws if x["eventId"] == target_eid), {})
        reason = "自动：numIndices×numInstances 最大（%d），flags=%s" % (draw_score(d), d.get("flags", MISSING))
    return {"candidates": rows, "target_eid": target_eid, "reason": reason}


def stage_p3(sess, target_eid):
    action, _, _, _ = sess.call("P3", "get_draw_info", {"eventId": target_eid})
    is_dispatch = "Dispatch" in (action or {}).get("flags", "")
    pipeline, _, _, _ = sess.call("P3", "get_pipeline_state", {"eventId": target_eid})
    bindings, _, _, _ = sess.call("P3", "get_bindings", {"eventId": target_eid})
    stages_present = []
    if pipeline:
        key_map = {"vs": ("vertexShader",), "hs": ("hullShader",), "ds": ("domainShader",),
                   "gs": ("geometryShader",), "ps": ("pixelShader",),
                   "cs": ("computeShader", "csShader")}
        for stage in STAGE_ORDER:
            if (stage == "cs") != is_dispatch:
                continue
            if any(pipeline.get(k) and pipeline[k].get("resourceId") not in (None, "ResourceId::0", "0", 0)
                   for k in key_map[stage]):
                stages_present.append(stage)
    if bindings:
        bindings["stages"] = {s: b for s, b in bindings.get("stages", {}).items() if s in stages_present}
    cbuffers = []
    reflects = {}
    for stage in stages_present:
        lst, ok, _, _ = sess.call("P3", "list_cbuffers", {"stage": stage, "eventId": target_eid})
        if not ok:
            continue
        for cb in (lst or {}).get("cbuffers", []):
            content, cok, cerr, _ = sess.call(
                "P3", "get_cbuffer_contents",
                {"stage": stage, "index": cb["index"], "eventId": target_eid})
            cbuffers.append({"stage": stage, "meta": cb,
                             "contents": content if cok else None,
                             "error": cerr})
        ref, rok, _, _ = sess.call("P3", "get_shader",
                                   {"stage": stage, "mode": "reflect", "eventId": target_eid})
        reflects[stage] = ref if rok else None
    disasm = {}
    for stage in [s for s in ("ps", "vs") if s in stages_present]:
        d, dok, derr, _ = sess.call("P3", "get_shader",
                                    {"stage": stage, "mode": "disasm", "eventId": target_eid})
        disasm[stage] = d if dok else {"error": derr}
    pattern_stage = "ps" if "ps" in stages_present else (stages_present[-1] if stages_present else None)
    pattern_hits = {}
    if pattern_stage and isinstance(disasm.get(pattern_stage), dict) and disasm[pattern_stage].get("disassembly"):
        api = (pipeline or {}).get("api", "")
        keys = ["ImageSampleImplicitLod(", "CompositeConstruct(", "FMix(", "FClamp(",
                "FSub(", "Dot(", "Pow(", "Exp(", "Log("] if not api.lower().startswith("d3d") else \
               ["sample", "mad", "dp3", "pow", "saturate", "discard", "tex"]
        pattern_hits = disasm_hits(disasm[pattern_stage]["disassembly"], keys)
    return {"pipeline": pipeline or {}, "bindings": bindings or {},
            "stages_present": stages_present, "cbuffers": cbuffers,
            "reflects": reflects, "disasm": disasm, "pattern_hits": pattern_hits,
            "pattern_stage": pattern_stage}


def disasm_hits(text, patterns):
    lines = [ln.lower() for ln in text.splitlines()]
    rows = []
    for p in patterns:
        low = p.lower()
        hit_lines = [i + 1 for i, ln in enumerate(lines) if low in ln]
        rows.append({"pattern": p, "count": len(hit_lines),
                     "firstLine": hit_lines[0] if hit_lines else None})
    return rows


def resolve_textures(sess, resources, bindings, target_eid, max_scan):
    """Resolve readOnlyResources (bindPoint/name, no ResourceId in 0.3.1) to ResourceIds."""
    by_name = {}
    for r in resources:
        if r.get("type") != "Texture":
            continue
        by_name.setdefault((r.get("name") or "").lower(), []).append(r["resourceId"])
    usage_cache = {}
    scan_needed = False
    for stage, sb in (bindings.get("stages") or {}).items():
        for ro in sb.get("readOnlyResources") or []:
            if not ro.get("resourceId"):
                scan_needed = True
    texture_ids = [r["resourceId"] for r in resources if r.get("type") == "Texture"]
    if scan_needed and len(texture_ids) <= max_scan:
        for rid in texture_ids:
            usage, ok, _, _ = sess.call("P4", "get_resource_usage", {"resourceId": rid}, quiet=True)
            if ok and isinstance(usage, dict):
                usage_cache[rid] = usage.get("entries") or []
    resolved = []
    for stage in STAGE_ORDER:
        sb = (bindings.get("stages") or {}).get(stage)
        if not sb:
            continue
        for ro in sb.get("readOnlyResources") or []:
            name = ro.get("name") or ""
            rid = ro.get("resourceId")
            if rid in ("ResourceId::0", "0", 0):
                resolved.append({"stage": stage, "bindPoint": ro.get("bindPoint"),
                                 "name": name, "resourceId": None, "method": "unbound descriptor"})
                continue
            method = "get_bindings.resourceId"
            if not rid and name.lower() in by_name and len(by_name[name.lower()]) == 1:
                rid = by_name[name.lower()][0]
                method = "list_resources.name 精确匹配"
            if not rid and usage_cache:
                hits = [r for r, entries in usage_cache.items()
                        if any(e.get("eventId") == target_eid and
                               str(e.get("usage", "")).lower().startswith(stage.lower() + "_")
                               for e in entries)]
                ro_count = len(sb.get("readOnlyResources") or [])
                if len(hits) == 1 and ro_count == 1:
                    rid = hits[0]
                    method = "get_resource_usage 反查（1:1）"
                else:
                    resolved.append({"stage": stage, "bindPoint": ro.get("bindPoint"),
                                     "name": name, "resourceId": None,
                                     "method": "未获取（候选 %d / 绑定 %d，映射不唯一）" % (len(hits), ro_count),
                                     "candidates": hits})
                    continue
            resolved.append({"stage": stage, "bindPoint": ro.get("bindPoint"),
                             "name": name, "resourceId": rid, "method": method})
    return resolved, len(texture_ids), scan_needed


def stage_p4(sess, p3, target_eid, work_dir, assets_dir, max_scan=600, do_mesh=True,
             do_snapshot=True, scratch_dir=None):
    scratch_dir = scratch_dir or work_dir
    os.makedirs(scratch_dir, exist_ok=True)
    export_dir = os.path.join(os.path.dirname(os.path.abspath(sess.capture_open or "")),
                              "renderdoc-mcp-export")
    # goto_event is mandatory: export_render_target has no eventId argument
    sess.call("P4", "goto_event", {"eventId": target_eid})
    resources, _, _, _ = sess.call("P4", "list_resources", {"type": "Texture"})
    textures, tex_total, scan_needed = resolve_textures(
        sess, (resources or {}).get("resources") or [], p3["bindings"], target_eid, max_scan)
    sess.call("P4", "goto_event", {"eventId": target_eid})
    exports = []
    rt_count = len((p3["pipeline"] or {}).get("renderTargets") or [])
    for idx in range(max(rt_count, 1)):
        res, ok, err, _ = sess.call("P4", "export_render_target", {"index": idx})
        exports.append({"kind": "render_target", "index": idx, "result": res,
                        "ok": ok, "error": err})
    for tex in textures:
        if not tex.get("resourceId"):
            exports.append({"kind": "texture", "stage": tex["stage"], "bindPoint": tex["bindPoint"],
                            "name": tex["name"], "result": None, "ok": False,
                            "error": "ResourceId 未获取：%s" % tex["method"]})
            continue
        res, ok, err, _ = sess.call("P4", "export_texture",
                                    {"resourceId": tex["resourceId"], "mip": 0, "layer": 0})
        exports.append({"kind": "texture", "stage": tex["stage"], "bindPoint": tex["bindPoint"],
                        "name": tex["name"], "resourceId": tex["resourceId"],
                        "result": res, "ok": ok, "error": err})
    mesh = None
    if do_mesh:
        mesh_path = os.path.join(scratch_dir, "mesh_%04d.obj" % target_eid)
        res, ok, err, _ = sess.call("P4", "export_mesh",
                                    {"eventId": target_eid, "format": "obj", "outputPath": mesh_path})
        mesh = {"result": res, "ok": ok, "error": err, "outputPath": mesh_path}
    snapshot = None
    if do_snapshot:
        snap_dir = os.path.join(scratch_dir, "snapshot_%04d" % target_eid)
        res, ok, err, _ = sess.call("P4", "export_snapshot",
                                    {"eventId": target_eid, "outputDir": snap_dir})
        snapshot = {"result": res, "ok": ok, "error": err, "outputDir": snap_dir}
    # archive with semantic names
    os.makedirs(assets_dir, exist_ok=True)
    archived = []
    rt_files = {}
    for e in exports:
        if e["kind"] == "render_target" and e["ok"] and isinstance(e["result"], dict):
            src = e["result"].get("path")
            if src and os.path.exists(src):
                target_name = "%04d_rt_t%d_unknown.png" % (target_eid, e["index"])
                dst = os.path.join(assets_dir, target_name)
                shutil.copy2(src, dst)
                archived.append({"src": src, "dst": dst, "name": target_name,
                                 "kind": "render_target", "index": e["index"],
                                 "source": "RT%d（无 shader 变量名）" % e["index"],
                                 "bytes": os.path.getsize(dst)})
    for e in exports:
        if e["kind"] != "texture":
            continue
        if not (e["ok"] and isinstance(e["result"], dict)):
            continue
        src = e["result"].get("path")
        if not src or not os.path.exists(src):
            continue
        name = safe_name(e.get("name") or "unknown")
        target_name = "%04d_%s_t%d_%s.png" % (target_eid, e["stage"], e["bindPoint"], name)
        dst = os.path.join(assets_dir, target_name)
        shutil.copy2(src, dst)
        archived.append({"src": src, "dst": dst, "name": target_name, "kind": "texture",
                         "stage": e["stage"], "bindPoint": e["bindPoint"],
                         "source": "%s@%s" % (e.get("name") or MISSING, e["bindPoint"]),
                         "bytes": os.path.getsize(dst)})
    if mesh and mesh["ok"] and os.path.exists(mesh["outputPath"]):
        target_name = "%04d_mesh_vs-out.obj" % target_eid
        dst = os.path.join(assets_dir, target_name)
        shutil.copy2(mesh["outputPath"], dst)
        archived.append({"src": mesh["outputPath"], "dst": dst, "name": target_name,
                         "kind": "mesh", "source": "export_mesh(vs-out)",
                         "bytes": os.path.getsize(dst)})
    if snapshot and snapshot["ok"] and isinstance(snapshot["result"], dict):
        snap_files = snapshot["result"].get("files") or []
        snap_dir = os.path.join(assets_dir, "snapshot_%04d" % target_eid)
        os.makedirs(snap_dir, exist_ok=True)
        total = 0
        for f in snap_files:
            if os.path.exists(f):
                dst = os.path.join(snap_dir, os.path.basename(f))
                shutil.copy2(f, dst)
                total += os.path.getsize(dst)
        archived.append({"src": snapshot["outputDir"], "dst": snap_dir,
                         "name": "snapshot_%04d/" % target_eid, "kind": "snapshot",
                         "source": "export_snapshot", "bytes": total,
                         "fileCount": len(snap_files)})
    tex_stats = {}
    for e in exports:
        if e["kind"] == "texture" and e["ok"] and e.get("resourceId"):
            st, sok, _, _ = sess.call("P4", "get_texture_stats",
                                      {"resourceId": e["resourceId"], "mip": 0, "slice": 0},
                                      quiet=True)
            if sok:
                tex_stats[e["resourceId"]] = st
    for t_ in textures:
        for arc in archived:
            if arc["kind"] == "texture" and arc.get("stage") == t_["stage"] and \
                    arc.get("bindPoint") == t_["bindPoint"]:
                t_["assetName"] = arc["name"]
    return {"exports": exports, "textures": textures, "textureTotal": tex_total,
            "scanNeeded": scan_needed, "archived": archived, "mesh": mesh,
            "snapshot": snapshot, "texStats": tex_stats, "exportDir": export_dir,
            "rtCount": rt_count}


# --------------------------------------------------------------------------- #
# report rendering
# --------------------------------------------------------------------------- #
def pass_rows(p1):
    if p1["passes"]:
        return p1["passes"], "list_passes（marker）"
    return p1["pass_stats"], "get_pass_statistics（synthetic）"


def render_pass_report(a):
    p1 = a["p1"]
    rows, source = pass_rows(p1)
    out = []
    out.append("# P1 · Pass 骨架（真实截帧）\n")
    out.append("> 生成：`pro/tools/rdc_analyze.py`。数据来源：%s。所有字段名取自工具实际返回。\n" % source)
    out.append("> synthetic 段不是引擎命名 Pass；三角形字段为 indices×instances/3 的估算。"
               "纯 Dispatch 段的 RT 可能是遗留绑定，应以 UAV 判断计算输出。\n")
    if p1.get("skipped"):
        out.append("> 本轮按预算跳过：" + ", ".join(p1["skipped"]) + "；使用完整 Draw 列表作为最小骨架。\n")
    out.append("## Pass 骨架表\n")
    out.append("| Pass 名 | 起始事件 | Draw 数 | Dispatch 数 | 三角形 | RT 宽×高 | 附件数 | synthetic |")
    out.append("|---|---|---|---|---|---|---|---|")
    for p in rows:
        size = "%dx%d" % (p.get("rtWidth") or 0, p.get("rtHeight") or 0)
        if not (p.get("rtWidth") or p.get("rtHeight")):
            size += "（无颜色 RT）"
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            md_cell(p.get("name")), md_cell(p.get("eventId")), md_cell(p.get("drawCount")),
            md_cell(p.get("dispatchCount")), md_cell(p.get("totalTriangles")), size,
            md_cell(p.get("attachmentCount")), md_cell(p.get("synthetic"))))
    out.append("")
    out.append("**Pass 数**：%d（来源：%s）；`list_passes.count=%d`。\n" % (
        len(rows), source, len(p1["passes"])))
    flags = Counter(d.get("flags") or "" for d in p1["draws"])
    out.append("## Draw 分布（list_draws，%d 条）\n" % len(p1["draws"]))
    out.append("| flags | 条数 |")
    out.append("|---|---|")
    for k, v in flags.most_common():
        out.append("| %s | %d |" % (md_cell(k), v))
    out.append("")
    out.append("## Pass 依赖图（Mermaid，由 get_pass_deps.edges 生成）\n")
    out.append("```mermaid")
    out.extend(mermaid(p1["deps"]))
    out.append("```\n")
    top = (p1["stats"] or {}).get("topDraws") or []
    if top:
        out.append("## get_stats.topDraws（前 10）\n")
        out.append("| eventId | name | numIndices |")
        out.append("|---|---|---|")
        for d in top[:10]:
            out.append("| %s | %s | %s |" % (md_cell(d.get("eventId")), md_cell(d.get("name")),
                                             md_cell(d.get("numIndices"))))
        out.append("")
    return "\n".join(out)


def mermaid(edges):
    nodes = OrderedDict()
    pairs = OrderedDict()
    for e in edges:
        s, d = e.get("srcPass") or "", e.get("dstPass") or ""
        for n in (s, d):
            if n not in nodes:
                nodes[n] = "n%d" % len(nodes)
        key = (s, d)
        pairs.setdefault(key, []).extend(e.get("resources") or [])
    if not nodes:
        return ["flowchart LR", "  empty[\"no pass dependency edges\"]"]
    lines = ["flowchart LR"]
    for name, nid in nodes.items():
        lines.append('  %s["%s"]' % (nid, name.replace('"', "")))
    for (s, d), res in pairs.items():
        label = "resources×%d" % len(res) if len(res) > 1 else (res[0] if res else "resources")
        lines.append('  %s -->|"%s"| %s' % (nodes[s], label.replace('"', ""), nodes[d]))
    return lines


def render_draw_report(a):
    p1 = a["p1"]
    draws = p1["draws"]
    ranked = sorted(draws, key=draw_score, reverse=True)
    out = ["# P2 · Draw 明细与目标定位（真实截帧）\n",
           "> 数据来源：`list_draws {limit:2000}`（%d 条）与 `get_draw_info`。\n" % len(draws),
           "## 三角形数 Top 10\n",
           "| eventId | flags | numIndices | numInstances | name |",
           "|---|---|---|---|---|"]
    for d in ranked[:10]:
        out.append("| %s | %s | %s | %s | %s |" % (
            d.get("eventId"), md_cell(d.get("flags")), d.get("numIndices"),
            d.get("numInstances"), md_cell(d.get("name"))))
    out.append("")
    out.append("## 目标候选表（get_pipeline_state + get_bindings + get_draw_info）\n")
    out.append("| 事件号 | 名称 | flags | numIndices | numInstances | VS resourceId | PS resourceId | RT 格式 | RT 宽×高 | 绑定纹理数 | 候选理由 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for row in a["p2"]["candidates"]:
        eid = row["eventId"]
        pipe = row["pipeline"]
        stages = (row["bindings"] or {}).get("stages") or {}
        tex_count = sum(len((s or {}).get("readOnlyResources") or []) for s in stages.values())
        rts = pipe.get("renderTargets") or []
        fmts = ", ".join(sorted(set(r.get("format") or MISSING for r in rts))) or MISSING
        sizes = ", ".join(sorted(set("%dx%d" % (r.get("width") or 0, r.get("height") or 0) for r in rts))) or MISSING
        d = next((x for x in draws if x["eventId"] == eid), {})
        if eid == a["p2"]["target_eid"] and a["p2"].get("reason"):
            reason = a["p2"]["reason"]
        else:
            reason = "候选：numIndices×numInstances=%d" % draw_score(d)
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (
            eid, md_cell(row["draw_info"].get("name")), md_cell(row["draw_info"].get("flags")),
            md_cell(row["draw_info"].get("numIndices")), md_cell(row["draw_info"].get("numInstances")),
            md_cell((pipe.get("vertexShader") or {}).get("resourceId")),
            md_cell((pipe.get("pixelShader") or {}).get("resourceId")),
            fmts, sizes, tex_count, md_cell(reason)))
    out.append("")
    out.append("**选定目标事件**：`%s`；理由：%s。\n" % (a["p2"]["target_eid"], a["p2"]["reason"]))
    out.append("## 全量 Draw 表（list_draws 原样字段）\n")
    out.append("| eventId | drawIndex | flags | name | numIndices | numInstances |")
    out.append("|---|---|---|---|---|---|")
    for d in draws:
        out.append("| %s | %s | %s | %s | %s | %s |" % (
            d.get("eventId"), d.get("drawIndex") if d.get("drawIndex") is not None else MISSING,
            md_cell(d.get("flags")), md_cell(d.get("name")), d.get("numIndices"), d.get("numInstances")))
    out.append("")
    return "\n".join(out)


def render_logic_report(a):
    p3 = a["p3"]
    eid = a["p2"]["target_eid"]
    out = ["# P3 · Shader 反射 / 常量缓冲 / 纹理绑定（真实截帧）\n",
           "> 目标事件 `%s`。CB 数值原样输出（不四舍五入）。\n" % eid,
           "## Shader 反射（get_shader mode=reflect）\n",
           "| stage | entryPoint | resourceId | constantBlocks | inputSignature | outputSignature |",
           "|---|---|---|---|---|---|"]
    for stage in STAGE_ORDER:
        ref = p3["reflects"].get(stage)
        if not ref:
            continue
        out.append("| %s | %s | %s | %d | %d | %d |" % (
            stage, md_cell(ref.get("entryPoint")), md_cell(ref.get("resourceId")),
            len(ref.get("constantBlocks") or []), len(ref.get("inputSignature") or []),
            len(ref.get("outputSignature") or [])))
    out.append("")
    out.append("## 常量缓冲清单（list_cbuffers）\n")
    out.append("| stage | index | name | bindSet | bindSlot | byteSize | variableCount | bufferBacked |")
    out.append("|---|---|---|---|---|---|---|---|")
    nodecoded = 0
    for cb in p3["cbuffers"]:
        m = cb["meta"]
        out.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            cb["stage"], m.get("index"), md_cell(m.get("name")), m.get("bindSet"),
            m.get("bindSlot"), m.get("byteSize"), m.get("variableCount"), m.get("bufferBacked")))
        c = cb.get("contents")
        if not c or not c.get("variables"):
            nodecoded += 1
    out.append("")
    out.append("## 常量缓冲变量值（get_cbuffer_contents）\n")
    for cb in p3["cbuffers"]:
        c = cb.get("contents")
        out.append("### `%s` stage=%s index=%s bindSet=%s bindSlot=%s byteSize=%s\n" % (
            md_cell(cb["meta"].get("name")) if c else md_cell(cb["meta"].get("name")),
            cb["stage"], cb["meta"].get("index"),
            (c or {}).get("bindSet", MISSING), (c or {}).get("bindSlot", MISSING),
            (c or {}).get("byteSize", MISSING)))
        if not c or not c.get("variables"):
            out.append("未获取（工具未返回 variables；原因：%s）\n" % md_cell(cb.get("error")))
            continue
        out.append("| 变量名 | 类型 | rows×cols | 实际值 | 变量名状态 |")
        out.append("|---|---|---|---|---|")
        for var in c["variables"]:
            key, values = values_of(var)
            if values is None:
                text = MISSING
            else:
                text = ", ".join(repr(v) for v in values)
            name = var.get("name") or MISSING
            state = "编译器生成名（变量名缺失）" if re.match(r"^_child\d+$", name or "") else "来自反射"
            out.append("| %s | %s | %s×%s | %s | %s |" % (
                md_cell(name), md_cell(var.get("type")), var.get("rows"), var.get("columns"),
                md_cell(text), state))
        out.append("")
    out.append("**验证点**：`variables` 数量 vs `variableCount`：%s。\n" % (
        "一致" if all((cb.get("contents") or {}).get("variables") and
                      len(cb["contents"]["variables"]) == cb["meta"].get("variableCount")
                      for cb in p3["cbuffers"]) else "存在不一致或未解码"))
    out.append("## 纹理 / 采样器绑定（get_bindings）\n")
    out.append("| stage | bindPoint | 变量名 | ResourceId | 解析方式 | 导出文件名（P4 填） |")
    out.append("|---|---|---|---|---|---|")
    tex_map = {("%s|%s" % (t["stage"], t["bindPoint"])): t for t in a.get("p4", {}).get("textures", [])}
    for stage, sb in (p3["bindings"].get("stages") or {}).items():
        for ro in sb.get("readOnlyResources") or []:
            key = "%s|%s" % (stage, ro.get("bindPoint"))
            t = tex_map.get(key, {})
            out.append("| %s | %s | %s | %s | %s | %s |" % (
                stage, ro.get("bindPoint"), md_cell(ro.get("name")),
                md_cell(ro.get("resourceId") or t.get("resourceId")),
                md_cell(t.get("method") or "未获取"),
                md_cell(t.get("assetName") or MISSING)))
        for ro in sb.get("samplers") or []:
            out.append("| %s | %s | %s | 未获取（sampler） | samplers | - |" % (
                stage, ro.get("bindPoint"), md_cell(ro.get("name"))))
    out.append("")
    out.append("## 反汇编关键模式命中（get_shader mode=disasm, stage=%s）\n" %
               md_cell(p3.get("pattern_stage")))
    out.append("| 关键词 | 命中行数 | 首次行号 |")
    out.append("|---|---|---|")
    for hit in p3.get("pattern_hits") or []:
        out.append("| %s | %d | %s |" % (md_cell(hit["pattern"]), hit["count"],
                                        hit["firstLine"] if hit["firstLine"] else MISSING))
    out.append("")
    return "\n".join(out)


def render_asset_report(a):
    p4 = a["p4"]
    eid = a["p2"]["target_eid"]
    out = ["# P4 · 资产导出清单（真实截帧）\n",
           "> 命名规则：`{eventId}_{stage}_t{slot}_{变量名}.{ext}`；变量名缺失用 `unknown` 并在清单标注。\n",
           "| 事件号 | 原始路径 | 目标文件名 | 类型 | 来源（变量名@slot） | 字节数 | 状态 |",
           "|---|---|---|---|---|---|---|"]
    by_src = {x.get("src"): x for x in p4["archived"]}
    for e in p4["exports"]:
        if e["kind"] == "render_target":
            res = e.get("result") or {}
            src = res.get("path") or ""
            rel = "renderdoc-mcp-export/" + os.path.basename(src) if src else MISSING
            arc = by_src.get(src)
            out.append("| %s | %s | %s | RT | RT%d | %s | %s |" % (
                eid, md_cell(rel), md_cell(arc["name"] if arc else MISSING), e["index"],
                arc["bytes"] if arc else MISSING, "OK" if arc else "未导出"))
        else:
            res = e.get("result") or {}
            src = res.get("path") or ""
            rel = "renderdoc-mcp-export/" + os.path.basename(src) if src else MISSING
            arc = by_src.get(src)
            out.append("| %s | %s | %s | 纹理 | %s@%s | %s | %s |" % (
                eid, md_cell(rel), md_cell(arc["name"] if arc else MISSING),
                md_cell(e.get("name")), e.get("bindPoint"),
                arc["bytes"] if arc else MISSING,
                "OK" if arc else ("未导出：" + md_cell(e.get("error")))))
    mesh = p4.get("mesh") or {}
    if mesh.get("ok"):
        arc = by_src.get(mesh.get("outputPath"))
        out.append("| %s | %s | %s | 网格 | export_mesh(vs-out) | %s | %s |" % (
            eid, "export_mesh → mesh_%04d.obj" % eid, md_cell(arc["name"] if arc else MISSING),
            arc["bytes"] if arc else MISSING, "OK" if arc else "未导出"))
    snap = p4.get("snapshot") or {}
    if snap.get("ok"):
        arc = by_src.get(snap.get("outputDir"))
        out.append("| %s | %s | %s | 快照 | export_snapshot | %s | %s |" % (
            eid, "export_snapshot → snapshot_%04d/" % eid, md_cell(arc["name"] if arc else MISSING),
            arc["bytes"] if arc else MISSING, "OK" if arc else "未导出"))
    out.append("")
    out.append("## 纹理数值校验（get_texture_stats）\n")
    out.append("| ResourceId | min(float) | max(float) | 判定 |")
    out.append("|---|---|---|---|")
    for rid, st in (p4.get("texStats") or {}).items():
        mn = (st.get("min") or {}).get("floatValue")
        mx = (st.get("max") or {}).get("floatValue")
        verdict = "未获取"
        if mn and mx:
            verdict = "全黑" if max(mx) == 0 else ("常量值" if min(mn) == max(mx) else "有变化")
        out.append("| %s | %s | %s | %s |" % (
            rid, md_cell(", ".join(repr(v) for v in mn) if mn else MISSING),
            md_cell(", ".join(repr(v) for v in mx) if mx else MISSING), verdict))
    out.append("")
    out.append("**文件核对**：以下文件均存在且字节数 > 0：\n")
    for arc in p4["archived"]:
        out.append("- `%s` — %d 字节" % (arc["name"], arc["bytes"]))
    out.append("")
    return "\n".join(out)


def render_p0(a):
    p0 = a["p0"]
    info = p0.get("info") or {}
    out = ["# P0 · 环境与前置检查（真实截帧）\n",
           "| 项 | 值 | 来源 |", "|---|---|---|",
           "| 截帧源路径 | `%s` | 输入 |" % a["capture_source"],
           "| 分析用路径 | `%s` | open_capture.path |" % display_path(p0.get("capture_open")),
           "| API | %s | get_capture_info.api |" % md_cell(info.get("api")),
           "| totalEvents | %s | get_capture_info.totalEvents |" % md_cell(info.get("totalEvents")),
           "| totalDraws | %s | get_capture_info.totalDraws |" % md_cell(info.get("totalDraws")),
           "| degraded | %s | get_capture_info.degraded |" % md_cell(info.get("degraded")),
           "| driverName | %s | get_capture_info.driverName |" % md_cell(info.get("driverName")),
           "| machineIdent | %s | get_capture_info.machineIdent |" % md_cell(info.get("machineIdent")),
           "| hasCallstacks | %s | get_capture_info.hasCallstacks |" % md_cell(info.get("hasCallstacks")),
           "| timestampBase | %s | get_capture_info.timestampBase |" % md_cell(info.get("timestampBase")),
           "| 工具面 | %d 个 | tools/list |" % p0.get("tool_count", 0),
           "| 必需工具缺失 | %s | 自检 |" % (", ".join(p0.get("required_missing") or []) or "无"),
           "| 运行库版本 | %s | renderdoc.dll 文件版本 |" % md_cell(p0.get("runtime_version")),
           "| MCP server | %s | initialize.result.serverInfo |" % md_cell(
               json.dumps(a.get("server") or {}, ensure_ascii=False)),
           ""]
    if a.get("ascii_note"):
        out.append("> **路径处置**：%s\n" % a["ascii_note"])
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="RenderDoc frame analysis harness (renderdoc-mcp 0.3.1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tools", help="dump tools/list")
    t.add_argument("--exe", default=DEFAULT_EXE)
    t.add_argument("--out", required=True)

    r = sub.add_parser("run", help="run P0-P4 and write reports")
    r.add_argument("--exe", default=DEFAULT_EXE)
    r.add_argument("--runtime-dll", default=None, help="Defaults to renderdoc.dll next to --exe")
    r.add_argument("--capture", required=True)
    r.add_argument("--out", required=True, help="work/evidence dir (raw JSON)")
    r.add_argument("--assets", default=None, help="archive dir for semantic asset names")
    r.add_argument("--scratch", default=None, help="ASCII scratch dir for export_mesh/export_snapshot")
    r.add_argument("--report-dir", default=None, help="where Markdown tables are written")
    r.add_argument("--eid", type=int, default=None, help="explicit target event id")
    r.add_argument("--reason", default=None, help="why this target was chosen")
    r.add_argument("--no-export", action="store_true")
    r.add_argument("--no-mesh", action="store_true")
    r.add_argument("--no-snapshot", action="store_true")
    r.add_argument("--max-scan", type=int, default=600, help="max textures for usage reverse scan")
    r.add_argument("--timeout", type=float, default=900)
    r.add_argument("--capture-scratch", default=None, help="ASCII directory for an isolated verified capture copy")
    r.add_argument("--detailed-passes", action="store_true", help="Opt in to expensive whole-frame pass replay on large captures")
    r.add_argument("--draw-limit", type=int, default=100000)

    args = ap.parse_args()
    if args.cmd == "run" and args.runtime_dll is None:
        args.runtime_dll = str(Path(args.exe).resolve().parent / "renderdoc.dll")
    if args.cmd == "run":
        os.makedirs(args.out, exist_ok=True)
        os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    else:
        parent = os.path.dirname(os.path.abspath(args.out))
        if parent:
            os.makedirs(parent, exist_ok=True)

    sess = Session(args.exe, timeout=getattr(args, "timeout", 900),
                   raw_dir=os.path.join(args.out, "raw") if args.cmd == "run" else None)
    started = time.time()
    analysis = {"tool": "renderdoc-mcp 0.3.1", "started": now(),
                "capture_source": os.path.abspath(getattr(args, "capture", "") or ".")}
    try:
        sess.initialize()
        tools = sess.list_tools()
        print("tools/list: %d" % len(tools))
        if args.cmd == "tools":
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump({"count": len(tools), "tools": tools}, fh, ensure_ascii=False, indent=2)
            print("wrote", args.out)
            return 0

        capture_open, ascii_note = ensure_ascii_capture(args.capture, args.capture_scratch)
        analysis["ascii_note"] = ascii_note
        analysis["capture_open"] = capture_open
        sess.capture_open = capture_open
        print("open:", capture_open)

        p0 = stage_p0(sess, tools, capture_open, analysis["capture_source"], args.runtime_dll)
        analysis["p0"] = p0
        analysis["server"] = sess.server
        if not p0["ok"]:
            analysis["failedStage"] = "P0"
            analysis["finished"] = now()
            analysis["wall_s"] = round(time.time() - started, 2)
            write_outputs(sess, analysis, args)
            print("\nP0 FAILED: %s" % p0.get("error"), file=sys.stderr)
            return 2
        print("P0 ok: api=%s events=%s draws=%s" % (
            (p0["info"] or {}).get("api"), (p0["info"] or {}).get("totalEvents"),
            (p0["info"] or {}).get("totalDraws")))

        p1 = stage_p1(sess, detailed=args.detailed_passes, draw_limit=args.draw_limit)
        analysis["p1"] = p1
        print("P1 ok: passes=%d (marker=%d), draws=%d, edges=%d" % (
            len(p1["pass_stats"]), len(p1["passes"]), len(p1["draws"]), len(p1["deps"])))

        p2 = stage_p2(sess, p1["draws"], args.eid, args.reason)
        analysis["p2"] = p2
        print("P2 target eid=%s reason=%s" % (p2["target_eid"], p2["reason"]))

        p3 = stage_p3(sess, p2["target_eid"])
        analysis["p3"] = p3
        print("P3 ok: stages=%s cbuffers=%d" % (",".join(p3["stages_present"]),
                                                len(p3["cbuffers"])))
        if not args.no_export:
            assets_dir = args.assets or os.path.join(args.out, "assets")
            scratch_dir = args.scratch or os.path.join(
                os.environ.get("TEMP") or os.environ.get("TMP") or args.out,
                "rdc", "analysis", safe_name(os.path.splitext(os.path.basename(args.capture))[0]))
            p4 = stage_p4(sess, p3, p2["target_eid"], args.out, assets_dir,
                          max_scan=args.max_scan, do_mesh=not args.no_mesh,
                          do_snapshot=not args.no_snapshot, scratch_dir=scratch_dir)
            analysis["p4"] = p4
            print("P4 ok: assets=%d" % len(p4["archived"]))
        else:
            analysis["p4"] = {"exports": [], "textures": [], "archived": [], "mesh": None,
                              "snapshot": None, "texStats": {}, "textureTotal": 0}

        analysis["finished"] = now()
        analysis["wall_s"] = round(time.time() - started, 2)
        sess.call("P6", "assert_count", {"what": "draws", "expected": p0["info"]["totalDraws"]})
        sess.call("P6", "close_capture", {})
        sess.call("P6", "session_status", {})
        write_outputs(sess, analysis, args)
    except Exception as exc:
        if args.cmd == "run":
            analysis["error"] = repr(exc)
            analysis["finished"] = now()
            write_outputs(sess, analysis, args)
        raise
    finally:
        sess.close()

    print("\nDONE in %.1fs -> %s" % (analysis.get("wall_s", 0), args.out))
    return 0


def write_outputs(sess, analysis, args):
    out = args.out
    report_dir = args.report_dir
    # raw results
    for i, rec in enumerate(sess.calls):
        fn = "%03d_%s.json" % (i, safe_name(rec["name"]))
        with open(os.path.join(out, "raw", fn), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
    # compact evidence
    evidence = {
        "tool": analysis.get("tool"),
        "started": analysis.get("started"),
        "finished": analysis.get("finished"),
        "wall_s": analysis.get("wall_s"),
        "capture_source": analysis.get("capture_source"),
        "capture_open": analysis.get("capture_open"),
        "ascii_note": analysis.get("ascii_note"),
        "server": analysis.get("server"),
        "error": analysis.get("error"),
        "p0": analysis.get("p0"),
        "p1": {"passes": (analysis.get("p1") or {}).get("passes"),
               "pass_stats": (analysis.get("p1") or {}).get("pass_stats"),
               "deps": (analysis.get("p1") or {}).get("deps"),
               "draws": (analysis.get("p1") or {}).get("draws"),
               "skipped": (analysis.get("p1") or {}).get("skipped")},
        "p2": analysis.get("p2"),
        "p3": analysis.get("p3"),
        "p4": analysis.get("p4"),
        "stageElapsed": {s: sess.stage_elapsed(s) for s in ["P0", "P1", "P2", "P3", "P4"]},
        "calls": [{k: c[k] for k in ("idx", "stage", "name", "args", "elapsed_s", "ok", "error")}
                  for c in sess.calls],
    }
    with open(os.path.join(out, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, ensure_ascii=False, indent=2)
    # reports
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)
        if analysis.get("p0"):
            write_text(os.path.join(report_dir, "00-p0-environment.md"), render_p0(analysis))
        if analysis.get("p1"):
            write_text(os.path.join(report_dir, "01-pass-skeleton.md"), render_pass_report(analysis))
        if analysis.get("p1"):
            write_text(os.path.join(report_dir, "02-target-draws.md"), render_draw_report(analysis))
        if analysis.get("p3"):
            write_text(os.path.join(report_dir, "03-cbuffers-textures.md"), render_logic_report(analysis))
        if analysis.get("p4"):
            write_text(os.path.join(report_dir, "04-assets.md"), render_asset_report(analysis))
    print("wrote evidence:", os.path.join(out, "evidence.json"))


def write_text(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())
