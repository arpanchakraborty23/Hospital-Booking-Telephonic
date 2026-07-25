import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.session import SessionManager

logger = logging.getLogger(__name__)

STT_RATE_PER_SEC = 0.0043 / 60
LLM_RATE_PER_TOKEN = 0.001 / 1000
TTS_RATE_PER_CHAR = 0.0001
SIP_RATE_PER_SEC = 0.001 / 60


def compute_cost(usage: dict) -> dict:
    model_usage = usage.get("model_usage", {})

    total_stt_duration = 0.0
    total_tts_chars = 0.0
    total_llm_tokens = 0
    total_session_duration = 0.0

    for key, mu in model_usage.items():
        provider = key.split("/")[0].lower() if "/" in key else ""

        audio_duration = mu.get("audio_duration", 0) or 0
        characters_count = mu.get("characters_count", 0) or 0
        input_tokens = mu.get("input_tokens", 0) or 0
        output_tokens = mu.get("output_tokens", 0) or 0

        if "deepgram" in provider:
            total_stt_duration += audio_duration
        if "cartesia" in provider:
            total_tts_chars += characters_count
        if "sarvam" in provider:
            total_llm_tokens += input_tokens + output_tokens

        total_session_duration += audio_duration

    stt_cost = total_stt_duration * STT_RATE_PER_SEC
    tts_cost = total_tts_chars * TTS_RATE_PER_CHAR
    llm_cost = total_llm_tokens * LLM_RATE_PER_TOKEN
    sip_cost = total_session_duration * SIP_RATE_PER_SEC
    total_cost = stt_cost + tts_cost + llm_cost + sip_cost

    return {
        "stt_cost": round(stt_cost, 6),
        "tts_cost": round(tts_cost, 6),
        "llm_cost": round(llm_cost, 6),
        "sip_cost": round(sip_cost, 6),
        "total_cost": round(total_cost, 6),
    }


async def persist_cost(session_manager: "SessionManager", report: dict) -> None:
    usage = session_manager.metrics.get_usage() if session_manager.metrics else None
    if usage is None:
        usage = {}
    cost = compute_cost(usage)
    session_manager.save_metrics_cost(**cost)
    logger.info("Cost computed for %s: $%.4f", session_manager.session_id, cost["total_cost"])
