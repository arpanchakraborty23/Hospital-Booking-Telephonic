import contextvars

current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_session_id", default=None
)


def set_session_id(sid: str) -> None:
    current_session_id.set(sid)


def get_session_id() -> str | None:
    return current_session_id.get()
