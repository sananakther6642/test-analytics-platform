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

variable "vnet_id" {
  description = "Needed to link the private DNS zone to the VNet — a zone link is a VNet-level resource, separate from the subnet delegation."
  type        = string
}

variable "delegated_subnet_id" {
  type = string
}

variable "database_name" {
  type    = string
  default = "tad"
}
