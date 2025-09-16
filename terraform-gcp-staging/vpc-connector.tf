/**
 * VPC Connector Configuration for Cloud Run Services
 *
 * CRITICAL: This connector is REQUIRED for Cloud Run services to access
 * private VPC resources like Redis and Cloud SQL instances.
 *
 * Without this connector, services will fail at startup with:
 * - "Redis ping timeout after 10.0s"
 * - Database connection failures
 * - Complete chat functionality breakdown
 *
 * ISSUE #1177 FIX: Enhanced VPC connector with improved networking and resilience
 * - Subnet alignment for Redis connectivity (10.166.204.83:6379)
 * - Enhanced scaling for production workloads
 * - Network security and firewall rule coordination
 *
 * See: SPEC/learnings/redis_vpc_connector_requirement.xml
 */

# VPC Access Connector for staging environment
resource "google_vpc_access_connector" "staging_connector" {
  name          = "staging-connector"
  project       = var.project_id
  region        = var.region
  network       = "staging-vpc" # Must match the VPC network name

  # ISSUE #1177 FIX: Updated CIDR to align with Redis subnet routing
  # This ensures proper connectivity to Redis at 10.166.204.83:6379
  # Redis is in 10.166.0.0/16 network, so using 10.2.0.0/28 for connector (non-overlapping)
  ip_cidr_range = "10.2.0.0/28" # Non-overlapping CIDR for VPC connector routing to Redis network

  # PHASE 1 FIX: Enhanced scaling configuration for VPC capacity exhaustion (Issue #1278)
  # Based on Five Whys analysis - increase capacity to handle staging load
  min_instances = 5  # Increased for better baseline availability
  max_instances = 50 # Significantly increased to prevent capacity exhaustion during test runs

  # Enhanced throughput settings to support multiple concurrent services
  min_throughput = 300 # Minimum throughput in Mbps
  max_throughput = 1000 # Maximum throughput in Mbps

  # ISSUE #1177 + #1278 FIX: Enhanced machine type for better performance and capacity
  machine_type = "e2-standard-4" # Upgraded for higher throughput and resilience

  # ISSUE #1177 FIX: Enhanced lifecycle management
  lifecycle {
    create_before_destroy = true
    # Prevent accidental deletion of critical infrastructure
    prevent_destroy = false # Set to true in production
  }

  # ISSUE #1177 FIX: Add labels for infrastructure tracking
  labels = {
    environment = "staging"
    component   = "vpc-connector"
    purpose     = "cloud-run-private-access"
    issue       = "1177-http-503-fixes"
  }
}

# ISSUE #1177 FIX: Enhanced outputs for comprehensive infrastructure tracking
output "vpc_connector_name" {
  value       = google_vpc_access_connector.staging_connector.name
  description = "Name of the VPC connector for Cloud Run services"
}

output "vpc_connector_id" {
  value       = google_vpc_access_connector.staging_connector.id
  description = "Full ID of the VPC connector"
}

output "vpc_connector_state" {
  value       = google_vpc_access_connector.staging_connector.state
  description = "State of the VPC connector (for monitoring)"
}

output "vpc_connector_ip_cidr_range" {
  value       = google_vpc_access_connector.staging_connector.ip_cidr_range
  description = "IP CIDR range of the VPC connector"
}

output "vpc_connector_self_link" {
  value       = google_vpc_access_connector.staging_connector.self_link
  description = "Self-link of the VPC connector for Cloud Run annotations"
}

# Cloud Run service configuration example (to be used in service definitions)
# This is a documentation block showing how to use the connector
/*
resource "google_cloud_run_service" "backend" {
  name     = "netra-backend-staging"
  location = var.region
  project  = var.project_id

  template {
    metadata {
      annotations = {
        # CRITICAL: These annotations enable VPC access
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.staging_connector.name
        "run.googleapis.com/vpc-access-egress"    = "all-traffic"
      }
    }
    
    spec {
      containers {
        image = "gcr.io/${var.project_id}/netra-backend-staging:latest"
        
        # Environment variables and other configuration...
      }
    }
  }
}
*/