---
name: debug-hf
description: Troubleshoot HuggingFace Spaces, datasets, models, tokens, and API issues
triggers: [huggingface, hf space, space down, build failed, space error, hf logs, space restart, hf api, hf token, hf dataset error, space sleeping, space broken, hf debug]
roles: [reasoner, tandem, coder]
---

## Space health check
```bash
# Status
curl -s "https://huggingface.co/api/spaces/MADdegens/Agent-Q3" | python3 -m json.tool | grep -E '"stage"|"runtime"'

# Stream runtime logs (live tail — like docker logs -f)
curl -N -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/MADdegens/Agent-Q3/logs/run"

# Stream build logs
curl -N -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/MADdegens/Agent-Q3/logs/build"
```
Spaces: `MADdegens/Agent-Q3` · `MADdegens/agent-q3-compiler` · `madDegen/job-automation-agent`

## Space stages
| Stage | Meaning | Action |
|---|---|---|
| `BUILDING` | Docker build in progress | Watch build logs |
| `BUILD_ERROR` | Dockerfile/pip failed | Fix Dockerfile, repush |
| `RUNNING` | Healthy | None |
| `RUNTIME_ERROR` | Container crashed | Check runtime logs |
| `SLEEPING` | Auto-paused (free tier) | Hit any endpoint or click Restart |
| `NO_APP_FILE` | Missing entry point | Push Dockerfile or app.py |

## Restart a space
```bash
curl -X POST -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/MADdegens/Agent-Q3/restart"
```

## Check / set secrets
```bash
# List secret names (values hidden)
curl -H "Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/api/spaces/MADdegens/Agent-Q3/secrets"

# Add/update a secret
curl -X POST -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key":"MOONSHOT_API_KEY","value":"<value>"}' \
  "https://huggingface.co/api/spaces/MADdegens/Agent-Q3/secrets"
```
**Still missing in MADdegens/Agent-Q3:** `MOONSHOT_API_KEY` · `OLLAMA_BASE_URL`

## Token issues
- `401` → token expired or wrong scope; regenerate at huggingface.co/settings/tokens
- Required scopes: `write` + `manage` for spaces operations
- Two tokens available: `HF_TOKEN` (org write) · `HF_TOKEN_2` (read fallback)

## Dataset / model errors
- `403` on gated repo → request access or verify token has org read permission
- `404` on dataset → check `MADdegens/agent-q3` vs `madDegen/agent-q3` capitalisation
- Dataset viewer Not Found → no parquet files uploaded yet (bucket is empty)

## Build failures — top causes
1. pip install conflict → pin versions in requirements.txt
2. COPY path wrong → paths must match repo structure exactly
3. OOM during build → split heavy `pip install` across multiple RUN layers
4. Port mismatch → HF Spaces requires `PORT=7860`; ensure uvicorn binds to it

## Python (huggingface_hub)
```python
from huggingface_hub import HfApi
api = HfApi(token=HF_TOKEN)
api.space_info("MADdegens/Agent-Q3")
api.restart_space("MADdegens/Agent-Q3")
api.list_repo_files("MADdegens/Agent-Q3", repo_type="space")
```
