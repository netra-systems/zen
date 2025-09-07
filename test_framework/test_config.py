"""Test configuration for modern category-based testing."""

import multiprocessing
import os
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

# Import environment management
from shared.isolated_environment import get_env

# Determine optimal parallelization
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)  # Leave one CPU free

# Test service ports configuration
TEST_PORTS = {
    "postgresql": 5434,    # Test PostgreSQL
    "redis": 6381,         # Test Redis  
    "backend": 8000,       # Backend service
    "auth": 8081,          # Auth service
    "frontend": 3000,      # Frontend
    "clickhouse": 8123,    # ClickHouse
    "analytics": 8002,     # Analytics service
}

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
    env = get_env()
    env.set("STAGING_MODE", "true", source="staging_test_config")
    env.set("STAGING_URL", staging_url, source="staging_test_config")
    env.set("STAGING_API_URL", staging_api_url, source="staging_test_config")
    env.set("BASE_URL", staging_url, source="staging_test_config")
    env.set("API_BASE_URL", staging_api_url, source="staging_test_config")
    env.set("CYPRESS_BASE_URL", staging_url, source="staging_test_config")
    env.set("CYPRESS_API_URL", staging_api_url, source="staging_test_config")

def configure_dev_environment():
    """Configure environment variables for dev mode testing."""
    env = get_env()
    # Set environment to development
    env.set("ENVIRONMENT", "development", source="dev_test_config")
    
    # Remove TESTING environment variable if present to allow dev mode detection
    env.delete("TESTING", source="dev_test_config")
    
    # Configure dev service URLs
    env.set("DEV_MODE", "true", source="dev_test_config")
    env.set("BASE_URL", "http://localhost:8001", source="dev_test_config")
    env.set("API_BASE_URL", "http://localhost:8001", source="dev_test_config")
    env.set("BACKEND_URL", "http://localhost:8001", source="dev_test_config")
    
    # Frontend URLs (if needed)
    env.set("FRONTEND_URL", "http://localhost:3000", source="dev_test_config")
    
    # Database and service URLs for dev environment
    env.set("DATABASE_URL", "postgresql://netra:netra123@localhost:5433/netra_dev", source="dev_test_config")
    env.set("REDIS_URL", "redis://localhost:6380", source="dev_test_config")
    env.set("CLICKHOUSE_URL", "http://localhost:8124", source="dev_test_config")

def configure_mock_environment():
    """Configure environment variables for mock/test services mode.
    
    This function configures mock/test services and sets TESTING=true.
    Use this when you want to use mock services instead of real ones.
    """
    env = get_env()
    # Set environment to testing  
    env.set("ENVIRONMENT", "testing", source="mock_test_config")
    env.set("TESTING", "true", source="mock_test_config")
    
    # Skip heavy startup checks during testing
    env.set("SKIP_STARTUP_CHECKS", "true", source="mock_test_config")
    env.set("TEST_COLLECTION_MODE", "false", source="mock_test_config")
    
    # Configure test service URLs
    env.set("BASE_URL", "http://localhost:8001", source="mock_test_config")
    env.set("API_BASE_URL", "http://localhost:8001", source="mock_test_config")
    env.set("BACKEND_URL", "http://localhost:8001", source="mock_test_config")
    
    # Frontend URLs (if needed)
    env.set("FRONTEND_URL", "http://localhost:3000", source="mock_test_config")
    
    # Database and service URLs for test environment
    # Use test-specific database to avoid conflicts with dev data
    # Updated to use correct credentials from docker-compose.test.yml
    env.set("DATABASE_URL", "postgresql://test_user:test_pass@localhost:5433/netra_test", source="mock_test_config")
    env.set("REDIS_URL", "redis://localhost:6381/1", source="mock_test_config")  # Use DB 1 for tests
    env.set("CLICKHOUSE_URL", "http://localhost:8125", source="mock_test_config")  # Use correct test port

