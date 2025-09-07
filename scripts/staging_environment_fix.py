#!/usr/bin/env python3
"""
Staging Environment Configuration Fix Script

This script configures the proper environment variables and secrets
needed for staging deployment to resolve HTTP 503 Service Unavailable errors.

CRITICAL: This addresses the root causes identified in Five Whys analysis:
1. Missing staging-specific environment variables
2. Incorrect configuration validation requirements
3. Missing GCP Secret Manager setup
4. OAuth configuration issues

Usage:
    python scripts/staging_environment_fix.py --setup-secrets
    python scripts/staging_environment_fix.py --validate-config
"""

import os
import sys
import subprocess
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.fernet import Fernet

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.windows_encoding import setup_windows_encoding

# Fix Unicode encoding issues on Windows
setup_windows_encoding()

# GCP project configuration
GCP_PROJECT = "netra-staging"
GCP_REGION = "us-central1"

# Required staging secrets and their descriptions
REQUIRED_SECRETS = {
    "jwt-secret-staging": "JWT secret for staging environment (86+ characters)",
    "database-password-staging": "PostgreSQL database password (32+ characters)", 
    "redis-password-staging": "Redis password (32+ characters)",
    "fernet-key-staging": "Fernet encryption key (32 bytes base64 encoded)",
    "gemini-api-key-staging": "Google Gemini API key for LLM operations",
    "google-oauth-client-id-staging": "Google OAuth client ID for staging",
    "google-oauth-client-secret-staging": "Google OAuth client secret for staging",
    "service-secret-staging": "Service-to-service authentication secret (32+ characters)",
    "clickhouse-password-staging": "ClickHouse database password"
}

# Staging environment variables that will be set in Cloud Run deployment
STAGING_ENV_VARS = {
    "ENVIRONMENT": "staging",
    "PYTHONUNBUFFERED": "1",
    "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
    "AUTH_SERVICE_ENABLED": "true",
    "FRONTEND_URL": "https://app.staging.netrasystems.ai",
    "FORCE_HTTPS": "true",
    "GCP_PROJECT_ID": GCP_PROJECT,
    
    # Database configuration (Cloud SQL)
    "POSTGRES_HOST": "/cloudsql/netra-staging:us-central1:netra-staging-db",
    "POSTGRES_USER": "netra_staging_user",
    "POSTGRES_DB": "netra_staging",
    "POSTGRES_PORT": "5432",
    
    # Redis configuration (Cloud Memorystore)
    "REDIS_HOST": "10.0.0.3",  # Internal IP of Cloud Memorystore instance
    "REDIS_PORT": "6379",
    "REDIS_REQUIRED": "true",
    
    # ClickHouse configuration
    "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
    "CLICKHOUSE_PORT": "8443", 
    "CLICKHOUSE_USER": "default",
    "CLICKHOUSE_DB": "default",
    "CLICKHOUSE_SECURE": "true",
    "CLICKHOUSE_REQUIRED": "true",
    
    # JWT Configuration
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "JWT_ACCESS_EXPIRY_MINUTES": "15",
    "JWT_REFRESH_EXPIRY_DAYS": "7",
    "JWT_SERVICE_EXPIRY_MINUTES": "60",
    
    # CORS Configuration
    "CORS_ALLOWED_ORIGINS": "https://app.staging.netrasystems.ai,https://api.staging.netrasystems.ai",
    
    # WebSocket timeout configuration for GCP staging
    "WEBSOCKET_CONNECTION_TIMEOUT": "900",
    "WEBSOCKET_HEARTBEAT_INTERVAL": "25",
    "WEBSOCKET_HEARTBEAT_TIMEOUT": "75",
    "WEBSOCKET_CLEANUP_INTERVAL": "180",
    "WEBSOCKET_STALE_TIMEOUT": "900",
}


def generate_secure_secret(length: int = 64) -> str:
    """Generate a secure random secret."""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_fernet_key() -> str:
    """Generate a Fernet encryption key."""
    key = Fernet.generate_key()
    return key.decode('utf-8')


