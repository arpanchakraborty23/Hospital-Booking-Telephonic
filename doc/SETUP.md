# Hospital Voice Agent - Setup Guide

Complete step-by-step guide to set up and run the Hospital Voice Agent project.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Neon Database Setup](#neon-database-setup)
4. [Redis Setup (Optional)](#redis-setup-optional)
5. [Environment Variables](#environment-variables)
6. [Running the Application](#running-the-application)
7. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **OS:** Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **CPU:** 2 cores minimum
- **RAM:** 4GB minimum (8GB recommended)
- **Disk Space:** 2GB available

### Software Requirements
- **Python:** 3.14 or higher
- **Git:** Latest version
- **Docker & Docker Compose:** For Redis (optional)

## Quick Start

```bash
# 1. Clone
git clone <repository-url>
cd QI_Hospital_Assitant

# 2. Virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -e .

# 4. Configure
cp .env.example .env
# Edit .env and add NEON_DATABASE_URL + API keys

# 5. Start Redis (optional)
docker compose up -d

# 6. Push schema to Neon
psql "$(grep NEON_DATABASE_URL .env | cut -d= -f2-)" -f init.sql

# 7. Run
python main.py
```

## Neon Database Setup

Neon is a serverless PostgreSQL platform — zero infrastructure to manage.

### Step 1: Create a Neon Account

Go to [console.neon.tech](https://console.neon.tech) and sign up.

### Step 2: Create a Project

1. Click **Create a project**
2. Name: `hospital-voice-agent`
3. Region: Choose closest to your users (e.g., `US East`)
4. Click **Create**

### Step 3: Get Connection String

1. Go to **Project Dashboard** → **Connection Details**
2. Copy the **PSL connection string**:
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. Add it to your `.env` file as `NEON_DATABASE_URL`

### Step 4: Apply Schema

You have two options:

**Option A — psql (CLI):**
```bash
# Install psql if you don't have it
# Then run:
psql "$NEON_DATABASE_URL" -f init.sql
```

**Option B — Neon SQL Editor:**
1. Go to **Project Dashboard** → **SQL Editor**
2. Copy-paste the entire `init.sql` content
3. Click **Run**

This creates all 7 tables:
- `doctors` — doctor profiles by department
- `availability` — weekly recurring slots per doctor
- `leave_tracker` — doctor time-off with approval status
- `bookings` — appointment records with status tracking
- `today_visiting` — daily visiting doctor roster
- `session_history` — per-call history with evaluation JSONB
- `session_cost` — per-call cost breakdown

## Redis Setup (Optional)

Redis is used for caching active session data. If unavailable, sessions still work without persistence.

### Docker (recommended):
```bash
docker compose up -d
```

### Native install:
**macOS:** `brew install redis && brew services start redis`
**Linux:** `sudo apt install redis-server && sudo systemctl start redis`
**Windows:** Use Docker or WSL

## Environment Variables

### Required

```env
# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=<your-api-key>
LIVEKIT_API_SECRET=<your-api-secret>

# Neon (serverless PostgreSQL) — copy from Neon dashboard
NEON_DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require

# AI providers
DEEPGRAM_API_KEY=<your-deepgram-key>
CARTESIA_API_KEY=<your-cartesia-key>
CARTESIA_MODEL_ID=9626c31c-bec5-4cca-baa8-f8ba9e84c8bc
OPENAI_API_KEY=<your-openai-key>
```

### Optional

```env
# Redis (omit to disable caching)
REDIS_URL=redis://localhost:6379/0

# AWS S3 for recordings
AWS_BUCKET_NAME=hospital-recordings
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
```

## Running the Application

```bash
# Start Redis (optional)
docker compose up -d

# Run the agent
python main.py
```

The agent connects to LiveKit and waits for incoming calls. All session data is cached in Redis and persisted to Neon at call end.

## Troubleshooting

### Neon Connection Issues

**1. Verify the connection string:**
```bash
psql "$NEON_DATABASE_URL" -c "SELECT 1"
```

**2. Check if schema exists:**
```bash
psql "$NEON_DATABASE_URL" -c "\dt"
```
Should show: doctors, availability, leave_tracker, bookings, today_visiting, session_history, session_cost

**3. Common errors:**
- `password authentication failed` → Check username/password in DSN
- `SSL required` → Ensure `?sslmode=require` is appended
- `connection refused` → Check Neon project is active (not paused)

### Redis Issues

**1. Check if Redis is running:**
```bash
redis-cli ping  # Should return PONG
```

**2. Agent still works without Redis** — only active session caching is lost.

### Agent Issues

- Run with `python main.py` and check stdout logs
- Ensure all API keys are valid
- Verify LiveKit credentials and server URL

## Zero-Infrastructure Mode

Since Neon is serverless and Redis is optional, you can run the entire system with:

```bash
# 1. Set NEON_DATABASE_URL in .env
# 2. Skip docker compose entirely
# 3. Run the agent
python main.py
```

No Docker, no local databases, no infrastructure management needed.
