# Cloud Run Backend Service
resource "google_cloud_run_v2_service" "backend" {
  name     = "staging-backend-${var.environment_name}"
  location = var.region
  
  template {
    service_account = google_service_account.staging_backend.email
    
    vpc_access {
      connector = var.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    timeout = "300s"
    
    containers {
      image = var.backend_image
      
      ports {
        container_port = 8000
      }
      
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        
        cpu_idle          = true
        startup_cpu_boost = true
      }
      
      # Environment variables
      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }
      
      # Database connection
      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
      
      env {
        name  = "REDIS_URL"
        value = var.redis_url
      }
      
      env {
        name  = "CLICKHOUSE_URL"
        value = var.clickhouse_url
      }
      
      # Secrets from Secret Manager
      dynamic "env" {
        for_each = var.secrets
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
      
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
        
        http_get {
          path = "/health"
          port = 8000
        }
      }
      
      liveness_probe {
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
        
        http_get {
          path = "/health"
          port = 8000
        }
      }
    }
    
    labels = var.labels
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = var.labels
}

# Cloud Run Frontend Service
resource "google_cloud_run_v2_service" "frontend" {
  name     = "staging-frontend-${var.environment_name}"
  location = var.region
  
  template {
    service_account = google_service_account.staging_frontend.email
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    timeout = "60s"
    
    containers {
      image = var.frontend_image
      
      ports {
        container_port = 3000
      }
      
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
        
        cpu_idle          = true
        startup_cpu_boost = true
      }
      
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = var.backend_url
      }
      
      env {
        name  = "NEXT_PUBLIC_WS_URL"
        value = replace(var.backend_url, "https://", "wss://")
      }
      
      # Additional environment variables
      dynamic "env" {
        for_each = var.environment_variables
        content {
          name  = env.key
          value = env.value
        }
      }
      
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
        
        http_get {
          path = "/"
          port = 3000
        }
      }
      
      liveness_probe {
        initial_delay_seconds = 30
        timeout_seconds       = 3
        period_seconds        = 30
        failure_threshold     = 3
        
        http_get {
          path = "/"
          port = 3000
        }
      }
    }
    
    labels = var.labels
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  labels = var.labels
}

# Service Accounts
resource "google_service_account" "staging_backend" {
  account_id   = "staging-backend-${var.environment_name}"
  display_name = "Staging Backend Service Account for ${var.environment_name}"
}

resource "google_service_account" "staging_frontend" {
  account_id   = "staging-frontend-${var.environment_name}"
  display_name = "Staging Frontend Service Account for ${var.environment_name}"
}

# IAM bindings for backend
resource "google_project_iam_member" "backend_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.staging_backend.email}"
}

resource "google_project_iam_member" "backend_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.staging_backend.email}"
}

resource "google_project_iam_member" "backend_redis_editor" {
  project = var.project_id
  role    = "roles/redis.editor"
  member  = "serviceAccount:${google_service_account.staging_backend.email}"
}

# Allow unauthenticated access (will be protected by OAuth)
resource "google_cloud_run_service_iam_member" "backend_invoker" {
  location = google_cloud_run_v2_service.backend.location
  service  = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_invoker" {
  location = google_cloud_run_v2_service.frontend.location
  service  = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Network Endpoint Groups for Load Balancer
resource "google_compute_region_network_endpoint_group" "backend" {
  name                  = "staging-backend-neg-${var.environment_name}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_v2_service.backend.name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend" {
  name                  = "staging-frontend-neg-${var.environment_name}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }
}

# Backend services for load balancer
resource "google_compute_backend_service" "backend" {
  name                  = "staging-backend-service-${var.environment_name}"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.backend.id
  }
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_backend_service" "frontend" {
  name                  = "staging-frontend-service-${var.environment_name}"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.frontend.id
  }
  
  # Enable CDN for frontend static assets
  enable_cdn = true
  
  cdn_policy {
    cache_mode = "CACHE_ALL_STATIC"
    
    default_ttl = 3600
    max_ttl     = 86400
    
    negative_caching = true
    
    negative_caching_policy {
      code = 404
      ttl  = 120
    }
  }
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}