"""
This module provides functionality to consume song metadata from a RabbitMQ queue
and transmit it to a SmartGen Mini RDS encoder for real-time updates of Radio Data
System (RDS) & RDS+ text. It manages a persistent TCP socket connection to the 
encoder, automatically reconnecting on failures to maintain a reliable link.

Key components and responsibilities include:

1. SmartGenConnectionManager:
    - Maintains a persistent TCP connection to the SmartGen Mini RDS encoder.
    - Automatically attempts reconnection using an exponential backoff strategy when
        the connection fails.
    - Exposes a method to send commands and handles the encoder's response.

2. RabbitMQ Integration:
    - Establishes a robust async connection to RabbitMQ and listens on a designated
        queue for incoming track metadata.
    - Received spin data is processed and then sent to the SmartGen encoder.
    - Optionally publishes a "preview" message to a configured exchange for further
        processing or logging.

3. Message Handling:
    - Processes each incoming message using the `on_message` coroutine, extracting
        relevant fields (like title and artist).
    - Sanitizes and formats the text for broadcast, ensuring it conforms to the
        SmartGen Mini's requirements (e.g., length, character set), and profanity 
        filtering.
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

from config import (
    RDS_ENCODER_HOST,
    RDS_ENCODER_PORT,
)
from utils.logging import configure_logging
from smartgen import SmartGenConnectionManager
from rabbitmq_consumer import consume_rabbitmq

logging.root.handlers = []
logger = configure_logging()


async def main():
    """
    Entry point for the application. Orchestrates the lifecycle of the SmartGen
    connection manager and the RabbitMQ consumer.
    """
    smartgen_mgr = SmartGenConnectionManager(RDS_ENCODER_HOST, RDS_ENCODER_PORT)
    await smartgen_mgr.start()

    connection = await consume_rabbitmq(smartgen_mgr)

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        await smartgen_mgr.stop()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
