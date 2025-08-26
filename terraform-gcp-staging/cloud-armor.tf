# Cloud Armor Security Policy Configuration
# Provides DDoS protection and WAF capabilities for the load balancer

resource "google_compute_security_policy" "cloud_armor" {
  name        = "${var.environment}-security-policy"
  description = "Cloud Armor security policy with DDoS protection and WAF rules"
  project     = var.project_id
  
  # Adaptive Protection (DDoS mitigation)
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
      rule_visibility = "STANDARD"
    }
  }
  
  # Default rule - Allow all traffic (will be filtered by specific rules)
  rule {
    action   = "allow"
    priority = 2147483647
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
  
  # Rate limiting rule - Protection against abuse
  rule {
    action   = "rate_based_ban"
    priority = 1000
    
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
    
    description = "Rate limiting - 100 requests per minute per IP"
  }
  
  # Block SQL injection attempts
  rule {
    action   = "deny(403)"
    priority = 100
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-stable', ['owasp-crs-v030001-id942251-sqli', 'owasp-crs-v030001-id942420-sqli', 'owasp-crs-v030001-id942431-sqli', 'owasp-crs-v030001-id942460-sqli'])"
      }
    }
    
    description = "Block SQL injection attempts"
  }
  
  # Block XSS attempts
  rule {
    action   = "deny(403)"
    priority = 101
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-stable', ['owasp-crs-v030001-id941150-xss', 'owasp-crs-v030001-id941320-xss', 'owasp-crs-v030001-id941330-xss', 'owasp-crs-v030001-id941340-xss'])"
      }
    }
    
    description = "Block XSS attempts"
  }
  
  # Block Local File Inclusion attempts
  rule {
    action   = "deny(403)"
    priority = 102
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-stable', ['owasp-crs-v030001-id930100-lfi', 'owasp-crs-v030001-id930110-lfi', 'owasp-crs-v030001-id930120-lfi', 'owasp-crs-v030001-id930130-lfi'])"
      }
    }
    
    description = "Block Local File Inclusion attempts"
  }
  
  # Block Remote Code Execution attempts
  rule {
    action   = "deny(403)"
    priority = 103
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rce-stable', ['owasp-crs-v030001-id932100-rce', 'owasp-crs-v030001-id932105-rce', 'owasp-crs-v030001-id932110-rce', 'owasp-crs-v030001-id932115-rce'])"
      }
    }
    
    description = "Block Remote Code Execution attempts"
  }
  
  # Block Remote File Inclusion attempts
  rule {
    action   = "deny(403)"
    priority = 104
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rfi-stable', ['owasp-crs-v030001-id931100-rfi', 'owasp-crs-v030001-id931110-rfi', 'owasp-crs-v030001-id931120-rfi', 'owasp-crs-v030001-id931130-rfi'])"
      }
    }
    
    description = "Block Remote File Inclusion attempts"
  }
  
  # Block Method Enforcement violations
  rule {
    action   = "deny(403)"
    priority = 105
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('methodenforcement-stable')"
      }
    }
    
    description = "Block Method Enforcement violations"
  }
  
  # Block Scanner Detection attempts
  rule {
    action   = "deny(403)"
    priority = 106
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('scannerdetection-stable')"
      }
    }
    
    description = "Block Scanner Detection attempts"
  }
  
  # Block Protocol Attack attempts
  rule {
    action   = "deny(403)"
    priority = 107
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('protocolattack-stable')"
      }
    }
    
    description = "Block Protocol Attack attempts"
  }
  
  # Block PHP injection attempts
  rule {
    action   = "deny(403)"
    priority = 108
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('php-stable')"
      }
    }
    
    description = "Block PHP injection attempts"
  }
  
  # Block Session Fixation attempts
  rule {
    action   = "deny(403)"
    priority = 109
    
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sessionfixation-stable')"
      }
    }
    
    description = "Block Session Fixation attempts"
  }
  
  # Geographical restrictions - Throttle high-risk countries
  rule {
    action   = "throttle"
    priority = 500
    
    match {
      expr {
        expression = "origin.region_code == 'CN' || origin.region_code == 'RU' || origin.region_code == 'KP' || origin.region_code == 'IR'"
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      
      rate_limit_threshold {
        count        = 10
        interval_sec = 60
      }
    }
    
    description = "Throttle requests from high-risk regions"
  }
  
  # Block requests with suspicious user agents
  rule {
    action   = "deny(403)"
    priority = 600
    
    match {
      expr {
        expression = "request.headers['user-agent'].lower().contains('bot') || request.headers['user-agent'].lower().contains('crawler') || request.headers['user-agent'].lower().contains('spider') || request.headers['user-agent'].lower().contains('scraper') || request.headers['user-agent'].lower().contains('scanner')"
      }
    }
    
    preview = true  # Set to false after testing
    description = "Block suspicious user agents (preview mode)"
  }
  
  # Advanced rate limiting for API endpoints
  rule {
    action   = "rate_based_ban"
    priority = 700
    
    match {
      expr {
        expression = "request.path.matches('/api/.*')"
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      
      rate_limit_threshold {
        count        = 1000
        interval_sec = 60
      }
      
      ban_duration_sec = 300
    }
    
    description = "API endpoint rate limiting - 1000 requests per minute"
  }
}

# Cloud Logging sink for security events
resource "google_logging_project_sink" "security_events" {
  name        = "${var.environment}-security-events"
  destination = "storage.googleapis.com/${google_storage_bucket.security_logs.name}"
  project     = var.project_id
  
  filter = <<-EOT
    resource.type="http_load_balancer"
    jsonPayload.enforcedSecurityPolicy.name="${google_compute_security_policy.cloud_armor.name}"
    (jsonPayload.enforcedSecurityPolicy.outcome="DENY" OR 
     jsonPayload.enforcedSecurityPolicy.outcome="RATE_BASED_BAN" OR
     jsonPayload.enforcedSecurityPolicy.outcome="THROTTLE")
  EOT
  
  unique_writer_identity = true
}

# Storage bucket for security logs
resource "google_storage_bucket" "security_logs" {
  name          = "${var.project_id}-security-logs"
  location      = var.region
  force_destroy = false
  project       = var.project_id
  
  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
  
  versioning {
    enabled = true
  }
  
  labels = var.labels
}

# IAM binding for log sink
resource "google_storage_bucket_iam_member" "security_logs_writer" {
  bucket = google_storage_bucket.security_logs.name
  role   = "roles/storage.objectCreator"
  member = google_logging_project_sink.security_events.writer_identity
}

# Monitoring alert for security events
resource "google_monitoring_alert_policy" "security_violations" {
  display_name = "${var.environment} - Security Policy Violations"
  project      = var.project_id
  combiner     = "OR"
  
  conditions {
    display_name = "High rate of security denials"
    
    condition_threshold {
      filter          = "resource.type=\"http_load_balancer\" AND metric.type=\"loadbalancing.googleapis.com/https/request_count\" AND metric.labels.response_code_class=\"400\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 100
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  notification_channels = var.notification_channels
  
  documentation {
    content = "High rate of security policy violations detected. Check Cloud Armor logs for details."
  }
}