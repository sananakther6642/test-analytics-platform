# ADR 0003: Denormalize started_at and git_sha onto test_results

## Status
Accepted

## Context
The schema has `test_runs` (one row per uploaded report) and `test_results`
(one row per test within a run), foreign-keyed together. Two queries run on
every dashboard load:

- **Trend aggregation** — group test results by day, which needs
  `started_at`.
- **Flaky-test detection** — group by `test_id`, then by `git_sha` (for
  same-commit disagreement) and by chronological order (for flip-rate).

Both `started_at` and `git_sha` are properties of the *run*, not the
individual result, so a strictly normalized schema would only store them on
`test_runs` and require a join to `test_results` for every one of these
queries.

## Decision
Denormalize: copy `started_at` and `git_sha` onto each `test_results` row at
insert time, in addition to keeping them on `test_runs` (which stays the
source of truth). Add a composite index `(test_id, started_at)` and a
separate index on `git_sha`, both on `test_results` directly.

## Alternatives considered
- **Strict normalization, join at query time.** No redundant data, but every
  flakiness/trend query — which runs on every dashboard load, not
  occasionally — pays a join cost, and a composite index spanning two
  tables isn't possible in Postgres the way a single-table composite index
  is. Rejected: this is exactly the kind of hot, repeated read path where
  the read-performance argument for denormalization is strongest, not a
  case of denormalizing prematurely.
- **A materialized view or summary table joining the two.** Gets the same
  query-time benefit without duplicating columns on the base table, but
  adds a refresh-timing concern (stale until refreshed, or triggers to keep
  it current) for a two-column duplication that doesn't need that
  complexity. Worth revisiting if trend queries actually show up slow under
  `EXPLAIN ANALYZE` at real data volumes — not assumed necessary now.

## Consequences
- `test_results.started_at` and `test_results.git_sha` must be set from the
  parent `TestRun` at insert time — the repository/storage layer is
  responsible for this, not left to chance. A future migration adding a
  new required run-level field should ask the same denormalize-or-join
  question explicitly rather than defaulting either way out of habit.
- `test_runs` remains the single source of truth for these fields; the
  copies on `test_results` are write-once and never independently updated.
  If a run's `started_at` or `git_sha` needed correcting after the fact,
  that correction would need to cascade to every associated result row —
  not a case this project expects to hit, but worth stating so it isn't
  silently wrong later.
