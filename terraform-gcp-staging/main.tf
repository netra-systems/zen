# Main Configuration for GCP Staging Infrastructure

# Data source for current project
data "google_project" "project" {
  project_id = var.project_id
}

# Create GCS bucket for Terraform state if it doesn't exist
resource "google_storage_bucket" "terraform_state" {
  name          = "${var.project_id}-terraform-state"
  location      = var.region
  force_destroy = false

  versioning {
    enabled = true
  }

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "sqladmin.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com"
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Random suffix for unique resource names
resource "random_id" "db_suffix" {
  byte_length = 4
}

# Generate secure passwords
resource "random_password" "postgres_password" {
  length  = 32
  special = true
}

resource "random_password" "app_password" {
  length  = 32
  special = true
}

# Local values for computed configurations
locals {
  db_instance_name    = "${var.environment}-postgres-${random_id.db_suffix.hex}"
  redis_instance_name = "${var.environment}-redis-${random_id.db_suffix.hex}"

  # Connection strings
  postgres_connection_string = format(
    "postgresql://%s:%s@%s/%s",
    var.database_user,
    random_password.postgres_password.result,
    google_sql_database_instance.postgres.public_ip_address,
    var.database_name
  )

  app_connection_string = format(
    "postgresql://%s:%s@%s/%s",
    var.app_database_user,
    random_password.app_password.result,
    google_sql_database_instance.postgres.public_ip_address,
    var.database_name
  )

  # Cloud SQL proxy connection string for Cloud Run
  cloudsql_connection_string = format(
    "postgresql://%s:%s@/%s?host=/cloudsql/%s:%s:%s",
    var.app_database_user,
    random_password.app_password.result,
    var.database_name,
    var.project_id,
    var.region,
    local.db_instance_name
  )
}