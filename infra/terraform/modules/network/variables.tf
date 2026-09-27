variable "name" {
  description = "VNet name."
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

variable "address_space" {
  description = "VNet address space. Phase 3 had to expand this from a single /24 to add a second /23 after discovering Container Apps VNet integration needs at least a /23 — see ADR 0008. Defaulting to both blocks from the start here so Terraform never needs a mid-project address-space expansion."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.1.0.0/23"]
}
