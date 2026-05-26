"""
Agent-Q3 Orchestrator — Main FastAPI App
MAD Gambit | github.com/MADdegen/Agent-Q3

Model stack (all from MADdegens/Models HF bucket → pushed to Ollama Cloud):
  [1] Kimi-Linear-48B-A3B Q6_K   — reasoning + multimodal + sub-agent dispatch  → /v1/instruct /v1/chat
  [2] Harmonic-Hermes-9B Q6_K    — tandem refiner + always-on monitor            → /v1/tandem stage-2 + /v1/monitor
  [3] Ultra-Coder-Brain Q4_K_M   — primary coder + monitor remediation           → /v1/code /v1/tandem stage-3
  [4] Qwopus3.6-27B Q8_0         — full-precision fallback                       → /v1/fallback
  [5] Qwen3-Coder-53B Q6_K       — dedicated long-form coding                   → /v1/coder
  [6] Genstruct-7B Q6_K          — structured generation middleware              → /v1/generate
  [7] Infinity-Parser2-Pro        — parsing/extraction middleware                 → /v1/parse

Pairs:
  Execution pair:  Harmonic-Hermes + Ultra-Coder  (reason/refine → implement/fix)
  Structure pair:  Genstruct + Infinity-Parser     (wrap all pipelines as pre/post middleware)

Endpoints:
  POST /v1/chat     — auto-classify → instruct/code/genstruct/parse
  POST /v1/instruct — Kimi-Linear-48B (reasoning, vision, multimodal, sub-agent dispatch)
  POST /v1/reason   — alias for /v1/instruct
  POST /v1/code     — Ultra-Coder-Brain (primary coder)
  POST /v1/coder    — Qwen3-Coder-53B TOTAL-RECALL (dedicated long-form coding)
  POST /v1/tandem   — Kimi-Linear → Harmonic-Hermes → Ultra-Coder pipeline
  POST /v1/fallback — Qwopus3.6-27B (full-precision fallback)
  POST /v1/generate — Genstruct-7B (structured data + template generation)
  POST /v1/parse    — Infinity-Parser2-Pro (document + data parsing)
  GET  /health      — all backends + loaded models
  GET  /metrics     — Prometheus
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .memory import memory
from .models import (
    CODER_SYSTEM,
    GENSTRUCT_SYSTEM,
    HERMES_SYSTEM,
    INFINITY_PARSER_SYSTEM,
    REASONER_SYSTEM,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    classify_task,
)
from .plugins import plugins
from .router import Backend, router
from .skills import skills
from .services.capacity import (
    capacity_status,
    record_request_end,
    record_request_start,
    should_spawn_subagent,
)
from .tools.multi_agent_router import MultiAgentRouter

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "Agent-Q3 starting",
        reasoner=settings.reasoner_model,
        tandem=settings.tandem_model,
        coder=settings.coder_model,
        coder_dedicated=settings.coder_dedicated_model,
        fallback=settings.fallback_model,
        genstruct=settings.genstruct_model,
        infinity_parser=settings.infinity_parser_model,
        monitor_pair=f"{settings.monitor_model} + {settings.monitor_coder_model}",
        strategy=settings.compute_strategy,
    )
    await memory.connect()
    skills.load()
    plugins.discover()
    plugins.mount_into(app)
    yield
    await memory.close()
    log.info("Agent-Q3 shutting down")


app = FastAPI(
    title="Agent-Q3 Orchestrator",
    description=(
        "7-model orchestrator: Kimi-Linear-48B (multimodal) + Harmonic-Hermes-9B (tandem/monitor) + "
        "Ultra-Coder-Brain (coder/remediation) + Qwopus-27B (fallback) + Qwen3-Coder-53B (dedicated) + "
        "Genstruct-7B (structure) + Infinity-Parser2-Pro (parse)"
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

# Multi-agent router triggered when a model role exceeds capacity thresholds
multi_agent = MultiAgentRouter(compute_router=router)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_messages(request: ChatRequest, system_override: str | None = None) -> list[dict]:
    msgs = []
    system = system_override or request.system_prompt
    if system and not any(m.role == "system" for m in request.messages):
        msgs.append({"role": "system", "content": system})
    for m in request.messages:
        msg = m.model_dump(exclude_none=True)
        msgs.append(msg)
    return msgs


def _extract_content(result: dict) -> str:
    msg = result.get("message") or result.get("response") or {}
    if isinstance(msg, dict):
        return msg.get("content", "")
    return str(msg)


# ── Routes ────────────────────────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Agent-Q3",
        "version": "3.0.0",
        "docs": "/docs",
        "models": {
            "reasoner": settings.reasoner_model,
            "tandem": settings.tandem_model,
            "coder": settings.coder_model,
            "coder_dedicated": settings.coder_dedicated_model,
            "fallback": settings.fallback_model,
            "genstruct": settings.genstruct_model,
            "infinity_parser": settings.infinity_parser_model,
        },
        "monitor_pair": {
            "analysis": settings.monitor_model,
            "remediation": settings.monitor_coder_model,
        },
    }


@app.get("/v1/loaded")
async def loaded():
    import httpx as _httpx

    mcp_info: dict = {"reachable": False}
    try:
        async with _httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://mcp-bridge:8004/mcp/tools")
            if r.status_code == 200:
                mcp_info = {"reachable": True, **r.json()}
    except Exception as e:
        mcp_info = {"reachable": False, "error": str(e)}

    return {
        "models": {
            "reasoner": settings.reasoner_model,
            "tandem": settings.tandem_model,
            "coder": settings.coder_model,
            "coder_dedicated": settings.coder_dedicated_model,
            "fallback": settings.fallback_model,
            "genstruct": settings.genstruct_model,
            "infinity_parser": settings.infinity_parser_model,
            "monitor_analysis": settings.monitor_model,
            "monitor_remediation": settings.monitor_coder_model,
        },
        "memory": {"backend": memory.backend, "alive": await memory.ping()},
        "skills": [s.to_dict() for s in skills.all],
        "plugins": [p.to_dict() for p in plugins.all],
        "mcp": mcp_info,
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    import httpx as _httpx

    ollama_ok = False
    loaded_models = []
    try:
        async with _httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                loaded_models = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass

    return HealthResponse(
        status="ok" if ollama_ok else "degraded",
        ollama=ollama_ok,
        models_loaded=loaded_models,
        compute_strategy=settings.compute_strategy,
        backends={
            "local": router._health[Backend.LOCAL].healthy,
            "huggingface": router._health[Backend.HF].healthy,
            "runpod": router._health[Backend.RUNPOD].healthy,
        },
    )


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Auto-classify → reasoner / coder / genstruct / infinity_parser.
    Vision inputs (images in messages) always route to Kimi-Linear-48B.
    Override with model_role. Pin compute with force_backend.
    """
    if request.model_role in (None, "auto"):
        role = classify_task(request.messages)
    else:
        role = request.model_role

    system_map = {
        "reasoner": REASONER_SYSTEM,
        "coder": CODER_SYSTEM,
        "coder_dedicated": CODER_SYSTEM,
        "tandem": HERMES_SYSTEM,
        "fallback": CODER_SYSTEM,
        "genstruct": GENSTRUCT_SYSTEM,
        "infinity_parser": INFINITY_PARSER_SYSTEM,
    }
    system = system_map.get(role, REASONER_SYSTEM)
    messages = _build_messages(request, system_override=system)
    force_backend = Backend(request.force_backend) if request.force_backend else None

    try:
        result = await router.route(
            model_role=role,
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        log.error("chat failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))

    return ChatResponse(
        content=_extract_content(result),
        model_role=role,
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/instruct", response_model=ChatResponse)
async def instruct(request: ChatRequest):
    """Kimi-Linear-48B — reasoning, multimodal vision, long-context, sub-agent dispatch."""
    messages = _build_messages(request, system_override=REASONER_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="reasoner",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="reasoner",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/reason", response_model=ChatResponse)
async def reason(request: ChatRequest):
    """Alias for /v1/instruct."""
    return await instruct(request)


@app.post("/v1/code", response_model=ChatResponse)
async def code(request: ChatRequest):
    """Ultra-Coder-Brain — primary code execution, debugging, structured output."""
    messages = _build_messages(request, system_override=CODER_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="coder",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="coder",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/coder", response_model=ChatResponse)
async def coder_dedicated(request: ChatRequest):
    """Qwen3-Coder-53B TOTAL-RECALL — dedicated long-form code generation and review."""
    messages = _build_messages(request, system_override=CODER_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="coder_dedicated",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="coder_dedicated",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/fallback", response_model=ChatResponse)
async def fallback(request: ChatRequest):
    """Qwopus3.6-27B Q8_0 — full-precision fallback for any role."""
    messages = _build_messages(request, system_override=CODER_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="fallback",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="fallback",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/generate", response_model=ChatResponse)
async def generate(request: ChatRequest):
    """Genstruct-7B — structured data, templates, schemas, training set generation."""
    messages = _build_messages(request, system_override=GENSTRUCT_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="genstruct",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="genstruct",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/parse", response_model=ChatResponse)
async def parse(request: ChatRequest):
    """Infinity-Parser2-Pro — document parsing, data extraction, structure transformation."""
    messages = _build_messages(request, system_override=INFINITY_PARSER_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="infinity_parser",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="infinity_parser",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )


@app.post("/v1/tandem", response_model=dict)
async def tandem(request: ChatRequest):
    """
    3-stage tandem pipeline:
      Stage 1 — Kimi-Linear-48B: multimodal analysis + initial plan
      Stage 2 — Harmonic-Hermes-9B: deep reasoning refinement
      Stage 3 — Ultra-Coder-Brain: implementation

    Genstruct structures the final output if structured output is requested.
    Infinity-Parser pre-processes complex inputs before Stage 1 if needed.
    """
    force_backend = Backend(request.force_backend) if request.force_backend else None

    # Stage 1: Kimi-Linear — multimodal analysis and planning
    kimi_msgs = _build_messages(request, system_override=REASONER_SYSTEM)
    try:
        kimi_result = await router.route(
            model_role="reasoner",
            messages=kimi_msgs,
            force_backend=force_backend,
            temperature=0.6,
            max_tokens=1024,
        )
        kimi_analysis = _extract_content(kimi_result)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Kimi-Linear (Stage 1) failed: {e}")

    # Stage 2: Harmonic-Hermes — deep reasoning and refinement
    hermes_msgs = [
        {"role": "system", "content": HERMES_SYSTEM},
        *[m.model_dump(exclude_none=True) for m in request.messages],
        {"role": "assistant", "content": f"[Kimi-Linear Analysis]\n{kimi_analysis}"},
        {"role": "user", "content": "Reason through this carefully. Identify gaps and produce a precise, refined implementation plan."},
    ]
    try:
        hermes_result = await router.route(
            model_role="tandem",
            messages=hermes_msgs,
            force_backend=force_backend,
            temperature=0.5,
            max_tokens=1024,
        )
        hermes_plan = _extract_content(hermes_result)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Harmonic-Hermes (Stage 2) failed: {e}")

    # Stage 3: Ultra-Coder-Brain — implementation
    coder_msgs = [
        {"role": "system", "content": CODER_SYSTEM},
        *[m.model_dump(exclude_none=True) for m in request.messages],
        {
            "role": "assistant",
            "content": f"[Kimi-Linear Analysis]\n{kimi_analysis}\n\n[Harmonic-Hermes Plan]\n{hermes_plan}",
        },
        {"role": "user", "content": "Implement this precisely. Return working, production-ready output only."},
    ]
    try:
        coder_result = await router.route(
            model_role="coder",
            messages=coder_msgs,
            force_backend=force_backend,
            temperature=0.3,
            max_tokens=request.max_tokens,
        )
        implementation = _extract_content(coder_result)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ultra-Coder (Stage 3) failed: {e}")

    return {
        "kimi_analysis": kimi_analysis,
        "hermes_plan": hermes_plan,
        "implementation": implementation,
        "kimi_model": kimi_result.get("_model_used"),
        "hermes_model": hermes_result.get("_model_used"),
        "coder_model": coder_result.get("_model_used"),
        "kimi_backend": kimi_result.get("_backend_used"),
        "hermes_backend": hermes_result.get("_backend_used"),
        "coder_backend": coder_result.get("_backend_used"),
    }
