# auth-service.tf - Dedicated Auth Service Infrastructure

# Auth Service Cloud Run
resource "google_cloud_run_service" "auth" {
  name     = "netra-auth-service"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/auth-service:latest"
        
        ports {
          container_port = 8080
        }
        
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"  # Auth service needs less memory
          }
        }
        
        # Core Environment Variables
        env {
          name  = "SERVICE_NAME"
          value = "auth-service"
        }
        
        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }
        
        # Database Configuration
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.main.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres.public_ip_address}:5432/${google_sql_database.main.name}"
        }
        
        # Redis Configuration
        env {
          name  = "REDIS_URL"
          value = var.redis_url
        }
        
        # JWT Configuration
        env {
          name  = "JWT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.secret_id
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "JWT_ALGORITHM"
          value = "HS256"
        }
        
        env {
          name  = "JWT_EXPIRATION_MINUTES"
          value = "1440"  # 24 hours
        }
        
        # CORS Configuration for Auth Service
        env {
          name  = "CORS_ORIGINS"
          value = join(",", [
            "https://netra-frontend-${var.project_id_numerical}.${var.region}.run.app",
            "https://app.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai",
            "https://api.staging.netrasystems.ai",
            "https://backend.staging.netrasystems.ai",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080"
          ])
        }
        
        # OAuth Configuration
        env {
          name  = "GOOGLE_OAUTH_CLIENT_ID_STAGING"
          value_from {
            secret_key_ref {
              name = "google-client-id-staging"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"
          value_from {
            secret_key_ref {
              name = "google-client-secret-staging"
              key  = "latest"
            }
          }
        }
        
        # Auth Service URLs
        env {
          name  = "AUTH_SERVICE_URL"
          value = "https://netra-auth-service-${var.project_id_numerical}.${var.region}.run.app"
        }
        
        env {
          name  = "BACKEND_URL"
          value = "https://netra-backend-${var.project_id_numerical}.${var.region}.run.app"
        }
        
        env {
          name  = "FRONTEND_URL"
          value = var.environment == "production" ? "https://netrasystems.ai" : "https://app.staging.netrasystems.ai"
        }
        
        # Secret Manager Configuration
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
          value = "true"
        }
        
        # Security Headers
        env {
          name  = "SECURE_HEADERS_ENABLED"
          value = "true"
        }
        
        # Encryption Key for sensitive data
        env {
          name  = "FERNET_KEY"
          value_from {
            secret_key_ref {
              name = "fernet-key-staging"
              key  = "latest"
            }
          }
        }
        
        # Session Configuration
        env {
          name  = "SESSION_SECRET_KEY"
          value_from {
            secret_key_ref {
              name = "session-secret-key"
              key  = "latest"
            }
          }
        }
        
        env {
          name  = "SESSION_COOKIE_NAME"
          value = "netra_auth_session"
        }
        
        env {
          name  = "SESSION_COOKIE_SECURE"
          value = var.environment != "development" ? "true" : "false"
        }
        
        env {
          name  = "SESSION_COOKIE_HTTPONLY"
          value = "true"
        }
        
        env {
          name  = "SESSION_COOKIE_SAMESITE"
          value = var.environment == "development" ? "lax" : "strict"
        }
      }
      
      service_account_name = google_service_account.auth_service.email
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"  # Always keep 1 instance warm
        "autoscaling.knative.dev/maxScale" = "10"
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.apis,
    google_service_account.auth_service
  ]
}

# Service Account for Auth Service
resource "google_service_account" "auth_service" {
  account_id   = "netra-auth-service"
  display_name = "Netra Auth Service Account"
  
  depends_on = [google_project_service.apis]
}

# IAM permissions for Auth Service
resource "google_project_iam_member" "auth_service_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.auth_service.email}"
}

resource "google_project_iam_member" "auth_service_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.auth_service.email}"
}

resource "google_project_iam_member" "auth_service_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.auth_service.email}"
}

# Allow public access to auth service
resource "google_cloud_run_service_iam_member" "auth_public" {
  service  = google_cloud_run_service.auth.name
  location = google_cloud_run_service.auth.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Session Secret Key
resource "random_password" "session_secret" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "session_secret" {
  secret_id = "session-secret-key"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "session_secret" {
  secret = google_secret_manager_secret.session_secret.id
  secret_data = random_password.session_secret.result
}

# Auth service is now enabled and ready for deployment
# Backend service configuration updated to use auth service
resource "google_cloud_run_service" "backend_with_auth" {
  count    = 1  # ENABLED - Auth service is active
  name     = "netra-backend"
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers/backend:latest"
        
        # ... existing backend configuration ...
        
        # Add auth service URL
        env {
          name  = "AUTH_SERVICE_URL"
          value = google_cloud_run_service.auth.status[0].url
        }
        
        env {
          name  = "AUTH_SERVICE_INTERNAL_URL"
          value = "http://netra-auth-service.${var.region}.run.app"
        }
      }
    }
  }
}