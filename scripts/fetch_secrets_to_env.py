from shared.isolated_environment import get_env
"""Fetch secrets from Google Secret Manager and create .env file."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from google.cloud import secretmanager

# Import our centralized GCP auth config
from gcp_auth_config import GCPAuthConfig


def fetch_secret(client, project_id, secret_name, version="latest"):
    """Fetch a single secret from Secret Manager."""
    try:
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Warning: Failed to fetch secret {secret_name}: {e}")
        return None

def _get_project_id() -> str:
    """Get project ID from environment or use default."""
    # Determine project ID based on environment
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    default_project_id = "701982941522" if environment == "staging" else "304612253870"
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', default_project_id)
    print(f"Using project ID: {project_id} for environment: {environment}")
    return project_id

def _create_secret_client() -> secretmanager.SecretManagerServiceClient:
    """Initialize Secret Manager client with timeout."""
    # Ensure authentication is set up
    if not GCPAuthConfig.ensure_authentication():
        print("Error: Failed to set up GCP authentication")
        sys.exit(1)
    
    try:
        import socket
        socket.setdefaulttimeout(10)
        return secretmanager.SecretManagerServiceClient()
    except Exception as e:
        print(f"Error: Failed to create Secret Manager client: {e}")
        print("Authentication is configured but client creation failed.")
        sys.exit(1)

def _get_secret_mappings() -> dict[str, str]:
    """Return mapping of secret names to environment variable names."""
    # Comprehensive list of all secrets in Secret Manager
    return {
        # API Keys
        "gemini-api-key": "GEMINI_API_KEY",
        "openai-api-key": "OPENAI_API_KEY",
        "anthropic-api-key": "ANTHROPIC_API_KEY",
        "groq-api-key": "GROQ_API_KEY",
        "replicate-api-key": "REPLICATE_API_KEY",
        "perplexity-api-key": "PERPLEXITY_API_KEY",
        "netra-api-key": "NETRA_API_KEY",
        
        # Google OAuth
        "google-client-id": "GOOGLE_CLIENT_ID",
        "google-client-secret": "GOOGLE_CLIENT_SECRET",
        
        # Monitoring & Analytics
        "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
        "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
        "sentry-dsn": "SENTRY_DSN",
        "mixpanel-token": "MIXPANEL_TOKEN",
        "posthog-api-key": "POSTHOG_API_KEY",
        
        # Database Passwords
        "clickhouse-password": "CLICKHOUSE_PASSWORD",
        "postgres-password": "POSTGRES_PASSWORD",
        "postgres-staging-password": "POSTGRES_STAGING_PASSWORD",
        "postgres-production-password": "POSTGRES_PRODUCTION_PASSWORD",
        
        # Redis
        "redis-default": "REDIS_PASSWORD",
        "redis-staging-password": "REDIS_STAGING_PASSWORD",
        "redis-production-password": "REDIS_PRODUCTION_PASSWORD",
        
        # Security Keys
        "jwt-secret-key": "JWT_SECRET_KEY",
        "fernet-key": "FERNET_KEY",
        "encryption-key": "ENCRYPTION_KEY",
        "session-secret-key": "SESSION_SECRET_KEY",
        
        # Service URLs (for staging/production)
        "backend-url": "BACKEND_URL",
        "frontend-url": "FRONTEND_URL",
        "auth-service-url": "AUTH_SERVICE_URL",
        
        # Cloud Services
        "gcp-project-id": "GCP_PROJECT_ID",
        "aws-access-key-id": "AWS_ACCESS_KEY_ID",
        "aws-secret-access-key": "AWS_SECRET_ACCESS_KEY",
        
        # Email/Communication
        "sendgrid-api-key": "SENDGRID_API_KEY",
        "twilio-account-sid": "TWILIO_ACCOUNT_SID",
        "twilio-auth-token": "TWILIO_AUTH_TOKEN",
        
        # Payment Processing
        "stripe-secret-key": "STRIPE_SECRET_KEY",
        "stripe-publishable-key": "STRIPE_PUBLISHABLE_KEY",
        "stripe-webhook-secret": "STRIPE_WEBHOOK_SECRET"
    }

def _get_static_config() -> dict[str, str]:
    """Return static configuration values."""
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    
    # Base configuration
    config = {
        "ENVIRONMENT": environment,
        "CLICKHOUSE_USER": "default",
        "CLICKHOUSE_DB": "default",
        "POSTGRES_USER": "postgres",
        "POSTGRES_DB": "netra",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "LOG_LEVEL": "INFO",
        "DEBUG": "false",
        "PYTHONPATH": "/app",
        "PYTHONUNBUFFERED": "1"
    }
    
    return config

def _fetch_all_secrets(client: secretmanager.SecretManagerServiceClient, project_id: str, mappings: dict[str, str]) -> dict[str, str]:
    """Fetch all secrets and return environment variables."""
    print("Fetching secrets from Google Secret Manager...")
    env_vars = {}
    for secret_name, env_var in mappings.items():
        print(f"Fetching {secret_name}...")
        secret_value = fetch_secret(client, project_id, secret_name)
        if secret_value:
            env_vars[env_var] = secret_value
            print(f"  [OK] Successfully fetched {secret_name}")
        else:
            print(f"  [FAIL] Failed to fetch {secret_name}")
    return env_vars

def _check_env_file_exists(file_path: str) -> bool:
    """Check if env file exists and warn user if it does."""
    if os.path.exists(file_path):
        print(f"\n WARNING: [U+FE0F]  WARNING: {file_path} already exists!")
        print("To protect your existing configuration, this script will not overwrite it.")
        print("Options:")
        print("  1. Rename or backup your existing .env file")
        print("  2. Use .env.development for local overrides")
        print("  3. Delete .env if you want to regenerate it")
        return True
    return False

def _write_env_sections(f, env_vars: dict[str, str]) -> None:
    """Write all environment variable sections to file."""
    sections = [
        ("# Environment Configuration\n", ["ENVIRONMENT", "LOG_LEVEL", "DEBUG", "PYTHONPATH", "PYTHONUNBUFFERED"]),
        ("\n# Google OAuth Configuration\n", ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]),
        ("\n# API Keys - LLM Providers\n", ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "REPLICATE_API_KEY", "PERPLEXITY_API_KEY", "NETRA_API_KEY"]),
        ("\n# Monitoring & Analytics\n", ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "SENTRY_DSN", "MIXPANEL_TOKEN", "POSTHOG_API_KEY"]),
        ("\n# ClickHouse Configuration\n", ["CLICKHOUSE_HOST", "CLICKHOUSE_PORT", "CLICKHOUSE_USER", "CLICKHOUSE_DB", "CLICKHOUSE_PASSWORD"]),
        ("\n# PostgreSQL Configuration\n", ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "POSTGRES_STAGING_PASSWORD", "POSTGRES_PRODUCTION_PASSWORD"]),
        ("\n# Redis Configuration\n", ["REDIS_HOST", "REDIS_PORT", "REDIS_DB", "REDIS_PASSWORD", "REDIS_STAGING_PASSWORD", "REDIS_PRODUCTION_PASSWORD"]),
        ("\n# Security Keys\n", ["JWT_SECRET_KEY", "FERNET_KEY", "ENCRYPTION_KEY", "SESSION_SECRET_KEY"]),
        ("\n# Service URLs\n", ["BACKEND_URL", "FRONTEND_URL", "AUTH_SERVICE_URL"]),
        ("\n# Cloud Services\n", ["GCP_PROJECT_ID", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]),
        ("\n# Communication Services\n", ["SENDGRID_API_KEY", "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]),
        ("\n# Payment Processing\n", ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"])
    ]
    for header, keys in sections:
        f.write(header)
        for key in keys:
            if key in env_vars:
                f.write(f"{key}={env_vars[key]}\n")

def _write_env_file(file_path: str, env_vars: dict[str, str]) -> None:
    """Write environment variables to .env file."""
    print(f"\nCreating new {file_path}...")
    with open(file_path, "w") as f:
        f.write("# Initial .env file from Google Secret Manager\n")
        f.write("# Generated by fetch_secrets_to_env.py\n")
        f.write("# This file will NOT be overwritten on subsequent runs\n\n")
        _write_env_sections(f, env_vars)

def _print_summary(env_vars: dict[str, str], secret_mappings: dict[str, str], static_config: dict[str, str]) -> None:
    """Print summary of operation results."""
    print(f"[SUCCESS] Created .env with {len(env_vars)} configuration values")
    print("\nSummary:")
    secrets_count = len([k for k in env_vars if k in secret_mappings.values()])
    print(f"  - Fetched {secrets_count} secrets from Google Secret Manager")
    print(f"  - Added {len(static_config)} static configuration values")

def _process_and_write_env(env_vars: dict[str, str], secret_mappings: dict[str, str], static_config: dict[str, str]) -> None:
    """Process environment variables and write .env file if it doesn't exist."""
    if not _check_env_file_exists(".env"):
        _write_env_file(".env", env_vars)
        _print_summary(env_vars, secret_mappings, static_config)

