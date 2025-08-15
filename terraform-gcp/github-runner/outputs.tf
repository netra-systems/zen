# Service Account
output "service_account_email" {
  description = "Email of the GitHub runner service account"
  value       = google_service_account.github_runner.email
}

# Runner Instances
output "runner_instances" {
  description = "Details of created runner instances"
  value = {
    for idx, instance in google_compute_instance.github_runner : 
    instance.name => {
      name        = instance.name
      zone        = instance.zone
      internal_ip = instance.network_interface[0].network_ip
      external_ip = try(instance.network_interface[0].access_config[0].nat_ip, null)
      status      = instance.current_status
    }
  }
}

# Autoscaling Group
output "autoscaling_group" {
  description = "Autoscaling group details (if enabled)"
  value = var.enable_autoscaling ? {
    instance_group = google_compute_instance_group_manager.github_runner[0].name
    min_replicas   = var.min_runners
    max_replicas   = var.max_runners
    target_size    = google_compute_instance_group_manager.github_runner[0].target_size
  } : null
}

# Storage
output "artifacts_bucket" {
  description = "Name of the artifacts storage bucket"
  value       = google_storage_bucket.runner_artifacts.name
}

output "artifacts_bucket_url" {
  description = "URL of the artifacts storage bucket"
  value       = google_storage_bucket.runner_artifacts.url
}

# Configuration
output "runner_configuration" {
  description = "Runner configuration details"
  value = {
    organization = var.github_org
    repository   = var.github_repo != "" ? var.github_repo : null
    labels       = var.runner_labels
    group        = var.runner_group != "" ? var.runner_group : null
  }
}

# Connection Instructions
output "ssh_command" {
  description = "SSH command to connect to runners (if SSH is enabled)"
  value = var.enable_ssh ? {
    for idx, instance in google_compute_instance.github_runner :
    instance.name => "gcloud compute ssh --zone ${instance.zone} ${instance.name} --project ${var.project_id}"
  } : null
}

# Monitoring
output "monitoring_urls" {
  description = "URLs for monitoring the runners"
  value = {
    logs_explorer = "https://console.cloud.google.com/logs/query;query=resource.type%3D%22gce_instance%22%0Aresource.labels.instance_id%3D~%22github-runner%22?project=${var.project_id}"
    metrics       = "https://console.cloud.google.com/monitoring/metrics-explorer?project=${var.project_id}"
    compute       = "https://console.cloud.google.com/compute/instances?project=${var.project_id}"
  }
}