#!/usr/bin/env bash
# tune-ollama — create/update an Ollama model with Pi-optimised parameters.
#
# Usage:
#   sudo ./tune-ollama.sh qwen2.5-coder:3b      # pull + tune a coder model
#   sudo ./tune-ollama.sh qwen2.5:1.5b           # smaller for Pi 4
#
# Creates a model called "deckcoder" (or custom --name) with these tunings:
#   - num_ctx 2048      (keep context small for ARM tok/s)
#   - num_thread 4      (pin to Pi 5's 4 performance cores)
#   - Q4_K_M quant      (4-bit — fits in RAM without swap)
#
set -euo pipefail

NAME="deckcoder"
BASE_MODEL=""
CTX=2048
THREADS=4

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name) NAME="$2"; shift 2 ;;
        --ctx) CTX="$2"; shift 2 ;;
        --threads) THREADS="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [base_model] [--name NAME] [--ctx N] [--threads N]"
            echo "Default base: qwen2.5-coder:3b"
            echo "Creates an Ollama model tuned for Pi 4/5."
            exit 0 ;;
        *) BASE_MODEL="$1"; shift ;;
    esac
done

BASE_MODEL="${BASE_MODEL:-qwen2.5-coder:3b}"

if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama is not installed. Run sudo ./setup-ai.sh first." >&2
    exit 1
fi

echo "==> Pulling base model: $BASE_MODEL"
ollama pull "$BASE_MODEL"

echo "==> Auto-detecting model chat template for $BASE_MODEL..."
# Try to detect the model's expected template format from Ollama's metadata.
MODEL_INFO=$(ollama show "$BASE_MODEL" 2>/dev/null || true)
TEMPLATE=""
if echo "$MODEL_INFO" | grep -q "<\|im_start\|>"; then
    TEMPLATE="qwen"
elif echo "$MODEL_INFO" | grep -q "\[INST\]"; then
    TEMPLATE="llama"
elif echo "$MODEL_INFO" | grep -q "<\|start_header_id\|>"; then
    TEMPLATE="llama3"
elif echo "$MODEL_INFO" | grep -q "<\|user\|>"; then
    TEMPLATE="gemma"
fi

TMPDIR=$(mktemp -d) || { echo "Failed to create temp dir"; exit 1; }
trap 'rm -rf "$TMPDIR"' EXIT

echo "==> Creating tuned model: $NAME (detected template: ${TEMPLATE:-qwen (default)})"
cat > "$TMPDIR/deckcoder-modelfile" <<EOF
FROM $BASE_MODEL

PARAMETER num_ctx $CTX
PARAMETER num_thread $THREADS
PARAMETER num_batch 4
EOF

case "$TEMPLATE" in
    llama)
        cat >> /tmp/deckcoder-modelfile <<'EOF'
TEMPLATE """[INST] {{ .System }}
{{ .Prompt }} [/INST]"""
EOF
        ;;
    llama3)
        cat >> /tmp/deckcoder-modelfile <<'EOF'
TEMPLATE """<|start_header_id|>system<|end_header_id|>
{{ .System }}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
{{ .Prompt }}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>"""
EOF
        ;;
    gemma)
        cat >> /tmp/deckcoder-modelfile <<'EOF'
TEMPLATE """<|user|>
{{ .Prompt }}<|end|>
<|assistant|>"""
EOF
        ;;
    *)
        # Default: qwen/chatml format.
        cat >> /tmp/deckcoder-modelfile <<'EOF'
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
EOF
        ;;
esac

ollama create "$NAME" -f "$TMPDIR/deckcoder-modelfile"

echo
echo "Done. Model '$NAME' is ready."
echo "  Base:      $BASE_MODEL"
echo "  Context:   $CTX tokens"
echo "  Threads:   $THREADS"
echo "  Quant:     Q4_K_M (4-bit, pulled by default)"
echo
echo "Run: ollama run $NAME"
echo "API: ollama run $NAME 'write a Python blink script for GPIO17'"
