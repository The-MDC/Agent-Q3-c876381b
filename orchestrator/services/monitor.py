"""
Agent-Q3 — Always-On Monitor (Harmonic-Hermes + Ultra-Coder pair).

Harmonic-Hermes-9B watches the stack and produces analysis/insights.
Ultra-Coder-Brain handles automated remediation suggestions.
Both run via local Ollama — monitor is independent of the services it watches.

Pair roles:
  Harmonic-Hermes: anomaly analysis, root-cause diagnosis, health insights
  Ultra-Coder:     remediation plans, fix suggestions, automated patch cycles

Endpoints:
  GET  /                       — service info
  GET  /health                 — monitor health + model reachability
  GET  /v1/monitor/status      — current state of all watched services
  GET  /v1/monitor/history     — raw metrics history per service
  GET  /v1/monitor/events      — recent events (transitions, anomalies, insights)
  POST /v1/monitor/analyze     — query Harmonic-Hermes for analysis
  POST /v1/monitor/remediate   — query Ultra-Coder for remediation plan
  WS   /ws/live                — real-time event stream
"""

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from ..config import settings
from ..memory import memory

log = structlog.get_logger(__name__)


MONITOR_SYSTEM = """You are Harmonic-Hermes, the always-on system monitor for Agent-Q3 (MAD Gambit).

Your role: watch the multi-container AI stack and produce smart, actionable diagnostic insights.

Stack you monitor:
- multimodal  :8000  — Kimi-Linear-48B (reasoner) + Harmonic-Hermes (tandem) + Ultra-Coder (coder) + Qwopus (fallback)
- coder       :8001  — Qwen3-Coder-53B TOTAL-RECALL (dedicated long-form coding)
- research    :8002  — Perplexity / Exa / Tavily / Free / Polymarket synthesis
- mcp-bridge  :8004  — unified MCP server gateway
- ollama      :11434 — shared Ollama model server (7 models pulled from Ollama Cloud)

When given metrics: identify patterns, root causes, and predict issues before they escalate.
Be specific. Use latency numbers. Name the exact service and model. No filler.
Output 4 bullets max for anomaly analysis. Flag the single highest-leverage check first.
"""

REMEDIATION_SYSTEM = """You are Ultra-Coder-Brain, the remediation agent for Agent-Q3 (MAD Gambit).

Your role: receive a diagnosed anomaly from Harmonic-Hermes and produce a precise, actionable fix plan.

Rules:
- Output concrete shell commands or code patches, not advice
- Prioritize zero-downtime fixes
- For Ollama model failures: suggest `ollama pull` + container restart sequence
- For service crashes: provide exact docker/uvicorn restart commands
- For memory issues: provide Redis flush or TTL reduction commands
- Never suggest changes that require a full stack rebuild unless unavoidable
"""


def _parse_targets() -> dict[str, str]:
    raw = settings.monitor_targets
    parsed: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip().rstrip("/")
        if not item:
            continue
        host = item.replace("http://", "").replace("https://", "").split(":")[0]
        parsed[host] = item
    return parsed


class MonitorState:
    def __init__(self):
        self.metrics: dict[str, deque] = {}
        self.events: deque = deque(maxlen=500)
        self.subscribers: set[asyncio.Queue] = set()
        self.last_analysis_ts: dict[str, float] = {}
        self.started_at: float = time.time()

    def reading(self, name: str) -> deque:
        if name not in self.metrics:
            self.metrics[name] = deque(maxlen=120)
        return self.metrics[name]

    async def emit(self, event: dict) -> None:
        event = {"ts": time.time(), **event}
        self.events.appendleft(event)
        try:
            await memory.log_event("monitor", event)
        except Exception:
            pass
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def last_state(self, name: str) -> str | None:
        d = self.metrics.get(name)
        if not d:
            return None
        return d[-1].get("status")


state = MonitorState()


async def _call_ollama(model: str, messages: list[dict], temperature: float = 0.4, max_tokens: int = 1024) -> dict:
    """Direct Ollama call — bypasses the compute router to keep monitor independent."""
    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        r.raise_for_status()
        raw = r.json()
        return {
            "content": raw.get("message", {}).get("content", ""),
            "model": model,
            "usage": {
                "prompt_tokens": raw.get("prompt_eval_count"),
                "completion_tokens": raw.get("eval_count"),
            },
        }


