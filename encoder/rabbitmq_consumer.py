"""
RabbitMQ consumer module.
"""

import aio_pika
from aio_pika import ExchangeType
from config import (
    RABBITMQ_HOST,
    RABBITMQ_USER,
    RABBITMQ_PASS,
    RABBITMQ_EXCHANGE,
    RABBITMQ_QUEUE,
    PREVIEW_EXCHANGE,
)
from utils.logging import configure_logging
from message_handler import on_message
from smartgen import SmartGenConnectionManager

logger = configure_logging(__name__)


async def consume_rabbitmq(smartgen_mgr: SmartGenConnectionManager):
    """Connects to RabbitMQ and consumes messages."""
    connection = await aio_pika.connect_robust(
        host=RABBITMQ_HOST, login=RABBITMQ_USER, password=RABBITMQ_PASS
    )
    channel = await connection.channel()

    # 1) Declare the spin_exchange explicitly
    await channel.declare_exchange(RABBITMQ_EXCHANGE, ExchangeType.TOPIC, durable=True)

    # 2) Declare the queue (durable so it survives a RabbitMQ restart)
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    # 3) Bind the queue to the newly declared exchange
    await queue.bind("spin_exchange", routing_key="spinitron.#")

    # Declare the preview exchange
    preview_exchange = await channel.declare_exchange(
        PREVIEW_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True
    )

    logger.info("Waiting for messages in queue `%s`...", RABBITMQ_QUEUE)

    await queue.consume(
        lambda msg: on_message(msg, smartgen_mgr, channel, preview_exchange)
    )

    return connection
