# ADR 0002: AKS node pool VM size — Standard_B2s_v2, not B2ats_v2

## Status
Accepted

## Context
The original build plan flagged `Standard_B2ats_v2` (ARM/Ampere, Basv2 family)
as the preferred AKS node VM size, because the Azure for Students portal
lists "B2ats_v2 / B2pts_v2, 750 free hours/month" among its free-service
grants. The plan explicitly noted two things needed empirical verification
before relying on this: whether the free-hours grant applies to AKS-managed
node VMs at all, and whether the SKU is actually obtainable in `westeurope`
on a student subscription.

We checked SKU/quota availability in the Azure Portal (Usage + quotas,
Compute provider, West Europe region) before creating anything, per the
project's Azure-via-portal-UI convention.

## What we found
Querying quota families in West Europe for the Azure for Students
subscription:

| SKU | Quota family | Availability in West Europe |
|---|---|---|
| `Standard_B2s_v2`, `Standard_B2ts_v2`, `Standard_B2ls_v2` | `standardBsv2Family` | Available — 0 of 10 vCPUs, adjustable |
| `Standard_B2ats_v2` (ARM) | `standardBasv2Family` | High demand — flagged "troubleshoot," not freely grantable |
| `Standard_B2pts_v2` (ARM) | `standardBpsv2Family` | **Unavailable in this region** |
| `Standard_B2s` (legacy v1, non-"v2" Bs family) | `standardBSFamily` | Available — 0 of 4 vCPUs, **not adjustable** (hard cap) |

Confirmed the exact SKU-to-family mapping via `az vm list-skus` (read-only):

```
Standard_B2ls_v2  standardBsv2Family
Standard_B2s_v2   standardBsv2Family
Standard_B2ts_v2  standardBsv2Family
```

Both ARM-based options the plan considered are effectively closed off in
this region: `B2pts_v2` is flatly unavailable, and `B2ats_v2` is
demand-restricted and would require a manual access request with no
guarantee of approval on a timeline this project can plan around.

## Decision
Use **`Standard_B2s_v2`** (x86/AMD64, `standardBsv2Family`) as the AKS
system node pool VM size, not `Standard_B2ats_v2`.

This also means the "multi-arch container images" stretch goal from the
original plan (justified as a trade-off for using an ARM node) is dropped —
there's no ARM node to target, so it would add complexity with no payoff.

The free-hours *billing* question (does the Students grant's "B2ats_v2 /
B2pts_v2, 750 hrs" line extend to this sibling SKU in the same generation)
is still open and requires the empirical cost spike described in the plan:
create a real node, leave it running a few hours, check Cost Analysis
grouped by meter.

## Alternatives considered
- **`Standard_B2ats_v2` as originally planned** — rejected: demand-restricted
  in West Europe, request outcome and timeline uncertain, not something to
  depend on for a project with no hard deadline pressure but real momentum
  value in not stalling on an access request.
- **`Standard_B2s` (legacy, non-v2 Bs family)** — available, but capped at a
  hard, non-adjustable 4 vCPU limit — enough for exactly one 2-vCPU node
  with zero headroom for the plan's multi-node exercises (Phase 6's
  deliberate 2-node scaling test, spot pool addition). Rejected in favor of
  the v2 family's 10 vCPU adjustable quota.
- **Request a quota increase for Basv2** — possible, but adds an
  unpredictable wait with no guaranteed approval, for a SKU whose only
  advantage over B2s_v2 was an assumed (unverified) cost benefit.

## Consequences
- AKS module in Terraform (Phase 4/6) will pin `Standard_B2s_v2`, not
  `Standard_B2ats_v2`. Update the plan's Phase 6 decision table accordingly.
- No multi-arch image build step needed; standard `linux/amd64` builds
  throughout.
- The cost-verification spike must specifically test `Standard_B2s_v2`
  against Cost Analysis, since the free-grant wording on the portal names
  a sibling SKU (`B2ats_v2`) and applying it to `B2s_v2` by assumption would
  repeat the exact mistake this ADR was written to avoid.
