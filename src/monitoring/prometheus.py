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

process_cpu_percent = Gauge("hospital_process_cpu_percent", "Agent process CPU usage %")
process_memory_percent = Gauge("hospital_process_memory_percent", "Agent process memory usage %")
process_memory_rss_bytes = Gauge("hospital_process_memory_rss_bytes", "Agent process RSS memory bytes")

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
        except Exception:
            pass
        await asyncio.sleep(5)


def observe_stt(m: Any) -> None:
    stt_latency.observe(m.duration)


def observe_llm(m: Any) -> None:
    llm_latency.observe(m.ttft)


def observe_tts(m: Any) -> None:
    tts_latency.observe(m.ttfb)
