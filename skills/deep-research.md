---
name: deep-research
description: Multi-source deep research synthesis with cost-optimised cascade and model routing
triggers: [research, investigate, sources, deep dive, analyze deeply, citations, current events, academic papers, multi-source]
roles: [reasoner, coder, tandem]
---

## Research cascade (cost-optimised — run tiers in order)

### Tier 1 — Free (always runs first)
1. DuckDuckGo + Jina + ArXiv + Wikipedia + GitHub (via `free_search.py`)
2. SearXNG self-hosted meta-search (70+ engines, zero cost)

### Tier 2 — Paid APIs (run if Tier 1 results are insufficient)
3. Exa → Tavily → Brave (auto-fallback via `web_search.py`)
4. Perplexity sonar / sonar-pro (via `perplexity_search.py`)

### Tier 3 — Deep research (comprehensive multi-step; use for complex or time-sensitive topics)
5. Perplexity `sonar-deep-research` — multi-step, 128K ctx, full citations

## Service endpoint
```
POST http://research:8002/v1/research/deep
{
  "query": "<user query>",
  "providers": ["perplexity", "exa", "tavily", "free"],
  "deep": true
}
```
For finance / prediction / event-driven topics also call:
```
POST http://research:8002/v1/research/quant
```
to include Polymarket conviction signals alongside research findings.

## MCP tool call (when using MCP bridge)
```
deep_research { "query": "...", "model": "sonar-deep-research" }
```

## Model routing
| Task | Model |
|------|-------|
| Short factual lookup | Harmonic-Hermes (fast, 9B) |
| Multi-step analysis / long documents | Kimi-Linear (1M ctx) |
| Structured step-by-step reasoning | Kimi-Distilled IQ4_XS (always-on `<think>`) |
| Vision / multimodal content | Kimi-Linear (pass `images[]` in message content) |
| Final synthesis / code-heavy output | Qwen3-Coder-53B TOTAL-RECALL |

## Output format
1. **Thesis** — one sentence
2. **Evidence** — numbered findings with inline `[n]` citations
3. **Counterpoints / source conflicts**
4. **Unknowns** — what the evidence does not resolve
5. **Sources** — numbered list with URLs
6. **Confidence** — High / Medium / Low
7. **Recommended follow-up queries** (optional)

Do not use filler words: "leverage", "synergy", "unlock", "game-changing".
