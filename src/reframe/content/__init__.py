"""Evidence-tiered content library and deterministic, rule-matched retrieval.

Public surface: the :class:`~reframe.content.schema.ExerciseModule` value
types, :func:`~reframe.content.library.load_library_json` /
:func:`~reframe.content.library.default_library` for fail-closed library
assembly, :func:`~reframe.content.matching.match_categories` for rule-based
category matching, and :func:`~reframe.content.retrieval.retrieve` for
deterministic tiered selection. No embeddings, no model calls, no I/O beyond
loading the packaged corpus.
"""

from reframe.content.library import ContentLibrary, default_library, load_library_json
from reframe.content.matching import MATCH_RULES, match_categories
from reframe.content.retrieval import RetrievalResult, retrieve
from reframe.content.schema import (
    EvidenceTier,
    ExerciseCategory,
    ExerciseModule,
    SafetyClass,
)

__all__ = [
    "MATCH_RULES",
    "ContentLibrary",
    "EvidenceTier",
    "ExerciseCategory",
    "ExerciseModule",
    "RetrievalResult",
    "SafetyClass",
    "default_library",
    "load_library_json",
    "match_categories",
    "retrieve",
]