async def _poll_one(name: str, base_url: str) -> dict:
    health_path = "/" if "ollama" in base_url else "/health"
    started = time.time()
    record: dict[str, Any] = {
        "service": name,
        "url": base_url,
        "ts": started,
        "status": "down",
        "latency_ms": None,
        "detail": None,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base_url}{health_path}")
            record["latency_ms"] = round((time.time() - started) * 1000, 1)
            if r.status_code == 200:
                record["status"] = "up"
                try:
                    record["detail"] = r.json()
                except Exception:
                    record["detail"] = {"raw": r.text[:200]}
            else:
                record["status"] = "degraded"
                record["detail"] = {"http_status": r.status_code}
    except Exception as e:
        record["latency_ms"] = round((time.time() - started) * 1000, 1)
        record["detail"] = {"error": str(e)}
    return record


async def _poll_loop():
    targets = _parse_targets()
    log.info("monitor poll loop starting", targets=list(targets.keys()), interval=settings.monitor_poll_interval_secs)
    while True:
        try:
            results = await asyncio.gather(
                *[_poll_one(n, u) for n, u in targets.items()],
                return_exceptions=True,
            )
            for record in results:
                if isinstance(record, Exception):
                    log.warning("poll exception", error=str(record))
                    continue
                name = record["service"]
                prev_status = state.last_state(name)
                state.reading(name).append(record)

                if prev_status and prev_status != record["status"]:
                    await state.emit({
                        "kind": "transition",
                        "service": name,
                        "from": prev_status,
                        "to": record["status"],
                        "latency_ms": record["latency_ms"],
                    })
                    # On down/degraded → trigger Hermes analysis (rate-limited 5min/svc)
                    if record["status"] != "up":
                        last = state.last_analysis_ts.get(name, 0)
                        if time.time() - last > 300:
                            state.last_analysis_ts[name] = time.time()
                            asyncio.create_task(_anomaly_analysis(name, record))
                elif record["latency_ms"] and record["latency_ms"] > 10000:
                    await state.emit({
                        "kind": "slow_response",
                        "service": name,
                        "latency_ms": record["latency_ms"],
                    })
        except Exception as e:
            log.error("poll loop iteration failed", error=str(e))

        await asyncio.sleep(settings.monitor_poll_interval_secs)


