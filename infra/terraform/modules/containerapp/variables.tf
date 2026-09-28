variable "name_prefix" {
  description = "Used to name the environment (cae-{name_prefix}) and both apps (ca-{name_prefix}-api, ca-{name_prefix}-web)."
  type        = string
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

variable "infrastructure_subnet_id" {
  description = "The Container Apps subnet from the network module. Setting this is what makes the environment support VNet integration and managed identity at all — see ADR 0008."
  type        = string
}

variable "identity_id" {
  type = string
}

variable "identity_client_id" {
  description = "Needed for TAD_MANAGED_IDENTITY_CLIENT_ID — DefaultAzureCredential doesn't auto-discover a user-assigned identity without it (ADR 0008 addendum)."
  type        = string
}

variable "acr_login_server" {
  type = string
}

variable "api_image" {
  type = string
}

variable "web_image" {
  type = string
}

variable "database_url_secret_id" {
  description = "The Key Vault secret's versionless URI, from the key_vault module."
  type        = string
}

variable "blob_account_url" {
  type = string
}
