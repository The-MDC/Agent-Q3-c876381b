#!/bin/bash
# Upload local GGUFs to MADdegens/Models HF bucket
# Usage:
#   ./scripts/upload-models.sh              — sync ./data to bucket
#   DATA_DIR=./my-models ./scripts/upload-models.sh

set -e

BUCKET="MADdegens/Models"
DATA_DIR="${DATA_DIR:-./data}"
HF_BIN="${HF_CLI:-hf}"

if [ -z "$HF_TOKEN" ]; then
  echo "ERROR: HF_TOKEN is not set — required to write to the bucket"
  echo "  export HF_TOKEN=hf_..."
  exit 1
fi

if [ ! -d "$DATA_DIR" ]; then
  echo "ERROR: $DATA_DIR does not exist"
  echo "  Place GGUFs in $DATA_DIR/ then re-run"
  exit 1
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Uploading GGUFs → hf://buckets/$BUCKET      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Source : $DATA_DIR"
echo "Bucket : hf://buckets/$BUCKET"
echo ""
echo "Files to upload:"
ls -lh "$DATA_DIR"/*.gguf 2>/dev/null || ls -lh "$DATA_DIR" 2>/dev/null
echo ""

"$HF_BIN" sync "$DATA_DIR" "hf://buckets/$BUCKET"

echo ""
echo "✓ Sync complete — hf://buckets/$BUCKET"
echo ""
echo "Next: run BOOTSTRAP_MODE=true docker compose up ollama"
echo "  to pull these GGUFs, create Ollama models, and push to nicholasjmcleod/ cloud"
