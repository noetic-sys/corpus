from typing import Callable, Dict, Any
import json
import asyncio
import aio_pika
from aio_pika import connect_robust, Message
from urllib.parse import quote

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from common.core.config import settings
from .interface import MessageQueueInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)

tracer = trace.get_tracer(__name__)
propagator = TraceContextTextMapPropagator()


# Constants
class QueueConfig:
    DEFAULT_PREFETCH_COUNT = 1
    DEFAULT_MAX_RETRIES = 1  # Simple retry once
    DLQ_MESSAGE_TTL_MS = 86400000  # 24 hours
    DLQ_MAX_LENGTH = 10000
    REDELIVERY_COUNT_HEADER = "x-redelivery-count"
    DLX_SUFFIX = ".dlx"
    DLQ_SUFFIX = ".dlq"


class RabbitMQClient(MessageQueueInterface):
    def __init__(self):
        self.connection = None
        self.channel = None
        self.host = settings.rabbitmq_host
        self.port = settings.rabbitmq_port
        self.username = settings.rabbitmq_username
        self.password = settings.rabbitmq_password
        self.vhost = settings.rabbitmq_vhost
        self._consume_task = None
        self._publisher_confirms_enabled = False

    async def _setup_dead_letter_queue(self, queue_name: str) -> Dict[str, str]:
        """Set up dead letter exchange and queue for a given queue."""
        dlx_name = f"{queue_name}{QueueConfig.DLX_SUFFIX}"
        dlq_name = f"{queue_name}{QueueConfig.DLQ_SUFFIX}"

        # Declare dead letter exchange
        await self.channel.declare_exchange(
            name=dlx_name, type=aio_pika.ExchangeType.DIRECT, durable=True
        )
        logger.info(f"Declared dead letter exchange: {dlx_name}")

        # Declare dead letter queue with TTL and size limits
        dlq = await self.channel.declare_queue(
            dlq_name,
            durable=True,
            arguments={
                "x-message-ttl": QueueConfig.DLQ_MESSAGE_TTL_MS,
                "x-max-length": QueueConfig.DLQ_MAX_LENGTH,
            },
        )
        logger.info(f"Declared dead letter queue: {dlq_name}")

        # Bind DLQ to DLX
        await dlq.bind(dlx_name, routing_key=queue_name)

        return {
            "x-dead-letter-exchange": dlx_name,
            "x-dead-letter-routing-key": queue_name,
        }

    async def connect(self) -> bool:
        try:
            # Create connection URL
            url = f"amqp://{quote(self.username)}:{quote(self.password)}@{self.host}:{self.port}/{self.vhost}"

            # Create robust connection (will auto-reconnect)
            self.connection = await connect_robust(url, loop=asyncio.get_event_loop())

            # Create channel
            self.channel = await self.connection.channel()

            # Enable publisher confirms for at-least-once delivery
            # In aio_pika, publisher confirms are automatically enabled for robust connections
            self._publisher_confirms_enabled = True

            logger.info(
                "Successfully connected to RabbitMQ (async) with publisher confirms enabled"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    async def disconnect(self) -> None:
        try:
            # Cancel any running consume task
            if self._consume_task and not self._consume_task.done():
                self._consume_task.cancel()
                try:
                    await self._consume_task
                except asyncio.CancelledError:
                    pass

            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def publish(
        self, queue: str, message: Dict[str, Any], exchange: str = ""
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # Declare queue to ensure it exists (with DLQ)
            await self.declare_queue(queue, durable=True, dlq_enabled=True)

            # Inject trace context into headers
            headers = {}
            propagator.inject(headers)

            # Create message
            message_body = json.dumps(message)
            msg = Message(
                body=message_body.encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
                headers=headers,
            )

            # Publish message
            await self.channel.default_exchange.publish(
                msg,
                routing_key=queue,
                mandatory=True,  # Ensure message is routed to at least one queue
            )

            # In aio_pika with robust connections, publisher confirms are automatic
            # The publish will raise an exception if it fails
            logger.info(f"Published message to queue {queue}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False

    async def publish_batch(
        self, queue: str, messages: list[Dict[str, Any]], exchange: str = ""
    ) -> int:
        """Publish multiple messages to a queue in a batch.

        Returns the number of successfully published messages.
        """
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # Declare queue once for the batch
            await self.declare_queue(queue, durable=True, dlq_enabled=True)

            # Inject trace context once (same for all messages in batch)
            headers = {}
            propagator.inject(headers)

            # Prepare all messages
            msg_objects = []
            for message in messages:
                message_body = json.dumps(message)
                msg = Message(
                    body=message_body.encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                    headers=headers,
                )
                msg_objects.append(msg)

            # Publish all messages asynchronously
            publish_tasks = [
                self.channel.default_exchange.publish(
                    msg,
                    routing_key=queue,
                    mandatory=True,
                )
                for msg in msg_objects
            ]

            # Await all publishes concurrently
            await asyncio.gather(*publish_tasks)

            logger.info(f"Published {len(messages)} messages to queue {queue} in batch")
            return len(messages)
        except Exception as e:
            logger.error(f"Failed to publish batch messages: {e}")
            return 0

    async def consume(
        self,
        queue: str,
        callback: Callable,
        auto_ack: bool = True,
        prefetch_count: int = 1,
    ) -> None:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # Set QoS based on prefetch_count parameter
            await self.channel.set_qos(prefetch_count=prefetch_count)
            logger.info(f"Set prefetch_count={prefetch_count} for queue {queue}")

            # Track active tasks for concurrent processing
            active_tasks: set = set()
            semaphore = asyncio.Semaphore(prefetch_count)

            # Declare queue with DLQ support
            await self.declare_queue(queue, durable=True, dlq_enabled=True)
            queue_obj = await self.channel.get_queue(queue)
            logger.info(f"Got queue object for consuming: {queue}")

            async def process_message(message: aio_pika.IncomingMessage):
                """Spawn concurrent task for message processing."""
                # Create task and track it
                task = asyncio.create_task(_handle_message(message))
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)

            async def _handle_message(message: aio_pika.IncomingMessage):
                """Handle message with concurrency control."""
                async with semaphore:  # Limit concurrent processing
                    try:
                        # Extract trace context from headers
                        headers = message.headers or {}
                        ctx = propagator.extract(headers)

                        # Check if this is a redelivered message
                        is_redelivered = getattr(message, "redelivered", False)

                        with tracer.start_as_current_span(
                            "consume_message", context=ctx
                        ) as span:
                            span.set_attribute("messaging.system", "rabbitmq")
                            span.set_attribute("messaging.source", queue)
                            span.set_attribute("messaging.redelivered", is_redelivered)
                            logger.info(
                                f"Received message from queue {queue} (redelivered={is_redelivered}): {message.body.decode()}"
                            )

                            # Parse message
                            msg_data = json.loads(message.body.decode())

                            # Call the async callback
                            logger.info(f"Processing message from queue {queue}")
                            await callback(msg_data)
                            logger.info(
                                f"Successfully processed message from queue {queue}"
                            )

                            # Acknowledge only after successful processing
                            if not auto_ack:
                                await message.ack()
                                logger.info(f"Acknowledged message from queue {queue}")

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to decode message body as JSON: {e}")
                        if not auto_ack:
                            # Don't requeue malformed messages
                            await message.reject(requeue=False)
                    except Exception as e:
                        if hasattr(span, "record_exception"):
                            span.record_exception(e)
                            span.set_status(trace.Status(trace.StatusCode.ERROR))
                        logger.error(f"Error processing message: {e}", exc_info=True)

                        if not auto_ack:
                            # Simple retry logic: retry once if not already redelivered
                            if not is_redelivered:
                                # First failure - requeue for retry
                                await message.reject(requeue=True)
                                logger.info(
                                    f"Rejected and requeued message from queue {queue} for retry"
                                )
                            else:
                                # Already redelivered - send to DLQ
                                await message.reject(requeue=False)
                                logger.error(
                                    f"Message from queue {queue} failed after retry, sending to DLQ"
                                )

            # Start consuming
            logger.info(
                f"Starting to consume from queue {queue} with prefetch={prefetch_count}, auto_ack={auto_ack}"
            )
            await queue_obj.consume(process_message, no_ack=auto_ack)

            logger.info(f"Consumer started for queue {queue}")

            # Keep the consumer running
            try:
                await asyncio.Future()  # Run forever
            except asyncio.CancelledError:
                logger.info(f"Consumer cancelled for queue {queue}")
                # Wait for active tasks to complete before exiting
                if active_tasks:
                    logger.info(
                        f"Waiting for {len(active_tasks)} active tasks to complete..."
                    )
                    await asyncio.gather(*active_tasks, return_exceptions=True)
                raise

        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)
            raise

    async def declare_queue(
        self, queue: str, durable: bool = True, dlq_enabled: bool = True
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            queue_arguments = {}

            # Set up dead letter queue if enabled
            if dlq_enabled:
                dlq_arguments = await self._setup_dead_letter_queue(queue)
                queue_arguments.update(dlq_arguments)

            # Declare the main queue
            await self.channel.declare_queue(
                queue,
                durable=durable,
                arguments=queue_arguments if queue_arguments else None,
            )

            logger.info(f"Declared queue: {queue} (DLQ enabled: {dlq_enabled})")
            return True
        except Exception as e:
            logger.error(f"Failed to declare queue {queue}: {e}")
            return False

    async def declare_exchange(
        self, exchange: str, exchange_type: str = "direct", durable: bool = True
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # Map exchange type
            type_map = {
                "direct": aio_pika.ExchangeType.DIRECT,
                "topic": aio_pika.ExchangeType.TOPIC,
                "fanout": aio_pika.ExchangeType.FANOUT,
                "headers": aio_pika.ExchangeType.HEADERS,
            }

            await self.channel.declare_exchange(
                name=exchange,
                type=type_map.get(exchange_type, aio_pika.ExchangeType.DIRECT),
                durable=durable,
            )
            logger.info(f"Declared exchange: {exchange}")
            return True
        except Exception as e:
            logger.error(f"Failed to declare exchange {exchange}: {e}")
            return False

    async def bind_queue(
        self, queue: str, exchange: str, routing_key: str = ""
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            routing_key = routing_key or queue

            # Get queue and exchange objects
            queue_obj = await self.channel.get_queue(queue)
            exchange_obj = await self.channel.get_exchange(exchange)

            # Bind queue to exchange
            await queue_obj.bind(exchange_obj, routing_key=routing_key)

            logger.info(
                f"Bound queue {queue} to exchange {exchange} with routing key {routing_key}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to bind queue: {e}")
            return False
