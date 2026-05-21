"""
Agent-Q3 Orchestrator — Main FastAPI App
MAD Gambit | github.com/MADdegen/Agent-Q3

Cloud model stack (all via Ollama Cloud):
  [1] kimi-vl:a3b-cloud          — reasoner  — /v1/instruct, /v1/chat
  [2] hermes3:8b-cloud           — tandem    — /v1/tandem stage-2
  [3] qwen3:48b-a4b-cloud        — coder     — /v1/code, /v1/tandem stage-3
  [4] qwopus:27b-cloud           — fallback  — /v1/fallback
  [5] qwen3-coder:30b-a3b-cloud  — coder_ded — /v1/coder
  [6] kimi-k2:2.6-cloud          — analyst   — /v1/analyze
  [7] kimi-k2:1t-cloud           — monitor   — /v1/monitor/analyze (external)

Endpoints:
  POST /v1/chat     — auto-classify → reasoner or coder
  POST /v1/instruct — force Kimi-VL-A3B (vision, long-ctx, agent)
  POST /v1/code     — force Qwen3-48B-A4B (multimodal, code)
  POST /v1/tandem   — Kimi-VL reasons → Hermes3 refines → Qwen3 implements
  POST /v1/fallback — force Qwopus3.6-27B
  POST /v1/analyze  — Kimi-K2.6 deep analysis + conviction scoring
  GET  /health      — all backends + loaded models
  GET  /v1/loaded   — full inventory
  GET  /metrics     — Prometheus
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .router import router, Backend
from .memory import memory
from .skills import skills
from .plugins import plugins
from .models import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    Message,
    classify_task,
    REASONER_SYSTEM,
    CODER_SYSTEM,
    HERMES_SYSTEM,
)

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "Agent-Q3 starting",
        reasoner=settings.reasoner_model,
        tandem=settings.tandem_model,
        coder=settings.coder_model,
        fallback=settings.fallback_model,
        analyst=settings.analyst_model,
        monitor=settings.kimi_k2_model,
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
        "7-model Ollama Cloud orchestrator: Kimi-VL-A3B (reasoner) + "
        "Hermes3-8B (tandem) + Qwen3-48B-A4B (coder) + Qwopus3.6-27B (fallback) + "
        "Qwen3-Coder-30B-A3B (coder_dedicated) + Kimi-K2.6 (analyst) + "
        "Kimi-K2-1T (monitor)"
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_messages(
    request: ChatRequest,
    system_override: str | None = None,
) -> list[dict]:
    msgs = []
    system = system_override or request.system_prompt
    if system and not any(m.role == "system" for m in request.messages):
        msgs.append({"role": "system", "content": system})
    msgs.extend([m.model_dump() for m in request.messages])
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
        "version": "2.0.0",
        "docs": "/docs",
        "models": {
            "reasoner":        settings.reasoner_model,
            "tandem":          settings.tandem_model,
            "coder":           settings.coder_model,
            "fallback":        settings.fallback_model,
            "coder_dedicated": settings.coder_dedicated_model,
            "analyst":         settings.analyst_model,
            "monitor":         settings.kimi_k2_model,
        },
        "loaded": {
            "memory_backend": memory.backend,
            "skills": [s.to_dict() for s in skills.all],
            "plugins": [p.to_dict() for p in plugins.all],
        }
    }


@app.get("/v1/loaded")
async def loaded():
    """Full inventory of models, skills, plugins, memory, and configured MCP servers."""
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
            "reasoner":        settings.reasoner_model,
            "tandem":          settings.tandem_model,
            "coder":           settings.coder_model,
            "fallback":        settings.fallback_model,
            "coder_dedicated": settings.coder_dedicated_model,
            "analyst":         settings.analyst_model,
            "monitor":         settings.kimi_k2_model,
        },
        "memory":  {"backend": memory.backend, "alive": await memory.ping()},
        "skills":  [s.to_dict() for s in skills.all],
        "plugins": [p.to_dict() for p in plugins.all],
        "mcp":     mcp_info,
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Full health check — all backends + loaded Ollama models."""
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
            "local":       router._health[Backend.LOCAL].healthy,
            "huggingface": router._health[Backend.HF].healthy,
            "runpod":      router._health[Backend.RUNPOD].healthy,
        },
    )


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Auto-classify → instruct (Kimi-VL) or multimodal (Qwen3-48B).
    Override with model_role='reasoner'|'coder'|'tandem'|'fallback'.
    Pin compute with force_backend='local'|'huggingface'|'runpod'.
    """
    if request.model_role in (None, "auto"):
        role = classify_task(request.messages)
    else:
        role = request.model_role

    system = REASONER_SYSTEM if role == "reasoner" else CODER_SYSTEM
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
    """Force Kimi-VL-A3B — vision, long-context, agent, instruct tasks."""
    request.model_role = "reasoner"
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
    """Alias for /v1/instruct — forces Kimi-VL-A3B."""
    return await instruct(request)


@app.post("/v1/code", response_model=ChatResponse)
async def code(request: ChatRequest):
    """Force Qwen3-48B-A4B-Savant — primary multimodal, code, fetch, structured output."""
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


@app.post("/v1/fallback", response_model=ChatResponse)
async def fallback(request: ChatRequest):
    """Force Qwopus3.6-27B — fallback multimodal when primary is overloaded."""
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


@app.post("/v1/tandem", response_model=dict)
async def tandem(request: ChatRequest):
    """
    3-stage tandem pipeline:
      Stage 1 — Kimi-VL-A3B reads the prompt, produces analysis + plan (vision aware)
      Stage 2 — Hermes3 refines the plan with deep reasoning
      Stage 3 — Qwen3-48B-A4B implements the refined plan

    Use for complex tasks that need vision → reasoning → implementation.
    """
    force_backend = Backend(request.force_backend) if request.force_backend else None

    # Stage 1: Kimi-VL — read + initial analysis
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
        raise HTTPException(status_code=503, detail=f"Kimi-VL (Stage 1) failed: {e}")

    # Stage 2: Hermes3 — deep reasoning on Kimi's analysis
    hermes_msgs = [
        {"role": "system", "content": HERMES_SYSTEM},
        *[m.model_dump() for m in request.messages],
        {"role": "assistant", "content": f"[Kimi-VL Analysis]\n{kimi_analysis}"},
        {"role": "user", "content": "Reason through this carefully. Identify any gaps or improvements in the analysis above, then produce a precise, refined implementation plan."},
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
        raise HTTPException(status_code=503, detail=f"Hermes3 (Stage 2) failed: {e}")

    # Stage 3: Qwen3-48B — implement the refined plan
    qwen_msgs = [
        {"role": "system", "content": CODER_SYSTEM},
        *[m.model_dump() for m in request.messages],
        {"role": "assistant", "content": f"[Kimi-VL Analysis]\n{kimi_analysis}\n\n[Hermes3 Refined Plan]\n{hermes_plan}"},
        {"role": "user", "content": "Implement this precisely. Return working, production-ready output only."},
    ]
    try:
        qwen_result = await router.route(
            model_role="coder",
            messages=qwen_msgs,
            force_backend=force_backend,
            temperature=0.3,
            max_tokens=request.max_tokens,
        )
        implementation = _extract_content(qwen_result)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Qwen3-48B (Stage 3) failed: {e}")

    return {
        "kimi_analysis":     kimi_analysis,
        "hermes_plan":       hermes_plan,
        "implementation":    implementation,
        "kimi_model":        kimi_result.get("_model_used"),
        "hermes_model":      hermes_result.get("_model_used"),
        "qwen_model":        qwen_result.get("_model_used"),
        "kimi_backend":      kimi_result.get("_backend_used"),
        "hermes_backend":    hermes_result.get("_backend_used"),
        "qwen_backend":      qwen_result.get("_backend_used"),
    }


_ANALYST_SYSTEM = """You are Kimi-K2.6, an advanced analytical intelligence within Agent-Q3.
Your role: deep situational analysis, conviction scoring, market intelligence, and strategic synthesis.
Produce structured, evidence-backed analysis. Be precise. Quantify uncertainty where possible."""


@app.post("/v1/analyze", response_model=ChatResponse)
async def analyze(request: ChatRequest):
    """
    Kimi-K2.6 deep analysis — conviction scoring, research synthesis, strategic intel.
    Also available as /v1/research/conviction.
    """
    messages = _build_messages(request, system_override=_ANALYST_SYSTEM)
    force_backend = Backend(request.force_backend) if request.force_backend else None
    try:
        result = await router.route(
            model_role="analyst",
            messages=messages,
            force_backend=force_backend,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except Exception as e:
        log.error("analyze failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))
    return ChatResponse(
        content=_extract_content(result),
        model_role="analyst",
        model_used=result.get("_model_used", "unknown"),
        backend_used=result.get("_backend_used", "unknown"),
        usage=result.get("usage"),
    )
