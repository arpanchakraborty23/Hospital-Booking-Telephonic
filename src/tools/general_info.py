from livekit.agents import function_tool

HOSPITAL_INFO = {
    "name": "ABC Hospital",
    "address": "123 Health Avenue, Medical District, Bengaluru - 560001",
    "phone": "+91-80-1234-5678",
    "email": "info@abchospital.com",
    "website": "www.abchospital.com",
    "timings": {
        "opd": "9:00 AM - 5:00 PM (Monday to Saturday)",
        "emergency": "24 x 7 (All days)",
        "visiting_hours": "10:00 AM - 12:00 PM, 4:00 PM - 6:00 PM",
        "pharmacy": "8:00 AM - 10:00 PM (All days)",
        "lab": "7:00 AM - 8:00 PM (Monday to Saturday)",
        "radiology": "8:00 AM - 6:00 PM (Monday to Saturday)",
    },
    "services": [
        "Outpatient Department (OPD)",
        "Inpatient Department (IPD)",
        "24x7 Emergency & Trauma Care",
        "Diagnostic Laboratory",
        "Pharmacy",
        "Radiology & Imaging (X-Ray, CT, MRI, Ultrasound)",
        "Ambulance Service",
        "Blood Bank",
        "ICU & NICU",
        "Operation Theatre",
    ],
    "facilities": [
        "Wheelchair accessible",
        "ATM on premises",
        "Cafeteria",
        "Multi-level parking",
        "Prayer room",
        "Visitor waiting lounge",
    ],
    "registration": {
        "process": "Visit the registration desk on the ground floor with a valid photo ID. Registration fee: Rs. 50.",
        "required_documents": "Aadhaar Card / PAN Card / Passport / Driving License (any government-issued photo ID)",
        "insurance": "We accept all major insurance providers. Cashless facility available for partner insurers. Bring your insurance card and ID.",
    },
    "departments": [
        "Cardiology",
        "Neurology",
        "Pediatrics",
        "Orthopedics",
        "Dermatology",
        "General Medicine",
        "ENT",
        "Ophthalmology",
        "Gynecology",
        "Psychiatry",
    ],
    "emergency_contact": "+91-80-1234-5600",
    "ambulance": "+91-80-1234-5601",
}


@function_tool()
async def get_hospital_info() -> dict:
    """Get general hospital information including address, timings, services, facilities, and registration details.

    Use this for queries about hospital location, visiting hours, OPD timings, emergency services,
    available facilities, registration process, insurance, or any general hospital-related question.
    """
    return HOSPITAL_INFO
