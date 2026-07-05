import logging
from typing import Optional

from livekit.agents import function_tool

from src.services.hospital_data import (
    get_departments as _mock_get_departments,
    get_doctors as _mock_get_doctors,
)
from src.services.database import NeonPool
from src.utils.main_utils import rows_to_dicts

logger = logging.getLogger(__name__)


@function_tool()
async def get_departments() -> list[str]:
    """Get list of all available departments in the hospital."""
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT department FROM doctors WHERE is_active = TRUE ORDER BY department"
            )
            if rows:
                return [r["department"] for r in rows]
    except Exception as e:
        logger.warning(f"DB get_departments failed, falling back to mock: {e}")

    return _mock_get_departments()


@function_tool()
async def get_doctors(department: str) -> list[dict]:
    """Get list of doctors in a specific department.

    Args:
        department: Department name
    """
    try:
        pool = await NeonPool.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name, specialty, consultation_fee, id FROM doctors WHERE department = $1 AND is_active = TRUE ORDER BY name",
                department,
            )
            if rows:
                return rows_to_dicts(rows)
    except Exception as e:
        logger.warning(f"DB get_doctors failed, falling back to mock: {e}")

    return _mock_get_doctors(department)
