## MODIFIED Requirements

> Extends the `chat-interface` spec from `define-project-scope`. All previously
> defined requirements remain in force. This spec adds accessibility requirements
> and implementation constraints introduced by this change.

---

### Requirement: WCAG 2.1 AA compliance
The chat interface SHALL conform to WCAG 2.1 Level AA in all user-facing interactions.

#### Scenario: Automated accessibility check passes
- **WHEN** an automated accessibility audit (e.g. axe-core) is run against the chat page
- **THEN** it SHALL report zero Level A and Level AA violations

#### Scenario: Manual screen reader test passes
- **WHEN** a user navigates the chat using NVDA (Windows) or VoiceOver (macOS/iOS)
- **THEN** they SHALL be able to read all messages and send a new message without using a mouse

---

### Requirement: Full keyboard navigation
The chat interface SHALL be fully operable using only a keyboard.

#### Scenario: Sending a message by keyboard
- **WHEN** a parent focuses the text input and types a message
- **THEN** they SHALL be able to submit it with the Enter key without pressing a mouse button

#### Scenario: Tab order is logical
- **WHEN** a parent presses Tab repeatedly from the top of the page
- **THEN** focus SHALL move through interactive elements in a logical reading order (skip link → message list → text input → send button)

#### Scenario: No keyboard trap
- **WHEN** focus enters any component (e.g. the text input)
- **THEN** the parent SHALL be able to move focus out again using only the keyboard

---

### Requirement: Skip-to-content link
The chat interface SHALL provide a skip navigation link as the first focusable element.

#### Scenario: Skip link is visible on focus
- **WHEN** a keyboard user presses Tab on the chat page for the first time
- **THEN** a "Skip to chat" link SHALL become visible and, when activated, move focus directly to the message input

---

### Requirement: Screen reader announcements for new messages
Incoming agent messages SHALL be announced to screen readers without requiring focus change.

#### Scenario: Agent reply announced
- **WHEN** the agent sends a new message
- **THEN** a screen reader SHALL announce the message content via an ARIA live region (`aria-live="polite"`)

#### Scenario: In-progress stream not announced mid-token
- **WHEN** the agent is streaming a response token by token
- **THEN** the live region SHALL NOT announce each individual token; only the completed message SHALL be announced

---

### Requirement: Focus moves to agent reply on completion
After the agent finishes a response, keyboard focus SHALL be placed near the new message.

#### Scenario: Focus after reply
- **WHEN** the agent finishes generating a response
- **THEN** focus SHALL move to the new agent message element (or a wrapper with `tabindex="-1"`) so the parent can read it immediately with a screen reader

---

### Requirement: Sufficient colour contrast
All text in the chat interface SHALL meet WCAG 2.1 SC 1.4.3 contrast requirements.

#### Scenario: Normal text contrast
- **WHEN** any text of normal size is rendered
- **THEN** its contrast ratio against the background SHALL be ≥ 4.5:1

#### Scenario: Large text contrast
- **WHEN** any text at 18pt (or 14pt bold) or larger is rendered
- **THEN** its contrast ratio against the background SHALL be ≥ 3:1

#### Scenario: Input placeholder contrast
- **WHEN** the text input displays placeholder text
- **THEN** the placeholder contrast ratio SHALL be ≥ 4.5:1

---

### Requirement: Typing indicator respects reduced-motion preference
The agent-processing indicator SHALL not use animation when the user has requested reduced motion.

#### Scenario: Reduced motion active
- **WHEN** the OS or browser has `prefers-reduced-motion: reduce` set
- **AND** the agent is generating a response
- **THEN** the typing indicator SHALL display as a static element (e.g. "…" text) with no animation

#### Scenario: Reduced motion not active
- **WHEN** `prefers-reduced-motion` is not set or is set to `no-preference`
- **THEN** the typing indicator MAY display an animated element (e.g. bouncing dots)

---

### Requirement: Mobile viewport input visibility
The text input SHALL remain visible when the virtual keyboard is open on mobile devices.

#### Scenario: iOS Safari virtual keyboard
- **WHEN** a parent taps the text input on an iOS device and the virtual keyboard appears
- **THEN** the input field SHALL remain in view and not be obscured by the keyboard

#### Scenario: Android Chrome virtual keyboard
- **WHEN** a parent taps the text input on an Android device and the virtual keyboard appears
- **THEN** the input field SHALL remain in view and the message list SHALL scroll to show the latest message above the keyboard

---

### Requirement: Session state survives page refresh
Conversation history and registration state SHALL be preserved when the parent reloads the page within the same browser session.

#### Scenario: Page refresh mid-conversation
- **WHEN** a parent refreshes the browser tab during an active conversation
- **THEN** the full conversation history SHALL be displayed and the registration state SHALL be intact on reconnect

#### Scenario: Server restart loses state (acceptable degradation)
- **WHEN** the server restarts while a session is active
- **THEN** the parent SHALL see a notification that the session ended and be invited to start a new conversation

---

### Requirement: Session-loss notification on disconnect
If the connection to the server is lost and cannot be recovered, the interface SHALL inform the parent.

#### Scenario: Unrecoverable disconnect
- **WHEN** the WebSocket / SSE connection is lost and reconnection fails after a reasonable timeout
- **THEN** the interface SHALL display a message explaining the session ended and suggest using email for longer registration processes

---

### Requirement: Welcome message in the parent's language
The chat interface SHALL display a welcome message in German by default, with automatic language adaptation.

#### Scenario: Default welcome message
- **WHEN** a parent opens the chat interface
- **THEN** the welcome message SHALL be displayed in German

#### Scenario: Language adaptation
- **WHEN** a parent sends their first message in English
- **THEN** the agent SHALL respond in English for the remainder of the session

---

## ADDED Requirements

### Requirement: Chainlit-based implementation
The chat interface SHALL be implemented using the Chainlit framework.

#### Scenario: Application entry point
- **WHEN** the server starts
- **THEN** it SHALL run a Chainlit application with `@cl.on_chat_start` and `@cl.on_message` handlers

#### Scenario: Telemetry disabled
- **WHEN** the application runs
- **THEN** Chainlit telemetry SHALL be disabled (`enable_telemetry = false` in `chainlit.toml`)

---

### Requirement: Custom accessibility CSS applied
The Chainlit default theme SHALL be extended with a custom CSS file that addresses accessibility gaps.

#### Scenario: Custom CSS loaded
- **WHEN** the chat page is served
- **THEN** the custom CSS file (`/public/custom.css`) SHALL be loaded and applied on top of the default Chainlit theme

#### Scenario: Custom CSS addresses contrast and motion
- **WHEN** the page renders
- **THEN** the custom CSS SHALL include contrast overrides achieving ≥ 4.5:1 for all normal text AND a `prefers-reduced-motion` block that suppresses typing-dot animation
