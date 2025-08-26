# Load Balancer Configuration for GCP Staging
# This creates an HTTPS Load Balancer with Cloud Run backend services

# Reserve static IP for load balancer
resource "google_compute_global_address" "lb_ip" {
  name         = "${var.environment}-lb-ip"
  description  = "Static IP for HTTPS Load Balancer"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
  project      = var.project_id
}

# Network Endpoint Groups for Cloud Run services
resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "${var.environment}-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id
  
  cloud_run {
    service = "netra-backend-staging"
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_compute_region_network_endpoint_group" "auth_neg" {
  name                  = "${var.environment}-auth-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id
  
  cloud_run {
    service = "netra-auth-service"
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "${var.environment}-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  project               = var.project_id
  
  cloud_run {
    service = "netra-frontend-staging"
  }
  
  depends_on = [google_project_service.required_apis]
}

# Health check for backend services
resource "google_compute_health_check" "http_health_check" {
  name                = "${var.environment}-http-health-check"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
  project             = var.project_id
  
  http_health_check {
    port         = 8080
    request_path = "/health"
  }
  
  log_config {
    enable = true
  }
}

# Backend services
resource "google_compute_backend_service" "api_backend" {
  name                  = "${var.environment}-api-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 30
  project               = var.project_id
  
  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
  
  security_policy = google_compute_security_policy.cloud_armor.id
  
  health_checks = [google_compute_health_check.http_health_check.id]
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  depends_on = [google_compute_security_policy.cloud_armor]
}

resource "google_compute_backend_service" "auth_backend" {
  name                  = "${var.environment}-auth-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 30
  project               = var.project_id
  
  backend {
    group = google_compute_region_network_endpoint_group.auth_neg.id
  }
  
  security_policy = google_compute_security_policy.cloud_armor.id
  
  health_checks = [google_compute_health_check.http_health_check.id]
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  depends_on = [google_compute_security_policy.cloud_armor]
}

resource "google_compute_backend_service" "frontend_backend" {
  name                  = "${var.environment}-frontend-backend"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  timeout_sec           = 30
  project               = var.project_id
  
  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }
  
  security_policy = google_compute_security_policy.cloud_armor.id
  
  health_checks = [google_compute_health_check.http_health_check.id]
  
  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    default_ttl                  = 3600
    client_ttl                   = 7200
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400
    
    negative_caching_policy {
      code = 404
      ttl  = 120
    }
  }
  
  compression_mode = "AUTOMATIC"
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  depends_on = [google_compute_security_policy.cloud_armor]
}

# URL Map for routing
resource "google_compute_url_map" "https_lb" {
  name            = "${var.environment}-https-lb"
  default_service = google_compute_backend_service.frontend_backend.id
  project         = var.project_id
  
  host_rule {
    hosts        = ["api.staging.netrasystems.ai"]
    path_matcher = "api-paths"
  }
  
  host_rule {
    hosts        = ["auth.staging.netrasystems.ai"]
    path_matcher = "auth-paths"
  }
  
  host_rule {
    hosts        = ["app.staging.netrasystems.ai", "staging.netrasystems.ai"]
    path_matcher = "frontend-paths"
  }
  
  path_matcher {
    name            = "api-paths"
    default_service = google_compute_backend_service.api_backend.id
  }
  
  path_matcher {
    name            = "auth-paths"
    default_service = google_compute_backend_service.auth_backend.id
  }
  
  path_matcher {
    name            = "frontend-paths"
    default_service = google_compute_backend_service.frontend_backend.id
  }
  
  # Add header-based routing for WebSocket connections
  default_route_action {
    cors_policy {
      allow_origins     = ["https://app.staging.netrasystems.ai", "https://staging.netrasystems.ai"]
      allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
      allow_headers     = ["*"]
      expose_headers    = ["*"]
      max_age           = 3600
      allow_credentials = true
    }
  }
}

# SSL Certificate (Google-managed)
resource "google_compute_managed_ssl_certificate" "staging" {
  name    = "${var.environment}-ssl-cert"
  project = var.project_id
  
  managed {
    domains = [
      "staging.netrasystems.ai",
      "*.staging.netrasystems.ai"
    ]
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# HTTPS Proxy
resource "google_compute_target_https_proxy" "https_lb" {
  name             = "${var.environment}-https-lb-proxy"
  url_map          = google_compute_url_map.https_lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.staging.id]
  project          = var.project_id
  
  depends_on = [
    google_compute_managed_ssl_certificate.staging
  ]
}

# Global Forwarding Rule
resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${var.environment}-https-forwarding-rule"
  target                = google_compute_target_https_proxy.https_lb.id
  port_range            = "443"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip.address
  project               = var.project_id
  
  labels = var.labels
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  name    = "${var.environment}-http-redirect"
  project = var.project_id
  
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "http_redirect" {
  name    = "${var.environment}-http-redirect-proxy"
  url_map = google_compute_url_map.http_redirect.id
  project = var.project_id
}

resource "google_compute_global_forwarding_rule" "http_redirect" {
  name                  = "${var.environment}-http-forwarding-rule"
  target                = google_compute_target_http_proxy.http_redirect.id
  port_range            = "80"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip.address
  project               = var.project_id
  
  labels = var.labels
}