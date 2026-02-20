# CLAUDE.md — Meister-Eder

This file provides context for AI assistants working in this repository.

## Project Overview

**Meister-Eder** is an AI-powered conversational registration system for **Spielgruppe Pumuckl**, a playgroup run by Familienverein Fällanden (Fällanden, Switzerland). It replaces a static Google Forms workflow with an AI agent that guides parents through child registration via natural conversation.

**Current state**: Greenfield project — no application code exists yet. All work to date is specification and scoping documentation.

**Primary stakeholders**:
- Playgroup admin (Markus Graf, Andrea Sigrist, Barbara Gross) — receives registrations, maintains knowledge base
- Parents — interact with the agent to register their child and ask questions

---

## Repository Structure

```
Meister-Eder/
├── README.md                          # Minimal placeholder
├── CLAUDE.md                          # This file
├── LICENSE
├── openspec/
│   ├── config.yaml                    # OpenSpec schema config (spec-driven)
│   └── changes/
│       └── define-project-scope/      # Completed scoping change (all tasks done)
│           ├── .openspec.yaml         # Change metadata
│           ├── proposal.md            # Why/What/Capabilities
│           ├── design.md              # Architecture decisions, risks, open questions
│           ├── tasks.md               # Implementation task breakdown (all checked)
│           ├── specs/                 # Formal capability specifications
│           │   ├── conversational-registration/spec.md
│           │   ├── chat-interface/spec.md
│           │   ├── email-channel/spec.md
│           │   ├── registration-data-store/spec.md
│           │   ├── registration-notifications/spec.md
│           │   └── service-knowledge-base/spec.md
│           └── content/               # Reference content and domain data
│               ├── agent-personality.md
│               ├── channel-config.md
│               ├── conversation-flow.md
│               ├── export-formats.md
│               ├── notification-template.md
│               ├── registration-fields.md
│               ├── registration-schema.json
│               ├── release-priorities.md
│               ├── sample-responses.md
│               ├── validation-rules.md
│               └── knowledge-base/
│                   ├── README.md
│                   ├── faq.md
│                   ├── fees.md
│                   ├── regulations.md
│                   ├── schedule.md
│                   ├── Reglement-Spielgruppe-2024.pdf
│                   └── Tarifliste-Spielgruppe-2024_2025.pdf
├── .claude/
│   ├── commands/opsx/                 # Claude Code slash commands for OpenSpec workflow
│   └── skills/                        # Claude skill implementations
└── .gemini/
    ├── commands/opsx/                 # Gemini CLI commands for OpenSpec workflow
    └── skills/                        # Gemini skill implementations
```

---

## Development Workflow (OpenSpec)

This project uses the **OpenSpec spec-driven workflow**. Changes are structured as artifacts before implementation begins.

### Key Commands (Claude Code)

| Command | Purpose |
|---------|---------|
| `/opsx:new` | Start a new change (creates proposal → design → specs → tasks) |
| `/opsx:continue` | Create the next artifact in the workflow |
| `/opsx:ff` | Fast-forward: create all artifacts at once |
| `/opsx:apply` | Implement tasks from a change |
| `/opsx:verify` | Verify implementation matches specs |
| `/opsx:archive` | Archive a completed change |
| `/opsx:explore` | Explore/research mode before committing to a change |

### Artifact Sequence (spec-driven schema)

