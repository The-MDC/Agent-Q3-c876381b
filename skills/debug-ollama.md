---
name: debug-ollama
description: Troubleshoot Ollama Cloud, local Ollama, model loading, VRAM, and inference issues
triggers: [ollama, ollama down, model not found, ollama error, ollama cloud, pull model, ollama timeout, ollama connection, model loading, ollama api, ollama debug]
roles: [reasoner, tandem, coder]
---

## Quick health check
```bash
# Docker-internal
curl http://ollama:11434/api/tags    # list loaded models
curl http://ollama:11434/api/ps      # running models + VRAM

# Ollama Cloud (LN-8RDGA90Ultra public endpoint)
curl -H "Authorization: Bearer $OLLAMA_API_KEY" "$OLLAMA_BASE_URL/api/tags"
```

## Model not found
```bash
# Pull from Ollama Cloud (nicholasjmcleod namespace)
curl -X POST http://ollama:11434/api/pull \
  -d '{"name":"nicholasjmcleod/kimi-linear:q6_k"}'
```
All 6 Agent-Q3 models:
- `nicholasjmcleod/kimi-linear:q6_k`
- `nicholasjmcleod/harmonic-hermes:q6_k`
- `nicholasjmcleod/qwen3-coder-53b:q6_k`
- `nicholasjmcleod/kimi-distilled:iq4_xs`
- `nicholasjmcleod/genstruct:q6_k`
- `nicholasjmcleod/infinity-parser:latest`

## Connection / timeout issues
| Symptom | Cause | Fix |
|---|---|---|
| `Connection refused :11434` | Ollama not running | `ollama serve` or check Docker |
| `timeout` on large model | Still loading into VRAM | Wait; check `/api/ps` |
| HF Space can't reach Ollama | `OLLAMA_BASE_URL` is docker-internal | Set public Cloud URL in Space secret |
| `401` from Cloud | API key expired | Regenerate at ollama.com dashboard |

## Free VRAM / unload model
```bash
curl -X POST http://ollama:11434/api/generate \
  -d '{"model":"nicholasjmcleod/kimi-linear:q6_k","keep_alive":0}'
```

## Test inference
```bash
curl http://ollama:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nicholasjmcleod/harmonic-hermes:q6_k","messages":[{"role":"user","content":"ping"}],"max_tokens":5}'
```

## Bootstrap (re-download all GGUFs)
```bash
BOOTSTRAP_MODE=true docker compose up ollama
```

## Docker logs
```bash
docker compose logs ollama --tail=50
docker compose restart ollama
docker exec -it ollama ollama list
```

## LN-8RDGA90Ultra device
- Dashboard: https://ollama.com → check device online status and public endpoint URL
- `OLLAMA_BASE_URL` in HF Space must be the **public** device URL, not `http://127.0.0.1:11434`
- SSH keys for device are in Easter Bunny file
