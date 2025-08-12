variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "staging_domain" {
  description = "Base domain for staging environments"
  type        = string
  default     = "staging.netrasystems.ai"
}