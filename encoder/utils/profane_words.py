"""
Load the `words.json` file and filter out profane words from the input text.
"""

import json


def filter_profane_words(text: str) -> str:
    """
    Filter out profane words from the input text.
    """
    with open("utils/words.json", "r", encoding="utf-8") as file:
        profane_words = json.load(file)

    # Iterate over the list of profane words and replace them with
    # asterisks of the same length if found in the input text.
    for word in profane_words:
        text = text.replace(word, "*" * len(word))

    return text
