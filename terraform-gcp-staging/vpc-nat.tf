# Cloud NAT for External Service Access with VPC Private Ranges
# 
# CRITICAL: This Cloud NAT enables external service connectivity (ClickHouse)
# while preserving Cloud SQL Unix socket compatibility with private-ranges-only VPC egress.
# 
# Background: Sept 15, 2025 VPC egress regression (commit 2acf46c8a)
# Changed VPC egress to "all-traffic" to fix ClickHouse but broke Cloud SQL.
# Solution: Cloud NAT + private-ranges-only enables both services.
#
# Related Documentation:
# - /SPEC/learnings/vpc_egress_cloud_sql_regression_critical.xml
# - /SPEC/learnings/vpc_clickhouse_proxy_solutions.xml  
# - /docs/infrastructure/vpc-egress-regression-timeline.md

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

# Local values for consistent naming
locals {
  project_id = var.project_id
  region     = var.region
  
  # NAT naming convention
  nat_router_name  = "staging-nat-router"
  nat_gateway_name = "staging-nat-gateway"
  
  # VPC network reference - must match the created VPC name
  vpc_network_name = "${var.environment}-vpc"
  
  # Tags for resource organization
  common_tags = {
    environment = "staging"
    purpose     = "vpc-nat"
    created_by  = "terraform"
    # Reference to the regression fix
    fixes_issue = "vpc-egress-cloud-sql-regression"
    documentation = "vpc_egress_cloud_sql_regression_critical.xml"
  }
}

# Cloud Router for NAT Gateway
# This router enables the NAT gateway to route traffic from private VPC to internet
resource "google_compute_router" "staging_nat_router" {
  count   = var.enable_private_ip ? 1 : 0
  name    = local.nat_router_name
  region  = local.region
  network = google_compute_network.vpc[0].name
  project = local.project_id

  description = "Cloud Router for NAT gateway - enables external service access while preserving Cloud SQL Unix socket compatibility"

  # Enable BGP for advanced routing (optional)
  bgp {
    asn = 64512  # Private ASN for staging
    
    # Advertise default route for better routing control
    advertise_mode = "DEFAULT"
  }
}

# Cloud NAT Gateway
# This NAT provides outbound internet access for private VPC resources
# while maintaining VPC egress private-ranges-only setting
resource "google_compute_router_nat" "staging_nat_gateway" {
  count   = var.enable_private_ip ? 1 : 0
  name    = local.nat_gateway_name
  router  = google_compute_router.staging_nat_router[0].name
  region  = local.region
  project = local.project_id

  # Route ALL subnet IP ranges through NAT for external access
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # Logging configuration for troubleshooting
  log_config {
    enable = true
    filter = "ERRORS_ONLY"  # Only log errors to reduce costs
  }

  # Minimum ports per VM to handle concurrent connections
  # Adjust based on expected external service connections
  min_ports_per_vm = 64
  
  # Enable endpoint independent mapping for better connection reliability
  enable_endpoint_independent_mapping = true

  # Drain timeout for graceful connection handling during updates
  nat_timeout {
    tcp_established_idle_timeout_sec = 1200   # 20 minutes
    tcp_transitory_idle_timeout_sec  = 30     # 30 seconds
    udp_idle_timeout_sec            = 30      # 30 seconds
    icmp_idle_timeout_sec           = 30      # 30 seconds
  }
}

# Output values for reference by other configurations
output "nat_router_name" {
  description = "Name of the Cloud NAT router"
  value       = var.enable_private_ip ? google_compute_router.staging_nat_router[0].name : null
}

output "nat_gateway_name" {
  description = "Name of the Cloud NAT gateway"
  value       = var.enable_private_ip ? google_compute_router_nat.staging_nat_gateway[0].name : null
}

output "nat_router_self_link" {
  description = "Self-link of the Cloud NAT router"
  value       = var.enable_private_ip ? google_compute_router.staging_nat_router[0].self_link : null
}

