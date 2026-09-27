# ADR 0009: Container Apps first, AKS later — deliberately, not as a default

## Status
Accepted

## Context
The natural instinct for a Kubernetes-focused portfolio project is to go
straight to AKS. Phase 3 deliberately doesn't: it deploys to Azure
Container Apps first, and AKS is scoped for Phase 6.

## Decision
Use Container Apps as the first real cloud compute target, and treat
getting the *application* working in Azure (networking, identity,
managed Postgres, Blob) as a separate, earlier milestone from getting a
*Kubernetes cluster* working.

## Rationale
- **Separates two different classes of failure.** Everything debugged in
  this phase — DNS resolution against a private-access Postgres server, a
  URL-unsafe password, a missing file in a Docker image, an nginx
  upstream misconfiguration, an Azure platform default (Express mode)
  that silently broke managed identity — was an *application and
  networking* problem, not a *Kubernetes* problem. Hitting all of this
  for the first time on a bare AKS cluster would make every failure
  ambiguous: is the pod crash-looping because of my code, my manifest, or
  the cluster? Container Apps removes that ambiguity for this pass.
- **Container Apps is still real infrastructure, not a toy.** It runs on
  Kubernetes internally (KEDA + Envoy under a managed control plane), so
  concepts learned here — ingress, scale-to-zero, revisions, managed
  identity federation, VNet integration — transfer directly. This isn't
  a simplified tutorial environment; ADR 0008's entire debugging arc
  (private DNS, subnet delegation, environment-mode quotas) is exactly
  the kind of real Azure networking problem a production AKS deployment
  would also require.
- **AKS is the expensive phase.** Deferring it until the application is
  already proven means AKS-phase debugging time goes toward actual
  Kubernetes concepts (Deployments, Services, probes, HPA) rather than
  re-discovering "is my connection string right" on a per-hour-billed
  cluster.

## Alternatives considered
- **Go straight to AKS.** Rejected per the above — conflates two
  learning goals and makes every failure mode ambiguous, on the single
  most expensive resource in the whole project.
- **Skip Container Apps, use App Service instead.** Rejected: App Service
  doesn't teach the container-registry-pull, managed-identity-federation,
  or VNet-integration concepts this phase specifically wanted to
  practice before AKS needs the same concepts at higher stakes.

## Consequences
- Phase 3's Container Apps deployment (`cae-tad-vnet`, `ca-tad-api`,
  `ca-tad-web`) is not meant to be thrown away — it remains the
  always-on, near-zero-cost reference deployment per the plan's runtime
  posture, even after AKS exists in Phase 6.
- AKS (Phase 6) is Terraform-only from the start, per the original plan —
  no manual-portal pass for that resource specifically, since its
  correctness surface (node pools, network plugin, identity model) is too
  large for portal-clicking to teach anything but frustration, unlike the
  comparatively small Container Apps surface this ADR covers.
