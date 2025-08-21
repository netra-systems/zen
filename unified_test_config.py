"""
UNIFIED TEST CONFIGURATION
==========================
Central configuration for all testing operations across Netra platform.
This module defines test levels, markers, environments, and execution strategies.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

# Project paths
PROJECT_ROOT = Path(__file__).parent
TEST_FRAMEWORK_DIR = PROJECT_ROOT / "test_framework"
BACKEND_DIR = PROJECT_ROOT / "netra_backend"
AUTH_DIR = PROJECT_ROOT / "auth_service"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TEST_REPORTS_DIR = PROJECT_ROOT / "test_reports"

# Test level definitions
TEST_LEVELS = {
    "smoke": {
        "description": "Quick validation tests (<30s)",
        "markers": ["smoke"],
        "timeout": 30,
        "parallel": True,
        "coverage_target": 0,  # No coverage for smoke tests
        "categories": ["unit", "api"]
    },
    "unit": {
        "description": "Component isolation tests (1-2min)",
        "markers": ["unit", "not integration", "not e2e"],
        "timeout": 120,
        "parallel": True,
        "coverage_target": 80,
        "categories": ["unit"]
    },
    "integration": {
        "description": "Feature integration tests (3-5min)",
        "markers": ["integration", "not e2e", "not slow"],
        "timeout": 300,
        "parallel": True,
        "coverage_target": 70,
        "categories": ["integration", "api", "database"]
    },
    "comprehensive": {
        "description": "Full test suite (30-45min)",
        "markers": [],  # Run all tests
        "timeout": 2700,
        "parallel": True,
        "coverage_target": 85,
        "categories": ["unit", "integration", "e2e", "performance"]
    },
    "critical": {
        "description": "Revenue-critical path tests (1-2min)",
        "markers": ["critical"],
        "timeout": 120,
        "parallel": False,  # Run sequentially for stability
        "coverage_target": 0,
        "categories": ["critical", "api"]
    },
    "agents": {
        "description": "Agent-specific tests with real LLMs",
        "markers": ["agents", "real_llm"],
        "timeout": 600,
        "parallel": False,
        "coverage_target": 60,
        "categories": ["agents"]
    }
}

# Test markers with descriptions
TEST_MARKERS = {
    # Test levels
    "unit": "Unit tests for isolated components",
    "integration": "Integration tests for component interaction",
    "e2e": "End-to-end tests",
    "smoke": "Quick smoke tests for basic functionality",
    "critical": "Critical path tests that protect revenue",
    
    # Service categories
    "backend": "Backend service tests",
    "auth": "Authentication service tests",
    "frontend": "Frontend application tests",
    "api": "API endpoint tests",
    "websocket": "WebSocket-related tests",
    "database": "Database-related tests",
    
    # Environment-specific
    "real_services": "Tests requiring real external services",
    "real_llm": "Tests that use real LLM services",
    "real_database": "Tests requiring real database connections",
    "mock_only": "Tests using only mocks",
    "staging": "Staging environment specific tests",
    "dev": "Development environment specific tests",
    
    # Performance categories
    "performance": "Performance and SLA validation tests",
    "slow": "Slow tests that may take longer to complete",
    "stress": "Stress tests with high load or concurrency",
    "soak": "Long-duration soak testing",
    "benchmark": "Performance benchmark tests",
    
    # Security and isolation
    "security": "Security validation tests",
    "oauth": "OAuth flow tests",
    "isolation": "Isolation and multi-tenancy tests",
    "rate_limiting": "Rate limiting and DDoS protection tests",
    
    # Quality categories
    "flaky": "Tests that may fail intermittently",
    "bad_test": "Tests marked as consistently failing",
    
    # Agent-specific
    "agents": "Agent-specific tests",
    
    # Specialized
    "redis": "Redis-dependent tests",
    "resilience": "Resilience and recovery validation tests",
    "comprehensive": "Comprehensive system-wide tests"
}

# Environment configurations
ENVIRONMENTS = {
    "local": {
        "name": "Local Development",
        "database_url": "postgresql://test:test@localhost:5432/netra_test",
        "redis_url": "redis://localhost:6379/0",
        "use_mocks": True,
        "real_llm": False,
        "api_base": "http://localhost:8000"
    },
    "dev": {
        "name": "Development Environment",
        "database_url": os.getenv("DEV_DATABASE_URL"),
        "redis_url": os.getenv("DEV_REDIS_URL"),
        "use_mocks": False,
        "real_llm": False,
        "api_base": "https://dev.netra.systems"
    },
    "staging": {
        "name": "Staging Environment",
        "database_url": os.getenv("STAGING_DATABASE_URL"),
        "redis_url": os.getenv("STAGING_REDIS_URL"),
        "use_mocks": False,
        "real_llm": True,
        "api_base": "https://staging.netra.systems"
    },
    "prod": {
        "name": "Production Environment",
        "database_url": None,  # Never run tests in prod
        "redis_url": None,
        "use_mocks": True,
        "real_llm": False,
        "api_base": "https://api.netra.systems"
    }
}

# Service-specific configurations
SERVICE_CONFIGS = {
    "backend": {
        "root": BACKEND_DIR,
        "test_dir": BACKEND_DIR / "tests",
        "config_file": "pytest.ini",
        "runner": "pytest",
        "env_file": ".env.test",
        "coverage_source": "netra_backend/app",
        "required_services": ["postgres", "redis", "clickhouse"]
    },
    "auth": {
        "root": AUTH_DIR,
        "test_dir": AUTH_DIR / "tests",
        "config_file": "pytest.ini",
        "runner": "pytest",
        "env_file": ".env.test",
        "coverage_source": "auth_service/app",
        "required_services": ["postgres", "redis"]
    },
    "frontend": {
        "root": FRONTEND_DIR,
        "test_dir": FRONTEND_DIR / "__tests__",
        "config_file": "jest.config.cjs",
        "runner": "jest",
        "env_file": ".env.test",
        "coverage_source": "src",
        "required_services": []
    }
}

# Test execution strategies
EXECUTION_STRATEGIES = {
    "fast": {
        "parallel": True,
        "workers": "auto",
        "fail_fast": True,
        "coverage": False,
        "verbose": False
    },
    "thorough": {
        "parallel": True,
        "workers": 4,
        "fail_fast": False,
        "coverage": True,
        "verbose": True
    },
    "debug": {
        "parallel": False,
        "workers": 1,
        "fail_fast": True,
        "coverage": False,
        "verbose": True
    },
    "ci": {
        "parallel": True,
        "workers": 2,
        "fail_fast": False,
        "coverage": True,
        "verbose": False
    }
}

# Coverage requirements by service
COVERAGE_REQUIREMENTS = {
    "backend": {
        "unit": 80,
        "integration": 70,
        "comprehensive": 85
    },
    "auth": {
        "unit": 85,
        "integration": 75,
        "comprehensive": 90
    },
    "frontend": {
        "unit": 75,
        "integration": 65,
        "comprehensive": 80
    }
}

# Test categories for organization
TEST_CATEGORIES = {
    "unit": {
        "path_pattern": "**/unit/**",
        "file_pattern": "test_*.py",
        "timeout": 10
    },
    "integration": {
        "path_pattern": "**/integration/**",
        "file_pattern": "test_*.py",
        "timeout": 30
    },
    "e2e": {
        "path_pattern": "**/e2e/**",
        "file_pattern": "test_*.py",
        "timeout": 60
    },
    "performance": {
        "path_pattern": "**/performance/**",
        "file_pattern": "test_*.py",
        "timeout": 120
    },
    "security": {
        "path_pattern": "**/security/**",
        "file_pattern": "test_*.py",
        "timeout": 30
    }
}


def get_test_level_config(level: str) -> Dict:
    """Get configuration for a specific test level."""
    return TEST_LEVELS.get(level, TEST_LEVELS["integration"])


def get_environment_config(env: str) -> Dict:
    """Get configuration for a specific environment."""
    return ENVIRONMENTS.get(env, ENVIRONMENTS["local"])


def get_service_config(service: str) -> Dict:
    """Get configuration for a specific service."""
    return SERVICE_CONFIGS.get(service)


def get_execution_strategy(strategy: str) -> Dict:
    """Get execution strategy configuration."""
    return EXECUTION_STRATEGIES.get(strategy, EXECUTION_STRATEGIES["thorough"])


def get_coverage_requirement(service: str, level: str) -> int:
    """Get coverage requirement for service and test level."""
    service_reqs = COVERAGE_REQUIREMENTS.get(service, {})
    return service_reqs.get(level, 0)


def configure_test_environment(env: str, service: Optional[str] = None):
    """Configure environment variables for testing."""
    env_config = get_environment_config(env)
    
    # Set common environment variables
    os.environ["TEST_ENV"] = env
    os.environ["USE_MOCKS"] = str(env_config["use_mocks"])
    os.environ["REAL_LLM"] = str(env_config["real_llm"])
    
    if env_config["database_url"]:
        os.environ["DATABASE_URL"] = env_config["database_url"]
    
    if env_config["redis_url"]:
        os.environ["REDIS_URL"] = env_config["redis_url"]
    
    if env_config["api_base"]:
        os.environ["API_BASE_URL"] = env_config["api_base"]
    
    # Set service-specific variables
    if service:
        service_config = get_service_config(service)
        if service_config and service_config["env_file"]:
            env_file = service_config["root"] / service_config["env_file"]
            if env_file.exists():
                from dotenv import load_dotenv
                load_dotenv(env_file)


def get_pytest_args(
    level: str,
    service: str,
    strategy: str = "thorough",
    additional_args: Optional[List[str]] = None
) -> List[str]:
    """Build pytest command arguments."""
    args = []
    
    # Get configurations
    level_config = get_test_level_config(level)
    service_config = get_service_config(service)
    strategy_config = get_execution_strategy(strategy)
    
    # Add test directory
    if service_config:
        args.append(str(service_config["test_dir"]))
    
    # Add markers
    if level_config.get("markers"):
        marker_expr = " and ".join(level_config["markers"])
        args.extend(["-m", marker_expr])
    
    # Add parallelization
    if strategy_config["parallel"]:
        workers = strategy_config["workers"]
        if workers == "auto":
            import multiprocessing
            workers = multiprocessing.cpu_count()
        args.extend(["-n", str(workers)])
    
    # Add coverage
    if strategy_config["coverage"] and service_config:
        args.extend([
            f"--cov={service_config['coverage_source']}",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
        
        # Add coverage requirement
        coverage_req = get_coverage_requirement(service, level)
        if coverage_req > 0:
            args.append(f"--cov-fail-under={coverage_req}")
    
    # Add verbosity
    if strategy_config["verbose"]:
        args.append("-vv")
    else:
        args.append("-q")
    
    # Add fail fast
    if strategy_config["fail_fast"]:
        args.append("-x")
    
    # Add timeout
    if level_config.get("timeout"):
        args.append(f"--timeout={level_config['timeout']}")
    
    # Add additional arguments
    if additional_args:
        args.extend(additional_args)
    
    return args


def validate_test_structure() -> List[str]:
    """Validate the test structure and return any issues."""
    issues = []
    
    # Check for test directories
    for service, config in SERVICE_CONFIGS.items():
        test_dir = config["test_dir"]
        if not test_dir.exists():
            issues.append(f"Missing test directory: {test_dir}")
        
        config_file = config["root"] / config["config_file"]
        if not config_file.exists():
            issues.append(f"Missing config file: {config_file}")
    
    # Check for duplicate test files
    test_files = set()
    for service_config in SERVICE_CONFIGS.values():
        if service_config["test_dir"].exists():
            for test_file in service_config["test_dir"].rglob("test_*.py"):
                if test_file.name in test_files:
                    issues.append(f"Duplicate test file: {test_file.name}")
                test_files.add(test_file.name)
    
    return issues