# Evaluation harness — adverse-event logging (Stage 7a)

Safety-monitoring instrumentation for the RE:FRAME feasibility pilot. This
document covers what Stage 7a delivers: the pre-specified adverse-event (AE)
taxonomy, the fail-closed AE log (in-memory + durable SQLite), the automatic
and audit detectors, and the `/evaluation/adverse-events` API. Pilot metrics,
progression criteria, and the feasibility report are Stage 7b (planned, not
built); the report UI is Stage 7c (planned, not built).

## Honest framing: pre-specified DESIGN definitions

The six AE types below are **RE:FRAME pre-specified design definitions**.
They are **not** validated published adverse-event definitions — none exist
for GenAI mental-health interventions: none of the 21 reviewed GenAI
interventions defines an adverse event (Olisaeloka et al. 2026,
*Healthcare*, DOI 10.3390/healthcare14101395). The AI-specific direction
(AE definitions plus human escalation pathways) follows the US FDA Digital
Health Advisory Committee (6 Nov 2025) and the UK MHRA DMHT AE-reporting
direction; the early-worsening monitoring signal follows NICE NG222
rec. 1.2.10. Every definition, threshold, and criterion in this harness is
provisional pending pilot validation, and none of it is a clinical claim.

## The taxonomy (six types)

| Type | Definition (pre-specified) | Citation | Default serious | Rationale |
|---|---|---|---|---|
| `crisis_response_failure` | A turn classified as crisis-level did not receive the scripted crisis response — the deterministic escalation layer failed to bypass the model for a person in crisis. | Pre-specified AI-specific AE definition (RE:FRAME design); Olisaeloka et al. 2026, *Healthcare*, DOI 10.3390/healthcare14101395; direction per US FDA Digital Health Advisory Committee, 6 Nov 2025. | **Yes** | The response a person in crisis depended on did not arrive; highest-harm class. |
| `hallucinated_clinical_claim` | Delivered output stated a clinical fact, diagnosis, or treatment claim not grounded in the curated exercise library — an invented or unverifiable claim. | Same design citation (Olisaeloka et al. 2026; FDA DHAC, 6 Nov 2025). | No | Content defect; seriousness judged by review. |
| `boundary_violation_diagnosis` | Delivered output diagnosed, assigned a risk category, or presented itself as care — a breach of the non-diagnostic wellness boundary. | Same design citation. | No | Content defect; seriousness judged by review. |
| `sycophancy_episode` | Delivered output agreed with or reinforced harmful reasoning instead of holding the safety line. | Same design citation. | No | Content defect; seriousness judged by review. |
| `inappropriate_or_delayed_escalation` | Escalation was shown when it should not have been, withheld when it should have been shown, or arrived outside the pre-specified response path. | Same design citation (the FDA sentence especially). | **Yes** | Escalation-pathway failure, the highest-harm class after crisis-response failure. |
| `transient_early_worsening` | A completed check-in showed a pre-specified increase over that instrument's baseline within the early window — a participant-level untoward-outcome signal detected by the check-in flags. | NICE NG222 rec. 1.2.10 (early worsening after starting an intervention is an AE signal to monitor); detection thresholds are provisional design defaults pending pilot validation. | No | A monitoring signal, not itself a serious event; review may escalate. |

Seriousness is pre-specified per type (the table above, decision **D2**) and
overridable at record time by a pilot reviewer: the POST body's optional
`serious` field wins over the default.

## Detection sources

Every record carries exactly one source (**D4**):

- **`automatic`** — the in-product detector fired. Today exactly one field
  signal is auto-detected (**D5**): a recorded check-in carrying the
  `EARLY_WORSENSING` flag becomes one `transient_early_worsening` event,
  appended by the `POST /checkins` route when an AE log is wired in
  (always, in the composed product service). The deterministic safety layer
  itself is never instrumented or modified: a crisis turn that escalates
  correctly is the product **working**, never an adverse event.
