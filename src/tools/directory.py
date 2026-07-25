import logging

from livekit.agents import function_tool

from src.services.hospital_data import (
    get_departments as _mock_get_departments,
    get_doctors as _mock_get_doctors,
)

logger = logging.getLogger(__name__)


@function_tool()
async def get_departments() -> list[str]:
    """Get list of all available departments in the hospital."""
    return _mock_get_departments()


@function_tool()
async def get_doctors(department: str) -> list[dict]:
    """Get list of doctors in a specific department.

    Args:
        department: Department name
    """
    return _mock_get_doctors(department)
