output "terraform_service_account_email" {
  description = "Email of the Terraform service account"
  value       = google_service_account.terraform.email
}

output "github_actions_service_account_email" {
  description = "Email of the GitHub Actions service account"
  value       = google_service_account.github_actions.email
}

output "workload_identity_pool_name" {
  description = "Workload Identity Pool name for GitHub Actions"
  value       = google_iam_workload_identity_pool.github.name
}

output "workload_identity_provider" {
  description = "Workload Identity Provider for GitHub Actions"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "api_key_secret_ids" {
  description = "Map of API key secret IDs"
  value       = { for k, v in google_secret_manager_secret.api_keys : k => v.secret_id }
}

output "oauth_secret_id" {
  description = "OAuth client secret ID"
  value       = google_secret_manager_secret.oauth_client.secret_id
}

output "jwt_secret_id" {
  description = "JWT secret ID"
  value       = google_secret_manager_secret.jwt_secret.secret_id
}

output "kms_key_ring_id" {
  description = "KMS key ring ID"
  value       = google_kms_key_ring.staging.id
}

output "kms_crypto_key_id" {
  description = "KMS crypto key ID"
  value       = google_kms_crypto_key.staging.id
}