## 1. Project Setup

- [ ] 1.1 Create `requirements.txt` with pinned versions: `chainlit`, `anthropic`, `python-dotenv`
- [ ] 1.2 Create `.env.example` documenting required environment variables (`ANTHROPIC_API_KEY`, etc.)
- [ ] 1.3 Create `chainlit.toml` with project name, telemetry disabled, custom CSS path, and default language set to German
- [ ] 1.4 Create the directory structure: `app/`, `app/agent/`, `app/knowledge_base/`, `app/storage/registrations/`, `public/`
- [ ] 1.5 Add `.gitignore` entries for `.env`, `app/storage/registrations/`, `__pycache__/`, `.chainlit/`

## 2. Chainlit Application Shell

- [ ] 2.1 Create `app/chat.py` with `@cl.on_chat_start` handler that sends the German welcome message from `channel-config.md`
- [ ] 2.2 Add `@cl.on_message` handler that echoes the received message (placeholder — wired to agent in task 4)
- [ ] 2.3 Create `chainlit.md` with the bilingual welcome message (German default, English comment)
- [ ] 2.4 Verify the app starts with `chainlit run app/chat.py` and the welcome message appears in the browser

## 3. Accessibility CSS

- [ ] 3.1 Create `public/custom.css` with colour contrast overrides (all normal text ≥ 4.5:1, large text ≥ 3:1, placeholder ≥ 4.5:1) — measure against Chainlit's default colours with a contrast checker
- [ ] 3.2 Add `@media (prefers-reduced-motion: reduce)` block to `custom.css` that hides animated typing dots and replaces with a static `"…"` pseudo-element
- [ ] 3.3 Add a visually-hidden skip link as the first element in the page via Chainlit's `custom_css` or `head` injection, targeting the message input (`#chat-input`)
- [ ] 3.4 Add CSS to make the skip link visible on `:focus`
- [ ] 3.5 Use `dvh` (dynamic viewport height) units in `custom.css` for the chat container height to prevent iOS Safari virtual keyboard from obscuring the input

## 4. Agent Core Stub

- [ ] 4.1 Create `app/agent/core.py` with a `process_message(message: str, session_state: dict) -> str` function that returns a hardcoded placeholder reply (full agent logic is a separate change)
- [ ] 4.2 Wire `app/chat.py`'s `@cl.on_message` to call `process_message` and stream the reply back using `cl.Message.stream_token()`
- [ ] 4.3 Initialise `cl.user_session` in `@cl.on_chat_start` with an empty registration state dict (`{"collected": {}, "history": []}`)
- [ ] 4.4 Pass `cl.user_session.get("state")` into `process_message` and write back any state updates it returns

## 5. ARIA and Focus Management

- [ ] 5.1 Identify the Chainlit message list container selector in the rendered DOM (use browser dev tools)
- [ ] 5.2 Add `aria-live="polite"` and `aria-atomic="false"` to the message list container via `custom.css` content injection or a `<script>` in Chainlit's `head` config
- [ ] 5.3 Inject a small JS snippet (via `chainlit.toml` `head` config) that, after each completed agent message, moves focus to the latest `.message` element by setting `tabindex="-1"` and calling `.focus()`
- [ ] 5.4 Ensure mid-stream tokens do NOT trigger the live region announcement — only fire the focus move after `cl.Message.send()` completes, not during `stream_token()` calls

## 6. Session Management

- [ ] 6.1 Confirm `cl.user_session` persists across a browser page refresh by testing manually: start a conversation, refresh, verify history is shown
- [ ] 6.2 Add an `@cl.on_chat_end` handler that logs session end (and in future will trigger email-channel reminders)
- [ ] 6.3 Add a disconnect message in the Chainlit error/reconnect UI config: "Deine Sitzung ist abgelaufen. Starte ein neues Gespräch oder nutze E-Mail für längere Pausen." (with English equivalent)

## 7. Mobile Testing

- [ ] 7.1 Test on iOS Safari (real device or BrowserStack): open chat, tap input, confirm keyboard does not obscure input
- [ ] 7.2 Test on Android Chrome: open chat, tap input, confirm input stays visible and message list scrolls correctly
- [ ] 7.3 Test landscape orientation on mobile: confirm no horizontal scroll and layout is usable

## 8. Accessibility Verification

- [ ] 8.1 Run `axe-core` browser extension against the running chat page and fix any Level A or AA violations
- [ ] 8.2 Verify keyboard-only flow: Tab to skip link → activate → Tab to input → type message → Enter → agent replies → focus moves to reply
- [ ] 8.3 Test with VoiceOver (macOS or iOS): open chat, navigate to input, send a message, confirm agent reply is announced without moving focus manually
- [ ] 8.4 Test with `prefers-reduced-motion: reduce` (set in OS accessibility settings): confirm typing indicator shows as static text, not animated
- [ ] 8.5 Verify colour contrast of all text elements using a browser contrast checker; document any elements that needed overrides

## 9. Final Integration Check

- [ ] 9.1 Confirm `chainlit run app/chat.py` starts cleanly with no warnings
- [ ] 9.2 Send a message, receive a reply, refresh the page — confirm history is preserved
- [ ] 9.3 Confirm telemetry is disabled (no outgoing requests to Chainlit analytics in network tab)
- [ ] 9.4 Confirm the `ANTHROPIC_API_KEY` env var is not logged or exposed in any output
- [ ] 9.5 Update `openspec/config.yaml` context field with the chosen tech stack (Python, Chainlit, Anthropic SDK)
