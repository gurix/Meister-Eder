"""Token and pattern utilities for the Meister-Eder application."""

import secrets
import string

# ---------------------------------------------------------------------------
# Shared patterns
# ---------------------------------------------------------------------------

EMAIL_PATTERN = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"


def generate_resume_token() -> str:
    """Generate a 6-character alphanumeric resume token (uppercase + digits).

    Uses ``secrets.choice`` for cryptographically-safe randomness.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))
