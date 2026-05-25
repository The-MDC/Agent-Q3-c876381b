# Agent-Q3 — Known Issues & Fixes

---

## Active Issues

### Dataset Parquet Viewer (Non-blocking)
**Status:** `parquet_failing` — HF dataset viewer returns 500 on the Parquet viewer  
**Impact:** Dataset at `madDegen/agent-q3` is accessible but the visual viewer fails  
**Workaround:** Access files directly via `huggingface_hub` or raw URLs  
**Fix:** Re-upload dataset with corrected Parquet schema when next training run completes

---

## Resolved

### Memory backend (Redis-only)
Postgres/pgvector/Supabase removed. `memory_store.py` is now Redis-only with graceful degradation when `REDIS_URL` is unset.

### Model stack
- Reasoner updated from `kimi-vl:a3b-cloud` → `moonshotai/Kimi-K2.6` BF16 via HF Router
- All local GGUF quants upgraded: Q4_K_M → Q8_0 (32B), Q4_K_M → F16 (8B)

### Deploy target
Migrated from Railway to HuggingFace Spaces. Deploy workflow: `5-hf-spaces-deploy.yml`.

### Monitor service
Removed standalone kimi-k2 monitor container. Anomaly analysis now routes through the orchestrator reasoner at `/v1/reason`.

### Compute routing
`support_model` added to `Settings` — was referenced in `cowork_ui.py` but missing from config, causing `AttributeError` at runtime.

---

## Local Dev Checks

```bash
# Lint
ruff check orchestrator/

# Unit tests
pytest tests/unit/ -v

# Health
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```
