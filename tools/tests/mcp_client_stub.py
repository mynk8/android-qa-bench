"""Minimal scripted MCP client for tests: reads mcp.json, spawns the device server,
runs a fixed tool sequence, and writes what it saw to ./transcript.json."""
import json
import subprocess
import sys
from pathlib import Path

cfg = json.loads(Path(sys.argv[1]).read_text())["mcpServers"]["device"]
script = json.loads(sys.argv[2])
env = dict(__import__("os").environ, **cfg.get("env", {}))
p = subprocess.Popen([cfg["command"], *cfg["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, env=env)
n = 0


def rpc(method, params=None):
    global n
    n += 1
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}}) + "\n")
    p.stdin.flush()
    return json.loads(p.stdout.readline())


out = {"init": rpc("initialize", {"protocolVersion": "2025-06-18"})}
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
p.stdin.flush()
out["tools"] = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
out["calls"] = []
for name, args in script:
    out["calls"].append({"tool": name, "result": rpc("tools/call", {"name": name, "arguments": args})["result"]})
    Path("transcript.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["calls"][-1])[:4000], flush=True)
Path("transcript.json").write_text(json.dumps(out, indent=1))
p.stdin.close()
p.wait(timeout=10)
