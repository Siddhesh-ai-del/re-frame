"""FastAPI service core for RE:FRAME (stage 5a).

Public surface: the :func:`~reframe.api.app.create_app` factory and the HTTP
contract models (:class:`~reframe.api.schemas.ChatRequest`,
:class:`~reframe.api.schemas.ChatResponse`,
:class:`~reframe.api.schemas.HealthResponse`,
:class:`~reframe.api.schemas.ResourceOut`,
:class:`~reframe.api.schemas.ErrorDetail`). The app wraps the deterministic
conversation pipeline behind a thin, fail-closed HTTP boundary that never
leaks internals and stays in the non-diagnostic wellness lane.
"""

from reframe.api.app import create_app
from reframe.api.schemas import ChatRequest, ChatResponse, ErrorDetail, HealthResponse, ResourceOut

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ErrorDetail",
    "HealthResponse",
    "ResourceOut",
    "create_app",
]
