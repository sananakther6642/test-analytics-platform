# ADR 0001: Record architecture decisions

## Status
Accepted

## Context
This project makes a large number of infrastructure and design decisions
(Terraform vs. manual, Postgres vs. SQLite, Container Apps vs. AKS-first,
Helm vs. Kustomize, Argo CD vs. Flux, and so on). Without a written record,
the reasoning behind each choice — and the alternatives that were rejected
and why — is lost the moment the decision is made. That reasoning is also
exactly what a technical interview probes for, so losing it is a direct
cost to the project's purpose as a CV artifact.

## Decision
We will keep a log of Architecture Decision Records (ADRs) in
`docs/decisions/`, one file per decision, numbered sequentially
(`0001-`, `0002-`, ...). Each ADR follows this shape:

- **Status** — Proposed / Accepted / Superseded by ADR-000N
- **Context** — the problem, constraints, and forces at play
- **Decision** — what was actually chosen
- **Alternatives considered** — what else was on the table and why it lost
- **Consequences** — what this makes easier, harder, or forecloses

ADRs are written at the time a decision is made, not reconstructed later.
An ADR is never deleted; a changed decision gets a new ADR that supersedes
the old one, so the history of *why things changed* is preserved.

## Alternatives considered
- **No formal record, just commit messages** — commit messages explain
  *what* changed, rarely *why*, and never *what was rejected*. Insufficient
  for the reasoning this project needs to preserve.
- **A single running `DECISIONS.md`** — simpler, but loses per-decision
  status tracking and makes superseding a decision awkward to represent.

## Consequences
- Every phase of the build plan that includes a real decision point ends
  with an ADR, not just an implementation.
- The ADR log becomes a defensible, checkable artifact for interviews:
  "why did you choose X over Y" has a written, dated answer.
