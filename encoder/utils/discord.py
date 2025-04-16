"""
Send status messages to Discord using webhooks.
https://github.com/lovvskillz/python-discord-webhook

Author: Mason Daugherty <@mdrxy>
Version: 1.0.1
Last Modified: 2025-04-15

Changelog:
    - 1.0.0 (2025-03-23): Initial release.
    - 1.0.1 (2025-04-15): Logging improvements and error handling.
"""

from config import DISCORD_AUTHOR_ICON_URL, DISCORD_WEBHOOK_URL
from discord_webhook import AsyncDiscordWebhook, DiscordEmbed
from utils.logging import configure_logging

logger = configure_logging(__name__)


class EmbedType:  # pylint: disable=too-few-public-methods
    """
    Categorize the type of message being sent.
    """

    UNIDECODE = "Unidecoded to ASCII"
    PROFANITY = "Profanity Filtered"
    METADATA = "Metadata Cleaned"


class Colors:  # pylint: disable=too-few-public-methods
    """
    Predefined colors for Discord embeds.
    """

    DEFAULT = 242424  # Default color
    SUCCESS = 3066993  # Green
    WARNING = 16776960  # Yellow
    ERROR = 15158332  # Red


async def send_basic_webhook(message: str) -> bool:
    """
    Send a message to Discord using a webhook.
    Returns True if successful, False otherwise.
    """
    webhook = AsyncDiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    response = await webhook.execute()

    if response.status_code in (200, 204):
        logger.debug("Successfully sent basic webhook message: `%s`", message)
        return True
    logger.error(
        "Failed to send basic webhook message: `%s` | Response: `%s`",
        message,
        response.status_code,
    )
    return False


async def send_embed(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    embed_type: EmbedType,
    title: str,
    title_url: str,
    desc: str,
    fields: dict,
    color: Colors = Colors.DEFAULT,
    author_icon_url: str = DISCORD_AUTHOR_ICON_URL,
    author: str = "wbor-rds-encoder",
) -> bool:
    """
    Send a message with an embed to Discord using a webhook.
    Returns True if successful, False otherwise.
    """
    webhook = AsyncDiscordWebhook(url=DISCORD_WEBHOOK_URL)
    embed = DiscordEmbed(title=title, color=color, description=desc, url=title_url)
    for field_name, field_value in fields.items():
        embed.add_embed_field(name=field_name, value=field_value)

    embed.set_author(name=author, icon_url=author_icon_url)
    embed.set_timestamp()
    webhook.add_embed(embed)
    response = await webhook.execute()

    if response.status_code in (200, 204):
        logger.debug("Successfully sent `%s` embed to Discord", embed_type)
        return True
    logger.error(
        "Failed to send `%s` embed to Discord - Status: `%s`, Response: `%s`",
        embed_type,
        response.status_code,
        response.content,
    )
    return False
