# GCP Project Configuration
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for compute resources"
  type        = string
  default     = "us-central1-a"
}

# GitHub Configuration
variable "github_token" {
  description = "GitHub Personal Access Token with repo and admin:org scopes"
  type        = string
  sensitive   = true
  
  validation {
    condition     = length(var.github_token) > 0
    error_message = "GitHub token must be provided. Set it via TF_VAR_github_token environment variable or enter when prompted."
  }
}

variable "github_org" {
  description = "GitHub organization name"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name (optional, for repo-level runners)"
  type        = string
  default     = ""
}

# Runner Configuration
variable "runner_name" {
  description = "Base name for GitHub runners"
  type        = string
  default     = "gcp-runner"
}

variable "runner_count" {
  description = "Number of runners to create (when not using autoscaling)"
  type        = number
  default     = 1
}

variable "runner_labels" {
  description = "Labels to apply to runners"
  type        = list(string)
  default     = ["self-hosted", "linux", "x64", "gcp"]
}

variable "runner_group" {
  description = "Runner group name (for organization runners)"
  type        = string
  default     = ""
}

variable "runner_version" {
  description = "GitHub Actions runner version"
  type        = string
  default     = "2.319.1"
}

# Instance Configuration
variable "machine_type" {
  description = "GCP machine type for runner instances"
  type        = string
  default     = "e2-standard-2"
}

variable "boot_disk_image" {
  description = "Boot disk image for runner instances"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "boot_disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "boot_disk_type" {
  description = "Boot disk type"
  type        = string
  default     = "pd-standard"
}

variable "use_preemptible" {
  description = "Use preemptible instances for cost savings"
  type        = bool
  default     = false
}

# Autoscaling Configuration
variable "enable_autoscaling" {
  description = "Enable autoscaling for runners"
  type        = bool
  default     = false
}

variable "min_runners" {
  description = "Minimum number of runners (for autoscaling)"
  type        = number
  default     = 1
}

variable "max_runners" {
  description = "Maximum number of runners (for autoscaling)"
  type        = number
  default     = 5
}

# Network Configuration
variable "enable_ssh" {
  description = "Enable SSH access to runners (for debugging)"
  type        = bool
  default     = false
}

variable "ssh_source_ranges" {
  description = "Source IP ranges allowed for SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Storage Configuration
variable "artifact_retention_days" {
  description = "Number of days to retain artifacts in storage bucket"
  type        = number
  default     = 30
}

# Environment
variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}