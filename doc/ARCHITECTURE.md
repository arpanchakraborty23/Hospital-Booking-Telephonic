# Hospital Voice Agent - Architecture Documentation

## System Design Overview

This document describes the architectural design patterns and decisions made in the Hospital Voice Agent system.

## 1. High-Level Architecture

### Layered Architecture

```
┌────────────────────────────────────────────────────┐
│           Presentation Layer                        │
│    (LiveKit WebRTC, Voice Input/Output)             │
└─────────────────────┬──────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────┐
│         Agent Orchestration Layer                   │
│    (LiveKit Agents Framework, Session Handler)      │
└─────────────────────┬──────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────┐
│           Business Logic Layer                      │
│  (SessionManager, Voice Agent, Metrics Tracking)    │
└─────────────────────┬──────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────┐
│              Service Layer                          │
│  (Neon, Redis, Metrics Collector)                    │
└─────────────────────┬──────────────────────────────┘
                      │
┌─────────────────────▼──────────────────────────────┐
│          External Services Layer                    │
│  (Neon, Redis, AWS S3, Deepgram, OpenAI,             │
│   Sarvam, Cartesia)                                 │
└────────────────────────────────────────────────────┘
```

## 2. Design Patterns

### 2.1 Factory Pattern
**Used by:** Agent setup in main.py
**Purpose:** Create language-specific agents dynamically
```python
agent_setup = {"en": ExiaEnglish, "bn": ExiaBengali, "hi": ExiaHindi}
agent = agent_setup[language](participant_context)
```

### 2.2 Singleton Pattern
**Used by:** NeonPool
**Purpose:** Single connection pool instance per process
- One Neon pool shared across all sessions
- Efficient connection reuse
- Thread-safe via asyncio

### 2.3 Observer Pattern
**Used by:** Metrics Collection
**Purpose:** React to metric events as they occur
```python
session.metrics_collected += _on_metrics_collected
```

### 2.4 Strategy Pattern
**Used by:** MetricsCollector class
**Purpose:** Different handling for different metric types
```python
if isinstance(metric, TTSMetrics):
    self.collect_tts(metric)
elif isinstance(metric, LLMMetrics):
    self.collect_llm(metric)
```

### 2.5 Decorator Pattern
**Used by:** Noise Cancellation
**Purpose:** Add noise cancellation to audio input
```python
noise_cancellation=lambda params: noise_cancellation.BVC()
```

## 3. Data Flow Architecture

### 3.1 Voice Conversation Flow

```
User Voice Input (Microphone)
        │
        ▼
┌──────────────────┐
│  Noise Cancel.   │ (Audio Processing)
│  (BVC/Silero)    │
└────────┬─────────┘
         │
         ▼
    ┌────────────┐
    │ VAD        │ (Voice Activity Detection)
    │ (Silero)   │ 
    └────┬───────┘
         │
         ▼
    ┌────────────────┐
    │ STT            │ (Speech-to-Text)
    │ (Deepgram/     │
    │  Sarvam)       │
    └────┬───────────┘
         │
         ▼
    ┌────────────────┐
    │ LLM            │ (Language Understanding)
    │ (Sarvam/       │ (Response Generation)
    │  OpenAI)       │
    └────┬───────────┘
         │
         ▼
    ┌────────────────┐
    │ TTS            │ (Text-to-Speech)
    │ (Cartesia/     │
    │  Sarvam)       │
    └────┬───────────┘
         │
         ▼
    Agent Voice Output (Speakers)
```

### 3.2 Data Persistence Flow

```
Session Start
    │
    └─▶ Redis: Initialize Session
        (session_id, conversation_history[], participant_context, TTL 2h)

Conversation Active
    │
    └─▶ Redis: Append Conversation Items
        (real-time, TTL reset on each write)

Session End
    │
    ├─▶ Neon: Insert session_history
    │   (session_id, summary, evaluation, turn_count, duration, category)
    │
    ├─▶ Neon: Insert session_cost
    │   (session_id, stt_cost, llm_cost, tts_cost, total_cost)
    │
    └─▶ Redis: Delete Temporary Data
        (cleanup active session key)
```

## 4. Component Responsibilities

### 4.1 Main Module (main.py)
**Responsibility:** Orchestration and coordination
- Set up LiveKit server
- Handle session lifecycle
- Initialize all components
- Configure audio pipeline
- Wire event handlers

### 4.2 Voice Agent Component
**Responsibility:** LLM-based conversation
- Receive user input
- Generate contextual responses
- Apply language-specific rules
- Call hospital tools for appointment operations

### 4.3 Session Manager
**Responsibility:** Session lifecycle and coordination
- Manage participant context
- Coordinate component interactions
- Persist session data to Neon
- Cache active data in Redis
- Handle cleanup

