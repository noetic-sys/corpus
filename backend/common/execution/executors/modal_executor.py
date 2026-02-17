"""
Modal executor for serverless job execution.

Manages Modal Sandboxes for agent execution using:
- Modal Python SDK for Sandbox lifecycle
- gVisor isolation (same as K8s executor)
"""

from typing import Dict, Any

import modal

from common.core.config import settings
from common.execution.executors.base import JobExecutor
from common.execution.job_spec import JobSpec


class ModalExecutor(JobExecutor):
    """Executor for Modal-based sandbox execution."""

    def __init__(self):
        """Initialize Modal app handle."""
        self.app = modal.App.lookup("corpus-agents", create_if_missing=True)
        self.image_registry = "ghcr.io/noetic-sys/corpus"

    def launch(self, job_spec: JobSpec) -> Dict[str, Any]:
        """Launch a Modal Sandbox based on job spec."""
        image_tag = job_spec.image_tag or settings.workflow_agent_image_tag
        image_ref = f"{self.image_registry}/{job_spec.image_name}:{image_tag}"
        image = modal.Image.from_registry(image_ref)

        timeout = job_spec.template_vars.get("timeout", 900)

        sb = modal.Sandbox.create(
            image=image,
            app=self.app,
            timeout=timeout,
            cpu=1.0,
            memory=1024,
            env=job_spec.env_vars,
        )

        return {
            "mode": "modal",
            "sandbox_id": sb.object_id,
            "job_name": job_spec.container_name,
        }

    def check_status(self, execution_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Modal Sandbox status."""
        sandbox_id = execution_info["sandbox_id"]

        try:
            sb = modal.Sandbox.from_id(sandbox_id)
        except Exception:
            return {"status": "failed", "error": "Sandbox not found"}

        exit_code = sb.poll()
        if exit_code is None:
            return {"status": "running"}
        if exit_code == 0:
            return {"status": "completed", "exit_code": 0}
        return {"status": "failed", "exit_code": exit_code}

    def cleanup(self, execution_info: Dict[str, Any]) -> None:
        """Terminate Modal Sandbox if still running."""
        sandbox_id = execution_info["sandbox_id"]
        job_name = execution_info.get("job_name", sandbox_id)

        try:
            sb = modal.Sandbox.from_id(sandbox_id)
            sb.terminate()
            print(f"Terminated Modal sandbox for {job_name}")
        except Exception:
            print(f"Sandbox {job_name} already terminated or not found")
