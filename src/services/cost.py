import logging
from datetime import datetime
from statistics import mean
from typing import Any, Optional

from .session import SessionManager

logger = logging.getLogger(__name__)

_STT_RATE_PER_SECOND = 0.00007167
_LLM_RATE_PER_INPUT_TOKEN = 0.00000015
_LLM_RATE_PER_OUTPUT_TOKEN = 0.00000060
_TTS_RATE_PER_CHARACTER = 0.00000300


class CostCalculator:
    """
    Compute monetary cost from LiveKit model-usage reports.
    Rates are per-unit; override by passing a custom rates dict.
    """

    DEFAULT_RATES = {
        "stt_per_second": _STT_RATE_PER_SECOND,
        "llm_per_input_token": _LLM_RATE_PER_INPUT_TOKEN,
        "llm_per_output_token": _LLM_RATE_PER_OUTPUT_TOKEN,
        "tts_per_character": _TTS_RATE_PER_CHARACTER,
    }

    def __init__(self, rates: Optional[dict[str, float]] = None):
        self.rates = {**self.DEFAULT_RATES, **(rates or {})}

    def compute(self, report: dict[str, Any]) -> dict:
        """
        Accept a LiveKit usage report (list of model_usage dicts) and
        return a cost breakdown keyed by service.
        """
        stt_cost = 0.0
        llm_cost = 0.0
        tts_cost = 0.0
        stt_seconds = 0.0
        llm_input_tokens = 0
        llm_output_tokens = 0
        tts_characters = 0

        for usage in report.get("model_usage", []):
            provider = usage.get("provider", "")
            model = usage.get("model", "")

            if "stt" in model.lower() or "deepgram" in provider.lower() or "sarvam" in provider.lower():
                duration = usage.get("audio_duration", 0)
                stt_seconds += duration
                stt_cost += duration * self.rates["stt_per_second"]

            if "llm" in model.lower() or "sarvam" in provider.lower():
                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                llm_input_tokens += inp
                llm_output_tokens += out
                llm_cost += inp * self.rates["llm_per_input_token"]
                llm_cost += out * self.rates["llm_per_output_token"]

            if "tts" in model.lower() or "cartesia" in provider.lower() or ("sarvam" in provider.lower() and "tts" in model.lower()):
                chars = usage.get("characters_count", 0)
                tts_characters += chars
                tts_cost += chars * self.rates["tts_per_character"]

        total = stt_cost + llm_cost + tts_cost

        return {
            "stt_cost": round(stt_cost, 6),
            "llm_cost": round(llm_cost, 6),
            "tts_cost": round(tts_cost, 6),
            "total_cost": round(total, 6),
            "currency": "USD",
            "stt_seconds": round(stt_seconds, 3),
            "llm_input_tokens": llm_input_tokens,
            "llm_output_tokens": llm_output_tokens,
            "tts_characters": tts_characters,
        }


class EfficiencyTracker:
    """
    Derive agent-efficiency KPIs from session transcripts and
    turn-latency data stored in Redis via SessionManager.
    """

    @staticmethod
    def compute(session_manager: SessionManager) -> dict[str, Any]:
        """
        Read session state from SessionManager's store classes and
        return a snapshot of efficiency metrics.
        """
        transcripts = session_manager.transcripts.get_all() if session_manager.transcripts else []
        latencies = session_manager.metrics.get_latencies() if session_manager.metrics else []
        usage = session_manager.metrics.get_usage() if session_manager.metrics else {}
        call_data = session_manager.call.get() if session_manager.call else {}

        total_turns = len(transcripts)
        user_turns = sum(1 for t in transcripts if t.get("role") == "user")
        assistant_turns = sum(1 for t in transcripts if t.get("role") == "assistant")

        # Latency breakdown
        stt_latencies = [l.get("stt_duration_ms", 0) for l in latencies if "stt_duration_ms" in l]
        llm_latencies = [l.get("llm_ttft_ms", 0) for l in latencies if "llm_ttft_ms" in l]
        tts_latencies = [l.get("tts_duration_ms", 0) for l in latencies if "tts_duration_ms" in l]

        per_turn_ms = []
        for l in latencies:
            turn_ms = l.get("stt_duration_ms", 0) + l.get("llm_ttft_ms", 0) + l.get("tts_duration_ms", 0)
            per_turn_ms.append(turn_ms)

        # Session duration
        session_duration_s = 0.0
        if call_data.get("started_at") and transcripts:
            try:
                started = datetime.fromisoformat(call_data["started_at"])
                last_ts = datetime.fromisoformat(transcripts[-1].get("timestamp", started.isoformat()))
                session_duration_s = (last_ts - started).total_seconds()
            except (ValueError, TypeError):
                pass

        # Token efficiency (from accumulated usage)
        total_input = 0
        total_output = 0
        for model_key, model_data in usage.get("model_usage", {}).items():
            total_input += model_data.get("input_tokens", 0)
            total_output += model_data.get("output_tokens", 0)

        result: dict[str, Any] = {
            "total_turns": total_turns,
            "user_turns": user_turns,
            "assistant_turns": assistant_turns,
            "session_duration_seconds": round(session_duration_s, 2),
            "turns_per_minute": round(total_turns / (session_duration_s / 60), 2) if session_duration_s > 0 else 0,
            "latency_ms": {
                "avg_stt": round(mean(stt_latencies), 2) if stt_latencies else 0,
                "avg_llm_ttft": round(mean(llm_latencies), 2) if llm_latencies else 0,
                "avg_tts": round(mean(tts_latencies), 2) if tts_latencies else 0,
                "avg_per_turn": round(mean(per_turn_ms), 2) if per_turn_ms else 0,
            },
            "tokens": {
                "total_input": total_input,
                "total_output": total_output,
                "avg_input_per_turn": round(total_input / total_turns, 1) if total_turns else 0,
                "avg_output_per_turn": round(total_output / total_turns, 1) if total_turns else 0,
            },
        }
        return result


class CostManager:
    """
    Top-level coordinator: compute cost + efficiency from a usage
    report and persist everything through SessionManager.
    """

    def __init__(self, rates: Optional[dict[str, float]] = None):
        self.calculator = CostCalculator(rates)
        self.efficiency = EfficiencyTracker()

    def process_report(
        self,
        session_manager: SessionManager,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        High-level entry point.
        1. Compute monetary cost from the usage report.
        2. Compute efficiency KPIs from stored session data.
        3. Persist cost through the session manager.
        4. Return a combined cost + efficiency result.
        """
        cost_data = self.calculator.compute(report)
        efficiency_data = self.efficiency.compute(session_manager)

        try:
            session_manager.save_metrics_cost(
                stt_cost=cost_data["stt_cost"],
                tts_cost=cost_data["tts_cost"],
                llm_cost=cost_data["llm_cost"],
                total_cost=cost_data["total_cost"],
            )
            logger.info(
                "Cost saved for %s: $%.4f (STT: $%.4f, LLM: $%.4f, TTS: $%.4f)",
                session_manager.session_id,
                cost_data["total_cost"],
                cost_data["stt_cost"],
                cost_data["llm_cost"],
                cost_data["tts_cost"],
            )
        except Exception as e:
            logger.error("Failed to persist cost for %s: %s", session_manager.session_id, e)

        return {
            "session_id": session_manager.session_id,
            "cost": cost_data,
            "efficiency": efficiency_data,
        }
