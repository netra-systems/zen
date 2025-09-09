# Terraform Outputs

# Database Outputs
output "database_instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "database_connection_name" {
  description = "The connection name of the Cloud SQL instance for Cloud SQL proxy"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_public_ip" {
  description = "The public IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.public_ip_address
  sensitive   = false
}

output "database_private_ip" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = false
}

output "database_url_secret_id" {
  description = "The Secret Manager secret ID for the database URL"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "database_url_direct_secret_id" {
  description = "The Secret Manager secret ID for the direct database URL"
  value       = google_secret_manager_secret.database_url_direct.secret_id
}

# Redis Outputs
output "redis_host" {
  description = "The hostname of the Redis instance"
  value       = google_redis_instance.redis.host
}

output "redis_port" {
  description = "The port of the Redis instance"
  value       = google_redis_instance.redis.port
}

output "redis_url_secret_id" {
  description = "The Secret Manager secret ID for the Redis URL"
  value       = google_secret_manager_secret.redis_url.secret_id
}

# JWT Secret Output
output "jwt_secret_id" {
  description = "The Secret Manager secret ID for the JWT secret"
  value       = google_secret_manager_secret.jwt_secret.secret_id
}

# Connection Strings (marked as sensitive)
output "postgres_connection_string" {
  description = "PostgreSQL connection string for superuser"
  value       = local.postgres_connection_string
  sensitive   = true
}

output "app_connection_string" {
  description = "PostgreSQL connection string for application user"
  value       = local.app_connection_string
  sensitive   = true
}

output "cloudsql_connection_string" {
  description = "PostgreSQL connection string for Cloud SQL proxy"
  value       = local.cloudsql_connection_string
  sensitive   = true
}

# VPC Outputs (if private IP is enabled)
output "vpc_network_name" {
  description = "The name of the VPC network"
  value       = var.enable_private_ip ? google_compute_network.vpc[0].name : null
}

output "vpc_subnet_name" {
  description = "The name of the VPC subnet"
  value       = var.enable_private_ip ? google_compute_subnetwork.subnet[0].name : null
}

# State Bucket
output "terraform_state_bucket" {
  description = "The GCS bucket used for Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

# Project Information
output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

# Summary Output
output "deployment_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment        = var.environment
    postgres_version   = var.postgres_version
    database_tier      = var.database_tier
    redis_tier         = var.redis_tier
    backup_enabled     = var.backup_enabled
    private_ip_enabled = var.enable_private_ip
    public_ip_enabled  = var.enable_public_ip
  }
}