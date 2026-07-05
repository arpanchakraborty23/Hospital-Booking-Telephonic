# Hospital Voice Agent – AI Receptionist

An AI-powered multilingual voice receptionist for hospital appointment booking, rescheduling, cancellations, and general inquiries — built with LiveKit Agents.

## Overview

This system provides an intelligent hospital receptionist experience through real-time voice conversations. It handles phone calls for:

- **Booking** new appointments
- **Rescheduling** existing appointments
- **Cancelling** appointments
- **Checking** appointment status
- **Emergency** escalation to human agents
- **General inquiries** about doctors, departments, and hospital info

### AI Stack

| Service | Provider | Model | Languages |
|---------|----------|-------|-----------|
| Speech-to-Text | Deepgram | Nova-3 | English, Hindi |
| Speech-to-Text | Sarvam | Saaras v2.5 | Bengali |
| Language Model | Sarvam | sarvam-105b-32k | All |
| LLM Fallback | OpenAI | GPT-4.1 Mini | All |
| Text-to-Speech | Cartesia | Sonic-3 | English, Hindi |
| Text-to-Speech | Sarvam | Bulbul v3 | Bengali |

## Quick Start

### Prerequisites

- Python 3.14+
- A [Neon](https://neon.tech) database (free serverless PostgreSQL)
- Redis (optional — `docker compose up -d` for local)
- API keys for: Deepgram, Sarvam AI, Cartesia TTS, LiveKit

### 1. Clone & Setup

```bash
git clone <repository-url>
cd QI_Hospital_Assitant

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -e .
```

### 2. Create Neon Database

1. Go to [console.neon.tech](https://console.neon.tech) and create a project
2. Copy the connection string (it looks like `postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require`)
3. Run the schema in the **Neon SQL Editor** or via `psql`:
   ```bash
   psql <connection-string> -f init.sql
   ```

### 3. Start Redis (optional, for session caching)

```bash
docker compose up -d
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Required variables:

```env
# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=<your-api-key>
LIVEKIT_API_SECRET=<your-api-secret>

# Neon (serverless PostgreSQL)
NEON_DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# AI Providers
DEEPGRAM_API_KEY=<your-deepgram-key>
CARTESIA_API_KEY=<your-cartesia-key>
OPENAI_API_KEY=<your-openai-key>
```

### 5. Run the Agent

```bash
python main.py
```

## Architecture

```
┌──────────────────────────────────────┐
│         Voice I/O (Phone/App)        │
└────────────────┬─────────────────────┘
                 │ WebRTC
                 ▼
┌──────────────────────────────────────┐
│        LiveKit Agent Server          │
│  ┌──────────┐  ┌──────────┐         │
│  │  Agent   │  │ Session  │         │
│  │ (Riya)   │  │ Manager  │         │
│  └────┬─────┘  └────┬─────┘         │
└───────┼──────────────┼───────────────┘
        │              │
┌───────▼──────────────▼───────────────┐
│         AI Services Layer            │
│  Deepgram → Sarvam/OpenAI → Cartesia │
└───────┬──────────────┬───────────────┘
        │              │
┌───────▼──────────────▼───────────────┐
│         Data Layer                   │
│  ┌──────────────┐  ┌────────────┐   │
│  │ Neon (Neon)  │  │   Redis    │   │
│  │ (serverless) │  │ (cache)    │   │
│  └──────────────┘  └────────────┘   │
└──────────────────────────────────────┘
```

### Storage Strategy

| Data | Store | Why |
|------|-------|-----|
| Active conversation history | Redis (2h TTL) | Fast read/write during call |
| Completed session history | Neon | Durable persistence with evaluation |
| Session cost per call | Neon | Cost tracking per AI service |
| Doctors & availability | Neon | Schedule management |
| Appointments (bookings) | Neon | CRUD for patient appointments |

## Database Schema

### `doctors`
Stores doctor profiles linked to departments.

### `availability`
Weekly recurring slots per doctor (day_of_week, start/end time).

### `leave_tracker`
Doctor time-off records with approval status.

### `bookings`
Appointment records with status (confirmed / rescheduled / cancelled / completed / no_show).

### `today_visiting`
Which doctors are available today, max slots, remaining availability.

### `session_history`
Per-call history with conversation summary, evaluation JSONB, duration, turn count, category, resolved flag.

### `session_cost`
Per-call cost breakdown: STT seconds, LLM tokens, TTS characters, total cost per call.

## Conversation Flow

The agent supports 6 distinct conversation paths:

| # | Branch | Description |
|---|--------|-------------|
| 1 | **Book Appointment** | Select dept/doctor → pick slot → confirm patient info → book → send confirmation |
| 2 | **Reschedule** | Lookup by phone → show current → pick new slot → reschedule → confirm |
| 3 | **Cancel** | Lookup by phone → confirm intent → cancel → send confirmation |
| 4 | **Check Status** | Lookup by phone → display doctor/date/time/status |
| 5 | **Emergency** | Immediate escalation to human agent |
| 6 | **General Inquiry** | Doctor info, departments, visiting hours, location, fees |

All non-emergency flows end with "Anything else?" — looping back or closing with a farewell.

See [doc/conversation_flow.md](doc/conversation_flow.md) for the visual flowchart.

## Project Structure

```
QI_Hospital_Assitant/
├── main.py                      # Agent server entry point
├── pyproject.toml               # Dependencies
├── docker-compose.yml           # Redis container (Neon is serverless)
├── init.sql                     # Database schema
├── Dockerfile                   # App container
├── .env.example                 # Environment template
├── monitoring/                  # Observability config
│   ├── prometheus.yml           # Prometheus scrape config
│   ├── loki-config.yml          # Loki log storage config
│   ├── promtail-config.yml      # Log shipping config
│   └── grafana-datasources.yml  # Pre-configured data sources
├── doc/
│   ├── conversation_flow.md     # Flowchart (Mermaid)
│   ├── conversation_flow.png    # Flowchart (image)
│   ├── ARCHITECTURE.md          # System design
│   ├── COMPONENTS.md            # Component reference
│   ├── README.md                # Documentation index
│   └── SETUP.md                 # Installation guide
├── src/
│   ├── prompt/                  # AI system prompts
│   │   ├── english.py
│   │   ├── hindi.py
│   │   └── bengali.py
│   ├── constants/               # Configuration classes
│   ├── services/                # Business logic
│   │   ├── database.py          # Neon (asyncpg via DSN)
│   │   ├── session.py           # Session lifecycle
│   │   ├── redis_client.py      # Redis cache wrapper
│   │   └── hospital_data.py     # Mock appointment data
│   ├── voice_agent/             # Agent implementations
│   │   ├── agents.py            # ExiaEnglish/Hindi/Bengali
│   │   ├── base_agent.py        # Base agent class
│   │   ├── hospital_tools.py    # LLM function tools
│   │   └── metrics.py           # Performance tracking
│   └── utils/                   # Utilities
└── templates/
    └── conversation_setup.html  # Frontend test page
```

## Production Deployment

### Agent Server Options

The agent uses production-ready defaults from LiveKit Agents SDK:

| Option | Value | Purpose |
|--------|-------|---------|
| `load_threshold` | `0.7` | Spawns new workers when CPU > 70% |
| `drain_timeout` | `3600s` | Graceful shutdown up to 1 hour |
| `num_idle_processes` | `0` (dev) / `4` (prod) | Pre-warmed standby workers |
| `prometheus_port` | `8001` | Built-in `/metrics` endpoint (no custom server needed) |
| `host` / `port` | `0.0.0.0:8081` | Health check endpoint |

Credentials (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`) are read automatically from the environment — **do not hardcode them** in the constructor. LiveKit Cloud injects them at runtime.

### Start the full stack

```bash
# Start Redis, Prometheus, Grafana, Loki, Promtail
docker compose up -d

# Run the agent (on host, not in Docker, so Prometheus can scrape it)
python main.py
```

> Prometheus scrapes the agent at `host.docker.internal:8001/metrics`.

### Build agent container (alternative)

```bash
docker build -t hospital-voice-agent .
docker run -d \
  --name hospital-agent \
  --env-file .env \
  --network host \
  hospital-voice-agent
```

> **Neon** is serverless — no Docker infrastructure needed. Just set `NEON_DATABASE_URL` in `.env`.

## Multilingual Support

The agent auto-detects the caller's language and responds in the same language:

| Language | STT | LLM | TTS |
|----------|-----|-----|-----|
| English | Deepgram Nova-3 (en-IN) | Sarvam 105B / GPT-4.1 Mini | Cartesia Sonic-3 |
| Hindi | Deepgram Nova-3 (hi-Latn) | Sarvam 105B / GPT-4.1 Mini | Cartesia Sonic-3 |
| Bengali | Sarvam Saaras v2.5 | Sarvam 105B / GPT-4.1 Mini | Sarvam Bulbul v3 |

## API Tools (LLM-callable)

The agent exposes 9 function tools that the LLM can invoke:

| Tool | Purpose |
|------|---------|
| `check_availability` | Get open slots by department/doctor/date |
| `book_appointment` | Book with patient details |
| `reschedule_appointment` | Change date/time of existing |
| `cancel_appointment` | Cancel by appointment ID |
| `lookup_appointment` | Find appointments by phone |
| `get_departments` | List all departments |
| `get_doctors` | List doctors in a department |
| `send_confirmation` | Send WhatsApp/SMS |
| `escalate_to_human` | Transfer to human agent |

## Performance Metrics

| Component | Typical Range | Target |
|-----------|---------------|--------|
| EOU Delay (VAD) | 200-600ms | < 500ms |
| LLM TTFT | 100-500ms | < 300ms |
| TTS TTFB | 50-200ms | < 100ms |
| **Total** | **350-1300ms** | **< 900ms** |

## Observability

The project includes a full observability stack via Docker:

| Service | Port | Purpose |
|---------|------|---------|
| **Prometheus** | `:9090` | Metrics collection from the agent (`/metrics` on port `8001`) |
| **Grafana** | `:3000` | Dashboards for metrics + logs (admin/admin) |
| **Loki** | `:3100` | Log aggregation via Promtail (Docker log driver) |
| **Promtail** | `:9080` | Ships container logs to Loki |

### Start the stack

```bash
docker compose up -d
```

This starts Redis, Prometheus, Loki, Promtail, and Grafana. The agent exposes Prometheus metrics on port `8001` via the **SDK's built-in endpoint** (no custom server needed).

### SDK Built-in Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `lk_agents_proc_initialize_duration_seconds` | Histogram | Process init time |
| `lk_agents_active_job_count` | Gauge | Active sessions across all workers |
| `lk_agents_child_process_count` | Gauge | Total child processes |
| `lk_agents_worker_load` | Gauge | Worker CPU load (0-1) |

### Custom Application Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `hospital_active_sessions` | Gauge | Currently active calls |
| `hospital_total_sessions_total` | Counter | Cumulative session count |
| `hospital_stt_latency_seconds` | Histogram | STT duration |
| `hospital_llm_latency_seconds` | Histogram | LLM time-to-first-token |
| `hospital_tts_latency_seconds` | Histogram | TTS time-to-first-byte |

### Access Grafana

1. Open `http://localhost:3000`
2. Login: `admin` / `admin`
3. Data sources **Prometheus** and **Loki** are pre-configured
4. Explore metrics in **Explore** tab or create custom dashboards

## License

Proprietary and confidential.
