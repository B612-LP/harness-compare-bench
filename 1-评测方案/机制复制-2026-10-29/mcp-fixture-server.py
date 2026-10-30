#!/usr/bin/env python3
"""MCP stdio fixture server：向 Codex CLI 提供与 DSH 原生夹具字节级相同的 fixture_output。

仅标准库；无网络、无 shell、无路径外访问。tools/call 时把工具文本与进程收据写入
MECHANISM_CAPTURE_DIR（与 DSH 侧 fixture-plugin-v2.mjs 相同的文件约定）。
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

PROTOCOL = "2025-06-18"


def fixture_text(size: str) -> str:
    noise = "" if size != "large" else "".join(
        "noise-%04d checksum=%s\n" % (i, hashlib.sha256(("fixture-v1-%d" % i).encode()).hexdigest())
        for i in range(420))
    return "OBSERVATION HEAD_KEY = AMBER-731\n" + noise + "OBSERVATION TAIL_KEY = COBALT-492\n"


def send(obj) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def log(event: dict) -> None:
    out = os.environ.get("MECHANISM_CAPTURE_DIR")
    if not out:
        return
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "mcp-server-log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(event, at=time.strftime("%Y-%m-%dT%H:%M:%S%z")), ensure_ascii=False) + "\n")


def main() -> int:
    text = fixture_text(os.environ.get("MECHANISM_SIZE", "large"))
    log({"event": "server-start", "size": os.environ.get("MECHANISM_SIZE"), "bytes": len(text.encode()),
         "sha256": hashlib.sha256(text.encode()).hexdigest()})
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method = msg.get("method", "")
        mid = msg.get("id")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": (msg.get("params", {}) or {}).get("protocolVersion", PROTOCOL),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mechanism-fixture", "version": "1.0"}}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [{
                "name": "fixture_output",
                "description": "Return the current instrument observation: HEAD_KEY and TAIL_KEY with optional irrelevant checksum noise. Call once, then report both observed values.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}}]}})
        elif method == "tools/call":
            out = os.environ.get("MECHANISM_CAPTURE_DIR")
            if out:
                d = Path(out)
                d.mkdir(parents=True, exist_ok=True)
                (d / "tool-output.txt").write_text(text, encoding="utf-8")
                (d / "tool-process.json").write_text(json.dumps(
                    {"kind": "mcp_stdio_deterministic_tool", "exit_code": 0,
                     "bytes": len(text.encode()), "sha256": hashlib.sha256(text.encode()).hexdigest()},
                    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log({"event": "tools-call", "bytes": len(text.encode())})
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": text}]}})
        elif method.startswith("notifications/"):
            log({"event": method})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: " + method}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
