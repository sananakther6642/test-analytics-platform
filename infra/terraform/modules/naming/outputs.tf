# Naming convention: {resource-type-prefix}-{project}[-{suffix}]
#
# Globally-unique resource types (storage accounts, ACR, Key Vault) get
# the random suffix baked in and can't use hyphens in some cases (storage
# accounts, ACR) — those outputs are built without hyphens deliberately,
# not because hyphens weren't considered.
#
# This mirrors the actual names chosen by hand in Phase 3
# (rg-tad-manual, tadacr4471, pg-tad4471, sttad4471, kv-tad4471,
# id-tad-app, cae-tad-vnet) so the imported/rebuilt resources are
# recognizable as "the same thing", not renamed for Terraform's sake.

output "resource_group" {
  value = "rg-tad-${var.environment}"
}

output "acr" {
  # ACR names: alphanumeric only, no hyphens, 5-50 chars, globally unique.
  value = "tadacr${var.suffix}"
}

output "postgres" {
  value = "pg-tad${var.suffix}"
}

output "storage_account" {
  # Storage account names: lowercase alphanumeric only, 3-24 chars,
  # globally unique.
  value = "sttad${var.suffix}"
}

output "key_vault" {
  value = "kv-tad${var.suffix}"
}

output "managed_identity" {
  value = "id-tad-app"
}

output "container_apps_environment" {
  value = "cae-tad-${var.environment}"
}

output "vnet" {
  value = "rg-tad-${var.environment}-vnet"
}

output "tags" {
  value = {
    project    = var.project
    env        = var.environment
    phase      = var.phase
    managed-by = "terraform"
  }
}
