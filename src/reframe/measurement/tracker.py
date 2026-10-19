"""In-memory longitudinal check-in tracking (deterministic, NOT thread-safe).

One :class:`CheckInTracker` per conversation, one caller: the tracker keeps
check-ins in memory only and performs no locking — callers must not share an
instance across threads. Data quality is fail-closed: unknown instruments
and out-of-order check-in dates are rejected rather than silently repaired.

Flags on each :class:`CheckIn` come from
:func:`reframe.measurement.flags.checkin_flags` and are never risk
categories of the person (NICE NG225); thresholds are provisional design
defaults pending pilot validation.
"""

import datetime
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from reframe.measurement.flags import CheckInFlag, EarlyWorseningPolicy, checkin_flags
from reframe.measurement.instruments import get_instrument
from reframe.measurement.scoring import score

_CHECKIN_KEYS = frozenset(
    {"instrument_id", "date", "responses", "total", "severity_label", "flags"}
)


@dataclass(frozen=True)
class CheckIn:
    """One recorded instrument completion: raw data, score, and pre-specified flags."""

    instrument_id: str
    date: datetime.date
    responses: tuple[int, ...]
    total: int
    severity_label: str | None
    flags: tuple[CheckInFlag, ...]


def _checkin_from_entry(entry: Any) -> CheckIn:
    """Rebuild one :class:`CheckIn` from a serialized mapping.

    Raises:
        ValueError: If the entry's keys don't exactly match the schema
            ("malformed check-in") or any flag value is unknown ("flag").
    """
    if set(entry) != _CHECKIN_KEYS:
        raise ValueError(
            f"malformed check-in entry: expected keys {sorted(_CHECKIN_KEYS)}, got {sorted(entry)}"
        )
    try:
        flags = tuple(CheckInFlag(flag) for flag in entry["flags"])
    except ValueError:
        raise ValueError(f"bad flag value in check-in entry: {entry['flags']!r}") from None
    return CheckIn(
        instrument_id=entry["instrument_id"],
        date=datetime.date.fromisoformat(entry["date"]),
        responses=tuple(entry["responses"]),
        total=entry["total"],
        severity_label=entry["severity_label"],
        flags=flags,
    )


