# Matches the manual deployment's real settings (verified via
# `az storage account show`): shared-key access disabled and Entra
# authorization as the portal default, both directly implementing
# D3.3's zero-secrets design — the app authenticates via managed
# identity + RBAC, never an account key.
resource "azurerm_storage_account" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  account_tier             = "Standard"
  account_replication_type = "LRS" # not GRS — not covered by the free
  # grant and costs more, per the manual deployment's own correction
  # (ADR-adjacent lesson from Phase 3).
  account_kind = "StorageV2"

  access_tier                   = "Hot"
  min_tls_version               = "TLS1_2"
  shared_access_key_enabled     = false
  public_network_access_enabled = true # RBAC, not network isolation,
  # is this project's access-control model for Blob — see Phase 3's
  # architecture notes on why Postgres and Blob deliberately differ here.
  default_to_oauth_authentication = true

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }
}

# trivy flags AZU-0012 (network default-deny), AZU-0057 (no logging),
# AZU-0058 (not geo-redundant), AZU-0060 (no customer-managed keys),
# AZU-0061 (no infrastructure/double encryption) — all real findings,
# none fixed here, each for a specific reason:
#
# - AZU-0012 (network default-deny): same problem as Key Vault's
#   AZU-0013 — the app and Terraform both need to reach Blob over the
#   public internet (Container Apps isn't VNet-integrated for Blob
#   egress), so a default-deny ACL has no allowlisted IP to add. RBAC is
#   this project's actual access-control layer, per D3.3.
# - AZU-0058 (GRS): explicitly rejected in Phase 3 — not covered by the
#   free grant, costs more, for a dev environment with disposable data.
# - AZU-0060/AZU-0061 (CMK, infrastructure encryption): enterprise-grade
#   controls (customer-managed keys need a Key Vault + rotation policy
#   to actually pay off) with no real threat model here — Microsoft-
#   managed keys are the correct default at this project's scale.
# - AZU-0057 (Storage Analytics logging): genuinely worth having, but
#   needs a Log Analytics workspace as a destination
#   (azurerm_monitor_diagnostic_setting), which is Phase 8's
#   observability work, not Phase 4's. Deferred deliberately, not
#   silently skipped.
#
# All four documented in .trivyignore with this same reasoning.

resource "azurerm_storage_container" "reports" {
  name                  = var.container_name
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}
