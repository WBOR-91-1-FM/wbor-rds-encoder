"""
This module provides functionality to consume track metadata from a RabbitMQ queue
and transmit it to a SmartGen Mini RDS encoder for real-time updates of Radio Data
System (RDS) text. It manages a persistent TCP socket connection to the encoder,
automatically reconnecting on failures to maintain a reliable link.

Key components and responsibilities include:

1. SmartGenConnectionManager:
   - Maintains a persistent TCP connection to the SmartGen Mini RDS encoder.
   - Automatically attempts reconnection using an exponential backoff strategy when
     the connection fails.
   - Exposes a method to send commands (e.g., updating RDS text) and handles the
     encoder's response.

2. RabbitMQ Integration:
   - Establishes a robust async connection to RabbitMQ and listens on a designated
     queue for incoming track metadata.
   - Received spin data is sent to the SmartGen encoder.
   - Optionally publishes a "preview" message to a configured exchange for further
     processing or logging.

3. Message Handling:
   - Processes each incoming message using the `on_message` coroutine, extracting
     relevant fields (like title and artist).
   - Sends commands to the RDS encoder using `SmartGenConnectionManager`.
   - Handles error scenarios gracefully, logging or requeueing messages as necessary.

4. Application Entry Point:
   - `main()` orchestrates the lifecycle of the encoder connection and the RabbitMQ
     consumer.
   - Keeps the event loop running indefinitely until interrupted or otherwise halted,
     ensuring that RDS updates are continuously processed in real time.

Environment variables (e.g., RABBITMQ_HOST, RDS_ENCODER_HOST) must be provided to
configure the module correctly. Missing or invalid variables result in an
EnvironmentError at startup.
"""

import asyncio
import logging
import os
import json
import socket
from contextlib import suppress

import aio_pika
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("aiormq").setLevel(logging.INFO)
logging.getLogger("aio_pika").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.INFO)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")

# Consuming from this queue
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE")

# Publishing to this exchange (optional, for a "preview" feature)
PREVIEW_EXCHANGE = os.getenv("RABBITMQ_PREVIEW_EXCHANGE")
PREVIEW_ROUTING_KEY = os.getenv("RABBITMQ_PREVIEW_ROUTING_KEY")

RDS_ENCODER_HOST = str(os.getenv("RDS_ENCODER_HOST"))
RDS_ENCODER_PORT = os.getenv("RDS_ENCODER_PORT")

required_env_vars = [
    RABBITMQ_HOST,
    RABBITMQ_USER,
    RABBITMQ_PASS,
    RABBITMQ_QUEUE,
    PREVIEW_EXCHANGE,
    PREVIEW_ROUTING_KEY,
    RDS_ENCODER_HOST,
    RDS_ENCODER_PORT,
]

if not all(required_env_vars):
    missing_vars = [
        var
        for var in [
            "RABBITMQ_HOST",
            "RABBITMQ_USER",
            "RABBITMQ_PASS",
            "RABBITMQ_QUEUE",
            "PREVIEW_EXCHANGE",
            "PREVIEW_ROUTING_KEY",
            "RDS_ENCODER_HOST",
            "RDS_ENCODER_PORT",
        ]
        if not locals()[var]
    ]
    raise EnvironmentError(
        f"Missing required environment variables: `{', '.join(missing_vars)}`"
    )

RDS_ENCODER_PORT = int(RDS_ENCODER_PORT)

# Content type codes
ARTIST_TAG = "04"
TITLE_TAG = "01"


