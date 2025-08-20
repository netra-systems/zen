"""Test configuration and level definitions."""

import multiprocessing
import os
from typing import Dict, Any

# Determine optimal parallelization
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)  # Leave one CPU free

# Define test levels with clear purposes
TEST_LEVELS: Dict[str, Dict[str, Any]] = {
    "smoke": {
        "description": "Quick smoke tests for basic functionality (< 30 seconds)",
        "purpose": "Pre-commit validation, basic health checks",
        "backend_args": ["--category", "smoke", "--fail-fast", "--coverage", "--markers", "not real_services"],
        "frontend_args": [],
        "timeout": 30,
        "run_coverage": True,
        "run_both": False  # Only run backend smoke tests for now
    },
    "unit": {
        "description": "Unit tests for isolated components (1-2 minutes)",
        "purpose": "Development validation, component testing",
        "backend_args": ["--category", "unit", "-v", "--coverage", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--markers", "not real_services"],
        "frontend_args": ["--category", "unit"],
        "timeout": 120,
        "run_coverage": True,
        "run_both": True
    },
    "agents": {
        "description": "Agent-specific unit tests (2-3 minutes)",
        "purpose": "Quick validation of agent functionality during development",
        "backend_args": [
            "--category", "agent", 
            "-v", "--coverage", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}",
            "--markers", "not real_services"
        ],
        "frontend_args": [],
        "timeout": 180,
        "run_coverage": True,
        "run_both": False
    },
    "agent-startup": {
        "description": "Agent startup E2E tests with real services (2-3 minutes)",
        "purpose": "Comprehensive agent initialization and startup validation",
        "backend_args": [
            "tests/unified/test_agent_cold_start.py",
            "tests/unified/test_concurrent_agents.py",
            "-v", "--fail-fast", f"--parallel={min(2, OPTIMAL_WORKERS)}",
            "--markers", "real_services"
        ],
        "frontend_args": [],
        "timeout": 300,
        "run_coverage": True,
        "run_both": False,
        "supports_real_llm": True,
        "business_critical": True,
        "highlight": True
    },
    "integration": {
        "description": "Integration tests for component interaction (3-5 minutes)",
        "purpose": "Feature validation, API testing",
        "backend_args": ["--category", "integration", "-v", "--coverage", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--markers", "not real_services"],
        "frontend_args": ["--category", "integration"],
        "timeout": 300,
        "run_coverage": True,
        "run_both": True
    },
    "comprehensive": {
        "description": "Full test suite with coverage (30-45 minutes)",
        "purpose": "Pre-release validation, full system testing",
        "backend_args": ["app/tests", "tests", "integration_tests", "--coverage", f"--parallel={min(6, OPTIMAL_WORKERS)}", "--html-output", "--fail-fast"],
        "frontend_args": ["--coverage"],
        "timeout": 2700,  # 45 minutes to handle real LLM tests
        "run_coverage": True,
        "run_both": True
    },
    "comprehensive-backend": {
        "description": "Comprehensive backend tests only (15-20 minutes)",
        "purpose": "Full backend validation without frontend",
        "backend_args": ["app/tests", "tests", "integration_tests", "--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--html-output", "--fail-fast", "--markers", "not frontend"],
        "frontend_args": [],
        "timeout": 1200,  # 20 minutes
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-frontend": {
        "description": "Comprehensive frontend tests only (10-15 minutes)",
        "purpose": "Full frontend validation without backend",
        "backend_args": [],
        "frontend_args": ["--coverage", "--e2e", "--fail-fast"],
        "timeout": 900,  # 15 minutes
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-core": {
        "description": "Core functionality comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of core components only",
        "backend_args": ["app/core", "app/config", "app/dependencies", "app/tests/unit/test_*core*", "app/tests/*core*", "tests/*core*", "tests/unified/test_*core*", "--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,  # 15 minutes
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-agents": {
        "description": "Agent system comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of multi-agent system",
        "backend_args": ["app/agents", "app/services/agent*", "app/tests/*agent*", "app/tests/**/*agent*", "tests/*agent*", "tests/**/*agent*", "tests/unified/test_*agent*", "tests/agents", "--coverage", f"--parallel={min(3, OPTIMAL_WORKERS)}", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,  # 15 minutes
        "run_coverage": True,
        "run_both": False,
        "supports_real_llm": True,
        "business_critical": True
    },
    "comprehensive-websocket": {
        "description": "WebSocket comprehensive tests (5-10 minutes)",
        "purpose": "Deep validation of WebSocket functionality",
        "backend_args": ["app/websocket", "app/routes/websocket_secure.py", "app/tests/*websocket*", "app/tests/**/*websocket*", "tests/*websocket*", "tests/**/*websocket*", "integration_tests/test_websocket*", "--coverage", f"--parallel={min(3, OPTIMAL_WORKERS)}", "--fail-fast"],
        "frontend_args": [],
        "timeout": 600,  # 10 minutes
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-database": {
        "description": "Database comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of all database operations",
        "backend_args": ["app/db", "app/repositories", "app/tests/*database*", "app/tests/*db*", "app/tests/**/*database*", "tests/*database*", "tests/*db*", "tests/**/*database*", "tests/unified/test_*database*", "--coverage", f"--parallel={min(3, OPTIMAL_WORKERS)}", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,  # 15 minutes
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-api": {
        "description": "API comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of all API endpoints",
        "backend_args": ["app/routes", "app/handlers", "app/tests/*api*", "app/tests/*auth*", "app/tests/**/*api*", "tests/*api*", "tests/*auth*", "tests/**/*api*", "tests/unified/test_*api*", "integration_tests/test_*api*", "--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,  # 15 minutes
        "run_coverage": True,
        "run_both": False
    },
    "critical": {
        "description": "Critical path tests only (1-2 minutes)",
        "purpose": "Essential functionality verification",
        "backend_args": ["--category", "critical", "--fail-fast", "--coverage"],
        "frontend_args": ["--category", "smoke"],
        "timeout": 120,
        "run_coverage": True,
        "run_both": False  # Backend only for critical paths
    },
    "all": {
        "description": "All tests including backend, frontend, e2e, integration (45-60 minutes)",
        "purpose": "Complete system validation including all test types",
        "backend_args": ["--coverage", f"--parallel={OPTIMAL_WORKERS}", "--html-output", "--fail-fast"],
        "frontend_args": ["--coverage", "--e2e"],
        "timeout": 3600,  # 60 minutes for complete test suite
        "run_coverage": True,
        "run_both": True,
        "run_e2e": True
    },
    "real_e2e": {
        "description": "Full end-to-end tests with real LLM and services (20-30 minutes)",
        "purpose": "Complete user journey validation with actual services",
        "backend_args": ["-m", "real_e2e", "-v", "--fail-fast", f"--parallel={min(2, OPTIMAL_WORKERS)}"],
        "frontend_args": [],
        "timeout": 1800,  # 30 minutes for E2E tests
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENABLE_REAL_LLM_TESTING=true"],
        "supports_real_llm": True,
        "default_llm_timeout": 90,  # Higher timeout for E2E scenarios
        "max_parallel_llm_calls": 2,  # Limit parallelism for stability
        "business_critical": True
    },
    "real_services": {
        "description": "Tests requiring real external services (LLM, DB, Redis, ClickHouse)",
        "purpose": "Validation with actual service dependencies",
        "backend_args": ["-m", "real_services", "-v", "--fail-fast", f"--parallel={min(2, OPTIMAL_WORKERS)}"],
        "frontend_args": [],
        "timeout": 2400,  # 40 minutes for real service tests with LLM retries
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENABLE_REAL_LLM_TESTING=true"],
        "supports_real_llm": True,
        "default_llm_timeout": 60,  # Higher default timeout for real services
        "max_parallel_llm_calls": 2  # Limit parallel LLM calls to avoid rate limits
    },
    "performance": {
        "description": "Performance validation suite for SLA compliance (3-5 minutes)",
        "purpose": "Validate response times meet business SLA requirements",
        "backend_args": ["-m", "performance", "tests/test_unified_performance.py", "-v", "--fail-fast"],
        "frontend_args": [],
        "timeout": 300,
        "run_coverage": False,
        "run_both": False,
        "highlight": True,
        "business_critical": True
    },
    "staging": {
        "description": "Staging environment configuration integration tests (10-15 minutes)",
        "purpose": "Validate staging deployment configuration and GCP resource integration",
        "backend_args": ["app/tests/integration/staging_config", "-v", "--fail-fast", f"--parallel={min(2, OPTIMAL_WORKERS)}"],
        "frontend_args": [],
        "timeout": 900,
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENVIRONMENT=staging", "GOOGLE_APPLICATION_CREDENTIALS"],
        "supports_real_services": True,
        "business_critical": True,
        "highlight": True
    },
    "staging-quick": {
        "description": "Quick staging validation tests (2-3 minutes)",
        "purpose": "Fast staging health check for deployment verification",
        "backend_args": [
            "app/tests/integration/staging_config/test_secret_manager_integration.py",
            "app/tests/integration/staging_config/test_health_checks.py",
            "-v", "--fail-fast"
        ],
        "frontend_args": [],
        "timeout": 180,
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENVIRONMENT=staging"],
        "highlight": True
    }
}

# Test runner configurations - DEPRECATED (kept for backward compatibility)
# Use test_runner.py as the single entry point
RUNNERS = {
    "backend": "scripts/test_backend.py", 
    "frontend": "scripts/test_frontend.py"
}

# Component mappings for focused testing
COMPONENT_MAPPINGS = {
    "core": ["app/core", "app/config", "app/dependencies"],
    "agents": ["app/agents", "app/services/agent"],
    "websocket": ["app/ws_manager", "app/services/websocket", "test_websocket"],
    "database": ["app/db", "app/services/database", "test_database"],
    "api": ["app/routes", "test_api", "test_auth"],
    "frontend": ["frontend"]
}

# Shard mappings for CI/CD parallel execution (numeric sharding)
SHARD_MAPPINGS = {
    "1/4": ["app/core", "app/config", "app/dependencies"],
    "2/4": ["app/agents", "app/services/agent"],
    "3/4": ["app/ws_manager", "app/services/websocket", "app/db", "app/services/database"],
    "4/4": ["app/routes", "test_api", "test_auth", "frontend"]
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

def configure_real_llm(model: str, timeout: int, parallel: str, test_level: str = None, use_dedicated_env: bool = True):
    """Configure environment for real LLM testing with smart defaults and dedicated test environment."""
    # Get level-specific defaults if available
    level_config = TEST_LEVELS.get(test_level, {}) if test_level else {}
    
    # Use level-specific timeout if not overridden
    if timeout == 30 and level_config.get("default_llm_timeout"):
        timeout = level_config["default_llm_timeout"]
    
    # Handle special parallel values
    if parallel == "max":
        parallel_value = str(OPTIMAL_WORKERS)
    elif parallel == "auto":
        # For real LLM tests, limit parallelism to avoid rate limits
        max_llm_parallel = level_config.get("max_parallel_llm_calls", 3)
        parallel_value = str(min(max_llm_parallel, OPTIMAL_WORKERS))
    else:
        parallel_value = str(parallel)
    
    config = {
        "model": model,
        "timeout": timeout,
        "parallel": parallel_value,
        "rate_limit_delay": 1 if int(parallel_value) > 2 else 0,  # Add delay for high parallelism
        "dedicated_environment": use_dedicated_env
    }
    
    # Set basic LLM environment variables
    os.environ["TEST_USE_REAL_LLM"] = "true"
    os.environ["ENABLE_REAL_LLM_TESTING"] = "true"
    os.environ["TEST_LLM_TIMEOUT"] = str(timeout)
    os.environ["TEST_LLM_MODEL"] = model
    
    if parallel_value != "auto":
        os.environ["TEST_PARALLEL"] = parallel_value
    
    # Add rate limit delay if needed
    if config["rate_limit_delay"] > 0:
        os.environ["TEST_LLM_RATE_LIMIT_DELAY"] = str(config["rate_limit_delay"])
    
    # Configure dedicated test environment if requested
    if use_dedicated_env:
        configure_dedicated_test_environment()
    
    return config


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
    
    # Staging URLs
    os.environ["STAGING_URL"] = os.getenv("STAGING_URL", "https://staging.netra.ai")
    
    # Enable observability
    os.environ["ENABLE_OBSERVABILITY"] = "true"
    
    # Check for GCP credentials
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("[WARNING] GOOGLE_APPLICATION_CREDENTIALS not set - staging tests may fail")
    
    print(f"[INFO] Configured for GCP staging environment (project: {project_id})")