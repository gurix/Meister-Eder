#!/usr/bin/env python3
"""Meister-Eder — Email Registration Agent for Spielgruppe Pumuckl.

Usage
-----
Copy `.env.example` to `.env`, fill in your credentials, then run:

    python main.py

The agent polls the configured IMAP inbox every POLL_INTERVAL seconds,
processes new messages, and replies via SMTP.

Environment variables (see .env.example for full list):
  AI_MODEL             litellm model string  (default: anthropic/claude-opus-4-6)
  ANTHROPIC_API_KEY    Required for Anthropic models
  OPENAI_API_KEY       Required for OpenAI models
  IMAP_HOST            IMAP server hostname
  IMAP_PORT            IMAP port             (default: 993)
  IMAP_USERNAME        Email account username
  IMAP_PASSWORD        Email account password
  SMTP_HOST            SMTP server hostname
  SMTP_PORT            SMTP port             (default: 587)
  REGISTRATION_EMAIL   Sender address shown to parents
  DATA_DIR             Directory for JSON storage  (default: data/)
  POLL_INTERVAL        Seconds between inbox polls (default: 60)
"""

import logging
import sys
import time

from src.agent.core import EmailAgent
from src.channels.email_channel import EmailChannel
from src.config import Config
from src.knowledge_base.loader import KnowledgeBase
from src.notifications.notifier import AdminNotifier
from src.storage.json_store import ConversationStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def build_components(config: Config):
    """Instantiate and wire together all agent components."""
    logger.info("AI model: %s", config.ai_model)

    kb = KnowledgeBase(config.knowledge_base_dir)
    store = ConversationStore(config.data_dir)

    notifier = AdminNotifier(
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        username=config.imap_username,
        password=config.imap_password,
        use_tls=config.smtp_use_tls,
        from_email=config.registration_email,
    )

    agent = EmailAgent(model=config.ai_model, kb=kb, store=store, notifier=notifier)

    channel = EmailChannel(
        imap_host=config.imap_host,
        imap_port=config.imap_port,
        smtp_host=config.smtp_host,
        smtp_port=config.smtp_port,
        username=config.imap_username,
        password=config.imap_password,
        use_ssl=config.imap_use_ssl,
        use_tls=config.smtp_use_tls,
        registration_email=config.registration_email,
    )

    return agent, channel


def run_poll_loop(agent: EmailAgent, channel: EmailChannel, poll_interval: int) -> None:
    """Main polling loop — never returns unless interrupted."""
    logger.info("Agent started. Polling every %ds for new messages.", poll_interval)

    while True:
        try:
            messages = channel.fetch_unread_messages()

            for msg in messages:
                logger.info("Processing message from %s", msg["from"])
                try:
                    reply = agent.process_message(
                        parent_email=msg["from"],
                        message_text=msg["body"],
                        inbound_message_id=msg["message_id"],
                    )
                    if reply:
                        channel.send_reply(
                            to=msg["from"],
                            subject=msg["subject"],
                            body=reply,
                            in_reply_to=msg["message_id"],
                            references=msg["references"],
                        )
                except Exception:
                    logger.exception(
                        "Unhandled error processing message from %s", msg["from"]
                    )

        except KeyboardInterrupt:
            logger.info("Shutdown requested — stopping.")
            break
        except Exception:
            logger.exception("Unexpected error in poll loop")

        time.sleep(poll_interval)


def main() -> None:
    config = Config.from_env()

    if not config.imap_host:
        logger.error(
            "IMAP_HOST is not set. "
            "Copy .env.example to .env and fill in your email credentials."
        )
        sys.exit(1)

    agent, channel = build_components(config)
    run_poll_loop(agent, channel, config.poll_interval)


if __name__ == "__main__":
    main()
