import json
import logging
from typing import Optional

from src.services.database import NeonPool

logger = logging.getLogger(__name__)


async def get_patient_history(phone: str, limit: int = 5) -> list[dict]:
    pool = await NeonPool.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT session_id, language, conversation_summary,
                   category, resolved, created_at
            FROM session_history
            WHERE patient_phone = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            phone, limit,
        )
        return [dict(r) for r in rows]


async def insert_session_history(data: dict) -> dict:
    pool = await NeonPool.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO session_history (session_id, patient_phone, language, conversation_summary, evaluation, duration_seconds, turn_count, resolved, category)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
            ON CONFLICT (session_id)
            DO UPDATE SET conversation_summary = EXCLUDED.conversation_summary,
                          evaluation = EXCLUDED.evaluation,
                          duration_seconds = EXCLUDED.duration_seconds,
                          turn_count = EXCLUDED.turn_count,
                          resolved = EXCLUDED.resolved
            RETURNING *
            """,
            data["session_id"],
            data.get("patient_phone"),
            data.get("language"),
            data.get("conversation_summary"),
            json.dumps(data.get("evaluation", {})),
            data.get("duration_seconds", 0),
            data.get("turn_count", 0),
            data.get("resolved", False),
            data.get("category"),
        )
        return dict(row)


async def insert_session_cost(data: dict) -> dict:
    pool = await NeonPool.get_pool()
    async with pool.acquire() as conn:
        total = (
            data.get("stt_cost", 0)
            + data.get("llm_cost", 0)
            + data.get("tts_cost", 0)
        )
        row = await conn.fetchrow(
            """
            INSERT INTO session_cost (session_id, stt_cost, llm_cost, tts_cost, total_cost, currency, stt_seconds, llm_tokens, tts_characters)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
            """,
            data["session_id"],
            data.get("stt_cost", 0),
            data.get("llm_cost", 0),
            data.get("tts_cost", 0),
            round(total, 6),
            data.get("currency", "USD"),
            data.get("stt_seconds", 0),
            data.get("llm_tokens", 0),
            data.get("tts_characters", 0),
        )
        return dict(row)
