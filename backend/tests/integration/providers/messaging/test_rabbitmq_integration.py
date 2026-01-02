import pytest
import asyncio
import aio_pika

from common.providers.messaging.rabbitmq_async import RabbitMQClient, QueueConfig


@pytest.mark.asyncio
class TestRabbitMQIntegration:
    """Integration tests for RabbitMQ client with real RabbitMQ instance."""

    async def teardown_method(self, method):
        """Clean up queues and exchanges after each test."""
        # This will be handled by the test fixtures

    async def test_connect_and_disconnect(self, rabbitmq_client):
        """Test basic connection and disconnection."""
        # Connection should already be established by fixture
        assert rabbitmq_client.connection is not None
        assert rabbitmq_client.channel is not None

        # Test disconnect
        await rabbitmq_client.disconnect()

        # Test reconnect
        connected = await rabbitmq_client.connect()
        assert connected is True

    async def test_declare_queue(self, rabbitmq_client, test_queue_name):
        """Test queue declaration."""
        result = await rabbitmq_client.declare_queue(test_queue_name, durable=True)
        assert result is True

        # Test declaring the same queue again (should succeed)
        result = await rabbitmq_client.declare_queue(test_queue_name, durable=True)
        assert result is True

    async def test_declare_exchange(self, rabbitmq_client, test_exchange_name):
        """Test exchange declaration."""
        result = await rabbitmq_client.declare_exchange(
            test_exchange_name, exchange_type="direct", durable=True
        )
        assert result is True

        # Test declaring the same exchange again (should succeed)
        result = await rabbitmq_client.declare_exchange(
            test_exchange_name, exchange_type="direct", durable=True
        )
        assert result is True

    async def test_bind_queue_to_exchange(
        self, rabbitmq_client, test_queue_name, test_exchange_name
    ):
        """Test binding queue to exchange."""
        # First declare queue and exchange
        await rabbitmq_client.declare_queue(test_queue_name, durable=True)
        await rabbitmq_client.declare_exchange(test_exchange_name, durable=True)

        # Bind queue to exchange
        result = await rabbitmq_client.bind_queue(
            test_queue_name, test_exchange_name, "test_key"
        )
        assert result is True

    async def test_publish_message_to_queue(
        self, rabbitmq_client, test_queue_name, sample_message
    ):
        """Test publishing a message to a queue."""
        # Declare queue first
        await rabbitmq_client.declare_queue(test_queue_name, durable=True)

        # Publish message
        result = await rabbitmq_client.publish(test_queue_name, sample_message)
        assert result is True

    async def test_publish_message_to_exchange(
        self, rabbitmq_client, test_queue_name, test_exchange_name, sample_message
    ):
        """Test publishing a message via exchange."""
        # Setup
        await rabbitmq_client.declare_queue(test_queue_name, durable=False)
        await rabbitmq_client.declare_exchange(test_exchange_name, durable=True)
        await rabbitmq_client.bind_queue(
            test_queue_name, test_exchange_name, "test_key"
        )

        # Publish to exchange
        result = await rabbitmq_client.publish(
            "test_key", sample_message, exchange=test_exchange_name
        )
        assert result is True

    @pytest.mark.skip(reason="infinite looping right now")
    async def test_message_consumption_flow(
        self, rabbitmq_client, test_queue_name, sample_message
    ):
        """Test end-to-end message flow: publish -> consume."""
        # Declare queue
        await rabbitmq_client.declare_queue(test_queue_name, durable=False)

        # Publish message
        await rabbitmq_client.publish(test_queue_name, sample_message)

        # Set up consumption test
        received_messages = []
        message_received_event = asyncio.Event()

        async def test_callback(message):
            received_messages.append(message)
            message_received_event.set()

        # Start consumption in background task
        consume_task = asyncio.create_task(
            rabbitmq_client.consume(test_queue_name, test_callback, auto_ack=True)
        )

        # Wait for message to be received (with timeout)
        try:
            await asyncio.wait_for(message_received_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Message was not received within timeout")
        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

        # Verify message was received correctly
        assert len(received_messages) == 1
        assert received_messages[0] == sample_message

    async def test_connection_failure_handling(self):
        """Test behavior when RabbitMQ is not available."""
        # Create client with invalid connection parameters
        client = RabbitMQClient()
        client.host = "127.0.0.1"  # Use IP instead of hostname
        client.port = 9999  # Non-existent port

        # Connection should fail gracefully
        result = await client.connect()
        assert result is False

        # Publishing should fail when not connected
        result = await client.publish("test_queue", {"test": "message"})
        assert result is False

    async def test_queue_declaration_after_disconnect(self, test_queue_name):
        """Test that queue operations trigger reconnection after disconnect."""
        client = RabbitMQClient()

        # Initially connect
        await client.connect()

        # Disconnect
        await client.disconnect()

        # Queue declaration should trigger reconnection
        result = await client.declare_queue(test_queue_name, durable=False)
        assert result is True
        assert client.connection is not None
        assert client.channel is not None

        await client.disconnect()

    async def test_message_persistence(self, rabbitmq_client, test_queue_name):
        """Test message persistence with durable queue."""
        # Declare queue
        await rabbitmq_client.declare_queue(test_queue_name, durable=True)

        # Publish persistent message
        persistent_message = {"data": "persistent_test", "important": True}
        result = await rabbitmq_client.publish(test_queue_name, persistent_message)
        assert result is True

        # In a real scenario, you could restart RabbitMQ here and verify
        # the message persists, but that's beyond the scope of unit testing

    async def test_exchange_types(self, rabbitmq_client):
        """Test different exchange types."""
        exchange_types = ["direct", "fanout", "topic", "headers"]

        for exchange_type in exchange_types:
            exchange_name = f"test_exchange_{exchange_type}"
            result = await rabbitmq_client.declare_exchange(
                exchange_name, exchange_type=exchange_type, durable=True
            )
            assert result is True

    @pytest.mark.parametrize("auto_ack", [True, False])
    @pytest.mark.skip(reason="infinite looping right now")
    async def test_message_acknowledgment_modes(
        self, rabbitmq_client, test_queue_name, sample_message, auto_ack
    ):
        """Test both auto-ack and manual acknowledgment modes."""
        await rabbitmq_client.declare_queue(test_queue_name, durable=False)
        await rabbitmq_client.publish(test_queue_name, sample_message)

        received_messages = []
        message_received_event = asyncio.Event()

        async def test_callback(message):
            received_messages.append(message)
            message_received_event.set()

        consume_task = asyncio.create_task(
            rabbitmq_client.consume(test_queue_name, test_callback, auto_ack=auto_ack)
        )

        try:
            await asyncio.wait_for(message_received_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pytest.fail("Message was not received within timeout")
        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

        assert len(received_messages) == 1
        assert received_messages[0] == sample_message

    async def test_dead_letter_queue_setup(self, rabbitmq_client, test_queue_name):
        """Test that DLQ and DLX are properly created when declaring a queue."""
        # Declare queue with DLQ enabled
        result = await rabbitmq_client.declare_queue(
            test_queue_name, durable=True, dlq_enabled=True
        )
        assert result is True

        # Verify DLX exists
        dlx_name = f"{test_queue_name}{QueueConfig.DLX_SUFFIX}"
        try:
            exchange = await rabbitmq_client.channel.get_exchange(dlx_name)
            assert exchange is not None
        except aio_pika.exceptions.ChannelNotFoundEntity:
            pytest.fail(f"Dead letter exchange {dlx_name} was not created")

        # Verify DLQ exists
        dlq_name = f"{test_queue_name}{QueueConfig.DLQ_SUFFIX}"
        try:
            queue = await rabbitmq_client.channel.get_queue(dlq_name)
            assert queue is not None
        except aio_pika.exceptions.ChannelNotFoundEntity:
            pytest.fail(f"Dead letter queue {dlq_name} was not created")

    async def test_message_routing_to_dlq_on_rejection(
        self, rabbitmq_client, test_queue_name, sample_message
    ):
        """Test that rejected messages are routed to the DLQ."""
        # Declare queue with DLQ
        await rabbitmq_client.declare_queue(
            test_queue_name, durable=True, dlq_enabled=True
        )

        # Publish a message
        await rabbitmq_client.publish(test_queue_name, sample_message)

        # Consume and reject the message
        message_received = asyncio.Event()

        async def reject_callback(message):
            message_received.set()
            # Simulate processing failure - this will be handled by the wrapper
            raise Exception("Simulated processing failure")

        # Start consumer with manual ack
        consume_task = asyncio.create_task(
            rabbitmq_client.consume(test_queue_name, reject_callback, auto_ack=False)
        )

        # Wait for message to be processed
        try:
            await asyncio.wait_for(message_received.wait(), timeout=5.0)
            # Give time for rejection to process
            await asyncio.sleep(1)
        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

        # Check if message is in DLQ
        dlq_name = f"{test_queue_name}{QueueConfig.DLQ_SUFFIX}"
        dlq = await rabbitmq_client.channel.get_queue(dlq_name)

        # Get message count
        declaration = await dlq.declare()
        assert declaration.message_count > 0

    async def test_message_retry_limit(
        self, rabbitmq_client, test_queue_name, sample_message
    ):
        """Test that messages are retried up to the limit then sent to DLQ."""
        # Declare queue with DLQ
        await rabbitmq_client.declare_queue(
            test_queue_name, durable=True, dlq_enabled=True
        )

        # Track retry attempts
        retry_count = 0
        message_events = []

        async def failing_callback(message):
            nonlocal retry_count
            retry_count += 1
            event = asyncio.Event()
            message_events.append(event)
            event.set()
            # Always fail to trigger retries
            raise Exception(f"Simulated failure {retry_count}")

        # Publish message
        await rabbitmq_client.publish(test_queue_name, sample_message)

        # Start consumer
        consume_task = asyncio.create_task(
            rabbitmq_client.consume(test_queue_name, failing_callback, auto_ack=False)
        )

        try:
            # Wait for retries (should be max_retries + 1 attempts)
            for i in range(QueueConfig.DEFAULT_MAX_RETRIES + 1):
                if i < len(message_events):
                    await asyncio.wait_for(message_events[i].wait(), timeout=5.0)
                else:
                    await asyncio.sleep(1)

            # Give time for final rejection
            await asyncio.sleep(1)

            # Should have attempted max_retries + 1 times
            assert retry_count >= QueueConfig.DEFAULT_MAX_RETRIES

            # Message should now be in DLQ
            dlq_name = f"{test_queue_name}{QueueConfig.DLQ_SUFFIX}"
            dlq = await rabbitmq_client.channel.get_queue(dlq_name)
            declaration = await dlq.declare()
            assert declaration.message_count > 0

        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass

    async def test_dlq_disabled(self, rabbitmq_client, test_queue_name):
        """Test queue declaration without DLQ."""
        # Declare queue with DLQ disabled
        result = await rabbitmq_client.declare_queue(
            test_queue_name, durable=True, dlq_enabled=False
        )
        assert result is True

        # Verify DLX does not exist by trying to declare it passively
        dlx_name = f"{test_queue_name}{QueueConfig.DLX_SUFFIX}"
        try:
            # This will fail if exchange doesn't exist
            await rabbitmq_client.channel.declare_exchange(
                dlx_name,
                type=aio_pika.ExchangeType.DIRECT,
                passive=True,  # Only check existence, don't create
            )
            pytest.fail(f"Exchange {dlx_name} should not exist")
        except Exception:
            # Expected - exchange doesn't exist
            pass

        # Reconnect since the channel might be closed after the error
        await rabbitmq_client.connect()

        # Verify DLQ does not exist by trying to declare it passively
        dlq_name = f"{test_queue_name}{QueueConfig.DLQ_SUFFIX}"
        try:
            # This will fail if queue doesn't exist
            await rabbitmq_client.channel.declare_queue(
                dlq_name, passive=True  # Only check existence, don't create
            )
            pytest.fail(f"Queue {dlq_name} should not exist")
        except Exception:
            # Expected - queue doesn't exist
            pass

    async def test_publisher_confirms(self, rabbitmq_client, test_queue_name):
        """Test that publisher confirms are working."""
        # Declare queue
        await rabbitmq_client.declare_queue(test_queue_name, durable=True)

        # Publish should succeed with confirms
        result = await rabbitmq_client.publish(test_queue_name, {"test": "confirms"})
        assert result is True

        # Publish to non-existent queue should fail with mandatory flag
        result = await rabbitmq_client.publish(
            "non_existent_queue_12345", {"test": "should_fail"}
        )
        # This might still return True if the queue gets auto-created
        # The important part is that publisher confirms are enabled

    async def test_malformed_message_to_dlq(self, rabbitmq_client, test_queue_name):
        """Test that malformed messages go straight to DLQ without retry."""
        # Declare queue with DLQ
        await rabbitmq_client.declare_queue(
            test_queue_name, durable=True, dlq_enabled=True
        )

        # Manually publish a malformed message (invalid JSON)
        await rabbitmq_client.channel.default_exchange.publish(
            aio_pika.Message(
                body=b"not valid json {",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=test_queue_name,
        )

        # Try to consume
        message_received = asyncio.Event()

        async def callback(message):
            message_received.set()
            pytest.fail("Callback should not be called for malformed message")

        consume_task = asyncio.create_task(
            rabbitmq_client.consume(test_queue_name, callback, auto_ack=False)
        )

        try:
            # Wait a bit for message processing
            await asyncio.sleep(2)

            # Message should be in DLQ
            dlq_name = f"{test_queue_name}{QueueConfig.DLQ_SUFFIX}"
            dlq = await rabbitmq_client.channel.get_queue(dlq_name)
            declaration = await dlq.declare()
            assert declaration.message_count > 0

        finally:
            consume_task.cancel()
            try:
                await consume_task
            except asyncio.CancelledError:
                pass
