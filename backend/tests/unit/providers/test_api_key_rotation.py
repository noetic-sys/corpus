from datetime import datetime, timedelta
import threading
import time

from common.providers.api_keys.rotation_provider import (
    APIKeyRotationProvider,
    KeyHealth,
)
from common.providers.api_keys.provider_enum import APIProviderType


class TestKeyHealth:
    def test_new_key_is_healthy(self):
        """Test that a new key starts healthy."""
        health = KeyHealth("test-key")
        assert health.is_healthy()
        assert health.failure_count == 0

    def test_key_becomes_unhealthy_after_three_failures(self):
        """Test that a key becomes unhealthy after 3 failures."""
        health = KeyHealth("test-key")

        # First two failures should still be healthy
        health.report_failure()
        assert health.is_healthy()
        assert health.failure_count == 1

        health.report_failure()
        assert health.is_healthy()
        assert health.failure_count == 2

        # Third failure should make it unhealthy
        health.report_failure()
        assert not health.is_healthy()
        assert health.failure_count == 3
        assert health.cooldown_until is not None

    def test_success_resets_failure_count(self):
        """Test that reporting success resets failure count."""
        health = KeyHealth("test-key")

        # Add some failures
        health.report_failure()
        health.report_failure()
        assert health.failure_count == 2

        # Success should reset
        health.report_success()
        assert health.failure_count == 0
        assert health.last_failure is None
        assert health.cooldown_until is None

    def test_cooldown_prevents_healthy_status(self):
        """Test that a key in cooldown is not healthy even if failure count drops."""
        health = KeyHealth("test-key")

        # Force cooldown
        health.failure_count = 3
        health.cooldown_until = datetime.now() + timedelta(minutes=1)

        assert not health.is_healthy()


class TestAPIKeyRotationProvider:
    def test_single_key_rotation(self):
        """Test rotation with a single key."""
        keys = ["key1"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Should always return the same key
        assert rotator.get_next_key() == "key1"
        assert rotator.get_next_key() == "key1"

    def test_multiple_key_rotation(self):
        """Test rotation cycles through keys."""
        keys = ["key1", "key2", "key3"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Should cycle through keys
        assert rotator.get_next_key() == "key1"
        assert rotator.get_next_key() == "key2"
        assert rotator.get_next_key() == "key3"
        assert rotator.get_next_key() == "key1"  # Back to start

    def test_skips_unhealthy_keys(self):
        """Test that rotation skips unhealthy keys."""
        keys = ["key1", "key2", "key3"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Make key2 unhealthy
        rotator.key_health["key2"].failure_count = 3
        rotator.key_health["key2"].cooldown_until = datetime.now() + timedelta(
            minutes=1
        )

        # Should skip key2
        assert rotator.get_next_key() == "key1"
        assert rotator.get_next_key() == "key3"
        assert rotator.get_next_key() == "key1"

    def test_all_keys_unhealthy_returns_first(self):
        """Test that when all keys are unhealthy, it returns the first key."""
        keys = ["key1", "key2"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Make all keys unhealthy
        for key in keys:
            rotator.key_health[key].failure_count = 3
            rotator.key_health[key].cooldown_until = datetime.now() + timedelta(
                minutes=1
            )

        # Should return first key anyway
        assert rotator.get_next_key() == "key1"

    def test_report_failure_increases_count(self):
        """Test that reporting failure increases failure count."""
        keys = ["key1"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        assert rotator.key_health["key1"].failure_count == 0

        rotator.report_failure("key1")
        assert rotator.key_health["key1"].failure_count == 1

    def test_report_success_resets_count(self):
        """Test that reporting success resets failure count."""
        keys = ["key1"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Add failure
        rotator.report_failure("key1")
        assert rotator.key_health["key1"].failure_count == 1

        # Report success
        rotator.report_success("key1")
        assert rotator.key_health["key1"].failure_count == 0

    def test_report_failure_unknown_key(self):
        """Test that reporting failure for unknown key doesn't crash."""
        keys = ["key1"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Should not crash
        rotator.report_failure("unknown-key")

    def test_report_success_unknown_key(self):
        """Test that reporting success for unknown key doesn't crash."""
        keys = ["key1"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # Should not crash
        rotator.report_success("unknown-key")

    def test_get_healthy_key_count(self):
        """Test getting count of healthy keys."""
        keys = ["key1", "key2", "key3"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)

        # All should be healthy initially
        assert rotator.get_healthy_key_count() == 3

        # Make one unhealthy
        rotator.key_health["key2"].failure_count = 3
        rotator.key_health["key2"].cooldown_until = datetime.now() + timedelta(
            minutes=1
        )

        assert rotator.get_healthy_key_count() == 2

    def test_thread_safety(self):
        """Test that the rotator is thread-safe."""

        keys = ["key1", "key2", "key3"]
        rotator = APIKeyRotationProvider(keys, APIProviderType.OPENAI)
        results = []

        def get_keys():
            for _ in range(10):
                key = rotator.get_next_key()
                results.append(key)
                time.sleep(0.001)  # Small delay to encourage race conditions

        # Run multiple threads
        threads = [threading.Thread(target=get_keys) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have collected keys without crashes
        assert len(results) == 30
        assert all(key in keys for key in results)
