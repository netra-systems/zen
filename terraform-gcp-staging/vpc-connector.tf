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
  network       = var.enable_private_ip ? google_compute_network.vpc[0].name : "default" # Must match the VPC network name

  # ISSUE #1177 FIX: Updated CIDR to align with Redis subnet routing
  # This ensures proper connectivity to Redis at 10.166.204.83:6379
  # Redis is in 10.166.0.0/16 network, so using 10.2.0.0/28 for connector (non-overlapping)
  ip_cidr_range = "10.2.0.0/28" # Non-overlapping CIDR for VPC connector routing to Redis network

  # EMERGENCY PHASE 2 FIX: Critical scaling for golden path test execution (Issue #1278)
  # Based on Five Whys analysis - emergency capacity increase to handle concurrent test execution
  min_instances = 10  # EMERGENCY: Doubled from 5 to 10 for immediate baseline capacity
  max_instances = 100 # EMERGENCY: Doubled from 50 to 100 for emergency peak capacity

  # EMERGENCY: Enhanced throughput settings for concurrent test execution load
  min_throughput = 500 # EMERGENCY: Increased from 300 to 500 for higher baseline
  max_throughput = 2000 # EMERGENCY: Doubled from 1000 to 2000 for emergency peak

  # EMERGENCY PHASE 2 FIX: Upgraded machine type for critical test execution capacity
  machine_type = "e2-standard-8" # EMERGENCY: Upgraded from e2-standard-4 to e2-standard-8

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

  # ISSUE #1177 FIX: Ensure VPC connector is created after VPC network
  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc
  ]
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