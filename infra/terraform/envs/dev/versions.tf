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
}
