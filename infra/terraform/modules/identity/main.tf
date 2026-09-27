# User-assigned, not system-assigned — the identity must survive
# recreating the compute resources that use it (Container Apps in
# particular gets destroyed/recreated across this project's phases), a
# system-assigned identity dies with its resource and every role
# assignment would need redoing. Same reasoning as the manual deployment
# (D3.3) and confirmed the hard way in ADR 0008 (Container Apps
# environment had to be recreated once — the identity survived that
# unchanged).
resource "azurerm_user_assigned_identity" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}
