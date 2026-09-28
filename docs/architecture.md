# Architecture

> Status: Phase 4 live. Every resource is now Terraform-managed, in one
> resource group (`rg-tad-dev`), verified end-to-end including a timed
> destroy/rebuild cycle. Phase 3's manual deployment (`rg-tad-manual`) is
> fully retired. Next: AKS/Helm/observability/GitOps in later phases.

## Local (Phases 1-2)

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  web (nginx) │─────▶│  api (FastAPI) │────▶│  postgres     │
│  :8080       │ /api │  :8000         │      │  :5432        │
└─────────────┘      └─────────────┘      └──────────────┘
```

Docker Compose, all three services on one bridge network. See
`docker-compose.yml`.

## Azure — Phase 4 (Terraform-managed, live)

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
                    └──┬─────────┬─────────────┘
                       │         │
            TLS, VNet  │         │  AcrPull / secret ref (managed identity)
                       ▼         ▼
        ┌───────────────────┐   ┌──────────────────┐
        │ pg-taddev4471      │   │ tadacr4471        │
        │ Postgres Flexible  │   │ Container Registry│
        │ Server (private,   │   │ (Standard, no      │
        │ VNet-integrated)   │   │  admin user)        │
        └───────────────────┘   └──────────────────┘
                       │
                       │  Storage Blob Data Contributor
                       ▼
        ┌───────────────────┐   ┌──────────────────┐
        │ sttaddev4471       │   │ kv-taddev4471      │
        │ Storage account    │   │ Key Vault          │
        │ (reports container)│   │ (tad-database-url) │
        └───────────────────┘   └──────────────────┘

   All resources live in one resource group, rg-tad-dev, fully
   Terraform-managed (infra/terraform/envs/dev/). Both apps run in
   cae-tad (Container Apps environment, VNet-integrated) and share one
   user-assigned managed identity, id-tad-app, with all three role
   assignments (AcrPull, Storage Blob Data Contributor, Key Vault
   Secrets User) applied by the identity module.

   rg-tad-dev-vnet (10.0.0.0/24 + 10.1.0.0/23):
     - subnet "default"       (10.0.0.0/24)  → delegated to Postgres
     - subnet "containerapps" (10.1.0.0/23)  → delegated to Container Apps
```

**8 Terraform modules** (`infra/terraform/modules/`): `naming`,
`network`, `registry`, `data` (Postgres), `identity`, `storage`,
`key_vault`, `containerapp` — see ADR 0011 for the module-structure
rationale, and ADR 0010 for the state-backend design.

**What changed from Phase 3's manual deployment**: the ACR
(`tadacr4471`) was originally imported from the manual deployment to
preserve its images, then recreated natively here after an incident
deleted the whole manual resource group by accident — see ADR 0011's
addendum. `rg-tad-manual` no longer exists; everything lives in
`rg-tad-dev`. The `azurerm_container_app_environment` Terraform resource
has no "Express mode" restriction at all (unlike the CLI/portal default
that caused ADR 0008's entire saga) — setting `infrastructure_subnet_id`
gets VNet integration and managed identity support by construction.

**A real, honest limitation**: `terraform apply` is not yet a true
zero-manual-steps rebuild. `terraform destroy` removes the container
registry along with everything else, so a rebuilt environment needs its
images rebuilt and pushed by hand before the Container Apps can start —
confirmed by a real timed destroy/rebuild test (destroy: 26m 8s; apply:
~1 minute once images existed). Closing this gap is Phase 5's job (CI
building and pushing images as part of the pipeline), not a workaround
added here.
