## 1. Update Conversation Storage

- [ ] 1.1 Modify `ConversationStore` to key conversations by normalized email address
- [ ] 1.2 Add `normalize_email()` helper function (lowercase, trim)
- [ ] 1.3 Update `_conversation_path()` to use email-based filename
- [ ] 1.4 Add `find_by_email()` method to replace thread-ID-based lookup

## 2. Update Email Channel

- [ ] 2.1 Remove `_resolve_thread_id()` from conversation matching logic
- [ ] 2.2 Pass sender email to agent instead of thread ID for conversation lookup
- [ ] 2.3 Keep thread ID handling for outbound reply headers (`In-Reply-To`, `References`)
- [ ] 2.4 Store most recent inbound message ID for reply threading

## 3. Update Agent Core

- [ ] 3.1 Modify `process_message()` to lookup conversation by email address
- [ ] 3.2 Add post-completion intent detection (question vs. update vs. new child)
- [ ] 3.3 Handle registration updates in completed conversations
- [ ] 3.4 Update prompts to guide LLM for post-completion states

## 4. Implement Versioned Registration Storage

- [ ] 4.1 Create versioned storage structure for registrations
- [ ] 4.2 Implement `save_registration_version()` method
- [ ] 4.3 Implement `get_registration_history()` method
- [ ] 4.4 Track change summary (which fields changed) between versions
- [ ] 4.5 Update `save_registration()` to use versioning for updates

## 5. Update Admin Notifications

- [ ] 5.1 Add `notify_registration_update()` method to `AdminNotifier`
- [ ] 5.2 Create email template for update notifications (include diff)
- [ ] 5.3 Distinguish "New Registration" vs "Registration Updated" subjects
- [ ] 5.4 Include version number in update notifications

## 6. Update Reminders

- [ ] 6.1 Remove expiration warnings from reminder templates
- [ ] 6.2 Update reminder messages to encourage completion without deletion threat
- [ ] 6.3 Remove any scheduled data cleanup jobs (if present)

## 7. Update Specs and Documentation

- [ ] 7.1 Update `conversation-flow.md` to remove expiration language
- [ ] 7.2 Update `channel-config.md` state management section
- [ ] 7.3 Update sample responses to remove expiration references
- [ ] 7.4 Update CLAUDE.md with new conversation matching behavior

## 8. Testing

- [ ] 8.1 Test: New email creates new conversation
- [ ] 8.2 Test: Follow-up email (same address, different thread) continues conversation
- [ ] 8.3 Test: Post-completion question is answered correctly
- [ ] 8.4 Test: Post-completion update creates new version and notifies admin
- [ ] 8.5 Test: Email address normalization works correctly
