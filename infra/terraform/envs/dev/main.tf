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

# Separate suffix for Postgres only — see var.postgres_suffix for why
# (the manual pg-tad4471 still exists and collides on server name,
# which is globally unique across all of Azure).
module "naming_postgres" {
  source = "../../modules/naming"

  project     = "tad"
  environment = "dev"
  phase       = "P4"
  suffix      = var.postgres_suffix
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

  name                = module.naming_postgres.postgres
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
  vnet_id             = module.network.vnet_id
  delegated_subnet_id = module.network.postgres_subnet_id
}

# sttad4471 (manual) still exists — storage account names are globally
# unique, same collision class as Postgres, so this reuses
# naming_postgres's "dev4471" suffix rather than adding a third naming
# module instance for one more exception.
module "storage" {
  source = "../../modules/storage"

  name                = module.naming_postgres.storage_account
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
}

module "key_vault" {
  source = "../../modules/key_vault"

  name                = module.naming_postgres.key_vault
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
  database_url        = module.data.connection_string
}

module "identity" {
  source = "../../modules/identity"

  name                = module.naming.managed_identity
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tags                = local.tags
  acr_id              = module.registry.id
  storage_account_id  = module.storage.id
  key_vault_id        = module.key_vault.id
}

module "containerapp" {
  source = "../../modules/containerapp"

  name_prefix              = "tad"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = var.location
  tags                     = local.tags
  infrastructure_subnet_id = module.network.container_apps_subnet_id
  identity_id              = module.identity.id
  identity_client_id       = module.identity.client_id
  acr_login_server         = module.registry.login_server
  api_image                = "${module.registry.login_server}/tad-api:0.1.0"
  web_image                = "${module.registry.login_server}/tad-web:0.1.0"
  database_url_secret_id   = module.key_vault.database_url_secret_id
  blob_account_url         = module.storage.account_url
}
