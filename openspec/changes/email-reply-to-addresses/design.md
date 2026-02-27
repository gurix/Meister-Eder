## Context

The system sends emails in two directions with two different purposes:

- **Outbound to parents**: The AI agent sends conversational replies and, upon registration completion, a confirmation email summarising the registration and next steps.
- **Outbound to admins/leaders**: The system sends a notification email to the relevant playgroup leader(s) and Markus Graf (CC) immediately after a registration is completed.

Email clients use the `Reply-To` header (falling back to `From`) to determine where a reply is directed. Without explicit `Reply-To` headers, all replies from both parents and admins flow back to the registration system's inbox — which is correct for ongoing conversation but wrong for post-completion follow-up.

## Goals / Non-Goals

**Goals:**
- Ensure parent replies to completion confirmation emails reach the admin (Markus Graf) rather than the agent pipeline
- Ensure admin/leader replies to registration notification emails reach the registering parent directly
- Formally specify `Reply-To` behavior in the relevant capability specs

**Non-Goals:**
- Changing the `From` address of any email
- Modifying conversational email behavior (mid-registration agent ↔ parent exchanges — these correctly use the registration address as both From and effective reply target)
- Introducing any new email addresses beyond what is already configured

## Decisions

### 1. Confirmation Email Reply-To: Admin Address

**Decision**: Set `Reply-To: spielgruppen@familien-verein.ch` (Markus Graf) on all confirmation emails sent to parents after registration completion.

**Rationale**: Once registration is complete, the conversation is over. Any parent reply is a human follow-up question — it should reach a human admin, not re-enter the agent pipeline. Markus Graf is the designated central admin contact and is already CC'd on all notifications.

**Alternatives considered**:
- No Reply-To (default to From): Parent replies re-enter the agent inbox and may trigger unwanted agent responses post-completion.
- Reply-To the relevant playgroup leader (Andrea/Barbara): More targeted, but leaders vary by registration type and parents may not know who they're reaching. The central admin address is simpler and consistent.

### 2. Notification Email Reply-To: Parent Address

**Decision**: Set `Reply-To: <parent email>` on all registration notification emails sent to admins/leaders.

**Rationale**: The primary reason admins reply to a notification is to contact the parent (e.g., to confirm a spot, ask a clarifying question, or provide further instructions). Pre-filling Reply-To with the parent's address eliminates a copy-paste step and reduces errors. This is already noted informally in `notification-template.md` — this change formalises it as a spec requirement.

**Alternatives considered**:
- No Reply-To (default to From/registration inbox): Admins must manually copy the parent's email to reply, adding friction.

## Risks / Trade-offs

**Admin confirmation email replies go to Markus, not directly to the leader**: For outdoor registrations, the leader is Barbara Gross, but parent replies to confirmation go to Markus Graf. This is acceptable — Markus can forward as needed, and having a single consistent Reply-To is simpler than routing by playgroup type.

**Mid-registration vs. post-registration distinction**: Conversational emails (mid-registration) should NOT set Reply-To to the admin — they must continue flowing back to the registration inbox so the agent can process them. The implementation must apply the admin Reply-To only to the final confirmation email, not to all outbound agent emails.