def configure_test_environment():
    """DEPRECATED: Use configure_mock_environment() instead.
    
    This function is maintained for backward compatibility only.
    """
    import warnings
    warnings.warn(
        "configure_test_environment() is deprecated. Use configure_mock_environment() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return configure_mock_environment()

# Helper function for checking real LLM usage with backward compatibility
def should_use_real_llm() -> bool:
    """Check if real LLM should be used, supporting both new and legacy variable names.
    
    CRITICAL: Real LLM testing is the DEFAULT for Netra Apex (per CLAUDE.md).
    Returns:
        bool: True if real LLM should be used, False otherwise
    """
    env = get_env()
    # Check primary control variable first (default to true)
    primary = env.get("NETRA_REAL_LLM_ENABLED", "true").lower() == "true"
    if primary:
        return True
    
    # Check legacy variables for backward compatibility
    return (env.get("USE_REAL_LLM", "true").lower() == "true" or
            env.get("TEST_USE_REAL_LLM", "true").lower() == "true" or
            env.get("ENABLE_REAL_LLM_TESTING", "true").lower() == "true")

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
    env = get_env()
    # Database configuration for test_dedicated environment
    test_db_url = env.get("TEST_DATABASE_URL")
    if not test_db_url:
        # Fallback to main database with test schema
        main_db_url = env.get("DATABASE_URL", "postgresql://localhost/netra_main")
        test_db_url = main_db_url.replace("/netra_main", "/netra_test")
        env.set("TEST_DATABASE_URL", test_db_url, source="dedicated_test_config")
    
    # Redis configuration with test namespace
    test_redis_url = env.get("TEST_REDIS_URL")
    if not test_redis_url:
        main_redis_url = env.get("REDIS_URL", "redis://localhost:6379/0")
        # Use database index 1 for tests
        test_redis_url = main_redis_url.replace("/0", "/1")
        env.set("TEST_REDIS_URL", test_redis_url, source="dedicated_test_config")
    
    # Set Redis namespace prefix for test isolation
    env.set("TEST_REDIS_NAMESPACE", "test:", source="dedicated_test_config")
    
    # ClickHouse configuration with test database
    test_clickhouse_url = env.get("TEST_CLICKHOUSE_URL")
    if not test_clickhouse_url:
        main_clickhouse_url = env.get("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_main")
        test_clickhouse_url = main_clickhouse_url.replace("/netra_main", "/netra_test")
        env.set("TEST_CLICKHOUSE_URL", test_clickhouse_url, source="dedicated_test_config")
    
    # Set ClickHouse table prefix for test isolation
    env.set("TEST_CLICKHOUSE_TABLES_PREFIX", "test_", source="dedicated_test_config")
    
    # Configure separate LLM API keys for testing if available
    for provider in ["ANTHROPIC", "GOOGLE", "OPENAI"]:
        test_key = env.get(f"TEST_{provider}_API_KEY")
        if test_key:
            env.set(f"{provider}_API_KEY", test_key, source="dedicated_test_config")
    
    # Set test environment flag
    env.set("TEST_ENVIRONMENT", "test_dedicated", source="dedicated_test_config")
    env.set("USE_TEST_ISOLATION", "true", source="dedicated_test_config")

def configure_gcp_staging_environment():
    """Configure environment for GCP staging tests."""
    env = get_env()
    # Set staging environment
    env.set("ENVIRONMENT", "staging", source="gcp_staging_config")
    
    # GCP configuration
    project_id = env.get("GCP_PROJECT_ID", "netra-ai-staging")
    env.set("GCP_PROJECT_ID", project_id, source="gcp_staging_config")
    env.set("GCP_REGION", env.get("GCP_REGION", "us-central1"), source="gcp_staging_config")
    
    # Enable Secret Manager
    env.set("USE_SECRET_MANAGER", "true", source="gcp_staging_config")
    
    # Cloud SQL configuration
    env.set("CLOUD_SQL_CONNECTION_NAME", f"{project_id}:us-central1:postgres-staging", source="gcp_staging_config")
    
    # Redis configuration for staging
    env.set("REDIS_HOST", "redis-staging", source="gcp_staging_config")
    
    # Actual Staging URLs
    staging_url = env.get("STAGING_URL", "https://app.staging.netrasystems.ai")
    staging_api_url = env.get("STAGING_API_URL", "https://api.staging.netrasystems.ai")
    staging_auth_url = env.get("STAGING_AUTH_URL", "https://auth.staging.netrasystems.ai")
    staging_frontend_url = env.get("STAGING_FRONTEND_URL", "https://app.staging.netrasystems.ai")
    
    env.set("STAGING_URL", staging_url, source="gcp_staging_config")
    env.set("STAGING_API_URL", staging_api_url, source="gcp_staging_config")
    env.set("STAGING_AUTH_URL", staging_auth_url, source="gcp_staging_config")
    env.set("STAGING_FRONTEND_URL", staging_frontend_url, source="gcp_staging_config")
    
    # Set base URLs for tests
    env.set("BASE_URL", staging_url, source="gcp_staging_config")
    env.set("API_BASE_URL", staging_api_url, source="gcp_staging_config")
    env.set("AUTH_BASE_URL", staging_auth_url, source="gcp_staging_config")
    env.set("FRONTEND_URL", staging_frontend_url, source="gcp_staging_config")
    
    # WebSocket URL
    env.set("WS_BASE_URL", env.get("WS_BASE_URL", "wss://api.staging.netrasystems.ai/ws"), source="gcp_staging_config")
    
    # Enable observability
    env.set("ENABLE_OBSERVABILITY", "true", source="gcp_staging_config")
    
    # Check for GCP credentials
    if not env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("[WARNING] GOOGLE_APPLICATION_CREDENTIALS not set - staging tests may fail")
    
    print(f"[INFO] Configured for GCP staging environment (project: {project_id})")
    print(f"[INFO] Staging URLs:")
    print(f"  - App: {staging_url}")
    print(f"  - API: {staging_api_url}")
    print(f"  - Auth: {staging_auth_url}")
    print(f"  - Frontend: {staging_frontend_url}")