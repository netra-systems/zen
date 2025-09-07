# GCP Project Configuration
variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "netra-staging"
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for resources"
  type        = string
  default     = "us-central1-c"
}

# Environment Configuration
variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

# Cloud SQL Configuration
variable "postgres_version" {
  description = "PostgreSQL version for Cloud SQL"
  type        = string
  default     = "POSTGRES_17"  # Latest PostgreSQL 17
}

variable "database_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-g1-small"  # Matching current staging tier
}

variable "database_name" {
  description = "Default database name"
  type        = string
  default     = "netra"
}

variable "database_user" {
  description = "Database superuser name"
  type        = string
  default     = "postgres"
}

variable "app_database_user" {
  description = "Application database user"
  type        = string
  default     = "netra_app"
}

# Network Configuration
variable "enable_private_ip" {
  description = "Enable private IP for Cloud SQL"
  type        = bool
  default     = true
}

variable "enable_public_ip" {
  description = "Enable public IP for Cloud SQL"
  type        = bool
  default     = true  # Needed for external connectivity
}

variable "authorized_networks" {
  description = "List of authorized networks for Cloud SQL"
  type = list(object({
    name  = string
    value = string
  }))
  default = [
    {
      name  = "allow-all"  # For staging only; restrict in production
      value = "0.0.0.0/0"
    }
  ]
}

# Backup Configuration
variable "backup_enabled" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Start time for automated backups (HH:MM format)"
  type        = string
  default     = "02:00"
}

variable "backup_location" {
  description = "Location for backups"
  type        = string
  default     = "us"
}

variable "retained_backups" {
  description = "Number of backups to retain"
  type        = number
  default     = 7
}

variable "transaction_log_retention_days" {
  description = "Number of days to retain transaction logs"
  type        = number
  default     = 7
}

# Storage Configuration
variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 10
}

variable "disk_type" {
  description = "Disk type (PD_SSD or PD_HDD)"
  type        = string
  default     = "PD_SSD"
}

variable "disk_autoresize" {
  description = "Enable disk autoresize"
  type        = bool
  default     = true
}

variable "disk_autoresize_limit" {
  description = "Maximum disk size in GB for autoresize"
  type        = number
  default     = 100
}

# High Availability Configuration
variable "availability_type" {
  description = "Availability type (ZONAL or REGIONAL)"
  type        = string
  default     = "ZONAL"  # Use REGIONAL for production
}

# Maintenance Configuration
variable "maintenance_window_day" {
  description = "Day of week for maintenance window (1-7, 1 = Monday)"
  type        = number
  default     = 7  # Sunday
}

variable "maintenance_window_hour" {
  description = "Hour of day for maintenance window (0-23)"
  type        = number
  default     = 3
}

variable "maintenance_window_update_track" {
  description = "Update track for maintenance (canary or stable)"
  type        = string
  default     = "stable"
}

# Database Flags Configuration
variable "database_flags" {
  description = "Database flags for PostgreSQL configuration"
  type = list(object({
    name  = string
    value = string
  }))
  default = [
    {
      name  = "max_connections"
      value = "200"
    },
    {
      name  = "shared_buffers"
      value = "256000"  # in 8KB units, ~2GB
    },
    {
      name  = "work_mem"
      value = "4096"  # in KB, 4MB
    },
    {
      name  = "maintenance_work_mem"
      value = "65536"  # in KB, 64MB
    },
    {
      name  = "effective_cache_size"
      value = "1048576"  # in 8KB units, ~8GB
    },
    {
      name  = "random_page_cost"
      value = "1.1"  # SSD optimization
    },
    {
      name  = "log_statement"
      value = "all"  # For staging debugging
    },
    {
      name  = "log_duration"
      value = "on"
    },
    {
      name  = "log_connections"
      value = "on"
    },
    {
      name  = "log_disconnections"
      value = "on"
    }
  ]
}

# Redis Configuration (using Memorystore)
variable "redis_tier" {
  description = "Redis instance tier"
  type        = string
  default     = "BASIC"
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_2"
}

# Load Balancer Configuration
variable "backend_timeout_sec" {
  description = "Backend service timeout in seconds for WebSocket support"
  type        = number
  default     = 86400  # CRITICAL FIX: Increase to 24 hours for WebSocket connections
}

variable "session_affinity_ttl_sec" {
  description = "Session affinity cookie TTL in seconds"
  type        = number
  default     = 86400  # CRITICAL FIX: Increase to 24 hours
}

# WebSocket Configuration
variable "websocket_timeout_sec" {
  description = "WebSocket connection timeout in seconds for long-lived connections"
  type        = number
  default     = 86400  # 24 hours for WebSocket connections
}

variable "force_https_enabled" {
  description = "Force HTTPS for all services"
  type        = bool
  default     = true
}

# Labels for resource organization
variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    environment = "staging"
    project     = "netra"
    managed_by  = "terraform"
    team        = "platform"
  }
}

# Monitoring and Alerting Configuration
variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []  # Add notification channel IDs once created in GCP
}