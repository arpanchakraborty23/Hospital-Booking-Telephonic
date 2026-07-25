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

# E2E latency per turn
e2e_latency = Histogram("hospital_e2e_latency_seconds", "End-to-end turn latency", buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0])

# Session duration
session_duration = Histogram("hospital_session_duration_seconds", "Session duration", buckets=[30, 60, 120, 300, 600, 1800])

# Session language
session_language = Counter("hospital_session_language_total", "Sessions by language", ["language"])

# Intent classification
intent_classification = Counter("hospital_intent_total", "Intent classifications", ["intent"])

# Tool call tracking
tool_calls = Counter("hospital_tool_calls_total", "Tool calls", ["tool_name", "status"])
tool_latency = Histogram("hospital_tool_latency_seconds", "Tool call latency", ["tool_name"], buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0])

# Error tracking
errors_total = Counter("hospital_errors_total", "Errors by category", ["type"])

# Cost tracking
cost_total = Counter("hospital_cost_total", "Cumulative cost", ["type"])

# DB query tracking
db_queries = Counter("hospital_db_queries_total", "DB queries by operation and table", ["operation", "table"])
db_query_latency = Histogram("hospital_db_query_latency_seconds", "DB query latency", ["operation"], buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0])

# Redis tracking
redis_operations = Counter("hospital_redis_operations_total", "Redis operations", ["operation"])
redis_latency = Histogram("hospital_redis_latency_seconds", "Redis operation latency", ["operation"], buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25])

# Evaluation scores (1-10 range)
eval_score = Gauge("hospital_eval_score", "Latest evaluation score by metric", ["metric"])
eval_total = Counter("hospital_eval_total", "Total evaluations processed")

# SIP call tracking
sip_calls = Counter("hospital_sip_calls_total", "SIP calls", ["status"])
returning_callers = Gauge("hospital_returning_callers", "Number of returning callers")

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


def observe_tool_call(tool_name: str, latency: float, status: str = "success") -> None:
    tool_calls.labels(tool_name=tool_name, status=status).inc()
    tool_latency.labels(tool_name=tool_name).observe(latency)


def observe_intent(intent: str | None) -> None:
    intent_classification.labels(intent=intent or "unknown").inc()


def observe_error(error_type: str) -> None:
    errors_total.labels(type=error_type).inc()


def observe_db(operation: str, table: str, latency: float) -> None:
    db_queries.labels(operation=operation, table=table).inc()
    db_query_latency.labels(operation=operation).observe(latency)


def observe_redis(operation: str, latency: float) -> None:
    redis_operations.labels(operation=operation).inc()
    redis_latency.labels(operation=operation).observe(latency)


def observe_eval(metric: str, value: float) -> None:
    eval_total.inc()
    eval_score.labels(metric=metric).set(value)


def observe_session_language(language: str) -> None:
    session_language.labels(language=language).inc()


def observe_sip_call(status: str) -> None:
    sip_calls.labels(status=status).inc()


def observe_cost(cost_type: str, amount: float) -> None:
    cost_total.labels(type=cost_type).inc(amount)


def observe_session_duration(seconds: float) -> None:
    session_duration.observe(seconds)
