# Google Secret Manager for storing sensitive configuration

# Secret for database URL (for backend services)
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.environment}-database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.cloudsql_connection_string
}

# Secret for direct database connection (for migrations/admin)
resource "google_secret_manager_secret" "database_url_direct" {
  secret_id = "${var.environment}-database-url-direct"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "database_url_direct" {
  secret      = google_secret_manager_secret.database_url_direct.id
  secret_data = local.app_connection_string
}

# Secret for Redis URL
resource "google_secret_manager_secret" "redis_url" {
  secret_id = "${var.environment}-redis-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = "redis://${google_redis_instance.redis.host}:${google_redis_instance.redis.port}"
}

# Secret for JWT secret
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "google_secret_manager_secret" "jwt_secret" {
  secret_id = "${var.environment}-jwt-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}

# Grant Cloud Run service account access to secrets
resource "google_secret_manager_secret_iam_member" "database_url_access" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_secret_manager_secret.database_url]
}

resource "google_secret_manager_secret_iam_member" "redis_url_access" {
  secret_id = google_secret_manager_secret.redis_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_secret_manager_secret.redis_url]
}

resource "google_secret_manager_secret_iam_member" "jwt_secret_access" {
  secret_id = google_secret_manager_secret.jwt_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [google_secret_manager_secret.jwt_secret]
}