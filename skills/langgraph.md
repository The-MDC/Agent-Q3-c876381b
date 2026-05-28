---
name: langgraph
description: LangGraph agent workflow construction, multi-step orchestration, state machine pipelines, and multi-agent coordination
triggers: [langgraph, agent graph, workflow, state machine, pipeline, dag, agent loop, tool node, checkpoint, supervisor, worker, agentic, orchestration flow]
roles: [reasoner, tandem, coder]
---

## When to activate
User asks to build, debug, or reason about LangGraph workflows, agent pipelines, or multi-agent coordination graphs.

## Core primitives

### StateGraph
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]   # reducer: append
    context: str
    step: int

graph = StateGraph(AgentState)
```

### Nodes
```python
def research_node(state: AgentState) -> dict:
    # return partial state update
    return {"messages": [AIMessage(content="...")], "step": state["step"] + 1}

graph.add_node("research", research_node)
```

### Edges
```python
# Unconditional
graph.add_edge("research", "draft")

# Conditional routing
def route(state: AgentState) -> str:
    if state["step"] > 3:
        return END
    return "review"

graph.add_conditional_edges("draft", route, {"review": "review", END: END})
```

### Entry point and compile
```python
graph.set_entry_point("research")
app = graph.compile(checkpointer=MemorySaver())
```

## Checkpointers (persistence)
```python
from langgraph.checkpoint.memory import MemorySaver       # in-memory (dev)
from langgraph.checkpoint.redis import RedisSaver          # production (24h TTL)

# Redis (matches Agent-Q3 Redis config)
saver = RedisSaver.from_conn_string(os.environ["REDIS_URL"])
app = graph.compile(checkpointer=saver)
```

## Multi-agent patterns

### Supervisor → Worker
```python
# Supervisor node decides which worker to call next
def supervisor(state):
    decision = llm.invoke(state["messages"])
    return {"next": decision.tool_calls[0]["name"]}

graph.add_node("supervisor", supervisor)
for worker in ["research", "code", "review"]:
    graph.add_node(worker, worker_fn)
    graph.add_edge(worker, "supervisor")

graph.add_conditional_edges("supervisor", lambda s: s["next"],
    {"research": "research", "code": "code", "review": "review", END: END})
```

### Tandem pipeline (Agent-Q3 pattern)
```
Kimi-Linear (plan + long-context intake)
    → Harmonic-Hermes (refinement + evaluation)
    → Qwen3-Coder-53B (implementation)
```
Wire as three sequential nodes with state passed between them.

## Model assignment per node

| Node purpose | Model | Why |
|---|---|---|
| Planning / intake | Kimi-Linear (`nicholasjmcleod/kimi-linear:q6_k`) | 1M ctx, handles full codebase or docs |
| Evaluation / critique | Harmonic-Hermes (`nicholasjmcleod/harmonic-hermes:q6_k`) | strong reasoning, fast |
| Code generation | Qwen3-Coder-53B (`nicholasjmcleod/qwen3-coder-53b:q6_k`) | TOTAL-RECALL, 53B coder |
| Structured reasoning steps | Kimi-Distilled (`nicholasjmcleod/kimi-distilled:iq4_xs`) | always-on `<think>` |

## Streaming
```python
config = {"configurable": {"thread_id": "session-123"}}
for chunk in app.stream({"messages": [HumanMessage(content=query)]}, config):
    print(chunk)
```

## Common pipeline: Research → Draft → Review loop
```
research_node → draft_node → review_node
                                 ↓           ↑
                            approve?  ──No──┘
                                 ↓
                               END
```
Max 3 iterations to prevent loops; track iteration count in state.

## Delegation
For implementation, call the coder service:
```
POST http://coder:8001/v1/coder
{
  "task": "build langgraph workflow",
  "context": "<graph spec>",
  "model": "qwen3-coder-53b:q6_k"
}
```
