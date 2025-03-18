"""
Load the `words.json` file and filter out profane words from the input text.

TODO: This is expensive since it is loading the `words.json` file for every
        message. Consider loading the file once and caching the profane words.
        This will reduce the overhead of reading the file for every message.
"""

import json
import re
from utils.logging import configure_logging

logger = configure_logging(__name__)


def filter_profane_words(text: str) -> str:
    """
    Filter out profane words from the input text.
    """
    try:
        with open("utils/words.json", "r", encoding="utf-8") as file:
            profane_words = json.load(file)
    except FileNotFoundError:
        logger.error("words.json file not found.")
        return text
    except json.JSONDecodeError as e:
        logger.error("Failed to decode JSON in words.json: %s", e)
        return text
    except IOError as e:
        logger.error("I/O error occurred while reading words.json: %s", e)
        return text

    for word in profane_words:
        # Match the full word using word boundaries
        pattern = r"\b" + re.escape(word) + r"\b"

        # Lowercase the text and the word for case-insensitive matching
        text = text.lower()
        if re.search(pattern, text):
            logger.info("Replacing profane word: %s", word)
        text = re.sub(pattern, lambda m: "*" * len(m.group(0)), text)

    return text
