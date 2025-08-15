# Docker Network Configuration

resource "docker_network" "netra_dev" {
  name   = "netra-dev-network"
  driver = "bridge"
}