"""
Docker executor for local job execution.

Manages Docker containers for agent execution during development.
"""

import subprocess
from typing import Dict, Any

from common.core.config import settings
from common.execution.executors.base import JobExecutor
from common.execution.job_spec import JobSpec


class DockerExecutor(JobExecutor):
    """Executor for Docker-based job execution."""

    def launch(self, job_spec: JobSpec) -> Dict[str, Any]:
        """Launch Docker container based on job spec."""
        # Build docker run command
        cmd = [
            "docker",
            "run",
            "--name",
            job_spec.container_name,
            "--network",
            job_spec.docker_network,
            "-d",  # detached
        ]

        # Add environment variables from job spec
        env_vars = dict(job_spec.env_vars)

        # Auto-inject ANTHROPIC_API_KEY for Docker mode (K8s uses secrets)
        if "ANTHROPIC_API_KEY" not in env_vars:
            env_vars["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add image
        image_full = f"{job_spec.image_name}:{job_spec.image_tag}"
        cmd.append(image_full)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Docker run failed with exit code {e.returncode}\n"
                f"Command: {' '.join(cmd)}\n"
                f"Stdout: {e.stdout}\n"
                f"Stderr: {e.stderr}"
            ) from e

        container_id = result.stdout.strip()

        return {
            "mode": "docker",
            "container_id": container_id,
            "container_name": job_spec.container_name,
        }

    def check_status(self, execution_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Docker container status."""
        container_id = execution_info["container_id"]

        status_result = subprocess.run(
            ["docker", "inspect", container_id, "--format", "{{.State.Status}}"],
            capture_output=True,
            text=True,
        )

        if status_result.returncode != 0:
            return {"status": "failed", "error": "Container not found"}

        status = status_result.stdout.strip()

        if status == "exited":
            exit_code_result = subprocess.run(
                ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}"],
                capture_output=True,
                text=True,
            )
            exit_code = int(exit_code_result.stdout.strip())

            return {
                "status": "completed" if exit_code == 0 else "failed",
                "exit_code": exit_code,
            }

        return {"status": "running"}

    def cleanup(self, execution_info: Dict[str, Any]) -> None:
        """
        Cleanup Docker container.

        Only called on successful execution - failed containers are left for debugging.
        """
        container_id = execution_info["container_id"]
        container_name = execution_info.get("container_name", "unknown")

        try:
            # Remove the container (forces removal even if still running)
            result = subprocess.run(
                ["docker", "rm", "-f", container_id],
                capture_output=True,
                text=True,
                check=False,  # Don't raise on error
            )

            if result.returncode == 0:
                print(f"Cleaned up Docker container {container_name} ({container_id})")
            else:
                print(f"Failed to remove container {container_name}: {result.stderr}")

        except Exception as e:
            print(f"Error cleaning up container {container_name}: {e}")
