# Cloud Armor Security Policy Configuration
# Provides DDoS protection and WAF capabilities for the load balancer

resource "google_compute_security_policy" "cloud_armor" {
  name        = "${var.environment}-security-policy"
  description = "Cloud Armor security policy with DDoS protection and WAF rules"
  project     = var.project_id

  # Adaptive Protection (DDoS mitigation)
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable          = true
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

  # REMOVED: OWASP WAF Rules (priorities 100-109)
  # These rules were causing excessive false positives and blocking legitimate traffic
  # See SPEC/learnings/cloud_armor_waf_removal.xml for detailed explanation
  # DO NOT RE-ADD without thorough testing and specific business justification

  # Note: Basic DDoS protection and rate limiting remain active
  # Custom security rules can be added for specific threats as needed

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

    preview     = true # Set to false after testing
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
      filter          = "resource.type=\"https_lb_rule\" AND metric.type=\"loadbalancing.googleapis.com/https/request_count\" AND metric.label.response_code_class=\"4xx\""
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