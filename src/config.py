"""Configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


@dataclass
class Config:
    # AI Provider
    ai_provider: str = "anthropic"  # "anthropic" or "openai"
    ai_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

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

    # Storage
    data_dir: Path = field(default_factory=lambda: Path("data"))
    knowledge_base_dir: Path = field(
        default_factory=lambda: Path(
            "openspec/changes/define-project-scope/content/knowledge-base"
        )
    )

    # Polling interval in seconds
    poll_interval: int = 60

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            ai_provider=os.getenv("AI_PROVIDER", "anthropic"),
            ai_model=os.getenv("AI_MODEL", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            imap_host=os.getenv("IMAP_HOST", ""),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            imap_username=os.getenv("IMAP_USERNAME", ""),
            imap_password=os.getenv("IMAP_PASSWORD", ""),
            imap_use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            registration_email=os.getenv("REGISTRATION_EMAIL", ""),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            knowledge_base_dir=Path(
                os.getenv(
                    "KNOWLEDGE_BASE_DIR",
                    "openspec/changes/define-project-scope/content/knowledge-base",
                )
            ),
            poll_interval=int(os.getenv("POLL_INTERVAL", "60")),
        )
