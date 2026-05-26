---
name: system-monitor
description: Use the Harmonic-Hermes monitor pair for stack health and meta-analysis
triggers: [system status, stack health, is the server up, monitor, diagnose, why is it slow, performance]
roles: [reasoner, tandem, coder]
---
The monitor service (`http://monitor:8003`) runs outside the local orchestration and watches every service continuously. It uses Harmonic-Hermes-9B for analysis and Qwen3-Coder-53B for remediation.

Endpoints to use:
- `GET /v1/monitor/status` — snapshot of all services + recent events
- `GET /v1/monitor/history?service=multimodal&limit=60` — raw 30s-interval metrics
- `GET /v1/monitor/events?limit=50` — anomalies, transitions, Hermes insights
- `POST /v1/monitor/analyze` — `{query, include_metrics: true}` — asks Harmonic-Hermes to diagnose

For any question about stack health, latency, or "why is X slow", call `/v1/monitor/analyze` and surface the Hermes analysis verbatim. Do not guess from prior context.
