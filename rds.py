import asyncio
import logging
import os
import json
import socket

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
        f"Missing required environment variables: {', '.join(missing_vars)}"
    )

RDS_ENCODER_PORT = int(RDS_ENCODER_PORT)


async def connect_smartgen():
    """Maintains a persistent TCP socket to the SmartGen Mini."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((RDS_ENCODER_HOST, RDS_ENCODER_PORT))
        sock.settimeout(
            5
        )  # If any socket operation (like connect, recv, or send) takes longer than 5 seconds, a socket.timeout exception will be raised
        logger.info(
            "Connected to SmartGen Mini RDS encoder at %s:%d",
            RDS_ENCODER_HOST,
            RDS_ENCODER_PORT,
        )
        return sock
    except Exception as e:
        logger.error(
            "Failed to connect to SmartGen Mini RDS encoder at %s:%d: %s",
            RDS_ENCODER_HOST,
            RDS_ENCODER_PORT,
            e,
        )
        sock.close()
        raise


def send_command(sock: socket.socket, command: str, value: str):
    """
    Send a line like `TEXT=HELLO`.
    Wait for `OK` or `NO` from the encoder.
    """
    message = f"{command}={value}\r\n"
    logger.info("Sending to encoder: %s", message.strip())
    try:
        sock.sendall(message.encode("ascii", errors="ignore"))

        response = sock.recv(1024).decode("ascii", errors="ignore").strip()
        # 1024 is NOT the receiving port, but instead the maximum number of bytes to receive
        logger.debug("Encoder response: %s", response)
        response = response.splitlines()
        if response[-1] != "OK":
            logger.warning(
                "Command '%s=%s' did not return `OK`. Response was: %s",
                command,
                value,
                response,
            )
    except Exception as e:
        logger.error("Failed to send command to encoder: %s", e)


def sanitize_text(raw_text: str) -> str:
    """
    Strip or replace disallowed characters, remove or filter out profane words.
    """
    # Example naive sanitization
    sanitized = raw_text.upper()
    return sanitized[:64]  # SmartGen TEXT= limit is 64


async def on_message(
    message: aio_pika.IncomingMessage,
    sock: socket.socket,
    channel: aio_pika.Channel,
    preview_exchange: aio_pika.Exchange,
):
    async with message.process():
        raw_payload = message.body.decode("utf-8")
        logger.debug("Received track payload: %s", raw_payload)

        # If payload is JSON, parse it accordingly
        # track_info = json.loads(raw_payload)
        # title = track_info.get("title", "")
        # artist = track_info.get("artist", "")

        # For demonstration, treat entire message as a title
        title = raw_payload
        text_value = sanitize_text(title)

        # 1) Send RDS TEXT=
        send_command(sock, "TEXT", text_value)

        # 2) Send RT+TAG=
        # Example payload for RT+ (title, artist)
        rt_plus_payload = f"TITLE:{text_value};ARTIST:UNKNOWN"
        send_command(sock, "RT+TAG", rt_plus_payload)

        # 3) Publish a "preview" message to another exchange
        preview_body = {"title": text_value, "artist": "UNKNOWN"}
        preview_message = aio_pika.Message(
            body=json.dumps(preview_body).encode("utf-8")
        )
        await preview_exchange.publish(
            message=preview_message, routing_key=PREVIEW_ROUTING_KEY
        )
        logger.info(
            "Published preview to exchange %s with routing key %s",
            PREVIEW_EXCHANGE,
            PREVIEW_ROUTING_KEY,
        )


async def main():
    # 1) Connect to encoder
    sock = await connect_smartgen()

    # 2) Connect to RabbitMQ
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST, login=RABBITMQ_USER, password=RABBITMQ_PASS
    )
    channel = await connection.channel()

    # 3) Ensure queue is declared (in case not declared externally)
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    # 4) Declare the preview exchange
    preview_exchange = await channel.declare_exchange(
        PREVIEW_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
    )

    logger.info("Waiting for messages in queue '%s' ...", RABBITMQ_QUEUE)

    # 5) Start consuming
    await queue.consume(lambda msg: on_message(msg, sock, channel, preview_exchange))

    # Keep the event loop running
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        sock.close()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
