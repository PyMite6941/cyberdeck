#!/usr/bin/env bash
#
# cyberdeck AI layer (OPT-IN) — run on the Pi AFTER the base setup.sh:
#   sudo ./setup-ai.sh
#
# Installs and memory-tunes everything needed to use Claude Code (cloud) and
# Ollama (local LLMs) on a Pi 4B/5. Idempotent — safe to re-run.
#
# What it does:
#   1. Trims idle RAM: disables printing/modem services nobody needs on a deck,
#      installs earlyoom so an LLM spike degrades gracefully instead of freezing
#   2. Node.js 22 (NodeSource) + Claude Code CLI
#   3. Ollama with a memory-tuned systemd override (models unload after 2 min,
#      one model at a time, quantised KV cache)
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run with sudo: sudo ./setup-ai.sh" >&2
    exit 1
fi

echo "==> [1/3] Trimming idle memory + installing earlyoom"
# Services a strapped-to-your-shoulder deck doesn't need (~60-100 MB + wakeups).
# Bluetooth is deliberately KEPT (wireless keyboards/mice are deck-relevant).
for svc in cups cups-browsed ModemManager; do
    if systemctl list-unit-files "$svc.service" --no-legend 2>/dev/null | grep -q "$svc"; then
        systemctl disable --now "$svc.service" 2>/dev/null || true
        echo "  disabled $svc"
    fi
done
# earlyoom: kills the fattest process BEFORE the kernel OOM-freezes the deck.
# With zram, true OOM means compressed swap is full too — act early.
apt-get update
apt-get install -y --no-install-recommends earlyoom
# Prefer sacrificing inference over the session: never kill systemd/sshd/X.
sed -i 's|^EARLYOOM_ARGS=.*|EARLYOOM_ARGS="-r 0 --avoid (^\|/)(init\|systemd\|sshd\|Xorg\|wayfire\|labwc)$"|' /etc/default/earlyoom
systemctl enable --now earlyoom
systemctl restart earlyoom

echo "==> [2/3] Installing Node.js 22 + Claude Code"
if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 20 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi
if ! command -v claude >/dev/null 2>&1; then
    npm install -g @anthropic-ai/claude-code
fi
echo "  node $(node -v), claude code installed (run 'claude' once to log in)"

echo "==> [3/3] Installing Ollama (memory-tuned)"
if ! command -v ollama >/dev/null 2>&1; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/cyberdeck.conf <<'EOF'
# cyberdeck memory tuning for Ollama on Pi 4/5 (installed by setup-ai.sh)
[Service]
# Unload model weights 2 min after last use — frees GBs back to the desktop.
Environment=OLLAMA_KEEP_ALIVE=2m
# One model resident at a time; no parallel request batching.
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_NUM_PARALLEL=1
# Quantised KV cache + flash attention: roughly halves per-context RAM.
Environment=OLLAMA_FLASH_ATTENTION=1
Environment=OLLAMA_KV_CACHE_TYPE=q8_0
EOF
systemctl daemon-reload
systemctl restart ollama 2>/dev/null || true

echo "==> [4/4] Pulling + tuning a local model (auto-detected by RAM)"
TOTAL_RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
TOTAL_RAM_GB=${TOTAL_RAM_GB:-0}

if [[ $TOTAL_RAM_GB -ge 7 ]]; then
    RECOMMENDED="qwen2.5-coder:3b"
    LABEL="Pi 5 8GB+ (qwen2.5-coder:3b, ~2 GB download)"
elif [[ $TOTAL_RAM_GB -ge 3 ]]; then
    RECOMMENDED="qwen2.5:1.5b"
    LABEL="Pi 4 4GB (qwen2.5:1.5b, ~1 GB download)"
else
    RECOMMENDED=""
    LABEL="< 3 GB RAM — skipping auto-pull (run tune-ollama.sh manually)"
fi

if [[ -n $RECOMMENDED ]]; then
    echo "  Detected ${TOTAL_RAM_GB}GB RAM → $LABEL"
    # Interactive prompt: skip if not a terminal or user says no.
    DO_PULL=true
    if [[ -t 0 ]]; then
        read -r -p "  Pull and tune now? (y/N, ~1-2 GB download) " REPLY
        [[ $REPLY =~ ^[Yy] ]] || DO_PULL=false
    fi
    if $DO_PULL; then
        echo "  Pulling $RECOMMENDED..."
        ollama pull "$RECOMMENDED"
        MODEL_NAME="${RECOMMENDED%%:*}"
        # Check if deckcoder already exists and ask before overwriting.
        if ollama list 2>/dev/null | grep -q "deckcoder"; then
            if [[ -t 0 ]]; then
                read -r -p "  Model 'deckcoder' exists. Overwrite? (y/N) " REPLY
                [[ $REPLY =~ ^[Yy] ]] || { echo "  Skipped — keeping existing deckcoder"; DO_PULL=false; }
            fi
        fi
        if $DO_PULL; then
            TMPDIR=$(mktemp -d) || { echo "Failed to create temp dir"; exit 1; }
            trap 'rm -rf "$TMPDIR"' EXIT
            echo "  Creating tuned model 'deckcoder' (num_ctx=2048, num_thread=4)..."
            cat > "$TMPDIR/deckcoder-modelfile" <<EOF
FROM $RECOMMENDED

PARAMETER num_ctx 2048
PARAMETER num_thread 4
PARAMETER num_batch 4

TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
EOF
            ollama create deckcoder -f "$TMPDIR/deckcoder-modelfile"
            echo "  Model 'deckcoder' ready. Run: ollama run deckcoder"
        fi
    else
        echo "  Skipped. Tune manually later: sudo ./ai/tune-ollama.sh $RECOMMENDED"
    fi
else
    echo "  $LABEL"
fi

echo
echo "Done. RAM-saving tip: 'deck-lite' drops to console (frees ~500 MB for inference),"
echo "'deck-gui' brings the desktop back."
