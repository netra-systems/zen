# Optimized variables for staging deployment

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_id_numerical" {
  description = "Numerical GCP project ID for Secret Manager"
  type        = string
  default     = ""
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment_name" {
  description = "Environment name for the deployment"
  type        = string
}

variable "pr_number" {
  description = "Pull request number or branch identifier"
  type        = string
}

variable "branch_name" {
  description = "Git branch name"
  type        = string
}

variable "commit_sha" {
  description = "Git commit SHA"
  type        = string
}

variable "action" {
  description = "Deployment action (deploy or destroy)"
  type        = string
  default     = "deploy"
}

# Image variables
variable "backend_image" {
  description = "Backend Docker image URL"
  type        = string
}

variable "frontend_image" {
  description = "Frontend Docker image URL"
  type        = string
}

# Database configuration
variable "postgres_password" {
  description = "PostgreSQL password for PR database"
  type        = string
  default     = ""
  sensitive   = true
}

variable "clickhouse_url" {
  description = "ClickHouse connection URL"
  type        = string
  default     = ""
  sensitive   = true
}

variable "clickhouse_password" {
  description = "ClickHouse password"
  type        = string
  default     = "staging-clickhouse"
  sensitive   = true
}

# Security configuration
variable "jwt_secret_key" {
  description = "JWT secret key for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "fernet_key" {
  description = "Fernet encryption key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "gemini_api_key" {
  description = "Gemini API key for LLM operations"
  type        = string
  default     = ""
  sensitive   = true
}

# Resource limits
variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = string
  default     = "0"
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = string
  default     = "5"
}

variable "cpu_limit" {
  description = "CPU limit for backend containers"
  type        = string
  default     = "2"
}

variable "memory_limit" {
  description = "Memory limit for backend containers"
  type        = string
  default     = "2Gi"
}