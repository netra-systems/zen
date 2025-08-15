# Project Configuration
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

# GitHub Configuration
variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (optional, for repo-level runners)"
  type        = string
  default     = ""
}

variable "github_token" {
  description = "GitHub Personal Access Token with admin:org or repo scope"
  type        = string
  sensitive   = true
}

# Runner Configuration
variable "runner_name" {
  description = "Base name for the runner"
  type        = string
  default     = "gcp-runner"
}

variable "runner_labels" {
  description = "Labels for the runner"
  type        = list(string)
  default     = ["warp-custom-default", "linux", "x64", "docker", "cloud-run"]
}

# Cloud Run Configuration
variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation for each instance"
  type        = string
  default     = "2"
}

variable "memory" {
  description = "Memory allocation for each instance"
  type        = string
  default     = "4Gi"
}

# Optional Features
variable "enable_docker" {
  description = "Enable Docker-in-Docker support"
  type        = bool
  default     = false
}

variable "enable_keepalive" {
  description = "Enable Cloud Scheduler to keep instances warm"
  type        = bool
  default     = true
}