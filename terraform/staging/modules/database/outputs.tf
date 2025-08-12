output "postgres_instance_name" {
  description = "Name of the PostgreSQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "postgres_connection_string" {
  description = "PostgreSQL connection string"
  value       = local.postgres_connection_string
  sensitive   = true
}

output "postgres_private_ip" {
  description = "Private IP address of PostgreSQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "postgres_public_ip" {
  description = "Public IP address of PostgreSQL instance"
  value       = google_sql_database_instance.postgres.public_ip_address
}

output "redis_instance_name" {
  description = "Name of the Redis instance"
  value       = google_redis_instance.cache.name
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = local.redis_connection_string
  sensitive   = true
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Redis port"
  value       = google_redis_instance.cache.port
}

output "clickhouse_connection_string" {
  description = "ClickHouse connection string (from external dev environment)"
  value       = local.clickhouse_connection_string
  sensitive   = true
}

output "database_secret_id" {
  description = "Secret Manager secret ID for database password"
  value       = google_secret_manager_secret.db_password.secret_id
}