# The environment supports VNet integration and user-assigned identity
# unconditionally through this resource — there is no "Express mode"
# concept in the azurerm provider's schema at all (confirmed by reading
# the actual provider schema before writing this, not assumed from the
# CLI's --environment-mode flag naming). Setting infrastructure_subnet_id
# is what the CLI's --environment-mode WorkloadProfiles flag maps to;
# the portal's simplified wizard and the CLI's bare default both created
# something more restrictive that this resource just doesn't have as an
# option. See ADR 0008 for the full saga this sidesteps entirely.
resource "azurerm_container_app_environment" "this" {
  name                     = "cae-${var.name_prefix}"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  tags                     = var.tags
  infrastructure_subnet_id = var.infrastructure_subnet_id

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }
}

resource "azurerm_container_app" "api" {
  name                         = "ca-${var.name_prefix}-api"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = var.acr_login_server
    identity = var.identity_id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = var.database_url_secret_id
    identity            = var.identity_id
  }

  ingress {
    external_enabled = false # internal only — the web app is the only
    # public entry point, matching Phase 3's split.
    target_port = 8000
    transport   = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "ca-tad-api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "TAD_DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "TAD_BLOB_ACCOUNT_URL"
        value = var.blob_account_url
      }
      env {
        name  = "TAD_MANAGED_IDENTITY_CLIENT_ID"
        value = var.identity_client_id
      }
    }
  }
}

resource "azurerm_container_app" "web" {
  name                         = "ca-${var.name_prefix}-web"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.this.id
  revision_mode                = "Single"
  tags                         = var.tags
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = var.acr_login_server
    identity = var.identity_id
  }

  ingress {
    external_enabled = true # the only public entry point.
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 3

    container {
      name   = "ca-tad-web"
      image  = var.web_image
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "API_UPSTREAM_HOST"
        value = azurerm_container_app.api.ingress[0].fqdn
      }
      env {
        name  = "API_UPSTREAM_SCHEME"
        value = "https" # Container Apps' internal ingress terminates
        # TLS even for internal traffic (allowInsecure/insecure not set
        # here), per Phase 3's own hard-won finding.
      }
    }
  }
}
