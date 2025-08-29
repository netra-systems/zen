"""Test configuration for modern category-based testing."""

import multiprocessing
import os
from typing import Any, Dict

# Determine optimal parallelization
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)  # Leave one CPU free

# Component mappings for focused testing
COMPONENT_MAPPINGS = {
    "backend": {
        "paths": ["netra_backend/tests"],
        "exclude": ["frontend", "auth_service"]
    },
    "frontend": {
        "paths": ["frontend/__tests__"],
        "exclude": []
    },
    "auth": {
        "paths": ["netra_backend/tests/auth_integration", "auth_service/tests"],
        "exclude": []
    },
    "agents": {
        "paths": ["netra_backend/tests/agents"],
        "exclude": []
    },
    "database": {
        "paths": ["netra_backend/tests/database", "netra_backend/tests/clickhouse"],
        "exclude": []
    },
    "websocket": {
        "paths": ["netra_backend/tests/websocket", "netra_backend/tests/ws_manager"],
        "exclude": []
    }
}

# Shard mappings for CI/CD parallel execution (numeric sharding)
SHARD_MAPPINGS = {
    "1/4": ["netra_backend/app/core", "netra_backend/app/config", "netra_backend/app/dependencies"],
    "2/4": ["netra_backend/app/agents", "netra_backend/app/services/agent"],
    "3/4": ["netra_backend/app/ws_manager", "netra_backend/app/services/websocket", "netra_backend/app/db", "netra_backend/app/services/database"],
    "4/4": ["netra_backend/app/routes", "test_api", "test_auth", "frontend"]
}

# Test levels configuration
TEST_LEVELS = {
    "unit": ["tests/unit", "tests/core"],
    "integration": ["tests/integration", "tests/e2e"],
    "smoke": ["tests/integration/critical_paths"],
    "e2e": ["tests/e2e"],
    "agents": ["tests/agents"],
}

# Runners configuration for different test types
RUNNERS = {
    "backend": {
        "command": "pytest",
        "paths": ["netra_backend/tests"],
        "options": ["-v", "--tb=short"]
    },
    "auth": {
        "command": "pytest",
        "paths": ["auth_service/tests"],
        "options": ["-v", "--tb=short"]
    },
    "frontend": {
        "command": "npm",
        "paths": ["frontend"],
        "options": ["test"]
    },
    "dev_launcher": {
        "command": "pytest",
        "paths": ["tests"],
        "options": ["-v", "--tb=short"]
    }
}

def configure_staging_environment(staging_url: str, staging_api_url: str):
    """Configure environment variables for staging testing."""
    os.environ["STAGING_MODE"] = "true"
    os.environ["STAGING_URL"] = staging_url
    os.environ["STAGING_API_URL"] = staging_api_url
    os.environ["BASE_URL"] = staging_url
    os.environ["API_BASE_URL"] = staging_api_url
    os.environ["CYPRESS_BASE_URL"] = staging_url
    os.environ["CYPRESS_API_URL"] = staging_api_url

def configure_dev_environment():
    """Configure environment variables for dev mode testing."""
    # Set environment to development
    os.environ["ENVIRONMENT"] = "development"
    
    # Remove TESTING environment variable if present to allow dev mode detection
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    
    # Configure dev service URLs
    os.environ["DEV_MODE"] = "true"
    os.environ["BASE_URL"] = "http://localhost:8001"
    os.environ["API_BASE_URL"] = "http://localhost:8001"
    os.environ["BACKEND_URL"] = "http://localhost:8001"
    
    # Frontend URLs (if needed)
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    
    # Database and service URLs for dev environment
    os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/netra_dev"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["CLICKHOUSE_URL"] = "http://localhost:8123"

def configure_test_environment():
    """Configure environment variables for testing mode."""
    # Set environment to testing  
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["TESTING"] = "true"
    
    # Skip heavy startup checks during testing
    os.environ["SKIP_STARTUP_CHECKS"] = "true"
    os.environ["TEST_COLLECTION_MODE"] = "false"
    
    # Configure test service URLs
    os.environ["BASE_URL"] = "http://localhost:8001"
    os.environ["API_BASE_URL"] = "http://localhost:8001" 
    os.environ["BACKEND_URL"] = "http://localhost:8001"
    
    # Frontend URLs (if needed)
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    
    # Database and service URLs for test environment
    # Use test-specific database to avoid conflicts with dev data
    os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/netra_test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use DB 1 for tests
    os.environ["CLICKHOUSE_URL"] = "http://localhost:8123"

# LLM configuration functions moved to test_framework.llm_config_manager
# Import the canonical function for backward compatibility
from test_framework.llm_config_manager import configure_llm_testing, LLMTestMode