# Data source to verify VPC network exists (only when private IP is enabled)
data "google_compute_network" "staging_vpc" {
  count   = var.enable_private_ip ? 1 : 0
  name    = local.vpc_network_name
  project = local.project_id
}

# Validation: Ensure VPC exists before creating NAT (only when private IP is enabled)
resource "null_resource" "vpc_validation" {
  count = var.enable_private_ip ? 1 : 0
  # This resource validates the VPC exists
  triggers = {
    vpc_network_id = data.google_compute_network.staging_vpc[0].id
  }

  provisioner "local-exec" {
    command = "echo 'VPC ${local.vpc_network_name} validated for NAT deployment'"
  }
}

# Variable definitions for enable_private_ip (should be defined in variables.tf or passed in)
variable "enable_private_ip" {
  description = "Enable private IP for Cloud SQL - also determines if VPC resources are created"
  type        = bool
  default     = true
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "netra-staging"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

# Resource monitoring and alerting (optional)
# Uncomment if you want monitoring alerts for NAT gateway

# resource "google_monitoring_alert_policy" "nat_gateway_utilization" {
#   display_name = "Cloud NAT Gateway High Utilization"
#   project      = local.project_id
#   
#   conditions {
#     display_name = "NAT Gateway Port Utilization"
#     
#     condition_threshold {
#       filter          = "resource.type=\"nat_gateway\" AND resource.labels.gateway_name=\"${local.nat_gateway_name}\""
#       comparison      = "COMPARISON_GT"
#       threshold_value = 0.8
#       duration        = "300s"
#       
#       aggregations {
#         alignment_period   = "60s"
#         per_series_aligner = "ALIGN_MEAN"
#       }
#     }
#   }
#   
#   alert_strategy {
#     notification_rate_limit {
#       period = "300s"
#     }
#   }
# }

# Documentation as code - embed key information
resource "null_resource" "documentation" {
  triggers = {
    # Force recreation if documentation needs update
    documentation_version = "1.0.0"
    issue_reference      = "vpc-egress-cloud-sql-regression"
    solution_date        = "2025-09-16"
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      echo "=== Cloud NAT Deployment Documentation ==="
      echo "Purpose: Enable external service access with VPC private-ranges-only"
      echo "Fixes: VPC egress regression from Sept 15, 2025 (commit 2acf46c8a)"
      echo "NAT Router: ${local.nat_router_name}"
      echo "NAT Gateway: ${local.nat_gateway_name}"
      echo "VPC Network: ${local.vpc_network_name}"
      echo "Project: ${local.project_id}"
      echo "Region: ${local.region}"
      echo ""
      echo "External Services Enabled:"
      echo "- ClickHouse Cloud (xedvrr4c3r.us-central1.gcp.clickhouse.cloud)"
      echo "- OpenAI API (api.openai.com)"
      echo "- Anthropic API (api.anthropic.com)"
      echo "- Other external APIs and services"
      echo ""
      echo "Cloud SQL Compatibility:"
      echo "- Unix socket connections work with private-ranges-only"
      echo "- No VPC routing conflicts"
      echo "- <1 second connection times expected"
      echo ""
      echo "Cost Estimate: ~$50/month for NAT gateway + data processing"
      echo "Documentation: /SPEC/learnings/vpc_egress_cloud_sql_regression_critical.xml"
      echo "=========================================="
    EOT
  }
}

# Resource dependencies to ensure proper creation order (only when private IP is enabled)
resource "null_resource" "deployment_order" {
  count = var.enable_private_ip ? 1 : 0
  depends_on = [
    data.google_compute_network.staging_vpc,
    google_compute_router.staging_nat_router,
    google_compute_router_nat.staging_nat_gateway
  ]

  provisioner "local-exec" {
    command = "echo 'Cloud NAT infrastructure deployed successfully'"
  }
}