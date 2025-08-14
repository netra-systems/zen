# Development PostgreSQL Infrastructure
# Optimized for local development with automatic configuration

terraform {
  required_version = ">= 1.0"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

provider "docker" {
  host = var.docker_host
}

# Generate secure passwords
resource "random_password" "postgres_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_password" "app_password" {
  length  = 32
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Create Docker network for database
resource "docker_network" "netra_dev" {
  name = "netra-dev-network"
  driver = "bridge"
}

# PostgreSQL container
resource "docker_container" "postgres_dev" {
  name  = "netra-postgres-dev"
  image = docker_image.postgres.image_id
  
  restart = "unless-stopped"
  
  env = [
    "POSTGRES_DB=${var.postgres_db}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${random_password.postgres_password.result}",
    "POSTGRES_INITDB_ARGS=--encoding=UTF-8 --locale=en_US.UTF-8"
  ]
  
  ports {
    internal = 5432
    external = var.postgres_port
  }
  
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }
  
  volumes {
    host_path      = abspath("${path.module}/init-scripts")
    container_path = "/docker-entrypoint-initdb.d"
    read_only      = true
  }
  
  networks_advanced {
    name = docker_network.netra_dev.name
    aliases = ["postgres-dev"]
  }
  
  healthcheck {
    test         = ["CMD-SHELL", "pg_isready -U ${var.postgres_user} -d ${var.postgres_db}"]
    interval     = "10s"
    timeout      = "5s"
    retries      = 5
    start_period = "30s"
  }
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# Pull PostgreSQL image
resource "docker_image" "postgres" {
  name = "postgres:${var.postgres_version}"
  keep_locally = true
}

# Volume for persistent data
resource "docker_volume" "postgres_data" {
  name = "netra-postgres-dev-data"
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# Redis container for development
resource "docker_container" "redis_dev" {
  name  = "netra-redis-dev"
  image = docker_image.redis.image_id
  
  restart = "unless-stopped"
  
  command = ["redis-server", "--appendonly", "yes"]
  
  ports {
    internal = 6379
    external = var.redis_port
  }
  
  volumes {
    volume_name    = docker_volume.redis_data.name
    container_path = "/data"
  }
  
  networks_advanced {
    name = docker_network.netra_dev.name
    aliases = ["redis-dev"]
  }
  
  healthcheck {
    test         = ["CMD", "redis-cli", "ping"]
    interval     = "10s"
    timeout      = "5s"
    retries      = 5
    start_period = "10s"
  }
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# Pull Redis image
resource "docker_image" "redis" {
  name = "redis:${var.redis_version}"
  keep_locally = true
}

# Volume for Redis data
resource "docker_volume" "redis_data" {
  name = "netra-redis-dev-data"
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# ClickHouse container for development
resource "docker_container" "clickhouse_dev" {
  name  = "netra-clickhouse-dev"
  image = docker_image.clickhouse.image_id
  
  restart = "unless-stopped"
  
  env = [
    "CLICKHOUSE_DB=${var.clickhouse_db}",
    "CLICKHOUSE_USER=${var.clickhouse_user}",
    "CLICKHOUSE_PASSWORD=${var.clickhouse_password}",
    "CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT=1"
  ]
  
  ports {
    internal = 8123
    external = var.clickhouse_http_port
  }
  
  ports {
    internal = 9000
    external = var.clickhouse_native_port
  }
  
  volumes {
    volume_name    = docker_volume.clickhouse_data.name
    container_path = "/var/lib/clickhouse"
  }
  
  networks_advanced {
    name = docker_network.netra_dev.name
    aliases = ["clickhouse-dev"]
  }
  
  healthcheck {
    test         = ["CMD", "wget", "--spider", "-q", "http://localhost:8123/ping"]
    interval     = "10s"
    timeout      = "5s"
    retries      = 5
    start_period = "30s"
  }
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# Pull ClickHouse image
resource "docker_image" "clickhouse" {
  name = "clickhouse/clickhouse-server:${var.clickhouse_version}"
  keep_locally = true
}

# Volume for ClickHouse data
resource "docker_volume" "clickhouse_data" {
  name = "netra-clickhouse-dev-data"
  
  labels {
    label = "environment"
    value = "development"
  }
  
  labels {
    label = "project"
    value = "netra"
  }
}

# Generate .env.development.local with connection strings
resource "local_file" "env_file" {
  filename = "${path.module}/../.env.development.local"
  content  = templatefile("${path.module}/templates/env.development.tpl", {
    postgres_host     = "localhost"
    postgres_port     = var.postgres_port
    postgres_db       = var.postgres_db
    postgres_user     = var.postgres_user
    postgres_password = random_password.postgres_password.result
    app_user          = var.app_user
    app_password      = random_password.app_password.result
    redis_host        = "localhost"
    redis_port        = var.redis_port
    clickhouse_host   = "localhost"
    clickhouse_http_port = var.clickhouse_http_port
    clickhouse_native_port = var.clickhouse_native_port
    clickhouse_db     = var.clickhouse_db
    clickhouse_user   = var.clickhouse_user
    clickhouse_password = var.clickhouse_password
    jwt_secret        = random_password.jwt_secret.result
    secret_key        = random_password.secret_key.result
  })
  
  depends_on = [
    docker_container.postgres_dev,
    docker_container.redis_dev,
    docker_container.clickhouse_dev
  ]
}

# Generate random JWT secret
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

# Generate random secret key
resource "random_password" "secret_key" {
  length  = 64
  special = false
}

# Output connection information
resource "local_file" "connection_info" {
  filename = "${path.module}/connection_info.txt"
  content  = <<-EOT
    Development Database Connection Information
    ==========================================
    
    PostgreSQL:
    - Host: localhost
    - Port: ${var.postgres_port}
    - Database: ${var.postgres_db}
    - User: ${var.postgres_user}
    - Password: ${random_password.postgres_password.result}
    - Connection String: postgresql+asyncpg://${var.postgres_user}:${random_password.postgres_password.result}@localhost:${var.postgres_port}/${var.postgres_db}
    
    Redis:
    - Host: localhost
    - Port: ${var.redis_port}
    - Connection String: redis://localhost:${var.redis_port}/0
    
    ClickHouse:
    - Host: localhost
    - HTTP Port: ${var.clickhouse_http_port}
    - Native Port: ${var.clickhouse_native_port}
    - Database: ${var.clickhouse_db}
    - User: ${var.clickhouse_user}
    - Password: ${var.clickhouse_password}
    - Connection String: clickhouse://${var.clickhouse_user}:${var.clickhouse_password}@localhost:${var.clickhouse_native_port}/${var.clickhouse_db}
    
    Application Credentials:
    - App User: ${var.app_user}
    - App Password: ${random_password.app_password.result}
    
    Security Keys:
    - JWT Secret: ${random_password.jwt_secret.result}
    - Secret Key: ${random_password.secret_key.result}
    
    Docker Network: netra-dev-network
    
    To connect from application:
    - Use the connection strings above in your .env.development file
    - Or use the auto-generated .env.development.local file
    
    To manage:
    - Start: terraform apply
    - Stop: terraform destroy
    - View logs: docker logs netra-postgres-dev
    - Connect: psql -h localhost -p ${var.postgres_port} -U ${var.postgres_user} -d ${var.postgres_db}
  EOT
}