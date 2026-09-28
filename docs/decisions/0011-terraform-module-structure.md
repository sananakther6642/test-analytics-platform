# ADR 0011: Terraform module structure — one root module, small child modules per concern

## Status
Accepted

## Context
Phase 4 codifies eight distinct pieces of infrastructure (naming/tags,
network, container registry, Postgres, managed identity, storage, Key
Vault, Container Apps). A flat `main.tf` with all of it inline would be
unreadable and impossible to reason about past the first few resources.

## Decision
One root module (`infra/terraform/envs/dev/`) composing eight small
child modules (`infra/terraform/modules/{naming,network,registry,data,
identity,storage,key_vault,containerapp}/`), each wrapping **one
logical concern**, not one Azure resource type. For example, `identity`
creates the managed identity *and* all three of its role assignments
together, since they are never meaningful apart; `data` creates
Postgres, its database, and its private DNS zone + VNet link together,
since a private-access Postgres server without its DNS zone doesn't
actually work.

A `naming` module computes every resource name and the shared tag set
from a handful of inputs (`project`, `environment`, `phase`, `suffix`),
so no other module hardcodes a name or risks forgetting a tag.

## A real wrinkle: two naming-module instances, not one

Two Azure resource types in this project have **globally unique names**
(Postgres server names, storage account names) that collided with the
still-live manual Phase 3 deployment during the transition
(`pg-tad4471`, `sttad4471` already existed). Rather than complicate the
`naming` module itself with an exception, the root module simply
instantiates it twice — `module.naming` for the shared suffix, and a
second `module.naming_postgres` with a different suffix, reused by both
Postgres and storage since they share the same collision class. This is
a deliberately narrow, visible workaround rather than a generalized
"sometimes has a different suffix" parameter threaded through the
`naming` module's own interface.

## Alternatives considered
- **Terragrunt** for DRY-er multi-environment wiring. Rejected as
  overkill for a single `dev` environment — worth knowing it exists
  (mentioned here for the record), not needed at this project's current
  scale. Revisit if/when a real `prod` environment is added.
- **Terraform workspaces** instead of separate root modules per
  environment. Rejected per the plan's own D4.2: workspaces share one
  backend key and one configuration, and teams have been burned by a
  `dev` mistake mechanically reaching `prod` through a workspace switch.
  A separate `envs/dev/` (and later `envs/prod/`) root module with its
  own backend key keeps that impossible by construction.
- **One module per Azure resource type** (e.g. separate `postgres` and
  `postgres_dns` modules). Rejected: it would force the root module to
  wire together resources that are never independently useful, adding
  indirection without adding real flexibility.

## Consequences: the ACR import design, revised mid-phase

The original design imported the real `tadacr4471` from `rg-tad-manual`
into the `registry` module via a Terraform `import` block, specifically
to preserve its real container images rather than re-push them — see
the module's own git history. That design required a `data
"azurerm_resource_group" "manual"` block referencing a resource group
Terraform didn't manage, and correctly avoided moving the ACR into
`rg-tad-dev` (the provider has no in-place resource-group move for
`azurerm_container_registry`; changing it forces a destroy+recreate,
which would have deleted the very images the import was meant to
save).

That resource group was later **accidentally deleted in full** — not
just the individual resources meant for teardown — while retiring the
now-redundant manual deployment, taking the imported ACR and its images
with it. Since the images could not be recovered either way, the
module structure was simplified rather than restored: the `registry`
module now creates the ACR **natively** in `rg-tad-dev`, with no
cross-resource-group data source and no `import` block anywhere in this
configuration. The final structure is genuinely simpler than the
original design — every resource this project owns now lives in one
resource group, managed by one Terraform state, with no external
references at all.

## The honest limit this structure doesn't yet solve

The timed `terraform destroy && terraform apply` test (see PR history)
surfaced a real gap this module structure does not paper over: `destroy`
removes the ACR along with everything else, so a rebuilt environment has
an **empty registry** until container images are rebuilt and pushed by
hand. This project's `apply` is not yet a true zero-manual-steps
rebuild. Fixing that properly means CI building and pushing images as
part of the pipeline — Phase 5's actual scope — not a workaround bolted
onto the `registry` module here.
