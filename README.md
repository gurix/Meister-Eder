# Meister-Eder

AI-powered conversational registration system for **Spielgruppe Pumuckl**, a playgroup run by Familienverein Fällanden (Fällanden, Switzerland).

Replaces a static Google Forms workflow with an AI agent that guides parents through child registration via natural conversation — over email or a web chat interface.

## What it does

- Guides parents through registration one question at a time, adapting to their responses
- Answers questions about fees, schedule, and policies from a curated knowledge base
- Validates and stores completed registrations as structured data
- Notifies playgroup administrators on completion, routed by playgroup type
- Supports German and English; defaults to German

## Channels

| Channel | Description |
|---------|-------------|
| Web chat | Real-time, session-based |
| Email | Async, thread-tracked; reminders on days 3, 10, 25 |

## Status

Greenfield — specification complete, implementation not yet started.

## Running the Email Agent

The email agent is a plain script invoked periodically via cron — no long-running daemon needed.

### Scheduling with cron

```cron
*/5 * * * * flock -n /tmp/meister-eder-email.lock python /path/to/check_email.py
```

`flock -n` acquires an exclusive lock before running the script. If a previous run is still in progress when the next cron tick fires, the new invocation exits immediately (non-blocking). The lock is released automatically by the kernel when the process ends — even on crash — so stuck locks are not a concern.

Adjust `*/5` to whatever polling interval makes sense (e.g. `*/2` for every 2 minutes).