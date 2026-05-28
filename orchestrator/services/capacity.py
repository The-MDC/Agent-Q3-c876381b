"""
Capacity tracker — triggers sub-agent spawning when a model role is overloaded.

Thresholds (both evaluated continuously via Redis sliding windows):
  - utilization > 85% sustained for 5 minutes  → spawn
  - queue depth  > 4  sustained for 4 minutes  → spawn
"""

from __future__ import annotations

import time

import structlog

from ..memory import memory

log = structlog.get_logger(__name__)

# Thresholds
UTIL_THRESHOLD = 0.85  # 85% utilization
UTIL_WINDOW_SECS = 300  # 5-minute window
QUEUE_THRESHOLD = 4  # items in flight
QUEUE_WINDOW_SECS = 240  # 4-minute window


async def record_request_start(role: str) -> None:
    """Call when a request for `role` begins."""
    ts = time.time()
    await memory.log_event(f"cap:start:{role}", {"ts": ts})


async def record_request_end(role: str) -> None:
    """Call when a request for `role` completes."""
    ts = time.time()
    await memory.log_event(f"cap:end:{role}", {"ts": ts})


async def _count_events(channel: str, since: float) -> int:
    """Count events in a channel newer than `since`."""
    events = await memory.get_events(channel, limit=500)
    return sum(1 for e in events if e.get("ts", 0) >= since)


async def should_spawn_subagent(role: str) -> bool:
    """
    Returns True if the role model is overloaded and work should be
    offloaded to sub-agents.

    Conditions (either triggers spawn):
      1. Utilization > 85% over last 5 min
         utilization = in-flight requests / (window_secs * assumed_max_rps)
         approximated as: open requests that started but haven't ended
      2. Queue depth > 4 sustained for the last 4 min
         (requests started in window with no matching end event)
    """
    now = time.time()

    starts_5min = await _count_events(f"cap:start:{role}", now - UTIL_WINDOW_SECS)
    ends_5min = await _count_events(f"cap:end:{role}", now - UTIL_WINDOW_SECS)
    inflight_5min = max(starts_5min - ends_5min, 0)

    starts_4min = await _count_events(f"cap:start:{role}", now - QUEUE_WINDOW_SECS)
    ends_4min = await _count_events(f"cap:end:{role}", now - QUEUE_WINDOW_SECS)
    inflight_4min = max(starts_4min - ends_4min, 0)

    # Max assumed concurrent requests per model (conservative)
    assumed_max = 5
    utilization = inflight_5min / assumed_max if assumed_max > 0 else 0.0

    over_util = utilization >= UTIL_THRESHOLD
    over_queue = inflight_4min > QUEUE_THRESHOLD

    if over_util or over_queue:
        log.warning(
            "model overloaded — sub-agent spawn recommended",
            role=role,
            utilization=round(utilization, 2),
            inflight_4min=inflight_4min,
            trigger="util" if over_util else "queue",
        )
        return True

    return False


async def capacity_status() -> dict:
    """Return current capacity metrics for all tracked roles."""
    roles = ["reasoner", "tandem", "coder", "coder_dedicated", "fallback", "genstruct", "infinity_parser"]
    now = time.time()
    result = {}
    for role in roles:
        starts = await _count_events(f"cap:start:{role}", now - UTIL_WINDOW_SECS)
        ends = await _count_events(f"cap:end:{role}", now - UTIL_WINDOW_SECS)
        inflight = max(starts - ends, 0)
        result[role] = {
            "inflight": inflight,
            "utilization": round(inflight / 5, 2),
            "spawn_recommended": inflight / 5 >= UTIL_THRESHOLD or inflight > QUEUE_THRESHOLD,
        }
    return result
