# Database Module - PostgreSQL, Redis, and ClickHouse for staging

# PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "staging-postgres-${var.environment_name}"
  database_version = "POSTGRES_14"
  region           = var.region
  
  # Add timeouts to prevent hanging
  timeouts {
    create = "15m"
    update = "10m"
    delete = "10m"
  }

  settings {
    tier = var.postgres_tier
    
    disk_size       = var.postgres_disk_size
    disk_type       = "PD_SSD"
    disk_autoresize = true
    
    backup_configuration {
      enabled                        = var.enable_backups
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = var.enable_point_in_time_recovery
      transaction_log_retention_days = 3
      
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = var.vpc_network_id
      require_ssl     = var.require_ssl
      
      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
    
    database_flags {
      name  = "log_statement"
      value = "all"
    }
    
    database_flags {
      name  = "log_duration"
      value = "on"
    }
    
    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM
      update_track = "stable"
    }
    
    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }
  }

  deletion_protection = var.deletion_protection
}

# Database
resource "google_sql_database" "main" {
  name     = "netra_staging"
  instance = google_sql_database_instance.postgres.name
}

# Database User
resource "google_sql_user" "main" {
  name     = "netra_user"
  instance = google_sql_database_instance.postgres.name
  password = var.postgres_password
}

# Redis Instance (Memorystore)
resource "google_redis_instance" "cache" {
  name           = "staging-redis-${var.environment_name}"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb

  region = var.region
  redis_version = "REDIS_6_X"
  
  # Add timeouts to prevent hanging
  timeouts {
    create = "10m"
    update = "10m"
    delete = "5m"
  }

  authorized_network = var.vpc_network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
    notify-keyspace-events = "Ex"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 4
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  labels = var.labels
}

# ClickHouse - Using existing dev environment instance
# No separate ClickHouse instance for staging, will use dev environment's ClickHouse

# Secret Manager for database credentials
resource "google_secret_manager_secret" "db_password" {
  secret_id = "staging-db-password-${var.environment_name}"
  
  replication {
    auto {}
  }
  
  labels = var.labels
}

resource "google_secret_manager_secret_version" "db_password" {
  secret = google_secret_manager_secret.db_password.id
  secret_data = var.postgres_password
}

# Generate connection strings
locals {
  postgres_connection_string = "postgresql://${google_sql_user.main.name}:${var.postgres_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.main.name}"
  
  redis_connection_string = "redis://:${google_redis_instance.cache.auth_string}@${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
  
  # ClickHouse connection string will be provided externally (from dev environment)
  clickhouse_connection_string = var.clickhouse_connection_string
}