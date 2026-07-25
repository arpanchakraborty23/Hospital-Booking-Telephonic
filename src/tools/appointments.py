import logging
from datetime import datetime
from typing import Optional

from livekit.agents import function_tool

from src.constants.config import DataBaseCOnfig
from src.constants.models import appointment as Appointment
from src.constants.models import doctor as Doctor
from src.services.database import SQLModelServices

logger = logging.getLogger(__name__)

_apt_svc = SQLModelServices(DataBaseCOnfig.sql_database_url, Appointment)
_doctor_svc = SQLModelServices(DataBaseCOnfig.sql_database_url, Doctor)


@function_tool()
async def check_availability(department: str, doctor: Optional[str] = None, date_str: Optional[str] = None) -> list[dict]:
    """Check available appointment slots for a department or doctor on a specific date.

    Args:
        department: The department name (e.g., Cardiology, Dermatology, General Medicine)
        doctor: Optional specific doctor name. If not provided, shows all doctors in the department.
        date_str: Date in YYYY-MM-DD format. Defaults to today if not provided.
    """
    if doctor:
        docs = _doctor_svc.filter(Doctor.doctor_name == doctor)
    else:
        docs = _doctor_svc.filter(Doctor.specialization == department)

    target_date = date_str or datetime.now().date().isoformat()
    weekday = datetime.fromisoformat(target_date).strftime("%A")

    result = []
    for d in docs:
        available_days = d.available_days or []
        if weekday not in available_days:
            continue
        result.append({
            "doctor": d.doctor_name,
            "specialization": d.specialization,
            "date": target_date,
            "available_time_slots": d.available_time_slots or [],
            "consultation_fee": d.consultation_fee,
        })
    return result


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
    apt_datetime = datetime.fromisoformat(f"{date_str}T{time}:00")
    apt = _apt_svc.create(
        session_id="",
        phone_number=phone,
        appointment_date=apt_datetime,
        doctor_name=doctor,
        payment_status="pending",
        status="scheduled",
    )
    return {
        "appointment_id": apt.id,
        "status": "scheduled",
        "doctor": doctor,
        "department": department,
        "date": date_str,
        "time": time,
        "phone": phone,
    }


@function_tool()
async def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Reschedule an existing appointment to a new date and time.

    Args:
        appointment_id: The appointment ID to reschedule
        new_date: New appointment date in YYYY-MM-DD format
        new_time: New appointment time in HH:MM format
    """
    apt_datetime = datetime.fromisoformat(f"{new_date}T{new_time}:00")
    updated = _apt_svc.update(int(appointment_id), appointment_date=apt_datetime)
    if updated is None:
        return {"error": "Appointment not found", "appointment_id": appointment_id}
    return {
        "appointment_id": updated.id,
        "status": updated.status,
        "new_date": new_date,
        "new_time": new_time,
        "doctor": updated.doctor_name,
    }


@function_tool()
async def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing appointment.

    Args:
        appointment_id: The appointment ID to cancel
    """
    updated = _apt_svc.update(int(appointment_id), status="cancelled")
    if updated is None:
        return {"error": "Appointment not found", "appointment_id": appointment_id}
    return {
        "appointment_id": updated.id,
        "status": "cancelled",
        "doctor": updated.doctor_name,
    }


@function_tool()
async def lookup_appointment(phone: str) -> list[dict]:
    """Look up appointments by phone number. Returns all appointments for that phone number.

    Args:
        phone: Patient's phone number with country code
    """
    apts = _apt_svc.filter(Appointment.phone_number == phone)
    return [
        {
            "appointment_id": a.id,
            "doctor_name": a.doctor_name,
            "appointment_date": a.appointment_date.isoformat() if a.appointment_date else None,
            "status": a.status,
            "payment_status": a.payment_status,
        }
        for a in apts
    ]
