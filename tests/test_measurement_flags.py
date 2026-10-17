"""Tests for ``reframe.measurement.flags`` — longitudinal check-in flags.

Strict TDD: these tests were written BEFORE ``reframe/measurement/flags.py``
exists; the first run must fail with ``ModuleNotFoundError`` (RED).

Grounding (provisional design defaults, pending pilot validation):
- NICE NG225: summed scores never drive risk categories — flags are
  single-item escalations or pre-specified adverse-event signals, not
  re-labelling of totals.
- PHQ-9 item 9 ("better off dead or of hurting yourself") is a single-item
  escalation flag regardless of the summed total.
- NICE NG222 rec. 1.2.10: early worsening after starting (score increase vs
  baseline within the first 14 days) is a pre-specified adverse-event signal.
- NICE NG222 rec. 1.4.3 (design-applied): score >= 16 persisting across two
  consecutive check-ins prompts a professional-referral conversation.
"""

from dataclasses import FrozenInstanceError

import pytest

from reframe.measurement.flags import (
    DEFAULT_EARLY_WORSENSING_THRESHOLDS,
    CheckInFlag,
    EarlyWorseningPolicy,
    checkin_flags,
)

PHQ9_ZEROS = (0, 0, 0, 0, 0, 0, 0, 0, 0)


def _phq9(item9: int = 0) -> tuple[int, ...]:
    """A minimal valid PHQ-9 response vector: only item 9 non-zero."""
    return (0, 0, 0, 0, 0, 0, 0, 0, item9)


# ---------------------------------------------------------------- enum shape


def test_checkin_flag_is_string_enum_with_expected_members() -> None:
    assert [flag.value for flag in CheckInFlag] == [
        "escalate",
        "early_worsening",
        "referral_prompt",
    ]
    assert isinstance(CheckInFlag.ESCALATE, str)


# ------------------------------------------------------------------ policy


def test_default_policy_thresholds_and_window_are_provisional_defaults() -> None:
    policy = EarlyWorseningPolicy()
    assert dict(policy.thresholds) == {"phq9": 5, "gad7": 4, "k10": 5}
    assert policy.window_days == 14
    assert DEFAULT_EARLY_WORSENSING_THRESHOLDS == {"phq9": 5, "gad7": 4, "k10": 5}


def test_default_policy_instances_do_not_share_threshold_state() -> None:
    first = EarlyWorseningPolicy()
    second = EarlyWorseningPolicy()
    assert first.thresholds is not second.thresholds


def test_policy_thresholds_are_read_only() -> None:
    policy = EarlyWorseningPolicy()
    with pytest.raises(TypeError):
        policy.thresholds["phq9"] = 99  # type: ignore[index]


def test_policy_is_frozen() -> None:
    policy = EarlyWorseningPolicy()
    with pytest.raises(FrozenInstanceError):
        policy.window_days = 7  # type: ignore[misc]


@pytest.mark.parametrize("bad_threshold", [0, -1])
def test_policy_rejects_non_positive_thresholds(bad_threshold: int) -> None:
    with pytest.raises(ValueError, match="threshold"):
        EarlyWorseningPolicy(thresholds={"phq9": bad_threshold})


@pytest.mark.parametrize("bad_window", [0, -3])
def test_policy_rejects_non_positive_window(bad_window: int) -> None:
    with pytest.raises(ValueError, match="window_days"):
        EarlyWorseningPolicy(window_days=bad_window)


# ------------------------------------------------------------------- ESCALATE
# PHQ-9 item 9 (index 8) is a single-item escalation flag (NICE NG225):
# any positive answer escalates regardless of the summed total.


def test_item9_positive_escalates_even_with_low_total() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=_phq9(item9=1),
        total=1,
        baseline_total=0,
        days_since_baseline=7,
        previous_total=0,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.ESCALATE,)


def test_item9_positive_escalates_on_first_checkin_without_baseline() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=_phq9(item9=3),
        total=3,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.ESCALATE,)


def test_item9_zero_does_not_escalate() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=_phq9(item9=0),
        total=0,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


