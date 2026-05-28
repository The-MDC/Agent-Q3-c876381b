from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Model stack — sourced from MADdegens/Models HF bucket ────────────────
    # GGUFs pulled via `hf buckets cp` → `ollama create` → `ollama push` (cloud)
    # Roles and their Ollama tags:
    #
    #   reasoner         nicholasjmcleod/kimi-linear:q6_k           Kimi-Linear-48B (1M ctx preprocessor)    /v1/instruct /v1/chat
    #   tandem           nicholasjmcleod/harmonic-hermes:q6_k       Harmonic-Hermes-9B (refine+monitor)      /v1/tandem stage-2 + /v1/monitor
    #   coder            nicholasjmcleod/qwen3-coder-53b:q6_k       Qwen3-Coder-53B TOTAL-RECALL (primary)   /v1/code /v1/tandem stage-3
    #   coder_dedicated  nicholasjmcleod/qwen3-coder-53b:q6_k       Qwen3-Coder-53B TOTAL-RECALL (dedicated) /v1/coder
    #   kimi_distilled   nicholasjmcleod/kimi-distilled:iq4_xs      Qwen3.6-35B K2.6-Distilled (reasoning)  /v1/reason
    #   genstruct        nicholasjmcleod/genstruct:q6_k             Genstruct-7B (structure middleware)       /v1/generate + pre/post all
    #   infinity_parser  nicholasjmcleod/infinity-parser:latest     Infinity-Parser2-Pro (parse midw.)       /v1/parse + pre/post all
    #   monitor_pair     harmonic-hermes + qwen3-coder-53b          Hermes watches / Coder remediates        /v1/monitor/analyze

    reasoner_model: str = "nicholasjmcleod/kimi-linear:q6_k"
    tandem_model: str = "nicholasjmcleod/harmonic-hermes:q6_k"
    # coder and coder_dedicated both point to Qwen3-Coder-53B TOTAL-RECALL
    coder_model: str = "nicholasjmcleod/qwen3-coder-53b:q6_k"
    coder_dedicated_model: str = "nicholasjmcleod/qwen3-coder-53b:q6_k"
    kimi_distilled_model: str = "nicholasjmcleod/kimi-distilled:iq4_xs"
    genstruct_model: str = "nicholasjmcleod/genstruct:q6_k"
    infinity_parser_model: str = "nicholasjmcleod/infinity-parser:latest"

    # ── Monitor pair — Harmonic-Hermes (analysis) + Qwen3-Coder-53B (remediation) ──
    monitor_model: str = "nicholasjmcleod/harmonic-hermes:q6_k"
    monitor_coder_model: str = "nicholasjmcleod/qwen3-coder-53b:q6_k"
    monitor_poll_interval_secs: int = 30
    monitor_targets: str = (
        "http://multimodal:8000,http://coder:8001,http://research:8002,http://mcp-bridge:8004,http://ollama:11434"
    )

    # ── Ollama endpoint ───────────────────────────────────────────────────────
    ollama_base_url: str = "http://ollama:11434"
    ollama_api_url: str = "http://ollama:11434/api"
    openwebui_url: str = "http://localhost:3000"

    # ── Ollama Cloud auth ─────────────────────────────────────────────────────
    ollama_cloud_enabled: bool = True
    ollama_cloud_account: str = "nicholasjmcleod@gmail.com"
    ollama_cloud_device: str = "LN-8RDGA90Ultra"

    # ── [2] Moonshot API — primary Kimi K2.6 endpoint (free credits) ─────────
    moonshot_api_key: str = ""
    moonshot_api_url: str = "https://api.moonshot.ai/v1"
    moonshot_model: str = "kimi-k2-0711-preview"

    # ── [3] OpenRouter — K2.6 fallback ───────────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_api_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "moonshotai/kimi-k2.6"

    # ── [4] HuggingFace Router — tertiary compute ─────────────────────────────
    hf_token: str = ""
    hf_token_2: str = ""
    hf_token_3: str = ""
    hf_router_url: str = "https://router.huggingface.co/v1"
    hf_reasoner_model: str = "moonshotai/Kimi-K2-Instruct-0905"
    hf_tandem_model: str = "NousResearch/Hermes-3-Llama-3.1-8B"
    hf_coder_model: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
    hf_frontier_reasoner: str = "moonshotai/Kimi-K2-Instruct-0905"
    hf_frontier_coder: str = "Qwen/Qwen3-Coder-480B-A35B-Instruct"

    # ── [5] RunPod Serverless — quaternary GPU burst ──────────────────────────
    runpod_api_key: str = ""
    runpod_s3_key: str = ""
    runpod_reasoner_endpoint_id: str = "kukl55t0053lob"
    runpod_coder_endpoint_id: str = "kukl55t0053lob"
    runpod_api_url: str = "https://api.runpod.ai/v2"
    runpod_gpu_class: str = "AMPERE_16"

    # ── HF Bucket — model source ──────────────────────────────────────────────
    hf_bucket_repo: str = "MADdegens/Models"
    hf_bucket_base: str = "https://huggingface.co/MADdegens/Models/resolve/main"
    model_cache_dir: str = "/models"

    # ── Search + Research tools ───────────────────────────────────────────────
    perplexity_api_key: str = ""
    perplexity_default_model: str = "sonar-pro"
    exa_api_key: str = ""
    tavily_api_key: str = ""
    smithery_api_key: str = ""

    # ── Compute routing ───────────────────────────────────────────────────────
    # cloud_priority = Ollama Cloud → Moonshot → OpenRouter → HuggingFace → RunPod
    compute_strategy: Literal[
        "cloud_priority",
        "round_robin",
        "load_based",
        "local_first",
        "hf_first",
        "runpod_first",
        "openrouter_first",
    ] = "cloud_priority"

    # Weights calibrated to actual subscription capacity (May 2026):
    #   Ollama Cloud Pro  ($20/mo): 3 concurrent sessions, ~$0.67/day GPU time
    #   Moonshot Tier 0   (free):   1.5M tokens/day FREE = ~750 K2.6 calls/day
    #   Moonshot Tier 1   ($10 rc): 50 concurrent / 200 RPM after recharge
    #   OpenRouter        (PAYG):   no platform limits; big coding + overflow
    #   HF Router         ($49/mo): $2 Personal + ~$4-6 Teams = ~$8/mo credits
    #                               + 50 ZeroGPU Spaces (Teams org)
    #   RunPod Community  ($25 dep):~73 hrs RTX 4090 total, scale-to-zero
    local_weight: int = 38
    moonshot_weight: int = 37
    openrouter_weight: int = 15
    hf_weight: int = 8
    runpod_weight: int = 2

    # ── Shared infrastructure ─────────────────────────────────────────────────
    redis_url: str = ""
    database_url: str = ""

    # ── Server ────────────────────────────────────────────────────────────────
    port: int = 8000
    log_level: str = "info"
    local_max_queue: int = 8
    hf_max_queue: int = 8
    request_timeout_secs: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def active_hf_token(self) -> str:
        return self.hf_token or self.hf_token_2 or self.hf_token_3 or ""

    def has_ollama(self) -> bool:
        return True

    def has_moonshot(self) -> bool:
        return bool(self.moonshot_api_key)

    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    def has_hf(self) -> bool:
        return bool(self.active_hf_token())

    def has_runpod(self) -> bool:
        return bool(self.runpod_api_key and self.runpod_reasoner_endpoint_id)

    def has_perplexity(self) -> bool:
        return bool(self.perplexity_api_key)

    def has_exa(self) -> bool:
        return bool(self.exa_api_key)

    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key)

    def has_monitor(self) -> bool:
        return True

    def all_local_models(self) -> list[str]:
        return [
            self.reasoner_model,
            self.tandem_model,
            self.coder_dedicated_model,
            self.kimi_distilled_model,
            self.genstruct_model,
            self.infinity_parser_model,
        ]


settings = Settings()
