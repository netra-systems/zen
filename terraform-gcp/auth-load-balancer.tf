# auth-load-balancer.tf - Load Balancer and Routing for Auth Service

# Network Endpoint Group for Auth Service
resource "google_compute_region_network_endpoint_group" "auth_neg" {
  name                  = "netra-auth-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.auth.name
  }
}

# Backend Service for Auth
resource "google_compute_backend_service" "auth" {
  name                  = "netra-auth-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.auth_neg.id
  }
  
  # Health check is automatically managed for Cloud Run
  
  # Session affinity for auth service
  session_affinity = "CLIENT_IP"
  
  # Security policy (if Cloud Armor is enabled)
  # security_policy = google_compute_security_policy.auth.id
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# URL Map for routing auth requests
resource "google_compute_url_map" "auth" {
  name            = "netra-auth-url-map"
  default_service = google_compute_backend_service.auth.id
  
  host_rule {
    hosts        = ["auth.staging.netrasystems.ai", "auth.netrasystems.ai"]
    path_matcher = "auth-paths"
  }
  
  path_matcher {
    name            = "auth-paths"
    default_service = google_compute_backend_service.auth.id
    
    # OAuth endpoints
    path_rule {
      paths   = ["/api/auth/login", "/api/auth/callback", "/api/auth/logout"]
      service = google_compute_backend_service.auth.id
    }
    
    # Token endpoints
    path_rule {
      paths   = ["/api/auth/token", "/api/auth/refresh", "/api/auth/validate"]
      service = google_compute_backend_service.auth.id
    }
    
    # User session endpoints
    path_rule {
      paths   = ["/api/auth/session", "/api/auth/me"]
      service = google_compute_backend_service.auth.id
    }
    
    # Configuration endpoint
    path_rule {
      paths   = ["/api/auth/config"]
      service = google_compute_backend_service.auth.id
    }
    
    # Health check
    path_rule {
      paths   = ["/health", "/api/health"]
      service = google_compute_backend_service.auth.id
    }
  }
}

# HTTPS Proxy for Auth Service
resource "google_compute_target_https_proxy" "auth" {
  name             = "netra-auth-https-proxy"
  url_map          = google_compute_url_map.auth.id
  ssl_certificates = [google_compute_managed_ssl_certificate.auth.id]
}

# SSL Certificate for Auth Service
resource "google_compute_managed_ssl_certificate" "auth" {
  name = "netra-auth-ssl-cert"
  
  managed {
    domains = var.environment == "production" ? 
      ["auth.netrasystems.ai"] : 
      ["auth.staging.netrasystems.ai"]
  }
}

# Global Forwarding Rule for Auth Service
resource "google_compute_global_forwarding_rule" "auth" {
  name                  = "netra-auth-forwarding-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.auth.id
  ip_address            = google_compute_global_address.auth.id
}

# Static IP for Auth Service
resource "google_compute_global_address" "auth" {
  name = "netra-auth-ip"
}

# HTTP to HTTPS redirect
resource "google_compute_url_map" "auth_http_redirect" {
  name = "netra-auth-http-redirect"
  
  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "auth_http" {
  name    = "netra-auth-http-proxy"
  url_map = google_compute_url_map.auth_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "auth_http" {
  name                  = "netra-auth-http-forwarding-rule"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.auth_http.id
  ip_address            = google_compute_global_address.auth.id
}

# Cloud Armor Security Policy for Auth Service (optional)
resource "google_compute_security_policy" "auth" {
  count = var.enable_cloud_armor ? 1 : 0
  name  = "netra-auth-security-policy"
  
  # Rate limiting rule
  rule {
    action   = "throttle"
    priority = "1000"
    
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
    }
    
    description = "Rate limit auth requests"
  }
  
  # Block suspicious patterns
  rule {
    action   = "deny(403)"
    priority = "2000"
    
    match {
      expr {
        expression = "origin.region_code == 'CN' || origin.region_code == 'RU'"
      }
    }
    
    description = "Block regions with high attack rates"
  }
  
  # Default rule
  rule {
    action   = "allow"
    priority = "2147483647"
    
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    description = "Default allow rule"
  }
}