"""
Handles incoming messages from RabbitMQ, extracting track metadata and sending
commands to the SmartGen encoder.
"""

import json
import socket
import aio_pika
from utils.logging import configure_logging
from utils.rt_plus import build_rt_plus_tag_command
from utils.sanitization import sanitize_text
from smartgen import SmartGenConnectionManager

logger = configure_logging(__name__)


async def on_message(
    message: aio_pika.IncomingMessage,
    smartgen_mgr: SmartGenConnectionManager,
    channel: aio_pika.Channel,
    preview_exchange: aio_pika.Exchange,
):
    """
    Handle incoming messages from RabbitMQ, extracting track metadata and sending
    commands to the SmartGen encoder.
    """
    async with message.process():
        raw_payload = message.body.decode("utf-8")
        logger.debug("Received track payload: `%s`", raw_payload)

        track_info = json.loads(raw_payload)
        logger.debug("Track JSON: `%s`", track_info)
        title = track_info.get("song")
        artist = track_info.get("artist")
        duration_seconds = track_info.get("duration", 0)

        if not (title and artist):
            logger.warning("Missing track info in payload: `%s`", raw_payload)
        else:
            logger.debug("Extracted track info: `%s` - `%s`", artist, title)

            # Create a TEXT value
            text = f"{artist} - {title}"
            logger.debug("Text value (pre-sanitization): `%s`", text)

            # Need to handle cases where it will exceed the 64 character limit

            # Sanitize
            sanitized_text = sanitize_text(text)
            logger.debug("Sanitized text: `%s`", sanitized_text)

            try:
                # Attempt to send commands. If the socket fails, the manager will reconnect,
                # but we may or may not want to requeue the message or handle partial failures.
                smartgen_mgr.send_command("TEXT", sanitized_text)

                # TODO: the text pagges into this function should also be sanitized
                rt_plus_payload = build_rt_plus_tag_command(
                    text, artist, title, duration_seconds
                )
                smartgen_mgr.send_command("RT+TAG", rt_plus_payload)
            except (ConnectionError, RuntimeError, socket.error) as e:
                # This means we failed to send to the encoder.
                # Either
                #   1) raise an exception so the message is requeued, or
                #   2) just log the error, acknowledging the message anyway.
                # We'll just log here and acknowledge the message.
                logger.error("Error sending commands to SmartGen encoder: `%s`", e)

        # If the previous commands succeeded, publish a preview to the exchange
        # preview_body = {"title": text_value, "artist": "UNKNOWN"}
        # preview_message = aio_pika.Message(
        #     body=json.dumps(preview_body).encode("utf-8")
        # )
        # await preview_exchange.publish(
        #     message=preview_message, routing_key=PREVIEW_ROUTING_KEY
        # )
        # logger.info(
        #     "Published preview to exchange `%s` with routing key `%s`",
        #     PREVIEW_EXCHANGE,
        #     PREVIEW_ROUTING_KEY,
        # )