### 4.4 Database Services
**Responsibility:** Data persistence
- Neon serverless connection pool management
- CRUD operations (doctors, bookings, availability, etc.)
- JSONB storage for evaluations and flexible data
- Async operations via asyncpg with serverless optimizations

### 4.5 Metrics Components
**Responsibility:** Performance monitoring
- Collect metrics from all components
- Aggregate statistics
- Monitor latency across the pipeline

## 5. State Management

### 5.1 Session States

```
┌─────────┐
│  IDLE   │ (No active session)
└────┬────┘
     │ start() called
     ▼
┌─────────────────────────┐
│ INITIALIZING            │ (Setting up resources)
└────┬────────────────────┘
     │ setup complete
     ▼
┌─────────────────────────┐
│ ACTIVE                  │ (Conversation ongoing)
│ - Tracking metrics      │
│ - Logging conversation  │
│ - Caching in Redis      │
└────┬────────────────────┘
     │ end_session() called
     ▼
┌─────────────────────────┐
│ FINALIZING              │ (Cleanup operations)
│ - Persist to Neon       │
│ - Clean up Redis        │
└────┬────────────────────┘
     │ cleanup complete
     ▼
┌─────────┐
│  IDLE   │ (Back to idle state)
└─────────┘
```

## 6. Configuration Management

### 6.1 Environment-Based Configuration

```
.env File (Local)
    │
    └─▶ python-dotenv
        └─▶ os.getenv()
            ├─▶ LiveKit Settings
            ├─▶ Neon Settings
            ├─▶ Redis Settings
            ├─▶ AWS Settings
            └─▶ API Keys
```

### 6.2 Configuration Classes

```python
class NeonConfig:
    database_url = env("NEON_DATABASE_URL")
```

## 7. Error Handling Architecture

### 7.1 Error Handling Strategy

```
Try-Except Blocks
    │
    ├─▶ Connection Errors → Log & Continue without DB
    │   (Neon, Redis)
    │
    ├─▶ Metric Processing Errors → Log Only
    │   (Don't interrupt conversation)
    │
    └─▶ Session Errors → Log & Cleanup
        (Graceful shutdown)
```

### 7.2 Graceful Degradation
- If Neon is unavailable, sessions continue with Redis-only caching
- Session data is logged as warning but conversation is not interrupted
- Final persistence is attempted at session end

## 8. Performance Optimization

### 8.1 Streaming Architecture
- **TTS Audio:** Streamed for faster delivery
- **VAD Processing:** Real-time stream analysis
- **Metrics:** Buffered then batch processed

### 8.2 Caching Strategy
- **VAD Model:** Pre-warmed in prewarm() function
- **Conversation Context:** Kept in Redis (2h TTL)
- **Session Data:** Active in Redis, persisted to Neon

### 8.3 Connection Pooling
- **Neon:** asyncpg pool (1-5 connections, serverless-optimized)
- **Redis:** Single connection with auto-reconnect

## 9. Scalability Considerations

### 9.1 Horizontal Scaling
```
Multiple Agent Servers
    ├─▶ Load Balancer (allocates rooms)
    │
    ├─▶ Neon Connection Pool
    │   (Serverless, auto-scaling)
    │
    └─▶ Redis (Shared cache)
```

### 9.2 Session Isolation
- Each session runs independently
- No cross-session data sharing
- Neon JSONB for flexible evaluation and metadata storage

## 10. Security Architecture

### 10.1 Credential Management
- Environment variables for secrets
- No hardcoded API keys
- Separate credentials per environment

### 10.2 Data Protection
- Neon SSL-encrypted connections (`sslmode=require`)
- AWS S3 bucket encryption
- Input validation on all API calls

### 10.3 Access Control
- LiveKit API authentication
- Neon connection string with embedded credentials
- Participant context tracking

## 11. Storage Architecture

### Neon Schema (7 tables)

```sql
doctors (id, name, specialty, department, phone, email, ...)
availability (id, doctor_id, day_of_week, start_time, end_time, ...)
leave_tracker (id, doctor_id, start_date, end_date, status, ...)
bookings (id, booking_id, patient_name, patient_phone, doctor_id, date, time, status, ...)
today_visiting (id, doctor_id, visit_date, available_slots, ...)
session_history (id, session_id, patient_phone, summary, evaluation JSONB, ...)
session_cost (id, session_id, stt_cost, llm_cost, tts_cost, total_cost, ...)
```

### Redis Keys
```
session:{session_id} → {session_id, conversation_history}
TTL: 7200s (2 hours)
```

---

**Version:** 2.0
**Last Updated:** July 5, 2026
