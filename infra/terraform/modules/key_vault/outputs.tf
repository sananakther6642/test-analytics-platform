output "id" {
  value = azurerm_key_vault.this.id
}

output "uri" {
  value = azurerm_key_vault.this.vault_uri
}

output "database_url_secret_id" {
  description = "The versionless secret URI Container Apps' keyvaultref needs."
  value       = azurerm_key_vault_secret.database_url.versionless_id
}
