output "backend_service_name" {
  value = google_cloud_run_v2_service.backend.name
}

output "frontend_service_name" {
  value = google_cloud_run_v2_service.frontend.name
}

output "backend_service_url" {
  value = google_cloud_run_v2_service.backend.uri
}

output "frontend_service_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "backend_neg_id" {
  value = google_compute_backend_service.backend.id
}

output "frontend_neg_id" {
  value = google_compute_backend_service.frontend.id
}

output "backend_service_account" {
  value = google_service_account.staging_backend.email
}

output "frontend_service_account" {
  value = google_service_account.staging_frontend.email
}