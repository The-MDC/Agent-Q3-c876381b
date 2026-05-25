#!/bin/bash
set -e

echo "╔════════════════════════════════════════════╗"
echo "║         Agent Q3 - Ollama Stack            ║"
echo "║  Reasoner: Qwen2.5-VL-32B  Q8_0           ║"
echo "║  Support:  Qwen3-8B Kimi-K2  F16           ║"
echo "║  Coder:    QwQ-32B  Q8_0                   ║"
echo "╚════════════════════════════════════════════╝"

# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to start..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama is ready"
    break
  fi
  sleep 2
done

pull_model() {
  local model=$1
  local label=$2
  # Exact tag match — check full model:tag string
  if ollama list | awk '{print $1}' | grep -qx "$model"; then
    echo " ✓ ${label} already cached, skipping pull"
  else
    echo " ↓ Pulling ${label}..."
    ollama pull "$model"
    echo " ✓ ${label} ready"
  fi
}

pull_model "${REASONER_MODEL:-hf.co/unsloth/Qwen2.5-VL-32B-Instruct-GGUF:Q8_0}" "Qwen2.5-VL-32B Q8_0 (Reasoner)"
pull_model "${SUPPORT_MODEL:-hf.co/TeichAI/Qwen3-8B-Kimi-K2-Thinking-Distill-GGUF:F16}" "Qwen3-8B Kimi-K2 F16 (Support)"
pull_model "${CODER_MODEL:-hf.co/unsloth/QwQ-32B-GGUF:Q8_0}" "QwQ-32B Q8_0 (Deep Research/Coder)"

echo ""
echo "✓ All models ready. Ollama running on :11434"
echo ""
ollama list

# Keep Ollama running
wait $OLLAMA_PID
