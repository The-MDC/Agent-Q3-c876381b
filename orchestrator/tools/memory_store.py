from __future__ import annotations
"""
memory_store.py — Persistent memory for Agent-Q3.

Architecture:
  - Short-term:  Redis (TTL 24h) — fast recent context, session storage
  - Episodic:    Structured JSON records stored in Redis hashes

Usage:
  from orchestrator.tools.memory_store import MemoryStore
  mem = MemoryStore()
  await mem.save(text="Nick prefers Q8_0 quants", tags=["preference","models"])
  results = await mem.get_recent(n=10)
"""
import hashlib
import json
import time
from typing import Optional

from orchestrator.config import settings


class MemoryStore:
    def __init__(self):
        self.redis_url = getattr(settings, "redis_url", None)

    async def save(
        self,
        text: str,
        tags: list[str] | None = None,
        source: str = "agent",
        session_id: str | None = None,
    ) -> str:
        """Save a memory entry to Redis. Returns memory ID."""
        mem_id = hashlib.sha256(f"{text}{time.time()}".encode()).hexdigest()[:16]
        record = {
            "id": mem_id,
            "text": text,
            "tags": tags or [],
            "source": source,
            "session_id": session_id,
            "timestamp": int(time.time()),
        }
        await self._save_redis(mem_id, record)
        return mem_id

    async def search(
        self,
        query: str,
        k: int = 5,
        tags: list[str] | None = None,
        min_score: float = 0.7,
    ) -> list[dict]:
        """Search recent memories (lexical match on text, no vector backend)."""
        recent = await self._get_redis_recent(100)
        query_lower = query.lower()
        matches = []
        for entry in recent:
            text = entry.get("text", "").lower()
            entry_tags = entry.get("tags", [])
            if query_lower in text:
                matches.append(entry)
            elif tags and any(t in entry_tags for t in tags):
                matches.append(entry)
        return matches[:k]

    async def get_recent(self, n: int = 10) -> list[dict]:
        """Get n most recent memories from Redis."""
        return await self._get_redis_recent(n)

    async def get_episodic(self, category: str) -> list[dict]:
        """Get memories by tag/category from Redis."""
        recent = await self._get_redis_recent(200)
        return [m for m in recent if category in m.get("tags", [])]

    # -- Redis backend -------------------------------------------------------
    async def _save_redis(self, mem_id: str, record: dict):
        if not self.redis_url:
            return
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(self.redis_url)
            await r.setex(f"mem:{mem_id}", 86400, json.dumps(record))
            await r.lpush("mem:recent", mem_id)
            await r.ltrim("mem:recent", 0, 499)
            await r.aclose()
        except Exception:
            pass

    async def _get_redis_recent(self, n: int) -> list[dict]:
        if not self.redis_url:
            return []
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(self.redis_url)
            ids = await r.lrange("mem:recent", 0, n - 1)
            results = []
            for mid in ids:
                raw = await r.get(f"mem:{mid.decode()}")
                if raw:
                    results.append(json.loads(raw))
            await r.aclose()
            return results
        except Exception:
            return []
