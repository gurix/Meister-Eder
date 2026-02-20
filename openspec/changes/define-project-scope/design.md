## Context

This is a new project for a small business playgroup. Currently, parent registration is handled via Google Forms → Google Sheets → email notification workflow. This project replaces the static form with an AI-powered conversational agent that can both collect registration information and answer questions about the service.

**Current state**: No existing codebase; greenfield project.

**Stakeholders**:
- Playgroup admin (receives registrations, maintains knowledge base)
- Parents (interact with the agent to register and ask questions)

## Goals / Non-Goals

**Goals:**
- Create a conversational AI agent that guides parents through registration naturally
- Enable parents to ask questions about fees, regulations, policies during or outside registration
- Support two communication channels initially: email and web chat
- Store registration data in a structured, processable format
- Notify admin when registrations are completed
- Design for extensibility to add channels (Telegram, WhatsApp) later

**Non-Goals:**
- Payment processing or online booking confirmation
- Calendar/scheduling integration
- Parent accounts or login system
- Mobile app (web chat is mobile-responsive, not a native app)
- Automated approval of registrations (admin still reviews manually)
- Telegram/WhatsApp integration (documented as future extension)

## Decisions

### 1. Conversational AI Approach
**Decision**: Use an LLM-based agent with structured conversation flow and tool access.

**Rationale**: LLMs handle natural language well and can adapt to varied parent responses. A hybrid approach—LLM for conversation, structured schema for data collection—ensures flexibility while guaranteeing all required fields are captured.

**Alternatives considered**:
- Rule-based chatbot: Too rigid, poor handling of unexpected questions
- Pure LLM without structure: Risk of missing required fields

### 2. Channel Architecture
**Decision**: Implement a channel-agnostic core agent with adapter layer for each channel (email, chat).

**Rationale**: Separating the conversation logic from channel-specific handling allows adding new channels without modifying the core agent. Each adapter translates channel messages to/from a common format.

**Alternatives considered**:
- Separate agents per channel: Duplicates logic, harder to maintain consistency
- Single monolithic implementation: Harder to extend with new channels

### 3. Knowledge Base Storage
**Decision**: Store service information (fees, policies, FAQs) as structured documents the agent can query.

**Rationale**: Keeping knowledge separate from agent logic allows the admin to update information without code changes. The agent retrieves relevant context when answering questions.

**Alternatives considered**:
- Hardcoded responses: Inflexible, requires code changes for updates
- Full database: Overkill for relatively static content

### 4. Registration Data Storage
**Decision**: Store completed registrations as structured JSON/records with schema validation.

**Rationale**: Structured format enables export to various systems (spreadsheets, databases) and ensures data consistency. Schema validation catches incomplete registrations before storage.

**Alternatives considered**:
- Direct Google Sheets integration: Maintains familiarity but adds external dependency
- Unstructured storage: Harder to process and validate

### 5. Conversation State Management
**Decision**: Maintain conversation state per session, tracking collected fields and conversation history.

**Rationale**: Registration may span multiple messages (especially via email). State tracking ensures the agent knows what's been collected and what's still needed, and maintains context for follow-up questions.

## Risks / Trade-offs

**LLM reliability** → Implement validation layer that checks all required fields are collected before finalizing registration; agent prompts for missing information.

**Email latency** → Email channel has inherent delays; design conversation to be stateless between messages (state stored server-side, not dependent on immediate response).

**Knowledge base maintenance** → Admin must keep service information updated; provide simple format (markdown or structured files) that's easy to edit without technical skills.

**Channel consistency** → Different channels have different capabilities (email allows attachments, chat is real-time); define common capability baseline and document channel-specific limitations.

**Cost of LLM calls** → Each conversation turn uses LLM tokens; for a small playgroup this is likely negligible, but monitor usage and consider caching common Q&A responses.

## Open Questions

- What specific fields are required for registration? (Need to define the registration schema)
- What information should be included in the knowledge base? (Fees, hours, policies—need content from admin)
- Should email responses be instant (automated) or batched?
- What format does the admin prefer for accessing completed registrations?
- Should the chat interface require any form of identification before starting?
