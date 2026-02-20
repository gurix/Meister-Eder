## Context

The current implementation on branch `claude/email-agent-multi-model-c3ShZ` uses email threading headers to identify conversations. This is fragile—parents often send new emails instead of replying, breaking the thread association.

**Current behavior:**
```
Email 1 (new): "I want to register" → Thread ID: <abc@gmail.com> → New conversation
Email 2 (new): "Her name is Emma"  → Thread ID: <xyz@gmail.com> → NEW conversation (context lost!)
```

**Desired behavior:**
```
Email 1: parent@example.com → Conversation for parent@example.com (new)
Email 2: parent@example.com → Conversation for parent@example.com (continue)
```

## Goals / Non-Goals

**Goals:**
- Reliable conversation continuity regardless of email threading behavior
- Simple mental model: one email address = one conversation
- Support post-completion interactions (questions and updates)
- Audit trail for registration changes

**Non-Goals:**
- Supporting multiple registrations per email address (one parent, multiple children handled in single conversation)
- Anonymous/guest conversations (email address is the identity)
- Complex merge logic for duplicate conversations

## Decisions

### 1. Conversation Key: Email Address

**Decision**: Use normalized sender email address as the conversation key.

**Rationale**: Email address is the only reliable identifier across email threads. Parents may use different devices, email clients, or simply compose new messages.

**Normalization**: Lowercase, trim whitespace. Consider: `maria@Example.com` = `maria@example.com`

**Trade-off**: A parent using multiple email addresses would have multiple conversations. This is acceptable—different address = different identity from the system's perspective.

### 2. Thread ID Usage

**Decision**: Store thread IDs for reply headers only, not for conversation matching.

**Rationale**: Thread IDs (`Message-ID`, `In-Reply-To`, `References`) are still needed for proper email client threading (so replies appear in the same thread in Gmail/Outlook). But matching uses email address.

**Implementation**: When sending a reply, use the most recent inbound message's ID for `In-Reply-To`.

### 3. No Data Expiration

**Decision**: Remove the 30-day retention limit for email conversations.

**Rationale**: With email-address-based matching, the conversation is a permanent record. There's no reason to delete it—if the parent returns in 6 months, their data should still be there.

**Privacy consideration**: If GDPR deletion is requested, admin can manually remove the conversation file.

### 4. Post-Completion Intent Detection

**Decision**: When a completed registration receives a new message, use the LLM to detect intent.

**Intent categories:**
- **Question**: Parent asking about fees, schedule, policies → Answer from knowledge base
- **Update request**: Parent wants to change registration data → Collect updates, version storage, notify admin
- **New registration**: Parent wants to register another child → Continue in same conversation, add to booking

**Implementation**: Add prompt guidance for post-completion state; LLM returns `intent` field.

### 5. Versioned Registration Storage

**Decision**: Store registration updates as versions, not overwrites.

**Structure:**
```
data/registrations/
  parent_at_example.com/
    v1_2024-09-15.json  # Original registration
    v2_2024-10-03.json  # Updated (changed phone number)
    current.json        # Symlink or copy of latest
```

**Rationale**: Admin needs audit trail to see what changed and when. Original data preserved for compliance.

### 6. Admin Update Notifications

**Decision**: Send notification when registration is updated, including diff.

**Email subject**: "Registration Updated: [Child Name]"
**Body includes**: What changed (old → new), when, conversation excerpt

## Risks / Trade-offs

**Multiple children per family** → Single conversation handles this; booking can include multiple children. If needed later, extend the data model.

**Parent changes email address** → Creates new conversation. Admin would need to manually merge if needed. Acceptable for MVP.

**Storage growth** → Without expiration, conversations accumulate. Monitor disk usage; consider archival strategy later.

**LLM intent detection accuracy** → May misclassify. Err on the side of asking for clarification rather than making assumptions.

## Open Questions

- Should the system support explicit "delete my data" requests via email? (GDPR)
- Should reminders stop after a certain count, or continue indefinitely for incomplete registrations?
