#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           Agent-Q3  —  Ollama Cloud Model Stack                   ║"
echo "║           ALL inference via Ollama Cloud — no local GGUFs         ║"
echo "║           Account: nicholasjmcleod@gmail.com / LN-8RDGA90Ultra    ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

NAMESPACE="${OLLAMA_NAMESPACE:-nicholasjmcleod}"

declare -A CLOUD_TAGS=(
  ["reasoner"]="${NAMESPACE}/kimi-linear:q6_k"
  ["tandem"]="${NAMESPACE}/harmonic-hermes:q6_k"
  ["coder"]="${NAMESPACE}/ultracoder:q4_k_m"
  ["fallback"]="${NAMESPACE}/qwopus:q8_0"
  ["coder_dedicated"]="${NAMESPACE}/qwen3-coder-53b:q6_k"
  ["genstruct"]="${NAMESPACE}/genstruct:q6_k"
  ["infinity_parser"]="${NAMESPACE}/infinity-parser:latest"
)

declare -A DISPLAY_NAMES=(
  ["reasoner"]="Kimi-Linear-48B"
  ["tandem"]="Harmonic-Hermes-9B"
  ["coder"]="Ultra-Coder-Brain"
  ["fallback"]="Qwopus3.6-27B"
  ["coder_dedicated"]="Qwen3-Coder-53B"
  ["genstruct"]="Genstruct-7B"
  ["infinity_parser"]="Infinity-Parser2-Pro"
)

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

echo "[1/3] Waiting for Ollama daemon..."
MAX_WAIT=60
WAITED=0
until curl -sf http://localhost:11434/ > /dev/null 2>&1; do
  sleep 2
  WAITED=$((WAITED + 2))
  if [ $WAITED -ge $MAX_WAIT ]; then
    echo "ERROR: Ollama did not start within ${MAX_WAIT}s"
    exit 1
  fi
done
echo "      ✓ Ollama ready after ${WAITED}s"
echo ""

# ── [2/3] Verify Ollama Cloud sign-in ───────────────────────────────────────
echo "[2/3] Verifying Ollama Cloud authentication..."
if [ -f /root/.ollama/id_ed25519 ]; then
  echo "      ✓ Device key found: LN-8RDGA90Ultra"
  echo "      ✓ All cloud models accessible via ollama.com"
else
  echo ""
  echo "  ╔══════════════════════════════════════════════════════════════╗"
  echo "  ║  ⚠  CLOUD SIGN-IN REQUIRED                                   ║"
  echo "  ║                                                                ║"
  echo "  ║  No device key at /root/.ollama/id_ed25519                    ║"
  echo "  ║                                                                ║"
  echo "  ║  Option A — Mount your host ~/.ollama (recommended):          ║"
  echo "  ║    volumes:                                                    ║"
  echo "  ║      - ~/.ollama:/root/.ollama                                 ║"
  echo "  ║                                                                ║"
  echo "  ║  Option B — Sign in interactively:                            ║"
  echo "  ║    docker exec -it agent-q3-ollama ollama signin              ║"
  echo "  ║    Account: nicholasjmcleod@gmail.com                         ║"
  echo "  ╚══════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Continuing — all cloud model calls will fail until signed in."
fi
echo ""

# ── [3/3] Pull all 7 nicholasjmcleod/ cloud models ──────────────────────────
echo "[3/3] Pulling Ollama Cloud models (nicholasjmcleod/ namespace)..."
echo ""

ROLES=("reasoner" "tandem" "coder" "fallback" "coder_dedicated" "genstruct" "infinity_parser")
FAILED=0

for role in "${ROLES[@]}"; do
  tag="${CLOUD_TAGS[$role]}"
  name="${DISPLAY_NAMES[$role]}"
  echo -n "      [${role}] ${name} — ${tag} ... "
  if ollama pull "${tag}" > /dev/null 2>&1; then
    echo "✓"
  else
    echo "⚠ pull failed (will retry on first request)"
    FAILED=$((FAILED + 1))
  fi
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  Role → Ollama Cloud Model (nicholasjmcleod/ namespace):"
echo ""
echo "    reasoner        ${CLOUD_TAGS[reasoner]}        /v1/instruct /v1/chat"
echo "    tandem+monitor  ${CLOUD_TAGS[tandem]}   /v1/tandem /v1/monitor/analyze"
echo "    coder+remediate ${CLOUD_TAGS[coder]}       /v1/code /v1/monitor/remediate"
echo "    fallback        ${CLOUD_TAGS[fallback]}            /v1/fallback"
echo "    coder_dedicated ${CLOUD_TAGS[coder_dedicated]}    /v1/coder"
echo "    genstruct       ${CLOUD_TAGS[genstruct]}          /v1/generate"
echo "    parser          ${CLOUD_TAGS[infinity_parser]}  /v1/parse"
echo ""
if [ $FAILED -gt 0 ]; then
  echo "  ⚠ ${FAILED} model(s) failed to pull — check Ollama Cloud sign-in"
else
  echo "  ✓ All 7 models ready"
fi
echo ""
echo "  Ollama API: http://0.0.0.0:11434"
echo "════════════════════════════════════════════════════════════════════"

wait $OLLAMA_PID
