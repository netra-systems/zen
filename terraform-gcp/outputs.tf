# outputs.tf - Output values from the infrastructure

output "frontend_url" {
  value       = google_cloud_run_service.frontend.status[0].url
  description = "Frontend application URL"
}

output "backend_url" {
  value       = google_cloud_run_service.backend.status[0].url
  description = "Backend API URL"
}

output "database_ip" {
  value       = google_sql_database_instance.postgres.public_ip_address
  description = "Database public IP address"
}

output "database_connection_name" {
  value       = google_sql_database_instance.postgres.connection_name
  description = "Database connection name for Cloud SQL proxy"
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers"
  description = "Container registry URL"
}

output "backup_bucket" {
  value       = google_storage_bucket.backups.name
  description = "GCS bucket for backups"
}

output "service_account_email" {
  value       = google_service_account.cloudrun.email
  description = "Cloud Run service account email"
}

output "database_name" {
  value       = google_sql_database.main.name
  description = "Database name"
}

output "database_user" {
  value       = google_sql_user.main.name
  description = "Database username"
  sensitive   = false
}

output "deployment_info" {
  value = {
    frontend_url    = google_cloud_run_service.frontend.status[0].url
    backend_url     = google_cloud_run_service.backend.status[0].url
    database_ip     = google_sql_database_instance.postgres.public_ip_address
    artifact_registry = "${var.region}-docker.pkg.dev/${var.project_id}/netra-containers"
    project_id      = var.project_id
    region          = var.region
  }
  description = "Complete deployment information"
}