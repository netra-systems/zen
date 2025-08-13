# Security Module - IAM, Service Accounts, and Secrets Management

# Service Account for Terraform operations
resource "google_service_account" "terraform" {
  account_id   = "staging-terraform-${var.environment_name}"
  display_name = "Terraform Service Account for ${var.environment_name}"
  description  = "Service account used by Terraform to manage staging environment"
}

# Service Account for GitHub Actions CI/CD
resource "google_service_account" "github_actions" {
  account_id   = "staging-github-actions-${var.environment_name}"
  display_name = "GitHub Actions Service Account for ${var.environment_name}"
  description  = "Service account used by GitHub Actions for CI/CD"
}

# Workload Identity Pool for GitHub Actions
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "staging-github-${var.environment_name}"
  display_name              = "GitHub Actions Pool for ${var.environment_name}"
  description               = "Workload Identity Pool for GitHub Actions OIDC"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                        = "GitHub Provider"
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.environment" = "assertion.environment"
  }
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# IAM bindings for GitHub Actions
resource "google_service_account_iam_member" "github_actions_workload_identity" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

# Roles for GitHub Actions service account
resource "google_project_iam_member" "github_actions_roles" {
  for_each = toset([
    "roles/run.developer",
    "roles/artifactregistry.writer",
    "roles/secretmanager.secretAccessor",
    "roles/cloudsql.client",
    "roles/redis.editor"
  ])
  
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# API Keys (stored in Secret Manager)
resource "google_secret_manager_secret" "api_keys" {
  for_each = var.api_keys
  
  secret_id = "staging-${each.key}-${var.environment_name}"
  
  replication {
    auto {}
  }
  
  labels = merge(var.labels, {
    environment = var.environment_name
    type        = "api-key"
  })
}

resource "google_secret_manager_secret_version" "api_keys" {
  for_each = var.api_keys
  
  secret      = google_secret_manager_secret.api_keys[each.key].id
  secret_data = each.value
}

# OAuth Client Configuration
resource "google_secret_manager_secret" "oauth_client" {
  secret_id = "staging-oauth-client-${var.environment_name}"
  
  replication {
    auto {}
  }
  
  labels = merge(var.labels, {
    environment = var.environment_name
    type        = "oauth"
  })
}

resource "google_secret_manager_secret_version" "oauth_client" {
  secret = google_secret_manager_secret.oauth_client.id
  secret_data = jsonencode({
    client_id     = var.oauth_client_id
    client_secret = var.oauth_client_secret
  })
}

# JWT Secret for authentication
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "staging-jwt-secret-${var.environment_name}"
  
  replication {
    auto {}
  }
  
  labels = merge(var.labels, {
    environment = var.environment_name
    type        = "jwt"
  })
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

# KMS Key for additional encryption
resource "google_kms_key_ring" "staging" {
  name     = "staging-keyring-${var.environment_name}"
  location = var.region
}

resource "google_kms_crypto_key" "staging" {
  name            = "staging-key-${var.environment_name}"
  key_ring        = google_kms_key_ring.staging.id
  rotation_period = "7776000s" # 90 days
  
  lifecycle {
    prevent_destroy = false  # Allow destruction for staging
  }
}

# IAM Policy for accessing secrets
data "google_iam_policy" "secret_accessor" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    
    members = var.secret_accessor_members
  }
}

# Apply IAM policy to each secret
resource "google_secret_manager_secret_iam_policy" "api_keys" {
  for_each = google_secret_manager_secret.api_keys
  
  secret_id   = each.value.secret_id
  policy_data = data.google_iam_policy.secret_accessor.policy_data
}

# Security Command Center Notifications (optional)
resource "google_scc_notification_config" "staging" {
  count = var.enable_security_notifications ? 1 : 0
  
  config_id    = "staging-notifications-${var.environment_name}"
  organization = var.organization_id
  
  description = "Security notifications for staging environment ${var.environment_name}"
  
  pubsub_topic = var.security_pubsub_topic
  
  streaming_config {
    filter = "category=\"OPEN_FIREWALL\" OR category=\"PUBLIC_SQL_INSTANCE\""
  }
}

# Organization Policy Constraints (optional)
resource "google_organization_policy" "staging_policies" {
  for_each = var.enable_org_policies ? var.organization_policies : {}
  
  org_id     = var.organization_id
  constraint = each.key
  
  dynamic "list_policy" {
    for_each = each.value.list_policy != null ? [each.value.list_policy] : []
    content {
      allow {
        values = list_policy.value.allow_values
      }
      deny {
        values = list_policy.value.deny_values
      }
    }
  }
  
  dynamic "boolean_policy" {
    for_each = each.value.boolean_policy != null ? [each.value.boolean_policy] : []
    content {
      enforced = boolean_policy.value.enforced
    }
  }
}