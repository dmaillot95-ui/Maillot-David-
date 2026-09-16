#!/usr/bin/env bash
set -euo pipefail

# Install CEREBRON Ω autonomous runtime on an EXISTING Linux machine.
# This does not create hardware. It turns the current machine into a local zero-euro node.

ROOT="${CEREBRON_INSTALL_ROOT:-$HOME/cerebron-physical-node}"
REPO_URL="${CEREBRON_GIT_URL:-https://github.com/dmaillot95-ui/Maillot-David-.git}"
PYTHON="${PYTHON:-python3}"

command -v git >/dev/null || { echo 'git required'; exit 2; }
command -v "$PYTHON" >/dev/null || { echo 'python3 required'; exit 2; }

if [ ! -d "$ROOT/.git" ]; then
  git clone --depth 1 "$REPO_URL" "$ROOT"
else
  git -C "$ROOT" pull --ff-only
fi

"$PYTHON" "$ROOT/cerebron/physical_node/node.py" init

mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/cerebron-physical-node.service" <<EOF
[Unit]
Description=CEREBRON Omega Physical Node
After=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=CEREBRON_NODE_ROOT=%h/.cerebron-node
ExecStart=/usr/bin/env python3 $ROOT/cerebron/physical_node/node.py daemon --sleep 1
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

if command -v systemctl >/dev/null; then
  systemctl --user daemon-reload || true
  systemctl --user enable --now cerebron-physical-node.service || true
fi

echo "CEREBRON_PHYSICAL_NODE_INSTALLED root=$ROOT"
echo "Status: python3 $ROOT/cerebron/physical_node/node.py status"
echo "CPU test: python3 $ROOT/cerebron/physical_node/node.py enqueue CALC '{\"expr\":\"sqrt(144)+2**10\"}' && python3 $ROOT/cerebron/physical_node/node.py run-once"
echo "Optional local LLM runtime: python3 -m pip install 'transformers>=4.56,<5' 'torch>=2.4' safetensors"
