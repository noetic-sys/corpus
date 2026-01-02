from typing import Callable, Dict, Any
import json
import asyncio

from deprecated import deprecated
import pika
from pika.exceptions import AMQPConnectionError

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from common.core.config import settings
from .interface import MessageQueueInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)

tracer = trace.get_tracer(__name__)
propagator = TraceContextTextMapPropagator()


@deprecated
class RabbitMQClient(MessageQueueInterface):
    def __init__(self):
        self.connection = None
        self.channel = None
        self.host = settings.rabbitmq_host
        self.port = settings.rabbitmq_port
        self.username = settings.rabbitmq_username
        self.password = settings.rabbitmq_password
        self.vhost = settings.rabbitmq_vhost

    async def connect(self) -> bool:
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )

            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("Successfully connected to RabbitMQ")
            return True
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    async def disconnect(self) -> None:
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    async def publish(
        self, queue: str, message: Dict[str, Any], exchange: str = ""
    ) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            message_body = json.dumps(message)

            # Inject trace context into headers
            headers = {}
            propagator.inject(headers)

            self.channel.basic_publish(
                exchange=exchange,
                routing_key=queue,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2, content_type="application/json", headers=headers
                ),
            )

            logger.info(f"Published message to queue {queue}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False

    async def consume(
        self, queue: str, callback: Callable, auto_ack: bool = True
    ) -> None:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # Get the event loop for async callback execution
            loop = asyncio.get_event_loop()

            def wrapper(ch, method, properties, body):
                try:
                    # Extract trace context from headers
                    headers = getattr(properties, "headers", {}) or {}
                    ctx = propagator.extract(headers)
                    with tracer.start_as_current_span(
                        "consume_message", context=ctx
                    ) as span:
                        span.set_attribute("messaging.system", "rabbitmq")
                        span.set_attribute("messaging.source", method.routing_key)
                        logger.info(
                            f"Received message from queue {queue}: {body.decode()}"
                        )
                        message = json.loads(body)

                        # Create async task to handle acknowledgment after processing
                        async def process_and_ack():
                            try:
                                await callback(message)
                                logger.info(
                                    f"Successfully processed message from queue {queue}"
                                )

                                if not auto_ack:
                                    # Run in executor to avoid blocking the event loop
                                    await loop.run_in_executor(
                                        None, ch.basic_ack, method.delivery_tag
                                    )
                                    logger.info(
                                        f"Acknowledged message from queue {queue}"
                                    )
                            except Exception as callback_error:
                                span.record_exception(callback_error)
                                span.set_status(trace.Status(trace.StatusCode.ERROR))
                                logger.error(
                                    f"Callback error processing message: {callback_error}",
                                    exc_info=True,
                                )
                                if not auto_ack:
                                    # Run in executor to avoid blocking the event loop
                                    await loop.run_in_executor(
                                        None,
                                        ch.basic_nack,
                                        method.delivery_tag,
                                        False,  # multiple
                                        True,  # requeue
                                    )
                                    logger.info(
                                        f"Negative acknowledged message from queue {queue}, requeued"
                                    )

                        # Schedule the processing without blocking
                        _ = asyncio.run_coroutine_threadsafe(process_and_ack(), loop)
                        logger.info(
                            f"Scheduled async processing for message from queue {queue}"
                        )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message body as JSON: {e}")
                    if not auto_ack:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    if not auto_ack:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            # Set QoS
            self.channel.basic_qos(prefetch_count=1)
            logger.info(f"Set prefetch_count=1 for queue {queue}")

            # Start consuming
            self.channel.basic_consume(
                queue=queue, on_message_callback=wrapper, auto_ack=auto_ack
            )
            logger.info(
                f"Started consuming from queue {queue} with auto_ack={auto_ack}"
            )

            logger.info(f"Starting to consume messages from queue {queue}")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumption")
            self.channel.stop_consuming()
            raise
        except Exception as e:
            logger.error(f"Error consuming messages: {e}", exc_info=True)
            raise

    async def declare_queue(self, queue: str, durable: bool = True) -> bool:
        try:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            self.channel.queue_declare(queue=queue, durable=durable)
            logger.info(f"Declared queue: {queue}")
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

            self.channel.exchange_declare(
                exchange=exchange, exchange_type=exchange_type, durable=durable
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
            self.channel.queue_bind(
                queue=queue, exchange=exchange, routing_key=routing_key
            )
            logger.info(
                f"Bound queue {queue} to exchange {exchange} with routing key {routing_key}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to bind queue: {e}")
            return False