# ------------------------------------------------------------ EARLY_WORSENSING
# NICE NG222 rec. 1.2.10 (design-applied): increase vs baseline within the
# first 14 days is a pre-specified adverse-event signal. Thresholds provisional.


def test_early_worsening_at_exact_threshold_on_window_edge() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),  # total 5, delta 5 over baseline 0
        total=5,
        baseline_total=0,
        days_since_baseline=14,  # exact window edge (inclusive)
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.EARLY_WORSENSING,)


def test_no_early_worsening_below_threshold() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 0, 0),  # total 4, delta 4 < threshold 5
        total=4,
        baseline_total=0,
        days_since_baseline=7,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_early_worsening_outside_window() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),
        total=5,
        baseline_total=0,
        days_since_baseline=15,  # window_days + 1
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_early_worsening_before_baseline_date() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),
        total=5,
        baseline_total=0,
        days_since_baseline=-1,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_early_worsening_without_baseline() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),
        total=5,
        baseline_total=None,
        days_since_baseline=7,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_early_worsening_when_days_unknown() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),
        total=5,
        baseline_total=0,
        days_since_baseline=None,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_gad7_early_worsening_uses_gad7_threshold() -> None:
    # GAD-7 threshold 4: baseline 6, total 10 -> delta 4 >= 4.
    flags = checkin_flags(
        instrument_id="gad7",
        responses=(2, 2, 2, 2, 1, 1, 0),
        total=10,
        baseline_total=6,
        days_since_baseline=10,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.EARLY_WORSENSING,)


def test_k10_early_worsening_uses_k10_threshold() -> None:
    # K-10 threshold 5: baseline 20, total 25 -> delta 5 >= 5.
    flags = checkin_flags(
        instrument_id="k10",
        responses=(2, 2, 2, 2, 2, 2, 2, 2, 2, 5),
        total=25,
        baseline_total=20,
        days_since_baseline=5,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.EARLY_WORSENSING,)


def test_unknown_instrument_produces_no_flags() -> None:
    # No phq-9 rules, no threshold — an unknown instrument must stay silent
    # here (it is already rejected at record time; flags stay fail-closed).
    flags = checkin_flags(
        instrument_id="not_an_instrument",
        responses=(0, 0, 0, 1, 1, 1, 1, 1, 0),
        total=5,
        baseline_total=0,
        days_since_baseline=3,
        previous_total=17,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


# ----------------------------------------------------------- REFERRAL_PROMPT
# NICE NG222 rec. 1.4.3, design-applied: two consecutive scores >= 16 prompt
# a professional-referral conversation. Thresholds provisional.


@pytest.mark.parametrize(("previous", "current"), [(16, 16), (16, 20), (24, 16)])
def test_referral_prompt_on_two_consecutive_scores_at_or_above_16(
    previous: int, current: int
) -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=PHQ9_ZEROS,
        total=current,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=previous,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (CheckInFlag.REFERRAL_PROMPT,)


def test_no_referral_prompt_when_previous_below_16() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=PHQ9_ZEROS,
        total=16,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=15,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_referral_prompt_when_current_below_16() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=PHQ9_ZEROS,
        total=14,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=16,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


def test_no_referral_prompt_on_first_checkin() -> None:
    flags = checkin_flags(
        instrument_id="phq9",
        responses=PHQ9_ZEROS,
        total=18,
        baseline_total=None,
        days_since_baseline=None,
        previous_total=None,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == ()


# ------------------------------------------------------- combinations / order


def test_flags_combine_in_enum_order_without_duplicates() -> None:
    # Item 9 > 0, delta 10 >= 5 within window, previous and current >= 16:
    # all three flags, in enum declaration order, each appearing once.
    flags = checkin_flags(
        instrument_id="phq9",
        responses=_phq9(item9=2),
        total=20,
        baseline_total=10,
        days_since_baseline=7,
        previous_total=17,
        policy=EarlyWorseningPolicy(),
    )
    assert flags == (
        CheckInFlag.ESCALATE,
        CheckInFlag.EARLY_WORSENSING,
        CheckInFlag.REFERRAL_PROMPT,
    )
    assert len(flags) == len(set(flags))
