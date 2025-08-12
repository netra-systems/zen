# Shared Staging Infrastructure
# This creates persistent resources that are shared across all PR environments
# Run this once to set up the staging environment, then PR deployments just create databases/services

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    # Configured in deployment
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Shared VPC for all staging environments
resource "google_compute_network" "staging" {
  name                    = "staging-vpc"
  auto_create_subnetworks = false
  mtu                     = 1460
}

resource "google_compute_subnetwork" "staging" {
  name          = "staging-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.staging.id
  
  private_ip_google_access = true
}

# Shared Cloud SQL Instance (much faster to create databases than instances)
resource "google_sql_database_instance" "staging_shared" {
  name             = "staging-shared-postgres"
  database_version = "POSTGRES_14"
  region           = var.region
  
  settings {
    tier = "db-g1-small"  # Small instance for staging
    
    disk_size       = 20
    disk_type       = "PD_SSD"
    disk_autoresize = true
    
    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }
    
    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.staging.id
      require_ssl     = false  # Simplify for staging
    }
    
    database_flags {
      name  = "max_connections"
      value = "200"  # Support multiple PR environments
    }
  }
  
  deletion_protection = true  # Protect shared instance
}

# Shared Redis Instance
resource "google_redis_instance" "staging_shared" {
  name           = "staging-shared-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  
  region        = var.region
  redis_version = "REDIS_6_X"
  
  authorized_network = google_compute_network.staging.id
  connect_mode      = "PRIVATE_SERVICE_ACCESS"
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
}

# Pre-provisioned wildcard SSL certificate (instant, no DNS wait)
resource "google_compute_managed_ssl_certificate" "wildcard" {
  name = "staging-wildcard-cert"
  
  managed {
    domains = ["*.${var.staging_domain}"]
  }
}

# Regional NEG for Cloud Run (faster than global)
resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "staging-cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    # This will be populated per-PR
  }
}

# Shared VPC Connector for Cloud Run
resource "google_vpc_access_connector" "staging" {
  name          = "staging-connector"
  region        = var.region
  network       = google_compute_network.staging.name
  ip_cidr_range = "10.1.0.0/28"
  
  min_instances = 2
  max_instances = 10
}

# Service account for staging environments
resource "google_service_account" "staging" {
  account_id   = "staging-environments"
  display_name = "Staging Environments Service Account"
}

# Grant necessary permissions
resource "google_project_iam_member" "staging_permissions" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/redis.editor",
    "roles/run.developer",
    "roles/compute.networkUser",
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.staging.email}"
}

# Outputs for PR deployments to use
output "vpc_id" {
  value = google_compute_network.staging.id
}

output "subnet_id" {
  value = google_compute_subnetwork.staging.id
}

output "vpc_connector_id" {
  value = google_vpc_access_connector.staging.id
}

output "sql_instance_name" {
  value = google_sql_database_instance.staging_shared.name
}

output "sql_instance_connection" {
  value = google_sql_database_instance.staging_shared.connection_name
}

output "redis_host" {
  value = google_redis_instance.staging_shared.host
}

output "redis_port" {
  value = google_redis_instance.staging_shared.port
}

output "ssl_certificate_id" {
  value = google_compute_managed_ssl_certificate.wildcard.id
}

output "service_account_email" {
  value = google_service_account.staging.email
}