class SmartGenConnectionManager:
    """
    Maintains a persistent TCP socket to the SmartGen Mini RDS encoder,
    with automatic reconnection logic.
    """

    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._stop = False
        self._reconnect_task = None

    async def start(self):
        """
        Launch a background task to ensure self.sock remains connected.
        """
        # Use create_task to start a background reconnection manager.
        self._reconnect_task = asyncio.create_task(self._manage_connection())

    async def stop(self):
        """
        Signal the background manager to stop and close socket.
        """
        self._stop = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._reconnect_task

        if self.sock:
            self.sock.close()
            self.sock = None
            logger.info("Closed SmartGen socket.")

    async def _manage_connection(self):
        """
        Continuously ensure there's a valid socket connection to the encoder.
        If the connection drops, retry with exponential backoff.
        """
        backoff = 1
        while not self._stop:
            if self.sock is None:
                try:
                    logger.info("Attempting to connect to SmartGen RDS encoder...")
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((self.host, self.port))
                    sock.settimeout(self.timeout)
                    self.sock = sock
                    logger.info(
                        "Connected to SmartGen Mini RDS encoder at `%s:%d`",
                        self.host,
                        self.port,
                    )
                    # Reset backoff on successful connect
                    backoff = 1
                except Exception as e:
                    logger.error(
                        "Failed to connect to SmartGen RDS encoder at `%s:%d`: %s",
                        self.host,
                        self.port,
                        e,
                    )
                    # Wait before retrying
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)  # Exponential backoff up to 1 min
            else:
                # If we already have a socket, just idle until it fails or we're stopped.
                await asyncio.sleep(1)

    def send_command(self, command: str, value: str):
        """
        Send a line like `TEXT=HELLO` to the encoder and wait for `OK` or `NO`.
        Raises an exception if no socket is available or if the send fails.
        """
        if not self.sock:
            raise ConnectionError("SmartGen socket is not connected.")

        message = f"{command}={value}\r\n"
        logger.info("Sending to encoder: `%s`", message.strip())
        try:
            self.sock.sendall(message.encode("ascii", errors="ignore"))
            response = self.sock.recv(1024).decode("ascii", errors="ignore").strip()
            logger.debug("Encoder response: `%s`", response)
            response_lines = response.splitlines()
            if not response_lines:
                logger.warning("No response from encoder.")
            elif response_lines[-1] != "OK":
                logger.warning(
                    "Command `%s=%s` did not return `OK`. Response was: `%s`",
                    command,
                    value,
                    response_lines,
                )
                raise RuntimeError(f"Command `{command}={value}` failed: `{response}`")
        except socket.error as e:
            logger.error("Socket error while sending command to encoder: `%s`", e)
            # Attempt to close so the manager reconnects
            self.sock.close()
            self.sock = None
            raise

        except Exception as e:
            logger.error("General error in send_command: `%s`", e)
            # We can also close so the manager attempts a reconnect
            self.sock.close()
            self.sock = None
            raise


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
    # Example naive sanitization
    sanitized = raw_text.upper()
    # SmartGen TEXT= limit is 64 characters
    return sanitized[:64]


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
    rt_plus_payload = f"{ARTIST_TAG},{start_artist},{len_artist},{TITLE_TAG},{start_title},{len_title},{running_bit},{timeout}"

    return rt_plus_payload


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

        track_info = json.loads(raw_payload).get("spin", {})
        title = track_info.get("title", "")
        artist = track_info.get("artist", "")
        duration_seconds = track_info.get("duration", 0)
        if not title and not artist:
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


async def main():
    """
    Entry point for the application. Orchestrates the lifecycle of the SmartGen
    connection manager and the RabbitMQ consumer.
    """
    # 1) Create a SmartGen connection manager and start its reconnection task
    smartgen_mgr = SmartGenConnectionManager(RDS_ENCODER_HOST, RDS_ENCODER_PORT)
    await smartgen_mgr.start()

    # 2) Connect to RabbitMQ with robust connection (automatically tries to reconnect)
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST, login=RABBITMQ_USER, password=RABBITMQ_PASS
    )
    channel = await connection.channel()

    # 3) Ensure queue is declared (in case not declared externally)
    # The queue will be durable, so it survives a RabbitMQ restart
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
    await queue.bind("spin_exchange", routing_key="spinitron.#")

    # 4) Declare the preview exchange
    preview_exchange = await channel.declare_exchange(
        PREVIEW_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
    )

    logger.info("Waiting for messages in queue `%s`...", RABBITMQ_QUEUE)

    # 5) Start consuming
    # On receipt of a message, call `on_message()` with the SmartGen manager and channel
    await queue.consume(
        lambda msg: on_message(msg, smartgen_mgr, channel, preview_exchange)
    )

    # Keep the event loop running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        # Close socket manager
        await smartgen_mgr.stop()
        # Close rabbit connection
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
