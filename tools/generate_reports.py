#!/usr/bin/env python3
"""Generates a synthetic TRF v1 corpus for local development and demos.

Deterministic (seeded RNG) so the corpus — and therefore the flaky-test
list, trend charts, and pass rates it produces — is reproducible.

Produces one JSON file per run under --out-dir, spanning --days simulated
days with one run per day, containing:
  - A stable baseline of tests that always pass.
  - Two tests that genuinely regress at a known commit and are later fixed
    (NOT flaky — a real regression-then-fix, used to verify the flakiness
    algorithm correctly does NOT flag these).
  - Five tests with a configurable flip probability per run (genuinely
    flaky — same code, unstable outcome).
  - One test with duration slowly increasing over time (a performance
    regression, unrelated to pass/fail flakiness).

All data and identifiers are invented for this project.
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

STABLE_TESTS = [f"test_stable_{i}" for i in range(10)]
REGRESSION_TESTS = ["test_regression_a", "test_regression_b"]
FLAKY_TESTS = [f"test_flaky_{i}" for i in range(5)]
SLOW_DRIFT_TEST = "test_slow_drift"


def build_run(
    day_index: int, run_date: datetime, rng: random.Random, git_sha: str | None = None
) -> dict:
    git_sha = git_sha or f"{rng.getrandbits(32):08x}"
    tests = []

    for name in STABLE_TESTS:
        tests.append(_test(name, "passed", rng.uniform(20, 80)))

    # Real regression: fails from day 30 to day 45, then fixed. Same commit
    # per day, so *within* a day these are consistent (not flaky) — the
    # generator gives every test in a run the same git_sha, matching how a
    # real CI run works.
    regressed = 30 <= day_index < 45
    for name in REGRESSION_TESTS:
        status = "failed" if regressed else "passed"
        msg = "AssertionError: expected 200, got 500" if regressed else None
        tests.append(_test(name, status, rng.uniform(30, 90), failure_message=msg))

    for name in FLAKY_TESTS:
        flip_probability = 0.3
        status = "failed" if rng.random() < flip_probability else "passed"
        msg = "intermittent timeout" if status == "failed" else None
        tests.append(_test(name, status, rng.uniform(10, 200), failure_message=msg))

    # Slow drift: duration creeps up ~1ms/day, independent of pass/fail.
    tests.append(_test(SLOW_DRIFT_TEST, "passed", 50 + day_index * 1.2))

    return {
        "run_id": str(uuid.uuid4()),
        "suite_name": "tad-synthetic-suite",
        "git_sha": git_sha,
        "branch": "main",
        "started_at": run_date.isoformat(),
        "finished_at": (run_date + timedelta(minutes=5)).isoformat(),
        "environment": "ci",
        "tests": tests,
    }


def _test(
    name: str, status: str, duration_ms: float, failure_message: str | None = None
) -> dict:
    return {
        "test_id": name,
        "name": name,
        "file": f"{name}.py",
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "retries": 0,
        "failure_message": failure_message,
        "tags": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=Path, default=Path("data/synthetic-reports"))
    args = parser.parse_args()

    rng = random.Random(args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    start = datetime.now(timezone.utc) - timedelta(days=args.days)
    run_count = 0
    for day_index in range(args.days):
        run_date = start + timedelta(days=day_index)
        git_sha = f"{rng.getrandbits(32):08x}"

        run = build_run(day_index, run_date, rng, git_sha=git_sha)
        _write_run(args.out_dir, day_index, run_count, run)
        run_count += 1

        # ~15% of days get a same-commit re-run (e.g. a CI retry, or a
        # second environment testing the same SHA). This is what lets the
        # flakiness algorithm's strongest signal — same-commit disagreement
        # — actually have an opportunity to fire; without repeat runs
        # against one commit, only the weaker flip-rate signal is ever
        # exercised.
        if rng.random() < 0.15:
            rerun = build_run(
                day_index, run_date + timedelta(hours=2), rng, git_sha=git_sha
            )
            _write_run(args.out_dir, day_index, run_count, rerun, suffix="-rerun")
            run_count += 1

    print(
        f"Generated {run_count} runs across {args.days} days into {args.out_dir}/ (seed={args.seed})"
    )


def _write_run(
    out_dir: Path, day_index: int, run_count: int, run: dict, suffix: str = ""
) -> None:
    out_path = (
        out_dir
        / f"run-{day_index:03d}-{run_count:03d}{suffix}-{run['run_id'][:8]}.json"
    )
    out_path.write_text(json.dumps(run, indent=2))


if __name__ == "__main__":
    main()
