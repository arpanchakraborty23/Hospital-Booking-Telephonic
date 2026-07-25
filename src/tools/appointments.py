import logging
from datetime import date
from typing import Optional

from livekit.agents import function_tool

from src.services.hospital_data import (
    check_availability as _mock_check_availability,
    book_appointment as _mock_book_appointment,
    reschedule_appointment as _mock_reschedule_appointment,
    cancel_appointment as _mock_cancel_appointment,
    lookup_appointment as _mock_lookup_appointment,
)

logger = logging.getLogger(__name__)


@function_tool()
async def check_availability(department: str, doctor: Optional[str] = None, date_str: Optional[str] = None) -> list[dict]:
    """Check available appointment slots for a department or doctor on a specific date.

    Args:
        department: The department name (e.g., Cardiology, Dermatology, General Medicine)
        doctor: Optional specific doctor name. If not provided, shows all doctors in the department.
        date_str: Date in YYYY-MM-DD format. Defaults to today if not provided.
    """
    return _mock_check_availability(department, doctor, date_str or date.today().isoformat())


@function_tool()
async def book_appointment(patient_name: str, phone: str, department: str, doctor: str, date_str: str, time: str, language: str = "en") -> dict:
    """Book a new appointment for a patient. Returns confirmation with appointment_id.

    Args:
        patient_name: Full name of the patient
        phone: Patient's phone number with country code (e.g., +919876543210)
        department: Department name
        doctor: Doctor's name
        language: Patient's preferred language code (en/hi/bn)
        date_str: Appointment date in YYYY-MM-DD format
        time: Appointment time in HH:MM format (e.g., 10:00, 14:30)
    """
    return _mock_book_appointment(patient_name, phone, department, doctor, date_str, time)


@function_tool()
async def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Reschedule an existing appointment to a new date and time.

    Args:
        appointment_id: The appointment ID to reschedule (e.g., APT001)
        new_date: New appointment date in YYYY-MM-DD format
        new_time: New appointment time in HH:MM format
    """
    return _mock_reschedule_appointment(appointment_id, new_date, new_time)


@function_tool()
async def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing appointment.

    Args:
        appointment_id: The appointment ID to cancel (e.g., APT001)
    """
    return _mock_cancel_appointment(appointment_id)


@function_tool()
async def lookup_appointment(phone: str) -> list[dict]:
    """Look up appointments by phone number. Returns all appointments for that phone number.

    Args:
        phone: Patient's phone number with country code
    """
    return _mock_lookup_appointment(phone)
