import logging
from typing import Any

from src.services.session_db import insert_session_cost

logger = logging.getLogger(__name__)

_STT_RATE_PER_SECOND = 0.00007167
_LLM_RATE_PER_INPUT_TOKEN = 0.00000015
_LLM_RATE_PER_OUTPUT_TOKEN = 0.00000060
_TTS_RATE_PER_CHARACTER = 0.00000300


def compute_cost(report: dict[str, Any]) -> dict:
    stt_cost = 0.0
    llm_cost = 0.0
    tts_cost = 0.0
    stt_seconds = 0.0
    llm_tokens = 0
    tts_characters = 0

    for usage in report.get("model_usage", []):
        provider = usage.get("provider", "")
        model = usage.get("model", "")

        if "stt" in model.lower() or "deepgram" in provider.lower() or "sarvam" in provider.lower():
            audio_duration = usage.get("audio_duration", 0)
            stt_seconds += audio_duration
            stt_cost += audio_duration * _STT_RATE_PER_SECOND

        if "llm" in model.lower() or "sarvam" in provider.lower():
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            llm_tokens += input_tokens + output_tokens
            llm_cost += input_tokens * _LLM_RATE_PER_INPUT_TOKEN
            llm_cost += output_tokens * _LLM_RATE_PER_OUTPUT_TOKEN

        if "tts" in model.lower() or "cartesia" in provider.lower() or ("sarvam" in provider.lower() and "tts" in model.lower()):
            chars = usage.get("characters_count", 0)
            tts_characters += chars
            tts_cost += chars * _TTS_RATE_PER_CHARACTER

    return {
        "stt_cost": round(stt_cost, 6),
        "llm_cost": round(llm_cost, 6),
        "tts_cost": round(tts_cost, 6),
        "total_cost": round(stt_cost + llm_cost + tts_cost, 6),
        "currency": "USD",
        "stt_seconds": round(stt_seconds, 3),
        "llm_tokens": llm_tokens,
        "tts_characters": tts_characters,
    }


async def persist_cost(session_id: str, report: dict[str, Any]) -> None:
    cost_data = compute_cost(report)
    cost_data["session_id"] = session_id
    try:
        await insert_session_cost(cost_data)
        logger.info(
            "Cost saved for session %s: $%.4f (STT: $%.4f, LLM: $%.4f, TTS: $%.4f)",
            session_id,
            cost_data["total_cost"],
            cost_data["stt_cost"],
            cost_data["llm_cost"],
            cost_data["tts_cost"],
        )
    except Exception as e:
        logger.error("Failed to persist cost for session %s: %s", session_id, e)
