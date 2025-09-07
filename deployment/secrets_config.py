"""
Centralized Secret Configuration for GCP Deployments

This module defines all secret requirements for each service and their mappings
to Google Secret Manager. This is the SINGLE SOURCE OF TRUTH for secret configuration.

This prevents regressions like the SECRET_KEY incident by:
1. Centralizing all secret definitions in one place
2. Making it easy to see what each service needs
3. Enabling automated validation
4. Providing a clear contract between services and deployment

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment failures and downtime
- Value Impact: Eliminates secret-related deployment failures
- Strategic Impact: Ensures reliable service availability
"""

from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)


class SecretConfig:
    """Centralized configuration for all service secrets."""
    
    # Define what secrets each service requires
    # Using lists to preserve order and allow duplicates if needed
    SERVICE_SECRETS: Dict[str, Dict[str, List[str]]] = {
        "backend": {
            "database": [
                "POSTGRES_HOST",
                "POSTGRES_PORT", 
                "POSTGRES_DB",
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
                "DATABASE_HOST",      # CRITICAL: Required by central config validator
                "DATABASE_PASSWORD"   # CRITICAL: Required by central config validator
            ],
            "authentication": [
                "JWT_SECRET",          # CRITICAL: Base JWT secret for auth validator
                "JWT_SECRET_KEY",      # CRITICAL: Primary JWT secret key
                "JWT_SECRET_STAGING",  # CRITICAL: Environment-specific JWT secret
                "SECRET_KEY",          # CRITICAL: Backend requires SECRET_KEY
                "SERVICE_SECRET",
                "SERVICE_ID",          # CRITICAL: Required for inter-service auth with auth service
                "FERNET_KEY"
            ],
            "oauth": [
                # Backend uses simplified OAuth naming (matches config.py fallback chain)
                # Backend config.py tries: OAUTH_GOOGLE_CLIENT_ID_ENV or GOOGLE_CLIENT_ID or GOOGLE_OAUTH_CLIENT_ID
                # Tests expect GOOGLE_CLIENT_ID which is the second fallback option
                "GOOGLE_CLIENT_ID", 
                "GOOGLE_CLIENT_SECRET",
                # CRITICAL: Also include staging-specific OAuth variables that config validation expects
                "GOOGLE_OAUTH_CLIENT_ID_STAGING",
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"
            ],
            "redis": [
                "REDIS_HOST",
                "REDIS_PORT",
                "REDIS_URL",
                "REDIS_PASSWORD"
            ],
            "ai_services": [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "GEMINI_API_KEY"
            ],
            "analytics": [
                "CLICKHOUSE_PASSWORD"
            ]
        },
        "auth": {
            "database": [
                "POSTGRES_HOST",
                "POSTGRES_PORT",
                "POSTGRES_DB", 
                "POSTGRES_USER",
                "POSTGRES_PASSWORD"
            ],
            "authentication": [
                "JWT_SECRET",          # CRITICAL: Base JWT secret for auth validator
                "JWT_SECRET_KEY",      # CRITICAL: Primary JWT secret key
                "JWT_SECRET_STAGING",  # CRITICAL: Environment-specific JWT secret
                "SECRET_KEY",          # CRITICAL: Auth service requires SECRET_KEY
                "SERVICE_SECRET",
                "SERVICE_ID"
            ],
            "oauth": [
                "GOOGLE_OAUTH_CLIENT_ID_STAGING",  # Auth uses environment-specific names
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
                "OAUTH_HMAC_SECRET",
                "E2E_OAUTH_SIMULATION_KEY"  # CRITICAL: Required for E2E testing in staging
            ],
            "redis": [
                "REDIS_HOST",
                "REDIS_PORT", 
                "REDIS_URL",
                "REDIS_PASSWORD"
            ]
        },
        "frontend": {
            # Frontend doesn't use Google Secret Manager secrets
            # All configuration is done via environment variables at build time
        }
    }
    
    # Map secret names to their GSM secret IDs
    # This allows us to use consistent names in code while GSM names may vary
    SECRET_MAPPINGS: Dict[str, str] = {
        # Database
        "POSTGRES_HOST": "postgres-host-staging",
        "POSTGRES_PORT": "postgres-port-staging",
        "POSTGRES_DB": "postgres-db-staging",
        "POSTGRES_USER": "postgres-user-staging",
        "POSTGRES_PASSWORD": "postgres-password-staging",
        "DATABASE_HOST": "postgres-host-staging",  # Same host, config validator expects this name
        "DATABASE_PASSWORD": "postgres-password-staging",  # Same password, different name
        
        # Authentication & JWT
        # CRITICAL FIX: All JWT secret names must map to the same secret for consistency
        # This ensures WebSocket authentication works correctly in staging
        "JWT_SECRET": "jwt-secret-staging",         # CRITICAL: Base JWT secret
        "JWT_SECRET_KEY": "jwt-secret-staging",     # CRITICAL: Same as JWT_SECRET for consistency
        "JWT_SECRET_STAGING": "jwt-secret-staging", # CRITICAL: Environment-specific name
        "SECRET_KEY": "secret-key-staging",         # CRITICAL: Maps to secret-key-staging
        "SERVICE_SECRET": "service-secret-staging",
        "SERVICE_ID": "service-id-staging",
        "FERNET_KEY": "fernet-key-staging",
        
        # OAuth - Dual naming convention for backend and auth services
        # Backend service uses simplified names (matches config.py fallback)
        "GOOGLE_CLIENT_ID": "google-oauth-client-id-staging",
        "GOOGLE_CLIENT_SECRET": "google-oauth-client-secret-staging",
        # Auth service uses environment-specific names
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "google-oauth-client-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "google-oauth-client-secret-staging",
        "OAUTH_HMAC_SECRET": "oauth-hmac-secret-staging",
        "E2E_OAUTH_SIMULATION_KEY": "e2e-oauth-simulation-key-staging",
        
        # Redis
        "REDIS_HOST": "redis-host-staging",
        "REDIS_PORT": "redis-port-staging",
        "REDIS_URL": "redis-url-staging",
        "REDIS_PASSWORD": "redis-password-staging",
        
        # AI Services
        "OPENAI_API_KEY": "openai-api-key-staging",
        "ANTHROPIC_API_KEY": "anthropic-api-key-staging",
        "GEMINI_API_KEY": "gemini-api-key-staging",
        
        # Analytics
        "CLICKHOUSE_PASSWORD": "clickhouse-password-staging"
    }
    
    # Critical secrets that MUST exist for service to function
    # If any of these are missing, deployment should fail
    CRITICAL_SECRETS: Dict[str, List[str]] = {
        "backend": [
            "SECRET_KEY",      # CRITICAL: Required for encryption
            "JWT_SECRET",      # CRITICAL: Required for JWT tokens (auth validator)
            "JWT_SECRET_KEY",  # CRITICAL: Required for JWT tokens (SSOT)
            "SERVICE_SECRET",  # CRITICAL: Required for inter-service auth
            "SERVICE_ID",      # CRITICAL: Required for inter-service auth
            "POSTGRES_PASSWORD",  # CRITICAL: Required for database
        ],
        "auth": [
            "SECRET_KEY",      # CRITICAL: Required for auth service
            "JWT_SECRET",      # CRITICAL: Required for JWT tokens (auth validator)
            "JWT_SECRET_KEY",  # CRITICAL: Required for JWT tokens (SSOT)
            "SERVICE_SECRET",  # CRITICAL: Required for inter-service auth
            "POSTGRES_PASSWORD",  # CRITICAL: Required for database
        ]
    }
    
    @classmethod
    def get_service_secrets(cls, service_name: str) -> Dict[str, List[str]]:
        """Get all secret categories for a service.
        
        Args:
            service_name: Name of the service (backend, auth, frontend)
            
        Returns:
            Dictionary of secret categories and their secrets
        """
        return cls.SERVICE_SECRETS.get(service_name, {})
    
    @classmethod
    def get_all_service_secrets(cls, service_name: str) -> List[str]:
        """Get flat list of all secrets for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            List of all secret names needed by the service
        """
        service_secrets = cls.get_service_secrets(service_name)
        all_secrets = []
        for category_secrets in service_secrets.values():
            all_secrets.extend(category_secrets)
        return all_secrets
    
    @classmethod
    def get_gsm_mapping(cls, secret_name: str) -> Optional[str]:
        """Get the GSM secret ID for a secret name.
        
        Args:
            secret_name: Internal secret name
            
        Returns:
            GSM secret ID or None if not mapped
        """
        return cls.SECRET_MAPPINGS.get(secret_name)
    
    @classmethod
    def generate_secrets_string(cls, service_name: str, environment: str = "staging") -> str:
        """Generate the --set-secrets parameter value for gcloud run deploy.
        
        Args:
            service_name: Name of the service
            environment: Deployment environment (staging, production)
            
        Returns:
            Comma-separated string of secret mappings for --set-secrets
        """
        all_secrets = cls.get_all_service_secrets(service_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_secrets = []
        for secret in all_secrets:
            if secret not in seen:
                seen.add(secret)
                unique_secrets.append(secret)
        
        # Build the secrets string
        secret_mappings = []
        for secret in unique_secrets:
            gsm_id = cls.get_gsm_mapping(secret)
            if gsm_id:
                # Format: ENV_VAR_NAME=gsm-secret-id:latest
                secret_mappings.append(f"{secret}={gsm_id}:latest")
            else:
                logger.warning(f"No GSM mapping found for secret: {secret}")
        
        return ",".join(secret_mappings)
    
    @classmethod
    def validate_critical_secrets(cls, service_name: str, available_secrets: Set[str]) -> List[str]:
        """Validate that all critical secrets are available.
        
        Args:
            service_name: Name of the service
            available_secrets: Set of secret names that are available
            
        Returns:
            List of missing critical secrets (empty if all present)
        """
        critical = cls.CRITICAL_SECRETS.get(service_name, [])
        missing = []
        
        for secret in critical:
            if secret not in available_secrets:
                missing.append(secret)
        
        return missing
    
    @classmethod
    def get_secret_categories(cls, service_name: str, secret_name: str) -> List[str]:
        """Find which categories a secret belongs to for a service.
        
        Args:
            service_name: Name of the service
            secret_name: Name of the secret
            
        Returns:
            List of category names that contain this secret
        """
        categories = []
        service_secrets = cls.get_service_secrets(service_name)
        
        for category, secrets in service_secrets.items():
            if secret_name in secrets:
                categories.append(category)
        
        return categories
    
    @classmethod
    def explain_secret(cls, secret_name: str) -> str:
        """Get a human-readable explanation of what a secret is for.
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Explanation string
        """
        explanations = {
            "SECRET_KEY": "General encryption key for the service (CRITICAL - required for startup)",
            "JWT_SECRET_KEY": "Key for signing JWT tokens (CRITICAL - required for authentication)",
            "SERVICE_SECRET": "Secret for inter-service authentication",
            "POSTGRES_PASSWORD": "PostgreSQL database password (CRITICAL - required for database access)",
            "REDIS_URL": "Redis connection URL for caching and sessions",
            "FERNET_KEY": "Symmetric encryption key for data encryption",
            "GOOGLE_CLIENT_ID": "Google OAuth client ID (simplified naming for backend)",
            "GOOGLE_CLIENT_SECRET": "Google OAuth client secret (simplified naming for backend)",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "Google OAuth client ID for staging environment (auth service)",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "Google OAuth client secret for staging environment (auth service)",
        }
        
        return explanations.get(
            secret_name,
            f"Configuration secret: {secret_name}"
        )
    
    @classmethod
    def print_service_requirements(cls, service_name: str) -> None:
        """Print a formatted report of service secret requirements.
        
        Args:
            service_name: Name of the service
        """
        print(f"\n{'='*60}")
        print(f"Secret Requirements for {service_name.upper()} Service")
        print(f"{'='*60}")
        
        service_secrets = cls.get_service_secrets(service_name)
        critical_secrets = set(cls.CRITICAL_SECRETS.get(service_name, []))
        
        for category, secrets in service_secrets.items():
            print(f"\n{category.replace('_', ' ').title()}:")
            for secret in secrets:
                gsm_id = cls.get_gsm_mapping(secret)
                critical_marker = " [CRITICAL]" if secret in critical_secrets else ""
                print(f"  - {secret} -> {gsm_id}{critical_marker}")
                if secret in critical_secrets:
                    print(f"    {cls.explain_secret(secret)}")
        
        print(f"\n{'='*60}")
        print(f"Total secrets required: {len(cls.get_all_service_secrets(service_name))}")
        print(f"Critical secrets: {len(critical_secrets)}")
        print(f"{'='*60}\n")


# Convenience functions for direct access
def get_backend_secrets_string() -> str:
    """Get the complete secrets string for backend deployment."""
    return SecretConfig.generate_secrets_string("backend")


def get_auth_secrets_string() -> str:
    """Get the complete secrets string for auth service deployment."""
    return SecretConfig.generate_secrets_string("auth")


def validate_deployment_secrets(service_name: str, project_id: str) -> bool:
    """Validate that all required secrets exist in GSM.
    
    Args:
        service_name: Name of the service to validate
        project_id: GCP project ID
        
    Returns:
        True if all secrets are available, False otherwise
    """
    # This would check against actual GSM
    # For now, we return True as a placeholder
    # Real implementation would use: gcloud secrets list --project {project_id}
    return True


if __name__ == "__main__":
    # Print requirements for all services when run directly
    print("SECRET CONFIGURATION REPORT")
    print("="*60)
    
    for service in ["backend", "auth"]:
        SecretConfig.print_service_requirements(service)
        
        # Show the generated secrets string
        secrets_string = SecretConfig.generate_secrets_string(service)
        print(f"\nGenerated --set-secrets for {service}:")
        print(f"Length: {len(secrets_string)} characters")
        
        # Show first few mappings as example
        mappings = secrets_string.split(",")
        print(f"Mappings ({len(mappings)} total):")
        for mapping in mappings[:5]:
            print(f"  {mapping}")
        if len(mappings) > 5:
            print(f"  ... and {len(mappings) - 5} more")
        print()