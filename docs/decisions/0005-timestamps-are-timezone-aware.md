# ADR 0005: All stored timestamps are timezone-aware

## Status
Accepted

## Context
`started_at` and `finished_at` were originally declared as plain
`Mapped[datetime]` columns with no explicit type, which SQLAlchemy maps to
`TIMESTAMP WITHOUT TIME ZONE` on Postgres by default.

This wasn't caught by any test before shipping, because every test fixture
used naive `datetime(2026, 1, 1, ...)` literals — which matched the naive
column type by coincidence, not by design. The bug surfaced only when
`tools/generate_reports.py`'s real corpus (which correctly uses
`datetime.now(timezone.utc)`, since real CI systems run in real timezones)
was uploaded through the actual running stack: every insert failed with
`can't subtract offset-naive and offset-aware datetimes`, a 500 on every
upload.

This is a direct instance of a broader lesson: unit and integration tests
built from hand-written fixtures can silently share a wrong assumption
with the code under test, and only genuinely independent data — generated
separately, for a different reason — exposes the mismatch. This project's
own synthetic generator did that job here.

## Decision
Every timestamp column (`test_runs.started_at`, `test_runs.finished_at`,
`test_results.started_at`) is explicitly `DateTime(timezone=True)` —
Postgres `TIMESTAMPTZ`, not `TIMESTAMP`. All application and test code
constructs timezone-aware datetimes (`tzinfo=timezone.utc` or equivalent)
when building these values.

## Alternatives considered
- **Keep columns naive; strip timezone info at the parser/generator
  boundary before it reaches storage.** Smaller diff (no migration), but
  this is exactly the class of fix that produced the bug in the first
  place: it relies on every future write path remembering to normalize
  timezone info correctly, rather than making the wrong state
  unrepresentable. A new upload path, a new generator, or a future
  Terraform-provisioned Postgres with a different server timezone default
  could reintroduce the exact same failure.
- **Silently coerce/strip timezone in the ORM layer** (e.g. a SQLAlchemy
  type decorator that drops tzinfo automatically). Rejected for the same
  reason plus an additional one: it hides real timezone information that
  matters for a test-analytics tool specifically — CI runs across
  different environments and timezones are exactly the kind of thing a
  trend-by-day query could get subtly wrong if timestamps were silently
  shifted or truncated.

## Consequences
- Migration `d03862a437ec` (`make timestamps timezone-aware`) alters all
  three columns from `TIMESTAMP` to `TIMESTAMPTZ` — tested in both
  directions against a real database (upgrade, downgrade, re-upgrade from
  empty) before being trusted.
- Test fixtures that construct `ParsedRun`/`TestRun` objects for anything
  that touches the database must use timezone-aware datetimes. Fixtures
  for pure in-memory logic (e.g. `tests/unit/test_flakiness.py`, which
  never touches Postgres) are unaffected and correctly remain naive for
  simplicity, since the flakiness algorithm only compares relative
  ordering, not absolute time zones.
- This is also a concrete example, not just a rule, for why "verify against
  real generated data, not just hand-picked test fixtures" matters as a
  practice on this project — the generator caught something 30 passing
  unit/integration tests did not.
