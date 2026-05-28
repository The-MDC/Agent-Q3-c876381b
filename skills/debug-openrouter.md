---
name: debug-openrouter
description: Troubleshoot OpenRouter API, model routing, rate limits, and billing
triggers: [openrouter, openrouter error, openrouter down, model unavailable, rate limit, openrouter api, openrouter key, openrouter debug, kimi k2, openrouter credit]
roles: [reasoner, tandem]
---

## Agent-Q3 OpenRouter config
- **Model:** `moonshotai/kimi-k2` (K2.6 swarm orchestrator — 10% routing weight)
- **Workspace:** https://openrouter.ai/workspaces/agent-q3
- **Key:** `OPENROUTER_API_KEY` (sk-or-v1-fd7497... Agent-Q3 workspace key)

## Quick health check
```bash
# Test key + model
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"moonshotai/kimi-k2","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' \
  "https://openrouter.ai/api/v1/chat/completions"

# Check credit balance
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  "https://openrouter.ai/api/v1/auth/key"
```

## Common errors
| HTTP | Meaning | Fix |
|---|---|---|
| `401` | Invalid key | Regenerate at openrouter.ai/keys |
| `402` | No credits | Top up at openrouter.ai/credits |
| `429` | Rate limit | Retry with exponential backoff |
| `503` | Provider down | Wait or use Moonshot API primary |
| `400 context_length_exceeded` | Prompt too long | Use Kimi-Linear (1M ctx) instead |

## Retry pattern
```python
async def call_with_retry(payload, max_retries=3):
    for i in range(max_retries):
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", json=payload)
        if resp.status_code == 429:
            await asyncio.sleep(2 ** i)
            continue
        resp.raise_for_status()
        return resp.json()
```

## preserve_thinking (required for Kimi K2.6)
```json
{
  "model": "moonshotai/kimi-k2",
  "messages": [...],
  "extra_body": {"preserve_thinking": true}
}
```

## Routing note
OpenRouter is fallback (10%): Moonshot API (37%) → OpenRouter (10%) → HF Router (8%) → RunPod (2%).
If Moonshot primary is down, OpenRouter absorbs the overflow automatically.
Pricing: $0.73/1M input · $3.49/1M output for K2.6.
