# variables.tf - Variable definitions for GCP infrastructure

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_id_numerical" {
  description = "GCP Project ID in numerical format for Secret Manager API"
  type        = string
  default     = ""  # Will use project_id if not specified
}

variable "region" {
  description = "GCP Region for deployment"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone for deployment"
  type        = string
  default     = "us-central1-a"
}

variable "redis_url" {
  description = "Redis connection URL (if setup separately)"
  type        = string
  default     = "redis://localhost:6379"
}

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
}

variable "enable_apis" {
  description = "Enable required GCP APIs"
  type        = bool
  default     = true
}

variable "create_backups_bucket" {
  description = "Create GCS bucket for backups"
  type        = bool
  default     = true
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"  # Smallest for budget
}

variable "db_disk_size" {
  description = "Database disk size in GB"
  type        = number
  default     = 20  # Minimum for Cloud SQL
}

variable "backend_cpu" {
  description = "Backend Cloud Run CPU allocation"
  type        = string
  default     = "1"
}

variable "backend_memory" {
  description = "Backend Cloud Run memory allocation"
  type        = string
  default     = "2Gi"
}

variable "backend_min_instances" {
  description = "Backend minimum instances"
  type        = number
  default     = 1
}

variable "backend_max_instances" {
  description = "Backend maximum instances"
  type        = number
  default     = 5
}

variable "frontend_cpu" {
  description = "Frontend Cloud Run CPU allocation"
  type        = string
  default     = "0.5"
}

variable "frontend_memory" {
  description = "Frontend Cloud Run memory allocation"
  type        = string
  default     = "1Gi"
}

variable "frontend_min_instances" {
  description = "Frontend minimum instances"
  type        = number
  default     = 1
}

variable "frontend_max_instances" {
  description = "Frontend maximum instances"
  type        = number
  default     = 3
}

variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  default     = ""
}

variable "google_oauth_client_id_staging" {
  description = "Google OAuth Client ID for staging"
  type        = string
  default     = ""
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor security policies"
  type        = bool
  default     = false
}

variable "auth_service_cpu" {
  description = "Auth Service Cloud Run CPU allocation"
  type        = string
  default     = "1"
}

variable "auth_service_memory" {
  description = "Auth Service Cloud Run memory allocation"
  type        = string
  default     = "512Mi"
}

variable "auth_service_min_instances" {
  description = "Auth Service minimum instances"
  type        = number
  default     = 1
}

variable "auth_service_max_instances" {
  description = "Auth Service maximum instances"
  type        = number
  default     = 10
}