import logging
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv

from .database import RedisServices

load_dotenv()
logger = logging.getLogger(__name__)

COST_TTL = 86400
SESSION_TTL = 720000


class CallLogs:
    """Stores and retrieves initial call metadata in Redis."""

    def __init__(self, redis: RedisServices, session_id: str):
        self._redis = redis
        self._session_id = session_id

    def _key(self) -> str:
        return f"call:{self._session_id}"

    def save(self, data: dict) -> None:
        self._redis.set_json(self._key(), data, ttl=SESSION_TTL)

    def get(self) -> Optional[dict]:
        return self._redis.get_json(self._key())

    def delete(self) -> None:
        self._redis.delete(self._key())


class TranscriptsLogs:
    """Stores and retrieves conversation transcript messages in Redis."""

    def __init__(self, redis: RedisServices, session_id: str):
        self._redis = redis
        self._session_id = session_id

    def _key(self) -> str:
        return f"transcripts:{self._session_id}"

    def append(self, entry: dict) -> None:
        self._redis.append_to_array(
            self._key(), "messages", entry, ttl=SESSION_TTL
        )

    def get_all(self) -> list:
        data = self._redis.get_json(self._key())
        return data.get("messages", []) if data else []

    def count(self) -> int:
        return len(self.get_all())

    def delete(self) -> None:
        self._redis.delete(self._key())


class MetricsLogs:
    """Stores and retrieves usage, latency, and cost data in Redis."""

    def __init__(self, redis: RedisServices, session_id: str):
        self._redis = redis
        self._session_id = session_id

    def _usage_key(self) -> str:
        return f"metrics:usage:{self._session_id}"

    def _latency_key(self) -> str:
        return f"metrics:latency:{self._session_id}"

    def _cost_key(self) -> str:
        return f"cost:{self._session_id}"

    def save_usage(self, data: dict) -> None:
        self._redis.set_json(self._usage_key(), data, ttl=SESSION_TTL)

    def get_usage(self) -> Optional[dict]:
        return self._redis.get_json(self._usage_key())

    def append_latency(self, entry: dict) -> None:
        self._redis.append_to_array(
            self._latency_key(), "latencies", entry, ttl=SESSION_TTL
        )

    def get_latencies(self) -> list:
        data = self._redis.get_json(self._latency_key())
        return data.get("latencies", []) if data else []

    def save_cost(self, data: dict) -> None:
        self._redis.set_json(self._cost_key(), data, ttl=COST_TTL)

    def get_cost(self) -> Optional[dict]:
        return self._redis.get_json(self._cost_key())

    def delete_all(self) -> None:
        self._redis.delete(self._usage_key())
        self._redis.delete(self._latency_key())
        self._redis.delete(self._cost_key())


class SessionManager:
    """
    Orchestrates session lifecycle — delegates actual Redis I/O to
    CallLogs, TranscriptsLogs, and MetricsLogs.
    """

    def __init__(self):
        self._redis = RedisServices()
        self.session_id: Optional[str] = None
        self._phone_number: Optional[str] = None
        self._language: str = "en"

        # Data-store sub-components (lazy-initialised in start())
        self.call: Optional[CallLogs] = None
        self.transcripts: Optional[TranscriptsLogs] = None
        self.metrics: Optional[MetricsLogs] = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start(self, session_id: str, participant_context: dict):
        """
        Initialise a new session: wire up stores, persist call metadata,
        and record the start time.
        """
        self.session_id = session_id
        self._phone_number = participant_context.get("identity")
        self._language = participant_context.get("language", "en")

        self.call = CallLogs(self._redis, session_id)
        self.transcripts = TranscriptsLogs(self._redis, session_id)
        self.metrics = MetricsLogs(self._redis, session_id)

        call_data = {
            "session_id": session_id,
            "identity": self._phone_number,
            "language": self._language,
            "started_at": datetime.now().isoformat(),
            "participant_context": participant_context,
        }
        self.call.save(call_data)
        logger.info("Session %s started", session_id)

    def end_session(self, duration_seconds: float = 0.0):
        """
        Tear down the session: log final stats, then delete all
        session data from Redis.
        """
        if not self._check_active():
            return

        msg_count = self.transcripts.count()
        logger.info(
            "Session %s ended. %s messages. Duration: %.1fs.",
            self.session_id, msg_count, duration_seconds,
        )

        self.call.delete()
        self.transcripts.delete()
        self.metrics.delete_all()

        self.session_id = None
        self.call = None
        self.transcripts = None
        self.metrics = None

    # ------------------------------------------------------------------
    # Conversation transcripts
    # ------------------------------------------------------------------

    def session_log(self, log_entry: dict):
        """
        Append a single turn (user / assistant) to the conversation
        transcript.  Adds an ISO-8601 timestamp if none is present.
        """
        if not self._check_active():
            return
        if "timestamp" not in log_entry:
            log_entry["timestamp"] = datetime.now().isoformat()
        self.transcripts.append(log_entry)

    def get_session_logs(self) -> list:
        """Return the full conversation transcript as a list of turns."""
        if not self._check_active():
            return []
        return self.transcripts.get_all()

    # ------------------------------------------------------------------
    # Model usage tracking
    # ------------------------------------------------------------------

    def update_usage(self, usage_data: dict):
        """
        Accumulate model-usage metrics (tokens, audio duration,
        characters, request count) by provider/model pair.
        Each call merges into the previously stored snapshot.
        """
        if not self._check_active():
            return
        current = self.metrics.get_usage() or {}
        accumulated = current.get("model_usage", {})

        for mu in usage_data.get("model_usage", []):
            provider = mu.get("provider", "unknown")
            model = mu.get("model", "unknown")
            acc = accumulated.setdefault(f"{provider}/{model}", {})
            for field in ("input_tokens", "output_tokens", "audio_duration",
                          "characters_count", "total_requests"):
                val = mu.get(field, 0)
                acc[field] = acc.get(field, 0) + val

        current["model_usage"] = accumulated
        self.metrics.save_usage(current)

    # ------------------------------------------------------------------
    # Turn latency tracking
    # ------------------------------------------------------------------

    def update_turn_latency(self, role: str, metrics: dict):
        """
        Record a single turn's processing latency (e.g. STT duration,
        LLM TTFT, TTS duration) together with the speaker role.
        """
        if not self._check_active():
            return
        entry = {"role": role, "timestamp": datetime.now().isoformat(), **metrics}
        self.metrics.append_latency(entry)

    # ------------------------------------------------------------------
    # Cost persistence
    # ------------------------------------------------------------------

    def save_metrics_cost(
        self,
        stt_cost: float = 0.0,
        tts_cost: float = 0.0,
        llm_cost: float = 0.0,
        sip_cost: float = 0.0,
        total_cost: float = 0.0,
    ):
        """
        Persist the computed cost breakdown for the session so it
        outlives the shorter-lived transcript / usage keys.
        """
        if not self._check_active():
            return
        cost_data = {
            "stt_cost": stt_cost,
            "tts_cost": tts_cost,
            "llm_cost": llm_cost,
            "sip_cost": sip_cost,
            "total_cost": total_cost,
            "timestamp": datetime.now().isoformat(),
        }
        self.metrics.save_cost(cost_data)
        logger.info("Cost saved for %s: $%.4f", self.session_id, total_cost)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_active(self) -> bool:
        """Guard: log a warning if no session has been started."""
        if not self.session_id:
            logger.error("No active session. Call start() first.")
            return False
        return True
