#!/usr/bin/env bash
set -euo pipefail
command -v node >/dev/null && command -v npm >/dev/null || { echo "Install Node.js 20+ first."; exit 1; }
node -e 'if(Number(process.versions.node.split(".")[0])<20)process.exit(1)'
connector_dir="${XDG_DATA_HOME:-$HOME/.local/share}/comiccraft-ai/codex-cli"
if [ ! -f "$connector_dir/node_modules/@openai/codex/bin/codex.js" ] || ! node "$connector_dir/node_modules/@openai/codex/bin/codex.js" --version | grep -q '0\.166\.0'; then
  npm install --prefix "$connector_dir" '@openai/codex@0.166.0' --no-audit --no-fund
fi
node "$connector_dir/node_modules/@openai/codex/bin/codex.js" --version
if login_status=$(node "$connector_dir/node_modules/@openai/codex/bin/codex.js" login status 2>&1); then
  case "$login_status" in *ChatGPT*) echo 'Existing ChatGPT login detected. Verify and enable it in the website.'; exit 0 ;; esac
fi
node "$connector_dir/node_modules/@openai/codex/bin/codex.js" login
login_status=$(node "$connector_dir/node_modules/@openai/codex/bin/codex.js" login status 2>&1)
case "$login_status" in *ChatGPT*) ;; *) echo 'Sign in with ChatGPT is required.'; exit 1 ;; esac
echo 'Refresh connector status in ComicCraft. Capabilities still need explicit testing.'
