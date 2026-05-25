# Agent-Q3 — CLAUDE.md

## Project identity
Agent-Q3 is a 7-model AI orchestrator deployed on HuggingFace Spaces (Docker SDK).
Owner: Nick (MADdegen) — Founder of MAD Gambit.
Spaces: MADdegens/Agent-Q3 (orchestrator) · MADdegens/agent-q3-compiler (routing/dispatch)

## Model stack (Ollama Cloud — nicholasjmcleod namespace)
All models sourced from MADdegens/Models HF bucket (GGUFs) → pushed to Ollama Cloud.

| Role             | Ollama Cloud Tag                              | Endpoint(s)                          |
|------------------|-----------------------------------------------|--------------------------------------|
| Reasoner         | nicholasjmcleod/kimi-linear:q6_k              | /v1/instruct /v1/chat (multimodal)   |
| Tandem + Monitor | nicholasjmcleod/harmonic-hermes:q6_k          | /v1/tandem stage-2 + /v1/monitor     |
| Coder + Remediate| nicholasjmcleod/ultracoder:q4_k_m             | /v1/code /v1/tandem stage-3          |
| Fallback         | nicholasjmcleod/qwopus:q8_0                   | /v1/fallback                         |
| Coder Dedicated  | nicholasjmcleod/qwen3-coder-53b:q6_k          | /v1/coder                            |
| Genstruct        | nicholasjmcleod/genstruct:q6_k                | /v1/generate (structure middleware)  |
| Parser           | nicholasjmcleod/infinity-parser:latest        | /v1/parse (parse middleware)         |

## Model pairs
- Execution pair: Harmonic-Hermes + Ultra-Coder (reason/refine → implement/fix + monitor)
- Structure pair: Genstruct + Infinity-Parser (wrap all pipelines as pre/post middleware)

## Tandem pipeline
Kimi-Linear (analysis + multimodal) → Harmonic-Hermes (refinement) → Ultra-Coder (implementation)

## Tech stack
- Compute: Ollama Cloud → OpenRouter → HuggingFace Router → RunPod (cloud_priority)
- Deploy:  HuggingFace Spaces — Docker SDK (MADdegens org)
- API:     FastAPI + uvicorn on port 8000
- Memory:  Redis (short-term 24h TTL)
- Search:  DuckDuckGo + Jina + ArXiv + Exa + Tavily + Perplexity
- Claude Cowork: MCP endpoint at /cowork/mcp, memory at /cowork/memory/*

## Canonical numbers (NEVER change)
- Platform fee: 1.88%
- Community profit share: 28.8% (display as 28%)
- Creator revenue share: 40%
- Seed raise: $1-2M at $12M pre-money valuation

## HF Bucket
- Models: MADdegens/Models (7 GGUFs)
- Bootstrap: BOOTSTRAP_MODE=true in start.sh → downloads GGUFs → creates Ollama models → pushes to cloud

## Rules
1. Always use exact nicholasjmcleod/<model>:<tag> strings
2. Never reference kimi-k2, kimi-vl, hermes3:8b-cloud, qwen3:48b-a4b-cloud, or any old stack models
3. Kimi-Linear handles multimodal/vision — pass images[] in message content
4. Monitor service uses Harmonic-Hermes (analysis) + Ultra-Coder (remediation) — NOT Kimi-K2
5. Genstruct + Infinity-Parser are middleware — they wrap other models, not standalone only
6. Deploy target is HuggingFace Spaces — NOT Railway, NOT local
7. Sub-agent dispatch: Kimi-Linear can spawn tasks to /v1/code, /v1/generate, /v1/parse
