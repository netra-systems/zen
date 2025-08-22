# Variables for Development PostgreSQL Infrastructure

variable "docker_host" {
  description = "Docker daemon host"
  type        = string
  default     = "npipe:////./pipe/docker_engine" # Windows default
  # For Linux/Mac, use: "unix:///var/run/docker.sock"
}

variable "postgres_version" {
  description = "PostgreSQL Docker image version"
  type        = string
  default     = "17.6-alpine"
}

variable "postgres_port" {
  description = "External port for PostgreSQL"
  type        = number
  default     = 5432
}

variable "postgres_db" {
  description = "PostgreSQL database name"
  type        = string
  default     = "netra_dev"
}

variable "postgres_user" {
  description = "PostgreSQL superuser name"
  type        = string
  default     = "postgres"
}

variable "app_user" {
  description = "Application database user"
  type        = string
  default     = "netra_app"
}

variable "redis_version" {
  description = "Redis Docker image version"
  type        = string
  default     = "7-alpine"
}

variable "redis_port" {
  description = "External port for Redis"
  type        = number
  default     = 6379
}

variable "clickhouse_version" {
  description = "ClickHouse Docker image version"
  type        = string
  default     = "latest"
}

variable "clickhouse_http_port" {
  description = "External HTTP port for ClickHouse"
  type        = number
  default     = 8123
}

variable "clickhouse_native_port" {
  description = "External native port for ClickHouse"
  type        = number
  default     = 9000
}

variable "clickhouse_db" {
  description = "ClickHouse database name"
  type        = string
  default     = "netra_dev"
}

variable "clickhouse_user" {
  description = "ClickHouse user name"
  type        = string
  default     = "default"
}

variable "clickhouse_password" {
  description = "ClickHouse password"
  type        = string
  default     = "netra_dev_password"
  sensitive   = true
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "development"
}

variable "enable_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = false
}

variable "backup_schedule" {
  description = "Backup schedule in cron format"
  type        = string
  default     = "0 2 * * *" # Daily at 2 AM
}

variable "max_connections" {
  description = "Maximum number of PostgreSQL connections"
  type        = number
  default     = 100
}

variable "shared_buffers" {
  description = "PostgreSQL shared buffers size"
  type        = string
  default     = "256MB"
}

variable "work_mem" {
  description = "PostgreSQL work memory size"
  type        = string
  default     = "4MB"
}