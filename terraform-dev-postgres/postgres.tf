# PostgreSQL Container Configuration

resource "docker_image" "postgres" {
  name         = "postgres:${var.postgres_version}"
  keep_locally = true
}

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

resource "docker_container" "postgres_dev" {
  name  = "netra-postgres-dev"
  image = docker_image.postgres.image_id
  
  restart = "unless-stopped"
  
  env = [
    "POSTGRES_DB=${var.postgres_db}",
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${random_string.postgres_password.result}",
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
    name    = docker_network.netra_dev.name
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