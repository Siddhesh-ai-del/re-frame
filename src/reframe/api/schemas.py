"""Pydantic v2 request/response contracts for the RE:FRAME HTTP API.

These models are the trust boundary at the edge of the service: ``ChatRequest``
rejects unknown body keys (``extra="forbid"``) and bounds the message length so
oversized or empty payloads never reach the pipeline. The response models are
plain, non-diagnostic value carriers with no internal fields exposed.
"""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Inbound chat body: a single length-bounded user message, nothing else."""

    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)


class ResourceOut(BaseModel):
    """A named crisis resource; ``url`` is ``None`` for non-linkable guidance."""

    name: str
    url: str | None


class ChatResponse(BaseModel):
    """Outbound chat result: the reply, its route, grounding, and resources."""

    reply: str
    route: str
    module_ids: list[str]
    violations: list[str]
    resources: list[ResourceOut]


class ResourcesOut(BaseModel):
    """Outbound resource list: the standing crisis resources, always available."""

    resources: list[ResourceOut]


class HealthResponse(BaseModel):
    """Liveness payload: service status and package version."""

    status: str
    version: str


class ErrorDetail(BaseModel):
    """Error body wrapper; the API always uses FastAPI's ``{"detail": ...}``."""

    detail: str
