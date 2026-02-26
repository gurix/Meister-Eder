## Context

The email poll loop (`main.py`) fetches all unread messages and passes each one to `EmailAgent.process_message()`, which calls the LLM and returns a reply. The reply is then sent via SMTP. There was no check to determine whether the inbound message came from a human or an automated system. Any message that arrived in the inbox — including MAILER-DAEMON bounces triggered by the agent's own previous reply — was processed and replied to, completing the loop.

## Goals / Non-Goals

**Goals:**
- Prevent the agent from replying to automated/bounce messages
- Alert admin once when an automated loop is detected
- Enforce a hard upper bound on conversation length as a secondary safety net
- Persist escalation state so alerts are not repeated across poll cycles

**Non-Goals:**
- General spam detection
- Blocking specific sender addresses permanently
- Exposing loop-detection configuration via the admin UI

## Decisions

### 1. Two-layer defence

**Decision**: Implement two independent checks in sequence:
1. Header-based automated sender detection (catches known patterns immediately)
2. Message-count cap (catches anything that slips through layer 1)

**Rationale**: Neither layer is infallible alone. Header-based detection covers RFC-standard signals and common patterns, but edge cases exist (e.g. a forwarding alias that strips headers). The count cap is a last-resort guarantee that no conversation runs forever.

### 2. Detection at the channel layer, handling in the agent

**Decision**: `email_channel.py` performs the header analysis and adds `is_automated` / `automated_reason` to the message dict. `main.py` checks the flag and calls `agent.handle_automated_message()` instead of `agent.process_message()`.

**Rationale**: The channel layer already has access to the raw `email.message.Message` object with all headers. The agent layer has access to conversation state and the notifier. Splitting cleanly at the channel/agent boundary keeps each layer doing what it does best without coupling them further.

**Alternative considered**: Detecting in the agent by inspecting the message text. Rejected — by that point the raw headers are gone, and text-based detection is less reliable than header-based.

### 3. Detection signals (in priority order)

| Signal | Standard | Reliability |
|---|---|---|
| Sender local-part: `mailer-daemon`, `postmaster`, `noreply`, `no-reply`, `bounce`, … | RFC 5321 §4.5.4 | Very high |
| `Auto-Submitted:` ≠ `no` | RFC 3834 | Very high |
| `X-Auto-Response-Suppress:` present | MS Exchange | Very high |
| `Content-Type: multipart/report` | RFC 3462 | Very high |
| `X-Loop:` present | MTA convention | High |
| `Precedence: bulk` or `junk` | Common practice | Medium |
| Subject heuristics (Undelivered Mail, Out of Office, Abwesenheitsnotiz, …) | — | Medium |

`Precedence: list` is intentionally excluded — mailing-list messages may be legitimate.

### 4. Message-count cap set at 20

**Decision**: `MAX_USER_MESSAGES = 20`. If `process_message()` is called when there are already more than 20 user messages in the history, return `""` (no reply) and escalate to admin.

**Rationale**: A typical registration takes 8–12 exchanges. 20 gives ample room for slow or verbose conversations while still catching runaway loops. The value is a module-level constant so it can be changed without config infrastructure overhead.

### 5. One-shot admin alert via `loop_escalated` flag

**Decision**: Add `loop_escalated: bool` to `ConversationState`. The admin is notified exactly once per conversation. Subsequent automated messages or over-limit polls are silently dropped after the flag is set.

**Rationale**: The admin needs to know something is wrong, but receiving one alert per bounce (which may arrive many times per minute) would create inbox spam worse than the original problem.

**Implementation**: The flag is persisted to JSON so it survives agent restarts.

### 6. Admin notification routed to CC list

**Decision**: Loop-escalation alerts go to `self._cc_emails` (Markus Graf / `ADMIN_EMAIL_CC`), not to playgroup leaders.

**Rationale**: This is a system/infrastructure issue, not a registration event. The CC address is the designated admin (Markus Graf) who handles operational issues. Playgroup leaders do not need to see these alerts.

## Risks / Trade-offs

**False positives** → A legitimate parent using a `noreply@` alias could be silently blocked. This is an unlikely edge case; the subject/header checks require multiple signals for ambiguous senders. A missed registration is recoverable — admin gets the alert and can follow up manually.

**False negatives** → A clever loop that uses a normal-looking sender address and no automated headers would slip past layer 1. The 20-message cap catches it.

**Completed conversations** → The count cap applies to all conversations, including completed ones with many post-completion Q&A exchanges. A very chatty parent could theoretically hit the cap after registration is done. Acceptable for MVP — the cap is high enough that normal use is unaffected.