def list_all_secrets(client: secretmanager.SecretManagerServiceClient, project_id: str) -> List[str]:
    """List all available secrets in the project."""
    print("\n[U+1F4CB] Listing all secrets in Secret Manager...")
    parent = f"projects/{project_id}"
    
    try:
        secrets = []
        for secret in client.list_secrets(request={"parent": parent}):
            secret_name = secret.name.split('/')[-1]
            secrets.append(secret_name)
            print(f"  - {secret_name}")
        
        return secrets
    except Exception as e:
        print(f"Error listing secrets: {e}")
        return []

def main():
    """Main function to fetch secrets and create .env file."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch secrets from GCP Secret Manager")
    parser.add_argument("--list", action="store_true", help="List all available secrets")
    parser.add_argument("--environment", default="development", 
                       choices=["development", "staging", "production"],
                       help="Environment to configure (default: development)")
    parser.add_argument("--force", action="store_true", 
                       help="Force overwrite existing .env file")
    args = parser.parse_args()
    
    # Set environment
    os.environ["ENVIRONMENT"] = args.environment
    
    project_id = _get_project_id()
    client = _create_secret_client()
    
    if args.list:
        # Just list secrets and exit
        secrets = list_all_secrets(client, project_id)
        print(f"\n PASS:  Found {len(secrets)} secrets in project {project_id}")
        return
    
    # Check for force flag
    if args.force and os.path.exists(".env"):
        print(" WARNING: [U+FE0F] Force flag set - backing up existing .env to .env.backup")
        import shutil
        shutil.copy(".env", ".env.backup")
        os.remove(".env")
    
    secret_mappings = _get_secret_mappings()
    static_config = _get_static_config()
    env_vars = {**_fetch_all_secrets(client, project_id, secret_mappings), **static_config}
    _process_and_write_env(env_vars, secret_mappings, static_config)

if __name__ == "__main__":
    main()
