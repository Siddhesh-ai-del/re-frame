"""Free, public measurement instruments with fail-closed, validated specifications.

Only instruments whose wording and licensing are confirmed free-to-use are
listed in :data:`INSTRUMENTS`. Instruments whose item wording still needs
verification against the published source live in :data:`PENDING_VERIFICATION`
and are deliberately unreachable through :func:`get_instrument` — callers
cannot tell a pending instrument from an unknown one.

As of 2026-10 the pending area is EMPTY: SCS-SF was activated after its item
wording was verified verbatim against the primary source (the official
self-compassion.org SCS-SF information sheet + Neff permission letter). The
fail-closed holding pattern remains for any future unverified instrument.
"""

import re
from dataclasses import dataclass

_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


@dataclass(frozen=True)
class AnswerOption:
    """A single labelled response option on an instrument's scale."""

    value: int
    label: str


@dataclass(frozen=True)
class ItemSpec:
    """One instrument item: a 1-based index and its verbatim prompt."""

    index: int
    prompt: str

    def __post_init__(self) -> None:
        if self.index <= 0:
            raise ValueError(f"ItemSpec.index must be 1-based (> 0), got {self.index}")
        if not self.prompt.strip():
            raise ValueError("ItemSpec.prompt must be a non-empty string")


@dataclass(frozen=True)
class SeverityBand:
    """An inclusive ``lower..upper`` total range mapped to a severity label."""

    label: str
    lower: int
    upper: int

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError(
                f"SeverityBand 'upper' ({self.upper}) must be >= 'lower' ({self.lower})"
            )


@dataclass(frozen=True)
class InstrumentSpec:
    """A fully validated measurement instrument specification.

    Raises:
        ValueError: Naming the offending field whenever the spec is
            malformed — indices must be exactly ``1..N``, answer options must
            exactly cover the scale, and non-empty severity bands must
            partition the total range with no gaps or overlaps.
    """

    id: str
    title: str
    recall_period: str
    items: tuple[ItemSpec, ...]
    scale_min: int
    scale_max: int
    total_min: int
    total_max: int
    answer_options: tuple[AnswerOption, ...]
    severity_bands: tuple[SeverityBand, ...]
    citation: str
    reverse_scored: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        """Enforce every invariant; raise ``ValueError`` naming the bad field."""
        if not _ID_PATTERN.match(self.id):
            raise ValueError(f"InstrumentSpec.id {self.id!r} must match ^[a-z0-9_]+$")
        if not self.title.strip():
            raise ValueError("InstrumentSpec.title must be a non-empty string")
        if not self.recall_period.strip():
            raise ValueError("InstrumentSpec.recall_period must be a non-empty string")
        if len(self.items) < 5:
            raise ValueError(
                f"InstrumentSpec.items must contain at least 5 items, got {len(self.items)}"
            )
        if [item.index for item in self.items] != list(range(1, len(self.items) + 1)):
            raise ValueError(
                "InstrumentSpec.items indices must be exactly 1..N in order, got "
                f"{[item.index for item in self.items]}"
            )
        if self.scale_max <= self.scale_min:
            raise ValueError(
                f"InstrumentSpec.scale_max ({self.scale_max}) must be greater than "
                f"scale_min ({self.scale_min})"
            )
        if self.total_max < self.total_min:
            raise ValueError(
                f"InstrumentSpec.total_max ({self.total_max}) must be >= "
                f"total_min ({self.total_min})"
            )
        if sorted(option.value for option in self.answer_options) != list(
            range(self.scale_min, self.scale_max + 1)
        ):
            raise ValueError(
                "InstrumentSpec.answer_options values must exactly cover "
                f"scale_min..scale_max ({self.scale_min}..{self.scale_max})"
            )
        if self.severity_bands:
            covered: list[int] = []
            for band in self.severity_bands:
                covered.extend(range(band.lower, band.upper + 1))
            if covered != list(range(self.total_min, self.total_max + 1)):
                raise ValueError(
                    "InstrumentSpec.severity_bands must partition total_min..total_max "
                    f"({self.total_min}..{self.total_max}) with no gaps or overlaps"
                )
        if not self.citation.strip():
            raise ValueError("InstrumentSpec.citation must be a non-empty string")
        unknown = set(self.reverse_scored) - {item.index for item in self.items}
        if unknown:
            raise ValueError(
                f"InstrumentSpec.reverse_scored contains unknown item indices: {sorted(unknown)}"
            )


_COMMON_OPTIONS = (
    AnswerOption(0, "Not at all"),
    AnswerOption(1, "Several days"),
    AnswerOption(2, "More than half the days"),
    AnswerOption(3, "Nearly every day"),
)

