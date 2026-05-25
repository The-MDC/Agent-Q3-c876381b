from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Model stack — sourced from MADdegens/Models HF bucket ────────────────
    # GGUFs pulled via `hf buckets cp` → `ollama create` → `ollama push` (cloud)
    # Roles and their Ollama tags (local tag after `ollama create`):
    #
    #   reasoner         nicholasjmcleod/kimi-linear:q6_k        Kimi-Linear-48B (multimodal)        /v1/instruct /v1/chat
    #   tandem           nicholasjmcleod/harmonic-hermes:q6_k    Harmonic-Hermes-9B (refine+monitor) /v1/tandem stage-2 + /v1/monitor
    #   coder            nicholasjmcleod/ultracoder:q4_k_m       Ultra-Coder-Brain (primary coder)   /v1/code /v1/tandem stage-3 + remediation
    #   fallback         nicholasjmcleod/qwopus:q8_0             Qwopus3.6-27B Q8_0 (full-precision) /v1/fallback
    #   coder_dedicated  nicholasjmcleod/qwen3-coder-53b:q6_k   Qwen3-Coder-53B TOTAL-RECALL        /v1/coder
    #   genstruct        nicholasjmcleod/genstruct:q6_k          Genstruct-7B (structure middleware)  /v1/generate + pre/post all
    #   infinity_parser  nicholasjmcleod/infinity-parser:latest  Infinity-Parser2-Pro (parse midw.)  /v1/parse + pre/post all
    #   monitor_pair     harmonic-hermes + ultracoder             Hermes watches / Coder remediates   /v1/monitor/analyze

    reasoner_model:          str = "nicholasjmcleod/kimi-linear:q6_k"
    tandem_model:            str = "nicholasjmcleod/harmonic-hermes:q6_k"
    coder_model:             str = "nicholasjmcleod/ultracoder:q4_k_m"
    fallback_model:          str = "nicholasjmcleod/qwopus:q8_0"
    coder_dedicated_model:   str = "nicholasjmcleod/qwen3-coder-53b:q6_k"
    genstruct_model:         str = "nicholasjmcleod/genstruct:q6_k"
    infinity_parser_model:   str = "nicholasjmcleod/infinity-parser:latest"

    # ── Monitor pair — Harmonic-Hermes (analysis) + Ultra-Coder (remediation) ──
    # Both served from local Ollama. Hermes watches the stack; Coder patches it.
    monitor_model:            str = "nicholasjmcleod/harmonic-hermes:q6_k"
    monitor_coder_model:      str = "nicholasjmcleod/ultracoder:q4_k_m"
    monitor_poll_interval_secs: int = 30
    monitor_targets:          str = "http://multimodal:8000,http://coder:8001,http://research:8002,http://mcp-bridge:8004,http://ollama:11434"

    # ── Ollama endpoint ───────────────────────────────────────────────────────
    ollama_base_url:     str = "http://ollama:11434"
    ollama_api_url:      str = "http://ollama:11434/api"
    openwebui_url:       str = "http://localhost:3000"

    # ── Ollama Cloud auth ─────────────────────────────────────────────────────
    ollama_cloud_enabled: bool = True
    ollama_cloud_account: str  = "nicholasjmcleod@gmail.com"
    ollama_cloud_device:  str  = "LN-8RDGA90Ultra"

    # ── [2] OpenRouter — secondary compute ───────────────────────────────────
    openrouter_api_key:        str = ""
    openrouter_api_url:        str = "https://openrouter.ai/api/v1"
    openrouter_reasoner_model: str = "moonshotai/kimi-k2"
    openrouter_coder_model:    str = "qwen/qwen3-coder-30b-a3b-instruct"
    openrouter_tandem_model:   str = "nousresearch/hermes-3-llama-3.1-8b"
    openrouter_fallback_model: str = "deepseek/deepseek-chat-v3-5"

    # ── [3] HuggingFace Router — tertiary compute ─────────────────────────────
    hf_token:              str = ""
    hf_token_2:            str = ""
    hf_token_3:            str = ""
    hf_router_url:         str = "https://router.huggingface.co/v1"
    hf_reasoner_model:     str = "moonshotai/Kimi-K2-Instruct"
    hf_tandem_model:       str = "NousResearch/Hermes-3-Llama-3.1-8B"
    hf_coder_model:        str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
    hf_frontier_reasoner:  str = "moonshotai/Kimi-K2-Instruct"
    hf_frontier_coder:     str = "Qwen/Qwen3-Coder-30B-A3B-Instruct"

    # ── [4] RunPod Serverless — quaternary GPU burst ──────────────────────────
    runpod_api_key:                str = ""
    runpod_s3_key:                 str = ""
    runpod_reasoner_endpoint_id:   str = "kukl55t0053lob"
    runpod_coder_endpoint_id:      str = "kukl55t0053lob"
    runpod_api_url:                str = "https://api.runpod.ai/v2"
    runpod_gpu_class:              str = "AMPERE_16"

    # ── HF Bucket — model source ──────────────────────────────────────────────
    hf_bucket_repo:    str = "MADdegens/Models"
    hf_bucket_base:    str = "https://huggingface.co/MADdegens/Models/resolve/main"
    model_cache_dir:   str = "/models"

    # ── Search + Research tools ───────────────────────────────────────────────
    perplexity_api_key:        str = ""
    perplexity_default_model:  str = "sonar-pro"
    exa_api_key:               str = ""
    tavily_api_key:            str = ""
    smithery_api_key:          str = ""

    # ── Compute routing ───────────────────────────────────────────────────────
    # cloud_priority = Local Ollama → OpenRouter → HuggingFace → RunPod
    compute_strategy: Literal[
        "cloud_priority",
        "round_robin",
        "load_based",
        "local_first",
        "hf_first",
        "runpod_first",
        "openrouter_first",
    ] = "cloud_priority"

    local_weight:      int = 60
    openrouter_weight: int = 20
    hf_weight:         int = 15
    runpod_weight:     int = 5

    # ── Shared infrastructure ─────────────────────────────────────────────────
    redis_url:    str = ""
    database_url: str = ""

    # ── Server ────────────────────────────────────────────────────────────────
    port:                  int = 8000
    log_level:             str = "info"
    local_max_queue:       int = 8
    hf_max_queue:          int = 8
    request_timeout_secs:  int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def active_hf_token(self) -> str:
        return self.hf_token or self.hf_token_2 or self.hf_token_3 or ""

    def has_ollama(self) -> bool:
        return True  # always available — local or cloud-session

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
        return True  # always available — harmonic-hermes on local Ollama

    def all_local_models(self) -> list[str]:
        return [
            self.reasoner_model,
            self.tandem_model,
            self.coder_model,
            self.fallback_model,
            self.coder_dedicated_model,
            self.genstruct_model,
            self.infinity_parser_model,
        ]


settings = Settings()
