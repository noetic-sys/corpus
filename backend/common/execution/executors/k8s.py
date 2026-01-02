"""
Kubernetes executor for production job execution.

Manages K8s jobs for agent execution in production using:
- Kubernetes Python client for API interactions
- Jinja2 templates for Job manifests
"""

import os
import yaml
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from common.core.config import settings
from common.execution.executors.base import JobExecutor
from common.execution.job_spec import JobSpec


class K8sExecutor(JobExecutor):
    """Executor for Kubernetes-based job execution."""

    def __init__(self):
        """Initialize K8s client and template environment."""
        # Load K8s config (in-cluster or kubeconfig)
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "corpus"

        # Setup Jinja2 template environment
        # Navigate to job_templates from backend root
        backend_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        template_dir = os.path.join(backend_root, "job_templates")
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def launch(self, job_spec: JobSpec) -> Dict[str, Any]:
        """Launch Kubernetes job based on job spec."""
        job_name = job_spec.container_name

        # Build image path (Artifact Registry format)
        image_full = f"us-central1-docker.pkg.dev/{settings.google_project_id}/{job_spec.image_name}:{job_spec.image_tag}"

        # Prepare template variables
        template_context = {
            "job_name": job_name,
            "namespace": self.namespace,
            "image": image_full,
            "api_endpoint": settings.api_endpoint,
            "execution_mode": "k8s",
            **job_spec.template_vars,  # Additional template-specific vars
        }

        # Convert env_vars dict to list of {name, value} for template
        template_context["env_vars"] = [
            {"name": k, "value": v} for k, v in job_spec.env_vars.items()
        ]

        # Render job manifest from template
        template = self.jinja_env.get_template(job_spec.template_name)
        manifest_yaml = template.render(**template_context)

        # Debug: Print rendered YAML
        print(f"DEBUG: Rendered Job YAML:\n{manifest_yaml}")

        # Parse YAML to dict
        job_dict = yaml.safe_load(manifest_yaml)

        # Debug: Print parsed dict
        print(f"DEBUG: Parsed Job dict keys: {job_dict.keys()}")
        print(f"DEBUG: Job name: {job_dict.get('metadata', {}).get('name')}")

        try:
            # Create job directly from dict (K8s Python client accepts dicts)
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job_dict)
        except ApiException as e:
            raise Exception(f"Failed to create K8s job {job_name}: {e}")

        return {"mode": "k8s", "job_name": job_name}

    def check_status(self, execution_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check Kubernetes job status."""
        job_name = execution_info["job_name"]

        try:
            job = self.batch_v1.read_namespaced_job(
                name=job_name, namespace=self.namespace
            )
        except ApiException as e:
            if e.status == 404:
                return {"status": "failed", "error": "Job not found"}
            raise Exception(f"Failed to check job status: {e}")

        # Check job status
        if job.status.succeeded and job.status.succeeded > 0:
            return {"status": "completed", "exit_code": 0}

        if job.status.failed and job.status.failed > 0:
            return {"status": "failed", "exit_code": 1}

        return {"status": "running"}

    def cleanup(self, execution_info: Dict[str, Any]) -> None:
        """
        Cleanup Kubernetes job and associated pods.

        Only called on successful execution - failed jobs are left for debugging.
        """
        job_name = execution_info["job_name"]

        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name,
                namespace=self.namespace,
                propagation_policy="Background",  # Delete pods in background
            )
            print(f"Cleaned up Kubernetes job {job_name} in namespace {self.namespace}")
        except ApiException as e:
            if e.status == 404:
                print(f"Job {job_name} already deleted or not found")
            else:
                print(f"Failed to delete job {job_name}: {e}")
                raise Exception(f"Failed to delete job {job_name}: {e}")
