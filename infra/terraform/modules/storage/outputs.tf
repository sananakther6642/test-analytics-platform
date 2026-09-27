output "id" {
  value = azurerm_storage_account.this.id
}

output "account_url" {
  description = "The value TAD_BLOB_ACCOUNT_URL needs."
  value       = azurerm_storage_account.this.primary_blob_endpoint
}

output "container_name" {
  value = azurerm_storage_container.reports.name
}
