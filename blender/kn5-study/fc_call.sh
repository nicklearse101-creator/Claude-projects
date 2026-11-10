#!/usr/bin/env bash
# fc_call.sh TOOL JSON_ARGS : call one tool on the live FreeCAD AI MCP (http://127.0.0.1:3000/mcp)
python - "$1" "$2" <<'PY'
import json, sys, urllib.request
tool, args = sys.argv[1], json.loads(sys.argv[2])
req = urllib.request.Request('http://127.0.0.1:3000/mcp', data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}).encode(),
                             headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'})
r = json.loads(urllib.request.urlopen(req, timeout=300).read())
for c in r.get('result', {}).get('content', []):
    if c.get('type') == 'text': print(c['text'][:3000])
    elif c.get('type') == 'image':
        import base64; p = 'D:/ClaudeData/tmp/fc_view.png'; open(p, 'wb').write(base64.b64decode(c['data'])); print('image ->', p)
if 'error' in r: print('ERROR', r['error'])
PY
