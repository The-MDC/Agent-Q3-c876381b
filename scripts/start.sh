#!/bin/bash
# Agent Q3 — Startup script
# PRODUCTION (default): pulls models from Ollama Cloud (nicholasjmcleod namespace)
# BOOTSTRAP (BOOTSTRAP_MODE=true): download GGUFs from HF bucket → create → push to cloud
set -e

BUCKET="MADdegens/Models"
MODELS_DIR="${MODEL_CACHE_DIR:-/models}"
HF_BIN="${HF_CLI:-hf}"
OLLAMA_NAMESPACE="${OLLAMA_NAMESPACE:-nicholasjmcleod}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Agent Q3 — Cloud Model Stack                   ║"
echo "║  Kimi-Linear-48B · Harmonic-Hermes-9B · Qwen3-Coder-53B    ║"
echo "║  Kimi-Distilled-35B · Genstruct-7B · Infinity-Parser2-Pro  ║"
echo "║  Monitor: Hermes-9B watches + Qwen3-Coder remediates        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ── Start Ollama ──────────────────────────────────────────────────────────────
ollama serve &
OLLAMA_PID=$!
echo "Waiting for Ollama..."
for i in $(seq 1 60); do
  curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "✓ Ollama ready" && break
  sleep 2
done

# ── PRODUCTION: pull all models from Ollama Cloud ─────────────────────────────
pull_from_cloud() {
  local cloud_tag="$1"
  local display_name="$2"

  if ollama list | awk '{print $1}' | grep -qx "$cloud_tag"; then
    echo " ✓ $display_name ($cloud_tag) already loaded"
    return 0
  fi
  echo " ↓ Pulling $display_name from Ollama Cloud..."
  ollama pull "$cloud_tag"
  echo " ✓ $display_name → $cloud_tag"
}

# ── BOOTSTRAP: download GGUF from HF bucket → create → push to Ollama Cloud ──
create_and_push() {
  local gguf_file="$1"
  local local_tag="$2"
  local cloud_tag="$3"
  local display_name="$4"

  mkdir -p "$MODELS_DIR"
  local local_path="$MODELS_DIR/$gguf_file"

  if [ ! -f "$local_path" ]; then
    echo " ↓ Syncing $display_name from HF bucket..."
    "$HF_BIN" sync "hf://buckets/$BUCKET" "$MODELS_DIR" --include "$gguf_file"
    echo " ✓ Downloaded $gguf_file"
  else
    echo " ✓ $display_name GGUF cached at $local_path"
  fi

  echo " ⚙  Creating local Ollama model $local_tag..."
  local tmpdir
  tmpdir=$(mktemp -d)
  cat > "$tmpdir/Modelfile" << MODELEOF
FROM $local_path
PARAMETER num_ctx 32768
PARAMETER num_predict 4096
PARAMETER temperature 0.7
MODELEOF
  ollama create "$local_tag" -f "$tmpdir/Modelfile"
  rm -rf "$tmpdir"

  echo " ↑ Pushing $display_name to Ollama Cloud as $cloud_tag..."
  ollama push "$cloud_tag"
  echo " ✓ $display_name → Ollama Cloud: $cloud_tag"
}

# ── Model definitions (GGUF filename → local tag → cloud tag) ─────────────────
declare -A MODEL_GGUFS=(
  ["reasoner"]="Kimi-Linear-48B-A3B-Instruct.i1-Q6_K.gguf"
  ["tandem"]="Harmonic-Hermes-9B.i1-Q6_K.gguf"
  ["coder_dedicated"]="Qwen3-Coder-53B-A3B-Instruct-TOTAL-RECALL-v2-MASTER-CODER-L.i1-Q6_K.gguf"
  ["kimi_distilled"]="Qwen3.6-35B-A3B-Kimi-K2.6-Reasoning-Distilled.IQ4_XS.gguf"
  ["genstruct"]="Genstruct-7B.i1-Q6_K.gguf"
  ["infinity_parser"]="Infinity-Parser2-Pro"
)