class CheckInTracker:
    """Chronological, per-instrument check-in history for one conversation.

    Deterministic and in-memory; NOT thread-safe (no locking — one caller
    per instance). Out-of-order dates for the same instrument are rejected
    (fail-closed data quality); same-day check-ins are allowed.
    """

    def __init__(self, policy: EarlyWorseningPolicy | None = None) -> None:
        self._policy = policy if policy is not None else EarlyWorseningPolicy()
        self._records: dict[str, list[CheckIn]] = {}

    def record(self, instrument_id: str, responses: Sequence[int], date: datetime.date) -> CheckIn:
        """Score, flag, and append one check-in; returns the recorded :class:`CheckIn`.

        The baseline for future early-worsening comparisons is the FIRST
        check-in of the same instrument; ``previous_total`` for the referral
        prompt is the immediately preceding check-in of the same instrument.
        The first check-in of an instrument can never carry
        EARLY_WORSENSING or REFERRAL_PROMPT, but CAN carry ESCALATE (item 9
        on day one still escalates).

        Raises:
            ValueError: For unknown/pending instruments, invalid responses
                (via :func:`score`), or an out-of-order date (earlier than
                the latest existing check-in for that instrument).
        """
        get_instrument(instrument_id)
        prior = self._records.get(instrument_id, [])
        if prior and date < prior[-1].date:
            raise ValueError(
                f"out-of-order check-in for {instrument_id!r}: {date.isoformat()} is earlier "
                f"than the latest recorded check-in {prior[-1].date.isoformat()}"
            )
        result = score(instrument_id, responses)
        baseline = prior[0] if prior else None
        flags = checkin_flags(
            instrument_id=instrument_id,
            responses=result.responses,
            total=result.total,
            baseline_total=baseline.total if baseline is not None else None,
            days_since_baseline=(date - baseline.date).days if baseline is not None else None,
            previous_total=prior[-1].total if prior else None,
            policy=self._policy,
        )
        checkin = CheckIn(
            instrument_id=instrument_id,
            date=date,
            responses=result.responses,
            total=result.total,
            severity_label=result.severity_label,
            flags=flags,
        )
        self._records.setdefault(instrument_id, []).append(checkin)
        return checkin

    def history(self, instrument_id: str) -> tuple[CheckIn, ...]:
        """All check-ins for ``instrument_id`` in chronological order.

        Raises:
            ValueError: If no check-ins exist for that instrument (unknown
                or simply never recorded — indistinguishable, fail-closed).
        """
        try:
            return tuple(self._records[instrument_id])
        except KeyError:
            raise ValueError(f"no check-ins recorded for instrument {instrument_id!r}") from None

    def latest(self, instrument_id: str) -> CheckIn | None:
        """Most recent check-in for ``instrument_id``, or ``None``."""
        records = self._records.get(instrument_id)
        return records[-1] if records else None

    def baseline(self, instrument_id: str) -> CheckIn | None:
        """First (baseline) check-in for ``instrument_id``, or ``None``."""
        records = self._records.get(instrument_id)
        return records[0] if records else None

    def delete_all(self) -> int:
        """Drop every recorded check-in from memory; return how many were dropped.

        The in-memory tracker holds no durable copy, so clearing its records
        IS the complete purge. ``PersistentCheckInTracker`` overrides this to
        purge its store as well (memory and disk stay in step — a purge must
        not resurrect rows on the next restart). Idempotent: an empty tracker
        purges to ``0``.
        """
        removed = sum(len(records) for records in self._records.values())
        self._records.clear()
        return removed

    def to_dict(self) -> dict[str, Any]:
        """Serialize every check-in (flags as their string values). The policy
        is not serialized — pass it back to :meth:`from_dict` explicitly."""
        return {
            "checkins": [
                {
                    "instrument_id": checkin.instrument_id,
                    "date": checkin.date.isoformat(),
                    "responses": list(checkin.responses),
                    "total": checkin.total,
                    "severity_label": checkin.severity_label,
                    "flags": [flag.value for flag in checkin.flags],
                }
                for checkin in self._all_checkins()
            ]
        }

    def _all_checkins(self) -> list[CheckIn]:
        """Every check-in across instruments, in insertion (global) order."""
        return [checkin for records in self._records.values() for checkin in records]

    @classmethod
    def from_dict(
        cls, data: Mapping[str, Any], policy: EarlyWorseningPolicy | None = None
    ) -> "CheckInTracker":
        """Rebuild a tracker from :meth:`to_dict` output, restoring flags verbatim.

        Score and flag computation are NOT re-run: the recorded flags are the
        authority. ``policy`` is not part of the serialized schema, so a
        non-default policy must be passed explicitly to continue an existing
        timeline under it.

        Raises:
            ValueError: For malformed data — a bad top-level key, a
                non-list ``checkins``, a check-in entry whose keys don't
                match the schema, or an unknown flag value.
        """
        if set(data) != {"checkins"}:
            raise ValueError(
                f"malformed tracker data: expected only the 'checkins' key, got {sorted(data)}"
            )
        raw_checkins = data["checkins"]
        if not isinstance(raw_checkins, list):
            raise ValueError(
                f"malformed tracker data: 'checkins' must be a list, "
                f"got {type(raw_checkins).__name__}"
            )
        tracker = cls(policy=policy)
        for entry in raw_checkins:
            tracker._append_restored(_checkin_from_entry(entry))
        return tracker

    def _append_restored(self, checkin: CheckIn) -> None:
        """Append one deserialized check-in without re-scoring or re-flagging."""
        self._records.setdefault(checkin.instrument_id, []).append(checkin)
