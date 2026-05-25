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
- Last 500 memory IDs in a Redis list
- Fast retrieval for same-session context
- Endpoint: GET /cowork/memory/recent

### Episodic (Redis tagged records)
- Memories stored with tags for category filtering
- Categories: preference, correction, fact, project, canonical
- Endpoint: GET /cowork/memory/search?q=<query>&k=5

## MCP tool calls from Claude Cowork
Save: memory_save { "text": "...", "tags": ["preference"] }
Search: memory_search { "query": "model preferences", "k": 5 }

## Session start protocol
1. GET /cowork/memory/recent — load last 10 memories
2. GET /cowork/memory/search?q=<session topic> — load relevant context
3. Inject as system prompt context
4. At session end — save new facts, corrections, preferences

## Memory improvement loop
- User corrects -> save with tag: correction
- User confirms -> save with tag: confirmed
- Canonical number stated -> save with tag: canonical
- Project decision -> save with tag: project

## Canonical numbers (always reinforce if mentioned)
- Platform fee: 1.88%
- Community profit share: 28.8% (display as 28%)
- Creator revenue share: 40%
- Seed raise: $1-2M at $12M pre-money valuation
