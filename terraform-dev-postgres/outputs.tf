# Outputs for Development PostgreSQL Infrastructure

output "postgres_connection_string" {
  description = "PostgreSQL connection string for asyncpg"
  value       = "postgresql+asyncpg://${var.postgres_user}:${random_password.postgres_password.result}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive   = true
}

output "postgres_sync_connection_string" {
  description = "PostgreSQL connection string for synchronous connections"
  value       = "postgresql://${var.postgres_user}:${random_password.postgres_password.result}@localhost:${var.postgres_port}/${var.postgres_db}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://localhost:${var.redis_port}/0"
}

output "clickhouse_connection_string" {
  description = "ClickHouse connection string"
  value       = "clickhouse://${var.clickhouse_user}:${var.clickhouse_password}@localhost:${var.clickhouse_native_port}/${var.clickhouse_db}"
  sensitive   = true
}

output "postgres_host" {
  description = "PostgreSQL host"
  value       = "localhost"
}

output "postgres_port" {
  description = "PostgreSQL port"
  value       = var.postgres_port
}

output "postgres_database" {
  description = "PostgreSQL database name"
  value       = var.postgres_db
}

output "postgres_user" {
  description = "PostgreSQL user"
  value       = var.postgres_user
}

output "postgres_password" {
  description = "PostgreSQL password"
  value       = random_password.postgres_password.result
  sensitive   = true
}

output "app_user" {
  description = "Application database user"
  value       = var.app_user
}

output "app_password" {
  description = "Application user password"
  value       = random_password.app_password.result
  sensitive   = true
}

output "redis_host" {
  description = "Redis host"
  value       = "localhost"
}

output "redis_port" {
  description = "Redis port"
  value       = var.redis_port
}

output "clickhouse_host" {
  description = "ClickHouse host"
  value       = "localhost"
}

output "clickhouse_http_port" {
  description = "ClickHouse HTTP port"
  value       = var.clickhouse_http_port
}

output "clickhouse_native_port" {
  description = "ClickHouse native port"
  value       = var.clickhouse_native_port
}

output "docker_network" {
  description = "Docker network name for containers"
  value       = docker_network.netra_dev.name
}

output "postgres_container_name" {
  description = "PostgreSQL container name"
  value       = docker_container.postgres_dev.name
}

output "redis_container_name" {
  description = "Redis container name"
  value       = docker_container.redis_dev.name
}

output "clickhouse_container_name" {
  description = "ClickHouse container name"
  value       = docker_container.clickhouse_dev.name
}

output "jwt_secret" {
  description = "JWT Secret for authentication"
  value       = random_password.jwt_secret.result
  sensitive   = true
}

output "secret_key" {
  description = "Application secret key"
  value       = random_password.secret_key.result
  sensitive   = true
}

output "env_file_path" {
  description = "Path to generated environment file"
  value       = local_file.env_file.filename
}

output "connection_info_file" {
  description = "Path to connection information file"
  value       = local_file.connection_info.filename
}