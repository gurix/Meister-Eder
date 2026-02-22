## 1. Add Chainlit Dependency

- [ ] 1.1 Run `uv add chainlit` to add Chainlit to `pyproject.toml` (matches existing `uv`-based workflow; do not create `requirements.txt`)
- [ ] 1.2 Create `chainlit.toml` at the project root with: `name = "Spielgruppe Pumuckl"`, `enable_telemetry = false`, `custom_css = "/public/custom.css"`, `default_language = "de"`

## 2. Add Streaming Support to src/llm.py

- [ ] 2.1 Add a `stream_complete(model: str, system: str, messages: list)` generator function to `src/llm.py` that calls `litellm.completion(..., stream=True)` and yields text chunks (parallels the existing `complete()` function; both share the same `api_messages` build logic)
- [ ] 2.2 Add tests for `stream_complete` in `tests/test_llm.py` — verify chunks are yielded, empty deltas are skipped, and the model/system/messages args are forwarded correctly

## 3. Create Chainlit Entry Point

- [ ] 3.1 Create `chat_app.py` at the project root with a `@cl.on_chat_start` handler that:
  - Loads `Config.from_env()` from `src/config.py`
  - Initialises `KnowledgeBase`, `ConversationStore`, `AdminNotifier` from existing `src/` modules
  - Creates a fresh `ConversationState` (use Chainlit's session ID as `conversation_id`; no email address required at this stage)
  - Stores state dict in `cl.user_session["state"]`
  - Sends the German welcome message (drawn from `content/sample-responses.md`)
- [ ] 3.2 Add a `@cl.on_message` handler in `chat_app.py` that:
  - Deserialises `ConversationState` from `cl.user_session["state"]`
  - Appends the parent's message to `state.messages` as a `ChatMessage(role="user", ...)`
  - Builds the system prompt via `build_system_prompt()` from `src/agent/prompts.py`
  - Creates a `cl.Message(content="")` and streams chunks from `stream_complete()` using `msg.stream_token(chunk)`, then calls `msg.send()`
  - Parses the completed response text for JSON (reuse `_parse_llm_response` logic from `src/agent/core.py` — extract into `src/agent/response_parser.py` if needed)
  - Applies field updates to `ConversationState.registration`; updates `state.flow_step` and `state.language`
  - Appends the assistant reply to `state.messages`
  - Serialises state back to `cl.user_session["state"]`
  - When `registration_complete` is true: saves registration via `ConversationStore`, sends admin notification via `AdminNotifier`, sets `state.completed = True`
- [ ] 3.3 Create `chainlit.md` at the project root with the German welcome/intro text shown in the Chainlit sidebar (plain markdown; drawn from `content/agent-personality.md`)

## 4. Accessibility CSS

- [ ] 4.1 Create `public/` directory at the project root
- [ ] 4.2 Create `public/custom.css` with colour contrast overrides: all normal text ≥ 4.5:1, large text ≥ 3:1, and placeholder text ≥ 4.5:1 — measure Chainlit's default colours with a contrast checker and override as needed
- [ ] 4.3 Add a `@media (prefers-reduced-motion: reduce)` block to `public/custom.css` that hides the animated typing-dot element and replaces it with a static `"…"` pseudo-element
- [ ] 4.4 Add CSS in `public/custom.css` for the skip link: hidden by default, visible and highlighted on `:focus`, and targeting `#chat-input`
- [ ] 4.5 Add `min-height: 100dvh` (dynamic viewport height) to the chat container selector in `public/custom.css` so the input is not obscured by iOS Safari's virtual keyboard

## 5. ARIA and Focus Management

- [ ] 5.1 Inspect the Chainlit message list container selector in a running browser (dev tools) and add `aria-live="polite"` and `aria-atomic="false"` to it via a `MutationObserver` JS snippet injected through `chainlit.toml`'s `[UI] custom_js` or as `public/accessibility.js`
- [ ] 5.2 Extend the JS snippet so that after each completed agent message (after `msg.send()`, not during streaming) focus moves to the new message element via `element.setAttribute("tabindex", "-1"); element.focus()`
- [ ] 5.3 Add the skip link HTML element to the page via the same JS snippet or Chainlit's `[UI] custom_header` config so it is the first focusable element

## 6. Session Management

- [ ] 6.1 Test manually: start a conversation in the browser, refresh the page, verify that `cl.user_session["state"]` is restored and conversation history is displayed
- [ ] 6.2 Add a `@cl.on_chat_end` handler in `chat_app.py` that logs the session end (no action needed for MVP, but provides a hook for future email-reminder integration)
- [ ] 6.3 Add a disconnect/reconnect message in Chainlit configuration: "Deine Sitzung ist abgelaufen. Starte ein neues Gespräch oder nutze E-Mail für eine längere Pause." (and English equivalent)

## 7. Mobile Testing

- [ ] 7.1 Test on iOS Safari (device or BrowserStack): tap the text input while virtual keyboard is open — confirm input is not obscured
- [ ] 7.2 Test on Android Chrome: tap input, confirm message list scrolls to keep the latest message visible above the keyboard
- [ ] 7.3 Test landscape orientation on a mobile screen: confirm no horizontal scroll and layout is usable

## 8. Accessibility Verification

- [ ] 8.1 Run the axe-core browser extension against the running chat page and fix all reported Level A and Level AA violations
- [ ] 8.2 Verify keyboard-only flow: Tab → skip link becomes visible → activate → focus moves to message input → type message → Enter → agent replies → focus moves to new message
- [ ] 8.3 Test with VoiceOver (macOS or iOS): navigate to input, send a message, confirm agent reply is announced via the live region without manual focus movement
- [ ] 8.4 Set OS `prefers-reduced-motion: reduce` and confirm the typing indicator shows as static text (not animated)
- [ ] 8.5 Spot-check contrast of all rendered text elements; document which selectors required overrides in `public/custom.css`

## 9. Final Integration Check

- [ ] 9.1 Confirm `chainlit run chat_app.py` starts cleanly with no warnings or import errors
- [ ] 9.2 Complete an end-to-end registration through the chat interface: verify the registration JSON is saved to `data/registrations/` and the admin notification email is sent
- [ ] 9.3 Confirm Chainlit telemetry is disabled: open the network tab and verify no requests go to Chainlit analytics endpoints
- [ ] 9.4 Confirm `ANTHROPIC_API_KEY` and other secrets are not printed in logs or error output
- [ ] 9.5 Update the `context` field in `openspec/config.yaml` with the finalised tech stack: Python 3.13, Chainlit, LiteLLM, uv, file-based JSON storage
