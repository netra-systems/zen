# Optimized Staging Terraform Configuration
# Addresses slow planning issues and uses shared infrastructure efficiently

terraform {
  required_version = ">= 1.5.0"
  
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
    # Configured dynamically in CI/CD
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Use data source with count to conditionally read remote state
# This avoids unnecessary API calls during destroy operations
data "terraform_remote_state" "shared" {
  count   = var.action == "destroy" ? 0 : 1
  backend = "gcs"
  config = {
    bucket = "${var.project_id}-terraform-state"
    prefix = "staging/shared-infrastructure"
  }
}

locals {
  environment_name = "pr-${var.pr_number}"
  
  # Handle conditional remote state access
  has_shared = length(data.terraform_remote_state.shared) > 0
  
  # Use try() to gracefully handle missing remote state
  vpc_id                  = try(data.terraform_remote_state.shared[0].outputs.vpc_id, "")
  vpc_connector_id        = try(data.terraform_remote_state.shared[0].outputs.vpc_connector_id, "")
  sql_instance_name       = try(data.terraform_remote_state.shared[0].outputs.sql_instance_name, "staging-shared-postgres")
  sql_instance_connection = try(data.terraform_remote_state.shared[0].outputs.sql_instance_connection, "${var.project_id}:${var.region}:staging-shared-postgres")
  redis_host              = try(data.terraform_remote_state.shared[0].outputs.redis_host, "10.0.0.10")
  redis_port              = try(data.terraform_remote_state.shared[0].outputs.redis_port, 6379)
  service_account         = try(data.terraform_remote_state.shared[0].outputs.service_account_email, "staging-sa@${var.project_id}.iam.gserviceaccount.com")
  
  # Calculate Redis DB index
  redis_db_index = tonumber(regex("[0-9]+", var.pr_number)) % 16
}

# Generate random password if not provided
resource "random_password" "postgres" {
  count   = var.postgres_password == "" ? 1 : 0
  length  = 32
  special = true
}

# Database resources - these are fast to create/destroy
resource "google_sql_database" "pr" {
  count    = var.action != "destroy" ? 1 : 0
  name     = "netra_${replace(local.environment_name, "-", "_")}"
  instance = local.sql_instance_name
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_sql_user" "pr" {
  count    = var.action != "destroy" ? 1 : 0
  name     = "user_${replace(local.environment_name, "-", "_")}"
  instance = local.sql_instance_name
  password = coalesce(var.postgres_password, try(random_password.postgres[0].result, "staging-default-password"))
  
  lifecycle {
    create_before_destroy = true
  }
}

# Cloud Run Backend Service
resource "google_cloud_run_v2_service" "backend" {
  count    = var.action != "destroy" ? 1 : 0
  name     = "backend-${local.environment_name}"
  location = var.region
  
  template {
    service_account = local.service_account
    
    # Use higher parallelism for faster startup
    max_instance_request_concurrency = 100
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    vpc_access {
      connector = local.vpc_connector_id
      egress    = "ALL_TRAFFIC"
    }
    
    containers {
      image = var.backend_image
      
      ports {
        container_port = 8080
      }
      
      # Optimized resource allocation
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
        for_each = {
          DATABASE_URL = "postgresql://${try(google_sql_user.pr[0].name, "")}:${coalesce(var.postgres_password, try(random_password.postgres[0].result, ""))}@/${try(google_sql_database.pr[0].name, "")}?host=/cloudsql/${local.sql_instance_connection}&sslmode=disable"
          REDIS_URL    = "redis://${local.redis_host}:${local.redis_port}/${local.redis_db_index}"
          REDIS_HOST   = local.redis_host
          REDIS_PORT   = tostring(local.redis_port)
          REDIS_DB     = tostring(local.redis_db_index)
          PR_NUMBER    = var.pr_number
          ENVIRONMENT  = "staging"
          
          # ClickHouse configuration
          CLICKHOUSE_URL      = coalesce(var.clickhouse_url, "clickhouse://default:${var.clickhouse_password}@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=1")
          CLICKHOUSE_HOST     = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
          CLICKHOUSE_PORT     = "8443"
          CLICKHOUSE_SECURE   = "true"
          CLICKHOUSE_TIMEOUT  = "60"
          CLICKHOUSE_PASSWORD = var.clickhouse_password
          CLICKHOUSE_USER     = "default"
          
          # GCP configuration
          GCP_PROJECT_ID                  = var.project_id
          GCP_PROJECT_ID_NUMERICAL_STAGING = var.project_id_numerical
          SECRET_MANAGER_PROJECT          = var.project_id
          LOAD_SECRETS                    = "true"
          
          # Database settings
          POSTGRES_HOST     = "/cloudsql/${local.sql_instance_connection}"
          POSTGRES_DB       = try(google_sql_database.pr[0].name, "")
          POSTGRES_USER     = try(google_sql_user.pr[0].name, "")
          POSTGRES_PASSWORD = coalesce(var.postgres_password, try(random_password.postgres[0].result, ""))
          
          # Auth configuration
          JWT_SECRET_KEY = coalesce(var.jwt_secret_key, "staging-jwt-secret-key-${var.pr_number}")
          FERNET_KEY     = coalesce(var.fernet_key, "ZmVybmV0LXN0YWdpbmcta2V5LXBsYWNlaG9sZGVyLTEyMw==")
          GEMINI_API_KEY = coalesce(var.gemini_api_key, "staging-gemini-api-key-placeholder")
          
          # Performance settings
          SKIP_MIGRATION_ON_STARTUP    = "true"
          SKIP_CLICKHOUSE_INIT        = "false"
          CLICKHOUSE_CONNECT_TIMEOUT  = "30"
          LOG_LEVEL                   = "INFO"
        }
        content {
          name  = env.key
          value = env.value
        }
      }
      
      # Optimized health checks
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 10
        
        http_get {
          path = "/health"
          port = 8080
        }
      }
      
      liveness_probe {
        initial_delay_seconds = 30
        timeout_seconds       = 5
        period_seconds        = 30
        failure_threshold     = 3
        
        http_get {
          path = "/health"
          port = 8080
        }
      }
    }
    
    # Cloud SQL connection
    annotations = {
      "run.googleapis.com/cloudsql-instances" = local.sql_instance_connection
    }
  }
  
  # Fast provisioning settings
  lifecycle {
    create_before_destroy = false
    ignore_changes        = [template[0].annotations["run.googleapis.com/client-name"]]
  }
  
  timeouts {
    create = "3m"
    update = "3m"
    delete = "1m"
  }
}