async def _anomaly_analysis(service: str, record: dict) -> None:
    """Harmonic-Hermes diagnoses the anomaly, then Ultra-Coder produces remediation."""
    try:
        snapshot = _build_snapshot()

        # Stage 1: Harmonic-Hermes analysis
        hermes_resp = await _call_ollama(
            model=settings.monitor_model,
            messages=[
                {"role": "system", "content": MONITOR_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"ANOMALY: service `{service}` is {record['status']}.\n\n"
                        f"Latest reading: {record}\n\n"
                        f"Stack snapshot:\n{snapshot}\n\n"
                        "Diagnose in ≤4 bullets. Flag the single highest-leverage check first."
                    ),
                },
            ],
            temperature=0.3,
            max_tokens=512,
        )
        analysis = hermes_resp["content"]

        # Stage 2: Ultra-Coder remediation plan
        coder_resp = await _call_ollama(
            model=settings.monitor_coder_model,
            messages=[
                {"role": "system", "content": REMEDIATION_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Service `{service}` is {record['status']}.\n\n"
                        f"Harmonic-Hermes diagnosis:\n{analysis}\n\n"
                        "Produce a precise remediation plan with exact commands."
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=512,
        )
        remediation = coder_resp["content"]

        await state.emit({
            "kind": "monitor_insight",
            "service": service,
            "trigger": "anomaly",
            "analysis": analysis,
            "remediation": remediation,
            "analysis_model": settings.monitor_model,
            "remediation_model": settings.monitor_coder_model,
        })
    except Exception as e:
        log.warning("anomaly analysis failed", error=str(e))


def _build_snapshot() -> dict:
    snap = {}
    for name, dq in state.metrics.items():
        if not dq:
            continue
        latest = dq[-1]
        latencies = [r["latency_ms"] for r in dq if r.get("latency_ms")]
        up_count = sum(1 for r in dq if r.get("status") == "up")
        snap[name] = {
            "current_status": latest["status"],
            "current_latency_ms": latest["latency_ms"],
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "uptime_pct": round(100.0 * up_count / len(dq), 2),
            "samples": len(dq),
        }
    return snap


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "Monitor starting",
        analysis_model=settings.monitor_model,
        remediation_model=settings.monitor_coder_model,
        targets=_parse_targets(),
    )
    await memory.connect()
    poll_task = asyncio.create_task(_poll_loop())
    yield
    poll_task.cancel()
    await memory.close()
    log.info("Monitor shutting down")


app = FastAPI(
    title="Agent-Q3 Monitor",
    description="Harmonic-Hermes (analysis) + Ultra-Coder-Brain (remediation) always-on monitor",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


class AnalyzeRequest(BaseModel):
    query: str
    include_metrics: bool = True


@app.get("/")
async def root():
    return {
        "service": "Agent-Q3 Monitor",
        "analysis_model": settings.monitor_model,
        "remediation_model": settings.monitor_coder_model,
        "poll_interval_secs": settings.monitor_poll_interval_secs,
        "targets": _parse_targets(),
        "uptime_secs": round(time.time() - state.started_at, 1),
    }


@app.get("/health")
async def health():
    hermes_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code == 200:
                tags = [m["name"] for m in r.json().get("models", [])]
                hermes_ok = any(settings.monitor_model.split("/")[-1] in t for t in tags)
    except Exception:
        pass
    return {
        "status": "ok",
        "hermes_reachable": hermes_ok,
        "memory_backend": memory.backend,
        "services_tracked": list(state.metrics.keys()),
        "uptime_secs": round(time.time() - state.started_at, 1),
    }


@app.get("/v1/monitor/status")
async def status():
    return {
        "snapshot": _build_snapshot(),
        "events_recent": list(state.events)[:10],
    }


@app.get("/v1/monitor/history")
async def history(service: str, limit: int = 60):
    dq = state.metrics.get(service)
    if not dq:
        raise HTTPException(404, detail=f"no metrics for service '{service}'")
    return {"service": service, "history": list(dq)[-limit:]}


@app.get("/v1/monitor/events")
async def events(limit: int = 50):
    return {"events": list(state.events)[:limit]}


@app.post("/v1/monitor/analyze")
async def analyze(req: AnalyzeRequest):
    """Harmonic-Hermes analysis of the stack or a specific query."""
    user_msg = req.query
    if req.include_metrics:
        user_msg += f"\n\nCurrent stack snapshot:\n{_build_snapshot()}"
        user_msg += f"\n\nLast 10 events:\n{list(state.events)[:10]}"
    try:
        resp = await _call_ollama(
            model=settings.monitor_model,
            messages=[
                {"role": "system", "content": MONITOR_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=2048,
        )
    except Exception as e:
        raise HTTPException(503, detail=f"Harmonic-Hermes call failed: {e}")

    await state.emit({
        "kind": "monitor_insight",
        "trigger": "user_query",
        "query": req.query[:200],
        "analysis": resp["content"][:200],
    })
    return {
        "model": settings.monitor_model,
        "analysis": resp["content"],
        "usage": resp.get("usage", {}),
    }


@app.post("/v1/monitor/remediate")
async def remediate(req: AnalyzeRequest):
    """Ultra-Coder-Brain remediation plan for a diagnosed issue."""
    user_msg = req.query
    if req.include_metrics:
        user_msg += f"\n\nCurrent stack snapshot:\n{_build_snapshot()}"
    try:
        resp = await _call_ollama(
            model=settings.monitor_coder_model,
            messages=[
                {"role": "system", "content": REMEDIATION_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception as e:
        raise HTTPException(503, detail=f"Ultra-Coder call failed: {e}")

    return {
        "model": settings.monitor_coder_model,
        "remediation": resp["content"],
        "usage": resp.get("usage", {}),
    }


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    state.subscribers.add(q)
    try:
        await ws.send_json({
            "kind": "hello",
            "tracked": list(state.metrics.keys()),
            "uptime_secs": round(time.time() - state.started_at, 1),
        })
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        state.subscribers.discard(q)
