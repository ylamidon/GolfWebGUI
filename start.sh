#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

env_file=".env"
example_file=".env.example"

print_help() {
  cat <<'TEXT'
NeuroGolf Lab startup

Required for export:
  HF_TOKEN    Hugging Face token with write access to your model repo.
  HF_REPO_ID  Hugging Face model repo, for example username/neurogolf-handcrafted.

Runtime:
  HOST        Bind host. Use 127.0.0.1 behind a tunnel. Default: 127.0.0.1.
  PORT        Bind port. Default: 8081.

Optional:
  PUBLIC_HOSTNAME        Public tunnel hostname, if any.
  CLOUDFLARE_API_TOKEN   Optional deployment automation token.
  GITHUB_TOKEN           Optional token for git automation on private machines.

Secrets stay in .env. Do not commit .env.
TEXT
}

ensure_env() {
  if [[ -f "$env_file" ]]; then
    return
  fi
  if [[ -f "$example_file" ]]; then
    cp "$example_file" "$env_file"
  else
    cat > "$env_file" <<'ENV'
HF_TOKEN=""
HF_REPO_ID="your-hf-username/neurogolf-handcrafted"
HOST="127.0.0.1"
PORT="8081"
PUBLIC_HOSTNAME=""
CLOUDFLARE_API_TOKEN=""
GITHUB_TOKEN=""
ENV
  fi
  echo "Created .env from template."
  print_help
}

set_env_value() {
  local key="$1"
  local value="$2"
  python3 - "$env_file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
line = f'{key}="{value}"'
lines = path.read_text().splitlines() if path.exists() else []
for index, current in enumerate(lines):
    if current.startswith(f"{key}="):
        lines[index] = line
        break
else:
    lines.append(line)
path.write_text("\n".join(lines) + "\n")
PY
}

read_env_value() {
  local key="$1"
  python3 - "$env_file" "$key" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
for line in path.read_text().splitlines():
    if line.startswith(f"{key}="):
        print(line.split("=", 1)[1].strip().strip('"').strip("'"))
        break
PY
}

prompt_missing() {
  local hf_token
  local hf_repo
  hf_token="$(read_env_value HF_TOKEN || true)"
  hf_repo="$(read_env_value HF_REPO_ID || true)"

  if [[ -z "$hf_token" ]]; then
    read -r -p "Enter HF_TOKEN for artifact upload, or press Enter to skip exports: " hf_token
    if [[ -n "$hf_token" ]]; then
      set_env_value HF_TOKEN "$hf_token"
    fi
  fi

  if [[ -z "$hf_repo" || "$hf_repo" == "your-hf-username/neurogolf-handcrafted" ]]; then
    read -r -p "Enter HF_REPO_ID, for example username/neurogolf-handcrafted: " hf_repo
    if [[ -n "$hf_repo" ]]; then
      set_env_value HF_REPO_ID "$hf_repo"
    fi
  fi
}

ensure_env
prompt_missing

set -a
source "$env_file"
set +a

host="${HOST:-127.0.0.1}"
port="${PORT:-8081}"

cat <<TEXT

Starting NeuroGolf Lab
  URL: http://${host}:${port}
  HF_REPO_ID: ${HF_REPO_ID:-not set}

Run headless agent export examples from another shell:
  python3 scripts/agent_export.py --task task276 --color-remap '{"6":2}'
  python3 scripts/agent_export.py --task task010 --graph graph.json

TEXT

exec python3 -m uvicorn server:app --host "$host" --port "$port"
