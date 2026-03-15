"""Token utilities for the Meister-Eder application."""

import secrets
import string


def generate_resume_token() -> str:
    """Generate a 6-character alphanumeric resume token (uppercase + digits).

    Uses ``secrets.choice`` for cryptographically-safe randomness.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))
