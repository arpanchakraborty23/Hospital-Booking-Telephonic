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
from src.services.database import NeonPool
from src.utils.main_utils import rows_to_dicts
from src.utils.session_ctx import get_session_id

logger = logging.getLogger(__name__)


@function_tool()
async def check_availability(department: str, doctor: Optional[str] = None, date_str: Optional[str] = None) -> list[dict]:
    """Check available appointment slots for a department or doctor on a specific date.

    Args:
        department: The department name (e.g., Cardiology, Dermatology, General Medicine)
        doctor: Optional specific doctor name. If not provided, shows all doctors in the department.
        date_str: Date in YYYY-MM-DD format. Defaults to today if not provided.
    """
    try:
        pool = await NeonPool.get_pool()
        query_date = date.fromisoformat(date_str) if date_str else date.today()
        async with pool.acquire() as conn:
            if doctor:
                rows = await conn.fetch(
                    """SELECT a.*, d.name AS doctor_name, d.specialty
                       FROM availability a JOIN doctors d ON d.id = a.doctor_id
                       WHERE d.name = $1 AND d.department = $2
                       AND a.day_of_week = EXTRACT(DOW FROM $3::date)::int
                       AND a.is_active = TRUE
                       ORDER BY a.start_time""",
                    doctor, department, query_date,
                )
            else:
                rows = await conn.fetch(
                    """SELECT a.*, d.name AS doctor_name, d.specialty
                       FROM availability a JOIN doctors d ON d.id = a.doctor_id
                       WHERE d.department = $1
                       AND a.day_of_week = EXTRACT(DOW FROM $2::date)::int
                       AND a.is_active = TRUE
                       ORDER BY d.name, a.start_time""",
                    department, query_date,
                )
            if rows:
                return rows_to_dicts(rows)
    except Exception as e:
        logger.warning(f"DB check_availability failed, falling back to mock: {e}")

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
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            doctor_row = await conn.fetchrow(
                "SELECT id FROM doctors WHERE name = $1 AND department = $2 LIMIT 1",
                doctor, department,
            )
            doctor_id = doctor_row["id"] if doctor_row else None
            import uuid
            booking_id = f"APT{uuid.uuid4().hex[:6].upper()}"
            session_id = get_session_id()
            row = await conn.fetchrow(
                """INSERT INTO bookings (booking_id, session_id, patient_name, patient_phone, language, doctor_id, department, appointment_date, appointment_time, status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8::date, $9::time, 'confirmed')
                   RETURNING *""",
                booking_id, session_id, patient_name, phone, language, doctor_id, department, date_str, time,
            )
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f"DB book_appointment failed, falling back to mock: {e}")

    return _mock_book_appointment(patient_name, phone, department, doctor, date_str, time)


@function_tool()
async def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Reschedule an existing appointment to a new date and time.

    Args:
        appointment_id: The appointment ID to reschedule (e.g., APT001)
        new_date: New appointment date in YYYY-MM-DD format
        new_time: New appointment time in HH:MM format
    """
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """UPDATE bookings
                   SET appointment_date = $1::date, appointment_time = $2::time, status = 'rescheduled', updated_at = NOW()
                   WHERE booking_id = $3
                   RETURNING *""",
                new_date, new_time, appointment_id,
            )
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f"DB reschedule_appointment failed, falling back to mock: {e}")

    return _mock_reschedule_appointment(appointment_id, new_date, new_time)


@function_tool()
async def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing appointment.

    Args:
        appointment_id: The appointment ID to cancel (e.g., APT001)
    """
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE booking_id = $1 RETURNING *",
                appointment_id,
            )
            if row:
                return dict(row)
    except Exception as e:
        logger.warning(f"DB cancel_appointment failed, falling back to mock: {e}")

    return _mock_cancel_appointment(appointment_id)


@function_tool()
async def lookup_appointment(phone: str) -> list[dict]:
    """Look up appointments by phone number. Returns all appointments for that phone number.

    Args:
        phone: Patient's phone number with country code
    """
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM bookings WHERE patient_phone = $1 AND status != 'cancelled' ORDER BY appointment_date DESC",
                phone,
            )
            if rows:
                return rows_to_dicts(rows)
    except Exception as e:
        logger.warning(f"DB lookup_appointment failed, falling back to mock: {e}")

    return _mock_lookup_appointment(phone)
