# Architecture

> Status: Phase 3 live. The Azure deployment below is running and
> verified end-to-end — it will be replaced by Terraform-managed
> infrastructure in Phase 4, then AKS/Helm/observability/GitOps in later
> phases.

## Local (Phases 1-2)

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  web (nginx) │─────▶│  api (FastAPI) │────▶│  postgres     │
│  :8080       │ /api │  :8000         │      │  :5432        │
└─────────────┘      └─────────────┘      └──────────────┘
```

Docker Compose, all three services on one bridge network. See
`docker-compose.yml`.

## Azure — Phase 3 (manual/portal-driven, live)

```
                              Internet
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  ca-tad-web (external)   │
                    │  nginx :8080             │
                    └────────────┬─────────────┘
                                 │ HTTPS, internal ingress
                                 ▼
                    ┌─────────────────────────┐
                    │  ca-tad-api (internal)   │
                    │  FastAPI/uvicorn :8000   │
                    └──┬───────────┬───────────┘
                       │           │
            TLS, VNet  │           │  AcrPull (managed identity)
                       ▼           ▼
        ┌───────────────────┐   ┌──────────────────┐
        │ pg-tad4471          │   │ tadacr4471         │
        │ Postgres Flexible   │   │ Container Registry │
        │ Server (private,    │   │ (Standard, no admin │
        │ VNet-integrated)    │   │  user)              │
        └───────────────────┘   └──────────────────┘

   Both apps run in cae-tad-vnet (Container Apps environment,
   WorkloadProfiles mode, VNet-integrated into rg-tad-manual-vnet)
   and share one user-assigned managed identity, id-tad-app:
     - AcrPull                        → tadacr4471
     - Storage Blob Data Contributor  → sttad4471 (not yet wired into
                                         the app; Blob upload path is a
                                         later Phase 3 task)
     - Key Vault Secrets User         → kv-tad4471 (fetches
                                         tad-database-url at startup)

   rg-tad-manual-vnet (10.0.0.0/24 + 10.1.0.0/23):
     - subnet "default"       (10.0.0.0/24)  → delegated to Postgres
     - subnet "containerapps" (10.1.0.0/23)  → delegated to Container Apps
```

**Why this shape, briefly** (see ADR 0008 for the full story): Postgres
is private-access only, so Container Apps had to be VNet-integrated into
the same VNet to reach it at all — this wasn't the original one-subnet
plan, and cost a full session to get right (Express-mode environments,
a `/23` subnet size requirement, a one-environment-per-region quota, a
URL-unsafe password, and a Docker image missing its own migrations).

**Not yet wired up:** Blob upload path (raw TRF files → `sttad4471`) and
Key Vault's original `postgres-admin-password` secret (superseded by
`tad-database-url`, which holds the full connection string the app
actually reads).
