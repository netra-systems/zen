# clickhouse.tf - ClickHouse deployment on GCP using Compute Engine
# Budget-optimized single-node deployment for analytics

# ClickHouse VM Instance
resource "google_compute_instance" "clickhouse" {
  name         = "netra-clickhouse-${var.environment}"
  machine_type = var.environment == "production" ? "e2-standard-4" : "e2-medium"
  zone         = var.zone

  tags = ["clickhouse", "allow-http", "allow-https", "allow-clickhouse"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = var.environment == "production" ? 100 : 50
      type  = "pd-standard"
    }
  }

  # Additional disk for ClickHouse data
  attached_disk {
    source      = google_compute_disk.clickhouse_data.self_link
    device_name = "clickhouse-data"
  }

  network_interface {
    network = "default"
    
    access_config {
      # Ephemeral public IP
    }
  }

  metadata_startup_script = templatefile("${path.module}/scripts/clickhouse-startup.sh", {
    environment = var.environment
    project_id  = var.project_id
  })

  service_account {
    email  = google_service_account.clickhouse.email
    scopes = ["cloud-platform"]
  }

  depends_on = [google_project_service.apis]
}

# Persistent disk for ClickHouse data
resource "google_compute_disk" "clickhouse_data" {
  name = "netra-clickhouse-data-${var.environment}"
  type = "pd-standard"
  zone = var.zone
  size = var.environment == "production" ? 500 : 100
  
  lifecycle {
    prevent_destroy = false
  }
}

# Service Account for ClickHouse
resource "google_service_account" "clickhouse" {
  account_id   = "netra-clickhouse-${var.environment}"
  display_name = "Netra ClickHouse Service Account"
}

# IAM permissions for ClickHouse
resource "google_project_iam_member" "clickhouse_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.clickhouse.email}"
}

resource "google_project_iam_member" "clickhouse_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.clickhouse.email}"
}

# Firewall rule for ClickHouse HTTP interface
resource "google_compute_firewall" "clickhouse_http" {
  name    = "allow-clickhouse-http-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8123"]
  }

  source_ranges = var.environment == "production" ? [
    google_cloud_run_service.backend.status[0].url
  ] : ["0.0.0.0/0"]

  target_tags = ["clickhouse"]
}

# Firewall rule for ClickHouse native protocol
resource "google_compute_firewall" "clickhouse_native" {
  name    = "allow-clickhouse-native-${var.environment}"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["9000"]
  }

  source_ranges = var.environment == "production" ? [
    google_cloud_run_service.backend.status[0].url
  ] : ["0.0.0.0/0"]

  target_tags = ["clickhouse"]
}

# Cloud Storage bucket for ClickHouse backups
resource "google_storage_bucket" "clickhouse_backups" {
  name          = "${var.project_id}-clickhouse-backups-${var.environment}"
  location      = var.region
  force_destroy = var.environment != "production"

  lifecycle_rule {
    condition {
      age = var.environment == "production" ? 30 : 7
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = var.environment == "production"
  }
}

# Grant ClickHouse access to backup bucket
resource "google_storage_bucket_iam_member" "clickhouse_backup_access" {
  bucket = google_storage_bucket.clickhouse_backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.clickhouse.email}"
}

# Output ClickHouse connection details
output "clickhouse_internal_ip" {
  value       = google_compute_instance.clickhouse.network_interface[0].network_ip
  description = "Internal IP address of ClickHouse instance"
}

output "clickhouse_external_ip" {
  value       = google_compute_instance.clickhouse.network_interface[0].access_config[0].nat_ip
  description = "External IP address of ClickHouse instance"
  sensitive   = true
}

output "clickhouse_http_url" {
  value       = "http://${google_compute_instance.clickhouse.network_interface[0].network_ip}:8123"
  description = "ClickHouse HTTP interface URL (internal)"
}

output "clickhouse_backup_bucket" {
  value       = google_storage_bucket.clickhouse_backups.name
  description = "GCS bucket for ClickHouse backups"
}