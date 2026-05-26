"""LangGraph decision workflow for multi-agent orchestration.

Harmonic-Hermes uses this graph to decide:
1. Should I spawn sub-agents?
2. Which agents to spawn?
3. How to synthesize their results?
"""

from __future__ import annotations

from typing import TypedDict

import structlog
from langgraph.graph import END, StateGraph

from ..router import ComputeRouter

logger = structlog.get_logger(__name__)


class AgentState(TypedDict):
    """State for multi-agent workflow."""

    conversation_id: str
    query: str
    context: dict
    should_spawn: bool
    spawned_agents: list[str]
    reasoner_result: str | None
    coder_result: str | None
    synthesis: str | None
    final_response: str


class DecisionGraph:
    """LangGraph workflow for multi-agent decision-making."""

    def __init__(self, compute_router: ComputeRouter):
        self.compute = compute_router
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the decision workflow."""
        graph = StateGraph(AgentState)

        graph.add_node("analyze_query", self._analyze_query)
        graph.add_node("spawn_reasoner", self._spawn_reasoner)
        graph.add_node("spawn_coder", self._spawn_coder)
        graph.add_node("synthesize", self._synthesize)
        graph.add_node("single_agent", self._single_agent)

        graph.add_edge("spawn_reasoner", "synthesize")
        graph.add_edge("spawn_coder", "synthesize")
        graph.add_edge("synthesize", END)
        graph.add_edge("single_agent", END)

        graph.add_conditional_edges(
            "analyze_query",
            self._should_spawn,
            {
                True: "spawn_reasoner",
                False: "single_agent",
            },
        )

        graph.set_entry_point("analyze_query")
        return graph.compile()

    async def _analyze_query(self, state: AgentState) -> AgentState:
        """Analyze query complexity."""
        query = state["query"]
        complexity_indicators = [
            "research", "analyze", "investigate", "compare",
            "implement", "debug", "refactor", "optimize",
            "design", "architecture", "complex", "difficult",
        ]
        should_spawn = any(ind in query.lower() for ind in complexity_indicators)
        state["should_spawn"] = should_spawn
        logger.info("query analyzed", should_spawn=should_spawn, query=query[:100])
        return state

    def _should_spawn(self, state: AgentState) -> bool:
        return state["should_spawn"]

    async def _spawn_reasoner(self, state: AgentState) -> AgentState:
        """Spawn Kimi-Linear for deep analysis."""
        try:
            result = await self.compute.route(
                model_role="reasoner",
                messages=[{"role": "user", "content": state["query"]}],
                max_tokens=4096,
            )
            state["reasoner_result"] = result.get("message", {}).get("content", "")
            logger.info("reasoner spawned", query=state["query"][:100])
        except Exception as e:
            logger.error("reasoner spawn failed", error=str(e))
            state["reasoner_result"] = f"Error: {e}"
        return state

    async def _spawn_coder(self, state: AgentState) -> AgentState:
        """Spawn Qwen3-Coder-53B for implementation."""
        try:
            result = await self.compute.route(
                model_role="coder",
                messages=[{"role": "user", "content": state["query"]}],
                max_tokens=4096,
            )
            state["coder_result"] = result.get("message", {}).get("content", "")
            logger.info("coder spawned", query=state["query"][:100])
        except Exception as e:
            logger.error("coder spawn failed", error=str(e))
            state["coder_result"] = f"Error: {e}"
        return state

    async def _synthesize(self, state: AgentState) -> AgentState:
        """Harmonic-Hermes synthesizes Reasoner + Coder results."""
        synthesis_prompt = f"""You are Harmonic-Hermes, the synthesis model in the Agent-Q3 pipeline.
Two agents have analyzed this task:

TASK: {state["query"]}

REASONER ANALYSIS (Kimi-Linear):
{state.get("reasoner_result", "No response")}

CODER ANALYSIS (Qwen3-Coder-53B):
{state.get("coder_result", "No response")}

Synthesize these analyses into a coherent, actionable response.
"""
        try:
            result = await self.compute.route(
                model_role="tandem",
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=2048,
            )
            synthesis = result.get("message", {}).get("content", "")
            state["synthesis"] = synthesis
            state["final_response"] = synthesis
            logger.info("synthesis complete")
        except Exception as e:
            logger.error("synthesis failed", error=str(e))
            state["final_response"] = f"Error: {e}"
        return state

    async def _single_agent(self, state: AgentState) -> AgentState:
        """Harmonic-Hermes handles query alone."""
        try:
            result = await self.compute.route(
                model_role="tandem",
                messages=[{"role": "user", "content": state["query"]}],
                max_tokens=2048,
            )
            state["final_response"] = result.get("message", {}).get("content", "")
            logger.info("single agent (tandem) mode")
        except Exception as e:
            logger.error("tandem agent failed", error=str(e))
            state["final_response"] = f"Error: {e}"
        return state

    async def invoke(self, state: AgentState) -> AgentState:
        """Run the decision graph."""
        return await self.graph.ainvoke(state)


_decision_graph: DecisionGraph | None = None


def get_decision_graph(compute_router: ComputeRouter) -> DecisionGraph:
    """Get or create decision graph."""
    global _decision_graph
    if _decision_graph is None:
        _decision_graph = DecisionGraph(compute_router)
    return _decision_graph
