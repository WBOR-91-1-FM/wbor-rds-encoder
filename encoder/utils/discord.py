"""
Module for sending status messages to Discord using webhooks.
https://github.com/lovvskillz/python-discord-webhook
"""

from discord_webhook import AsyncDiscordWebhook

from config import (
    DISCORD_WEBHOOK_URL,
)


async def send_webhook(message):
    """
    Send a message to Discord using a webhook.
    """
    webhook = AsyncDiscordWebhook(url=DISCORD_WEBHOOK_URL, content=message)
    await webhook.execute()
