"""Conversation state model — persisted per sender email address."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .registration import RegistrationData


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatMessage:
    role: str      # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=_now)


@dataclass
class ConversationState:
    conversation_id: str                           # normalized sender email address
    language: str = "de"                           # "de" or "en"
    flow_step: str = "greeting"                    # current step in registration flow
    registration: RegistrationData = field(default_factory=RegistrationData)
    messages: list = field(default_factory=list)   # list[ChatMessage]
    parent_email: str = ""
    parent_name: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    last_activity: str = field(default_factory=_now)
    completed: bool = False
    reminder_count: int = 0
    # Most recent inbound Message-ID — used for reply threading headers only,
    # NOT for conversation matching (which is always by email address).
    last_inbound_message_id: str = ""

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "language": self.language,
            "flow_step": self.flow_step,
            "registration": self.registration.to_dict(),
            "messages": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.messages
            ],
            "parent_email": self.parent_email,
            "parent_name": self.parent_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_activity": self.last_activity,
            "completed": self.completed,
            "reminder_count": self.reminder_count,
            "last_inbound_message_id": self.last_inbound_message_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        state = cls(conversation_id=data["conversation_id"])
        state.language = data.get("language", "de")
        state.flow_step = data.get("flow_step", "greeting")
        state.registration = RegistrationData.from_dict(data.get("registration", {}))
        state.messages = [
            ChatMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m.get("timestamp", ""),
            )
            for m in data.get("messages", [])
        ]
        state.parent_email = data.get("parent_email", "")
        state.parent_name = data.get("parent_name")
        state.created_at = data.get("created_at", "")
        state.updated_at = data.get("updated_at", "")
        state.last_activity = data.get("last_activity", "")
        state.completed = data.get("completed", False)
        state.reminder_count = data.get("reminder_count", 0)
        state.last_inbound_message_id = data.get("last_inbound_message_id", "")
        return state
