#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Install Python 3.11+ first.'; exit 1; }
command -v node >/dev/null || { echo 'Install Node.js 20+ first.'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
node -e 'if(Number(process.versions.node.split(".")[0])<20)throw Error("Node.js 20+ required")'
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
if [ ! -f .env ]; then cp .env.example .env; fi
.venv/bin/python -m pip install -e .
if [ ! -d frontend/node_modules ]; then npm --prefix frontend ci; fi
npm --prefix frontend run build
.venv/bin/python -m app.services.diagnostics
echo 'Open http://127.0.0.1:8000 ? Ctrl+C stops the server.'
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
