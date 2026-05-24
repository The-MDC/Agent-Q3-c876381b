"""
Agent Q3 Router Pipeline
Open WebUI Pipelines — multi-agent classifier and router.

Exposed in the GUI as model: "agent-q3-router"
Classifies each message and routes to the right Agent-Q3 service:
  reasoner → multimodal:8000  /v1/chat       (Kimi-VL-A3B)
  coder    → coder:8001       /v1/code        (Qwen3-Coder-30B)
  research → research:8002    /v1/research    (Perplexity/Exa/Tavily)
"""

import os
import re
import httpx
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel

CODER_RE = re.compile(
    r"\b(code|function|class|def |import |from .+ import|"
    r"python|typescript|javascript|solidity|rust|golang|"
    r"sql|query|schema|migrate|"
    r"fetch|http|api|endpoint|curl|axios|"
    r"bug|fix|error|exception|traceback|debug|"
    r"write .*(script|code|function|class|test)|"
    r"implement|refactor|snippet|boilerplate|"
    r"compile|build|deploy|dockerfile|yaml|json|"
    r"foundry|forge|cast|abi|erc-?20|erc-?721)\b",
    re.IGNORECASE,
)
REASONER_RE = re.compile(
    r"\b(research|analyze|analyse|explain|compare|evaluate|"
    r"why|how does|what is|summarize|summarise|describe|"
    r"strategy|plan|roadmap|decision|recommend|advise|"
    r"think through|reason|logic|argument|thesis|"
    r"pros and cons|tradeoff|trade-off|"
    r"market|prediction|probability|sentiment|"
    r"write .*(essay|report|memo|plan|proposal))\b",
    re.IGNORECASE,
)
RESEARCH_RE = re.compile(
    r"\b(latest|current|today|news|recent|trend|search|"
    r"find me|look up|what happened|who is|where is|"
    r"polymarket|prediction market|odds|price of|"
    r"arxiv|paper|study|survey|literature)\b",
    re.IGNORECASE,
)


class Pipeline:
    class Valves(BaseModel):
        orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://multimodal:8000")
        coder_url: str = os.getenv("CODER_URL", "http://coder:8001")
        research_url: str = os.getenv("RESEARCH_URL", "http://research:8002")
        timeout: int = 300

    def __init__(self):
        self.name = "Agent Q3 — Router"
        self.id = "agent-q3-router"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[{self.name}] orchestrator={self.valves.orchestrator_url}")

    async def on_shutdown(self):
        pass

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        role, url, endpoint = self._route(user_message)
        payload = {
            "messages": messages,
            "model_role": role,
            "max_tokens": body.get("max_tokens", 2048),
            "temperature": body.get("temperature", 0.7),
        }
        try:
            r = httpx.post(url, json=payload, timeout=self.valves.timeout)
            r.raise_for_status()
            data = r.json()
            content = (
                data.get("content")
                or (data.get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return f"[routed → {role} via {endpoint}]\n\n{content}"
        except httpx.HTTPError as e:
            return f"[Agent-Q3 Router] {role} service error: {e}"

    def _route(self, text: str):
        t = text[-2000:]
        c = len(CODER_RE.findall(t))
        r = len(REASONER_RE.findall(t))
        s = len(RESEARCH_RE.findall(t))

        if s > c and s > r:
            return "research", f"{self.valves.research_url}/v1/research", "research:8002"
        if c > r:
            return "coder", f"{self.valves.coder_url}/v1/code", "coder:8001"
        if r > c:
            return "reasoner", f"{self.valves.orchestrator_url}/v1/chat", "multimodal:8000"
        return "coder", f"{self.valves.coder_url}/v1/code", "coder:8001"
