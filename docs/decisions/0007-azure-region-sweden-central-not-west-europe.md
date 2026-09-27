# ADR 0007: Deploy to Sweden Central, not West Europe

## Status
Accepted

## Context
The plan (and ADR 0002's quota research) assumed `westeurope` throughout,
on the reasoning that it's geographically sensible for a German job hunt
and had confirmed vCPU quota for the relevant SKU families.

Creating the first real resource in Phase 3 — an Azure Container Registry
in `westeurope` — failed at validation with:

> Resource 'tadacr4471' was disallowed by Azure: This policy maintains a
> set of best available regions where your subscription can deploy
> resources... The selected region is currently not accepting new
> customers.

Retrying in `northeurope` produced the identical error. This is a
**subscription-level "new customer" regional restriction**, distinct from
vCPU quota (which the CSV export in this session's research confirmed is
allocated and available in West Europe — `Standard BS Family vCPUs: 0 of
4`, `Standard Basv2 Family vCPUs: 0 of 10`, etc.). Quota being allocated
does not mean the region will accept a first deployment on this
subscription; that's gated by a separate, opaque "best available regions"
policy Microsoft applies to some subscriptions (Azure for Students
subscriptions appear to be affected, based on this being the very first
resource ever created on this subscription).

Retrying with `swedencentral` passed validation immediately and the ACR
deployed successfully.

## Decision
Deploy all Phase 3+ resources to **Sweden Central**, not West Europe or
North Europe.

## Alternatives considered
- **Keep trying West/North Europe via a support ticket or waiting period**
  — the error message references contacting support for additional
  regions. Rejected for this project: adds delay with no guaranteed
  outcome, for a benefit (marginally closer geography to Germany) that
  doesn't materially affect anything measured in this project — latency to
  a portfolio demo audience is not a real constraint here.
- **Try a different Students-friendly region blind** (e.g. France Central,
  Germany West Central) before confirming Sweden Central works — rejected
  in favor of testing the specific candidate already identified as a
  reasonable EU alternative (GDPR-compliant, modern region), rather than
  trial-and-erroring through the full candidate list.

## Consequences
- Every resource from this point forward — Postgres Flexible Server,
  Storage account, Key Vault, Container Apps environment, and eventually
  the AKS cluster in Phase 6 — must be created in Sweden Central for
  consistency (same-region resources avoid cross-region latency and
  egress charges) and because they may hit the identical new-customer
  restriction in West/North Europe.
- **ADR 0002's SKU/quota findings need re-verification for Sweden
  Central** before Phase 6. That ADR's research (B2ats_v2 demand-restricted,
  B2pts_v2 unavailable, B2s_v2 available with clean 10-vCPU quota) was
  specific to West Europe and cannot be assumed to hold in a different
  region without checking.
- Resource groups themselves are not region-restricted the same way —
  `rg-tad-manual` (created against West Europe as its own metadata region)
  can still contain Sweden Central resources without issue. Only each
  individual resource's own location setting is what's gated by this
  policy.
