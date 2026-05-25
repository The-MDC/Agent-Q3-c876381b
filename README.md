# Agent-Q3 — MAD Gambit AI Orchestrator

**7-model Ollama Cloud stack** · Harmonic-Hermes + Ultra-Coder paired monitor · 4-tier compute routing

---

## Model Stack (nicholasjmcleod/ Ollama Cloud namespace)

| Role | Model | Endpoints |
|------|-------|-----------|
| Reasoner (multimodal) | `nicholasjmcleod/kimi-linear:q6_k` | `/v1/instruct` `/v1/chat` |
| Tandem + Monitor | `nicholasjmcleod/harmonic-hermes:q6_k` | `/v1/tandem` `/v1/monitor/analyze` |
| Coder + Remediate | `nicholasjmcleod/ultracoder:q4_k_m` | `/v1/code` `/v1/tandem` `/v1/monitor/remediate` |
| Fallback | `nicholasjmcleod/qwopus:q8_0` | `/v1/fallback` |
| Coder Dedicated | `nicholasjmcleod/qwen3-coder-53b:q6_k` | `/v1/coder` |
| Genstruct (middleware) | `nicholasjmcleod/genstruct:q6_k` | `/v1/generate` |
| Parser (middleware) | `nicholasjmcleod/infinity-parser:latest` | `/v1/parse` |

Models are GGUFs stored in `MADdegens/Models` HF bucket, pushed to Ollama Cloud via `scripts/start.sh`.

---

## Architecture

```
POST /v1/chat        → auto-classify → Reasoner or Coder
POST /v1/instruct    → Kimi-Linear-48B  (multimodal / deep reasoning / vision)
POST /v1/code        → Ultra-Coder-Brain (code / debug / implement)
POST /v1/coder       → Qwen3-Coder-53B  (long-form dedicated coding)
POST /v1/tandem      → Kimi-Linear → Harmonic-Hermes → Ultra-Coder (chained)
POST /v1/generate    → Genstruct-7B (structured output middleware)
POST /v1/parse       → Infinity-Parser2-Pro (extract/transform middleware)
GET  /health         → backend health + model reachability
GET  /metrics        → Prometheus
```

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent-Q3 (HF Space)                      │
│                                                             │
│  Ollama Cloud :11434  (nicholasjmcleod/ namespace)          │
│  ├── kimi-linear:q6_k        (Reasoner)                     │
│  ├── harmonic-hermes:q6_k    (Tandem + Monitor)             │
│  ├── ultracoder:q4_k_m       (Coder + Remediate)            │
│  ├── qwopus:q8_0             (Fallback)                     │
│  ├── qwen3-coder-53b:q6_k    (Coder Dedicated)              │
│  ├── genstruct:q6_k          (Structure middleware)          │
│  └── infinity-parser:latest  (Parse middleware)             │
│                                                             │
│  Orchestrator FastAPI :8000                                 │
│  └── ComputeRouter                                          │
│       ├── Ollama Cloud  (60% weight — primary)              │
│       ├── OpenRouter    (20% — kimi-k2.6 sole model)        │
│       ├── HF Router     (15% — 7-model public equivalents)  │
│       └── RunPod        (5%  — GPU burst)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Tandem Pipeline

Kimi-Linear-48B (analysis + multimodal) → Harmonic-Hermes-9B (refinement) → Ultra-Coder-Brain (implementation)

---

## Monitor Pair

Harmonic-Hermes watches the stack → diagnoses anomalies  
Ultra-Coder-Brain produces remediation plans with exact commands  
Always-on, independent of the main router, rate-limited 5 min per service

---

## Quick Start

```bash
cp .env.example .env
# Fill in: HF_TOKEN, RUNPOD_API_KEY, OPENROUTER_API_KEY
# Optional: PERPLEXITY_API_KEY, EXA_API_KEY, TAVILY_API_KEY

docker compose up --build
```

---

## API Usage

```bash
# Auto-classify (recommended)
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Write a Solidity ERC-20 contract"}]}'

# Multimodal reasoning (with image)
curl -X POST http://localhost:8000/v1/chat \
  -d '{"messages": [{"role": "user", "content": "Analyze this chart", "images": ["base64..."]}], "model_role": "reasoner"}'

# Tandem (reason → refine → implement)
curl -X POST http://localhost:8000/v1/tandem \
  -d '{"messages": [{"role": "user", "content": "Build a market resolution oracle in Solidity using Chainlink"}]}'

# Dedicated coder (long-form)
curl -X POST http://localhost:8000/v1/coder \
  -d '{"messages": [{"role": "user", "content": "Implement a full ERC-4626 vault with 1.88% fee"}]}'

# Monitor status
curl http://localhost:8000/v1/monitor/status

# Monitor analysis (Harmonic-Hermes)
curl -X POST http://localhost:8000/v1/monitor/analyze \
  -d '{"query": "Why is the coder service latency spiking?"}'

# Remediation plan (Ultra-Coder-Brain)
curl -X POST http://localhost:8000/v1/monitor/remediate \
  -d '{"query": "coder service is down, provide exact fix commands"}'
```

---

## Compute Strategy

| Strategy | Behaviour |
|---|---|
| `cloud_priority` | Ollama Cloud → OpenRouter → HF → RunPod (default) |
| `local_first` | Ollama Cloud primary, HF fallback |
| `hf_first` | HF Router primary |
| `runpod_first` | RunPod GPU primary |
| `round_robin` | Weighted distribution |

Set `COMPUTE_STRATEGY` env var to switch at runtime.

---

## Deployment

**Platform:** HuggingFace Spaces — `MADdegens/Agent-Q3` (Docker SDK)  
**CI/CD:** GitHub Actions → `.github/workflows/5-hf-spaces-deploy.yml` (push to `main` triggers deploy)  
**Models:** `MADdegens/Models` HF bucket → `ollama create` → `ollama push nicholasjmcleod/` (via `scripts/start.sh BOOTSTRAP_MODE=true`)

---

## Env Vars

See `.env.example` for full reference.  
RunPod endpoint IDs: [RunPod Console](https://www.runpod.io/console/serverless)  
HF token: [HuggingFace Settings](https://huggingface.co/settings/tokens)

---

## Canonical Numbers

| Metric | Value |
|--------|-------|
| Platform fee | 1.88% |
| Community profit share | 28% (28.8% actual) |
| Creator revenue share | 40% |
| Seed raise | $1–2M at $12M pre-money |