def check_gcp_auth() -> bool:
    """Check if user is authenticated with GCP."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        accounts = json.loads(result.stdout)
        return len(accounts) > 0
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return False


def setup_gcp_secrets() -> bool:
    """Create all required secrets in GCP Secret Manager."""
    if not check_gcp_auth():
        print("❌ Not authenticated with GCP. Run: gcloud auth login")
        return False
    
    print(f"🔧 Setting up secrets in GCP project: {GCP_PROJECT}")
    
    # Generate secrets
    secrets_data = {
        "jwt-secret-staging": generate_secure_secret(86),  # Extra long for JWT
        "database-password-staging": generate_secure_secret(32),
        "redis-password-staging": generate_secure_secret(32), 
        "fernet-key-staging": generate_fernet_key(),
        "gemini-api-key-staging": "PLACEHOLDER_GEMINI_API_KEY_STAGING",  # Must be manually set
        "google-oauth-client-id-staging": "PLACEHOLDER_GOOGLE_CLIENT_ID_STAGING",  # Must be manually set
        "google-oauth-client-secret-staging": "PLACEHOLDER_GOOGLE_CLIENT_SECRET_STAGING",  # Must be manually set
        "service-secret-staging": generate_secure_secret(64),
        "clickhouse-password-staging": "PLACEHOLDER_CLICKHOUSE_PASSWORD_STAGING"  # Must be manually set
    }
    
    success_count = 0
    total_secrets = len(secrets_data)
    
    for secret_name, secret_value in secrets_data.items():
        try:
            # Create secret
            result = subprocess.run([
                "gcloud", "secrets", "create", secret_name,
                f"--project={GCP_PROJECT}",
                "--replication-policy=automatic"
            ], capture_output=True, text=True)
            
            if result.returncode != 0 and "already exists" not in result.stderr:
                print(f"⚠️  Failed to create secret {secret_name}: {result.stderr}")
                continue
            
            # Add secret version
            echo_process = subprocess.Popen(
                ["echo", secret_value],
                stdout=subprocess.PIPE,
                text=True
            )
            
            add_result = subprocess.run([
                "gcloud", "secrets", "versions", "add", secret_name,
                f"--project={GCP_PROJECT}",
                "--data-file=-"
            ], stdin=echo_process.stdout, capture_output=True, text=True)
            
            echo_process.stdout.close()
            echo_process.wait()
            
            if add_result.returncode == 0:
                if "PLACEHOLDER" in secret_value:
                    print(f"⚠️  Created {secret_name} with PLACEHOLDER - MUST UPDATE MANUALLY")
                else:
                    print(f"✅ Created secret: {secret_name}")
                success_count += 1
            else:
                print(f"❌ Failed to add secret version for {secret_name}: {add_result.stderr}")
                
        except Exception as e:
            print(f"❌ Error creating secret {secret_name}: {e}")
    
    print(f"\n📊 Secret creation summary: {success_count}/{total_secrets} secrets created")
    
    if success_count < total_secrets:
        print("\n⚠️  MANUAL STEPS REQUIRED:")
        print("   1. Set real GEMINI_API_KEY in gemini-api-key-staging")
        print("   2. Set real Google OAuth credentials in google-oauth-*-staging secrets") 
        print("   3. Set real ClickHouse password in clickhouse-password-staging")
        print("\n   Use: gcloud secrets versions add SECRET_NAME --data-file=secret.txt")
    
    return success_count == total_secrets


def validate_staging_config() -> bool:
    """Validate staging configuration meets requirements."""
    print("🔍 Validating staging configuration...")
    
    # Test with proper staging environment variables
    test_env = os.environ.copy()
    test_env.update(STAGING_ENV_VARS)
    
    # Add mock secrets for validation
    test_env.update({
        "JWT_SECRET_STAGING": generate_secure_secret(86),
        "JWT_SECRET": generate_secure_secret(86),  # Fallback
        "SERVICE_SECRET": generate_secure_secret(64),
        "DATABASE_PASSWORD": generate_secure_secret(32),
        "REDIS_PASSWORD": generate_secure_secret(32),
        "FERNET_KEY": generate_fernet_key(),
        "GEMINI_API_KEY": "test-gemini-key-for-validation",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "test-staging-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "test-staging-client-secret",
    })
    
    try:
        # Test startup validation
        validation_script = '''
import sys
import asyncio
sys.path.insert(0, ".")

from netra_backend.app.core.startup_validator import validate_startup

async def test():
    success = await validate_startup()
    return success

result = asyncio.run(test())
print("VALIDATION_RESULT:", result)
'''
        
        result = subprocess.run([
            sys.executable, "-c", validation_script
        ], env=test_env, capture_output=True, text=True, cwd=project_root)
        
        if "VALIDATION_RESULT: True" in result.stdout:
            print("✅ Staging configuration validation PASSED")
            return True
        else:
            print("❌ Staging configuration validation FAILED")
            print("STDOUT:", result.stdout[-1000:])  # Last 1000 chars
            print("STDERR:", result.stderr[-1000:])  # Last 1000 chars
            return False
            
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


def generate_deployment_command() -> str:
    """Generate the correct GCP deployment command with all secrets."""
    secret_flags = []
    for secret_name in REQUIRED_SECRETS.keys():
        secret_flags.append(f"--set-secrets={secret_name.upper().replace('-', '_')}={secret_name}:latest")
    
    env_flags = []
    for key, value in STAGING_ENV_VARS.items():
        env_flags.append(f"--set-env-vars={key}={value}")
    
    command = f"""
# Deploy backend with proper secrets and environment variables
gcloud run deploy netra-backend-staging \\
  --source . \\
  --project {GCP_PROJECT} \\
  --region {GCP_REGION} \\
  --memory 2Gi \\
  --cpu 2 \\
  --min-instances 1 \\
  --max-instances 10 \\
  --timeout 1800 \\
  --port 8000 \\
  {' \\\n  '.join(env_flags)} \\
  {' \\\n  '.join(secret_flags)}
"""
    return command


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix staging environment configuration")
    parser.add_argument("--setup-secrets", action="store_true", 
                       help="Setup secrets in GCP Secret Manager")
    parser.add_argument("--validate-config", action="store_true",
                       help="Validate staging configuration")
    parser.add_argument("--generate-deploy-command", action="store_true",
                       help="Generate deployment command")
    
    args = parser.parse_args()
    
    if args.setup_secrets:
        success = setup_gcp_secrets()
        if success:
            print("\n✅ All secrets created successfully!")
        else:
            print("\n❌ Some secrets failed to create. See output above.")
            sys.exit(1)
    
    elif args.validate_config:
        success = validate_staging_config()
        if success:
            print("\n✅ Staging configuration is valid!")
        else:
            print("\n❌ Staging configuration validation failed!")
            sys.exit(1)
    
    elif args.generate_deploy_command:
        command = generate_deployment_command()
        print("🚀 Deployment command:")
        print(command)
    
    else:
        parser.print_help()
        
        print("\n📋 Current status:")
        print(f"   GCP Project: {GCP_PROJECT}")
        print(f"   Required secrets: {len(REQUIRED_SECRETS)}")
        print(f"   Environment variables: {len(STAGING_ENV_VARS)}")
        
        auth_status = "✅ Authenticated" if check_gcp_auth() else "❌ Not authenticated"
        print(f"   GCP Auth: {auth_status}")


if __name__ == "__main__":
    main()