output "fqdn" {
  value = azurerm_postgresql_flexible_server.this.fqdn
}

output "database_name" {
  value = azurerm_postgresql_flexible_server_database.tad.name
}

output "admin_login" {
  value = azurerm_postgresql_flexible_server.this.administrator_login
}

output "admin_password" {
  value     = random_password.postgres_admin.result
  sensitive = true
}

output "connection_string" {
  description = "The full TAD_DATABASE_URL value, ssl=require per ADR 0008's finding that Flexible Server requires it."
  value       = "postgresql+asyncpg://${azurerm_postgresql_flexible_server.this.administrator_login}:${random_password.postgres_admin.result}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/${azurerm_postgresql_flexible_server_database.tad.name}?ssl=require"
  sensitive   = true
}
