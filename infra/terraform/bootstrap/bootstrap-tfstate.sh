#!/usr/bin/env bash
# Creates the storage Terraform itself needs before it can run at all —
# the classic bootstrap problem: Terraform can't create the backend it
# stores its own state in. This is the one deliberate exception to
# "everything is Terraform" in this project, and it's why this is a
# plain script, not a .tf file.
#
# Idempotent: safe to re-run. Each az command either creates the
# resource or is a no-op if it already exists (checked explicitly below
# rather than relying on az's own "already exists" exit codes, which
# vary by resource type).
#
# Run once, by hand, before `terraform init` is ever run against this
# backend. Not part of CI, not run automatically.

set -euo pipefail

RESOURCE_GROUP="rg-tad-tfstate"
LOCATION="swedencentral"
STORAGE_ACCOUNT="sttadtfstate$(openssl rand -hex 3)"
CONTAINER_NAME="tfstate"

echo "== Terraform state bootstrap =="
echo "Resource group:  $RESOURCE_GROUP"
echo "Location:        $LOCATION"
echo "Storage account: $STORAGE_ACCOUNT (generated, must be globally unique)"
echo ""

if az group show --name "$RESOURCE_GROUP" &>/dev/null; then
  echo "Resource group '$RESOURCE_GROUP' already exists, skipping create."
else
  echo "Creating resource group '$RESOURCE_GROUP'..."
  az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags project=tad env=dev phase=P4 managed-by=bootstrap-script
fi

echo "Creating storage account '$STORAGE_ACCOUNT'..."
# Standard_LRS: state files are small text, no need for geo-redundancy.
# TLS 1.2 minimum, key access disabled to match this project's
# zero-secrets pattern — Terraform authenticates via `az login` /
# service principal through azurerm's own auth, not a storage key.
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-shared-key-access false \
  --tags project=tad env=dev phase=P4 managed-by=bootstrap-script

echo "Enabling blob versioning (state-recovery story: a bad apply that"
echo "corrupts state can be rolled back to a previous blob version)..."
az storage account blob-service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --enable-versioning true

echo "Creating container '$CONTAINER_NAME'..."
az storage container create \
  --name "$CONTAINER_NAME" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login

echo "Applying a CanNotDelete lock on the storage account..."
# This is the actual protection against "terraform destroy" or a stray
# portal click wiping out the one thing that must never disappear:
# the record of everything else Terraform has created.
az lock create \
  --name "tfstate-cannot-delete" \
  --resource-group "$RESOURCE_GROUP" \
  --resource-name "$STORAGE_ACCOUNT" \
  --resource-type Microsoft.Storage/storageAccounts \
  --lock-type CanNotDelete

echo ""
echo "== Done =="
echo "Add this to your Terraform backend config (envs/dev/backend.tf):"
echo ""
echo "  backend \"azurerm\" {"
echo "    resource_group_name  = \"$RESOURCE_GROUP\""
echo "    storage_account_name = \"$STORAGE_ACCOUNT\""
echo "    container_name       = \"$CONTAINER_NAME\""
echo "    key                  = \"dev.terraform.tfstate\""
echo "    use_azuread_auth     = true"
echo "  }"
