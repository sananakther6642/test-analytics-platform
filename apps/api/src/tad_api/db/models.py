"""SQLAlchemy models for the persistence layer (Phase 2).

Three tables, not one flat table:

- `test_identity` — a stable identity for "this test" across renames. A
  test's `test_id` from an uploaded report can be renamed in a later commit
  (e.g. a file gets restructured); without a separate identity row, a rename
  would silently reset that test's entire flakiness history, because the
  flakiness algorithm groups outcomes by test_id. This table exists purely
  so future work (not this phase) has somewhere to record "these two
  test_ids are the same test." For now it's populated 1:1 with test_ids
  seen — the identity-merging logic itself is out of scope for Phase 2.
- `test_runs` — one row per uploaded report.
- `test_results` — one row per test-within-a-run, foreign-keyed to both.

Indexes on (test_id, started_at) and (git_sha) directly support the two
queries that matter most: flakiness scoring (groups by test_id, needs
chronological order) and same-commit disagreement detection (groups by
git_sha).
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TestIdentity(Base):
    __tablename__ = "test_identity"

    test_id: Mapped[str] = mapped_column(String, primary_key=True)
    # Nullable now — populated once flakiness scoring is persisted (a later
    # phase concern, not Phase 2). Declaring the column now avoids a
    # migration-only-to-add-one-column churn later, since the table's whole
    # purpose is to eventually hold this.
    flakiness_score: Mapped[float | None] = mapped_column(nullable=True)


class TestRun(Base):
    __tablename__ = "test_runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    suite_name: Mapped[str] = mapped_column(String, nullable=False)
    git_sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    branch: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime] = mapped_column(nullable=False)
    environment: Mapped[str] = mapped_column(String, nullable=False)

    results: Mapped[list["TestResult"]] = relationship(back_populates="run")


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        Index("ix_test_results_test_id_started_at", "test_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("test_runs.run_id"), nullable=False)
    test_id: Mapped[str] = mapped_column(
        ForeignKey("test_identity.test_id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    file: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    duration_ms: Mapped[float] = mapped_column(nullable=False)
    retries: Mapped[int] = mapped_column(default=0, nullable=False)
    failure_message: Mapped[str | None] = mapped_column(nullable=True)

    # Denormalized from test_runs.started_at (and git_sha, below) so the
    # flakiness/trend queries — which run on every dashboard load — can hit
    # a single composite index on this table instead of joining to
    # test_runs every time. The source of truth is still test_runs; these
    # are write-once copies set when a result row is inserted.
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    git_sha: Mapped[str] = mapped_column(String, nullable=False, index=True)

    run: Mapped["TestRun"] = relationship(back_populates="results")
