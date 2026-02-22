## Context

The `chat-interface` capability is specified but not yet built. This change implements it. The core agent (LLM conversation logic) is defined separately; this design covers the web frontend, its real-time transport, session management, and how the chat layer connects to the agent core.

The tech stack for the entire project is decided here as part of this first implementation change, since the chat interface is the most visible component and its runtime shapes the whole backend.

## Goals / Non-Goals

**Goals:**
- Deliver a working, accessible web chat interface parents can use to register
- Choose a library that provides WCAG 2.1 AA compliance out of the box or close to it
- Keep the frontend thin: no business logic, just message in / message out
- Establish the Python tech stack and project layout for all subsequent changes

**Non-Goals:**
- Custom chat UI built from scratch (we use a library)
- Authentication / login before chatting
- Persistent chat history across separate browser sessions (session-scoped only)
- Admin-facing UI (out of scope for this project entirely)

## Decisions

### 1. Chat UI Library: Chainlit

**Decision**: Use [Chainlit](https://github.com/Chainlit/chainlit) as the chat interface framework.

**Rationale**:
Chainlit is purpose-built for AI assistant chat interfaces. It handles everything the spec requires without building it from scratch:
- Real-time streaming responses (SSE / WebSocket)
- Typing indicators while the agent generates
- Session management (server-side, survives page refresh within the same session)
- Message history display with clear agent / user attribution
- Built-in mobile-responsive layout
- Python-native: integrates directly with the Anthropic SDK with no bridging layer

**Accessibility baseline**: Chainlit's React frontend uses semantic HTML and has basic ARIA support. Gaps (see Risk section) are filled with CSS overrides and custom header components.

**Alternatives considered**:

| Option | Why rejected |
|--------|-------------|
| React + `@chatscope/chat-ui-kit-react` | Requires a separate Node.js build pipeline and a backend bridge; more moving parts for a small project |
| Gradio | Data-science oriented; poor accessibility; limited chat customisation |
| FastAPI + HTMX (server-rendered) | Accessible by default but no real-time streaming without complex SSE setup; typing indicators are awkward |
| Custom React app | Reimplements what Chainlit provides; no accessibility gains justify the cost |

### 2. Language and Runtime: Python

**Decision**: Python as the sole backend language.

**Rationale**: The Anthropic SDK is first-class in Python. Email processing (IMAP/SMTP), file I/O for the knowledge base, and JSON storage are all well-supported. Chainlit is Python-native. Using one language for the entire stack minimises operational complexity for a small project.

### 3. Real-Time Transport: Chainlit's built-in WebSocket / SSE

**Decision**: Rely on Chainlit's managed real-time layer; do not implement a separate WebSocket server.

**Rationale**: Chainlit handles connection lifecycle, reconnection, and streaming out of the box. The agent core is invoked inside Chainlit's `@cl.on_message` handler and streams tokens back with `cl.Message.stream_token()`. There is no need for a separate transport layer.

### 4. Session State: Chainlit User Session

**Decision**: Store in-progress registration state in `cl.user_session` (server-side, keyed by Chainlit's session ID).

**Rationale**: Chainlit provides a per-connection server-side dict (`cl.user_session`) that persists across page refreshes within the same browser session. This satisfies the spec requirement that conversation history and state survive a refresh. No external state store (Redis, database) is needed for MVP.

**Trade-off**: State is lost when the server restarts. For a small playgroup this is acceptable; parents are encouraged to use email if they need to resume days later.

### 5. Accessibility Gaps and Mitigations

Chainlit covers most WCAG 2.1 AA requirements but has known gaps:

| Gap | Mitigation |
|----|-----------|
| ARIA live region for incoming messages | Add `aria-live="polite"` via Chainlit's custom CSS / element override on the message list container |
| Focus management after agent reply | Inject a small JS snippet via Chainlit's `head` config to move focus to the latest message |
| Colour contrast of default theme | Override with a high-contrast custom CSS theme (≥ 4.5:1 for all text) |
| Animated typing dots | Wrap in `@media (prefers-reduced-motion: reduce)` to hide or swap for a static indicator |
| Skip-to-content link | Add via Chainlit's custom `header` HTML config |

### 6. Project Layout

```
meister-eder/
├── app/
│   ├── chat.py              # Chainlit entry point (@cl.on_chat_start, @cl.on_message)
│   ├── agent/
│   │   ├── core.py          # Channel-agnostic agent logic (shared with email)
│   │   └── tools.py         # Agent tool definitions (knowledge base lookup, etc.)
│   ├── knowledge_base/      # Markdown files (symlink or copy of content/knowledge-base/)
│   └── storage/
│       └── registrations/   # JSON registration records
├── public/
│   └── custom.css           # Accessibility overrides for Chainlit
├── chainlit.md              # Welcome message shown in chat (German default)
├── chainlit.toml            # Chainlit configuration (theme, title, etc.)
└── requirements.txt
```

### 7. Chainlit Configuration

Key settings in `chainlit.toml`:

```toml
[project]
name = "Spielgruppe Pumuckl"
enable_telemetry = false

[UI]
name = "Spielgruppe Pumuckl"
default_language = "de"
# Custom CSS applied on top of default theme
custom_css = "/public/custom.css"

[meta]
generated_by = "1.x"
```

Welcome message (`chainlit.md`) is written in German with an English fallback comment, matching the agent personality spec.

## Risks / Trade-offs

**Chainlit version stability**: Chainlit's API has changed between major versions. Pin to a specific minor version in `requirements.txt` and document upgrade steps.

**Accessibility completeness**: Chainlit's built-in accessibility is not fully audited. The mitigations in Decision 5 address known gaps; a manual screen-reader test (NVDA/VoiceOver) should be part of the implementation verification.

**Session loss on server restart**: Acceptable for MVP. Documented in the chat UI welcome message ("for longer registrations, consider email").

**Mobile keyboard overlap**: On small screens, the browser's virtual keyboard can obscure the chat input. Chainlit's layout is mobile-responsive but may need a CSS viewport-height fix (`dvh` units) for iOS Safari.

## Open Questions

- Should the Chainlit app be the same process as future admin/export endpoints, or run separately? (Likely separate; Chainlit's web server is not designed to host arbitrary REST APIs.)
- What domain/subdomain will the chat be served from? (Affects CORS config if the agent API is separate.)
