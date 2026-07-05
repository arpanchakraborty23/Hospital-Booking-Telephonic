# Documentation Index

Welcome to the Hospital Voice Agent documentation.

## Documentation Files

### 1. conversation_flow.md
Conversation Flow Diagram

Mermaid flowchart showing the complete 6-branch conversation flow:
- Book, Reschedule, Cancel, Check Status, Emergency, General Inquiry
- Welcome greeting and closing script
- "Anything else?" loop for non-emergency paths

### 2. COMPONENTS.md
Detailed Component Reference

Complete documentation of all components and services:
- Voice Agent Components (ExiaEnglish, ExiaHindi, ExiaBengali)
- Session Management (SessionManager)
- Database Services (NeonServices, NeonPool)
- Metrics Collection (MetricsCollector)
- Hospital Tools (HospitalTools)
- Prompt System (english.py, hindi.py, bengali.py)

### 3. ARCHITECTURE.md
System Design & Architecture

High-level architectural overview:
- Layered architecture with async pipelines
- Design patterns (Factory, Singleton, Observer, Strategy)
- Data flow diagrams (voice + persistence)
- Neon schema design (7 tables: doctors, availability, bookings, etc.)
- Redis caching strategy
- Error handling with graceful degradation

### 4. SETUP.md
Installation & Configuration Guide

Step-by-step setup guide:
- Neon serverless database + Redis caching
- Environment configuration
- Running the agent

---

## Quick Navigation

### I want to...

**...see the conversation flow**
Start with conversation_flow.md

**...understand how a specific component works**
Check COMPONENTS.md

**...know why the system is designed this way**
Read ARCHITECTURE.md

**...set up the project**
Read SETUP.md (or root README.md)

---

## Documentation Structure

doc/
|- README.md              (Documentation Index)
|- conversation_flow.md   (Conversation Flow Diagram)
|- conversation_flow.png  (Conversation Flow Diagram - image)
|- COMPONENTS.md          (Component Reference)
|- ARCHITECTURE.md        (System Design)
|- SETUP.md              (Installation Guide)

---

Documentation Version: 2.0
Last Updated: July 5, 2026
