variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "acr_id" {
  description = "Scopes the AcrPull role assignment."
  type        = string
}

variable "storage_account_id" {
  description = "Scopes the Storage Blob Data Contributor role assignment."
  type        = string
}

variable "key_vault_id" {
  description = "Scopes the Key Vault Secrets User role assignment."
  type        = string
}