- **`audit`** — a seeded-corpus audit miss: a crisis-class text the
  classifier failed to flag, detected before any participant impact
  (a near-miss). Each `AuditReport` miss becomes one
  `crisis_response_failure` event. The converter is pure and tested now;
  the CLI that will invoke it (`--audit`) is Stage 7b (planned).
- **`review`** — entered by a pilot reviewer over HTTP. The
  `POST /evaluation/adverse-events` endpoint always stamps
  `source="review"` server-side; the client cannot set or spoof a source
  (unknown body fields are rejected).

## The no-content rule (D1)

AE records never carry message content — **ever**. Each record's
`reference` is a locator string only (non-empty after stripping, at most
200 characters): an instrument id/date/total (automatic), a content-free
truncated sha256 digest of the missed text (audit), or a reviewer locator
like `"session 3 turn 14"` (review). Check-in response vectors and turn
text are never accepted into, stored in, or returned from an AE record.

## The 48-hour follow-up marker (D3)

Serious events get `followup_due_at = detected_at + 48h`, computed as a
**property** from `serious` + `detected_at` (one constant,
`SERIOUS_FOLLOWUP_HOURS = 48`; NIA/NIH DSMP serious-unexpected-event
reporting timeline, design-applied) — never a stored column, so the policy
lives in exactly one place. Non-serious events have `followup_due_at:
null`. `POST /evaluation/adverse-events/{id}/followup` records that a
reviewer addressed the event (`followup_completed: true`); the due marker
stays visible. An unknown id is a loud 404, never a silent no-op.

## Fail-closed durable log

- In-memory `AdverseEventLog`: insertion-ordered, duplicate ids rejected on
  seed and append, unknown follow-up ids raise.
- Durable `PersistentAdverseEventLog` over `SqliteAdverseEventStore`: one
  lock-guarded SQLite connection per store; **all-or-nothing** semantics —
  a store failure rolls the in-memory change back and re-raises, so the
  log exists either everywhere or nowhere. A durable append failure
  surfaces as a generic HTTP 500 (never dressed up as a 422, never
  swallowed): the AE response never pretends success (**D7**).
- Loading is fail-closed: a malformed stored row makes `load()` raise
  naming the event id — rows are never silently skipped.
- The composed service **always** builds a log — durable when `db_path` is
  given, in-memory otherwise — attached to `app.state.ae_log`; the product
  path can never silently skip safety recording (**D8**).

## Independence from the journal purge (D6)

AE records are **safety monitoring records**, independent of the journal
purge: `DELETE /checkins` removes check-in rows only and never touches
adverse-event records. Purging journal data cannot silently destroy safety
records — the two stores are separate (separate tables, separate
connections), and no code path couples them.

## API surface (Stage 7a)

All routes live under the `/evaluation/*` namespace (the SPA owns none of
them) and return operational safety-monitoring data, never clinical
claims:

| Route | Behavior |
|---|---|
| `GET /evaluation/adverse-events` | Every logged event in insertion order (`AdverseEventListOut`). |
| `POST /evaluation/adverse-events` | Record one reviewer event; `source` always `review`; `serious` optional (taxonomy default when omitted); 422 with one generic detail on any failure. |
| `POST /evaluation/adverse-events/{event_id}/followup` | Mark the follow-up completed; unknown id → 404 with one generic detail. |

Error mapping is deliberately boring: one generic 422 detail for every
record-level failure (unknown type, invalid reference, duplicate id) and
one generic 404 detail for unknown ids — no internals leak either way.

## Planned next (not built in 7a)

- **Stage 7b** — feasibility-pilot metrics (retention, data completeness,
  safety-event rate), pre-specified green/amber/red progression criteria
  (provisional, cited), a structured feasibility report with an explicit
  non-efficacy banner, `GET /evaluation/report`, and CLI `--report` /
  `--audit` flags.
- **Stage 7c** — web UI for the pilot report surface, with progression
  criteria rendered as text labels only (never red/amber/green risk color
  fills).
