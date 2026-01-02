"""
Base executor interface.

Defines common interface for container/K8s job execution.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from common.execution.job_spec import JobSpec


class JobExecutor(ABC):
    """Abstract base class for job executors (Docker, K8s)."""

    @abstractmethod
    def launch(self, job_spec: JobSpec) -> Dict[str, Any]:
        """
        Launch a job based on specification.

        Args:
            job_spec: Job specification with container name, image, env vars, etc.

        Returns:
            Dict with execution info (mode, container_id/job_name, etc.)
        """
        pass

    @abstractmethod
    def check_status(self, execution_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check execution status.

        Args:
            execution_info: Info returned from launch()

        Returns:
            Dict with status ("running"|"completed"|"failed"), exit_code if completed
        """
        pass

    @abstractmethod
    def cleanup(self, execution_info: Dict[str, Any]) -> None:
        """
        Cleanup execution resources.

        Args:
            execution_info: Info returned from launch()
        """
        pass
