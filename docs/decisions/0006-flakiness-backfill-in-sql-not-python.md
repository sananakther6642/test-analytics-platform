# ADR 0006: Flakiness-score backfill migration uses raw SQL, not the Python algorithm

## Status
Accepted

## Context
`test_identity.flakiness_score` existed as a nullable column from the
initial schema, declared with exactly this future use in mind (see
`db/models.py`'s docstring), but nothing populated it — every existing row
was NULL. The plan calls for a deliberately non-trivial migration as a
realistic evolution example, not just an additive column.

The scoring logic itself already exists and is tested:
`analytics/flakiness.py`'s `score_test()`, combining same-commit
disagreement (weighted 0.7) and flip-rate (weighted 0.3). The migration
needs to compute the same score for every existing test.

## Decision
Reimplement the scoring algorithm as raw SQL inside the migration
(`4fea7f7069dd_backfill_flakiness_score.py`), using window functions
(`LAG()`, `COUNT() OVER (PARTITION BY ...)`) rather than importing and
calling `analytics/flakiness.py` from the migration.

**This was chosen with the trade-off explicit, not by default.** The
migration file's own docstring states the real risk: the SQL and the
Python implementation must be kept in sync by hand if the algorithm's
weights or definition change, and this migration will not automatically
reflect such a change.

Verified the two implementations actually agree, not just assumed it:
uploaded a real 30-day synthetic corpus (36 runs, 18 distinct tests)
through the live API, captured the Python-computed scores from
`GET /analytics/flaky`, then ran the migration's exact SQL by hand against
the same data and compared. Every score matched to 4 decimal places
(`test_flaky_1: 0.2648`, `test_flaky_4: 0.1986`, `test_flaky_3: 0.19`,
`test_flaky_0: 0.141`, `test_flaky_2: 0.1324`, all others `0`). Also
verified the migration's actual `UPDATE` (not just the standalone query)
produces identical values in `test_identity`, and that `downgrade()`
genuinely nulls the column (not a no-op) and `upgrade()` correctly
re-backfills it — full round trip against a real database.

## Alternatives considered
- **Call `analytics.flakiness.score_test()` from the migration** (import
  the app's own Python module inside `env.py`'s execution context, which
  is possible since Alembic migrations can run arbitrary Python). Rejected
  in favor of SQL: a schema/data migration coupling to application code
  means the migration's behavior can change if unrelated application code
  changes, and — more importantly for a migration that runs once against
  whatever data exists at that moment — it doesn't need to track future
  algorithm changes at all. A future change to the weights or definition
  should be a conscious decision about whether historical data needs
  re-backfilling (a new migration), not something that happens
  automatically because the migration silently calls current code.
- **Skip the backfill, leave the column NULL until a later phase populates
  it via the application** (e.g. persisting scores on each analytics
  request instead of via migration). Would have avoided the duplication
  question entirely, but the plan specifically wants a realistic
  *migration* evolution example — a `NULL`-only additive column is not
  meaningfully different from the initial schema.

## Consequences
- If `analytics/flakiness.py`'s algorithm changes (different weights, a
  new signal, a different definition of "same commit"), this migration's
  SQL does NOT update automatically and does not need to — but a decision
  should be made explicitly at that time about whether a new backfill
  migration is warranted for historical data, rather than assuming the
  column silently stays correct.
- The verification method used here (upload real data, compare Python
  output to hand-run SQL, then confirm the actual migration produces the
  same result) is the pattern to repeat if this migration or a similar
  data-migration is ever modified — proving numeric equivalence, not just
  "the migration runs without error."
