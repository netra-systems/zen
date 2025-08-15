# ClickHouse Container Configuration

resource "docker_image" "clickhouse" {
  name         = "clickhouse/clickhouse-server:${var.clickhouse_version}"
  keep_locally = true
}

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
    name    = docker_network.netra_dev.name
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