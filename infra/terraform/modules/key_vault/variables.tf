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

variable "database_url" {
  description = "The full TAD_DATABASE_URL connection string, written as a Key Vault secret. Sensitive."
  type        = string
  sensitive   = true
}
