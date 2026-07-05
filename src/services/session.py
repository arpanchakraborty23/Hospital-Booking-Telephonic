import logging
from datetime import datetime

from dotenv import load_dotenv

from src.services.database import NeonServices
from src.services.session_db import insert_session_history
from src.services.redis_client import RedisClient

load_dotenv()

SESSION_TTL = 7200  # 2 hours in seconds


class SessionManager:
    # Manages one session lifecycle: Redis for real-time, Neon for persistence at end
    def __init__(self):
        self.db = NeonServices()
        self.session_id = None
        self.logger = logging.getLogger(__name__)
        self._db_initialized = False
        self._redis = RedisClient()

    async def _ensure_db_connected(self) -> None:
        if not self._db_initialized:
            try:
                await self.db.connect()
                self._db_initialized = True
            except Exception as e:
                self.logger.error(f"Failed to connect to Neon: {e}")
                self.logger.warning("Continuing without Neon - session data will not be persisted")

    def _redis_key(self, session_id: str) -> str:  # Redis key format: session:<room_name>
        return f"session:{session_id}"

    async def start(self, session_id: str, participant_context: dict) -> None:  # Init Redis blob with empty history + participant data
        try:
            self.session_id = session_id
            await self._ensure_db_connected()

            redis_data = {
                "session_id": session_id,
                "conversation_history": [],
                "participant_context": participant_context,
            }
            self._redis.set_json(self._redis_key(session_id), redis_data, ttl=SESSION_TTL)
            self.logger.info(f"Session {session_id} initialized in Redis with {SESSION_TTL}s TTL.")

        except Exception as e:
            self.logger.error(f"Failed to start session {session_id}: {e}")
            raise

    def session_log(self, log_entry: dict) -> None:  # Append a turn (user or agent) to Redis conversation_history
        if not self.session_id:
            self.logger.error("No active session. Call start() first.")
            return
        try:
            if "timestamp" not in log_entry:
                log_entry["timestamp"] = datetime.now().isoformat()
            self._redis.append_to_array(
                self._redis_key(self.session_id),
                "conversation_history",
                log_entry,
                ttl=SESSION_TTL,
            )
        except Exception as e:
            self.logger.error(f"Failed to log conversation for session {self.session_id}: {e}")
            raise

    def get_session_logs(self) -> list:  # Read current conversation history from Redis
        if not self.session_id:
            self.logger.error("No active session. Call start() first.")
            return []
        try:
            data = self._redis.get_json(self._redis_key(self.session_id))
            return data.get("conversation_history", []) if data else []
        except Exception as e:
            self.logger.error(f"Failed to read session logs from Redis: {e}")
            return []

    async def end_session(self) -> None:  # Persist to Neon, then delete Redis key
        if not self.session_id:
            self.logger.warning("No active session to end.")
            return
        redis_key = self._redis_key(self.session_id)
        try:
            session_data = self._redis.get_json(redis_key) or {}
            conversation_history = session_data.get("conversation_history", [])
            participant_context = session_data.get("participant_context", {})

            if self._db_initialized:
                summary = " ".join(
                    m.get("message", "") for m in conversation_history[-10:]
                )
                await insert_session_history({
                    "session_id": self.session_id,
                    "patient_phone": participant_context.get("identity"),
                    "patient_name": participant_context.get("name"),
                    "language": participant_context.get("language"),
                    "conversation_summary": summary[:1000],
                    "evaluation": {},
                    "duration_seconds": 0,
                    "turn_count": len(conversation_history),
                    "resolved": True,
                    "category": "appointment",
                })
                self.logger.info(
                    f"Session {self.session_id} ended. "
                    f"Stored {len(conversation_history)} messages in session_history."
                )
            else:
                self.logger.warning(f"Session {self.session_id} ended but not persisted to Neon.")

            self._redis.delete(redis_key)
            self.logger.info(f"Redis key {redis_key} deleted.")
        except Exception as e:
            self.logger.error(f"Failed to end session {self.session_id}: {e}")
            raise
