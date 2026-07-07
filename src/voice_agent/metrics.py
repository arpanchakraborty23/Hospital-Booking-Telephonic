from collections import defaultdict
from datetime import datetime
from typing import Any


class MetricsCollector:
    def __init__(self):
        self.session_usage: dict[str, dict] = defaultdict(dict)
        self.turn_latency_history: list[dict] = []

    def update_session_usage(self, ev: Any) -> None:
        for usage in ev.usage.model_usage:
            provider_model = f"{usage.provider}/{usage.model}"
            self.session_usage[provider_model] = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens,
                "session_duration": usage.session_duration,
            }

    def add_turn_latency(self, role: str, metrics: dict) -> None:
        latency_entry = {
            "role": role,
            "timestamp": datetime.now().isoformat(),
        }
        if role == "user":
            latency_entry["transcription_delay"] = metrics.get("transcription_delay")
            latency_entry["end_of_turn_delay"] = metrics.get("end_of_turn_delay")
        elif role == "assistant":
            latency_entry["llm_node_ttft"] = metrics.get("llm_node_ttft")
            latency_entry["tts_node_ttfb"] = metrics.get("tts_node_ttfb")
            latency_entry["e2e_latency"] = metrics.get("e2e_latency")
        self.turn_latency_history.append(latency_entry)
