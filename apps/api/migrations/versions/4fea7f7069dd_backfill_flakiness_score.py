"""backfill flakiness score

Revision ID: 4fea7f7069dd
Revises: d03862a437ec
Create Date: 2026-09-27 17:14:43.501237

A deliberately non-trivial migration: not just adding a column (that
already exists, nullable, from the initial schema — see the model
docstring in db/models.py), but backfilling real values computed from
existing data.

Mirrors the same two-signal algorithm in analytics/flakiness.py
(same-commit disagreement, weighted 0.7; flip-rate, weighted 0.3) as raw
SQL rather than calling the Python module from the migration. This is a
deliberate trade-off, not an oversight: a data migration should not depend
on application code that could change shape independently of the schema,
and this backfill only ever needs to run once against whatever data exists
at migration time — it does not need to track future changes to the
scoring algorithm. See ADR 0006 for the full reasoning, including the real
risk this accepts: the SQL below and analytics/flakiness.py's Python logic
must be kept in sync by hand if the algorithm's weights or definition ever
change. A future change to the algorithm's weights does not need to be
reflected here; this migration is not re-run automatically when the
Python logic changes, so any such change should be evaluated for whether
it needs a new backfill migration.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4fea7f7069dd"
down_revision: Union[str, Sequence[str], None] = "d03862a437ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SAME_COMMIT_WEIGHT = 0.7
_FLIP_RATE_WEIGHT = 0.3

_UPGRADE_SQL = f"""
WITH
same_commit AS (
    -- Fraction of distinct git_shas where a test showed more than one
    -- outcome. Mirrors _same_commit_disagreement_rate() in
    -- analytics/flakiness.py exactly.
    SELECT
        test_id,
        COUNT(*) FILTER (WHERE outcome_count > 1)::float
            / NULLIF(COUNT(*), 0) AS same_commit_rate
    FROM (
        SELECT test_id, git_sha, COUNT(DISTINCT status) AS outcome_count
        FROM test_results
        GROUP BY test_id, git_sha
    ) per_commit
    GROUP BY test_id
),
ordered AS (
    -- Consecutive-run status, ordered by started_at per test. Mirrors
    -- _flip_rate()'s "sort by started_at, compare each pair" logic.
    SELECT
        test_id,
        status,
        LAG(status) OVER (PARTITION BY test_id ORDER BY started_at) AS prev_status,
        ROW_NUMBER() OVER (PARTITION BY test_id ORDER BY started_at) AS rn,
        COUNT(*) OVER (PARTITION BY test_id) AS total_runs
    FROM test_results
),
flip_rate AS (
    SELECT
        test_id,
        COUNT(*) FILTER (WHERE prev_status IS NOT NULL AND status != prev_status)::float
            / NULLIF(MAX(total_runs) - 1, 0) AS rate
    FROM ordered
    GROUP BY test_id
)
UPDATE test_identity
SET flakiness_score = ROUND(
    (
        {_SAME_COMMIT_WEIGHT} * COALESCE(same_commit.same_commit_rate, 0)
        + {_FLIP_RATE_WEIGHT} * COALESCE(flip_rate.rate, 0)
    )::numeric,
    4
)
FROM (SELECT test_id FROM test_identity) AS ti
LEFT JOIN same_commit ON same_commit.test_id = ti.test_id
LEFT JOIN flip_rate ON flip_rate.test_id = ti.test_id
WHERE test_identity.test_id = ti.test_id;
"""

_DOWNGRADE_SQL = "UPDATE test_identity SET flakiness_score = NULL;"


def upgrade() -> None:
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    op.execute(_DOWNGRADE_SQL)