def configure_real_llm(model: str = "gemini-2.5-flash", 
                       timeout: int = 60, 
                       parallel: str = "auto", 
                       test_level: str = None, 
                       use_dedicated_env: bool = True):
    """DEPRECATED: Use test_framework.llm_config_manager.configure_llm_testing instead.
    
    This function is maintained for backward compatibility only.
    All LLM configuration has been consolidated into llm_config_manager.py.
    """
    import warnings
    warnings.warn(
        "configure_real_llm in test_config.py is deprecated. "
        "Use test_framework.llm_config_manager.configure_llm_testing instead",
        DeprecationWarning,
        stacklevel=2
    )
    
    return configure_llm_testing(
        mode=LLMTestMode.REAL,
        model=model,
        timeout=timeout,
        parallel=parallel,
        use_dedicated_env=use_dedicated_env
    )


def configure_dedicated_test_environment():
    """Configure dedicated test environment with isolated resources."""
    # Database configuration for test_dedicated environment
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        # Fallback to main database with test schema
        main_db_url = os.getenv("DATABASE_URL", "postgresql://localhost/netra_main")
        test_db_url = main_db_url.replace("/netra_main", "/netra_test")
        os.environ["TEST_DATABASE_URL"] = test_db_url
    
    # Redis configuration with test namespace
    test_redis_url = os.getenv("TEST_REDIS_URL")
    if not test_redis_url:
        main_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # Use database index 1 for tests
        test_redis_url = main_redis_url.replace("/0", "/1")
        os.environ["TEST_REDIS_URL"] = test_redis_url
    
    # Set Redis namespace prefix for test isolation
    os.environ["TEST_REDIS_NAMESPACE"] = "test:"
    
    # ClickHouse configuration with test database
    test_clickhouse_url = os.getenv("TEST_CLICKHOUSE_URL")
    if not test_clickhouse_url:
        main_clickhouse_url = os.getenv("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_main")
        test_clickhouse_url = main_clickhouse_url.replace("/netra_main", "/netra_test")
        os.environ["TEST_CLICKHOUSE_URL"] = test_clickhouse_url
    
    # Set ClickHouse table prefix for test isolation
    os.environ["TEST_CLICKHOUSE_TABLES_PREFIX"] = "test_"
    
    # Configure separate LLM API keys for testing if available
    for provider in ["ANTHROPIC", "GOOGLE", "OPENAI"]:
        test_key = os.getenv(f"TEST_{provider}_API_KEY")
        if test_key:
            os.environ[f"{provider}_API_KEY"] = test_key
    
    # Set test environment flag
    os.environ["TEST_ENVIRONMENT"] = "test_dedicated"
    os.environ["USE_TEST_ISOLATION"] = "true"

def configure_gcp_staging_environment():
    """Configure environment for GCP staging tests."""
    # Set staging environment
    os.environ["ENVIRONMENT"] = "staging"
    
    # GCP configuration
    project_id = os.getenv("GCP_PROJECT_ID", "netra-ai-staging")
    os.environ["GCP_PROJECT_ID"] = project_id
    os.environ["GCP_REGION"] = os.getenv("GCP_REGION", "us-central1")
    
    # Enable Secret Manager
    os.environ["USE_SECRET_MANAGER"] = "true"
    
    # Cloud SQL configuration
    os.environ["CLOUD_SQL_CONNECTION_NAME"] = f"{project_id}:us-central1:postgres-staging"
    
    # Redis configuration for staging
    os.environ["REDIS_HOST"] = "redis-staging"
    
    # Actual Staging URLs
    os.environ["STAGING_URL"] = os.getenv("STAGING_URL", "https://app.staging.netrasystems.ai")
    os.environ["STAGING_API_URL"] = os.getenv("STAGING_API_URL", "https://api.staging.netrasystems.ai")
    os.environ["STAGING_AUTH_URL"] = os.getenv("STAGING_AUTH_URL", "https://auth.staging.netrasystems.ai")
    os.environ["STAGING_FRONTEND_URL"] = os.getenv("STAGING_FRONTEND_URL", "https://app.staging.netrasystems.ai")
    
    # Set base URLs for tests
    os.environ["BASE_URL"] = os.environ["STAGING_URL"]
    os.environ["API_BASE_URL"] = os.environ["STAGING_API_URL"]
    os.environ["AUTH_BASE_URL"] = os.environ["STAGING_AUTH_URL"]
    os.environ["FRONTEND_URL"] = os.environ["STAGING_FRONTEND_URL"]
    
    # WebSocket URL
    os.environ["WS_BASE_URL"] = os.getenv("WS_BASE_URL", "wss://api.staging.netrasystems.ai/ws")
    
    # Enable observability
    os.environ["ENABLE_OBSERVABILITY"] = "true"
    
    # Check for GCP credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("[WARNING] GOOGLE_APPLICATION_CREDENTIALS not set - staging tests may fail")
    
    print(f"[INFO] Configured for GCP staging environment (project: {project_id})")
    print(f"[INFO] Staging URLs:")
    print(f"  - App: {os.environ['STAGING_URL']}")
    print(f"  - API: {os.environ['STAGING_API_URL']}")
    print(f"  - Auth: {os.environ['STAGING_AUTH_URL']}")
    print(f"  - Frontend: {os.environ['STAGING_FRONTEND_URL']}")