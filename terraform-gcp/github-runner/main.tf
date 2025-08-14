# GitHub Actions Self-Hosted Runner on GCP
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
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "compute" {
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Service account for GitHub Runner
resource "google_service_account" "github_runner" {
  account_id   = "github-runner-sa"
  display_name = "GitHub Actions Runner Service Account"
  description  = "Service account for GitHub Actions self-hosted runner"
}

# IAM roles for the service account
resource "google_project_iam_member" "runner_compute" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin"
  member  = "serviceAccount:${google_service_account.github_runner.email}"
}

resource "google_project_iam_member" "runner_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.github_runner.email}"
}

resource "google_project_iam_member" "runner_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.github_runner.email}"
}

resource "google_project_iam_member" "runner_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.github_runner.email}"
}

# Secret for GitHub Personal Access Token
resource "google_secret_manager_secret" "github_token" {
  project   = var.project_id  # EXPLICIT project specification
  secret_id = "github-runner-token"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_version" "github_token" {
  secret      = google_secret_manager_secret.github_token.id
  secret_data = var.github_token
  
  lifecycle {
    create_before_destroy = true
    precondition {
      condition     = var.github_token != "" && var.github_token != null
      error_message = "GitHub token is required. Please set TF_VAR_github_token environment variable with a valid GitHub PAT."
    }
  }
  
  depends_on = [google_secret_manager_secret.github_token]
}

# IAM for accessing the secret
resource "google_secret_manager_secret_iam_member" "github_token_access" {
  project   = var.project_id  # EXPLICIT project specification
  secret_id = google_secret_manager_secret.github_token.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.github_runner.email}"
  
  depends_on = [
    google_secret_manager_secret.github_token,
    google_secret_manager_secret_version.github_token,
    google_service_account.github_runner
  ]
}

# Firewall rule for SSH (optional, for debugging)
resource "google_compute_firewall" "github_runner_ssh" {
  count = var.enable_ssh ? 1 : 0
  
  name    = "github-runner-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.ssh_source_ranges
  target_tags   = ["github-runner"]
}

# Startup script for the runner
locals {
  startup_script = templatefile("${path.module}/scripts/install-runner.sh", {
    github_org        = var.github_org
    github_repo       = var.github_repo
    runner_name       = var.runner_name
    runner_labels     = join(",", var.runner_labels)
    runner_group      = var.runner_group
    project_id        = var.project_id
    runner_version    = var.runner_version
  })
  
  # Additional script to ensure Docker is ready
  docker_fix_script = file("${path.module}/scripts/fix-docker-daemon.sh")
}

# Compute instance for GitHub Runner
resource "google_compute_instance" "github_runner" {
  count = var.runner_count
  
  name         = "${var.runner_name}-${count.index + 1}"
  machine_type = var.machine_type
  zone         = var.zone

  tags = ["github-runner"]

  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = var.boot_disk_size
      type  = var.boot_disk_type
    }
  }

  network_interface {
    network = "default"
    
    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    email  = google_service_account.github_runner.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = local.startup_script

  metadata = {
    enable-oslogin = "TRUE"
    github-org     = var.github_org
    github-repo    = var.github_repo
  }

  scheduling {
    preemptible       = var.use_preemptible
    automatic_restart = !var.use_preemptible
    on_host_maintenance = var.use_preemptible ? "TERMINATE" : "MIGRATE"
  }

  labels = {
    environment = var.environment
    purpose     = "github-runner"
    managed-by  = "terraform"
  }

  depends_on = [
    google_project_service.compute,
    google_secret_manager_secret_version.github_token,
    google_secret_manager_secret_iam_member.github_token_access
  ]
}

# Instance group for auto-scaling (optional)
resource "google_compute_instance_template" "github_runner" {
  count = var.enable_autoscaling ? 1 : 0
  
  name_prefix  = "github-runner-template-"
  machine_type = var.machine_type
  region       = var.region

  disk {
    source_image = var.boot_disk_image
    auto_delete  = true
    boot         = true
    disk_size_gb = var.boot_disk_size
    disk_type    = var.boot_disk_type
  }

  network_interface {
    network = "default"
    
    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    email  = google_service_account.github_runner.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = local.startup_script

  metadata = {
    enable-oslogin = "TRUE"
    github-org     = var.github_org
    github-repo    = var.github_repo
  }

  scheduling {
    preemptible       = var.use_preemptible
    automatic_restart = !var.use_preemptible
    on_host_maintenance = var.use_preemptible ? "TERMINATE" : "MIGRATE"
  }

  tags = ["github-runner"]

  labels = {
    environment = var.environment
    purpose     = "github-runner"
    managed-by  = "terraform"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Instance group manager for auto-scaling
resource "google_compute_instance_group_manager" "github_runner" {
  count = var.enable_autoscaling ? 1 : 0
  
  name               = "github-runner-group"
  base_instance_name = var.runner_name
  zone               = var.zone

  version {
    instance_template = google_compute_instance_template.github_runner[0].id
  }

  target_size = var.min_runners

  named_port {
    name = "http"
    port = 8080
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto-scaler for the instance group
resource "google_compute_autoscaler" "github_runner" {
  count = var.enable_autoscaling ? 1 : 0
  
  name   = "github-runner-autoscaler"
  zone   = var.zone
  target = google_compute_instance_group_manager.github_runner[0].id

  autoscaling_policy {
    max_replicas    = var.max_runners
    min_replicas    = var.min_runners
    cooldown_period = 60

    cpu_utilization {
      target = 0.8
    }
  }
}

# Storage bucket for runner artifacts
resource "google_storage_bucket" "runner_artifacts" {
  name          = "${var.project_id}-github-runner-artifacts"
  location      = var.region
  force_destroy = true

  lifecycle_rule {
    condition {
      age = var.artifact_retention_days
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = false
  }

  uniform_bucket_level_access = true
}

# IAM for bucket access
resource "google_storage_bucket_iam_member" "runner_artifacts" {
  bucket = google_storage_bucket.runner_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_runner.email}"
}