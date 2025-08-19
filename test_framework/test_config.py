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
            "-v", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}",
            "--markers", "not real_services"
        ],
        "frontend_args": [],
        "timeout": 180,
        "run_coverage": False,
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
        "backend_args": ["app/tests", "tests", "integration_tests", "--coverage", f"--parallel={min(6, OPTIMAL_WORKERS)}", "--html-output", "--fail-fast"],
        "frontend_args": [],
        "timeout": 1200,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-frontend": {
        "description": "Comprehensive frontend tests only (10-15 minutes)",
        "purpose": "Full frontend validation without backend",
        "backend_args": [],
        "frontend_args": ["--coverage"],
        "timeout": 900,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-core": {
        "description": "Core functionality comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of core components only",
        "backend_args": ["--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "-k", "core or config or dependencies", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-agents": {
        "description": "Agent system comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of multi-agent system",
        "backend_args": [
            "app/tests/agents", "tests/test_actions_sub_agent.py",
            "--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "--fail-fast",
            "--markers", "not real_services"
        ],
        "frontend_args": [],
        "timeout": 900,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-websocket": {
        "description": "WebSocket comprehensive tests (5-10 minutes)",
        "purpose": "Deep validation of WebSocket functionality",
        "backend_args": ["--coverage", f"--parallel={min(2, OPTIMAL_WORKERS)}", "-k", "websocket or ws_manager", "--fail-fast"],
        "frontend_args": [],
        "timeout": 600,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-database": {
        "description": "Database comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of all database operations",
        "backend_args": ["--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "-k", "database or repository or clickhouse or postgres", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,
        "run_coverage": True,
        "run_both": False
    },
    "comprehensive-api": {
        "description": "API comprehensive tests (10-15 minutes)",
        "purpose": "Deep validation of all API endpoints",
        "backend_args": ["--coverage", f"--parallel={min(4, OPTIMAL_WORKERS)}", "-k", "routes or api", "--fail-fast"],
        "frontend_args": [],
        "timeout": 900,
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
        "description": "[REAL E2E] Tests with actual LLM calls and services (15-20 minutes)",
        "purpose": "End-to-end validation with real LLM and service integrations",
        "backend_args": ["-k", "real_ or _real", "-v", "--fail-fast"],
        "frontend_args": [],
        "timeout": 1200,  # 20 minutes for real e2e tests
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENABLE_REAL_LLM_TESTING=true"],
        "highlight": True  # Flag to highlight in output
    },
    "real_services": {
        "description": "Tests requiring real external services (LLM, DB, Redis, ClickHouse)",
        "purpose": "Validation with actual service dependencies",
        "backend_args": ["-m", "real_services", "-v", "--fail-fast"],
        "frontend_args": [],
        "timeout": 1800,  # 30 minutes for real service tests
        "run_coverage": False,
        "run_both": False,
        "requires_env": ["ENABLE_REAL_LLM_TESTING=true"]
    },
    "mock_only": {
        "description": "Tests using only mocks, no external dependencies",
        "purpose": "Fast CI/CD validation without external dependencies",
        "backend_args": ["-m", "mock_only", "-v", "--coverage", f"--parallel={OPTIMAL_WORKERS}"],
        "frontend_args": [],
        "timeout": 300,
        "run_coverage": True,
        "run_both": False
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

# Test runner configurations
RUNNERS = {
    "simple": "test_scripts/simple_test_runner.py",
    "backend": "scripts/test_backend.py", 
    "frontend": "scripts/test_frontend.py"
}

# Shard mappings for parallel execution in CI/CD
SHARD_MAPPINGS = {
    "core": ["app/core", "app/config", "app/dependencies"],
    "agents": ["app/agents", "app/services/agent"],
    "websocket": ["app/ws_manager", "app/services/websocket", "test_websocket"],
    "database": ["app/db", "app/services/database", "test_database"],
    "api": ["app/routes", "test_api", "test_auth"],
    "frontend": ["frontend"]
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

def configure_real_llm(model: str, timeout: int, parallel: str):
    """Configure environment for real LLM testing."""
    config = {
        "model": model,
        "timeout": timeout,
        "parallel": parallel
    }
    
    # Set environment variables
    os.environ["TEST_USE_REAL_LLM"] = "true"
    os.environ["ENABLE_REAL_LLM_TESTING"] = "true"
    os.environ["TEST_LLM_TIMEOUT"] = str(timeout)
    
    if parallel != "auto":
        os.environ["TEST_PARALLEL"] = str(parallel)
    
    return config