# Cloud Run Frontend Service
resource "google_cloud_run_v2_service" "frontend" {
  count    = var.action != "destroy" ? 1 : 0
  name     = "frontend-${local.environment_name}"
  location = var.region
  
  template {
    service_account = local.service_account
    
    max_instance_request_concurrency = 100
    
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
    
    containers {
      image = var.frontend_image
      
      ports {
        container_port = 8080
      }
      
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
      
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = try(google_cloud_run_v2_service.backend[0].uri, "")
      }
      
      startup_probe {
        initial_delay_seconds = 10
        timeout_seconds       = 5
        period_seconds        = 5
        failure_threshold     = 10
        
        http_get {
          path = "/"
          port = 8080
        }
      }
    }
  }
  
  lifecycle {
    create_before_destroy = false
    ignore_changes        = [template[0].annotations["run.googleapis.com/client-name"]]
  }
  
  timeouts {
    create = "3m"
    update = "3m"
    delete = "1m"
  }
}

# IAM bindings for public access
resource "google_cloud_run_service_iam_member" "backend_public" {
  count    = var.action != "destroy" ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.backend[0].location
  service  = google_cloud_run_v2_service.backend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "frontend_public" {
  count    = var.action != "destroy" ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.frontend[0].location
  service  = google_cloud_run_v2_service.frontend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "frontend_url" {
  value = try(google_cloud_run_v2_service.frontend[0].uri, "")
}

output "backend_url" {
  value = try(google_cloud_run_v2_service.backend[0].uri, "")
}

output "database_name" {
  value = try(google_sql_database.pr[0].name, "")
}

output "database_user" {
  value = try(google_sql_user.pr[0].name, "")
}

output "redis_db_index" {
  value = local.redis_db_index
}

output "deployment_info" {
  value = {
    environment = local.environment_name
    pr_number   = var.pr_number
    commit_sha  = var.commit_sha
    deployed_at = timestamp()
  }
}