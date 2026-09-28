# Matches the real tadacr4471 exactly (verified via `az acr show`) so
# importing it produces a zero-diff plan — that zero diff is the actual
# proof the import worked, not just that it ran without erroring.
resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = var.tags
}
