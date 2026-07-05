# Hospital Voice Agent – Conversation Flow

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'background': '#ffffff',
    'fontFamily': 'arial, sans-serif',
    'fontSize': '14px',
    'primaryColor': '#f0f4f8',
    'primaryTextColor': '#1a1a2e',
    'primaryBorderColor': '#c0c8d4',
    'lineColor': '#8892a4',
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#f8fafc'
  },
  'flowchart': {
    'curve': 'basis',
    'padding': 20,
    'nodeSpacing': 80,
    'rankSpacing': 100
  }
}}%%

flowchart TB
    classDef welcome fill:#1a1a2e,color:#ffffff,stroke:#1a1a2e,stroke-width:2px,rx:12,ry:12,font-weight:bold
    classDef decision fill:#fff8e1,color:#5d4037,stroke:#f9a825,stroke-width:1.5px,rx:10,ry:10,font-style:italic
    classDef endNode fill:#f5f5f5,color:#333333,stroke:#999999,stroke-width:1.5px,rx:10,ry:10
    classDef subStyle fill:#f8fafc,color:#333333,stroke:#c0c8d4,stroke-width:1px,rx:8,ry:8

    subgraph MAIN["Main Flow"]
        W([""]):::welcome
        W1["<b>Welcome to ABC Hospital</b><br/>Thank you for calling.<br/><i>How may I help you today?</i>"]:::welcome
    end

    W --> W1

    %% Style definitions for each branch
    classDef blueBranch fill:#e3f2fd,color:#0d47a1,stroke:#1976d2,stroke-width:2px,rx:10,ry:10
    classDef greenBranch fill:#e8f5e9,color:#1b5e20,stroke:#388e3c,stroke-width:2px,rx:10,ry:10
    classDef redBranch fill:#ffebee,color:#b71c1c,stroke:#d32f2f,stroke-width:2px,rx:10,ry:10
    classDef purpleBranch fill:#f3e5f5,color:#4a148c,stroke:#7b1fa2,stroke-width:2px,rx:10,ry:10
    classDef orangeBranch fill:#fff3e0,color:#e65100,stroke:#f57c00,stroke-width:2px,rx:10,ry:10
    classDef cyanBranch fill:#e0f7fa,color:#006064,stroke:#0097a7,stroke-width:2px,rx:10,ry:10

    %% Branch selection nodes
    B1["📅 1. Book New Appointment"]:::blueBranch
    B2["🔄 2. Reschedule Appointment"]:::greenBranch
    B3["❌ 3. Cancel Appointment"]:::redBranch
    B4["📋 4. Check Appointment Status"]:::purpleBranch
    B5["🚨 5. Emergency / Urgent Care"]:::orangeBranch
    B6["ℹ️ 6. General Inquiry"]:::cyanBranch

    W1 --> B1
    W1 --> B2
    W1 --> B3
    W1 --> B4
    W1 --> B5
    W1 --> B6

    %% ==================== 1. BOOK APPOINTMENT (Blue) ====================
    subgraph BOOK["1. Book New Appointment"]
        direction TB
        A1["I'd be happy to help you book an appointment."]:::blueBranch
        A1Q["May I know which doctor or department<br/>you would like to visit?"]:::blueBranch
        A1R["Caller provides department"]
        A2["What date would you prefer?"]:::blueBranch
        A2R["Caller provides date"]
        A3["What time would you prefer?<br/>Morning, Afternoon, or Evening?"]:::blueBranch
        A4["Let me check the available slots."]:::blueBranch
        A5["I found these available appointments:<br/><br/>• Dr. Sharma — 10:00 AM<br/>• Dr. Sharma — 11:30 AM<br/>• Dr. Gupta — 2:00 PM"]:::blueBranch
        A6["Caller selects slot"]
        A7["Perfect.<br/>Your appointment has been booked."]:::blueBranch
        A8["<b>Appointment Details</b><br/><br/>• Doctor<br/>• Department<br/>• Date<br/>• Time"]:::blueBranch
        A9["I've sent the confirmation to<br/>your registered mobile number."]:::blueBranch
    end

    B1 --> A1 --> A1Q --> A1R --> A2 --> A2R --> A3 --> A4 --> A5 --> A6 --> A7 --> A8 --> A9

    %% Decision after booking
    D1{"Anything else<br/>I can help you with?"}:::decision
    A9 --> D1
    D1 -->|Yes| W1
    D1 -->|No| END1

    %% ==================== 2. RESCHEDULE (Green) ====================
    subgraph RESCHEDULE["2. Reschedule Appointment"]
        direction TB
        R1["I can help you reschedule your appointment."]:::greenBranch
        R1Q["Please provide your phone number<br/>or Booking ID."]:::greenBranch
        R1R["Caller provides details"]
        R2["Let me find your appointment."]:::greenBranch
        R3["I found your appointment.<br/><br/>Doctor: ...<br/>Date: ...<br/>Time: ..."]:::greenBranch
        R4["What new date would you prefer?"]:::greenBranch
        R5["Here are the available time slots."]:::greenBranch
        R6["Caller chooses new slot"]
        R7["Great.<br/>Your appointment has been<br/>successfully rescheduled."]:::greenBranch
        R8["Your updated appointment details are..."]:::greenBranch
        R9["I've sent the updated confirmation."]:::greenBranch
    end

    B2 --> R1 --> R1Q --> R1R --> R2 --> R3 --> R4 --> R5 --> R6 --> R7 --> R8 --> R9

    D2{"Anything else<br/>I can help you with?"}:::decision
    R9 --> D2
    D2 -->|Yes| W1
    D2 -->|No| END1

    %% ==================== 3. CANCEL (Red) ====================
    subgraph CANCEL["3. Cancel Appointment"]
        direction TB
        C1["I can help you cancel your appointment."]:::redBranch
        C1Q["Please provide your phone number<br/>or Booking ID."]:::redBranch
        C1R["Caller provides details"]
        C2["Let me locate your appointment."]:::redBranch
        C3["I found your appointment.<br/><br/>Doctor: ...<br/>Date: ...<br/>Time: ..."]:::redBranch
        C4["Are you sure you'd like to<br/>cancel this appointment?"]:::redBranch
        C4D{"Caller confirms?"}:::decision
        C5["Your appointment has been<br/>cancelled successfully."]:::redBranch
        C6["A cancellation confirmation has been<br/>sent to your registered mobile number."]:::redBranch
    end

    B3 --> C1 --> C1Q --> C1R --> C2 --> C3 --> C4 --> C4D
    C4D -->|Yes| C5 --> C6
    C4D -->|No| W1

    D3{"Anything else<br/>I can help you with?"}:::decision
    C6 --> D3
    D3 -->|Yes| W1
    D3 -->|No| END1

    %% ==================== 4. CHECK STATUS (Purple) ====================
    subgraph STATUS["4. Check Appointment Status"]
        direction TB
        S1["I'll check your appointment details."]:::purpleBranch
        S1Q["Please provide your phone number<br/>or Booking ID."]:::purpleBranch
        S1R["Caller provides details"]
        S2["One moment while I retrieve<br/>your appointment."]:::purpleBranch
        S3["<b>Your Appointment Details</b><br/><br/>• Doctor<br/>• Department<br/>• Date<br/>• Time<br/>• Status"]:::purpleBranch
    end

    B4 --> S1 --> S1Q --> S1R --> S2 --> S3

    D4{"Anything else<br/>I can help you with?"}:::decision
    S3 --> D4
    D4 -->|Yes| W1
    D4 -->|No| END1

    %% ==================== 5. EMERGENCY (Orange) ====================
    subgraph EMERGENCY["5. Emergency / Urgent Care"]
        direction TB
        E1["If this is a medical emergency,<br/>I'll connect you immediately."]:::orangeBranch
        E2["Please stay on the line while<br/>I transfer your call."]:::orangeBranch
        E3["Call Connected"]:::orangeBranch
        E4["All emergency representatives are currently<br/>assisting other patients.<br/>Please remain on the line."]:::orangeBranch
        E5["<b>Your safety is our priority.</b>"]:::orangeBranch
    end

    B5 --> E1 --> E2
    E2 -->|Agent Available| E3
    E2 -->|Agent Unavailable| E4 --> E5

    %% ==================== 6. GENERAL INQUIRY (Cyan) ====================
    subgraph INQUIRY["6. General Inquiry / Doctor Information"]
        direction TB
        I1["What information can<br/>I help you with today?"]:::cyanBranch
        I2["<b>Examples:</b><br/><br/>• Doctor Information<br/>• Department Information<br/>• Visiting Hours<br/>• Hospital Location<br/>• Consultation Fees<br/>• Facilities"]:::cyanBranch
        I3["AI searches information"]:::cyanBranch
        I4["AI provides answer"]:::cyanBranch
    end

    B6 --> I1 --> I2 --> I3 --> I4

    D6{"Is there anything else<br/>I can help you with?"}:::decision
    I4 --> D6
    D6 -->|Yes| W1
    D6 -->|No| END1

    %% ==================== GLOBAL ENDING ====================
    END1["<b>Thank you for calling ABC Hospital.</b><br/><br/>We wish you good health.<br/>Have a wonderful day."]:::endNode
```

## Legend

| Color | Branch |
|-------|--------|
| 🟦 Blue | Book New Appointment |
| 🟩 Green | Reschedule Appointment |
| 🟥 Red | Cancel Appointment |
| 🟪 Purple | Check Appointment Status |
| 🟧 Orange | Emergency / Urgent Care |
| 🟦 Cyan | General Inquiry / Doctor Information |
