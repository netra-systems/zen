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
 * See: SPEC/learnings/redis_vpc_connector_requirement.xml
 */

# VPC Access Connector for staging environment
resource "google_vpc_access_connector" "staging_connector" {
  name          = "staging-connector"
  project       = var.project_id
  region        = var.region
  network       = "staging-vpc" # Must match the VPC network name
  ip_cidr_range = "10.1.0.0/28" # Reserved range for connector

  # Scaling configuration
  min_instances = 2
  max_instances = 10

  # Machine type for connector instances
  machine_type = "e2-micro"

  lifecycle {
    create_before_destroy = true
  }
}

# Output the connector name for use in Cloud Run services
output "vpc_connector_name" {
  value       = google_vpc_access_connector.staging_connector.name
  description = "Name of the VPC connector for Cloud Run services"
}

output "vpc_connector_id" {
  value       = google_vpc_access_connector.staging_connector.id
  description = "Full ID of the VPC connector"
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
        "run.googleapis.com/vpc-access-egress"    = "private-ranges-only"
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