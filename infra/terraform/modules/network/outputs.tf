output "vnet_id" {
  value = azurerm_virtual_network.this.id
}

output "postgres_subnet_id" {
  value = azurerm_subnet.postgres.id
}

output "container_apps_subnet_id" {
  value = azurerm_subnet.container_apps.id
}
