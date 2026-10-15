"""Wellness-lane lint: the packaged library must stay free of clinical claims.

Scans every string field of every packaged module against
:data:`BANNED_CLAIM_PATTERNS` (case-insensitive), verifies citations are drawn
only from the approved anchor list, and checks evidence-tier honesty rules.
"""

import re

import pytest

from reframe.content.library import default_library
from reframe.content.schema import ExerciseCategory, ExerciseModule

BANNED_CLAIM_PATTERNS: dict[str, re.Pattern[str]] = {
    "treat": re.compile(r"\btreat\w*\b", re.IGNORECASE),
    "therapy": re.compile(r"\btherap(?:y|ies)\b", re.IGNORECASE),
    "therapist": re.compile(r"\btherapists?\b", re.IGNORECASE),
    "cure": re.compile(r"\bcur(?:e|es|ed|ing)\b", re.IGNORECASE),
    "diagnos": re.compile(r"\bdiagnos\w*\b", re.IGNORECASE),
    "prescrib": re.compile(r"\bprescrib\w*\b", re.IGNORECASE),
    "medication": re.compile(r"\bmedications?\b", re.IGNORECASE),
    "clinically proven": re.compile(r"\bclinically proven\b", re.IGNORECASE),
    "healing your depression": re.compile(r"\bhealing your depression\b", re.IGNORECASE),
}

REQUIRED_BANNED_KEYWORDS = (
    "treat",
    "therapy",
    "therapist",
    "cure",
    "diagnos",
    "prescrib",
    "medication",
    "clinically proven",
    "healing your depression",
)

ALLOWED_CITATIONS = frozenset(
    {
        "NICE NG222 depression in adults (2022)",
        "Spinhoven et al. 2018, Behavior Research and Therapy (meta-analysis: "
        "rumination-focused CBT)",
        "Stenzel et al. 2025, Psychological Medicine (meta-analysis: rumination-focused "
        "interventions)",
        "Krieger et al. 2019 (online compassion training for self-criticism)",
        "Tong et al. 2024, EBioMedicine (meta-analysis: self-guided digital interventions)",
    }
)

DOI_PATTERN = re.compile(r"\bdoi\b|\b10\.\d{4,9}/", re.IGNORECASE)


def string_fields(module: ExerciseModule) -> list[tuple[str, str]]:
    """Every string field of ``module`` as ``(field_name, value)`` pairs."""
    fields: list[tuple[str, str]] = [
        ("id", module.id),
        ("title", module.title),
        ("summary", module.summary),
        ("category", module.category.value),
        ("tier", module.tier.value),
        ("safety_class", module.safety_class.value),
    ]
    fields += [(f"steps[{i}]", step) for i, step in enumerate(module.steps)]
    fields += [(f"sources[{i}]", source) for i, source in enumerate(module.sources)]
    fields += [(f"contraindications[{i}]", text) for i, text in enumerate(module.contraindications)]
    return fields


def banned_claims_in(module: ExerciseModule) -> list[str]:
    """Describe every banned-claim hit in ``module`` (empty when clean)."""
    hits: list[str] = []
    for field, value in string_fields(module):
        for name, pattern in BANNED_CLAIM_PATTERNS.items():
            match = pattern.search(value)
            if match is not None:
                hits.append(
                    f"module {module.id!r} field {field}: banned claim {name!r} "
                    f"matched {match.group(0)!r} in {value!r}"
                )
    return hits


# ---------------------------------------------------------------------------
# Pattern-table integrity
# ---------------------------------------------------------------------------


def test_banned_patterns_cover_every_required_keyword() -> None:
    assert set(BANNED_CLAIM_PATTERNS) >= set(REQUIRED_BANNED_KEYWORDS)


@pytest.mark.parametrize(
    ("keyword", "sample"),
    [
        ("treat", "You should seek treatment."),
        ("therapy", " Therapy can help."),
        ("therapist", "Ask a Therapist."),
        ("cure", "A guaranteed cure."),
        ("diagnos", "DIAGNOSIS of any kind."),
        ("prescrib", "Prescribing medication."),
        ("medication", "Medications are not advised."),
        ("clinically proven", "Clinically Proven results."),
        ("healing your depression", "Healing Your Depression fast."),
    ],
)
def test_banned_pattern_matches_its_keyword_case_insensitively(keyword: str, sample: str) -> None:
    pattern = BANNED_CLAIM_PATTERNS[keyword]
    assert pattern.search(sample), f"pattern {keyword!r} failed to flag {sample!r}"
    assert pattern.flags & re.IGNORECASE, keyword


# ---------------------------------------------------------------------------
# The packaged library must be clean
# ---------------------------------------------------------------------------


def test_library_is_wellness_lane_clean() -> None:
    modules = default_library().modules
    assert modules, "packaged library is empty"
    failures: list[str] = []
    for module in modules:
        failures.extend(banned_claims_in(module))
    assert not failures, "wellness-lane violations:\n" + "\n".join(failures)


def test_every_string_field_is_actually_scanned() -> None:
    module = next(m for m in default_library().modules if m.contraindications)
    fields = [name for name, _value in string_fields(module)]
    assert fields[:4] == ["id", "title", "summary", "category"]
    assert any(name.startswith("steps[") for name in fields)
    assert any(name.startswith("sources[") for name in fields)
    assert any(name.startswith("contraindications[") for name in fields)


# ---------------------------------------------------------------------------
# Citations: approved anchors only, human-readable, no DOIs
# ---------------------------------------------------------------------------


def test_every_source_is_an_approved_anchor_citation() -> None:
    for module in default_library().modules:
        for source in module.sources:
            assert source in ALLOWED_CITATIONS, (
                f"module {module.id!r} cites a non-approved source: {source!r}"
            )


def test_sources_contain_no_dois() -> None:
    for module in default_library().modules:
        for source in module.sources:
            assert not DOI_PATTERN.search(source), (
                f"module {module.id!r} source looks like a DOI: {source!r}"
            )


def test_every_module_has_at_least_one_source() -> None:
    for module in default_library().modules:
        assert module.sources, module.id


# ---------------------------------------------------------------------------
# Evidence-tier honesty rules
# ---------------------------------------------------------------------------


def test_emotion_regulation_modules_are_not_tier_a() -> None:
    for module in default_library().by_category(ExerciseCategory.EMOTION_REGULATION):
        assert module.tier.value in {"B", "C"}, module.id


def test_rumination_and_activation_modules_are_tier_a() -> None:
    library = default_library()
    for category in (ExerciseCategory.RUMINATION, ExerciseCategory.BEHAVIORAL_ACTIVATION):
        for module in library.by_category(category):
            assert module.tier.value == "A", module.id


def test_contraindications_present_where_painful_material_may_surface() -> None:
    required = {"self-compassion-break", "self-criticism-noticing", "common-humanity-reminder"}
    library = default_library()
    for module_id in sorted(required):
        module = library.by_id(module_id)
        assert module.contraindications, module_id


def test_trauma_guard_contraindication_wording_exists() -> None:
    module = default_library().by_id("self-compassion-break")
    text = " ".join(module.contraindications)
    assert "traumatic memories" in text
    assert "pause and seek support" in text
