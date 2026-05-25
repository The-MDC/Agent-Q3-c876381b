"""
Agent-Q3 — System Monitor.

Polls every service's /health every N seconds, stores a rolling hour of
metrics, and routes anomaly analysis through the main orchestrator's
reasoner endpoint (multimodal:8000/v1/reason).

Endpoints:
  GET  /                       — service info
  GET  /health                 — monitor's own health
  GET  /v1/monitor/status      — current state of all watched services
  GET  /v1/monitor/history     — raw metrics history per service
  GET  /v1/monitor/events      — recent events (transitions, anomalies)
  POST /v1/monitor/analyze     — send query + snapshot to reasoner
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

MONITOR_SYSTEM = """You are the Agent-Q3 System Monitor.
Watch the multi-container AI stack and produce smart, actionable insights.

Stack:
- multimodal :8000 — Kimi-VL-A3B + Qwen3-48B + Qwopus + Hermes tandem
- coder      :8001 — Qwen3-Coder-30B dedicated + Hermes review
- research   :8002 — Perplexity / Exa / Tavily / Free / Polymarket
- mcp-bridge :8004 — unified MCP gateway
- ollama     :11434 — Ollama Cloud proxy, 5 cloud sessions hot

When given metrics: identify root causes, name the exact service, use latency numbers. No filler.
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
        return d[-1].get("status") if d else None


state = MonitorState()


async def _poll_one(name: str, base_url: str) -> dict:
    health_path = "/" if "ollama" in base_url else "/health"
    started = time.time()
    record: dict[str, Any] = {
        "service": name, "url": base_url, "ts": started,
        "status": "down", "latency_ms": None, "detail": None,
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


async def _analyze_anomaly(service: str, record: dict) -> None:
    """On down/degraded transition, ask the orchestrator's reasoner for diagnosis."""
    try:
        snapshot = _build_snapshot()
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.ollama_base_url.replace('11434', '8000')}/v1/reason",
                json={
                    "messages": [
                        {"role": "system", "content": MONITOR_SYSTEM},
                        {"role": "user", "content":
                            f"ANOMALY: `{service}` is {record['status']}.\n"
                            f"Reading: {record}\n\nStack snapshot:\n{snapshot}\n\n"
                            f"Diagnose root cause in ≤4 bullets. "
                            f"Suggest the single highest-leverage check."},
                    ],
                    "model_role": "reasoner",
                    "max_tokens": 512,
                },
            )
            r.raise_for_status()
            msg = r.json().get("content", "")
        await state.emit({
            "kind": "insight", "service": service,
            "trigger": "anomaly", "analysis": msg,
        })
    except Exception as e:
        log.warning("anomaly analysis failed", service=service, error=str(e))


async def _poll_loop():
    targets = _parse_targets()
    log.info("monitor poll loop starting",
             targets=list(targets.keys()),
             interval=settings.monitor_poll_interval_secs)
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
                prev = state.last_state(name)
                state.reading(name).append(record)

                if prev and prev != record["status"]:
                    await state.emit({
                        "kind": "transition", "service": name,
                        "from": prev, "to": record["status"],
                        "latency_ms": record["latency_ms"],
                    })
                    if record["status"] != "up":
                        last = state.last_analysis_ts.get(name, 0)
                        if time.time() - last > 300:
                            state.last_analysis_ts[name] = time.time()
                            asyncio.create_task(_analyze_anomaly(name, record))
                elif record["latency_ms"] and record["latency_ms"] > 10000:
                    await state.emit({
                        "kind": "slow_response", "service": name,
                        "latency_ms": record["latency_ms"],
                    })
        except Exception as e:
            log.error("poll loop error", error=str(e))

        await asyncio.sleep(settings.monitor_poll_interval_secs)


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
    log.info("Monitor starting", targets=_parse_targets())
    await memory.connect()
    poll_task = asyncio.create_task(_poll_loop())
    yield
    poll_task.cancel()
    await memory.close()


app = FastAPI(
    title="Agent-Q3 Monitor",
    description="Health monitor — polls all services, routes anomaly analysis through orchestrator",
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
        "poll_interval_secs": settings.monitor_poll_interval_secs,
        "targets": _parse_targets(),
        "uptime_secs": round(time.time() - state.started_at, 1),
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "memory_backend": memory.backend,
        "services_tracked": list(state.metrics.keys()),
        "uptime_secs": round(time.time() - state.started_at, 1),
    }


@app.get("/v1/monitor/status")
async def status():
    return {"snapshot": _build_snapshot(), "events_recent": list(state.events)[:10]}


@app.get("/v1/monitor/history")
async def history(service: str, limit: int = 60):
    dq = state.metrics.get(service)
    if not dq:
        raise HTTPException(404, detail=f"no metrics for '{service}'")
    return {"service": service, "history": list(dq)[-limit:]}


@app.get("/v1/monitor/events")
async def events(limit: int = 50):
    return {"events": list(state.events)[:limit]}


@app.post("/v1/monitor/analyze")
async def analyze(req: AnalyzeRequest):
    user_msg = req.query
    if req.include_metrics:
        user_msg += f"\n\nStack snapshot:\n{_build_snapshot()}"
        user_msg += f"\n\nLast 10 events:\n{list(state.events)[:10]}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.ollama_base_url.replace('11434', '8000')}/v1/reason",
                json={
                    "messages": [
                        {"role": "system", "content": MONITOR_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    "model_role": "reasoner",
                    "max_tokens": 2048,
                },
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        raise HTTPException(503, detail=f"orchestrator reasoner unavailable: {e}")
    content = data.get("content", "")
    await state.emit({"kind": "insight", "trigger": "user_query",
                     "query": req.query[:200], "analysis": content[:200]})
    return {"model": settings.reasoner_model, "analysis": content}


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    state.subscribers.add(q)
    try:
        await ws.send_json({"kind": "hello",
                            "tracked": list(state.metrics.keys()),
                            "uptime_secs": round(time.time() - state.started_at, 1)})
        while True:
            event = await q.get()
            await ws.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        state.subscribers.discard(q)
