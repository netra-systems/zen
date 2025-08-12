variable "environment_name" {
  description = "Name of the staging environment"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR range for the main subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "connector_cidr" {
  description = "CIDR range for the VPC connector"
  type        = string
  default     = "10.1.0.0/28"
}

variable "domain" {
  description = "Domain name for the application"
  type        = string
  default     = "*"
}

variable "ssl_certificate_id" {
  description = "ID of the SSL certificate for HTTPS"
  type        = string
  default     = ""
}

variable "backend_backend_service" {
  description = "Backend service ID for the API"
  type        = string
  default     = ""
}

variable "frontend_backend_service" {
  description = "Backend service ID for the frontend"
  type        = string
  default     = ""
}

variable "default_backend_service" {
  description = "Default backend service ID"
  type        = string
  default     = ""
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor security policy"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}