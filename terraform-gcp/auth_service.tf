# Auth Service Cloud Run Deployment

resource "google_cloud_run_service" "auth_service" {
  name     = "netra-auth-service"
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_id}/auth-service:latest"
        
        ports {
          container_port = 8080
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }

        env {
          name  = "SERVICE_NAME"
          value = "auth-service"
        }

        env {
          name  = "LOG_LEVEL"
          value = "INFO"
        }

        env {
          name = "JWT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.jwt_secret.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "DATABASE_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.auth_database_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name = "REDIS_URL"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.redis_url.secret_id
              key  = "latest"
            }
          }
        }

        env {
          name  = "CORS_ORIGINS"
          value = var.cors_origins
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
      }

      service_account_name = google_service_account.auth_service_sa.email
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"
        "autoscaling.knative.dev/maxScale" = "10"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.jwt_secret,
    google_secret_manager_secret_version.auth_database_url,
    google_secret_manager_secret_version.redis_url
  ]
}

# Service Account for Auth Service
resource "google_service_account" "auth_service_sa" {
  account_id   = "auth-service-sa"
  display_name = "Auth Service Account"
  project      = var.project_id
}

# IAM binding for public access
resource "google_cloud_run_service_iam_member" "auth_service_public" {
  service  = google_cloud_run_service.auth_service.name
  location = google_cloud_run_service.auth_service.location
  project  = var.project_id
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Secret Manager secrets for Auth Service
resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "jwt-secret"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = var.jwt_secret
}

resource "google_secret_manager_secret" "auth_database_url" {
  secret_id = "auth-database-url"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "auth_database_url" {
  secret      = google_secret_manager_secret.auth_database_url.id
  secret_data = var.auth_database_url
}

resource "google_secret_manager_secret" "redis_url" {
  secret_id = "redis-url"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = var.redis_url
}

# Grant secret access to service account
resource "google_secret_manager_secret_iam_member" "auth_service_jwt_secret" {
  secret_id = google_secret_manager_secret.jwt_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.auth_service_sa.email}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "auth_service_database_url" {
  secret_id = google_secret_manager_secret.auth_database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.auth_service_sa.email}"
  project   = var.project_id
}

resource "google_secret_manager_secret_iam_member" "auth_service_redis_url" {
  secret_id = google_secret_manager_secret.redis_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.auth_service_sa.email}"
  project   = var.project_id
}

# Output the auth service URL
output "auth_service_url" {
  value = google_cloud_run_service.auth_service.status[0].url
}