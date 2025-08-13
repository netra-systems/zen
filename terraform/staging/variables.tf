variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_id_numerical" {
  description = "GCP Project Numerical ID for Secret Manager"
  type        = string
  default     = ""  # Will be set in workflow
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "pr_number" {
  description = "Pull Request number"
  type        = string
}

variable "pr_branch" {
  description = "Pull Request branch name"
  type        = string
  default     = ""
}

variable "backend_image" {
  description = "Backend container image URL"
  type        = string
}

variable "frontend_image" {
  description = "Frontend container image URL"
  type        = string
}

variable "domain" {
  description = "Base domain for staging environments"
  type        = string
  default     = "staging.netrasystems.ai"
}

variable "dns_zone_name" {
  description = "Cloud DNS zone name"
  type        = string
  default     = "staging-netrasystems-ai"
}

variable "billing_account" {
  description = "GCP Billing Account ID"
  type        = string
  default     = ""
}

variable "cost_limit_per_pr" {
  description = "Maximum cost per PR in USD"
  type        = string
  default     = "50"
}

variable "resource_limits" {
  description = "Resource limits for staging environment"
  type = object({
    cpu_limit             = string
    memory_limit          = string
    min_instances         = number
    max_instances         = number
    database_tier         = string
    database_storage_gb   = number
    redis_tier            = string
    redis_memory_gb       = number
  })
  default = {
    cpu_limit           = "2"
    memory_limit        = "4Gi"
    min_instances       = 0
    max_instances       = 3
    database_tier       = "db-f1-micro"
    database_storage_gb = 10
    redis_tier          = "BASIC"
    redis_memory_gb     = 1
  }
}

variable "environment_variables" {
  description = "Additional environment variables for the application"
  type        = map(string)
  default     = {}
}

variable "authorized_users" {
  description = "List of email addresses authorized to access staging"
  type        = list(string)
  default     = []
}

variable "enable_cdn" {
  description = "Enable Cloud CDN for static assets"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable monitoring and alerting"
  type        = bool
  default     = true
}

variable "ttl_hours" {
  description = "Time to live for staging environment in hours"
  type        = number
  default     = 168 # 7 days
}

variable "max_instances" {
  description = "Maximum number of instances for auto-scaling"
  type        = number
  default     = 3
}

variable "postgres_password" {
  description = "Password for PostgreSQL database"
  type        = string
  sensitive   = true
}

variable "cpu_limit" {
  description = "CPU limit for backend service"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit for backend service"
  type        = string
  default     = "4Gi"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "jwt_secret_key" {
  description = "JWT secret key for authentication (optional, will use default if not provided)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "fernet_key" {
  description = "Fernet key for encryption (optional, will use default if not provided)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "clickhouse_password" {
  description = "ClickHouse password for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "clickhouse_url" {
  description = "Full ClickHouse URL with credentials (optional, overrides default)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key for LLM operations (optional, will use placeholder if not provided)"
  type        = string
  default     = ""
  sensitive   = true
}