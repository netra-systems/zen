variable "environment_name" {
  description = "Name of the staging environment"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "vpc_network_id" {
  description = "VPC network ID for private connectivity"
  type        = string
}

variable "postgres_tier" {
  description = "Machine type for PostgreSQL instance"
  type        = string
  default     = "db-f1-micro"
}

variable "postgres_disk_size" {
  description = "Disk size for PostgreSQL in GB"
  type        = number
  default     = 20
}

variable "postgres_password" {
  description = "Password for PostgreSQL user"
  type        = string
  sensitive   = true
}

variable "redis_tier" {
  description = "Redis tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "BASIC"
}

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
}

variable "clickhouse_connection_string" {
  description = "ClickHouse connection string (provided from external dev environment)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "authorized_networks" {
  description = "List of authorized networks for database access"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "enable_backups" {
  description = "Enable database backups"
  type        = bool
  default     = true
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery for PostgreSQL"
  type        = bool
  default     = false
}

variable "require_ssl" {
  description = "Require SSL for database connections"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection for databases"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default     = {}
}