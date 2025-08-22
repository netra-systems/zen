"""Test configuration and level definitions."""

import multiprocessing
import os
from typing import Any, Dict

# Determine optimal parallelization
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)  # Leave one CPU free

# Define simplified 5-level test system with clear boundaries
TEST_LEVELS: Dict[str, Dict[str, Any]] = {
    "unit": {
        "description": "Fast isolated component tests for rapid development feedback (1-3 minutes)",
        "purpose": "Daily development, pre-commit validation, isolated component testing",
        "backend_args": [
            "--category", "unit,smoke,critical,agent", 
            "-v", "--coverage", "--fail-fast", 
            f"--parallel={min(4, OPTIMAL_WORKERS)}", 
            "--markers", "not real_services and not real_llm"
        ],
        "frontend_args": ["--category", "unit,smoke"],
        "timeout": 180,  # 3 minutes max
        "run_coverage": True,
        "run_both": True,
        "includes_legacy": ["smoke", "unit", "critical", "agents", "code-quality"],
        "default_for_development": True
    },
    "integration": {
        "description": "Service interaction and feature validation tests (3-8 minutes)",
        "purpose": "Feature validation, API testing, service interaction validation",
        "backend_args": [
            "--category", "integration", 
            "-v", "--coverage", "--fail-fast", 
            f"--parallel={min(4, OPTIMAL_WORKERS)}", 
            "--markers", "not real_llm"
        ],
        "frontend_args": ["--category", "integration"],
        "timeout": 480,  # 8 minutes max
        "run_coverage": True,
        "run_both": True,
        "includes_legacy": ["integration", "agent-startup"],
        "business_critical": True,
        "default_level": True  # This is the default level for CI/CD
    },
    "e2e": {
        "description": "End-to-end tests with real services and user journeys (10-30 minutes)",
        "purpose": "Real user scenario validation, pre-release testing with actual services",
        "backend_args": [
            "-m", "real_e2e or real_services or staging", 
            "-v", "--fail-fast", 
            f"--parallel={min(2, OPTIMAL_WORKERS)}",
            "--markers", "real_llm or real_services or staging"
        ],
        "frontend_args": ["--e2e"],
        "timeout": 1800,  # 30 minutes
        "run_coverage": False,  # Focus on functionality over coverage
        "run_both": True,
        "requires_env": ["ENABLE_REAL_LLM_TESTING=true"],
        "supports_real_llm": True,
        "supports_real_services": True,
        "includes_staging": True,
        "includes_legacy": ["real_e2e", "real_services", "staging", "staging-real", "staging-quick"],
        "business_critical": True,
        "highlight": True,
        "default_llm_timeout": 90,
        "max_parallel_llm_calls": 2
    },
    "performance": {
        "description": "Performance validation and load testing for SLA compliance (3-10 minutes)",
        "purpose": "Response time validation, load testing, performance regression detection",
        "backend_args": [
            "-m", "performance", 
            "tests/test_unified_performance.py",
            "-v", "--fail-fast"
        ],
        "frontend_args": ["--performance"],
        "timeout": 600,  # 10 minutes
        "run_coverage": False,
        "run_both": True,
        "includes_legacy": ["performance"],
        "business_critical": True,
        "highlight": True
    },
    "comprehensive": {
        "description": "Complete system validation for releases (30-60 minutes)",
        "purpose": "Full release validation, complete regression testing, all environments",
        "backend_args": [
            "netra_backend/tests", "tests", "integration_tests", 
            "--coverage", f"--parallel={min(6, OPTIMAL_WORKERS)}", 
            "--html-output", "--fail-fast"
        ],
        "frontend_args": ["--coverage", "--e2e"],
        "timeout": 3600,  # 60 minutes
        "run_coverage": True,
        "run_both": True,
        "run_e2e": True,
        "includes_staging": True,
        "includes_legacy": ["comprehensive", "comprehensive-backend", "comprehensive-frontend", "comprehensive-core", "comprehensive-agents", "comprehensive-websocket", "comprehensive-database", "comprehensive-api", "all"],
        "supports_real_llm": True,
        "supports_real_services": True,
        "business_critical": True,
        "release_validation": True
    },
    
    # Backward compatibility aliases - maps old level names to new levels
    # These are deprecated and will be removed in future versions
    "smoke": {"alias_for": "unit", "deprecated": True},
    "critical": {"alias_for": "unit", "deprecated": True},
    "agents": {"alias_for": "unit", "deprecated": True},
    "code-quality": {"alias_for": "unit", "deprecated": True},
    "agent-startup": {"alias_for": "integration", "deprecated": True},
    "real_e2e": {"alias_for": "e2e", "deprecated": True},
    "real_services": {"alias_for": "e2e", "deprecated": True},
    "staging": {"alias_for": "e2e", "deprecated": True},
    "staging-real": {"alias_for": "e2e", "deprecated": True},
    "staging-quick": {"alias_for": "e2e", "deprecated": True},
    "comprehensive-backend": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-frontend": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-core": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-agents": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-websocket": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-database": {"alias_for": "comprehensive", "deprecated": True},
    "comprehensive-api": {"alias_for": "comprehensive", "deprecated": True},
    "all": {"alias_for": "comprehensive", "deprecated": True}
}

