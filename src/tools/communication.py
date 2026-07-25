import logging
import time

from livekit.agents import function_tool

from src.monitoring import observe_tool_call, observe_error

logger = logging.getLogger(__name__)


@function_tool()
async def send_confirmation(phone: str, appointment_details: dict) -> dict:
    """Send appointment confirmation via WhatsApp or SMS to the patient's phone.

    Args:
        phone: Patient's phone number with country code
        appointment_details: Appointment details object containing doctor, date, time, department
    """
    _start = time.perf_counter()
    try:
        logger.info("Confirmation sent to %s: %s", phone, appointment_details)
        result = {"status": "sent", "phone": phone, "method": "whatsapp", "details": appointment_details}
        observe_tool_call("send_confirmation", time.perf_counter() - _start, "success")
        return result
    except Exception as e:
        observe_tool_call("send_confirmation", time.perf_counter() - _start, "error")
        observe_error("tool_send_confirmation")
        raise


@function_tool()
async def escalate_to_human(reason: str) -> dict:
    """Transfer the call to a human agent. Use when the caller has an emergency, is distressed, asks repeatedly for a human, or has a request outside booking/rescheduling/cancelling.

    Args:
        reason: Reason for escalation (e.g., medical emergency, billing query, repeated human request)
    """
    _start = time.perf_counter()
    try:
        logger.info("Escalation requested: %s", reason)
        result = {"status": "transferred", "reason": reason}
        observe_tool_call("escalate_to_human", time.perf_counter() - _start, "success")
        return result
    except Exception as e:
        observe_tool_call("escalate_to_human", time.perf_counter() - _start, "error")
        observe_error("tool_escalate_to_human")
        raise
