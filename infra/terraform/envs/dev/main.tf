locals {
  tags = module.naming.tags
}

module "naming" {
  source = "../../modules/naming"

  project     = "tad"
  environment = "dev"
  phase       = "P4"
  suffix      = var.resource_suffix
}

resource "azurerm_resource_group" "main" {
  name     = module.naming.resource_group
  location = var.location
  tags     = local.tags
}

module "network" {
  source = "../../modules/network"

  name                = module.naming.vnet
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
}
