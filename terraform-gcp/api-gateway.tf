# api-gateway.tf - API Gateway configuration for routing between services

# Main URL Map for routing between services
resource "google_compute_url_map" "main_api_gateway" {
  name            = "netra-api-gateway"
  default_service = google_compute_backend_service.backend_main.id
  
  # Auth service routing
  host_rule {
    hosts        = ["auth.staging.netrasystems.ai", "auth.netrasystems.ai"]
    path_matcher = "auth-service"
  }
  
  # Main application routing
  host_rule {
    hosts        = ["api.staging.netrasystems.ai", "api.netrasystems.ai", "staging.netrasystems.ai"]
    path_matcher = "main-api"
  }
  
  # Auth service paths
  path_matcher {
    name            = "auth-service"
    default_service = google_compute_backend_service.auth.id
    
    path_rule {
      paths   = ["/api/auth/*", "/auth/*"]
      service = google_compute_backend_service.auth.id
    }
    
    path_rule {
      paths   = ["/api/oauth/*", "/oauth/*"]
      service = google_compute_backend_service.auth.id
    }
  }
  
  # Main API paths
  path_matcher {
    name            = "main-api"
    default_service = google_compute_backend_service.backend_main.id
    
    # Route auth endpoints to auth service
    path_rule {
      paths   = ["/api/auth/*"]
      service = google_compute_backend_service.auth.id
      
      route_action {
        url_rewrite {
          host_rewrite = google_cloud_run_service.auth.status[0].url
        }
      }
    }
    
    # All other API endpoints to backend
    path_rule {
      paths   = ["/api/*"]
      service = google_compute_backend_service.backend_main.id
    }
    
    # WebSocket endpoints
    path_rule {
      paths   = ["/ws", "/ws/*"]
      service = google_compute_backend_service.backend_main.id
    }
    
    # Frontend routes
    path_rule {
      paths   = ["/*"]
      service = google_compute_backend_service.frontend_main.id
    }
  }
}

# Backend service for main backend
resource "google_compute_backend_service" "backend_main" {
  name                  = "netra-backend-main"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
  
  session_affinity = "CLIENT_IP"
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Backend service for frontend
resource "google_compute_backend_service" "frontend_main" {
  name                  = "netra-frontend-main"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }
  
  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

# Network Endpoint Groups
resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "netra-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.backend.name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "netra-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  
  cloud_run {
    service = google_cloud_run_service.frontend.name
  }
}

# Main HTTPS proxy
resource "google_compute_target_https_proxy" "main" {
  name             = "netra-main-https-proxy"
  url_map          = google_compute_url_map.main_api_gateway.id
  ssl_certificates = [
    google_compute_managed_ssl_certificate.main.id,
    google_compute_managed_ssl_certificate.auth.id
  ]
}

# Main SSL certificate
resource "google_compute_managed_ssl_certificate" "main" {
  name = "netra-main-ssl-cert"
  
  managed {
    domains = var.environment == "production" ? 
      ["netrasystems.ai", "api.netrasystems.ai", "app.netrasystems.ai"] : 
      ["staging.netrasystems.ai", "api.staging.netrasystems.ai", "app.staging.netrasystems.ai"]
  }
}

# Main Global IP
resource "google_compute_global_address" "main" {
  name = "netra-main-ip"
}

# Main HTTPS forwarding rule
resource "google_compute_global_forwarding_rule" "main_https" {
  name                  = "netra-main-https-forwarding"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.main.id
  ip_address            = google_compute_global_address.main.id
}

# HTTP to HTTPS redirect for main
resource "google_compute_url_map" "main_http_redirect" {
  name = "netra-main-http-redirect"
  
  default_url_redirect {
    https_redirect         = true
    strip_query            = false
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
  }
}

resource "google_compute_target_http_proxy" "main_http" {
  name    = "netra-main-http-proxy"
  url_map = google_compute_url_map.main_http_redirect.id
}

resource "google_compute_global_forwarding_rule" "main_http" {
  name                  = "netra-main-http-forwarding"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.main_http.id
  ip_address            = google_compute_global_address.main.id
}