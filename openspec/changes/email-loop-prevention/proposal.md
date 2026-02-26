## Why

The email channel had no protection against automated message loops. When the agent sent a reply that bounced (e.g. due to an invalid recipient address or a misconfigured mail server), the bounce message arrived back in the inbox. The agent treated it as a new inbound message, generated another reply, which bounced again — creating an infinite loop.

A real incident demonstrated this: a `MAILER-DAEMON@tacitus2.sui-inter.net` bounce began accumulating replies indefinitely, consuming LLM quota and filling the inbox with noise while the agent remained unaware it was talking to an automated system.

Beyond bounce loops, any automated sender — out-of-office replies, mailing-list software, delivery status notifications — can trigger this pattern if the agent replies to them. The system needs to recognise non-human senders and refuse to reply.

A secondary risk: a legitimate but very slow conversation (or a forwarding-alias loop that bypasses simple bounce detection) could still accumulate messages indefinitely. A hard cap on conversation length provides a safety net.

## What Changes

- **Detect automated/bounce senders** before the agent replies — inspect email headers and sender address patterns to identify non-human messages
- **Skip sending any reply** to automated messages — silence breaks the loop
- **Alert the admin once** when an automated sender is detected, so a human can investigate
- **Cap conversation length** at 20 inbound messages — if a conversation has not completed after 20 user messages, stop responding and alert the admin
- **Track escalation state** per conversation so admin alerts fire at most once

### Non-Goals

- Spam filtering (automated detection is specific to loop-causing patterns, not general spam)
- Automatic unsubscribe/block of senders
- Forwarding the original problem email to the admin (admin receives only a warning notification)

## Capabilities

### Modified Capabilities

- `email-channel`: Add automated/bounce sender detection; skip replies for flagged messages
- `registration-notifications`: Add loop-escalation alert type sent to admin CC address