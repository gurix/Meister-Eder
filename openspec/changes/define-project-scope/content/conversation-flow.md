# Registration Conversation Flow

## Overview

The agent guides parents through registration in a natural conversation, collecting information in a logical sequence while allowing for questions and interruptions.

## Main Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ 1. GREETING & INTENT                │
│ "Hi! I can help you register your   │
│ child or answer questions about     │
│ our playgroups. What would you      │
│ like to do?"                        │
└─────────────────────────────────────┘
  │
  ├── [Question about service] → Answer from knowledge base → Return
  │
  ▼
┌─────────────────────────────────────┐
│ 2. CHILD INFORMATION                │
│ - Child's full name                 │
│ - Date of birth                     │
│   → Validate age (2-5 years)        │
│   → If too young/old, inform parent │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 3. PLAYGROUP SELECTION              │
│ "We have two playgroups:"           │
│ - Indoor (Mon/Wed/Thu, 9-11:30)     │
│ - Outdoor Forest (Mon, 9-14:00)     │
│ "Which interests you?"              │
│                                     │
│ → Collect selected type(s)          │
│ → Collect selected days             │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 4. SPECIAL NEEDS                    │
│ "Does your child have any special   │
│ needs, allergies, or medical        │
│ conditions we should know about?"   │
│                                     │
│ → If yes: collect details           │
│ → If no: note "None" and continue   │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 5. PARENT/GUARDIAN CONTACT          │
│ - Full name                         │
│ - Address (street, postal code,     │
│   city) for invoicing               │
│ - Phone number                      │
│ - Email address                     │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 6. EMERGENCY CONTACT                │
│ "Please provide an emergency        │
│ contact (someone other than         │
│ yourself):"                         │
│ - Full name                         │
│ - Phone number                      │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 7. CONFIRMATION                     │
│ Display summary of all collected    │
│ information                         │
│ "Is this correct?"                  │
│                                     │
│ → If corrections needed: go back    │
│ → If confirmed: submit              │
└─────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────┐
│ 8. COMPLETION                       │
│ "Registration complete!"            │
│ - Mention registration fee (80.-)   │
│ - Mention monthly fees              │
│ - Provide contact for questions     │
│ - Thank parent                      │
└─────────────────────────────────────┘
  │
  ▼
END
```

## Branch: Question Handling

At any point during registration, the parent can ask questions:

```
[Parent asks question]
  │
  ▼
┌─────────────────────────────────────┐
│ Query knowledge base                │
│ → Provide answer                    │
│ → Ask: "Would you like to continue  │
│   with registration?"               │
└─────────────────────────────────────┘
  │
  ▼
