# GitHub Runner on Cloud Run with Terraform
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com"
  ])
  
  service            = each.value
  disable_on_destroy = false
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "runner_images" {
  location      = var.region
  repository_id = "github-runners"
  description   = "Docker images for GitHub Actions runners"
  format        = "DOCKER"
  
  depends_on = [google_project_service.required_apis]
}

# Service account for Cloud Run
resource "google_service_account" "runner_sa" {
  account_id   = "github-runner-cloudrun"
  display_name = "GitHub Runner Cloud Run Service Account"
}

# IAM roles
resource "google_project_iam_member" "runner_roles" {
  for_each = toset([
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runner_sa.email}"
}

# Secret for GitHub token
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-runner-token"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
}

resource "google_secret_manager_secret_iam_member" "token_accessor" {
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runner_sa.email}"
}

# Cloud Build trigger for building Docker image
resource "google_cloudbuild_trigger" "build_runner_image" {
  name        = "build-github-runner"
  description = "Build GitHub Runner Docker image"
  
  github {
    owner = var.github_org
    name  = var.github_repo
    push {
      branch = "^main$"
    }
  }
  
  included_files = ["terraform-gcp/github-runner/docker/**"]
  
  build {
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "build",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner:$COMMIT_SHA",
        "-t", "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner:latest",
        "-f", "terraform-gcp/github-runner/docker/Dockerfile",
        "terraform-gcp/github-runner/docker"
      ]
    }
    
    step {
      name = "gcr.io/cloud-builders/docker"
      args = [
        "push",
        "--all-tags",
        "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner"
      ]
    }
    
    step {
      name = "gcr.io/google.com/cloudsdktool/cloud-sdk"
      entrypoint = "gcloud"
      args = [
        "run",
        "deploy",
        google_cloud_run_v2_service.github_runner.name,
        "--image", "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner:$COMMIT_SHA",
        "--region", var.region
      ]
    }
  }
  
  depends_on = [
    google_artifact_registry_repository.runner_images,
    google_project_service.required_apis
  ]
}

# Cloud Run service
resource "google_cloud_run_v2_service" "github_runner" {
  name     = "github-runner"
  location = var.region
  
  template {
    service_account = google_service_account.runner_sa.email
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner:latest"
      
      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true
      }
      
      env {
        name  = "GITHUB_ORG"
        value = var.github_org
      }
      
      env {
        name  = "GITHUB_REPO"
        value = var.github_repo
      }
      
      env {
        name  = "RUNNER_NAME"
        value = var.runner_name
      }
      
      env {
        name  = "RUNNER_LABELS"
        value = join(",", var.runner_labels)
      }
      
      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.github_token.secret_id
            version = "latest"
          }
        }
      }
      
      # Note: Docker socket mounting not supported in Cloud Run
      # Would need to use Cloud Build or GKE for Docker support
    }
    
    # Note: Cloud Run v2 doesn't support empty_dir volumes
    # Docker support would require a different approach
    
    timeout = "3600s"
  }
  
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.github_token,
    google_secret_manager_secret_iam_member.token_accessor
  ]
}

# Cloud Scheduler for keeping runners alive (optional)
resource "google_cloud_scheduler_job" "runner_keepalive" {
  count = var.enable_keepalive ? 1 : 0
  
  name        = "github-runner-keepalive"
  description = "Keep GitHub runners warm"
  schedule    = "*/5 * * * *"  # Every 5 minutes
  
  http_target {
    uri         = google_cloud_run_v2_service.github_runner.uri
    http_method = "GET"
    
    oidc_token {
      service_account_email = google_service_account.runner_sa.email
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Outputs
output "service_url" {
  value       = google_cloud_run_v2_service.github_runner.uri
  description = "URL of the Cloud Run service"
}

output "image_repository" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/github-runners/runner"
  description = "Docker image repository URL"
}

output "build_trigger" {
  value       = google_cloudbuild_trigger.build_runner_image.id
  description = "Cloud Build trigger ID"
}