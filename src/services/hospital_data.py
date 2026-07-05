"""
Mock data layer for hospital appointments.
Replace this with real HMS/calendar integration later.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import uuid
import json
import os

# In-memory storage (replace with Neon DB queries in production)
_appointments_db: dict[str, dict] = {}
_patients_db: dict[str, dict] = {}

# Sample departments and doctors
DEPARTMENTS = [
    "General Medicine",
    "Cardiology",
    "Dermatology",
    "Orthopedics",
    "Pediatrics",
    "Gynecology",
    "Neurology",
    "Ophthalmology",
    "ENT",
    "Psychiatry"
]

DOCTORS = {
    "General Medicine": [
        {"name": "Dr. Rahul Sharma", "specialty": "Internal Medicine"},
        {"name": "Dr. Anjali Patel", "specialty": "General Practice"}
    ],
    "Cardiology": [
        {"name": "Dr. Amit Kumar", "specialty": "Interventional Cardiology"},
        {"name": "Dr. Sunita Singh", "specialty": "Heart Failure"}
    ],
    "Dermatology": [
        {"name": "Dr. Priya Ghosh", "specialty": "Cosmetic Dermatology"},
        {"name": "Dr. Raj Malhotra", "specialty": "Clinical Dermatology"}
    ],
    "Orthopedics": [
        {"name": "Dr. Vikram Reddy", "specialty": "Joint Replacement"},
        {"name": "Dr. Meera Shah", "specialty": "Sports Medicine"}
    ],
    "Pediatrics": [
        {"name": "Dr. Arjun Nair", "specialty": "General Pediatrics"},
        {"name": "Dr. Kavita Das", "specialty": "Neonatology"}
    ],
    "Gynecology": [
        {"name": "Dr. Lakshmi Iyer", "specialty": "Obstetrics"},
        {"name": "Dr. Fatima Begum", "specialty": "Reproductive Medicine"}
    ],
    "Neurology": [
        {"name": "Dr. Sanjay Gupta", "specialty": "Neurological Disorders"},
        {"name": "Dr. Rani Mukherjee", "specialty": "Stroke Management"}
    ],
    "Ophthalmology": [
        {"name": "Dr. Deepak Agarwal", "specialty": "Cataract Surgery"},
        {"name": "Dr. Anu Sharma", "specialty": "Retina"}
    ],
    "ENT": [
        {"name": "Dr. Kiran Desai", "specialty": "Ear Surgery"},
        {"name": "Dr. Rohit Khanna", "specialty": "Sinus Treatment"}
    ],
    "Psychiatry": [
        {"name": "Dr. Maya Trivedi", "specialty": "Clinical Psychiatry"},
        {"name": "Dr. Akbar Khan", "specialty": "Child Psychiatry"}
    ]
}

# Generate mock availability slots
def _generate_slots(date: str, doctor: str) -> list[str]:
    """Generate mock time slots for a doctor on a given date."""
    slots = []
    base_hour = 9
    for hour in range(base_hour, 17):  # 9 AM to 5 PM
        for minute in [0, 30]:
            if hour == 12:  # Lunch break
                continue
            time_str = f"{hour:02d}:{minute:02d}"
            # Randomly make some slots unavailable for realism
            if hash(f"{date}{doctor}{time_str}") % 3 != 0:
                slots.append(time_str)
    return slots

# Pre-populate with sample patients and appointments for demo/testing
def _init_mock_data():
    global _appointments_db, _patients_db
    
    # Sample patients
    _patients_db = {
        "+919876543210": {
            "name": "Ramesh Kumar",
            "phone": "+919876543210",
            "language": "hi"
        },
        "+919123456789": {
            "name": "Smt. Lakshmi Devi",
            "phone": "+919123456789",
            "language": "ta"
        }
    }
    
    # Sample appointments
    base_date = datetime.now().strftime("%Y-%m-%d")
    _appointments_db = {
        "APT001": {
            "appointment_id": "APT001",
            "patient_name": "Ramesh Kumar",
            "phone": "+919876543210",
            "department": "Cardiology",
            "doctor": "Dr. Amit Kumar",
            "date": base_date,
            "time": "10:00",
            "status": "confirmed"
        },
        "APT002": {
            "appointment_id": "APT002",
            "patient_name": "Smt. Lakshmi Devi",
            "phone": "+919123456789",
            "department": "Gynecology",
            "doctor": "Dr. Lakshmi Iyer",
            "date": base_date,
            "time": "14:30",
            "status": "confirmed"
        }
    }

# Initialize on import
_init_mock_data()


@dataclass
class Appointment:
    appointment_id: str
    patient_name: str
    phone: str
    department: str
    doctor: str
    date: str
    time: str
    status: str = "confirmed"


def check_availability(department: str, doctor: Optional[str], date: str) -> list[dict]:
    """
    Check available slots for a department/doctor on a given date.
    Returns list of available time slots.
    """
    available_slots = []
    
    if doctor:
        doctors_list = [d for d in DOCTORS.get(department, []) if d["name"] == doctor]
        if doctors_list:
            slots = _generate_slots(date, doctor)
            available_slots.append({
                "doctor": doctor,
                "slots": slots
            })
    else:
        # Return slots for all doctors in department
        for doc_info in DOCTORS.get(department, []):
            doc_name = doc_info["name"]
            slots = _generate_slots(date, doc_name)
            available_slots.append({
                "doctor": doc_name,
                "specialty": doc_info["specialty"],
                "slots": slots
            })
    
    return available_slots


def book_appointment(  # Create a new appointment, store in-memory, return with ID
    patient_name: str,
    phone: str,
    department: str,
    doctor: str,
    date: str,
    time: str
) -> dict:
    """
    Book an appointment. Returns confirmation with appointment_id.
    """
    appointment_id = f"APT{str(len(_appointments_db) + 1).zfill(3)}"
    
    appointment = {
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "phone": phone,
        "department": department,
        "doctor": doctor,
        "date": date,
        "time": time,
        "status": "confirmed"
    }
    
    _appointments_db[appointment_id] = appointment
    
    # Also store by phone for lookup
    if phone not in _patients_db:
        _patients_db[phone] = {"name": patient_name, "phone": phone}
    
    return appointment


def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:  # Update date/time, mark as rescheduled
    """
    Reschedule an existing appointment.
    """
    if appointment_id not in _appointments_db:
        return {"error": "Appointment not found", "appointment_id": appointment_id}
    
    apt = _appointments_db[appointment_id]
    apt["date"] = new_date
    apt["time"] = new_time
    apt["status"] = "rescheduled"
    
    return apt


def cancel_appointment(appointment_id: str) -> dict:  # Mark appointment as cancelled (keeps record)
    """
    Cancel an appointment.
    """
    if appointment_id not in _appointments_db:
        return {"error": "Appointment not found", "appointment_id": appointment_id}
    
    apt = _appointments_db[appointment_id]
    apt["status"] = "cancelled"
    
    return apt


def lookup_appointment(phone: str) -> list[dict]:  # Find all non-cancelled appointments for a phone
    """
    Lookup appointments by phone number.
    """
    results = []
    for apt in _appointments_db.values():
        if apt["phone"] == phone and apt["status"] != "cancelled":
            results.append(apt)
    return results


def get_departments() -> list[str]:  # Static list of hospital departments
    return DEPARTMENTS


def get_doctors(department: str) -> list[dict]:  # Doctors within a department
    return DOCTORS.get(department, [])


def send_confirmation(phone: str, appointment_details: dict) -> dict:
    """
    Send confirmation via WhatsApp/SMS.
    Stub - replace with real provider later.
    """
    # Stub implementation
    return {
        "status": "sent",
        "phone": phone,
        "message": f"Appointment confirmed: {appointment_details.get('doctor')} on {appointment_details.get('date')} at {appointment_details.get('time')}",
        "channel": "whatsapp"
    }


def escalate_to_human(reason: str) -> dict:  # Stub: flags call for manual handoff
    """
    Flag call for human escalation.
    """
    return {
        "status": "escalated",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }