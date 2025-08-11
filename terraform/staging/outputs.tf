output "frontend_url" {
  description = "Frontend application URL"
  value       = "https://${local.frontend_subdomain}.${var.domain}"
}

output "backend_url" {
  description = "Backend API URL"
  value       = "https://${local.backend_subdomain}.${var.domain}"
}

output "database_host" {
  description = "Database host"
  value       = module.database.database_host
  sensitive   = true
}

output "redis_host" {
  description = "Redis host"
  value       = module.database.redis_host
  sensitive   = true
}

output "environment_name" {
  description = "Environment name"
  value       = local.environment_name
}

output "load_balancer_ip" {
  description = "Load balancer IP address"
  value       = google_compute_global_address.staging.address
}

output "monitoring_dashboard_url" {
  description = "Cloud Console monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/staging-${local.environment_name}?project=${var.project_id}"
}

output "logs_url" {
  description = "Cloud Logging URL"
  value       = "https://console.cloud.google.com/logs/query;query=resource.labels.service_name%3D%22staging-${local.environment_name}%22?project=${var.project_id}"
}

output "created_at" {
  description = "Timestamp when environment was created"
  value       = timestamp()
}

output "expires_at" {
  description = "Timestamp when environment will expire"
  value       = timeadd(timestamp(), "${var.ttl_hours}h")
}