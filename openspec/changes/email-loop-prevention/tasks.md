## 1. Automated Sender Detection (email_channel.py)

- [x] 1.1 Add `_AUTOMATED_SENDER_RE` regex for known non-human local-parts (mailer-daemon, postmaster, noreply, no-reply, donotreply, bounce, …)
- [x] 1.2 Add `_AUTOMATED_SUBJECT_RE` regex for bounce/OOO subject patterns (German + English)
- [x] 1.3 Implement `detect_automated_message(raw_msg, from_addr) → (bool, str)` checking all signals in priority order: sender pattern → Auto-Submitted → X-Auto-Response-Suppress → multipart/report → X-Loop → Precedence → subject
- [x] 1.4 Add `is_automated` and `automated_reason` fields to the dict returned by `fetch_unread_messages()`

## 2. Poll Loop Guard (main.py)

- [x] 2.1 In `run_poll_loop()`, check `msg.get("is_automated")` before calling `agent.process_message()`
- [x] 2.2 If automated: log a warning, call `agent.handle_automated_message()`, and `continue` (skip `send_reply`)

## 3. Agent — Automated Message Handler (agent/core.py)

- [x] 3.1 Add `MAX_USER_MESSAGES = 20` module-level constant
- [x] 3.2 Implement `handle_automated_message(sender_email, subject, reason, inbound_message_id)` method
- [x] 3.3 In `handle_automated_message`: load or create state; set `loop_escalated = True`; call `notify_loop_escalation()` once; silently skip if already escalated; save state
- [x] 3.4 In `process_message()`, after appending the user message, count user messages; if count > `MAX_USER_MESSAGES` and not escalated: set `loop_escalated = True`, call `notify_loop_escalation()`, return `""`
- [x] 3.5 If already escalated and over limit: silently save state and return `""`

## 4. Conversation State (models/conversation.py)

- [x] 4.1 Add `loop_escalated: bool = False` field to `ConversationState`
- [x] 4.2 Include `loop_escalated` in `to_dict()`
- [x] 4.3 Restore `loop_escalated` in `from_dict()` with default `False` for backward compatibility

## 5. Admin Notification (notifications/notifier.py)

- [x] 5.1 Implement `notify_loop_escalation(sender_email, conversation_id, reason, message_count)` method
- [x] 5.2 Route alert to `self._cc_emails` only (not playgroup leaders)
- [x] 5.3 Subject: `[WARNUNG] Automatische E-Mail / Endlosschleife erkannt: {sender_email}`
- [x] 5.4 Body: sender, conversation ID, message count, reason, call-to-action in German
- [x] 5.5 Guard: if no CC emails configured, log warning and return without SMTP call

## 6. Tests

- [x] 6.1 `TestDetectAutomatedMessageBySender` — mailer-daemon, postmaster, noreply, no-reply, donotreply, bounce; normal parent address not flagged
- [x] 6.2 `TestDetectAutomatedMessageByHeaders` — Auto-Submitted (auto-replied, auto-generated, no); X-Auto-Response-Suppress; multipart/report; X-Loop; Precedence bulk/junk; Precedence list not flagged
- [x] 6.3 `TestDetectAutomatedMessageBySubject` — Undelivered Mail, Mail Delivery Failed, Out of Office, Abwesenheitsnotiz, Automatische Antwort; case-insensitive; normal subject not flagged
- [x] 6.4 `TestHandleAutomatedMessage` — sets loop_escalated; calls notifier once; creates state when none exists; drops silently if already escalated; notifier failure does not propagate; inbound message ID stored
- [x] 6.5 `TestProcessMessageCountCap` — at limit still processes; over limit returns ""; sets loop_escalated; calls notifier once; no duplicate alert; notifier failure does not propagate; constant equals 20
- [x] 6.6 `TestNotifyLoopEscalation` — sends to CC; [WARNUNG] in subject; sender in subject; reason in body; message count in body; no-CC guard; no-SMTP guard
- [x] 6.7 `TestConversationStateLoopEscalated` (test_models.py) — default False; to_dict includes key; True round-trip; from_dict backward compatibility
