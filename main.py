import asyncio
import logging

from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, room_io, JobProcess, metrics, UserStateChangedEvent, MetricsCollectedEvent
from livekit.agents.voice import SessionUsageUpdatedEvent
from livekit.agents import ChatContext, JobContext, ServerEnvOption
from livekit.agents.metrics import STTMetrics, LLMMetrics, TTSMetrics
from livekit.plugins import noise_cancellation, silero

from src.monitoring import active_sessions, total_sessions, observe_stt, observe_llm, observe_tts, start_cpu_monitoring
from src.services.cost import persist_cost
from src.utils.session_ctx import set_session_id
from src.voice_agent import RiyaEnglish, RiyaHindi, RiyaBengali
from src.tools.hospital_tools import HospitalTools
from src.services import SessionManager
from src.voice_agent import MetricsCollector
from src.constants.config import LiveKitConfig, DataBaseCOnfig
from src.constants.models import call_logs as CallLog
from src.services.database import SQLModelServices

logger = logging.getLogger(__name__)

session_manager = SessionManager()
metrics_collector = MetricsCollector()
agent_name = LiveKitConfig.livekit_agent_name or "Riya"
_call_svc = SQLModelServices(DataBaseCOnfig.sql_database_url, CallLog)


server = AgentServer(
    load_threshold=0.7,
    drain_timeout=3600,
    num_idle_processes=ServerEnvOption(dev_default=0, prod_default=4),
    log_level=ServerEnvOption(dev_default="DEBUG", prod_default="INFO"),
    prometheus_port=8081,
    host="0.0.0.0",
    port=8081,
)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm



@server.rtc_session(agent_name="qj-hospital")
async def my_agent(ctx: JobContext):

    inactivity_task: asyncio.Task | None = None
    participant_context : dict = {}
    language = "en"

    ctx.log_context_fields = {"room_name": ctx.room.name}
    set_session_id(ctx.room.name)

    await ctx.connect()

    # Wait for participant to join the room before proceeding with session setup
    participant = await ctx.wait_for_participant()

    # Check if this is a SIP call and initialize logging
    is_sip_call = (
                hasattr(participant, 'kind') and 
                participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
            )
    
    # Lookup previous patient info by phone number for SIP calls
    patient_info = None
    if is_sip_call:
        logger.info(f"SIP call detected for participant {participant.identity}. Initializing SIP logging.")
        ctx.log_context_fields["sip_identity"] = participant.identity
        caller_id = participant.identity
        phone_number = participant.attributes.get('sip.phoneNumber', 'Unknown')
        previous_calls = await asyncio.to_thread(_call_svc.filter, CallLog.phone_number == phone_number)
        if previous_calls:
            patient_info = {
                "name": participant.name,
                "phone": phone_number,
                "language": "en",
                "previous_summary": previous_calls[-1].summary,
            }

    if patient_info:
        language = patient_info.get("language", language)

    participant_context = {
        "identity": participant.identity,
        "name": patient_info["name"] if patient_info else participant.name,
        "language": language,
        "previous_summary": patient_info.get("previous_summary") if patient_info else None,
    }
    logger.info("Participant context: %s", participant_context)

    # Start Redis session — stores participant context + conversation history with 2h TTL
    await session_manager.start(session_id=ctx.room.name, participant_context=participant_context)

    # Inject long-term patient history into chat context so agent knows past interactions
    chat_ctx = ChatContext()
    chat_ctx.add_message(role="system", content=participant_context)
    logger.info("Injected participant context for %s", participant_context["identity"])


    # Create language-specific agent with fixed name (never receives participant.name)
    agent_setup = {
        "en": RiyaEnglish,
        "bn": RiyaBengali,
        "hi": RiyaHindi,
    }
    agent = agent_setup[language](
        agent_name=agent_name,
        chat_ctx=chat_ctx,
    )

    # Scope tools — start with only the router toolset; domain tools loaded on demand by user_intent / tool_router
    await agent.update_tools([HospitalTools.get_toolset("router")])

    session = AgentSession(
        vad=silero.VAD.load(),
        turn_handling={
            "endpointing": {"mode": "dynamic", "min_delay": 0.5, "max_delay": 1.5},
            "interruption": {"mode": "adaptive", "min_duration": 0.4, "resume_false_interruption": True},
            "preemptive_generation": {"enabled": True, "preemptive_tts": True},
        },
    )
                
    async def user_presence_task():
        # try to ping the user 3 times, if we get no answer, close the session
        for attempt in range(3):
            await session.generate_reply(
                instructions=(
                    "The user has been inactive. Politely check if the user is still present."
                )
            )
            await asyncio.sleep(20)

        await asyncio.shield(session.aclose())
        ctx.delete_room()
      
    active_sessions.inc()
    total_sessions.inc()

    await session.start(
        room=ctx.room,
        agent=agent,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    @session.on("user_state_changed")
    def _user_state_changed(ev: UserStateChangedEvent):
        nonlocal inactivity_task
        # ev.new_state: listening, speaking, away, ..
        if getattr(ev, "new_state", None) == "away":
            # start a task to check presence
            inactivity_task = asyncio.create_task(user_presence_task())
            return

        # user returned / changed state — cancel inactivity task if present
        if inactivity_task is not None:
            inactivity_task.cancel()
            inactivity_task = None



    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        m = ev.metrics
        if isinstance(m, STTMetrics):
            observe_stt(m)
        elif isinstance(m, LLMMetrics):
            observe_llm(m)
        elif isinstance(m, TTSMetrics):
            observe_tts(m)

    @session.on("session_usage_updated")
    def _on_session_usage_updated(ev: SessionUsageUpdatedEvent):
        metrics_collector.update_session_usage(ev)
        session_manager.update_usage(ev.to_dict())

    @session.on("conversation_item_added")
    def on_conversation_item(event):
        try:
            item = event.item
            if hasattr(item, "content") and item.content:
                speaker = "USER" if hasattr(item, "role") and item.role == "user" else "AGENT"
                session_manager.session_log({
                    "role": speaker.lower(),
                    "message": item.content,
                    "speaker": speaker,
                })
            if event.item.metrics:
                metrics_collector.add_turn_latency(event.item.role, event.item.metrics)
                session_manager.update_turn_latency(event.item.role, event.item.metrics)
        except Exception as e:
            logger.error(f"Error logging conversation item: {e}")


    async def end_handler():
        try:
            active_sessions.dec()
            report = ctx.make_session_report()
            await persist_cost(session_manager, report.to_dict())
            await session_manager.end_session()
            logger.info(f"Session for room {ctx.room.name} ended and cleaned up.")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")

    ctx.add_shutdown_callback(end_handler)


if __name__ == "__main__":
    start_cpu_monitoring()
    agents.cli.run_app(server)
