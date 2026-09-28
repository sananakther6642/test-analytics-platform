output "id" {
  value = azurerm_user_assigned_identity.this.id
}

output "principal_id" {
  description = "Consumed by future modules (storage, key_vault) to add their own role assignments against this identity."
  value       = azurerm_user_assigned_identity.this.principal_id
}

output "client_id" {
  description = "The value Container Apps' TAD_MANAGED_IDENTITY_CLIENT_ID env var needs — DefaultAzureCredential requires this explicitly for a user-assigned identity (see ADR 0008's addendum)."
  value       = azurerm_user_assigned_identity.this.client_id
}
