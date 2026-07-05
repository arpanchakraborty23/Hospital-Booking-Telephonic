from collections.abc import AsyncIterable


from livekit import rtc
from livekit.agents import Agent, ModelSettings, llm, stt
from livekit.agents.llm import ChatContext


class BaseAgent(Agent):
    """
    Extended Agent class with streaming capabilities for LLM, STT, and TTS.
    Optimized for ultra-fast streaming with minimal latency and async TTS.
    """

    def __init__(self, *args, **kwargs):
        # Pass all args to LiveKit Agent; set defaults for language tracking and context window
        super().__init__(*args, **kwargs)
        self.language = "en"
        self._conversation_summary: str = ""
        self._max_ctx_items = 10

    @property
    def conversation_summary(self) -> str:
        return self._conversation_summary

    async def on_enter(self):  # Auto-trigger first LLM response when session starts
        await self.session.generate_reply()

    async def stt_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> AsyncIterable[stt.SpeechEvent | str]:  # Detect language from speech and pass through
        async def filtered_audio():
            async for frame in audio:
                yield frame

        async for event in Agent.default.stt_node(
            self, filtered_audio(), model_settings
        ):
            if event.alternatives:
                self.language = event.alternatives[0].language or self.language
            yield event

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk]:  # Truncate context window + summarize overflow, then generate
        truncated_ctx = self.chat_ctx.truncate(max_items=self._max_ctx_items)

        async for chunk in Agent.default.llm_node(
            self, chat_ctx=truncated_ctx, model_settings=model_settings
        ):
            yield chunk


    async def tts_node(  # Passthrough — delegates to the configured TTS engine
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        async for frame in Agent.default.tts_node(self, text, model_settings):
            yield frame






