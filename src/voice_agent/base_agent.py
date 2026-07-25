from collections.abc import AsyncIterable
from typing import Literal


from livekit import rtc
from livekit.agents import Agent, ModelSettings, llm, stt


from src.monitoring import observe_intent
from src.prompt import get_prompt
class BaseAgent(Agent):
    """
    Extended Agent class with streaming capabilities for LLM, STT, and TTS.
    Optimized for ultra-fast streaming with minimal latency and async TTS.
    """

    def __init__(self, *args, **kwargs):
        # Pass all args to LiveKit Agent; set defaults for language tracking and context window
        super().__init__(*args, **kwargs)
        self.language = "en"


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
        tools: list[llm.Tool] ,
    ) -> AsyncIterable[llm.ChatChunk]:  # Truncate context window + summarize overflow, then generate

        async for chunk in Agent.default.llm_node(
            self, chat_ctx=chat_ctx,tools=tools, model_settings=model_settings
        ):
            yield chunk


    async def tts_node(  # Passthrough — delegates to the configured TTS engine
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        async for frame in Agent.default.tts_node(self, text, model_settings):
            yield frame


    @llm.function_tool
    async def user_intent(self, labels: list[Literal["Booking", "Rescheduling", "Cancellation", "Status_Check", "Emergency", "General_Inquiry"]]) -> None:
        """
        Update the prompt for the LLM. This function can be called from within the LLM context.
        """
        intent = labels[0]
        language = self.language
        observe_intent(intent)
        get_prompt_func = get_prompt
        prompt = get_prompt_func(language, intent)  # Use the first label as the intent

        await self.update_instructions(prompt)

        # Auto-load the matching toolset so the LLM doesn't need a separate tool_router call
        intent_to_toolset = {
            "Booking": "appointments",
            "Rescheduling": "appointments",
            "Cancellation": "appointments",
            "Status_Check": "appointments",
            "Emergency": "communication",
            "General_Inquiry": "directory",
        }
        target = intent_to_toolset.get(labels[0])
        if target:
            from src.tools.hospital_tools import HospitalTools
            from src.tools.router import state as router_state

            router_ts = HospitalTools.get_toolset("router")
            target_ts = HospitalTools.get_toolset(target)
            await self.update_tools([router_ts, target_ts])

            # Keep router's in-memory state in sync so check_tools reports correctly
            router_state.set("loaded_tool_groups", [target])

        await self.session.generate_reply()  # Trigger a new LLM response with the updated prompt

    @llm.function_tool
    async def update_agent(self,language: str, instructions: str) -> None:
        """
        Update the prompt for the LLM. This function can be called from within the LLM context.
        """
        from .agents import get_agent_class
        agent_class = get_agent_class(language)
        self.session.update_agent(agent_class(instructions=instructions, vad=self._vad, chat_ctx=self.chat_ctx))
        await self.session.generate_reply()  # Trigger a new LLM response with the updated prompt






