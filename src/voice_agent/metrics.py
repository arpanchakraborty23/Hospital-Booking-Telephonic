from collections import defaultdict
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from rich.panel import Panel

console = Console()


class MetricsCollector:
    # Aggregates per-turn, per-session, and end-of-call metrics for display and Prometheus
    def __init__(self):
        self.turn_metrics: dict[str, dict[str, float]] = defaultdict(dict)
        self.vad_metrics_list: list[dict] = []
        self.stt_metrics_list: list[dict] = []
        self.interruption_metrics_list: list[dict] = []
        self.session_usage: dict[str, dict] = defaultdict(dict)
        self.turn_latency_history: list[dict] = []

    def collect_stt(self, m: Any) -> None:  # Store STT latency and audio duration
        self.stt_metrics_list.append({
            "audio_duration": m.audio_duration,
            "duration": m.duration,
            "streamed": m.streamed,
            "timestamp": datetime.now().isoformat()
        })

    def collect_vad(self, m: Any) -> None:  # Record VAD idle time and inference stats
        self.vad_metrics_list.append({
            "idle_time": m.idle_time,
            "inference_duration_total": m.inference_duration_total,
            "inference_count": m.inference_count,
            "timestamp": datetime.now().isoformat()
        })

    def collect_eou(self, m: Any) -> None:  # Track end-of-utterance delay per speech segment
        sid = getattr(m, "speech_id", None)
        if sid:
            self.turn_metrics[sid]["eou_delay"] = m.end_of_utterance_delay
            self.turn_metrics[sid]["transcription_delay"] = m.transcription_delay
            self.turn_metrics[sid]["on_user_turn_completed_delay"] = m.on_user_turn_completed_delay

    def collect_llm(self, m: Any) -> None:  # Capture LLM TTFT, tokens, tokens/sec per turn
        sid = getattr(m, "speech_id", None)
        if sid:
            self.turn_metrics[sid]["llm_ttft"] = m.ttft
            self.turn_metrics[sid]["llm_duration"] = m.duration
            self.turn_metrics[sid]["llm_completion_tokens"] = m.completion_tokens
            self.turn_metrics[sid]["llm_prompt_tokens"] = m.prompt_tokens
            self.turn_metrics[sid]["llm_total_tokens"] = m.total_tokens
            self.turn_metrics[sid]["llm_tokens_per_second"] = m.tokens_per_second

    def collect_tts(self, m: Any) -> None:  # Store TTS TTFB, audio duration, character count per turn
        sid = getattr(m, "speech_id", None)
        if sid:
            self.turn_metrics[sid]["tts_ttfb"] = m.ttfb
            self.turn_metrics[sid]["tts_duration"] = m.duration
            self.turn_metrics[sid]["tts_audio_duration"] = m.audio_duration
            self.turn_metrics[sid]["tts_characters_count"] = m.characters_count

    def collect_interruption(self, m: Any) -> None:  # Log interruption events (user barge-in)
        self.interruption_metrics_list.append({
            "total_duration": m.total_duration,
            "prediction_duration": m.prediction_duration,
            "detection_delay": m.detection_delay,
            "num_interruptions": m.num_interruptions,
            "num_backchannels": m.num_backchannels,
            "num_requests": m.num_requests,
            "timestamp": datetime.now().isoformat()
        })

    def update_session_usage(self, ev: Any) -> None:  # Aggregate LLM token usage from SessionUsageUpdatedEvent
        for usage in ev.usage.model_usage:
            provider_model = f"{usage.provider}/{usage.model}"
            self.session_usage[provider_model] = {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.input_tokens + usage.output_tokens,
                "session_duration": usage.session_duration,
            }

    def add_turn_latency(self, role: str, metrics: dict) -> None:  # Per-turn E2E latency from conversation item metrics
        latency_entry = {
            "role": role,
            "timestamp": datetime.now().isoformat(),
        }
        if role == "user":
            latency_entry["transcription_delay"] = metrics.get("transcription_delay")
            latency_entry["end_of_turn_delay"] = metrics.get("end_of_turn_delay")
            latency_entry["on_user_turn_completed_delay"] = metrics.get("on_user_turn_completed_delay")
        elif role == "assistant":
            latency_entry["llm_node_ttft"] = metrics.get("llm_node_ttft")
            latency_entry["tts_node_ttfb"] = metrics.get("tts_node_ttfb")
            latency_entry["e2e_latency"] = metrics.get("e2e_latency")
        self.turn_latency_history.append(latency_entry)

    def display_summary(self) -> None:  # Rich console output of all collected metrics
        console.print(Panel("[bold cyan]Session Metrics Summary[/bold cyan]", box=ROUNDED))
        
        self._display_turn_metrics()
        self._display_session_usage()
        self._display_vad_metrics()
        self._display_stt_metrics()
        self._display_interruption_metrics()
        self._display_turn_latency()

    def _display_turn_metrics(self) -> None:
        if not self.turn_metrics:
            return
        table = Table(title="Per-Turn Latency Metrics", box=ROUNDED)
        table.add_column("Speech ID", style="cyan")
        table.add_column("EOU Delay (s)", style="yellow")
        table.add_column("LLM TTFT (s)", style="green")
        table.add_column("TTS TTFB (s)", style="magenta")
        table.add_column("Total (s)", style="bold")
        
        for sid, parts in self.turn_metrics.items():
            total = sum(parts.values())
            table.add_row(
                sid[:8] + "..." if len(sid) > 8 else sid,
                f"{parts.get('eou_delay', 0):.3f}",
                f"{parts.get('llm_ttft', 0):.3f}",
                f"{parts.get('tts_ttfb', 0):.3f}",
                f"{total:.3f}"
            )
        console.print(table)

    def _display_session_usage(self) -> None:
        if not self.session_usage:
            return
        table = Table(title="Session Usage (Token Counts)", box=ROUNDED)
        table.add_column("Provider/Model", style="cyan")
        table.add_column("Input Tokens", style="yellow")
        table.add_column("Output Tokens", style="green")
        table.add_column("Total Tokens", style="magenta")
        table.add_column("Duration (s)", style="bold")
        
        for provider_model, usage in self.session_usage.items():
            table.add_row(
                provider_model,
                str(usage.get("input_tokens", 0)),
                str(usage.get("output_tokens", 0)),
                str(usage.get("total_tokens", 0)),
                f"{usage.get('session_duration', 0):.2f}"
            )
        console.print(table)

    def _display_vad_metrics(self) -> None:
        if not self.vad_metrics_list:
            return
        latest = self.vad_metrics_list[-1]
        table = Table(title="VAD Metrics (Latest)", box=ROUNDED)
        table.add_column("Idle Time (s)", style="yellow")
        table.add_column("Inference Duration (s)", style="green")
        table.add_column("Inference Count", style="cyan")
        table.add_row(
            f"{latest.get('idle_time', 0):.3f}",
            f"{latest.get('inference_duration_total', 0):.3f}",
            str(latest.get('inference_count', 0))
        )
        console.print(table)

    def _display_stt_metrics(self) -> None:
        if not self.stt_metrics_list:
            return
        latest = self.stt_metrics_list[-1]
        table = Table(title="STT Metrics (Latest)", box=ROUNDED)
        table.add_column("Audio Duration (s)", style="yellow")
        table.add_column("Duration (s)", style="green")
        table.add_column("Streamed", style="cyan")
        table.add_row(
            f"{latest.get('audio_duration', 0):.3f}",
            f"{latest.get('duration', 0):.3f}",
            str(latest.get('streamed', False))
        )
        console.print(table)

    def _display_interruption_metrics(self) -> None:
        if not self.interruption_metrics_list:
            return
        table = Table(title="Interruption Metrics", box=ROUNDED)
        table.add_column("Total (s)", style="yellow")
        table.add_column("Prediction (s)", style="green")
        table.add_column("Delay (s)", style="cyan")
        table.add_column("Interruptions", style="red")
        table.add_column("Backchannels", style="magenta")
        
        for intr in self.interruption_metrics_list:
            table.add_row(
                f"{intr.get('total_duration', 0):.3f}",
                f"{intr.get('prediction_duration', 0):.3f}",
                f"{intr.get('detection_delay', 0):.3f}",
                str(intr.get('num_interruptions', 0)),
                str(intr.get('num_backchannels', 0))
            )
        console.print(table)

    def _display_turn_latency(self) -> None:
        if not self.turn_latency_history:
            return
        table = Table(title="Per-Turn Latency (ChatMessage.metrics)", box=ROUNDED)
        table.add_column("Role", style="cyan")
        table.add_column("E2E Latency (s)", style="yellow")
        table.add_column("LLM TTFT (s)", style="green")
        table.add_column("TTS TTFB (s)", style="magenta")
        
        for entry in self.turn_latency_history:
            if entry["role"] == "assistant":
                table.add_row(
                    "assistant",
                    f"{entry.get('e2e_latency', 0):.3f}" if entry.get('e2e_latency') else "N/A",
                    f"{entry.get('llm_node_ttft', 0):.3f}" if entry.get('llm_node_ttft') else "N/A",
                    f"{entry.get('tts_node_ttfb', 0):.3f}" if entry.get('tts_node_ttfb') else "N/A",
                )
        console.print(table)