from livekit.agents.llm import Toolset

from src.tools import (
    check_availability,
    book_appointment,
    reschedule_appointment,
    cancel_appointment,
    lookup_appointment,
    get_departments,
    get_doctors,
    get_hospital_info,
    send_confirmation,
    escalate_to_human,
    tool_router,
)


class HospitalTools:
    _router = Toolset(id="router", tools=[tool_router])
    _directory = Toolset(id="directory", tools=[get_departments, get_doctors, get_hospital_info])
    _appointments = Toolset(id="appointments", tools=[
        check_availability,
        book_appointment,
        reschedule_appointment,
        cancel_appointment,
        lookup_appointment,
    ])
    _communication = Toolset(id="communication", tools=[
        send_confirmation,
        escalate_to_human,
    ])

    @classmethod
    def create_toolsets(cls) -> list:
        return [cls._router, cls._directory, cls._appointments, cls._communication]

    @classmethod
    def get_toolset(cls, toolset_id: str) -> Toolset:
        return {
            "router": cls._router,
            "directory": cls._directory,
            "appointments": cls._appointments,
            "communication": cls._communication,
        }[toolset_id]
