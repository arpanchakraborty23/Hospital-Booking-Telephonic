# Hospital Voice Agent - Component Documentation

## Overview
This document provides detailed information about all components and classes used in the Hospital Voice Agent project.

---

## 1. Voice Agent Components

### 1.1 Agent Classes (ExiaEnglish, ExiaHindi, ExiaBengali)
**Location:** `src/voice_agent/agents.py`

**Purpose:** Language-specific hospital receptionist agents.

**Key Features:**
- Language-specific STT/LLM/TTS pipeline
- HospitalTools integration for appointment management
- Fallback adapters for reliability

**Usage:**
```python
from src.voice_agent.agents import ExiaEnglish

agent = ExiaEnglish(chat_ctx=chat_ctx)
```

---

## 2. Session Management Components

### 2.1 SessionManager Class
**Location:** `src/services/session.py`

**Purpose:** Manages conversation sessions, tracking participant context, and storing session data in Neon (serverless PostgreSQL) and Redis.

**Key Methods:**
- `start(session_id, participant_context)` - Initializes a new session in Redis
- `session_log(log_entry)` - Logs conversation entries to Redis
- `get_session_logs()` - Retrieves conversation history from Redis
- `end_session()` - Persists session history to Neon and cleans up Redis

---

## 3. Database Components

### 3.1 NeonServices Class
**Location:** `src/services/database.py`

**Purpose:** Manages Neon (serverless PostgreSQL) connection lifecycle and CRUD operations via asyncpg.

**Key Methods:**
- `connect()` / `disconnect()` - Connection pool management
- `get_doctors(department)` - Fetch doctors by department
- `get_availability(doctor_id)` - Fetch weekly recurring slots
- `is_doctor_on_leave(doctor_id, date)` - Check leave status
- `create_booking(data)` - Insert new appointment
- `get_bookings_by_phone(phone)` - Lookup appointments
- `reschedule_booking(id, date, time)` - Change appointment
- `update_booking_status(id, status)` - Cancel/complete
- `get_today_visiting(date)` - Today's doctor roster
- `insert_session_history(data)` - Store call history with eval
- `insert_session_cost(data)` - Store per-call cost breakdown

### 3.2 NeonPool Class
**Location:** `src/services/database.py`

**Purpose:** Singleton asyncpg connection pool for Neon (1-5 connections, serverless-optimized).

---

## 4. Metrics Components

### 4.1 MetricsCollector Class
**Location:** `src/voice_agent/metrics.py`

**Purpose:** Handles collection and display of all LiveKit agent metrics.

**Supported Metrics:**
- TTS Metrics (Text-to-Speech)
- STT Metrics (Speech-to-Text)
- LLM Metrics (Language Model)
- VAD Metrics (Voice Activity Detection)
- EOUMetrics (End-of-Utterance)
- Interruption Metrics

---

## 5. Appointment Management

### 5.1 HospitalTools Class
**Location:** `src/voice_agent/hospital_tools.py`

**Purpose:** Creates LLM-callable function tools for appointment operations.

**Available Tools:**
- `check_availability` - Check open slots
- `book_appointment` - Book new appointment
- `reschedule_appointment` - Reschedule existing
- `cancel_appointment` - Cancel appointment
- `lookup_appointment` - Find by phone
- `get_departments` - List departments
- `get_doctors` - List doctors
- `send_confirmation` - WhatsApp/SMS
- `escalate_to_human` - Emergency transfer

---

## 6. Database Schema (7 tables)

| Table | Purpose |
|-------|---------|
| `doctors` | Doctor profiles by department |
| `availability` | Weekly recurring slots per doctor |
| `leave_tracker` | Doctor time-off with approval status |
| `bookings` | Appointment records with status |
| `today_visiting` | Daily visiting doctor roster |
| `session_history` | Per-call history + evaluation JSONB |
| `session_cost` | Per-call cost by AI service |

---

## 7. External Services

**STT:** Deepgram Nova-3 (English/Hindi), Sarvam Saaras v2.5 (Bengali)
**LLM:** Sarvam 105b-32k, OpenAI GPT-4.1 Mini (fallback)
**TTS:** Cartesia Sonic-3 (English/Hindi), Sarvam Bulbul v3 (Bengali)
**VAD:** Silero Voice Activity Detection
**Database:** Neon (serverless PostgreSQL) + Redis (cache)
**Storage:** AWS S3

---

**Version:** 2.1
**Last Updated:** July 5, 2026
