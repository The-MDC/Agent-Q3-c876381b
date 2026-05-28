"""
Unit tests — Agent-Q3 orchestrator
Tests classifier, router logic, and schema validation without containers.
"""

from orchestrator.config import Settings
from orchestrator.models import ChatRequest, Message, classify_task


def msg(content: str, role: str = "user") -> Message:
    return Message(role=role, content=content)


class TestClassifier:
    def test_code_prompt_routes_to_coder(self):
        msgs = [msg("write a python function to fetch data from an API")]
        assert classify_task(msgs) == "coder"

    def test_reasoning_prompt_routes_to_reasoner(self):
        msgs = [msg("analyze the market sentiment for prediction markets and explain the tradeoffs")]
        assert classify_task(msgs) == "reasoner"

    def test_solidity_routes_to_coder(self):
        msgs = [msg("write a Solidity ERC-20 contract with 1.88% fee logic")]
        assert classify_task(msgs) == "coder"

    def test_research_routes_to_reasoner(self):
        msgs = [msg("research the best approach for a prediction market oracle resolution strategy")]
        assert classify_task(msgs) == "reasoner"

    def test_tie_defaults_to_coder(self):
        msgs = [msg("hello")]
        assert classify_task(msgs) == "coder"


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.reasoner_model == "nicholasjmcleod/kimi-linear:q6_k"
        assert s.coder_model == "nicholasjmcleod/qwen3-coder-53b:q6_k"
        assert s.tandem_model == "nicholasjmcleod/harmonic-hermes:q6_k"
        assert s.coder_dedicated_model == "nicholasjmcleod/qwen3-coder-53b:q6_k"
        assert s.kimi_distilled_model == "nicholasjmcleod/kimi-distilled:iq4_xs"
        assert s.genstruct_model == "nicholasjmcleod/genstruct:q6_k"
        assert s.infinity_parser_model == "nicholasjmcleod/infinity-parser:latest"
        assert s.monitor_model == "nicholasjmcleod/harmonic-hermes:q6_k"
        assert s.monitor_coder_model == "nicholasjmcleod/qwen3-coder-53b:q6_k"
        assert s.openrouter_model == "moonshotai/kimi-k2.6"
        assert s.local_weight == 38
        assert s.moonshot_weight == 37
        assert s.openrouter_weight == 15
        assert s.hf_weight == 8
        assert s.runpod_weight == 2
        assert s.compute_strategy == "cloud_priority"

    def test_weights_sum_to_100(self):
        s = Settings()
        assert s.local_weight + s.moonshot_weight + s.openrouter_weight + s.hf_weight + s.runpod_weight == 100


class TestChatRequest:
    def test_default_role_is_auto(self):
        req = ChatRequest(messages=[msg("test")])
        assert req.model_role == "auto"

    def test_force_backend_optional(self):
        req = ChatRequest(messages=[msg("test")], force_backend=None)
        assert req.force_backend is None

    def test_tandem_request_structure(self):
        req = ChatRequest(messages=[msg("implement a prediction market contract")], model_role="auto", max_tokens=4096)
        assert req.max_tokens == 4096

    def test_message_fields(self):
        m = msg("analyze this")
        assert m.role == "user"
        assert m.content == "analyze this"

    def test_stream_default(self):
        req = ChatRequest(messages=[msg("test")])
        assert req.stream is False
