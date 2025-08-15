# Password Generation Module - Simplified for Local Development
# Generates alphanumeric passwords without special characters

resource "random_string" "postgres_password" {
  length  = 20
  special = false
  upper   = true
  lower   = true
  numeric = true
}

resource "random_string" "app_password" {
  length  = 20
  special = false
  upper   = true
  lower   = true
  numeric = true
}

resource "random_string" "jwt_secret" {
  length  = 32
  special = false
  upper   = true
  lower   = true
  numeric = true
}

resource "random_string" "secret_key" {
  length  = 32
  special = false
  upper   = true
  lower   = true
  numeric = true
}