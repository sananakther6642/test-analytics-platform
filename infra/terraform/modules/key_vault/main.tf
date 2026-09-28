data "azurerm_client_config" "current" {}

# RBAC permission model, not legacy access policies — consistent with
# every other identity/access decision in this project (D3.3). Purge
# protection deliberately off: this is a teardown-heavy dev project
# (Phase 4's whole point is destroy/apply cycles), and purge protection
# would block recreating a same-named vault for 90 days after a
# destroy — a real, deliberate tradeoff already made once for the
# manual deployment, kept the same way here.
resource "azurerm_key_vault" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = false
  public_network_access_enabled = true

  # trivy (AZU-0013) wants default_action = "Deny" here. Deliberately
  # NOT doing that: Terraform itself needs to write the database_url
  # secret below, running from wherever `terraform apply` is invoked
  # (a laptop, not an Azure service) — a default-deny ACL would block
  # that write with no allowlisted IP to add, since this project has no
  # fixed egress IP. RBAC (rbac_authorization_enabled above) is this
  # project's actual access-control layer for who can read/write
  # secrets, consistent with every other identity decision here — see
  # .trivyignore.
}

# Terraform itself (running as whoever applies, via az login) needs
# Secrets Officer to write the secret below — being subscription Owner
# does NOT grant Key Vault data-plane access under RBAC, the same gap
# hit manually in Phase 3. Without this, the secret resource below fails
# with Forbidden on the very first apply.
resource "azurerm_role_assignment" "terraform_secrets_officer" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "tad-database-url"
  value        = var.database_url
  content_type = "text/plain; charset=utf-8" # a connection string, no
  # richer type applies — satisfies trivy AZU-0015, genuinely useful as
  # a hint for anyone reading this secret in the portal later.
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_role_assignment.terraform_secrets_officer]
}
