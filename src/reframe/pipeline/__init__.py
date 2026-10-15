"""Conversation pipeline: safety decides, content grounds, generation speaks, filter approves.

Public surface: the :class:`~reframe.pipeline.pipeline.Route` /
:class:`~reframe.pipeline.pipeline.PipelineOutcome` value types and the
:class:`~reframe.pipeline.pipeline.ConversationPipeline` orchestrator, the
Layer 5 output filter (:data:`~reframe.pipeline.output_filter.OUTPUT_RULES`,
:func:`~reframe.pipeline.output_filter.filter_output`), and the scripted
response catalog (:data:`~reframe.pipeline.messages.SCRIPTED`).
"""

from reframe.pipeline.messages import (
    BOUNDARY_RESPONSE,
    CRISIS_RESPONSE,
    FILTER_FALLBACK,
    SCRIPTED,
    ScriptedResponse,
)
from reframe.pipeline.output_filter import OUTPUT_RULES, OutputVerdict, filter_output
from reframe.pipeline.pipeline import ConversationPipeline, PipelineOutcome, Route

__all__ = [
    "BOUNDARY_RESPONSE",
    "CRISIS_RESPONSE",
    "FILTER_FALLBACK",
    "OUTPUT_RULES",
    "SCRIPTED",
    "ConversationPipeline",
    "OutputVerdict",
    "PipelineOutcome",
    "Route",
    "ScriptedResponse",
    "filter_output",
]
