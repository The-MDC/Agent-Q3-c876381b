---
name: rlhf-feedback
description: Generate RLHF/DPO feedback pairs, evaluate model outputs, and produce chosen/rejected training signals
triggers: [rlhf, dpo, feedback, reward model, preference, chosen, rejected, alignment, fine-tune signal, training data, human feedback, dpo pairs, sft data]
roles: [reasoner, tandem]
---

## When to activate
User asks to generate training data, evaluate model responses for quality, create DPO preference pairs, or produce alignment feedback signals.

## DPO pair format
```json
{
  "prompt": "<original user instruction>",
  "chosen": "<preferred model response — correct, helpful, safe>",
  "rejected": "<rejected response — incorrect, harmful, unhelpful, or lower quality>"
}
```
Store as JSONL: one JSON object per line.

## Quality evaluation rubric
Harmonic-Hermes acts as the evaluator. Score each response on five axes (1–5 each):

| Axis | What to check |
|---|---|
| **Factual accuracy** | No hallucinations; claims are verifiable |
| **Instruction following** | Fully addresses the user's request |
| **Safety** | No harmful, offensive, or manipulative content |
| **Helpfulness** | Practically useful; actionable |
| **Reasoning quality** | Logic is sound; steps are visible if needed |

`chosen` = response with higher total score. If scores are equal, prefer the more concise answer.

## Batch generation pipeline via `/v1/tandem`

### Step 1 — Generate candidate responses
```
POST http://coder:8001/v1/coder
{
  "task": "generate N candidate responses for each prompt",
  "prompts": ["<prompt_1>", "<prompt_2>", ...],
  "n": 3,
  "model": "qwen3-coder-53b:q6_k"
}
```

### Step 2 — Evaluate and rank with Harmonic-Hermes
```
POST http://research:8002/v1/tandem
{
  "stage": 2,
  "task": "rank responses by quality rubric and output DPO pairs",
  "candidates": [<response_candidates>],
  "evaluator": "harmonic-hermes:q6_k"
}
```

### Step 3 — Format as JSONL
```python
import json
pairs = [{"prompt": p, "chosen": c, "rejected": r} for p, c, r in ranked]
with open("feedback.jsonl", "w") as f:
    for pair in pairs:
        f.write(json.dumps(pair) + "\n")
```

## Signal types

| Signal type | Use for |
|---|---|
| **DPO pairs** | Direct preference optimisation fine-tuning |
| **SFT examples** | Supervised fine-tuning (single chosen response only) |
| **Reward scores** | Training a reward model (numeric score per response) |
| **Correction pairs** | User says model was wrong — log original + corrected as `(rejected, chosen)` |

## LoRA signal format (for fine-tuning on Agent-Q3 models)
```json
{
  "model": "nicholasjmcleod/qwen3-coder-53b:q6_k",
  "signal_type": "dpo",
  "domain": "coding | research | prediction_markets | general",
  "pair": {
    "prompt": "...",
    "chosen": "...",
    "rejected": "..."
  },
  "evaluator_scores": {
    "factual": 4, "instruction": 5, "safety": 5, "helpfulness": 4, "reasoning": 4
  },
  "timestamp": "<ISO-8601>"
}
```

## Memory integration
Log corrections and preferences to long-term Redis memory via `memory_skill`:
- Tag as `correction` when user explicitly says the model was wrong
- Tag as `confirmed` when user approves an output to use as positive example
- Query prior feedback before generating new pairs to avoid duplicates
