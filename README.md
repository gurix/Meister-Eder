# Meister-Eder

AI-powered conversational registration agent for **Spielgruppe Pumuckl** (Familienverein Fällanden, Switzerland). Parents register their child and ask questions via email — the agent handles the conversation, validates all required fields, and notifies the playgroup admin on completion.

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

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (dependency manager)

## Installation

```bash
git clone https://github.com/gurix/Meister-Eder.git
cd Meister-Eder
uv sync
```

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

### Required variables

| Variable | Description |
|---|---|
| `AI_MODEL` | litellm model string, e.g. `anthropic/claude-opus-4-6` or `openai/gpt-4o` |
| `ANTHROPIC_API_KEY` | API key for Anthropic models |
| `OPENAI_API_KEY` | API key for OpenAI models (if using OpenAI) |
| `IMAP_HOST` | IMAP server hostname for receiving parent emails |
| `IMAP_USERNAME` | Email account username |
| `IMAP_PASSWORD` | Email account password |
| `SMTP_HOST` | SMTP server hostname for sending replies |
| `REGISTRATION_EMAIL` | Sender address shown to parents |

### Optional variables

| Variable | Default | Description |
|---|---|---|
| `IMAP_PORT` | `993` | IMAP port |
| `IMAP_USE_SSL` | `true` | Use SSL for IMAP |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USE_TLS` | `true` | Use STARTTLS for SMTP |
| `DATA_DIR` | `data/` | Directory for conversation state and completed registrations |
| `KNOWLEDGE_BASE_DIR` | `openspec/…/knowledge-base` | Path to admin-editable knowledge base markdown files |
| `POLL_INTERVAL` | `60` | Seconds between inbox polls (only used when running as a daemon) |

### Switching AI providers

`AI_MODEL` uses [litellm](https://docs.litellm.ai/docs/providers) model strings — any supported provider works without code changes:

```bash
# Anthropic (default)
AI_MODEL=anthropic/claude-opus-4-6
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
AI_MODEL=openai/gpt-4o
OPENAI_API_KEY=sk-...

# Google Gemini
AI_MODEL=gemini/gemini-2.0-flash
GEMINI_API_KEY=...
```

## Running

### As a cron job (recommended)

The agent is a plain script — no long-running daemon needed. Schedule it with cron and use `flock` to prevent overlapping runs:

```cron
*/5 * * * * flock -n /tmp/meister-eder-email.lock uv run python main.py
```

`flock -n` exits immediately if a previous run is still in progress, so the script is always safe to schedule aggressively.

### Manually

```bash
uv run python main.py
```

## Development

### Running tests

```bash
uv run pytest
```

All tests are unit tests — no network access or API keys required.

### Knowledge base

The agent answers parent questions from markdown files in the knowledge base directory. These files are designed to be edited directly by playgroup admins — no code changes needed to update fees, schedules, or policies.

### Adding a new AI provider

Set `AI_MODEL` to any [litellm-supported model string](https://docs.litellm.ai/docs/providers) and set the corresponding API key environment variable. No code changes required.
