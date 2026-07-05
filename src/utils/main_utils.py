import json
import logging
import os
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def required_env(name: str) -> str:
    value = env(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def safe_json_loads(data: str | None, default: Any = None) -> Any:
    if not data or data == "empty":
        return default if default is not None else {}
    try:
        parsed = json.loads(data)
        return parsed if isinstance(parsed, dict) else {"raw_metadata": parsed}
    except json.JSONDecodeError:
        logger.warning("Failed to parse JSON. Falling back to raw string.")
        return {"raw_metadata": data} if default is None else default


def parse_json_metadata(raw_metadata: str | None) -> dict[str, Any]:
    return safe_json_loads(raw_metadata, default={})


def normalize_participant_attributes(raw_attributes: Any) -> dict[str, Any]:
    if not raw_attributes:
        return {}
    if isinstance(raw_attributes, dict):
        return raw_attributes
    try:
        return dict(raw_attributes)
    except Exception:
        logger.warning("Participant attributes could not be normalized. Ignoring attributes.")
        return {}


def build_user_profile_text(participant_context: dict[str, Any]) -> str:
    user_name = participant_context.get("user_name") or participant_context.get("name") or "Unknown"
    age = participant_context.get("age") or "Unknown"
    native_language = participant_context.get("native_language") or "Unknown"
    level = participant_context.get("level") or participant_context.get("english_level") or "Unknown"
    practice_language = participant_context.get("language") or "english"
    reason = participant_context.get("reason") or "general practice"
    examples = participant_context.get("conversation_examples") or "not provided"
    return (
        f"name:{user_name},"
        f"age:{age},"
        f"native_language:{native_language},"
        f"english_level:{level},"
        f"practice_language:{practice_language},"
        f"practice_reason:{reason},"
        f"examples:{examples}"
    )


def utc_timestamp() -> str:
    return datetime.now().isoformat()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def row_to_dict(row) -> dict | None:
    return dict(row) if row else None
