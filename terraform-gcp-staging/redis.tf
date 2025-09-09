# Google Cloud Memorystore for Redis

# Redis Instance
resource "google_redis_instance" "redis" {
  name           = local.redis_instance_name
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_size_gb
  region         = var.region
  project        = var.project_id
  redis_version  = var.redis_version
  display_name   = "${var.environment} Redis Instance"

  # Use the same VPC as Cloud SQL if private IP is enabled
  authorized_network = var.enable_private_ip ? google_compute_network.vpc[0].id : null

  # Redis configuration
  redis_configs = {
    "maxmemory-policy"       = "allkeys-lru"
    "notify-keyspace-events" = "Ex"
  }

  # Maintenance policy
  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time {
        hours   = 3
        minutes = 0
        seconds = 0
        nanos   = 0
      }
    }
  }

  labels = var.labels

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}