PHQ9 = InstrumentSpec(
    id="phq9",
    title="Patient Health Questionnaire-9 (PHQ-9)",
    recall_period="the past 2 weeks",
    items=(
        ItemSpec(1, "Little interest or pleasure in doing things"),
        ItemSpec(2, "Feeling down, depressed, or hopeless"),
        ItemSpec(3, "Trouble falling or staying asleep, or sleeping too much"),
        ItemSpec(4, "Feeling tired or having little energy"),
        ItemSpec(5, "Poor appetite or overeating"),
        ItemSpec(
            6,
            "Feeling bad about yourself — or that you are a failure or have let "
            "yourself or your family down",
        ),
        ItemSpec(
            7,
            "Trouble concentrating on things, such as reading the newspaper or watching television",
        ),
        ItemSpec(
            8,
            "Moving or speaking so slowly that other people could have noticed? "
            "Or the opposite — being so fidgety or restless that you have been "
            "moving around a lot more than usual",
        ),
        ItemSpec(
            9,
            "Thoughts that you would be better off dead or of hurting yourself in some way",
        ),
    ),
    scale_min=0,
    scale_max=3,
    total_min=0,
    total_max=27,
    answer_options=_COMMON_OPTIONS,
    severity_bands=(
        SeverityBand("minimal", 0, 4),
        SeverityBand("mild", 5, 9),
        SeverityBand("moderate", 10, 14),
        SeverityBand("moderately severe", 15, 19),
        SeverityBand("severe", 20, 27),
    ),
    citation=(
        "Kroenke, Spitzer & Williams 2001, Journal of General Internal Medicine "
        "(PHQ-9; free to use, no permission required)"
    ),
)

GAD7 = InstrumentSpec(
    id="gad7",
    title="Generalized Anxiety Disorder-7 (GAD-7)",
    recall_period="the past 2 weeks",
    items=(
        ItemSpec(1, "Feeling nervous, anxious, or on edge"),
        ItemSpec(2, "Not being able to stop or control worrying"),
        ItemSpec(3, "Worrying too much about different things"),
        ItemSpec(4, "Trouble relaxing"),
        ItemSpec(5, "Being so restless that it's hard to sit still"),
        ItemSpec(6, "Becoming easily annoyed or irritable"),
        ItemSpec(7, "Feeling afraid, as if something awful might happen"),
    ),
    scale_min=0,
    scale_max=3,
    total_min=0,
    total_max=21,
    answer_options=_COMMON_OPTIONS,
    severity_bands=(
        SeverityBand("minimal", 0, 4),
        SeverityBand("mild", 5, 9),
        SeverityBand("moderate", 10, 14),
        SeverityBand("severe", 15, 21),
    ),
    citation=(
        "Spitzer, Kroenke & Williams 2006, Archives of Internal Medicine "
        "(GAD-7; free to use, no permission required)"
    ),
)

K10 = InstrumentSpec(
    id="k10",
    title="Kessler Psychological Distress Scale (K-10)",
    recall_period="the past 30 days",
    items=(
        ItemSpec(1, "About how often did you feel tired out for no good reason?"),
        ItemSpec(2, "About how often did you feel nervous?"),
        ItemSpec(3, "About how often did you feel so nervous that nothing could calm you down?"),
        ItemSpec(4, "About how often did you feel hopeless?"),
        ItemSpec(5, "About how often did you feel restless or fidgety?"),
        ItemSpec(6, "About how often did you feel so restless you could not sit still?"),
        ItemSpec(7, "About how often did you feel depressed?"),
        ItemSpec(8, "About how often did you feel that everything was an effort?"),
        ItemSpec(9, "About how often did you feel so sad that nothing could cheer you up?"),
        ItemSpec(10, "About how often did you feel worthless?"),
    ),
    scale_min=1,
    scale_max=5,
    total_min=10,
    total_max=50,
    answer_options=(
        AnswerOption(1, "None of the time"),
        AnswerOption(2, "A little of the time"),
        AnswerOption(3, "Some of the time"),
        AnswerOption(4, "Most of the time"),
        AnswerOption(5, "All of the time"),
    ),
    severity_bands=(
        SeverityBand("likely well", 10, 19),
        SeverityBand("mild", 20, 24),
        SeverityBand("moderate", 25, 29),
        SeverityBand("severe", 30, 50),
    ),
    citation="Kessler & Andrews 1993 (K-10; ABS scoring bands; free to use)",
)

