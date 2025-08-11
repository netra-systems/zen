terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "gcs" {
    # Configured dynamically in GitHub Actions
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Generate unique suffix for resources
resource "random_id" "staging" {
  byte_length = 4
}

locals {
  environment_name = "pr-${var.pr_number}"
  resource_suffix  = "${local.environment_name}-${random_id.staging.hex}"
  
  common_labels = {
    environment = "staging"
    pr_number   = var.pr_number
    managed_by  = "terraform"
    auto_delete = "true"
  }
  
  # Resource limits based on configuration
  cpu_limit       = var.resource_limits.cpu_limit
  memory_limit    = var.resource_limits.memory_limit
  min_instances   = var.resource_limits.min_instances
  max_instances   = var.resource_limits.max_instances
  
  # URLs
  backend_subdomain  = "${local.environment_name}-api"
  frontend_subdomain = local.environment_name
  backend_url        = "https://${local.backend_subdomain}.${var.domain}"
  frontend_url       = "https://${local.frontend_subdomain}.${var.domain}"
}

# Networking module
module "networking" {
  source = "./modules/networking"
  
  project_id       = var.project_id
  region           = var.region
  environment_name = local.environment_name
  resource_suffix  = local.resource_suffix
  labels           = local.common_labels
}

# Security module - IAM, secrets, SSL
module "security" {
  source = "./modules/security"
  
  project_id       = var.project_id
  region           = var.region
  environment_name = local.environment_name
  resource_suffix  = local.resource_suffix
  domain           = var.domain
  backend_subdomain  = local.backend_subdomain
  frontend_subdomain = local.frontend_subdomain
  labels           = local.common_labels
}

# Database module - Cloud SQL and Redis
module "database" {
  source = "./modules/database"
  
  project_id       = var.project_id
  region           = var.region
  environment_name = local.environment_name
  resource_suffix  = local.resource_suffix
  network_id       = module.networking.network_id
  labels           = local.common_labels
  
  database_tier    = var.resource_limits.database_tier
  database_storage = var.resource_limits.database_storage_gb
  redis_tier       = var.resource_limits.redis_tier
  redis_memory_gb  = var.resource_limits.redis_memory_gb
}

# Compute module - Cloud Run services
module "compute" {
  source = "./modules/compute"
  
  project_id       = var.project_id
  region           = var.region
  environment_name = local.environment_name
  resource_suffix  = local.resource_suffix
  
  backend_image    = var.backend_image
  frontend_image   = var.frontend_image
  
  vpc_connector_id = module.networking.vpc_connector_id
  
  backend_url      = local.backend_url
  frontend_url     = local.frontend_url
  database_url     = module.database.database_url
  redis_url        = module.database.redis_url
  clickhouse_url   = module.database.clickhouse_url
  
  ssl_certificate_id = module.security.ssl_certificate_id
  
  cpu_limit        = local.cpu_limit
  memory_limit     = local.memory_limit
  min_instances    = local.min_instances
  max_instances    = local.max_instances
  
  environment_variables = merge(
    var.environment_variables,
    {
      STAGING_ENV     = "true"
      PR_NUMBER       = var.pr_number
      PR_BRANCH       = var.pr_branch
      STAGING_URL     = local.frontend_url
      API_URL         = local.backend_url
      NODE_ENV        = "production"
      PYTHON_ENV      = "production"
      LOG_LEVEL       = "INFO"
      CORS_ORIGINS    = jsonencode([local.frontend_url])
    }
  )
  
  secrets = module.security.secret_ids
  labels  = local.common_labels
  
  depends_on = [
    module.networking,
    module.database,
    module.security
  ]
}

# Set up load balancer and URL mapping
resource "google_compute_url_map" "staging" {
  name            = "staging-${local.resource_suffix}"
  default_service = module.compute.frontend_neg_id
  
  host_rule {
    hosts        = ["${local.frontend_subdomain}.${var.domain}"]
    path_matcher = "frontend"
  }
  
  host_rule {
    hosts        = ["${local.backend_subdomain}.${var.domain}"]
    path_matcher = "backend"
  }
  
  path_matcher {
    name            = "frontend"
    default_service = module.compute.frontend_neg_id
  }
  
  path_matcher {
    name            = "backend"
    default_service = module.compute.backend_neg_id
  }
}

resource "google_compute_target_https_proxy" "staging" {
  name             = "staging-proxy-${local.resource_suffix}"
  url_map          = google_compute_url_map.staging.id
  ssl_certificates = [module.security.ssl_certificate_id]
}

resource "google_compute_global_forwarding_rule" "staging" {
  name       = "staging-forwarding-${local.resource_suffix}"
  target     = google_compute_target_https_proxy.staging.id
  port_range = "443"
  ip_address = google_compute_global_address.staging.id
  
  labels = local.common_labels
}

resource "google_compute_global_address" "staging" {
  name   = "staging-ip-${local.resource_suffix}"
  labels = local.common_labels
}

# DNS records
resource "google_dns_record_set" "frontend" {
  name         = "${local.frontend_subdomain}.${var.domain}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_zone_name
  rrdatas      = [google_compute_global_address.staging.address]
}

resource "google_dns_record_set" "backend" {
  name         = "${local.backend_subdomain}.${var.domain}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_zone_name
  rrdatas      = [google_compute_global_address.staging.address]
}

# Monitoring and alerting
resource "google_monitoring_uptime_check_config" "staging" {
  display_name = "Staging PR-${var.pr_number} Health"
  timeout      = "10s"
  period       = "60s"
  
  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }
  
  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${local.backend_subdomain}.${var.domain}"
    }
  }
  
  selected_regions = ["USA"]
}

# Budget alert for this staging environment
resource "google_billing_budget" "staging" {
  billing_account = var.billing_account
  display_name    = "Staging PR-${var.pr_number} Budget"
  
  budget_filter {
    projects               = ["projects/${var.project_id}"]
    labels                 = local.common_labels
    calendar_period        = "MONTH"
  }
  
  amount {
    specified_amount {
      currency_code = "USD"
      units         = var.cost_limit_per_pr
    }
  }
  
  threshold_rules {
    threshold_percent = 0.5
  }
  
  threshold_rules {
    threshold_percent = 0.9
  }
  
  threshold_rules {
    threshold_percent = 1.0
  }
}