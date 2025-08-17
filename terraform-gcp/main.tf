# main.tf - GCP Infrastructure for Netra (Budget-Optimized)
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "gcs" {
    # Bucket and prefix will be set via backend-config
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "sqladmin.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com"
  ])
  
  service = each.value
  disable_on_destroy = false
}

# Artifact Registry for Container Images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "netra-containers"
  format        = "DOCKER"
  description   = "Docker repository for Netra containers"
  
  depends_on = [google_project_service.apis]
}

# Random suffix for unique resource names
resource "random_id" "db_name_suffix" {
  byte_length = 4
}

# Cloud SQL PostgreSQL Instance (Budget-optimized)
resource "google_sql_database_instance" "postgres" {
  name             = "netra-postgres-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_14"
  region           = var.region

  settings {
    tier = "db-f1-micro"  # Smallest instance for budget
    
    disk_size = 20  # 20GB minimum
    disk_type = "PD_SSD"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                       = var.region
      point_in_time_recovery_enabled = false  # Disabled to save costs
    }

    ip_configuration {
      ipv4_enabled    = true
      
      authorized_networks {
        name  = "allow-all"  # For development; restrict in production
        value = "0.0.0.0/0"
      }
    }

    database_flags {
      name  = "max_connections"
      value = "50"
    }
  }

  deletion_protection = false  # For easy cleanup; enable in production
  
  depends_on = [google_project_service.apis]
}

# Database
resource "google_sql_database" "main" {
  name     = "netra"
  instance = google_sql_database_instance.postgres.name
}

# Database User Password
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Database User
resource "google_sql_user" "main" {
  name     = "netra_user"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# JWT Secret
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# Secret Manager for sensitive data
resource "google_secret_manager_secret" "db_password" {
  secret_id = "netra-db-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# JWT secret is defined in auth_service.tf

# Service Account for Cloud Run
resource "google_service_account" "cloudrun" {
  account_id   = "netra-cloudrun"
  display_name = "Netra Cloud Run Service Account"
  
  depends_on = [google_project_service.apis]
}

# IAM permissions for Cloud Run
resource "google_project_iam_member" "cloudrun_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

resource "google_project_iam_member" "cloudrun_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = "netra-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/backend:latest"
        
        ports {
          container_port = 8080
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.main.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.public_ip_address}:5432/${google_sql_database.main.name}"
        }
        
        env {
          name  = "REDIS_URL"
          value = var.redis_url
        }
        
        env {
          name  = "ENVIRONMENT"
          value = "staging"
        }
        
        env {
          name  = "CORS_ORIGINS"
          value = "https://netra-frontend-701982941522.us-central1.run.app,https://staging.netrasystems.ai,https://app.staging.netrasystems.ai"
        }
        
        env {
          name  = "GCP_PROJECT_ID_NUMERICAL_STAGING"
          value = var.project_id_numerical != "" ? var.project_id_numerical : var.project_id
        }
        
        env {
          name  = "SECRET_MANAGER_PROJECT_ID"
          value = var.project_id_numerical != "" ? var.project_id_numerical : var.project_id
        }
        
        env {
          name  = "LOAD_SECRETS"
          value = "true"  # Explicitly enable secret loading for staging
        }
        
        env {
          name  = "ENVIRONMENT"
          value = "staging"  # Ensure auth system knows this is staging
        }
        
        env {
          name  = "GOOGLE_OAUTH_CLIENT_ID_STAGING"  # Match what environment_config.py expects
          value_from {
            secret_key_ref {
              name = "google-client-id-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"  # Match what environment_config.py expects
          value_from {
            secret_key_ref {
              name = "google-client-secret-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "FRONTEND_URL"
          value = "https://netra-frontend-e7oy7k4boa-uc.a.run.app"
        }
        
        env {
          name  = "BACKEND_URL"
          value = "https://netra-backend-e7oy7k4boa-uc.a.run.app"
        }
        
        env {
          name  = "CLICKHOUSE_URL"
          value = "http://localhost:8123"
        }
        
        env {
          name  = "CLICKHOUSE_DATABASE"
          value = "netra"
        }
        
        env {
          name  = "ANTHROPIC_API_KEY"
          value = "dummy-api-key"
        }
        
        env {
          name  = "OPENAI_API_KEY"
          value = "dummy-api-key"
        }
        
        env {
          name  = "GEMINI_API_KEY"  # Changed from GOOGLE_GEMINI_API_KEY to match expected env var
          value_from {
            secret_key_ref {
              name = "gemini-api-key-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "FERNET_KEY"
          value_from {
            secret_key_ref {
              name = "fernet-key-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "JWT_SECRET_KEY"  # Changed from SECRET_KEY to match expected env var
          value_from {
            secret_key_ref {
              name = "jwt-secret-key-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "SKIP_MIGRATIONS"
          value = "true"
        }
        
        env {
          name  = "DISABLE_STARTUP_CHECKS"
          value = "true"
        }
      }
      
      service_account_name = google_service_account.cloudrun.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "0"
        "autoscaling.knative.dev/maxScale" = "2"
        "run.googleapis.com/cpu-throttling" = "true"  # Only charge when processing
        # Not using Cloud SQL proxy - using direct IP connection
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_service.apis,
    google_artifact_registry_repository.main
  ]
}

# Cloud Run Service - Frontend
resource "google_cloud_run_service" "frontend" {
  name     = "netra-frontend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/frontend:latest"
        
        resources {
          limits = {
            cpu    = "0.5"
            memory = "1Gi"
          }
        }
        
        env {
          name  = "NEXT_PUBLIC_API_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
        
        env {
          name  = "NEXT_PUBLIC_WS_URL"
          value = replace(google_cloud_run_service.backend.status[0].url, "https", "wss")
        }
      }
      
      service_account_name = google_service_account.cloudrun.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "3"
        "run.googleapis.com/cpu-throttling" = "true"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_cloud_run_service.backend,
    google_artifact_registry_repository.main
  ]
}

# Allow unauthenticated access to Frontend (public app)
resource "google_cloud_run_service_iam_member" "frontend_public" {
  service  = google_cloud_run_service.frontend.name
  location = google_cloud_run_service.frontend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Allow unauthenticated access to Backend API
resource "google_cloud_run_service_iam_member" "backend_public" {
  service  = google_cloud_run_service.backend.name
  location = google_cloud_run_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Storage bucket for backups - commented out due to constraints
# resource "google_storage_bucket" "backups" {
#   name          = "${var.project_id}-netra-backups"
#   location      = var.region
#   force_destroy = true
#
#   lifecycle_rule {
#     condition {
#       age = 30  # Delete backups older than 30 days
#     }
#     action {
#       type = "Delete"
#     }
#   }
#   
#   versioning {
#     enabled = false  # Disabled to save costs
#   }
#   
#   depends_on = [google_project_service.apis]
# }