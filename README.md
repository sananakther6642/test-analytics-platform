# Test Analytics Platform (TAP)

> Status: **in progress** — Phase 0 (foundations) underway. This README is a
> skeleton that grows with the project; see `docs/decisions/` for the reasoning
> behind each major choice and `PLAN.md` for the original scoping notes.

A cloud-native test-analytics service: upload a synthetic test-report file, it
gets parsed, stored, and shown on a dashboard with pass/fail charts, trend
analysis, and flaky-test detection.

All data is synthetic and invented for this project. This is not a copy of
any employer's system or format.

## Why this exists

Built to close real skill gaps against 2026 DevOps/SRE hiring demand
(Kubernetes, Terraform, CI/CD, observability, GitOps), with a deliberate
learning structure: every phase documents the decision points, the
alternatives considered, and why the choice was made — see `docs/decisions/`.

## Stack

- **Backend**: Python / FastAPI
- **Frontend**: plain HTML/JS + Chart.js (kept intentionally simple)
- **Database**: PostgreSQL (local: containerized; cloud: Azure Database for
  PostgreSQL Flexible Server)
- **Object storage**: Azure Blob Storage
- **Infrastructure**: Terraform (Azure)
- **Orchestration**: Kubernetes (AKS), packaged with Helm
- **Delivery**: GitHub Actions (OIDC) → Argo CD (GitOps)
- **Observability**: Prometheus / Grafana, SLO-based alerting
- **Testing**: pytest, Playwright

## Status / roadmap

See `docs/decisions/` for ADRs and the phase plan for the full build order:
local app → manual Azure deploy → Terraform → CI/CD → AKS → Helm →
observability → GitOps → E2E → hardening.

## Local development

```bash
make setup   # install toolchain (mise) + pre-commit + Python deps
make up      # docker compose up --build
make seed    # generate the synthetic test-report corpus
make test    # unit + integration tests
```

## Cost / FinOps

This project tracks its own Azure spend as a first-class concern —
see `docs/cost-analysis.md` (added once cloud phases begin) and:

```bash
make cost            # month-to-date spend by resource group
make cost-phase      # month-to-date spend by build phase (tag)
make quota           # vCPU quota usage in westeurope
make whats-running   # every tracked resource, flagging live compute
```
