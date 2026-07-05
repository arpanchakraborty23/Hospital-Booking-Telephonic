import logging

from livekit.agents import function_tool

from src.services.hospital_data import (
    send_confirmation as _mock_send_confirmation,
    escalate_to_human as _mock_escalate_to_human,
)

logger = logging.getLogger(__name__)


@function_tool()
async def send_confirmation(phone: str, appointment_details: dict) -> dict:
    """Send appointment confirmation via WhatsApp or SMS to the patient's phone.

    Args:
        phone: Patient's phone number with country code
        appointment_details: Appointment details object containing doctor, date, time, department
    """
    return _mock_send_confirmation(phone, appointment_details)


@function_tool()
async def escalate_to_human(reason: str) -> dict:
    """Transfer the call to a human agent. Use when the caller has an emergency, is distressed, asks repeatedly for a human, or has a request outside booking/rescheduling/cancelling.

    Args:
        reason: Reason for escalation (e.g., medical emergency, billing query, repeated human request)
    """
    return _mock_escalate_to_human(reason)
