import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CallEvaluation:
    """Evaluates and summarises call transcripts.

    Called at session end to produce a summary that is stored in the
    call_logs and transcriptions tables.  Currently uses a template-based
    approach; can be extended with LLM-based evaluation.
    """

    def __init__(self, phone_number: str = "", language: str = "en"):
        self._phone_number = phone_number
        self._language = language

    def generate_summary(self, messages: list) -> str:
        """Generate a concise summary from the conversation transcript."""
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