1. **proposal.md** — Why/what/capabilities (non-technical)
2. **design.md** — Architecture decisions, risks, goals/non-goals
3. **specs/** — Formal `ADDED/MODIFIED/REMOVED` requirements per capability
4. **tasks.md** — Checklist of implementation tasks
5. Archive after implementation is verified

### Changes Directory

Each change lives in `openspec/changes/<change-name>/`. The only current change is `define-project-scope` (status: **all tasks complete**).

---

## System Architecture (Designed, Not Yet Built)

### Core Design Decisions

1. **Channel-agnostic core agent** with adapter layer — the conversation logic is separate from channel-specific handling (email vs. chat). This enables adding Telegram/WhatsApp later without touching the core.

2. **LLM + structured schema** — LLM handles natural language; a structured JSON schema validates all required fields before submission. Pure LLM was rejected (risk of missing fields); pure rule-based was rejected (too rigid).

3. **Knowledge base as editable files** — Service info (fees, regulations, FAQs) stored as markdown files that admins can update without code changes.

4. **Structured JSON storage** — Completed registrations stored as JSON records validated against a schema. CSV/JSON export for Google Sheets compatibility.

5. **Email state via thread tracking** — Email conversations maintained via `In-Reply-To`/`References` headers. No timeout (async by nature); 1-month retention for incomplete registrations.

### Capabilities

| Capability | Description |
|------------|-------------|
| `conversational-registration` | AI agent guides parents through registration one question at a time |
| `service-knowledge-base` | Markdown files the agent queries to answer questions about fees, schedule, policies |
| `email-channel` | Email-based conversation; thread-tracked state; async |
| `chat-interface` | Web-based real-time chat; mobile-responsive; session-based state |
| `registration-data-store` | Structured JSON storage with schema validation; CSV/JSON export |
| `registration-notifications` | Email notifications to admin on completion; routed by playgroup type |

---

## Domain Knowledge

### Playgroup Details

**Organization**: Familienverein Fällanden
**Playgroup name**: Spielgruppe Pumuckl
**Location**: Sunnetalstrasse 4, 8117 Fällanden, Switzerland

**Indoor Playgroup** (Innenspielgruppe)
- Days: Monday, Wednesday, Thursday — 9:00–11:30
- Age: 2.5+ years
- Group size: 8–11 children
- Leaders: Andrea Sigrist (079 674 99 92, andrea.sigrist@gmx.net) & Kübra Karatas

**Outdoor Forest Playgroup** (Waldspielgruppe)
- Days: Monday — 9:00–14:00 (includes snack & lunch)
- Age: 3+ years
- Group size: max 10 children
- Leader: Barbara Gross (078 761 19 64, baba.laeubli@gmail.com)

**Administration**: Markus Graf (079 261 16 37, spielgruppen@familien-verein.ch)

### Fees (2024/2025)

| Playgroup | Frequency | Monthly Fee |
|-----------|-----------|-------------|
| Indoor | 1x/week | CHF 130 |
| Indoor | 2x/week | CHF 260 |
| Indoor | 3x/week | CHF 390 |
| Outdoor | 1x/week (Mon only) | CHF 250 |

- One-time registration fee: CHF 80 (first year); CHF 80 craft materials from second year
- Indoor only: CHF 50 refundable cleaning deposit
- Sibling discount: 10% per additional child
- July and August: fee-free

### Registration Schema

All fields are required (13 total):

```json
{
  "child": {
    "fullName": "string (min 2 chars)",
    "dateOfBirth": "YYYY-MM-DD",
    "specialNeeds": "string or 'None'"
  },
  "parentGuardian": {
    "fullName": "string",
    "streetAddress": "string",
    "postalCode": "4-digit Swiss code",
    "city": "string",
    "phone": "string",
    "email": "valid email"
  },
  "emergencyContact": {
    "fullName": "string",
    "phone": "string"
  },
  "booking": {
    "playgroupTypes": ["indoor" | "outdoor"],
    "selectedDays": [{"day": "monday|wednesday|thursday", "type": "indoor|outdoor"}]
  },
  "metadata": {
    "submittedAt": "ISO 8601",
    "channel": "email | chat",
    "conversationId": "string (optional)"
  }
}
```

**Booking constraints**:
- Indoor: Monday, Wednesday, or Thursday
- Outdoor: Monday only
- Children can register for one, both, or any day combination

**Age validation**: 2–5 years at time of registration

### Conversation Flow

```
1. Greeting & intent detection
2. Child information (name → DOB → age validation)
3. Playgroup selection (type → days)
4. Special needs
5. Parent/guardian contact (name, address, phone, email)
6. Emergency contact (name, phone)
7. Confirmation summary → corrections if needed
8. Completion (fee summary, contact info)
```

At any point, parents can ask questions — agent answers from knowledge base, then returns to registration.

### Language

- **Default language: German** (informal "du", Swiss context)
- Detect parent's language automatically; respond consistently in same language
- Both German and English fully supported

### Admin Notification Routing

| Registration type | Notification recipients |
|-------------------|------------------------|
| Indoor only | Andrea Sigrist + CC: Markus Graf |
| Outdoor only | Barbara Gross + CC: Markus Graf |
| Both | Andrea Sigrist + Barbara Gross + CC: Markus Graf |

### Email Channel State

- **Incomplete registration retention**: 1 month
- **Reminder schedule**: Day 3, Day 10, Day 25 (max 3 reminders)
- **Day 30**: Data cleared (no email sent)

### Chat Channel State

- Session-based (browser session); no server-side persistence for incomplete registrations
- For longer breaks, email channel is recommended

---

## Data Export

### CSV format

Filename: `registrations_YYYY-MM-DD.csv` (UTF-8, comma-separated)

Columns: `registration_id`, `submitted_at`, `channel`, `child_name`, `child_dob`, `child_age_years`, `child_age_months`, `special_needs`, `playgroup_types`, `selected_days`, `monthly_fee`, `parent_name`, `parent_address`, `parent_postal_code`, `parent_city`, `parent_phone`, `parent_email`, `emergency_name`, `emergency_phone`

### JSON format

Bulk export wraps records in `{ exportedAt, totalRecords, filters, registrations: [...] }`.

### Export filters

Date range, playgroup type (indoor/outdoor), booking day, channel — combinable.

---

## MVP Release Priorities

All of the following are **must-have** for initial release:

- Chat interface (web, mobile-responsive)
- Email channel (full conversation support)
- Conversational registration (guided AI collection)
- Knowledge base Q&A
- Bilingual support (German + English)
- Registration data storage (structured JSON)
- Admin notifications (routed by playgroup type)
- Email reminders for incomplete registrations (Day 3/10/25)
- Data export (CSV + JSON)

**Out of scope**: Payment processing, calendar integration, parent accounts, mobile app, Telegram/WhatsApp (Phase 2).

---

## Conventions for AI Assistants

1. **No code exists yet.** The scoping phase is complete. The next step is implementation planning and then building.

2. **Read specs before implementing.** All capability specifications are in `openspec/changes/define-project-scope/specs/`. Implement to these requirements.

3. **Domain content is in `content/`.** Agent personality, sample responses, conversation flow, and all knowledge base content is pre-written. Use it — don't invent new fee amounts, contact info, or policies.

4. **Tech stack is undecided.** The design documents deliberately leave the tech stack open. When implementing, choose based on the constraints: the system needs LLM access, email send/receive, a web server, and file-based storage. Document your choices in `openspec/config.yaml`'s context field.

5. **Use OpenSpec workflow for new changes.** Don't add features or refactor without creating a proper change via `/opsx:new`. This ensures all work is spec'd before implementation.

6. **Agent tone is warm and friendly.** Refer to `content/agent-personality.md` for tone guidelines and `content/sample-responses.md` for example responses. The agent should feel like a helpful staff member, not an automated system.

7. **Bilingual by default.** All agent-facing output (messages, responses) must support both German and English. German is the default.

8. **Schema validation is non-negotiable.** Every completed registration must pass JSON schema validation before storage and notification. Incomplete registrations must never trigger admin notifications.

9. **Channel-agnostic core.** Business logic (conversation, validation, storage, notification) must not contain channel-specific code. Channel adapters translate to/from a common message format.

10. **Knowledge base files are admin-editable.** Keep knowledge base content in simple markdown files that a non-technical admin can edit. Never hardcode fee amounts or policy text in application code.
