import asyncio
import os
from typing import Any

import psutil
from prometheus_client import Counter, Gauge, Histogram

_process = psutil.Process(os.getpid())

active_sessions = Gauge("hospital_active_sessions", "Currently active voice sessions")
total_sessions = Counter("hospital_total_sessions_total", "Total sessions handled")
stt_latency = Histogram("hospital_stt_latency_seconds", "STT latency", buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
llm_latency = Histogram("hospital_llm_latency_seconds", "LLM latency", buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0])
tts_latency = Histogram("hospital_tts_latency_seconds", "TTS latency", buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0])
llm_input_tokens = Counter("hospital_llm_input_tokens_total", "LLM input tokens", ["provider", "model"])
llm_output_tokens = Counter("hospital_llm_output_tokens_total", "LLM output tokens", ["provider", "model"])
tts_characters = Counter("hospital_tts_characters_total", "TTS characters synthesized", ["provider", "model"])
stt_audio_duration = Counter("hospital_stt_audio_duration_seconds_total", "STT audio duration processed", ["provider", "model"])

process_cpu_percent = Gauge("hospital_process_cpu_percent", "Agent process CPU usage %")
process_memory_percent = Gauge("hospital_process_memory_percent", "Agent process memory usage %")
process_memory_rss_bytes = Gauge("hospital_process_memory_rss_bytes", "Agent process RSS memory bytes")
process_disk_read_bytes = Gauge("hospital_process_disk_read_bytes_total", "Agent process total disk read bytes")
process_disk_write_bytes = Gauge("hospital_process_disk_write_bytes_total", "Agent process total disk write bytes")
process_network_bytes_sent = Gauge("hospital_process_network_bytes_sent_total", "Agent process total network bytes sent")
process_network_bytes_recv = Gauge("hospital_process_network_bytes_recv_total", "Agent process total network bytes received")
process_open_fds = Gauge("hospital_process_open_fds", "Agent process open file descriptors")
process_threads = Gauge("hospital_process_threads", "Agent process thread count")
process_connections = Gauge("hospital_process_connections", "Agent process active network connections")

_cpu_task: asyncio.Task | None = None


def start_cpu_monitoring() -> None:
    global _cpu_task
    if _cpu_task is None:
        _process.cpu_percent()
        _cpu_task = asyncio.create_task(_cpu_loop())


def stop_cpu_monitoring() -> None:
    global _cpu_task
    if _cpu_task:
        _cpu_task.cancel()
        _cpu_task = None


async def _cpu_loop() -> None:
    while True:
        try:
            process_cpu_percent.set(_process.cpu_percent())
            process_memory_percent.set(_process.memory_percent())
            process_memory_rss_bytes.set(_process.memory_info().rss)
            io_counters = _process.io_counters()
            if io_counters:
                process_disk_read_bytes.set(io_counters.read_bytes)
                process_disk_write_bytes.set(io_counters.write_bytes)
            net_counters = psutil.net_io_counters()
            process_network_bytes_sent.set(net_counters.bytes_sent)
            process_network_bytes_recv.set(net_counters.bytes_recv)
            process_open_fds.set(_process.num_fds())
            process_threads.set(_process.num_threads())
            process_connections.set(len(_process.connections()))
        except Exception:
            pass
        await asyncio.sleep(5)


def observe_stt(m: Any) -> None:
    stt_latency.observe(m.duration)
    stt_audio_duration.labels(provider=getattr(m, "provider", "unknown"), model=getattr(m, "model", "unknown")).inc(m.audio_duration)


def observe_llm(m: Any) -> None:
    llm_latency.observe(m.ttft)
    llm_input_tokens.labels(provider=getattr(m, "provider", "unknown"), model=getattr(m, "model", "unknown")).inc(m.prompt_tokens)
    llm_output_tokens.labels(provider=getattr(m, "provider", "unknown"), model=getattr(m, "model", "unknown")).inc(m.completion_tokens)


def observe_tts(m: Any) -> None:
    tts_latency.observe(m.ttfb)
    tts_characters.labels(provider=getattr(m, "provider", "unknown"), model=getattr(m, "model", "unknown")).inc(m.characters_count)
