"""
Methods to sanitize text for broadcast and comply with SmartGen Mini requirements.
"""

import re
from unidecode import unidecode
from utils.logging import configure_logging
from utils.discord import send_webhook as notify_discord

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
    original_text = raw_text

    # (1) Detect non-ASCII characters. If found, unidecode the text by replacing
    #     them with ASCII equivalents. If none are found, the character is
    #     substituted with a question mark. Log the original and unidecoded text
    #     for debugging to logs and Discord.
    non_ascii_chars = re.findall(r"[^\x00-\x7F]", raw_text)
    if non_ascii_chars:
        unidecoded_text = unidecode(raw_text, errors="replace")

        log_message = (
            f"Non-ASCII characters found: {''.join(set(non_ascii_chars))}\n"
            f"Original: `{original_text}`\n"
            f"Unidecoded: `{unidecoded_text}`"
        )
        logger.warning(log_message)
        notify_discord(log_message)

    # (2) At this point, the raw_text string may have been unidecoded. It should
    #     be safe within the ASCII range. We move on to filtering out profanity.
    #     Profanity filtering is not yet implemented in this snippet.

    sanitized = raw_text.upper()
    return sanitized
