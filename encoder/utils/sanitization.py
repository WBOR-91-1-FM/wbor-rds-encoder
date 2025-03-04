"""
Methods to sanitize text for broadcast and comply with SmartGen Mini requirements.
"""

from utils.logging import configure_logging

logger = configure_logging(__name__)


def sanitize_text(raw_text: str) -> str:
    """
    Strip or replace disallowed characters, remove or filter out profane words.

    We need to reduce the character set to the ASCII range and ensure that the
    text is safe for broadcast. This may involve:
    - Removing control characters
    - Filtering out profanity
    - Truncating to a safe length
    - Converting to uppercase
    - Replacing special characters with safe equivalents
    """
    logger.debug("Sanitizing text: `%s`", raw_text)
    # Example naive sanitization
    sanitized = raw_text.upper()
    # SmartGen TEXT= limit is 64 characters
    return sanitized[:64]
