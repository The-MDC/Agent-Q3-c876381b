"""
Agent Q3 Deep Research Pipeline
Open WebUI Pipelines — multi-source search + synthesis.

Exposed in the GUI as model: "agent-q3-research"
Routes to research:8002 which fans out across:
  Perplexity (primary) → Exa → Tavily → DuckDuckGo/Jina (free fallback)
  + ArXiv for academic queries
  + Polymarket / MAD Gambit for prediction market data

The research service synthesizes all sources and returns a structured report.
"""

import os
import httpx
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel


class Pipeline:
    class Valves(BaseModel):
        research_url: str = os.getenv("RESEARCH_URL", "http://research:8002")
        orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://multimodal:8000")
        timeout: int = 300

    def __init__(self):
        self.name = "Agent Q3 — Deep Research"
        self.id = "agent-q3-research"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[{self.name}] research={self.valves.research_url}")

    async def on_shutdown(self):
        pass

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        # Try the research service first; fall back to the reasoning orchestrator.
        for url, label in [
            (f"{self.valves.research_url}/v1/research", "research:8002"),
            (f"{self.valves.orchestrator_url}/v1/reason", "multimodal:8000 (fallback)"),
        ]:
            try:
                r = httpx.post(
                    url,
                    json={
                        "messages": messages,
                        "model_role": "reasoner",
                        "max_tokens": body.get("max_tokens", 4096),
                        "temperature": body.get("temperature", 0.3),
                    },
                    timeout=self.valves.timeout,
                )
                r.raise_for_status()
                data = r.json()
                content = (
                    data.get("content")
                    or (data.get("choices") or [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                sources = data.get("sources", [])
                header = f"[deep research via {label}]"
                if sources:
                    src_lines = "\n".join(f"- {s}" for s in sources[:8])
                    return f"{header}\n\n{content}\n\n---\n**Sources**\n{src_lines}"
                return f"{header}\n\n{content}"
            except httpx.HTTPError:
                continue

        return "[Agent-Q3 Research] Both research and fallback services unavailable."