# Default test level for CI/CD and development
DEFAULT_TEST_LEVEL = "integration"

# Test level documentation and usage guidelines
TEST_LEVEL_USAGE = {
    "unit": {
        "when_to_use": ["Daily development", "Pre-commit hooks", "Quick feedback", "Component isolation testing"],
        "what_it_includes": ["Unit tests", "Smoke tests", "Critical path tests", "Agent unit tests", "Code quality checks"],
        "typical_runtime": "1-3 minutes",
        "coverage_focus": "Component isolation"
    },
    "integration": {
        "when_to_use": ["Feature development", "CI/CD pipelines", "API validation", "Service interaction testing"],
        "what_it_includes": ["Integration tests", "Service interaction tests", "Agent startup tests"],
        "typical_runtime": "3-8 minutes", 
        "coverage_focus": "Service interactions",
        "default": True
    },
    "e2e": {
        "when_to_use": ["Pre-release validation", "Real service testing", "User journey validation", "Staging validation"],
        "what_it_includes": ["Real LLM tests", "Real service tests", "Staging tests", "Full user workflows"],
        "typical_runtime": "10-30 minutes",
        "coverage_focus": "Real user scenarios"
    },
    "performance": {
        "when_to_use": ["Performance regression detection", "SLA validation", "Load testing", "Response time validation"],
        "what_it_includes": ["Performance tests", "Load tests", "Response time validation"],
        "typical_runtime": "3-10 minutes",
        "coverage_focus": "Performance metrics"
    },
    "comprehensive": {
        "when_to_use": ["Release validation", "Full system testing", "Complete regression testing"],
        "what_it_includes": ["All test types", "All environments", "Full coverage", "Staging validation"],
        "typical_runtime": "30-60 minutes",
        "coverage_focus": "Complete system validation"
    }
}

# Resolve level aliases for backward compatibility
def resolve_test_level(level: str) -> str:
    """Resolve test level aliases to actual levels for backward compatibility."""
    if level in TEST_LEVELS:
        config = TEST_LEVELS[level]
        if config.get("alias_for"):
            if config.get("deprecated"):
                print(f"[WARNING] Test level '{level}' is deprecated. Use '{config['alias_for']}' instead.")
            return config["alias_for"]
    return level

# Test runner configurations - DEPRECATED (kept for backward compatibility)
# Use unified_test_runner.py as the single entry point
RUNNERS = {
    "backend": "unified_test_runner.py --service backend", 
    "frontend": "unified_test_runner.py --service frontend"
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
    },
    "dev_launcher": {
        "paths": [
            "tests/test_system_startup.py", 
            "tests/unified/test_dev_launcher_real_startup.py",
            "tests/e2e/integration/test_dev_launcher_startup_complete.py",
            "tests/integration/test_dev_launcher*"
        ],
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