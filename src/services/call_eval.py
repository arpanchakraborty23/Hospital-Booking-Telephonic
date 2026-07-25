import json
import logging

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage

from src.constants.config import AWSConfig, EvalConfig
from src.monitoring import observe_eval, observe_error

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a call quality evaluator for a hospital voice agent named "Riya".
Analyze the conversation transcript and evaluate the call.

Return ONLY valid JSON (no markdown, no explanation outside the JSON) with this structure:
{
  "summary": "Brief one-paragraph summary of what the patient wanted and what happened",
  "metrics": {
    "response_accuracy": <1-10 score — how accurately the agent answered>,
    "task_completion": <1-10 score — was the patient's request fulfilled>,
    "behavior_tone": <1-10 score — quality of agent tone, empathy, professionalism>,
    "conversation_flow": <1-10 score — how natural and coherent the dialogue was>,
    "information_retrieval": <1-10 score — how well the agent retrieved relevant info (RAG quality)>
  },
  "feedback": "Specific, actionable feedback for improving the agent on this type of call"
}\
"""


class CallEvaluation:
    """Evaluates call transcripts using an LLM (AWS Bedrock via LangChain).

    At session end the transcript is sent to the LLM which returns:
      - summary  (stored in call_logs.summary and transcriptions.summary)
      - metrics  (stored inside transcriptions.transcription_text JSON)
      - feedback (stored inside transcriptions.transcription_text JSON)

    The feedback loop (using feedback to improve the agent) will be
    added later — for now we only generate and persist the evaluation.
    """

    def __init__(self, phone_number: str = "", language: str = "en"):
        self._phone_number = phone_number
        self._language = language
        self._model = ChatBedrockConverse(
            model=EvalConfig.bedrock_eval_model,
            region_name=AWSConfig.aws_region,
            temperature=0.3,
            max_tokens=2048,
        )

    async def evaluate(self, messages: list) -> dict:
        """Send transcript to LLM and return {summary, metrics, feedback}.

        Falls back to a template-based summary if the LLM call fails.
        """
        if not messages:
            return {
                "summary": "No conversation recorded.",
                "metrics": {},
                "feedback": "",
            }

        transcript = self._format_transcript(messages)

        try:
            response = await self._model.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=f"Phone: {self._phone_number}\nLanguage: {self._language}\n\nTranscript:\n{transcript}"),
            ])
            result = self._parse_response(response.content)
            logger.info("LLM evaluation completed for %s", self._phone_number)
            metrics = result.get("metrics", {})
            for metric, value in metrics.items():
                if isinstance(value, (int, float)):
                    observe_eval(metric, value)
            return result
        except Exception as e:
            observe_error("llm_eval")
            logger.error("LLM evaluation failed, using fallback: %s", e)
            return self._fallback_summary(messages)

    def _format_transcript(self, messages: list) -> str:
        """Convert message dicts into a readable transcript string."""
        lines = []
        for m in messages:
            role = m.get("role", "unknown").upper()
            content = m.get("message", m.get("content", ""))
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _parse_response(self, content: str) -> dict:
        """Parse the LLM JSON response into a dict."""
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") for block in content if isinstance(block, dict)
            )
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            parsed = json.loads(content)
            return {
                "summary": parsed.get("summary", ""),
                "metrics": parsed.get("metrics", {}),
                "feedback": parsed.get("feedback", ""),
            }
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("Failed to parse LLM response as JSON: %s", e)
            return {
                "summary": content[:500] if content else "Evaluation parse error.",
                "metrics": {},
                "feedback": "",
            }

    def _fallback_summary(self, messages: list) -> dict:
        """Template-based fallback if the LLM call fails."""
        user_count = sum(1 for m in messages if m.get("role") == "user")
        agent_count = sum(1 for m in messages if m.get("role") == "agent")
        return {
            "summary": (
                f"Call with {self._phone_number}. "
                f"{len(messages)} messages ({user_count} user, {agent_count} agent). "
                f"General inquiry."
            ),
            "metrics": {},
            "feedback": "",
        }
