# Redis Container Configuration

resource "docker_image" "redis" {
  name         = "redis:${var.redis_version}"
  keep_locally = true
}

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
    name    = docker_network.netra_dev.name
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