## Why

The `chat-interface` capability was defined in the scoping phase as a must-have for the initial release, but no implementation exists yet. This change delivers it.

Parents need a zero-friction way to start a registration or ask questions without setting up email threads. A web chat interface lowers that barrier: they navigate to a URL, start typing, and they're immediately talking to the agent. The interface must work equally well on a mobile phone held in one hand while watching a toddler.

Accessibility is a first-class concern. Parents may rely on screen readers, keyboard navigation, or high-contrast displays. An inaccessible registration interface excludes families with disabilities—contrary to the playgroup's values.

Using a mature, accessibility-tested chat UI library rather than building from scratch means we inherit ARIA compliance, keyboard navigation, focus management, and screen reader support without reimplementing them.

## What Changes

- **ADDED `chat-interface` implementation**: A deployable web application that renders the chat UI, connects to the core agent, and manages browser-session state. Built on top of an existing accessible chat UI library.

### What this does NOT include

- The core conversational agent (separate concern, shared with email channel)
- Email channel implementation
- Backend API for the agent (defined separately; this change specifies only the frontend and its integration contract)

## Capabilities

### Modified Capabilities

- `chat-interface`: Moves from specified-but-unbuilt to implemented. Requirements remain as defined in the existing spec, with accessibility requirements added:
  - WCAG 2.1 AA compliance
  - Full keyboard navigation (no mouse required)
  - Screen reader compatibility (ARIA live regions for incoming messages)
  - Sufficient colour contrast (≥ 4.5:1 for normal text)
  - Focus management (focus moves to new agent messages; skip-to-content link)
  - Respects `prefers-reduced-motion` (no animated typing dots if disabled)

## Impact

- **Parents**: Can access the registration agent from any browser without email setup; works on mobile phones; usable by parents with accessibility needs
- **Infrastructure**: Adds a web server serving the chat frontend; WebSocket or SSE connection to the agent backend
- **Dependencies**: One new runtime dependency — a well-maintained, accessible chat UI library (to be decided in design); the existing agent core (no changes required to the core)
- **Admin**: No impact; admin does not interact with the chat interface
