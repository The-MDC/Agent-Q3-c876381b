"""
Models & task classifier — Agent-Q3

Routes incoming prompts → Reasoner (Kimi-Linear-48B) or Coder (Ultra-Coder-Brain / Qwen3-Coder-53B)
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

# ── Request / Response schemas ────────────────────────────────────────────────


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    model_role: Literal["reasoner", "coder", "tandem", "fallback", "auto"] | None = "auto"
    force_backend: Literal["local", "huggingface", "runpod", "openrouter"] | None = None
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    system_prompt: str | None = None


class ChatResponse(BaseModel):
    content: str
    role: str = "assistant"
    model_role: str
    model_used: str
    backend_used: str
    usage: dict | None = None


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    models_loaded: list[str]
    compute_strategy: str
    backends: dict


# ── Task classifier ───────────────────────────────────────────────────────────

CODER_SIGNALS = re.compile(
    r"\b("
    r"code|function|class|def |import |from .+ import|"
    r"python|typescript|javascript|solidity|rust|golang|"
    r"sql|query|schema|migrate|"
    r"fetch|http|api|endpoint|curl|axios|request|"
    r"bug|fix|error|exception|traceback|debug|"
    r"write .*(script|code|function|class|test)|"
    r"implement|refactor|snippet|boilerplate|"
    r"compile|build|deploy|dockerfile|yaml|json|"
    r"solidity|foundry|forge|cast|abi|erc-?20|erc-?721"
    r")\b",
    re.IGNORECASE,
)

REASONER_SIGNALS = re.compile(
    r"\b("
    r"research|analyze|analyse|explain|compare|evaluate|"
    r"why|how does|what is|summarize|summarise|describe|"
    r"strategy|plan|roadmap|decision|recommend|advise|"
    r"think through|reason|logic|argument|thesis|"
    r"pros and cons|tradeoff|trade-off|"
    r"market|prediction|probability|sentiment|"
    r"write .*(essay|report|memo|plan|proposal)"
    r")\b",
    re.IGNORECASE,
)


def classify_task(messages: list[Message]) -> Literal["reasoner", "coder"]:
    """
    Heuristic classifier: examines last user message to pick the right model.
    Coder wins on ties (faster for mixed tasks).
    """
    text = " ".join(m.content for m in messages if m.role in ("user", "system"))[-2000:]

    coder_hits = len(CODER_SIGNALS.findall(text))
    reasoner_hits = len(REASONER_SIGNALS.findall(text))

    if coder_hits > reasoner_hits:
        return "coder"
    elif reasoner_hits > coder_hits:
        return "reasoner"
    else:
        return "coder"


# ── System prompts ────────────────────────────────────────────────────────────

REASONER_SYSTEM = """You are the Reasoning Agent in the Agent-Q3 system for MAD Gambit — a prediction conviction platform on Base L2.

Your role: deep analysis, multi-step reasoning, research synthesis, strategic planning, and instructed output.
Model: Kimi-Linear-48B-A3B-Instruct (Q6_K). You have access to the Coder agent for technical implementation.

Be concise. Lead with the answer. Use specific numbers over adjectives.
Never use: leverage, synergy, ecosystem play, unlock value, game-changing, utilize.
"""

CODER_SYSTEM = """You are the Multimodal Implementation Agent in the Agent-Q3 system for MAD Gambit.

Your role: write precise code, fetch data, check code correctness, debug, and produce structured file output.
Tech stack: React 18 + TypeScript, Hono/HonoX, Redis, Solidity/Foundry, Arbitrum/Base L2, Alchemy AA-SDK.

Return working code. No filler explanations unless asked.
Prefer TypeScript for frontend/backend. Solidity for contracts. Python for scripts.
"""

HERMES_SYSTEM = """You are Harmonic-Hermes, the deep reasoning partner in the Agent-Q3 tandem pipeline for MAD Gambit.

Your role: receive an initial analysis from Kimi-Linear-48B and reason through it rigorously.
- Identify logical gaps, unstated assumptions, and edge cases
- Sharpen the plan — be specific, remove ambiguity, add constraints
- Output a concise, structured implementation plan ready for the coder agent

Model: Harmonic-Hermes-9B (Q6_K). Be precise. Be critical. Do not repeat the input — improve it.
"""

GENSTRUCT_SYSTEM = """You are the Structured Generation Agent in the Agent-Q3 system for MAD Gambit.

Your role: generate structured data, templates, schemas, and formatted outputs from natural language instructions.
Model: Genstruct-7B (Q6_K).

Produce clean, valid structured output. Follow the format exactly as requested.
"""

INFINITY_PARSER_SYSTEM = """You are the Infinity Parser in the Agent-Q3 system for MAD Gambit.

Your role: parse, extract, and transform complex documents, code, and data structures.
Model: Infinity-Parser2-Pro.

Extract all relevant information. Preserve structure. Flag ambiguities.
"""
