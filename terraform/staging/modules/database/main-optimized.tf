# Optimized Database Module - Creates only databases, not instances
# This is MUCH faster - database creation takes seconds vs instance creation taking minutes

# Create a database in the shared instance
resource "google_sql_database" "pr_database" {
  name     = "netra_pr_${var.pr_number}"
  instance = var.shared_sql_instance_name
  
  # Clean up automatically when PR is closed
  lifecycle {
    create_before_destroy = false
  }
}

# Create a user for this PR's database
resource "google_sql_user" "pr_user" {
  name     = "pr_${var.pr_number}_user"
  instance = var.shared_sql_instance_name
  password = var.postgres_password
}

# Grant permissions to the PR user on the PR database
resource "null_resource" "grant_permissions" {
  provisioner "local-exec" {
    command = <<-EOT
      gcloud sql connect ${var.shared_sql_instance_name} --user=postgres --database=postgres << EOF
      GRANT ALL PRIVILEGES ON DATABASE netra_pr_${var.pr_number} TO pr_${var.pr_number}_user;
      EOF
    EOT
  }
  
  depends_on = [
    google_sql_database.pr_database,
    google_sql_user.pr_user
  ]
}

# For Redis, use database selection (0-15) instead of separate instances
locals {
  # Use PR number modulo 16 to select Redis database
  # This allows up to 16 concurrent PR environments
  redis_db_number = var.pr_number % 16
}

# Output connection strings
output "database_url" {
  value = "postgresql://${google_sql_user.pr_user.name}:${var.postgres_password}@${var.shared_sql_host}:5432/${google_sql_database.pr_database.name}"
}

output "redis_url" {
  value = "redis://${var.shared_redis_host}:${var.shared_redis_port}/${local.redis_db_number}"
}

output "clickhouse_url" {
  value = var.clickhouse_url  # Use shared development ClickHouse
}