"""
Unified secret mappings for Google Secrets Manager.

This module provides a single source of truth for mapping Google Secret names
to environment variable names across all services and environments.
"""

# Staging environment secret mappings
# Maps Google Secret Manager secret names to environment variable names
STAGING_SECRET_MAPPINGS = {
    # Database Secrets
    "postgres-host-staging": "POSTGRES_HOST",
    "postgres-port-staging": "POSTGRES_PORT",
    "postgres-db-staging": "POSTGRES_DB",
    "postgres-user-staging": "POSTGRES_USER",
    "postgres-password-staging": "POSTGRES_PASSWORD",
    
    # Redis Secrets
    "redis-password-staging": "REDIS_PASSWORD",
    "redis-host-staging": "REDIS_HOST",
    "redis-port-staging": "REDIS_PORT",
    
    # ClickHouse Secrets
    "clickhouse-password-staging": "CLICKHOUSE_PASSWORD",
    "clickhouse-host-staging": "CLICKHOUSE_HOST",
    "clickhouse-port-staging": "CLICKHOUSE_PORT",
    "clickhouse-user-staging": "CLICKHOUSE_USER",
    "clickhouse-db-staging": "CLICKHOUSE_DB",
    
    # Authentication Secrets
    "jwt-secret-key": "JWT_SECRET_KEY",
    "jwt-secret": "JWT_SECRET",  # Duplicate for compatibility
    "fernet-key": "FERNET_KEY",
    
    # OAuth Secrets
    "google-client-id": "GOOGLE_CLIENT_ID",
    "google-client-secret": "GOOGLE_CLIENT_SECRET",
    
    # AI/LLM API Keys
    "anthropic-api-key": "ANTHROPIC_API_KEY",
    "openai-api-key": "OPENAI_API_KEY",
    "gemini-api-key": "GEMINI_API_KEY",
    
    # Monitoring
    "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
    "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
}

# Production environment secret mappings
PRODUCTION_SECRET_MAPPINGS = {
    # Database Secrets
    "postgres-host-prod": "POSTGRES_HOST",
    "postgres-port-prod": "POSTGRES_PORT",
    "postgres-db-prod": "POSTGRES_DB",
    "postgres-user-prod": "POSTGRES_USER",
    "postgres-password-prod": "POSTGRES_PASSWORD",
    
    # Redis Secrets  
    "redis-password-prod": "REDIS_PASSWORD",
    "redis-host-prod": "REDIS_HOST",
    "redis-port-prod": "REDIS_PORT",
    
    # ClickHouse Secrets
    "clickhouse-password-prod": "CLICKHOUSE_PASSWORD",
    "clickhouse-host-prod": "CLICKHOUSE_HOST",
    "clickhouse-port-prod": "CLICKHOUSE_PORT",
    "clickhouse-user-prod": "CLICKHOUSE_USER",
    "clickhouse-db-prod": "CLICKHOUSE_DB",
    
    # Authentication Secrets (shared across environments)
    "jwt-secret-key": "JWT_SECRET_KEY",
    "jwt-secret": "JWT_SECRET",
    "fernet-key": "FERNET_KEY",
    
    # OAuth Secrets
    "google-client-id": "GOOGLE_CLIENT_ID",
    "google-client-secret": "GOOGLE_CLIENT_SECRET",
    
    # AI/LLM API Keys
    "anthropic-api-key": "ANTHROPIC_API_KEY",
    "openai-api-key": "OPENAI_API_KEY",
    "gemini-api-key": "GEMINI_API_KEY",
    
    # Monitoring
    "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
    "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
}

def get_secret_mappings(environment: str) -> dict:
    """
    Get secret mappings for a specific environment.
    
    Args:
        environment: The environment name ('staging', 'production', etc.)
        
    Returns:
        Dictionary mapping Google Secret names to environment variable names
    """
    environment = environment.lower()
    
    if environment == "staging":
        return STAGING_SECRET_MAPPINGS.copy()
    elif environment in ["production", "prod"]:
        return PRODUCTION_SECRET_MAPPINGS.copy()
    else:
        # Development/local environments don't use Google Secrets Manager
        return {}


def get_required_secrets(environment: str) -> set:
    """
    Get the set of required environment variables for an environment.
    
    Args:
        environment: The environment name
        
    Returns:
        Set of required environment variable names
    """
    mappings = get_secret_mappings(environment)
    return set(mappings.values())


def get_secret_name_for_env_var(env_var: str, environment: str) -> str:
    """
    Get the Google Secret name for a given environment variable.
    
    Args:
        env_var: The environment variable name
        environment: The environment name
        
    Returns:
        The Google Secret name, or None if not found
    """
    mappings = get_secret_mappings(environment)
    
    for secret_name, mapped_env_var in mappings.items():
        if mapped_env_var == env_var:
            return secret_name
    
    return None