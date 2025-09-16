# Firewall Rules for Redis and VPC Connectivity
#
# CRITICAL: These rules enable Cloud Run services to access Redis and other VPC resources
# through the VPC connector. Without these rules, services will fail with connection timeouts.
#
# ISSUE #1177 FIX: Missing firewall rules for Redis connectivity
# - Redis port 6379 access from VPC connector subnet
# - General VPC ingress/egress rules for Cloud Run services
# - Enhanced security and monitoring for production readiness
#
# See: SPEC/learnings/redis_vpc_connector_requirement.xml

# Firewall rule to allow VPC connector to access Redis on port 6379
resource "google_compute_firewall" "allow_vpc_connector_to_redis" {
  name    = "allow-vpc-connector-to-redis"
  network = var.enable_private_ip ? google_compute_network.vpc[0].name : "default"
  project = var.project_id

  description = "Allow VPC connector subnet to access Redis on port 6379 - ISSUE #1177 FIX"

  # Allow TCP traffic on Redis port 6379
  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  # Source: VPC connector CIDR range (from vpc-connector.tf)
  source_ranges = ["10.2.0.0/28"]

  # Target: Redis instances (using network tags or all instances)
  target_tags = ["redis", "memorystore"]

  # Enhanced logging for troubleshooting
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }

  # Labels for infrastructure tracking
  labels = {
    environment = "staging"
    component   = "firewall"
    purpose     = "redis-connectivity"
    issue       = "1177-redis-vpc-fixes"
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}

# Firewall rule to allow internal VPC communication for Cloud Run services
resource "google_compute_firewall" "allow_internal_vpc_communication" {
  name    = "allow-internal-vpc-communication"
  network = var.enable_private_ip ? google_compute_network.vpc[0].name : "default"
  project = var.project_id

  description = "Allow internal VPC communication for Cloud Run services via VPC connector - ISSUE #1177 FIX"

  # Allow all TCP traffic within VPC
  allow {
    protocol = "tcp"
  }

  # Allow all UDP traffic within VPC
  allow {
    protocol = "udp"
  }

  # Allow ICMP for network diagnostics
  allow {
    protocol = "icmp"
  }

  # Source: VPC connector subnet range
  source_ranges = ["10.2.0.0/28"]

  # Target: All VPC resources
  target_tags = ["vpc-internal", "cloud-run", "database", "redis"]

  # Enhanced logging for troubleshooting
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }

  # Labels for infrastructure tracking
  labels = {
    environment = "staging"
    component   = "firewall"
    purpose     = "vpc-internal-communication"
    issue       = "1177-vpc-connectivity-fixes"
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}

# Firewall rule to allow health checks from Google Cloud Load Balancer
resource "google_compute_firewall" "allow_health_checks" {
  name    = "allow-health-checks"
  network = var.enable_private_ip ? google_compute_network.vpc[0].name : "default"
  project = var.project_id

  description = "Allow health checks from Google Cloud Load Balancer to Cloud Run services - ISSUE #1177 FIX"

  # Allow HTTP and HTTPS traffic for health checks
  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8000", "8080"]
  }

  # Google Cloud health check source ranges
  source_ranges = [
    "130.211.0.0/22",
    "35.191.0.0/16"
  ]

  # Target: Cloud Run services and load balancer backends
  target_tags = ["cloud-run", "http-server", "https-server", "load-balancer-backend"]

  # Enhanced logging for troubleshooting
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }

  # Labels for infrastructure tracking
  labels = {
    environment = "staging"
    component   = "firewall"
    purpose     = "health-checks"
    issue       = "1177-load-balancer-connectivity"
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}

# Firewall rule to allow egress to external APIs (OpenAI, Anthropic, etc.)
resource "google_compute_firewall" "allow_external_apis" {
  name      = "allow-external-apis"
  network   = var.enable_private_ip ? google_compute_network.vpc[0].name : "default"
  project   = var.project_id
  direction = "EGRESS"

  description = "Allow egress to external APIs for AI services - ISSUE #1177 FIX"

  # Allow HTTPS traffic to external APIs
  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  # Allow HTTP traffic (some APIs might redirect)
  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  # Target: All VPC resources that need external API access
  target_tags = ["cloud-run", "external-api-access"]

  # Destination: Internet (0.0.0.0/0)
  destination_ranges = ["0.0.0.0/0"]

  # Enhanced logging for security monitoring
  log_config {
    metadata = "INCLUDE_ALL_METADATA"
  }

  # Labels for infrastructure tracking
  labels = {
    environment = "staging"
    component   = "firewall"
    purpose     = "external-api-access"
    issue       = "1177-external-connectivity"
  }

  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
}

# Output firewall rule names for reference
output "firewall_rules" {
  description = "Names of created firewall rules for Redis VPC connectivity"
  value = {
    redis_access        = google_compute_firewall.allow_vpc_connector_to_redis.name
    internal_vpc        = google_compute_firewall.allow_internal_vpc_communication.name
    health_checks       = google_compute_firewall.allow_health_checks.name
    external_apis       = google_compute_firewall.allow_external_apis.name
  }
}

# Output firewall rule IDs for monitoring and validation
output "firewall_rule_ids" {
  description = "IDs of created firewall rules for monitoring"
  value = {
    redis_access_id     = google_compute_firewall.allow_vpc_connector_to_redis.id
    internal_vpc_id     = google_compute_firewall.allow_internal_vpc_communication.id
    health_checks_id    = google_compute_firewall.allow_health_checks.id
    external_apis_id    = google_compute_firewall.allow_external_apis.id
  }
}