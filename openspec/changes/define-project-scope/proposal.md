## Why

Managing playgroup registrations through Google Forms is static and impersonal. Parents fill out a long form without guidance, often missing details or providing incomplete information about special needs or booking preferences. This creates manual follow-up work and delays in processing registrations.

An AI-powered conversational registration agent can guide parents through the process naturally, ask clarifying questions when needed, and ensure all required information is collected before submission—improving the experience for parents while reducing administrative overhead.

## What Changes

- **Replace static form registration** with an interactive AI agent that converses with parents
- **Guided data collection**: The agent asks questions one at a time, adapting based on responses (e.g., asking follow-up questions about special needs only when relevant)
- **Context-aware assistant**: During the registration conversation (or independently), parents can ask questions about service fees, regulations, opening hours, policies, and other service-related information—the agent has access to this knowledge and responds naturally within the conversation flow
- **Multi-channel support**: Parents can register via email or a simple web chat interface
- **Structured data output**: All collected information is stored in a structured format for easy processing and integration with existing workflows
- **Email notifications**: Maintain notification flow when new registrations are completed

### Future Extensions
- Telegram bot integration
- WhatsApp integration
- Additional communication channels as needed

## Capabilities

### New Capabilities

- `conversational-registration`: AI agent that guides parents through the registration process via natural conversation, collecting child information (name, age, special needs, booking days) and validating completeness before submission
- `service-knowledge-base`: Curated information about the playgroup (fees, regulations, opening hours, policies, FAQs) that the AI agent can access to answer parent questions during or outside of registration
- `email-channel`: Email-based interaction where parents can register by exchanging emails with the AI agent
- `chat-interface`: Simple web-based chat interface for real-time registration conversations
- `registration-data-store`: Structured storage of registration data in a format suitable for further processing (replacing/complementing Google Sheets workflow)
- `registration-notifications`: Email notifications to admin when a new registration is completed

### Modified Capabilities

<!-- No existing specs to modify - this is a new project -->

## Impact

- **User Experience**: Parents interact with a conversational agent instead of filling out a static form; they can ask questions and get instant answers about fees, policies, etc.
- **Data Flow**: Registration data flows through the AI agent into structured storage, replacing direct Google Form → Spreadsheet flow
- **Admin Workflow**: Admin receives notifications, accesses structured registration data, and maintains the service knowledge base (fees, regulations, policies)
- **Infrastructure**: Requires hosting for the AI agent, chat interface, email processing, and knowledge base storage
- **External Dependencies**: AI/LLM service for conversational capabilities, email service for email channel
