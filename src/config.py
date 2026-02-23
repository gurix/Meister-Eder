"""Configuration loaded from environment variables."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


@dataclass
class Config:
    # Primary model for conversation with parents — litellm format.
    # The matching API key must be set as an env var (ANTHROPIC_API_KEY, OPENAI_API_KEY, …).
    # Example: "anthropic/claude-opus-4-6", "google/gemini-2.0-flash", "openai/gpt-4o"
    ai_model: str = "anthropic/claude-opus-4-6"

    # Lightweight model for simple tasks such as email-label translation.
    # Can be from a different provider than ai_model.
    # If not configured (SIMPLE_MODEL env var unset), falls back to ai_model with a warning.
    # Example: "anthropic/claude-haiku-4-5-20251001", "openai/gpt-4o-mini"
    simple_model: str = ""

    # Email — IMAP (receiving)
    imap_host: str = ""
    imap_port: int = 993
    imap_username: str = ""
    imap_password: str = ""
    imap_use_ssl: bool = True

    # Email — SMTP (sending)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True

    # Registration email address shown to parents
    registration_email: str = ""

    # Admin notification routing.
    # Each leader receives mail only when a day in their group is booked.
    # For testing, point all three to your own address.
    admin_email_indoor: str = ""   # Indoor leader (Andrea Sigrist) — To when indoor booked
    admin_email_outdoor: str = ""  # Outdoor leader (Barbara Gross) — To when outdoor booked
    admin_email_cc: str = ""       # Always Cc'd (Markus Graf / admin); comma-separated if multiple

    # Storage
    data_dir: Path = field(default_factory=lambda: Path("data"))
    knowledge_base_dir: Path = field(
        default_factory=lambda: Path(
            "openspec/changes/define-project-scope/content/knowledge-base"
        )
    )

    # Polling interval in seconds
    poll_interval: int = 60

    # Extended thinking — Anthropic models only.
    # When set, enables the thinking phase before the LLM replies.
    # Recommended value: 8000 (tokens). Set to None/unset to disable.
    thinking_budget: int | None = None

    @classmethod
    def from_env(cls) -> "Config":
        ai_model = os.getenv("AI_MODEL", "anthropic/claude-opus-4-6")
        simple_model = os.getenv("SIMPLE_MODEL", "")
        if not simple_model:
            logger.warning(
                "SIMPLE_MODEL not configured — falling back to AI_MODEL (%s) for simple tasks "
                "(set SIMPLE_MODEL to a cheaper model, e.g. anthropic/claude-haiku-4-5-20251001)",
                ai_model,
            )
            simple_model = ai_model
        return cls(
            ai_model=ai_model,
            simple_model=simple_model,
            imap_host=os.getenv("IMAP_HOST", ""),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            imap_username=os.getenv("IMAP_USERNAME", ""),
            imap_password=os.getenv("IMAP_PASSWORD", ""),
            imap_use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            registration_email=os.getenv("REGISTRATION_EMAIL", ""),
            admin_email_indoor=os.getenv("ADMIN_EMAIL_INDOOR", ""),
            admin_email_outdoor=os.getenv("ADMIN_EMAIL_OUTDOOR", ""),
            admin_email_cc=os.getenv("ADMIN_EMAIL_CC", ""),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            knowledge_base_dir=Path(
                os.getenv(
                    "KNOWLEDGE_BASE_DIR",
                    "openspec/changes/define-project-scope/content/knowledge-base",
                )
            ),
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
            thinking_budget=(
                int(os.getenv("THINKING_BUDGET"))
                if os.getenv("THINKING_BUDGET")
                else None
            ),
        )
