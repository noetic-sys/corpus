import threading
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .provider_enum import APIProviderType
from .interface import APIKeyRotationInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class KeyHealth:
    def __init__(self, key: str):
        self.key = key
        self.failure_count = 0
        self.last_failure: Optional[datetime] = None
        self.cooldown_until: Optional[datetime] = None

    def is_healthy(self) -> bool:
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        return self.failure_count < 3  # Allow up to 3 failures before cooldown

    def report_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.now()
        if self.failure_count >= 3:
            # Put key in cooldown for 5 minutes
            self.cooldown_until = datetime.now() + timedelta(minutes=5)
            logger.warning(f"Key entering cooldown until {self.cooldown_until}")

    def report_success(self):
        # Reset on successful use
        self.failure_count = 0
        self.last_failure = None
        self.cooldown_until = None


class APIKeyRotationProvider(APIKeyRotationInterface):
    def __init__(self, keys: List[str], provider_type: APIProviderType):
        self.keys = keys
        self.provider_type = provider_type
        self.current_index = 0
        self.lock = threading.Lock()

        # Track health of each key
        self.key_health: Dict[str, KeyHealth] = {key: KeyHealth(key) for key in keys}

        logger.info(f"Initialized {provider_type.value} rotation with {len(keys)} keys")

    def get_next_key(self) -> str:
        with self.lock:
            # Find next healthy key
            attempts = 0
            while attempts < len(self.keys):
                key = self.keys[self.current_index]
                health = self.key_health[key]

                # Move to next key for next call
                self.current_index = (self.current_index + 1) % len(self.keys)

                if health.is_healthy():
                    logger.info(
                        f"{self.provider_type.value}: Using key index {self.current_index - 1}"
                    )
                    return key

                attempts += 1

            # All keys unhealthy - return first one anyway and log warning
            logger.error(
                f"{self.provider_type.value}: All keys unhealthy, using first key anyway"
            )
            return self.keys[0]

    def report_failure(self, key: str):
        with self.lock:
            if key in self.key_health:
                self.key_health[key].report_failure()
                logger.warning(
                    f"{self.provider_type.value}: Key failure reported (failures: {self.key_health[key].failure_count})"
                )

    def report_success(self, key: str):
        with self.lock:
            if key in self.key_health:
                self.key_health[key].report_success()

    def get_healthy_key_count(self) -> int:
        """Get the number of currently healthy keys."""
        with self.lock:
            return sum(1 for health in self.key_health.values() if health.is_healthy())
