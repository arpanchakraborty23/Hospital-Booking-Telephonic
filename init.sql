-- ============================================================
-- Hospital Voice Agent - Neon Database Schema
-- Serverless PostgreSQL for production
-- ============================================================

-- 1. DOCTORS
CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    specialty VARCHAR(255),
    department VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    consultation_fee DECIMAL(10,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. AVAILABILITY (weekly recurring slots per doctor)
CREATE TABLE IF NOT EXISTS availability (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. LEAVE (doctor time-off)
CREATE TABLE IF NOT EXISTS leave_tracker (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. BOOKINGS (appointments)
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_id VARCHAR(50) UNIQUE NOT NULL,
    session_id VARCHAR(255),
    patient_name VARCHAR(255) NOT NULL,
    patient_phone VARCHAR(50) NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    doctor_id INTEGER REFERENCES doctors(id),
    department VARCHAR(255),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'rescheduled', 'cancelled', 'completed', 'no_show')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. DOCTOR VISITS (daily visiting schedule)
CREATE TABLE IF NOT EXISTS doctor_visits (
    id SERIAL PRIMARY KEY,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    visit_date DATE NOT NULL,
    department VARCHAR(255),
    available_slots INTEGER DEFAULT 0,
    max_slots INTEGER DEFAULT 20,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(doctor_id, visit_date)
);

-- 6. SESSION HISTORY (with evaluation)
CREATE TABLE IF NOT EXISTS session_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    patient_phone VARCHAR(50),
    language VARCHAR(10),
    conversation_summary TEXT,
    evaluation JSONB DEFAULT '{}',
    duration_seconds INTEGER DEFAULT 0,
    turn_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. SESSION COST (per-call cost tracking)
CREATE TABLE IF NOT EXISTS session_cost (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES session_history(session_id) ON DELETE CASCADE,
    stt_cost DECIMAL(10,6) DEFAULT 0,
    llm_cost DECIMAL(10,6) DEFAULT 0,
    tts_cost DECIMAL(10,6) DEFAULT 0,
    total_cost DECIMAL(10,6) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    stt_seconds INTEGER DEFAULT 0,
    llm_tokens INTEGER DEFAULT 0,
    tts_characters INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- INDEXES
CREATE INDEX IF NOT EXISTS idx_bookings_phone ON bookings (patient_phone);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings (appointment_date);
CREATE INDEX IF NOT EXISTS idx_bookings_doctor ON bookings (doctor_id);
CREATE INDEX IF NOT EXISTS idx_availability_doctor ON availability (doctor_id);
CREATE INDEX IF NOT EXISTS idx_leave_doctor ON leave_tracker (doctor_id);
CREATE INDEX IF NOT EXISTS idx_doctor_visits_date ON doctor_visits (visit_date);
CREATE INDEX IF NOT EXISTS idx_session_history_phone ON session_history (patient_phone);
CREATE INDEX IF NOT EXISTS idx_session_cost_session ON session_cost (session_id);
