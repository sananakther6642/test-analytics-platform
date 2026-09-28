# ADR 0010: Terraform state backend — Azure Blob, bootstrapped by hand

## Status
Accepted

## Context
Terraform needs somewhere to store its state file — the record mapping
HCL resources to real Azure object IDs. This creates a genuine
bootstrap problem: state storage can't be created *by* the Terraform it
will eventually back, because Terraform needs it to exist before it can
run at all.

## Decision
A dedicated resource group (`rg-tad-tfstate`), a storage account with
**shared-key access disabled** (`allow_shared_key_access = false`), a
`tfstate` Blob container, **blob versioning** enabled, and a
**`CanNotDelete` lock** on the storage account. Created once by a plain
shell script (`infra/terraform/bootstrap/bootstrap-tfstate.sh`), not
Terraform, run by hand and never as part of CI.

Terraform authenticates to this backend via Azure AD
(`use_azuread_auth = true` in the `backend "azurerm"` block), the same
identity running `terraform apply` (a user via `az login`, or later a
service principal in CI) — never a storage account key.

## Alternatives considered
- **Local state file.** Rejected outright: no locking (concurrent
  applies could corrupt it), no encryption at rest, lost with the
  laptop, and unusable from CI once that exists in Phase 5.
- **Terraform Cloud / HCP Terraform.** A real, common choice with a
  nicer UI and built-in state locking, but it introduces a third-party
  vendor and teaches less about the actual mechanism (Blob's native
  lease-based locking, Azure AD auth to a backend) than self-managing
  the backend does. Worth knowing exists; not chosen here deliberately
  because this project's goal is depth on Azure primitives.
- **Storage account key for backend auth.** The default, simplest path
  — but every other identity decision in this project (D3.3, and every
  module built in Phase 4) uses managed identity or Azure AD RBAC
  instead of shared keys. Using a key here specifically for the one
  thing that holds every other secret in plaintext would be the single
  weakest link in an otherwise consistent design.

## Consequences
- **State-recovery story**: blob versioning means a bad `apply` that
  corrupts state can be rolled back to a previous version of the state
  blob — a genuine answer to "what's your state-recovery plan," not a
  theoretical one.
- **The `CanNotDelete` lock** is the actual protection against the
  single most catastrophic mistake possible in this whole project: an
  accidental `terraform destroy` or portal delete of the state storage
  account itself, which would make Terraform "forget" it owns anything
  it has created and try to recreate the entire environment from
  scratch on the next `apply`.
- **Discovered mid-Phase-4**: being subscription Owner does **not**
  grant Blob data-plane access under this Azure AD-only auth model — the
  same RBAC-is-separate-from-management-plane lesson learned repeatedly
  throughout this project (Key Vault in Phase 3, this backend in Phase
  4). The user's own account needed an explicit **Storage Blob Data
  Contributor** role assignment on the state storage account before
  `terraform init` would even succeed.
- **Bootstrap is a real, deliberate exception** to "everything is
  Terraform" in this project — documented in the script itself, not
  hidden. It is idempotent and safe to re-run, but is never invoked by
  CI or by any Terraform configuration.
