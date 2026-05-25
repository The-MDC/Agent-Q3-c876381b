# Agent-Q3 — CLAUDE.md

## Project identity
Agent-Q3 is a self-hosted triple-model AI agent stack deployed on HuggingFace Spaces.
Owner: Nick (MADdegen) — Founder of MAD Gambit.

## Model stack
- Reasoner: moonshotai/Kimi-K2.6 (BF16, multimodal image-text-to-text, HF Router)
- Support:  hf.co/TeichAI/Qwen3-8B-Kimi-K2-Thinking-Distill-GGUF:F16 (hybrid, punches at 16B)
- Coder:    hf.co/unsloth/QwQ-32B-GGUF:Q8_0 (131K ctx, deep research + coding)

Local GGUF fallback: hf.co/unsloth/Qwen2.5-VL-32B-Instruct-GGUF:Q8_0 (Reasoner)
All local models: Q8_0 minimum (32B) / F16 (8B). No Q4 quants.

## Tech stack
- Compute: HuggingFace Spaces (Ollama Cloud) → HuggingFace Router → RunPod → OpenRouter
- Reasoner primary: HF Router at router.huggingface.co/v1 (Kimi-K2.6 BF16)
- API: FastAPI + uvicorn on port 7860
- Memory: Redis only (24h TTL, sessions, recent context)
- Search: DuckDuckGo + Jina + ArXiv + SearXNG + Exa + Tavily + Perplexity
- Claude Cowork: MCP endpoint at /cowork/mcp, memory at /cowork/memory/*

## HuggingFace Spaces (production)
- Orchestrator → hf.co/spaces/madDegen/agent-q3-space (port 7860)
- WebUI        → hf.co/spaces/madDegen/agent-q3-webui (port 7860)
- Dataset      → hf.co/datasets/madDegen/agent-q3
- Model repo   → hf.co/madDegen/agent-q3-core

## Canonical numbers (NEVER change)
- Platform fee: 1.88%
- Community profit share: 28.8% (display as 28%)
- Creator revenue share: 40%
- Seed raise: $1-2M at $12M pre-money valuation

## Repo structure
- orchestrator/        FastAPI app (main.py, router.py, config.py, models.py)
- orchestrator/tools/  Search + memory tools (Redis-only memory_store.py)
- orchestrator/cowork_ui.py  Claude Cowork MCP + memory endpoints
- pipelines/           Open WebUI Pipelines (router, tandem, research)
- spaces/              HF Spaces README configs (orchestrator/, webui/)
- skills/              Memory + deep research skill definitions
- config/              engine_config.yaml
- scripts/start.sh     Ollama model pull + serve (Q8_0/F16 quants)
- .mcp.json            MCP server registry (12 servers)

## Rules
1. Always use exact model:tag strings — never short names
2. Never use gemma4 or qwen3.5 names — those are the OLD stack
3. Never use kimi-vl:a3b-cloud — replaced by moonshotai/Kimi-K2.6
4. pull_model() uses exact grep-qx match — do not revert to base name grep
5. Memory saves go to /cowork/memory/save — not to files
6. Deep research routes through the tier cascade in skills/deep_research_skill.md
7. Claude Cowork connects via /cowork/mcp — all 8 tools exposed
8. No Railway, no Supabase, no Postgres — HF Spaces + Redis only

## From My-Claude toolkit (The-MDC org)
- Hooks: .claude/hooks/ from The-MDC/claude-code-hooks
- Best practices: patterns from The-MDC/claude-code-best-practice
- Multi-agent: orchestration patterns from The-MDC/claude-code-multi-agent-orchestrartion
- Skills: Alchemy agent skills from The-MDC/skills
