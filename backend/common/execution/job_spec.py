"""
Job specification for generic executor.

Defines what to run in a container/K8s job regardless of execution type.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    """
    Specification for a container/K8s job execution.

    This generic model is used by both workflow execution and agent QA,
    with different templates and parameters.
    """

    # Container identity
    container_name: str = Field(..., description="Name for container/job")

    # Template selection
    template_name: str = Field(
        ...,
        description="Jinja2 template name (e.g. 'workflow_job.yaml.j2', 'agent_qa_job.yaml.j2')",
    )

    # Image selection
    image_name: str = Field(..., description="Docker image name (without tag)")
    image_tag: str = Field(default="latest", description="Docker image tag")

    # Environment variables to pass to container
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for the container"
    )

    # Template variables (for K8s Job manifest rendering)
    template_vars: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional variables to pass to Jinja2 template",
    )

    # Docker-specific settings
    docker_network: Optional[str] = Field(
        default="corpus_default",
        description="Docker network to attach container to (Docker only)",
    )
