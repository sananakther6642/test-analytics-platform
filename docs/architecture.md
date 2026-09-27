# Architecture

> Status: Phase 3 in progress. This diagram reflects the manual Azure
> deployment being built now — it will be updated as later phases add
> Terraform, AKS, Helm, observability, and GitOps.

## Local (Phases 1-2)

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  web (nginx) │─────▶│  api (FastAPI) │────▶│  postgres     │
│  :8080       │ /api │  :8000         │      │  :5432        │
└─────────────┘      └─────────────┘      └──────────────┘
```

Docker Compose, all three services on one bridge network. See
`docker-compose.yml`.

## Azure — Phase 3 (this phase, manual/portal-driven)

Diagram to be added once the deployment is live — see the Phase 3 PR
checklist for the resources being created (resource group, ACR, Postgres
Flexible Server, Blob Storage, Key Vault, managed identity, Container
Apps).
