import logging
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from .database import RedisServices, SQLModelServices
from src.constants.config import DataBaseCOnfig
from src.constants.models import call_logs as CallLogModel
from src.constants.models import cost as CostModel
from src.constants.models import Metrics as MetricsModel
from src.constants.models import transcriptions as TranscriptionModel

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
    CallLogs, TranscriptsLogs, and MetricsLogs.  At session end, all
    data is persisted to PostgreSQL via SQLModelServices.
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

    async def end_session(self, duration_seconds: float = 0.0):
        """
        Tear down the session:

        1. Read transcript, usage, latency, and cost from Redis.
        2. Generate a summary (eval) from the transcript.
        3. Store transcript in DB (transcriptions table).
        4. Store call log with summary in DB (call_logs table).
        5. Store metrics in DB (Metrics table).
        6. Store cost in DB (cost table).
        7. Clean up all session data from Redis.
        """
        if not self._check_active():
            return

        messages = []
        call_data = {}
        usage = {}
        latencies = []
        cost_data = {}

        try:
            # ---- 1. Gather data from Redis ----
            messages = self.transcripts.get_all()
            call_data = self.call.get() or {}
            usage = self.metrics.get_usage() or {}
            latencies = self.metrics.get_latencies()
            cost_data = self.metrics.get_cost() or {}

            # Compute timing
            started_at_str = call_data.get("started_at")
            start_time = (
                datetime.fromisoformat(started_at_str) if started_at_str else datetime.now()
            )
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # ---- 2. Eval / summarise using transcript ----
            summary = self._generate_summary(messages)

            # ---- 3. Store transcript in DB ----
            _trans_svc = SQLModelServices(
                DataBaseCOnfig.sql_database_url, TranscriptionModel
            )
            _trans_svc.create(
                session_id=self.session_id,
                phone_number=self._phone_number or "",
                transcription_text={"messages": messages},
                count=len(messages),
                language=self._language,
                summary=summary,
            )

            # ---- 4. Call logs with summary ----
            _call_svc = SQLModelServices(
                DataBaseCOnfig.sql_database_url, CallLogModel
            )
            _call_svc.create(
                session_id=self.session_id,
                phone_number=self._phone_number or "",
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            )

            # ---- 5. Metrics in DB ----
            stt_metric: dict = {}
            tts_metric: dict = {}
            llm_metric: dict = {}
            prompt_tokens = 0
            completion_tokens = 0

            model_usage = usage.get("model_usage", {})
            for key, mu in model_usage.items():
                provider = key.split("/")[0].lower() if "/" in key else ""
                if "deepgram" in provider:
                    stt_metric[key] = mu
                elif "cartesia" in provider:
                    tts_metric[key] = mu
                elif "sarvam" in provider:
                    llm_metric[key] = mu
                    prompt_tokens += mu.get("input_tokens", 0) or 0
                    completion_tokens += mu.get("output_tokens", 0) or 0

            avg_latency = 0
            if latencies:
                total = sum(
                    (l.get("e2e_latency") or l.get("transcription_delay") or 0)
                    for l in latencies
                )
                avg_latency = int(total / len(latencies))

            _metrics_svc = SQLModelServices(
                DataBaseCOnfig.sql_database_url, MetricsModel
            )
            _metrics_svc.create(
                session_id=self.session_id,
                stt_metric=stt_metric,
                tts_metric=tts_metric,
                llm_metric=llm_metric,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                average_latency=avg_latency,
            )

            # ---- 6. Cost in DB ----
            if cost_data:
                _cost_svc = SQLModelServices(
                    DataBaseCOnfig.sql_database_url, CostModel
                )
                _cost_svc.create(
                    session_id=self.session_id,
                    phone_number=self._phone_number or "",
                    stt_cost=cost_data.get("stt_cost", 0.0),
                    tts_cost=cost_data.get("tts_cost", 0.0),
                    llm_cost=cost_data.get("llm_cost", 0.0),
                    sip_cost=cost_data.get("sip_cost", 0.0),
                    total_cost=cost_data.get("total_cost", 0.0),
                )

            logger.info(
                "Session %s ended. %d messages. Duration: %.1fs. "
                "Transcript, call log, metrics, and cost stored in DB.",
                self.session_id,
                len(messages),
                duration,
            )
        except Exception as e:
            logger.error("Error during DB persistence in end_session: %s", e)
        finally:
            # ---- 7. Clean up Redis regardless ----
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

    def _generate_summary(self, messages: list) -> str:
        """Generate a concise summary (eval) from the conversation transcript."""
        if not messages:
            return "No conversation recorded."

        user_count = sum(1 for m in messages if m.get("role") == "user")
        agent_count = sum(1 for m in messages if m.get("role") == "agent")

        topics = []
        for m in messages:
            msg = str(m.get("message", "")).lower()
            if "appointment" in msg or "booking" in msg:
                topics.append("appointment booking")
            elif "reschedule" in msg:
                topics.append("rescheduling")
            elif "cancel" in msg:
                topics.append("cancellation")
            elif "doctor" in msg or "department" in msg:
                topics.append("directory inquiry")

        summary = (
            f"Call with {self._phone_number}. "
            f"{len(messages)} messages ({user_count} user, {agent_count} agent). "
        )
        if topics:
            unique_topics = list(dict.fromkeys(topics))
            summary += f"Topics: {', '.join(unique_topics)}."
        else:
            summary += "General inquiry."

        return summary

    def _check_active(self) -> bool:
        """Guard: log a warning if no session has been started."""
        if not self.session_id:
            logger.error("No active session. Call start() first.")
            return False
        return True
