import asyncio
import logging
import time

from livekit.agents import function_tool

from src.constants.config import DataBaseCOnfig
from src.constants.models import doctor as Doctor
from src.monitoring import observe_tool_call, observe_error
from src.services.database import SQLModelServices

logger = logging.getLogger(__name__)

_doctor_svc = SQLModelServices(DataBaseCOnfig.sql_database_url, Doctor)


@function_tool()
async def get_departments() -> list[str]:
    """Get list of all available departments in the hospital."""
    _start = time.perf_counter()
    try:
        doctors = await asyncio.to_thread(_doctor_svc.get_all)
        departments = sorted({d.specialization for d in doctors if d.specialization})
        observe_tool_call("get_departments", time.perf_counter() - _start, "success")
        return departments
    except Exception as e:
        observe_tool_call("get_departments", time.perf_counter() - _start, "error")
        observe_error("tool_get_departments")
        raise


@function_tool()
async def get_doctors(department: str) -> list[dict]:
    """Get list of doctors in a specific department.

    Args:
        department: Department name
    """
    _start = time.perf_counter()
    try:
        doctors = await asyncio.to_thread(_doctor_svc.filter, Doctor.specialization == department)
        result = [
            {
                "name": d.doctor_name,
                "specialization": d.specialization,
                "hospital_name": d.hospital_name,
                "consultation_fee": d.consultation_fee,
                "experience_years": d.experience_years,
                "available_days": d.available_days,
                "available_time_slots": d.available_time_slots,
            }
            for d in doctors
        ]
        observe_tool_call("get_doctors", time.perf_counter() - _start, "success")
        return result
    except Exception as e:
        observe_tool_call("get_doctors", time.perf_counter() - _start, "error")
        observe_error("tool_get_doctors")
        raise
