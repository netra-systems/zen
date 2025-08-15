# Output File Generation

resource "local_file" "env_file" {
  filename = "${path.module}/../.env.development.local"
  content  = templatefile("${path.module}/templates/env.development.tpl", {
    postgres_host          = "localhost"
    postgres_port          = var.postgres_port
    postgres_db            = var.postgres_db
    postgres_user          = var.postgres_user
    postgres_password      = random_string.postgres_password.result
    app_user               = var.app_user
    app_password           = random_string.app_password.result
    redis_host             = "localhost"
    redis_port             = var.redis_port
    clickhouse_host        = "localhost"
    clickhouse_http_port   = var.clickhouse_http_port
    clickhouse_native_port = var.clickhouse_native_port
    clickhouse_db          = var.clickhouse_db
    clickhouse_user        = var.clickhouse_user
    clickhouse_password    = var.clickhouse_password
    jwt_secret             = random_string.jwt_secret.result
    secret_key             = random_string.secret_key.result
  })
  
  depends_on = [
    docker_container.postgres_dev,
    docker_container.redis_dev,
    docker_container.clickhouse_dev
  ]
}

resource "local_file" "connection_info" {
  filename = "${path.module}/connection_info.txt"
  content  = <<-EOT
    Development Database Connection Information
    ==========================================
    
    PostgreSQL:
    - Host: localhost
    - Port: ${var.postgres_port}
    - Database: ${var.postgres_db}
    - User: ${var.postgres_user}
    - Password: ${random_string.postgres_password.result}
    - Connection String: postgresql+asyncpg://${var.postgres_user}:${random_string.postgres_password.result}@localhost:${var.postgres_port}/${var.postgres_db}
    
    Redis:
    - Host: localhost
    - Port: ${var.redis_port}
    - Connection String: redis://localhost:${var.redis_port}/0
    
    ClickHouse:
    - Host: localhost
    - HTTP Port: ${var.clickhouse_http_port}
    - Native Port: ${var.clickhouse_native_port}
    - Database: ${var.clickhouse_db}
    - User: ${var.clickhouse_user}
    - Password: ${var.clickhouse_password}
    - Connection String: clickhouse://${var.clickhouse_user}:${var.clickhouse_password}@localhost:${var.clickhouse_native_port}/${var.clickhouse_db}
    
    Application Credentials:
    - App User: ${var.app_user}
    - App Password: ${random_string.app_password.result}
    
    Security Keys:
    - JWT Secret: ${random_string.jwt_secret.result}
    - Secret Key: ${random_string.secret_key.result}
    
    Docker Network: netra-dev-network
    
    To connect from application:
    - Use the connection strings above in your .env.development file
    - Or use the auto-generated .env.development.local file
    
    To manage:
    - Start: terraform apply
    - Stop: terraform destroy
    - View logs: docker logs netra-postgres-dev
    - Connect: psql -h localhost -p ${var.postgres_port} -U ${var.postgres_user} -d ${var.postgres_db}
  EOT
}