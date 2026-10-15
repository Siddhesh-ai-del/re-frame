"""Deterministic input safety layer: classify disclosed text, then escalate.

Public surface: :func:`classify_input` (rule-based signal routing),
:func:`escalation_decision` (fixed policy table), and
:func:`run_crisis_audit` (pre-specified seeded-corpus audit harness).
"""

from reframe.safety.audit import MINIMUM_CRISIS_RECALL, AuditReport, run_crisis_audit
from reframe.safety.classifier import RULES, classify_input
from reframe.safety.escalation import (
    EscalationAction,
    EscalationDecision,
    escalation_decision,
)
from reframe.safety.resources import DEFAULT_CRISIS_RESOURCES, CrisisResource
from reframe.safety.types import (
    SIGNAL_PRECEDENCE,
    SafetyVerdict,
    SignalType,
    VerdictLevel,
)

__all__ = [
    "DEFAULT_CRISIS_RESOURCES",
    "MINIMUM_CRISIS_RECALL",
    "RULES",
    "SIGNAL_PRECEDENCE",
    "AuditReport",
    "CrisisResource",
    "EscalationAction",
    "EscalationDecision",
    "SafetyVerdict",
    "SignalType",
    "VerdictLevel",
    "classify_input",
    "escalation_decision",
    "run_crisis_audit",
]
