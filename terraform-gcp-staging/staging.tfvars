# GCP Staging Infrastructure Variables
# CRITICAL: These values configure the staging environment infrastructure

project_id = "netra-staging"
region = "us-central1"
zone = "us-central1-c"
environment = "staging"

# Database Configuration - Optimized for staging workloads
postgres_version = "POSTGRES_17"
database_tier = "db-g1-small"
database_name = "netra"
database_user = "postgres"
app_database_user = "netra_app"

# Network Configuration - VPC required for Redis/Database access
enable_private_ip = true
enable_public_ip = true

# Database performance settings
disk_size = 20
disk_type = "PD_SSD"
disk_autoresize = true
disk_autoresize_limit = 100
availability_type = "ZONAL"

# Redis Configuration - Memory Store for caching
redis_tier = "BASIC"
redis_memory_size_gb = 1
redis_version = "REDIS_7_2"

# Load Balancer Configuration - CRITICAL for WebSocket support
backend_timeout_sec = 86400  # 24 hours for WebSocket connections
session_affinity_ttl_sec = 86400  # 24 hours
websocket_timeout_sec = 86400  # 24 hours for long-lived connections
force_https_enabled = true

# Authentication Header Preservation - Required for JWT/WebSocket
authentication_header_preservation_enabled = true
preserved_auth_headers = ["Authorization", "X-E2E-Bypass"]

# Database Performance Flags
database_flags = [
  {
    name  = "max_connections"
    value = "100"
  },
  {
    name  = "shared_buffers"
    value = "128000"  # ~1GB for staging
  },
  {
    name  = "work_mem"
    value = "4096"  # 4MB
  },
  {
    name  = "maintenance_work_mem"
    value = "32768"  # 32MB
  },
  {
    name  = "effective_cache_size"
    value = "524288"  # ~4GB
  },
  {
    name  = "random_page_cost"
    value = "1.1"  # SSD optimization
  },
  {
    name  = "log_statement"
    value = "ddl"  # Reduced logging for staging performance
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

# Backup Configuration
backup_enabled = true
backup_start_time = "03:00"
backup_location = "us"
retained_backups = 3
transaction_log_retention_days = 3

# Maintenance Window
maintenance_window_day = 7  # Sunday
maintenance_window_hour = 4  # 4 AM
maintenance_window_update_track = "stable"

# Resource Labels
labels = {
  environment = "staging"
  project     = "netra"
  managed_by  = "terraform"
  team        = "platform"
  purpose     = "staging-infrastructure"
  cost_center = "engineering"
}

# Authorized Networks for Cloud SQL (staging - more permissive)
authorized_networks = [
  {
    name  = "staging-access"
    value = "0.0.0.0/0"  # Open for staging, restrict for production
  }
]