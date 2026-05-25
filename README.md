# Agent Q3 — Triple-Model AI Orchestrator

**Reasoner:** `moonshotai/Kimi-K2.6` · BF16, multimodal image-text-to-text, HF Router  
**Support:** `TeichAI/Qwen3-8B-Kimi-K2-Thinking-Distill-GGUF:F16` · hybrid, punches at 16B  
**Coder:** `unsloth/QwQ-32B-GGUF:Q8_0` · 131K ctx, deep research + coding  
**Compute:** HuggingFace Spaces (Ollama Cloud) → HuggingFace Router → RunPod → OpenRouter

---

## Architecture

```
POST /v1/chat        → auto-classify → Reasoner | Support | Coder
POST /v1/reason      → force Qwen2.5-VL-32B   (multimodal reasoning / planning)
POST /v1/support     → force Qwen3-8B-Kimi     (hybrid tasks, punches at 16B)
POST /v1/code        → force QwQ-32B           (131K ctx, deep research + coding)
POST /v1/tandem      → Reasoner reasons → Coder implements (chained)
GET  /health         → backend health + loaded models
GET  /metrics        → Prometheus
GET  /cowork/mcp     → Claude Cowork MCP endpoint (8 tools)
GET  /cowork/memory/ → Memory read/write (Redis 24h TTL)
```

```
┌──────────────────────────────────────────────────────┐
│                  Agent Q3 Container                  │
│                                                      │
│  Ollama :11434                                       │
│  ├── Qwen2.5-VL-32B-Instruct-Q4_K_M  (Reasoner)    │
│  ├── Qwen3-8B-Kimi-K2-Thinking-Q4_K_M (Support)    │
│  └── QwQ-32B-Q4_K_M                  (Coder)       │
│                                                      │
│  Orchestrator FastAPI :8000                          │
│  └── ComputeRouter                                   │
│       ├── Railway  (Ollama GPU volume)               │
│       ├── HuggingFace Router                         │
│       ├── RunPod   (serverless GPU)                  │
│       └── OpenRouter (fallback)                      │
│                                                      │
│  Memory                                              │
│  ├── Redis    (short-term, 24h TTL)                  │
│  └── Postgres pgvector (long-term, 384-dim)          │
└──────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
cp .env.example .env
# Fill in HF_TOKEN, RUNPOD_API_KEY, RUNPOD_*_ENDPOINT_ID

docker compose up --build
```

---

## API Usage

```bash
# Auto-classify (recommended)
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write a Solidity ERC-20 contract"}]}'

# Force Reasoner (multimodal / deep planning)
curl -X POST http://localhost:8000/v1/reason \
  -d '{"messages": [{"role": "user", "content": "Research Polymarket vs MAD Gambit market design"}]}'

# Force Support (hybrid tasks)
curl -X POST http://localhost:8000/v1/support \
  -d '{"messages": [{"role": "user", "content": "Summarize this document and suggest next steps"}]}'

# Force Coder (deep research + code)
curl -X POST http://localhost:8000/v1/code \
  -d '{"messages": [{"role": "user", "content": "Fix this Hono middleware bug: ..."}]}'

# Tandem (Reasoner thinks → Coder implements)
curl -X POST http://localhost:8000/v1/tandem \
  -d '{"messages": [{"role": "user", "content": "Build a market resolution oracle in Solidity using Chainlink"}]}'
```

---

## Compute Strategy

| Strategy | Behaviour |
|---|---|
| `round_robin` | Railway → HF → RunPod weighted (default) |
| `local_first` | Always Railway Ollama, fall back to HF |
| `hf_first` | Always HF Router, fall back to Railway |
| `runpod_first` | Always RunPod, fall back to Railway |
| `load_based` | Routes based on queue depth |

Set `COMPUTE_STRATEGY` env var to switch at runtime.

---

## Railway Deployment

Railway project: `exciting-freedom`  
Pushes to `main` auto-deploy via the Railway GitHub integration.

---

## Env Vars

See `.env.example` for full reference.  
RunPod endpoint IDs: [RunPod Console](https://www.runpod.io/console/serverless)  
HF token: [HuggingFace Settings](https://huggingface.co/settings/tokens)

---

## Unified Asset Registry

Full machine-readable registry: [`registry.json`](./registry.json)

| Type | Label | Link |
|------|-------|------|
| Dataset | Agent Q3 (unified) | [madDegen/agent-q3](https://hf.co/datasets/madDegen/agent-q3) |
| Model repo | Agent Q3 (unified) | [madDegen/agent-q3-core](https://hf.co/madDegen/agent-q3-core) |
| Space | Agent Q3 (unified) | [madDegen/agent-q3-space](https://hf.co/spaces/madDegen/agent-q3-space) |
| GitHub | Agent Q3 — Orchestrator | [MADdegen/Agent-Q3](https://github.com/MADdegen/Agent-Q3) |
| GitHub | MAD Gambit — Platform | [MADdegen/MPP-2.0](https://github.com/MADdegen/MPP-2.0) |
| GitHub | MAD Gambit — Core (contracts + API) | [The-MDC/mad-gambit-core](https://github.com/The-MDC/mad-gambit-core) |
| GitHub | MAD Gambit — UI | [The-MDC/mad-gambit-ui](https://github.com/The-MDC/mad-gambit-ui) |
| GitHub | LobeHub UI | [MADdegen/lobehub](https://github.com/MADdegen/lobehub) |
| GitHub | Investor Presentation | [MADdegen/MADHATs-Gambit-Presentation](https://github.com/MADdegen/MADHATs-Gambit-Presentation) |
| GitHub | Claude Enhancement Stack | [The-MDC/MADHATs-Claude-Enhancement](https://github.com/The-MDC/MADHATs-Claude-Enhancement) |
| GitHub | Claude Toolkit | [MADdegen/My-Claude](https://github.com/MADdegen/My-Claude) |