[Return to previous step in flow]
```

## Branch: Age Validation

```
[Child's DOB collected]
  │
  ▼
┌─────────────────────────────────────┐
│ Calculate age                       │
│                                     │
│ Indoor: 2.5+ years                  │
│ Outdoor: 3+ years                   │
└─────────────────────────────────────┘
  │
  ├── [Age OK] → Continue with playgroup selection
  │
  └── [Age outside range] →
      "Your child is [age]. Our indoor playgroup
      is for children 2.5+ and outdoor is for 3+.
      Would you like to proceed anyway, or contact
      us to discuss?"
```

## Information Collection Order

1. Child name → Personalize conversation
2. Child DOB → Validate eligibility early
3. Playgroup selection → Core booking decision
4. Special needs → Important safety/care info
5. Parent contact → Who to reach
6. Emergency contact → Safety requirement
7. Confirmation → Verify all correct

*Rationale: Child info first (topic of registration), then logistics, then parent details. Special needs before parent info so we can ask follow-up questions while still on child topic.*

---

## Mixed Intent Handling

Parents may combine registration with questions, or switch between intents mid-conversation. The agent should handle this gracefully.

### Scenario 1: Question During Registration

```
[Registration in progress at Step 3]
Parent: "By the way, what are the fees?"

Agent:
1. Acknowledge the question
2. Answer from knowledge base
3. Offer to return to registration
4. Wait for parent response

Example:
"Good question! The indoor playgroup is CHF 130/month and outdoor is
CHF 250/month. There's also a one-time CHF 80 registration fee.

Shall we continue with the registration? We were just about to pick
which days work for you."
```

### Scenario 2: Question-Only Intent (No Registration)

```
Parent: "I just have some questions about the playgroup"

Agent:
1. Acknowledge intent
2. Offer to answer questions
3. Don't push registration unless asked

Example:
"Of course! I'm happy to answer any questions. What would you like
to know?"

[After answering questions]
"Is there anything else you'd like to know? I'm also here if you
decide you'd like to register your child."
```

### Scenario 3: Starting with Question, Then Registration

```
Parent: "How much does it cost?"
Agent: [Answers fee question]
Agent: "Is there anything else you'd like to know?"

Parent: "No, I'd like to register my son"
Agent: "Great! Let's get started. What's your son's name?"
[Begin registration flow from Step 2]
```

### Scenario 4: Multiple Questions at Once

```
Parent: "What are the hours and how much does it cost?"

Agent:
1. Answer both questions together
2. Keep response organized but not overwhelming

Example:
"Happy to help with both!

**Hours:**
- Indoor: Mon/Wed/Thu, 9:00-11:30
- Outdoor: Mon, 9:00-14:00

**Fees:**
- Indoor: CHF 130/month
- Outdoor: CHF 250/month
- Registration: CHF 80 (one-time)

Anything else you'd like to know?"
```

### Scenario 5: Correction During Registration

```
[At confirmation step]
Parent: "Actually, I want to change the days"

Agent:
1. Acknowledge the change request
2. Go back to the relevant step
3. Re-collect only the changed information
4. Return to confirmation

Example:
"No problem! Which days would you like instead?"
[Collect new days]
"Got it. Let me update that... Here's the revised summary: [show again]"
```

### Intent Detection Guidelines

| Parent says... | Intent | Agent response |
|----------------|--------|----------------|
| "I want to register" | Registration | Start registration flow |
| "How much..." / "What are the fees..." | Question | Answer from knowledge base |
| "What time..." / "When is..." | Question | Answer from knowledge base |
| "Register + question in same message" | Mixed | Answer question first, then start registration |
| "Question mid-registration" | Mixed | Answer, then return to registration |
| "Just questions for now" | Question-only | Answer questions, don't push registration |

### Preserving Registration State

When handling questions mid-registration:
- Keep all collected data in memory
- Note which step we paused at
- Return to that exact step after answering
- Don't ask for already-collected information again

---

## Timeout and Resumption Behavior

### Chat Channel

**Session-Based Persistence**

The chat uses browser sessions to maintain state. There is no fixed inactivity timeout—as long as the session exists, the registration can be resumed.

```
[Parent closes browser or tab]
[Session ends]

[Parent returns with same session (e.g., reopens tab)]
Agent: "Welcome back! I still have your registration in progress.
        We were at [current step]. Would you like to continue?"

[Parent returns without session (new browser/device)]
Agent: "Hi! Would you like to start a new registration?"
```

**Data Retention:**
- Incomplete registration data retained for the duration of the browser session
- If session is lost, parent starts fresh (no server-side persistence for chat)
- For longer breaks, recommend email channel

### Email Channel

**No timeout** - email is inherently asynchronous

```
[Parent sends email, agent responds]
[Parent doesn't reply for days/weeks]
[Parent sends another email in the thread]

Agent:
1. Detect existing conversation from email thread
2. Load previously collected data
3. Continue from where we left off

Example:
"Hi again! I still have the registration in progress for Emma.
We just need your emergency contact details to finish up.
Who should we contact in case of emergency?"
```

**Email Data Retention:**
- Registration data retained for **1 month** in email conversations
- After 1 month without response, data cleared

### Reminder Emails

**Automated reminders for incomplete registrations:**

| Timing | Action |
|--------|--------|
| Day 3 | First reminder: "Just checking in—would you like to complete [child name]'s registration?" |
| Day 10 | Second reminder: "We still have your registration saved. Ready to finish?" |
| Day 25 | Final reminder: "Your registration will expire in 5 days. Complete it now or start fresh later." |
| Day 30 | Data cleared (no email sent) |

**Reminder Rules:**
- Only sent for email channel (chat is session-based)
- Stop sending if parent replies or completes registration
- Stop sending if parent explicitly says they're no longer interested
- Maximum 3 reminders per incomplete registration

### Resumption Messages

**Chat - Short absence (< 5 minutes):**
No special message needed, just continue

**Chat - Medium absence (5-30 minutes):**
> "Welcome back! Ready to continue? We were collecting your contact details."

**Chat - Return after session end:**
> "Hi again! I found your earlier registration for [child name]. Would you like to pick up where we left off, or start fresh?"

**Email - After days of silence:**
> "Hi [parent name], just following up on [child name]'s registration. I have most of the details saved—we just need [remaining fields]. Would you like to continue?"

### Incomplete Registration Handling

If a parent abandons registration:
1. Data is NOT submitted to the admin
2. No notification sent for incomplete registrations
3. Data cleared after retention period
4. If parent returns: offer to resume or start fresh

### Privacy Considerations

- Clear incomplete data after retention period
- Don't send reminders to parents who explicitly say they're not interested
- Maximum of 1 reminder email per incomplete registration
