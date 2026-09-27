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
