variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "environment_name" {
  type = string
}

variable "resource_suffix" {
  type = string
}

variable "backend_image" {
  type = string
}

variable "frontend_image" {
  type = string
}

variable "vpc_connector_id" {
  type = string
}

variable "backend_url" {
  type = string
}

variable "frontend_url" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}

variable "clickhouse_url" {
  type      = string
  sensitive = true
}

variable "ssl_certificate_id" {
  type = string
}

variable "cpu_limit" {
  type = string
}

variable "memory_limit" {
  type = string
}

variable "min_instances" {
  type = number
}

variable "max_instances" {
  type = number
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "secrets" {
  type    = map(string)
  default = {}
}

variable "labels" {
  type = map(string)
}