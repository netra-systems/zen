# Domain mappings for staging environment
# Configures custom domains for Cloud Run services in staging

# Backend staging domain mapping
resource "google_cloud_run_domain_mapping" "backend_staging" {
  location = var.region
  name     = "backend.staging.netrasystems.ai"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = "netra-backend-staging"
  }
}

# Frontend staging domain mapping  
resource "google_cloud_run_domain_mapping" "frontend_staging" {
  location = var.region
  name     = "app.staging.netrasystems.ai"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = "netra-frontend-staging"
  }
}

# Auth proxy staging domain mapping
resource "google_cloud_run_domain_mapping" "auth_staging" {
  location = var.region
  name     = "auth.staging.netrasystems.ai"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = "netra-auth-proxy-staging"
  }
}

# Cloud Run service for auth proxy
resource "google_cloud_run_service" "auth_proxy_staging" {
  name     = "netra-auth-proxy-staging"
  location = var.region

  template {
    spec {
      containers {
        image = "gcr.io/cloudrun/hello"  # Replace with actual auth proxy image
        
        env {
          name  = "ENVIRONMENT"
          value = "staging"
        }
        
        env {
          name  = "BACKEND_URL"
          value = "https://backend.staging.netrasystems.ai"
        }
        
        env {
          name  = "FRONTEND_URL"
          value = "https://app.staging.netrasystems.ai"
        }
        
        env {
          name  = "GOOGLE_OAUTH_CLIENT_ID"
          value = var.google_oauth_client_id_staging
        }
        
        env {
          name = "GOOGLE_OAUTH_CLIENT_SECRET"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.oauth_client_secret_staging.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# IAM policy for auth proxy public access
resource "google_cloud_run_service_iam_member" "auth_proxy_staging_public" {
  service  = google_cloud_run_service.auth_proxy_staging.name
  location = google_cloud_run_service.auth_proxy_staging.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Secret for OAuth client secret
resource "google_secret_manager_secret" "oauth_client_secret_staging" {
  secret_id = "oauth-client-secret-staging"
  
  replication {
    auto {}
  }
}

# Output URLs for reference
output "staging_urls" {
  value = {
    frontend = "https://app.staging.netrasystems.ai"
    backend  = "https://backend.staging.netrasystems.ai"
    auth     = "https://auth.staging.netrasystems.ai"
  }
  description = "Staging environment URLs"
}