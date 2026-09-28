terraform {
  # Pinned with an exact lower bound, not just a floor — an unpinned
  # major-version bump can silently change resource schemas and turn the
  # next `plan` into a proposal to destroy the database. This has
  # genuinely happened to people; D4.4 in the plan calls it out
  # explicitly.
  required_version = ">= 1.16, < 2.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    # Values filled in from infra/terraform/bootstrap's output — not
    # hardcoded here as a template because the storage account name has
    # a random suffix baked in at bootstrap time. See backend.hcl
    # (gitignored — contains the actual account name) and README.md in
    # this directory for the real values and how `terraform init` picks
    # them up.
  }
}

provider "azurerm" {
  features {}

  # The provider defaults to shared-key auth for its OWN reads of
  # storage account properties (queue/blob/etc), regardless of what
  # shared_access_key_enabled is set to on the resource itself — this
  # is what caused "KeyBasedAuthenticationNotPermitted" on every
  # plan/apply against sttaddev4471 once its keys were disabled, even
  # for a resource the provider itself created correctly. This flag
  # tells the provider to authenticate via Azure AD for its own
  # management calls instead. Documented, known azurerm limitation, not
  # a workaround specific to this project — see
  # https://github.com/hashicorp/terraform-provider-azurerm/issues/17341
  # and HashiCorp's own support article for this exact error.
  storage_use_azuread = true
}
