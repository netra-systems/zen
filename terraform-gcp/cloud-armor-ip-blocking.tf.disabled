# Cloud Armor IP Blocking for Cloud Run
# This creates a Load Balancer with Cloud Armor to block specific IPs

# Cloud Armor Security Policy
resource "google_compute_security_policy" "ip_blocking" {
  name = "netra-ip-blocking-policy"

  # Default rule - allow all traffic
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "default rule"
  }

  # Block specific IPs
  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = [
          "138.197.191.87/32",  # Blocked IP
          # Add more IPs here as needed
        ]
      }
    }
    description = "Block malicious IPs"
  }
}

# NEG for Cloud Run service
resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "netra-cloudrun-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.app.name
  }
}

# Backend service
resource "google_compute_backend_service" "default" {
  name                  = "netra-backend-service"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.cloudrun_neg.id
  }
  
  security_policy = google_compute_security_policy.ip_blocking.id
}

# URL Map
resource "google_compute_url_map" "default" {
  name            = "netra-url-map"
  default_service = google_compute_backend_service.default.id
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "default" {
  name    = "netra-https-proxy"
  url_map = google_compute_url_map.default.id
  
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

# SSL Certificate
resource "google_compute_managed_ssl_certificate" "default" {
  name = "netra-ssl-cert"
  
  managed {
    domains = [var.domain_name]  # Add your domain
  }
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "default" {
  name                  = "netra-forwarding-rule"
  target                = google_compute_target_https_proxy.default.id
  port_range            = "443"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.default.id
}

# Reserved IP
resource "google_compute_global_address" "default" {
  name = "netra-global-ip"
}

# Output the load balancer IP
output "load_balancer_ip" {
  value = google_compute_global_address.default.address
}