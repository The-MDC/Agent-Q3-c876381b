# Agent-Q3 — CLAUDE.md

## Project identity
Agent-Q3 is a 6+1 model AI orchestrator deployed on HuggingFace Spaces (Docker SDK). Zero GPU required — all inference via Ollama Cloud.
Owner: Nick (MADdegen) — Founder of MAD Gambit.
Spaces: MADdegens/Agent-Q3 (orchestrator) · MADdegens/agent-q3-compiler (routing/dispatch)

## Model stack (Ollama Cloud — nicholasjmcleod namespace)
All models sourced from MADdegens/Models HF bucket (GGUFs) → pushed to Ollama Cloud.

| Role                  | Ollama Cloud Tag                               | Endpoint(s)                                  |
|-----------------------|------------------------------------------------|----------------------------------------------|
| Reasoner (1M ctx)     | nicholasjmcleod/kimi-linear:q6_k               | /v1/instruct /v1/chat (multimodal)           |
| Tandem + Monitor      | nicholasjmcleod/harmonic-hermes:q6_k           | /v1/tandem stage-2 + /v1/monitor/analyze     |
| Coder + Remediate     | nicholasjmcleod/qwen3-coder-53b:q6_k           | /v1/code /v1/coder /v1/monitor/remediate     |
| Kimi Distilled (local)| nicholasjmcleod/kimi-distilled:iq4_xs          | /v1/reason (structured K2.6-style reasoning) |
| Genstruct             | nicholasjmcleod/genstruct:q6_k                 | /v1/generate (structure middleware)          |
| Parser                | nicholasjmcleod/infinity-parser:latest         | /v1/parse (parse middleware)                 |
| K2.6 Orchestrator     | Moonshot API + OpenRouter (kimi-k2-0711)       | /v1/instruct (swarm, multimodal, 256K ctx)   |

## Model pairs
- Execution pair: Harmonic-Hermes (analysis) + Qwen3-Coder-53B (implement/remediate + monitor)
- Structure pair: Genstruct + Infinity-Parser (wrap all pipelines as pre/post middleware)
- Reasoning layer: Kimi-Distilled IQ4_XS (local, always-on <think>) + Kimi K2.6 API (swarm)

## Tandem pipeline
Kimi-Linear (1M-ctx pre-processing + multimodal) → Harmonic-Hermes (refinement) → Qwen3-Coder-53B (implementation)

## Compute routing (cloud_priority)
Ollama Cloud (55%) → Moonshot API free credits (25%) → OpenRouter K2.6 fallback (10%) → HuggingFace Router (8%) → RunPod AMPERE_16 (2%)

## Tech stack
- Compute: Ollama Cloud (Tier 1) → Moonshot API → OpenRouter → HuggingFace Router → RunPod (cloud_priority)
- Deploy:  HuggingFace Spaces — Docker SDK (MADdegens org) — ZERO GPU
- API:     FastAPI + uvicorn on port 8000
- Memory:  Redis (short-term 24h TTL)
- Search:  DuckDuckGo + Jina + ArXiv + Exa + Tavily + Perplexity
- HF Subs: Personal (Level 1) + MADdegens Org (Teams)

## Canonical numbers (NEVER change)
- Platform fee: 1.88%
- Community profit share: 28.8% (display as 28%)
- Creator revenue share: 40%
- Seed raise: $1-2M at $12M pre-money valuation

## HF Bucket
- Models: MADdegens/Models (6 GGUFs — kimi-linear, harmonic-hermes, qwen3-coder-53b, kimi-distilled, genstruct, infinity-parser)
- Bootstrap: BOOTSTRAP_MODE=true in start.sh → downloads GGUFs → creates Ollama models → pushes to cloud

## Rules
1. Always use exact nicholasjmcleod/<model>:<tag> strings
2. Never reference kimi-k2, kimi-vl, hermes3:8b-cloud, qwen3:48b-a4b-cloud, ultracoder, qwopus, or any removed models
3. Kimi-Linear handles multimodal/vision — pass images[] in message content
4. Monitor service uses Harmonic-Hermes (analysis) + Qwen3-Coder-53B (remediation)
5. Genstruct + Infinity-Parser are middleware — they wrap other models, not standalone only
6. Deploy target is HuggingFace Spaces — NOT Railway, NOT local
7. Sub-agent dispatch: Kimi-Linear can spawn tasks to /v1/code, /v1/generate, /v1/parse
8. Kimi K2.6 API (Moonshot primary, OpenRouter fallback) is the swarm orchestrator — preserve_thinking: true
9. Kimi-Distilled IQ4_XS runs locally via Ollama Cloud — structured reasoning with always-on <think>
10. HF Subscriptions: Personal Level 1 (nicholasjmcleod) + Teams Org (MADdegens) — use both token pools
11. RunPod: Level 1 Community — AMPERE_16, scale-to-zero, fallback only
