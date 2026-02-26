# Meister-Eder

AI-powered conversational registration agent for **Spielgruppe Pumuckl** (Familienverein Fällanden, Switzerland). Parents register their child and ask questions via email — the agent handles the conversation, validates all required fields, and notifies the playgroup admin on completion.

Replaces a static Google Forms workflow with an AI agent that guides parents through child registration via natural conversation — over email or a web chat interface.

## What it does

- Guides parents through registration one question at a time, adapting to their responses
- Answers questions about fees, schedule, and policies from a curated knowledge base
- Validates and stores completed registrations as structured data
- Notifies playgroup administrators on completion, routed by playgroup type
- Responds in any language the parent uses; defaults to German

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
| `AI_MODEL` | Primary model (litellm string), e.g. `anthropic/claude-opus-4-6` |
| `IMAP_HOST` | IMAP server hostname for receiving parent emails |
| `IMAP_USERNAME` | Email account username |
| `IMAP_PASSWORD` | Email account password |
| `SMTP_HOST` | SMTP server hostname for sending replies |
| `REGISTRATION_EMAIL` | Sender address shown to parents |

The API key variable depends on your chosen provider — see [Switching AI providers](#switching-ai-providers) below.

### Optional variables

| Variable | Default | Description |
|---|---|---|
| `SIMPLE_MODEL` | _(falls back to `AI_MODEL`)_ | Lightweight model for simple tasks (e.g. email-label translation). Can be from a different provider. Logs a warning if unset. |
| `THINKING_BUDGET` | _(disabled)_ | Token budget for extended thinking — Anthropic models only. Recommended: `8000`. |
| `IMAP_PORT` | `993` | IMAP port |
| `IMAP_USE_SSL` | `true` | Use SSL for IMAP |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USE_TLS` | `true` | Use STARTTLS for SMTP |
| `CHAINLIT_HOST` | `localhost` | Host the web chat binds to. Set to `0.0.0.0` to expose externally. |
| `DATA_DIR` | `data/` | Directory for conversation state and completed registrations |
| `KNOWLEDGE_BASE_DIR` | `openspec/…/knowledge-base` | Path to admin-editable knowledge base markdown files |
| `POLL_INTERVAL` | `60` | Seconds between inbox polls (only used when running as a daemon) |

### Switching AI providers

Both `AI_MODEL` and `SIMPLE_MODEL` use [litellm](https://docs.litellm.ai/docs/providers) model strings — any supported provider works without code changes. The two models can be from different providers:

```bash
# Anthropic for both (default)
AI_MODEL=anthropic/claude-opus-4-6
SIMPLE_MODEL=anthropic/claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini for both
AI_MODEL=gemini/gemini-3-pro-preview
SIMPLE_MODEL=gemini/gemini-3-flash-preview
GEMINI_API_KEY=...

# Mixed providers
AI_MODEL=gemini/gemini-3-pro-preview
SIMPLE_MODEL=anthropic/claude-haiku-4-5-20251001
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

## Running

### Web chat

Start the web chat interface:

```bash
uv run chainlit run chat_app.py
```

The chat opens at **http://localhost:8000** by default.

To listen on a different port or host:

```bash
uv run chainlit run chat_app.py --port 8080 --host 0.0.0.0
```

**Minimum required env vars for the web chat:**

| Variable | Description |
|---|---|
| `AI_MODEL` | litellm model string, e.g. `anthropic/claude-opus-4-6` |
| `ANTHROPIC_API_KEY` | (or the key for your chosen provider) |
| `SMTP_HOST` / `SMTP_PORT` | For admin notification emails on registration completion |
| `IMAP_USERNAME` / `IMAP_PASSWORD` | Used as SMTP credentials |
| `ADMIN_EMAIL_INDOOR` | Andrea Sigrist — notified when indoor group is booked |
| `ADMIN_EMAIL_OUTDOOR` | Barbara Gross — notified when outdoor group is booked |
| `ADMIN_EMAIL_CC` | Markus Graf — always CC'd on notifications |

IMAP variables (`IMAP_HOST`, etc.) are not required for the web chat — only for the email channel.

### Email channel

The email agent polls an IMAP inbox and replies via SMTP. No web server required.

**As a cron job (recommended)**

Schedule with cron and use `flock` to prevent overlapping runs:

```cron
*/5 * * * * flock -n /tmp/meister-eder-email.lock uv run python main.py
```

`flock -n` exits immediately if a previous run is still in progress, so the script is always safe to schedule aggressively.

**Manually**

```bash
uv run python main.py
```

### Running both channels together

The web chat and email agent are independent processes — run them side by side:

```bash
# Terminal 1 — web chat
uv run chainlit run chat_app.py

# Terminal 2 — email polling
uv run python main.py
```

Completed registrations from both channels are stored in the same `DATA_DIR` (default: `data/`) and share the same admin notification configuration.

## Development

### Running tests

```bash
uv run pytest
```

All tests are unit tests — no network access or API keys required.

### Knowledge base

The agent answers parent questions from markdown files in the knowledge base directory. These files are designed to be edited directly by playgroup admins — no code changes needed to update fees, schedules, or policies.

### Adding a new AI provider

Set `AI_MODEL` (and optionally `SIMPLE_MODEL`) to any [litellm-supported model string](https://docs.litellm.ai/docs/providers) and set the corresponding API key environment variable. No code changes required.
