# Channel Configuration

## Email Channel

### Registration Email Address

**Address:** `[To be determined]`

Suggested options:
- `anmeldung@familienvereinfaellanden.ch` (German: "registration")
- `spielgruppen@familien-verein.ch` (existing admin address - Markus Graf)
- `registration@familienvereinfaellanden.ch`

*Note: The existing admin email spielgruppen@familien-verein.ch could be used, or a new dedicated address could be created.*

### Requirements for Email Address
- Should be memorable and clear in purpose
- Associated with the organization's domain (preferred)
- Or a dedicated Gmail/other address if domain email not available

### Email Processing
- All emails to this address are processed by the AI agent
- Agent responds from the same address
- Thread tracking via email headers (In-Reply-To, References)

---

## Chat Interface

### Access URL

**URL:** `[To be determined]`

Suggested options:
- `https://familienvereinfaellanden.ch/anmeldung`
- `https://register.familienvereinfaellanden.ch`
- Embedded widget on existing website

### Branding Requirements

**Style:** Simple and neutral

| Element | Specification |
|---------|--------------|
| Color scheme | Clean, neutral colors (white background, subtle accent) |
| Logo | Optional - can include Familienverein logo if available |
| Typography | System fonts, readable and accessible |
| Layout | Mobile-first, clean chat bubble design |

### Welcome Message

**German (default):**
> Willkommen bei der Spielgruppe Pumuckl! Ich kann dir bei der Anmeldung deines Kindes helfen oder Fragen beantworten. Was möchtest du tun?

**English:**
> Welcome to Spielgruppe Pumuckl! I can help you register your child or answer questions. What would you like to do?

### Chat Interface Elements

- Chat message bubbles (agent vs parent visually distinct)
- Text input field
- Send button
- Typing indicator when agent is responding
- Minimal header with playgroup name

---

## Channel Selection Notes

Both channels lead to the same AI agent and registration system. The choice of channel is purely based on parent preference:

| Channel | Best for |
|---------|----------|
| Email | Parents who prefer asynchronous communication |
| Chat | Parents who want immediate, real-time interaction |

Registrations from both channels are stored in the same system and appear identical to the admin.

---

## Channel-Specific Behavior Differences

While both channels use the same AI agent and conversation logic, there are some inherent differences:

### Response Timing

| Aspect | Email | Chat |
|--------|-------|------|
| Response time | Near-instant (automated) | Real-time |
| Parent expectation | Can be async | Expects immediate reply |
| Session concept | Thread-based | Session-based |

### Conversation Flow

| Aspect | Email | Chat |
|--------|-------|------|
| Multiple questions | One per email preferred | Multiple turns easy |
| Length | Can be longer | Shorter, conversational |
| Formatting | Rich text, headers | Simple text, emojis OK |

### State Management

| Aspect | Email | Chat |
|--------|-------|------|
| Session timeout | No timeout (thread-based) | Session-based (browser) |
| Resumption | Automatic via thread | Same session required |
| Data retention | 1 month | Browser session duration |
| Reminders | Yes (Day 3, 10, 25) | No (session-based) |

### Error Handling

| Aspect | Email | Chat |
|--------|-------|------|
| Invalid input | Ask in next reply | Immediate correction |
| Dropped session | Follow-up email | Timeout message |
| Technical error | Error response email | Error message in chat |

### Unique Capabilities

**Email Only:**
- Can handle overnight/delayed responses naturally
- Parent can attach documents if needed
- Formal record via email threads

**Chat Only:**
- Typing indicators
- Immediate validation feedback
- More natural conversation flow
- Session can redirect to email if preferred

### Consistent Across Both

- Same AI agent personality
- Same registration data collected
- Same validation rules
- Same knowledge base access
- Same notification to admin
- Same data storage format
