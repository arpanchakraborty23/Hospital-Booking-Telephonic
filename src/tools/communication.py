import logging

from livekit.agents import function_tool

logger = logging.getLogger(__name__)


@function_tool()
async def send_confirmation(phone: str, appointment_details: dict) -> dict:
    """Send appointment confirmation via WhatsApp or SMS to the patient's phone.

    Args:
        phone: Patient's phone number with country code
        appointment_details: Appointment details object containing doctor, date, time, department
    """
    logger.info("Confirmation sent to %s: %s", phone, appointment_details)
    return {"status": "sent", "phone": phone, "method": "whatsapp", "details": appointment_details}


@function_tool()
async def escalate_to_human(reason: str) -> dict:
    """Transfer the call to a human agent. Use when the caller has an emergency, is distressed, asks repeatedly for a human, or has a request outside booking/rescheduling/cancelling.

    Args:
        reason: Reason for escalation (e.g., medical emergency, billing query, repeated human request)
    """
    logger.info("Escalation requested: %s", reason)
    return {"status": "transferred", "reason": reason}
