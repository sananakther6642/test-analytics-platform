variable "project" {
  description = "Short project slug used in every resource name (e.g. \"tad\")."
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. \"dev\", \"prod\") — becomes part of resource names and the env tag."
  type        = string
}

variable "phase" {
  description = "Plan phase this resource belongs to, for cost attribution (e.g. \"P4\")."
  type        = string
}

variable "suffix" {
  description = "Short random suffix for globally-unique names (storage accounts, ACR, Key Vault). Generated once in envs/dev and passed in everywhere, not regenerated per-module, so all resources in one apply share the same suffix."
  type        = string
}
