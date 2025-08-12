variable "environment_name" {
  description = "Name of the staging environment"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in format owner/repo"
  type        = string
  default     = ""
}

variable "api_keys" {
  description = "Map of API key names to values"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "oauth_client_id" {
  description = "OAuth client ID"
  type        = string
  default     = ""
}

variable "oauth_client_secret" {
  description = "OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "secret_accessor_members" {
  description = "List of members who can access secrets"
  type        = list(string)
  default     = []
}

variable "enable_security_notifications" {
  description = "Enable Security Command Center notifications"
  type        = bool
  default     = false
}

variable "organization_id" {
  description = "GCP organization ID"
  type        = string
  default     = ""
}

variable "security_pubsub_topic" {
  description = "Pub/Sub topic for security notifications"
  type        = string
  default     = ""
}

variable "enable_org_policies" {
  description = "Enable organization policy constraints"
  type        = bool
  default     = false
}

variable "organization_policies" {
  description = "Map of organization policy constraints"
  type = map(object({
    list_policy = optional(object({
      allow_values = list(string)
      deny_values  = list(string)
    }))
    boolean_policy = optional(object({
      enforced = bool
    }))
  }))
  default = {}
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}