SCS_SF = InstrumentSpec(
    id="scs_sf",
    title="Self-Compassion Scale Short Form (SCS-SF)",
    recall_period="in difficult times (typically)",  # dispositional, NOT a fixed window
    items=(  # VERBATIM from the official sheet, 1..12
        ItemSpec(
            1,
            "When I fail at something important to me I become consumed by feelings of inadequacy.",
        ),
        ItemSpec(
            2,
            "I try to be understanding and patient towards those aspects of my "
            "personality I don't like.",
        ),
        ItemSpec(
            3, "When something painful happens I try to take a balanced view of the situation."
        ),
        ItemSpec(
            4,
            "When I'm feeling down, I tend to feel like most other people are "
            "probably happier than I am.",
        ),
        ItemSpec(5, "I try to see my failings as part of the human condition."),
        ItemSpec(
            6,
            "When I'm going through a very hard time, I give myself the caring "
            "and tenderness I need.",
        ),
        ItemSpec(7, "When something upsets me I try to keep my emotions in balance."),
        ItemSpec(
            8,
            "When I fail at something that's important to me, I tend to feel alone in my failure.",
        ),
        ItemSpec(
            9, "When I'm feeling down I tend to obsess and fixate on everything that's wrong."
        ),
        ItemSpec(
            10,
            "When I feel inadequate in some way, I try to remind myself that "
            "feelings of inadequacy are shared by most people.",
        ),
        ItemSpec(11, "I'm disapproving and judgmental about my own flaws and inadequacies."),
        ItemSpec(
            12, "I'm intolerant and impatient towards those aspects of my personality I don't like."
        ),
    ),
    scale_min=1,
    scale_max=5,
    total_min=12,
    total_max=60,
    answer_options=(
        # Endpoints verbatim on the SCS-SF sheet (2,3,4 unlabeled there);
        # middle anchors are those used by Neff's own online SCS test
        # (self-compassion.org/self-compassion-test, verified 2026-10-25):
        # "1 - Almost Never / 2 - Occasionally / 3 - About half of the time /
        # 4 - Fairly Often / 5 - Almost Always". Frequency framing matches the
        # sheet's instruction "Indicate how often you behave in the stated
        # manner". Casing follows the sheet for endpoints.
        AnswerOption(1, "Almost never"),
        AnswerOption(2, "Occasionally"),
        AnswerOption(3, "About half of the time"),
        AnswerOption(4, "Fairly Often"),
        AnswerOption(5, "Almost always"),
    ),
    severity_bands=(
        # The sheet's ad hoc rubric is on the MEAN scale (1.0-2.49 low,
        # 2.5-3.5 moderate, 3.51-5.0 high); mapped to the integer sum by
        # x12 (each subscale has 2 items, so the total mean = sum/12).
        SeverityBand("low", 12, 29),
        SeverityBand("moderate", 30, 42),
        SeverityBand("high", 43, 60),
    ),
    citation=(
        "Raes, Pommier, Neff & Van Gucht 2011, Clinical Psychology & "
        "Psychotherapy (SCS-SF; free to use with attribution per Neff / "
        "self-compassion.org). Response anchors 1=Almost never…5=Almost always "
        "are the standard SCS scale the short form inherits. Total = sum of the "
        "12 items after reverse-scoring items 1,4,8,9,11,12 (the Raes et al. "
        "2011 item-total method); the modern mean score is total/12 on a 1–5 "
        "scale. The low/moderate/high bands are the source's explicitly AD HOC "
        "rubric — there are NO clinical norms for self-compassion; treat them "
        "as descriptive, not diagnostic."
    ),
    reverse_scored=(1, 4, 8, 9, 11, 12),
)

#: ACTIVE registry. Only confirmed free, verbatim-worded instruments.
INSTRUMENTS: dict[str, InstrumentSpec] = {spec.id: spec for spec in (PHQ9, GAD7, K10, SCS_SF)}

#: Fail-closed holding area: specs here are NOT reachable via :func:`get_instrument`.
#: EMPTY as of 2026-10 — SCS-SF was activated after primary-source verification.
PENDING_VERIFICATION: dict[str, InstrumentSpec] = {}


def get_instrument(instrument_id: str) -> InstrumentSpec:
    """Return the ACTIVE instrument named ``instrument_id``.

    Raises:
        ValueError: If ``instrument_id`` is unknown or names a pending
            instrument — the two cases are indistinguishable to callers,
            so unverified instruments fail closed exactly like typos.
    """
    try:
        return INSTRUMENTS[instrument_id]
    except KeyError:
        raise ValueError(f"unknown or unavailable instrument {instrument_id!r}") from None
