"""
Agent Q3 Tandem Pipeline
Open WebUI Pipelines — chained reasoning + implementation.

Exposed in the GUI as model: "agent-q3-tandem"
Stage 1 → multimodal:8000 /v1/reason  (Kimi-VL-A3B — deep analysis + plan)
Stage 2 → coder:8001       /v1/code    (Qwen3-Coder-30B — implementation)

The stage-1 output is injected as a system prompt for stage-2 so the
coder receives the full reasoning context without the user needing to repeat it.
"""

import os
import httpx
from typing import List, Union, Generator, Iterator
from pydantic import BaseModel


class Pipeline:
    class Valves(BaseModel):
        orchestrator_url: str = os.getenv("ORCHESTRATOR_URL", "http://multimodal:8000")
        coder_url: str = os.getenv("CODER_URL", "http://coder:8001")
        timeout: int = 300

    def __init__(self):
        self.name = "Agent Q3 — Tandem (Reason → Code)"
        self.id = "agent-q3-tandem"
        self.valves = self.Valves()

    async def on_startup(self):
        print(f"[{self.name}] ready")

    async def on_shutdown(self):
        pass

    def pipe(
        self,
        user_message: str,
        model_id: str,
        messages: List[dict],
        body: dict,
    ) -> Union[str, Generator, Iterator]:
        max_tokens = body.get("max_tokens", 2048)
        temp = body.get("temperature", 0.7)

        # ── Stage 1: Reasoner (Kimi-VL-A3B) ──────────────────────────────────
        try:
            r1 = httpx.post(
                f"{self.valves.orchestrator_url}/v1/reason",
                json={"messages": messages, "model_role": "reasoner", "max_tokens": max_tokens, "temperature": temp},
                timeout=self.valves.timeout,
            )
            r1.raise_for_status()
            reasoning = (
                r1.json().get("content")
                or (r1.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
            )
        except httpx.HTTPError as e:
            return f"[Tandem Stage 1 — Reasoner failed]: {e}"

        # ── Stage 2: Coder (Qwen3-Coder-30B) ─────────────────────────────────
        # Inject the reasoner's plan as a system message so the coder has full context.
        stage2_messages = [
            {
                "role": "system",
                "content": (
                    "You are implementing the plan produced by the Reasoning Agent.\n\n"
                    f"## Reasoning Agent Output\n\n{reasoning}\n\n"
                    "Now write the complete, working implementation. "
                    "Return code only — no filler explanations unless asked."
                ),
            }
        ] + [m for m in messages if m.get("role") == "user"]

        try:
            r2 = httpx.post(
                f"{self.valves.coder_url}/v1/code",
                json={"messages": stage2_messages, "model_role": "coder", "max_tokens": max_tokens, "temperature": temp},
                timeout=self.valves.timeout,
            )
            r2.raise_for_status()
            implementation = (
                r2.json().get("content")
                or (r2.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
            )
        except httpx.HTTPError as e:
            return f"[Tandem Stage 1 complete]\n\n{reasoning}\n\n[Stage 2 — Coder failed]: {e}"

        return (
            f"## Reasoning (Kimi-VL-A3B)\n\n{reasoning}\n\n"
            f"---\n\n## Implementation (Qwen3-Coder-30B)\n\n{implementation}"
        )
