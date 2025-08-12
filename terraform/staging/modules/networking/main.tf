# Networking Module - VPC, Subnets, and Load Balancer configuration

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "staging-vpc-${var.environment_name}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  mtu                     = 1460
}

# Subnet for Cloud Run and other services
resource "google_compute_subnetwork" "main" {
  name          = "staging-subnet-${var.environment_name}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
  
  private_ip_google_access = true
  
  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# VPC Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "staging-connector-${var.environment_name}"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_cidr
  
  min_instances = 2
  max_instances = 10
  
  machine_type = "e2-micro"
}

# Private Service Connection for databases
resource "google_compute_global_address" "private_ip_address" {
  name          = "staging-private-ip-${var.environment_name}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Cloud NAT for outbound internet access
resource "google_compute_router" "router" {
  name    = "staging-router-${var.environment_name}"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "staging-nat-${var.environment_name}"
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  
  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Global IP address for Load Balancer
resource "google_compute_global_address" "lb_ip" {
  name = "staging-lb-ip-${var.environment_name}"
}

# URL Map for routing
resource "google_compute_url_map" "lb" {
  name            = "staging-lb-${var.environment_name}"
  default_service = var.default_backend_service

  host_rule {
    hosts        = [var.domain]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = var.frontend_backend_service

    path_rule {
      paths   = ["/api/*", "/ws/*", "/auth/*", "/health"]
      service = var.backend_backend_service
    }
    
    path_rule {
      paths   = ["/*"]
      service = var.frontend_backend_service
    }
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "lb" {
  name             = "staging-https-proxy-${var.environment_name}"
  url_map          = google_compute_url_map.lb.id
  ssl_certificates = var.ssl_certificate_id != "" ? [var.ssl_certificate_id] : []
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "lb" {
  name                  = "staging-forwarding-rule-${var.environment_name}"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.lb.id
  ip_address            = google_compute_global_address.lb_ip.id
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name = "staging-http-redirect-${var.environment_name}"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "staging-http-redirect-proxy-${var.environment_name}"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  name                  = "staging-http-redirect-rule-${var.environment_name}"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.http_redirect.id
  ip_address            = google_compute_global_address.lb_ip.id
}

# Firewall Rules
resource "google_compute_firewall" "allow_health_checks" {
  name    = "staging-allow-health-checks-${var.environment_name}"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8000", "3000"]
  }

  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22"
  ]
  
  target_tags = ["health-check"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "staging-allow-internal-${var.environment_name}"
  network = google_compute_network.vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
  
  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.subnet_cidr,
    var.connector_cidr
  ]
}

# Cloud Armor Security Policy (optional)
resource "google_compute_security_policy" "policy" {
  count = var.enable_cloud_armor ? 1 : 0
  
  name = "staging-security-policy-${var.environment_name}"

  rule {
    action   = "allow"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Allow all traffic by default"
  }

  rule {
    action   = "rate_based_ban"
    priority = "900"
    
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      
      enforce_on_key = "IP"
      
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      
      ban_duration_sec = 600
    }
    
    description = "Rate limiting rule"
  }
}