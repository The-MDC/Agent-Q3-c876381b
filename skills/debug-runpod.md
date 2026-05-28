---
name: debug-runpod
description: Troubleshoot RunPod serverless endpoints, GPU pods, S3 storage, and API issues
triggers: [runpod, runpod error, runpod timeout, runpod api, pod failed, serverless error, runpod s3, runpod debug, gpu pod, ampere]
roles: [reasoner, tandem, coder]
---

## Agent-Q3 RunPod config
- **Type:** Serverless (scale-to-zero) — AMPERE_16
- **Role:** Fallback compute — 2% routing weight
- **Keys:** `RUNPOD_API_KEY` (rpa_...) · `RUNPOD_S3_KEY` (rps_...)

## Quick health check
```bash
curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://api.runpod.io/v2/endpoints" | python3 -m json.tool

curl -H "Authorization: Bearer $RUNPOD_API_KEY" \
  "https://api.runpod.io/v2/$RUNPOD_ENDPOINT_ID/health"
```

## Submit test job
```bash
curl -X POST -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"ping","max_tokens":5}}' \
  "https://api.runpod.io/v2/$RUNPOD_ENDPOINT_ID/runsync"
```

## Common failures
| Error | Cause | Fix |
|---|---|---|
| `FAILED` | Worker crash / OOM | Check job logs; reduce batch size |
| `IN_QUEUE` indefinitely | Cold start — AMPERE_16 takes 30-90s | Wait |
| `401` | API key revoked | Regenerate at runpod.io/console/user/settings |
| `TIMED_OUT` | Job too slow | Increase `execution_timeout` in endpoint settings |
| S3 upload fails | Wrong key | Verify key starts with `rps_` |

## Scale-to-zero note
Workers spin down after ~5 min idle. Cold start is 30-90s — already accounted for in router (2% weight, fallback only). Never set as primary compute.

## S3 access test
```bash
aws s3 ls s3://runpod-storage/ \
  --endpoint-url https://api.runpod.io/s3 \
  --aws-access-key-id "$RUNPOD_S3_KEY" \
  --aws-secret-access-key "$RUNPOD_API_KEY"
```

## Router check (orchestrator/router.py)
RunPod = `Backend.RUNPOD`. Verify `RUNPOD_API_KEY` is set in HF Space secrets and endpoint ID is correct.