declare -A LOCAL_TAGS=(
  ["reasoner"]="${REASONER_MODEL:-kimi-linear:q6_k}"
  ["tandem"]="${TANDEM_MODEL:-harmonic-hermes:q6_k}"
  ["coder_dedicated"]="${CODER_DEDICATED_MODEL:-qwen3-coder-53b:q6_k}"
  ["kimi_distilled"]="${KIMI_DISTILLED_MODEL:-kimi-distilled:iq4_xs}"
  ["genstruct"]="${GENSTRUCT_MODEL:-genstruct:q6_k}"
  ["infinity_parser"]="${INFINITY_PARSER_MODEL:-infinity-parser:latest}"
)

declare -A CLOUD_TAGS=(
  ["reasoner"]="$OLLAMA_NAMESPACE/${REASONER_MODEL:-kimi-linear:q6_k}"
  ["tandem"]="$OLLAMA_NAMESPACE/${TANDEM_MODEL:-harmonic-hermes:q6_k}"
  ["coder_dedicated"]="$OLLAMA_NAMESPACE/${CODER_DEDICATED_MODEL:-qwen3-coder-53b:q6_k}"
  ["kimi_distilled"]="$OLLAMA_NAMESPACE/${KIMI_DISTILLED_MODEL:-kimi-distilled:iq4_xs}"
  ["genstruct"]="$OLLAMA_NAMESPACE/${GENSTRUCT_MODEL:-genstruct:q6_k}"
  ["infinity_parser"]="$OLLAMA_NAMESPACE/${INFINITY_PARSER_MODEL:-infinity-parser:latest}"
)

declare -A DISPLAY_NAMES=(
  ["reasoner"]="Kimi-Linear-48B (1M-ctx Preprocessor)"
  ["tandem"]="Harmonic-Hermes-9B (Tandem+Monitor)"
  ["coder_dedicated"]="Qwen3-Coder-53B TOTAL-RECALL (Primary Coder)"
  ["kimi_distilled"]="Qwen3.6-35B Kimi-K2.6-Distilled IQ4_XS (Structured Reasoning)"
  ["genstruct"]="Genstruct-7B (Generator)"
  ["infinity_parser"]="Infinity-Parser2-Pro (Parser)"
)

ROLES=("reasoner" "tandem" "coder_dedicated" "kimi_distilled" "genstruct" "infinity_parser")

if [ "${BOOTSTRAP_MODE:-false}" = "true" ]; then
  echo ""
  echo "=== BOOTSTRAP MODE: Syncing models from HF bucket → Ollama Cloud ==="
  echo ""

  echo " ↓ Syncing all GGUFs from hf://buckets/$BUCKET → $MODELS_DIR ..."
  mkdir -p "$MODELS_DIR"
  "$HF_BIN" sync "hf://buckets/$BUCKET" "$MODELS_DIR"
  echo " ✓ Bucket synced to $MODELS_DIR"
  echo ""

  for role in "${ROLES[@]}"; do
    gguf="${MODEL_GGUFS[$role]}"
    local_tag="${LOCAL_TAGS[$role]}"
    cloud_tag="${CLOUD_TAGS[$role]}"
    name="${DISPLAY_NAMES[$role]}"

    if [ "$role" = "infinity_parser" ]; then
      if ! "$HF_BIN" buckets list "$BUCKET" 2>/dev/null | grep -q "Infinity-Parser2-Pro"; then
        echo " ⚠  Infinity-Parser2-Pro not yet in bucket — skipping"
        continue
      fi
    fi

    create_and_push "$gguf" "$local_tag" "$cloud_tag" "$name"
  done

  echo ""
  echo "✓ All models pushed to Ollama Cloud under $OLLAMA_NAMESPACE/"
  ollama list

else
  echo ""
  echo "=== PRODUCTION MODE: Pulling models from Ollama Cloud ==="
  echo ""
  for role in "${ROLES[@]}"; do
    cloud_tag="${CLOUD_TAGS[$role]}"
    name="${DISPLAY_NAMES[$role]}"
    pull_from_cloud "$cloud_tag" "$name"
  done

  echo ""
  echo "✓ All models loaded from Ollama Cloud"
  ollama list
fi

# ── Start FastAPI orchestrator ────────────────────────────────────────────────
exec python -m uvicorn orchestrator.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --log-level "${LOG_LEVEL:-info}" &
UVICORN_PID=$!

wait $OLLAMA_PID $UVICORN_PID
