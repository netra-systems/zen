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
        "backend_args": ["--category", "smoke", "--fail-fast", "--markers", "not real_services"],
        "frontend_args": [],
        "timeout": 30,
        "run_coverage": False,
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

def configure_real_llm(model: str, timeout: int, parallel: str, test_level: str = None):
    """Configure environment for real LLM testing with smart defaults."""
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
        "rate_limit_delay": 1 if int(parallel_value) > 2 else 0  # Add delay for high parallelism
    }
    
    # Set environment variables
    os.environ["TEST_USE_REAL_LLM"] = "true"
    os.environ["ENABLE_REAL_LLM_TESTING"] = "true"
    os.environ["TEST_LLM_TIMEOUT"] = str(timeout)
    os.environ["TEST_LLM_MODEL"] = model
    
    if parallel_value != "auto":
        os.environ["TEST_PARALLEL"] = parallel_value
    
    # Add rate limit delay if needed
    if config["rate_limit_delay"] > 0:
        os.environ["TEST_LLM_RATE_LIMIT_DELAY"] = str(config["rate_limit_delay"])
    
    return config