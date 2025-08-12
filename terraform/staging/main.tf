# Optimized Staging Terraform Configuration
# Uses shared infrastructure for fast PR environment provisioning
# Provisioning time: ~2-3 minutes vs 15-20 minutes

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    # Configured dynamically
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data source to get shared infrastructure
data "terraform_remote_state" "shared" {
  backend = "gcs"
  config = {
    bucket = "${var.project_id}-terraform-state"
    prefix = "staging/shared-infrastructure"
  }
}

locals {
  environment_name = "pr-${var.pr_number}"
  
  # Use data from shared infrastructure
  vpc_id                  = data.terraform_remote_state.shared.outputs.vpc_id
  vpc_connector_id        = data.terraform_remote_state.shared.outputs.vpc_connector_id
  sql_instance_name       = data.terraform_remote_state.shared.outputs.sql_instance_name
  sql_instance_connection = data.terraform_remote_state.shared.outputs.sql_instance_connection
  redis_host              = data.terraform_remote_state.shared.outputs.redis_host
  redis_port              = data.terraform_remote_state.shared.outputs.redis_port
  ssl_certificate_id      = data.terraform_remote_state.shared.outputs.ssl_certificate_id
  service_account         = data.terraform_remote_state.shared.outputs.service_account_email
}

# Only create database and user (seconds vs minutes)
resource "google_sql_database" "pr" {
  name     = "netra_${local.environment_name}"
  instance = local.sql_instance_name
}

resource "google_sql_user" "pr" {
  name     = "user_${local.environment_name}"
  instance = local.sql_instance_name
  password = var.postgres_password
}

# Cloud Run service for backend (fast deployment)
resource "google_cloud_run_service" "backend" {
  name     = "backend-${local.environment_name}"
  location = var.region
  
  template {
    spec {
      service_account_name = local.service_account
      
      containers {
        image = var.backend_image
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.pr.name}:${var.postgres_password}@/${google_sql_database.pr.name}?host=/cloudsql/${local.sql_instance_connection}"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${local.redis_host}:${local.redis_port}/${var.pr_number % 16}"
        }
        
        env {
          name  = "PR_NUMBER"
          value = var.pr_number
        }
        
        env {
          name  = "ENVIRONMENT"
          value = "staging"
        }
        
        env {
          name  = "K_SERVICE"
          value = "backend-${local.environment_name}"
        }
        
        env {
          name  = "CLICKHOUSE_URL"
          value = "clickhouse://default:@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1"
        }
        
        env {
          name  = "CLICKHOUSE_HOST"
          value = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
        }
        
        env {
          name  = "CLICKHOUSE_PORT"
          value = "8443"
        }
        
        env {
          name  = "CLICKHOUSE_SECURE"
          value = "true"
        }
        
        env {
          name  = "CLICKHOUSE_TIMEOUT"
          value = "30"
        }
        
        env {
          name  = "SKIP_MIGRATION_ON_STARTUP"
          value = "false"
        }
        
        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
        
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "LOAD_SECRETS"
          value = "true"
        }
        
        env {
          name  = "SECRET_MANAGER_PROJECT"
          value = var.project_id
        }
        
        env {
          name  = "GCP_PROJECT_ID_NUMERICAL_STAGING"
          value = var.project_id_numerical  # Numerical project ID for Secret Manager
        }
        
        # Note: All secrets including Gemini API key will be loaded from Secret Manager at runtime
        # The service account needs access to these secrets in the staging project
        
        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }
        
        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 10
          period_seconds        = 10
          failure_threshold     = 30
        }
        
        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 60
          timeout_seconds       = 10
          period_seconds        = 30
          failure_threshold     = 5
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.min_instances
        "autoscaling.knative.dev/maxScale"        = var.max_instances
        "run.googleapis.com/vpc-access-connector" = local.vpc_connector_id
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
        "run.googleapis.com/cloudsql-instances"   = local.sql_instance_connection
        "run.googleapis.com/startup-cpu-boost"    = "true"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  # Fast provisioning timeout
  timeouts {
    create = "5m"
    update = "5m"
    delete = "2m"
  }
}

# Cloud Run service for frontend
resource "google_cloud_run_service" "frontend" {
  name     = "frontend-${local.environment_name}"
  location = var.region
  
  template {
    spec {
      service_account_name = local.service_account
      
      containers {
        image = var.frontend_image
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
        
        startup_probe {
          http_get {
            path = "/"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 10
          period_seconds        = 10
          failure_threshold     = 30
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "3"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  timeouts {
    create = "5m"
    update = "5m"
    delete = "2m"
  }
}

# Allow unauthenticated access to services
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Use regional load balancer (faster than global)
resource "google_compute_region_network_endpoint_group" "backend" {
  name                  = "backend-neg-${local.environment_name}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.backend.name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend" {
  name                  = "frontend-neg-${local.environment_name}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.frontend.name
  }
}

# Simple URL map using Cloud Run URLs directly
output "frontend_url" {
  value = google_cloud_run_service.frontend.status[0].url
}

output "backend_url" {
  value = google_cloud_run_service.backend.status[0].url
}

output "database_name" {
  value = google_sql_database.pr.name
}