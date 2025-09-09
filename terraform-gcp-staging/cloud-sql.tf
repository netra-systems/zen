# Cloud SQL PostgreSQL Instance Configuration

# VPC for private IP (if enabled)
resource "google_compute_network" "vpc" {
  count                   = var.enable_private_ip ? 1 : 0
  name                    = "${var.environment}-vpc"
  auto_create_subnetworks = false
  project                 = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Subnet for Cloud SQL
resource "google_compute_subnetwork" "subnet" {
  count         = var.enable_private_ip ? 1 : 0
  name          = "${var.environment}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc[0].id
  project       = var.project_id
}

# Private VPC connection for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  count         = var.enable_private_ip ? 1 : 0
  name          = "${var.environment}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc[0].id
  project       = var.project_id

  depends_on = [google_project_service.required_apis]
}

# Service networking connection
resource "google_service_networking_connection" "private_vpc_connection" {
  count                   = var.enable_private_ip ? 1 : 0
  network                 = google_compute_network.vpc[0].id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address[0].name]

  depends_on = [google_project_service.required_apis]
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name                = local.db_instance_name
  database_version    = var.postgres_version
  region              = var.region
  project             = var.project_id
  deletion_protection = false # Set to true for production

  settings {
    tier                  = var.database_tier
    availability_type     = var.availability_type
    disk_size             = var.disk_size
    disk_type             = var.disk_type
    disk_autoresize       = var.disk_autoresize
    disk_autoresize_limit = var.disk_autoresize_limit

    backup_configuration {
      enabled                        = var.backup_enabled
      start_time                     = var.backup_start_time
      location                       = var.backup_location
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = var.transaction_log_retention_days

      backup_retention_settings {
        retained_backups = var.retained_backups
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = var.maintenance_window_day
      hour         = var.maintenance_window_hour
      update_track = var.maintenance_window_update_track
    }

    ip_configuration {
      ipv4_enabled    = var.enable_public_ip
      private_network = var.enable_private_ip ? google_compute_network.vpc[0].id : null
      ssl_mode        = "ALLOW_UNENCRYPTED_AND_ENCRYPTED" # Set to "REQUIRE_SSL" for production

      dynamic "authorized_networks" {
        for_each = var.enable_public_ip ? var.authorized_networks : []
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.value
        }
      }
    }

    dynamic "database_flags" {
      for_each = var.database_flags
      content {
        name  = database_flags.value.name
        value = database_flags.value.value
      }
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    user_labels = var.labels
  }

  depends_on = [
    google_project_service.required_apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# Default database
resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

# Additional databases as needed
resource "google_sql_database" "auth_db" {
  name     = "auth"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

# Database users
resource "google_sql_user" "postgres" {
  name     = var.database_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.postgres_password.result
  project  = var.project_id
}

resource "google_sql_user" "app_user" {
  name     = var.app_database_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.app_password.result
  project  = var.project_id
}