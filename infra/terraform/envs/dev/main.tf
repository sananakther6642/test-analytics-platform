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

# The ACR stays in rg-tad-manual, not rg-tad-dev — Azure's provider has
# no in-place resource-group move for azurerm_container_registry;
# changing resource_group_name forces a destroy+recreate, which would
# delete the real images this import exists specifically to avoid
# re-pushing. Referenced via a data source since rg-tad-manual is not
# Terraform-managed.
data "azurerm_resource_group" "manual" {
  name = "rg-tad-manual"
}

module "registry" {
  source = "../../modules/registry"

  name                = module.naming.acr
  resource_group_name = data.azurerm_resource_group.manual.name
  # var.location (Sweden Central), not the resource group's own
  # metadata location — rg-tad-manual's metadata region is West Europe
  # (see ADR 0007), but the ACR itself was deployed to Sweden Central.
  # A resource group's location and the region its resources actually
  # live in are two different things.
  location = var.location
  tags     = local.tags
}

import {
  to = module.registry.azurerm_container_registry.this
  id = "/subscriptions/9b574ede-20f2-42b0-ae69-b59312253eab/resourceGroups/rg-tad-manual/providers/Microsoft.ContainerRegistry/registries/tadacr4471"
}

module "data" {
  source = "../../modules/data"

  name                = module.naming.postgres
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
  vnet_id             = module.network.vnet_id
  delegated_subnet_id = module.network.postgres_subnet_id
}
