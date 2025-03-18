"""
Functions to build the RT+TAG payload string for the SmartGen.

RT+ requires specifying the offsets, lengths, and content type codes for each
tagged item. The format is:

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

NOTE: Only two items can be tagged at a time, so no more than two pairs of
content_type, start_pos, and length can be specified at once.

Timeout values: 0=NO TIMEOUT, 1-255 timeout in minutes

`item_running_bit`: shall be set to "1" if an item is running.
NOTE: The Item Toggle bit can't be set manually, since it's toggled
automatically each time the RT+TAG command is issued.
"""

from utils.logging import configure_logging
from config import ARTIST_TAG, TITLE_TAG

logger = configure_logging(__name__)


def build_rt_plus_tag_command(
    full_text: str, artist: str, title: str, duration: int
) -> str:
    """
    Build the RT+TAG payload string for the 'artist - title' text.

    Returns a string to pass as the `RT+TAG=` value on the SmartGen.
    """
    logger.debug("Building `RT+TAG` payload")

    # Handle missing artist or title
    if not artist:
        logger.warning("No artist provided")
        artist = "NO ARTIST"
    if not title:
        logger.warning("No title provided")
        title = "NO TITLE"

    # Set to one since we will never send a command to indicate that the
    # item is not running.
    running_bit = 1

    # Provided a duration in seconds, calculate the number of minutes
    # If the duration is 0, the resulting timeout will be 0 (no timeout),
    # meaning the text will remain on the display indefinitely.
    timeout = duration // 60  # Convert seconds to minutes

    payload_parts = []

    # Find positions for artist and title in full_text
    if artist != "NO ARTIST":
        start_artist = full_text.find(artist)
        if start_artist != -1:
            # Ensure within the bounds of 00-63
            if len(artist) > 63:
                logger.critical("Artist exceeds 63 characters, trimming: `%s`", artist)
                artist = artist[:63]
            payload_parts.append(f"{ARTIST_TAG},{start_artist},{len(artist)}")
        else:
            logger.warning("Artist not found in `full_text`: `%s`", artist)

    if title != "NO TITLE":
        start_title = full_text.find(title)
        if start_title != -1:
            # Ensure within the bounds of 00-63
            if len(title) > 63:
                logger.critical("Title exceeds 63 characters, trimming: `%s`", title)
                title = title[:63]
            payload_parts.append(f"{TITLE_TAG},{start_title},{len(title)}")
        else:
            logger.warning("Title not found in `full_text`: `%s`", title)

    # Construct final payload
    if not payload_parts:
        logger.error("No valid artist or title found in `full_text`")
        return ""

    # The third to last value has a unique bound of 31, so we need to check
    # if it exceeds this value and if so, set to 31.
    if int(payload_parts[-1].split(",")[2]) > 31:
        payload_parts[-1] = ",".join(
            # Keep the first two values, set the third to 31
            payload_parts[-1].split(",")[:2]
            + ["31"]
        )

    # Now that we've handled for potential final value exceeding 31, we can
    # join the parts together with the running bit and timeout
    rt_plus_payload = ",".join(payload_parts + [str(running_bit), str(timeout)])

    logger.debug("Final `RT+TAG` payload: `%s`", rt_plus_payload)
    return rt_plus_payload
