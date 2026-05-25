# Agent-Q3 — Deployment Guide

**Platform:** HuggingFace Spaces (Docker SDK)  
**Spaces:** `madDegen/agent-q3-space` (Orchestrator) · `madDegen/agent-q3-webui` (WebUI)

---

## Quick Deploy

Push to `main` — `5-hf-spaces-deploy.yml` auto-deploys both Spaces.

```bash
git push origin main
```

Or trigger manually via GitHub Actions → `🚀 Deploy → HuggingFace Spaces` → Run workflow.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│             HF Space: agent-q3-space :7860              │
│                                                         │
│  FastAPI Orchestrator                                   │
│  ├── POST /v1/chat    — auto-classify → route           │
│  ├── POST /v1/reason  — Kimi-K2.6 BF16 (HF Router)    │
│  ├── POST /v1/code    — Qwen3-48B cloud                │
│  ├── POST /v1/tandem  — reason → implement             │
│  ├── GET  /health     — all backends                   │
│  └── GET  /cowork/mcp — Claude Cowork (8 tools)        │
│                                                         │
│  Compute cascade:                                       │
│  Ollama Cloud → HF Router → OpenRouter → RunPod        │
└─────────────────────────────────────────────────────────┘
         ↑
┌─────────────────────────────────────────────────────────┐
│             HF Space: agent-q3-webui :7860              │
│                                                         │
│  Open WebUI + Pipelines                                 │
│  ├── agent-q3-router    — classify → route              │
│  ├── agent-q3-tandem    — reason + implement            │
│  └── agent-q3-research  — Perplexity/Exa/Tavily        │
└─────────────────────────────────────────────────────────┘
```

---

## Model Stack

| Role | Model | Backend |
|------|-------|---------|
| Reasoner | `moonshotai/Kimi-K2.6` BF16 | HF Router |
| Support | `hf.co/TeichAI/Qwen3-8B-Kimi-K2-Thinking-Distill-GGUF:F16` | Ollama local |
| Coder | `hf.co/unsloth/QwQ-32B-GGUF:Q8_0` | Ollama local |
| Tandem (cloud) | `hermes3:8b-cloud` | Ollama Cloud |
| Coder (cloud) | `qwen3:48b-a4b-cloud` | Ollama Cloud |
| Fallback | `qwopus:27b-cloud` | Ollama Cloud |
| Coder dedicated | `qwen3-coder:30b-a3b-cloud` | Ollama Cloud |

---

## Environment Variables

Set these as HuggingFace Space secrets:

```bash
HF_TOKEN=hf_xxxx                        # HF Router + deploy token
OLLAMA_CLOUD_ENABLED=true
OLLAMA_CLOUD_ACCOUNT=nicholasjmcleod@gmail.com
OLLAMA_CLOUD_DEVICE=LN-8RDGA90Ultra
REASONER_MODEL=moonshotai/Kimi-K2.6
COMPUTE_STRATEGY=cloud_priority
REDIS_URL=redis://...                   # Upstash or self-hosted
OPENROUTER_API_KEY=sk-or-v1-xxxx       # Secondary compute
RUNPOD_API_KEY=rpa_xxxx                # Quaternary GPU burst
PERPLEXITY_API_KEY=pplx-xxxx
EXA_API_KEY=xxxx
TAVILY_API_KEY=tvly-xxxx
PIPELINES_API_KEY=0p3n-w3bu!
WEBUI_SECRET_KEY=change-me
```

---

## Local Development

```bash
cp .env.example .env
# Fill in HF_TOKEN, REDIS_URL, API keys

docker compose up --build
```

Services:
- Orchestrator: `http://localhost:8000`
- Pipelines: `http://localhost:9099`
- Open WebUI: `http://localhost:3000`
- Ollama: `http://localhost:11434`

---

## Health Check

```bash
curl https://maddegen-agent-q3-space.hf.space/health
```

Expected:
```json
{
  "status": "ok",
  "memory_backend": "redis",
  "services_tracked": ["multimodal", "coder", "research", "mcp-bridge", "ollama"],
  "uptime_secs": 3600
}
```

---

## Test Endpoints

```bash
# Auto-classify and route
curl -X POST https://maddegen-agent-q3-space.hf.space/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write a Solidity ERC-20 with 1.88% fee"}]}'

# Force reasoner
curl -X POST https://maddegen-agent-q3-space.hf.space/v1/reason \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Analyze prediction market conviction scoring"}]}'

# Tandem — reason then implement
curl -X POST https://maddegen-agent-q3-space.hf.space/v1/tandem \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Design and implement a market oracle resolver"}]}'
```

---

## Agent-Triggered Deploy

The orchestrator can trigger a redeploy via GitHub repository_dispatch:

```bash
curl -X POST https://api.github.com/repos/MADdegen/Agent-Q3/dispatches \
  -H "Authorization: Bearer $GH_PAT" \
  -d '{"event_type":"agent_deploy","client_payload":{"space":"orchestrator","reason":"post-training-update"}}'
```
