from __future__ import annotations

from livekit.agents import ChatContext, inference
from livekit.agents.llm import FallbackAdapter as LLMFallBack
from livekit.agents.stt import FallbackAdapter as STTFallBack
from livekit.agents.tts import FallbackAdapter as TTSFallBack
from livekit.plugins import deepgram, sarvam, silero

from . import BaseAgent
from src.tools import tool_router
from src.constants import ProviderConfig, get_models
from src.prompt.english import english_prompt
from src.prompt.hindi import hindi_prompt
from src.prompt.bengali import bengali_prompt

# Pre-fetch model configs for all three supported languages
english_models = get_models(language="en")
hindi_models = get_models(language="hi")
bengali_models = get_models(language="bn")

# Singleton: all tool groups as Toolsets for dynamic loading
_hospital_toolsets = [tool_router]


class RiyaEnglish(BaseAgent):  # English-speaking agent with English STT/LLM/TTS models
    def __init__(self, *, agent_name: str = "Riya", vad: silero.VAD = None, chat_ctx: ChatContext = None) -> None:
        self._vad = vad
        super().__init__(
            instructions=english_prompt(agent_name=agent_name),
            stt=STTFallBack(
                stt=[
                    english_models.stt,
                    inference.STT(model="assemblyai/universal-streaming"),
                    deepgram.STT(
                        model="nova-3",
                        language="en-IN",
                        enable_diarization=True,
                        api_key=ProviderConfig.deepgram_api_key,
                    ),
                ]
            ),
            llm=LLMFallBack(
                llm=[
                    english_models.llm,
                    inference.LLM(model="openai/gpt-4.1-mini")
                ]
            ),
            tts=TTSFallBack(
                tts=[
                    english_models.tts,
                    inference.TTS(model="elevenlabs/eleven_multilingual_v2"),
                    sarvam.TTS(
                        target_language_code="en-IN",
                        api_key=ProviderConfig.sarvam_api_key
                    ),
                ]
            ),
            tools=_hospital_toolsets,
            chat_ctx=chat_ctx,
            vad=vad,
        )


class RiyaHindi(BaseAgent):  # Hindi-speaking agent with Hindi STT/LLM/TTS models
    def __init__(self, *, agent_name: str = "Riya", vad: silero.VAD = None, chat_ctx: ChatContext = None) -> None:
        self._vad = vad
        super().__init__(
            instructions=hindi_prompt(agent_name=agent_name),
            stt=STTFallBack(
                stt=[
                    hindi_models.stt,
                    deepgram.STT(
                        model="nova-3",
                        language="hi-IN",
                        enable_diarization=True,
                        api_key=ProviderConfig.deepgram_api_key,
                    ),
                ]
            ),
            llm=LLMFallBack(
                llm=[
                    hindi_models.llm,
                    inference.LLM(model="openai/gpt-4.1-mini"),
        
                ]
            ),
            tts=TTSFallBack(
                tts=[
                    hindi_models.tts,
                    sarvam.TTS(
                        target_language_code="hi-IN",
                        api_key=ProviderConfig.sarvam_api_key
                    ),
                ]
            ),
            tools=_hospital_toolsets,
            chat_ctx=chat_ctx,
            vad=vad,
        )


class RiyaBengali(BaseAgent):  # Bengali-speaking agent with Bengali STT/LLM/TTS models
    def __init__(self, *, agent_name: str = "Riya", vad: silero.VAD = None, chat_ctx: ChatContext = None) -> None:
        self._vad = vad
        super().__init__(
            instructions=bengali_prompt(agent_name=agent_name),
            stt=STTFallBack(
                stt=[
                    bengali_models.stt,
                    deepgram.STT(
                        model="nova-3",
                        language="bn-IN",
                        enable_diarization=True,
                        api_key=ProviderConfig.deepgram_api_key,
                    ),
                ]
            ),
            llm=LLMFallBack(
                llm=[
                    bengali_models.llm,
                    inference.LLM(model="openai/gpt-4.1-mini"),
                ]
            ),
            tts=TTSFallBack(
                tts=[
                    bengali_models.tts,
                    sarvam.TTS(
                        target_language_code="bn-IN",
                        api_key=ProviderConfig.sarvam_api_key,
                    ),
                ]
            ),
            tools=_hospital_toolsets,
            chat_ctx=chat_ctx,
            vad=vad,
        )
