"""
Functions to build the RT+TAG payload string for the SmartGen.
"""

from utils.logging import configure_logging
from config import ARTIST_TAG, TITLE_TAG

logger = configure_logging(__name__)


def build_rt_plus_tag_command(
    full_text: str, artist: str, title: str, duration: int
) -> str:
    """
    Build the RT+TAG payload string for the 'artist - title' text.

    RT+ requires specifying the offsets, lengths, and content type codes
    for each tagged item. The format is:

        <content_type_1>,
        <start_pos_1>,
        <length_1>,
        <content_type_2>,
        <start_pos_2>,
        <length_2>,
        <item_running_bit>,
        <timeout>

    The accepted values for each field is as follows:
    (00-63, 00-63, 00-63, 00-63, 00-63, 00-31, 0-1, 0-255).

    Timeout values: 0=NO TIMEOUT, 1-255 timeout in minutes

    NOTE: The Item Toggle bit can't be set manually, since it's toggled each time the RT+TAG
    command is issued.

    Return a string to pass as the 'RT+TAG=' value on the SmartGen.
    """
    logger.debug("Building RT+TAG payload for `%s` - `%s`", artist, title)
    running_bit = 1

    # Provided a duration in seconds, calculate the number of minutes
    # If the duration is 0, the resulting timeout will be 0 (no timeout), meaning
    # the text will remain on the display indefinitely.
    duration_minutes = duration // 60
    timeout = duration_minutes

    # Find where the artist substring starts
    # We assume the text is "ARTIST - TITLE".
    # So artist starts at index 0, with length = len(artist).
    start_artist = full_text.find(artist)
    len_artist = len(artist)

    # Find where the title substring starts
    # We expect that " - " is between them, so the title starts after that.
    start_title = full_text.find(title)
    len_title = len(title)

    # Build the payload according to the expected format
    rt_plus_payload = (
        f"{ARTIST_TAG},{start_artist},{len_artist},"
        f"{TITLE_TAG},{start_title},{len_title},{running_bit},{timeout}"
    )
    logger.debug("RT+TAG payload: `%s`", rt_plus_payload)

    return rt_plus_payload
