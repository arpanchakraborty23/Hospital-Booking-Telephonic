from datetime import datetime
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Column, ForeignKey
from typing import Optional

# Call logs table
class call_logs(SQLModel, table=True):
    __tablename__ = "call_logs"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    session_id: str
    phone_number: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    start_time: datetime
    end_time: datetime
    duration: float

# transcriptions table
class transcriptions(SQLModel, table=True):
    __tablename__ = "transcriptions"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    session_id: str
    phone_number: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    transcription_text: dict = Field(sa_type=JSON)
    count: int = Field(default=0)
    language: str = Field(default="en")
    summary: str = Field(default="")

class Metrics(SQLModel, table=True):
    __tablename__ = "metrics"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Link all metrics to one call/session
    session_id: str = Field(index=True, unique=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Raw metrics from each service
    stt_metric: dict = Field(default_factory=dict, sa_type=JSON)

    tts_metric: dict = Field(default_factory=dict, sa_type=JSON)

    llm_metric: dict = Field(default_factory=dict, sa_type=JSON)

    # Token usage
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    average_latency: int = 0


# cost table
class cost(SQLModel, table=True):
    __tablename__ = "cost"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    session_id: str
    phone_number: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    stt_cost: float
    tts_cost: float
    llm_cost: float
    sip_cost: float
    total_cost: float


# appointment table
class appointment(SQLModel, table=True):
    __tablename__ = "appointment"
    __table_args__ = {"extend_existing": True}

    id: int = Field(default=None, primary_key=True)
    session_id: str
    phone_number: str
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    appointment_date: datetime
    doctor_name: str
    payment_status: str = Field(default="pending")
    status: str = Field(default="scheduled")

# doctor table
class doctor(SQLModel, table=True):
    __tablename__ = "doctor"
    __table_args__ = {"extend_existing": True}
    # no session_id field for doctor table
    id: int = Field(default=None, primary_key=True)
    doctor_name: str
    specialization: str
    hospital_name: str
    consultation_fee: float
    experience_years: int
    max_patients_per_day: int
    available_days: list = Field(sa_type=JSON)
    available_time_slots: list = Field(sa_type=JSON)