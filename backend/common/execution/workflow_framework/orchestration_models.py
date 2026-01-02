"""
Configuration models for workflow orchestration patterns.

These models define the parameters for the launch→poll→extract→cleanup pattern.
"""

from typing import Any, List, Callable, Optional
from dataclasses import dataclass


@dataclass
class PollingConfig:
    """Configuration for polling job status until completion."""

    max_wait_minutes: int
    poll_interval_seconds: int
    check_status_activity: str
    status_timeout_seconds: int = 30


@dataclass
class OrchestrationConfig:
    """
    Configuration for full agent job orchestration.

    Defines the activities and parameters for the launch→poll→extract→cleanup pattern.
    """

    # Launch phase
    launch_activity: str
    launch_args: List[Any]
    launch_timeout_minutes: int = 2

    # Polling phase
    polling: PollingConfig = None

    # Extract phase
    extract_activity: str = None
    extract_args_builder: Optional[Callable[[dict], List[Any]]] = None
    extract_timeout_minutes: int = 1

    # Cleanup phase
    cleanup_activity: str = None
    cleanup_args_builder: Optional[Callable[[dict], List[Any]]] = None
    cleanup_timeout_minutes: int = 1
