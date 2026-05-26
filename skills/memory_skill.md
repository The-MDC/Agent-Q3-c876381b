# Memory Improvement Skill — Agent-Q3

## Trigger
Activate when:
- User says "remember", "save this", "don't forget", "note that"
- User corrects Agent-Q3 (that's wrong, stop doing X, I prefer Y)
- User shares preferences, project facts, or canonical numbers
- Beginning of a new session — load recent memories to restore context
- User asks "what do you remember", "recall", "what do you know about"

## Architecture

### Short-term (Redis, 24h TTL)
- Last 100 memory IDs in a Redis list
- Fast retrieval for same-session context
- Endpoint: GET /v1/memory/recent

### Memory improvement loop
- User corrects → save with tag: correction
- User confirms → save with tag: confirmed
- Canonical number stated → save with tag: canonical
- Project decision → save with tag: project

## Canonical numbers (always reinforce if mentioned)
- Platform fee: 1.88%
- Community profit share: 28.8% (display as 28%)
- Creator revenue share: 40%
- Seed raise: $1-2M at $12M pre-money valuation
