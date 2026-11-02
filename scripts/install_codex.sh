#!/usr/bin/env bash
set -euo pipefail
command -v node >/dev/null && command -v npm >/dev/null || { echo "Install Node.js 20+ first."; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<20)process.exit(1)'
connector_dir="${XDG_DATA_HOME:-$HOME/.local/share}/comiccraft-ai/codex-cli"
if [ ! -f "$connector_dir/node_modules/@openai/codex/bin/codex.js" ]; then
  npm install --prefix "$connector_dir" '@openai/codex@0.166.0' --no-audit --no-fund
fi
node "$connector_dir/node_modules/@openai/codex/bin/codex.js" --version
node "$connector_dir/node_modules/@openai/codex/bin/codex.js" login
echo 'Refresh connector status in ComicCraft. Capabilities still need explicit testing.'
