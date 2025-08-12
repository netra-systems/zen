"""
Test Categories and Configuration for Netra Platform

This module defines clear separation between different test types:
- MOCK_TESTS: Fast, isolated tests using mocks (run always)
- REAL_SERVICE_TESTS: Tests requiring real external services (run conditionally)
- INTEGRATION_TESTS: Tests verifying component interactions
"""

import os
from pathlib import Path
from typing import List, Dict, Set

# Environment flags for controlling test execution
ENABLE_REAL_LLM_TESTS = os.environ.get("ENABLE_REAL_LLM_TESTING", "false").lower() == "true"
ENABLE_REAL_DB_TESTS = os.environ.get("ENABLE_REAL_DB_TESTING", "false").lower() == "true"
ENABLE_REAL_CLICKHOUSE_TESTS = os.environ.get("ENABLE_REAL_CLICKHOUSE_TESTING", "false").lower() == "true"
ENABLE_REAL_REDIS_TESTS = os.environ.get("ENABLE_REAL_REDIS_TESTING", "false").lower() == "true"

# Test categories with clear separation
TEST_CATEGORIES = {
    # Basic plumbing tests - always run, use mocks
    "plumbing": {
        "description": "Basic system functionality with mocked dependencies",
        "patterns": [
            "**/test_*_mock.py",
            "**/test_*_unit.py",
            "**/test_imports.py",
            "**/test_internal_imports.py",
            "**/test_external_imports.py",
            "**/test_schemas.py",
            "**/test_models.py",
            "**/test_utils.py",
            "**/test_config.py",
            "**/test_auth.py",
            "**/test_routes.py",  # API routes with mocked services
        ],
        "requires_services": False,
        "always_run": True
    },
    
    # Real LLM provider tests - require API keys
    "real_llm": {
        "description": "Tests using real LLM providers (OpenAI, Anthropic, Google)",
        "patterns": [
            "**/test_*_real_llm.py",
            "**/test_llm_providers.py",
            "**/test_structured_generation.py",  # Can run with real LLMs
            "**/test_example_prompts_e2e_real.py",
            "**/agents/test_*_agent.py",  # Agent tests that can use real LLMs
        ],
        "requires_services": True,
        "enabled": ENABLE_REAL_LLM_TESTS,
        "required_env_vars": [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY", 
            "GEMINI_API_KEY"
        ]
    },
    
    # Real database tests - require PostgreSQL
    "real_database": {
        "description": "Tests using real PostgreSQL database",
        "patterns": [
            "**/database/test_*_repository.py",
            "**/database/test_*_queries.py",
            "**/test_database_*.py",
            "**/test_*_persistence.py",
        ],
        "requires_services": True,
        "enabled": ENABLE_REAL_DB_TESTS,
        "required_env_vars": ["DATABASE_URL"]
    },
    
    # Real ClickHouse tests
    "real_clickhouse": {
        "description": "Tests using real ClickHouse database",
        "patterns": [
            "**/clickhouse/test_*.py",
            "**/test_clickhouse_*.py",
            "**/test_analytics_*.py",
            "**/test_metrics_*.py",
        ],
        "requires_services": True,
        "enabled": ENABLE_REAL_CLICKHOUSE_TESTS,
        "required_env_vars": ["CLICKHOUSE_URL"]
    },
    
    # Real Redis tests
    "real_redis": {
        "description": "Tests using real Redis instance",
        "patterns": [
            "**/test_redis_*.py",
            "**/test_cache_*.py",
            "**/test_session_*.py",
            "**/test_pubsub_*.py",
        ],
        "requires_services": True,
        "enabled": ENABLE_REAL_REDIS_TESTS,
        "required_env_vars": ["REDIS_URL"]
    },
    
    # WebSocket tests - can be mocked or real
    "websocket": {
        "description": "WebSocket communication tests",
        "patterns": [
            "**/test_websocket_*.py",
            "**/test_ws_*.py",
            "**/test_realtime_*.py",
        ],
        "requires_services": False,  # Can run with mocked WebSocket
        "always_run": True
    },
    
    # Integration tests - test component interactions
    "integration": {
        "description": "Tests verifying multiple components working together",
        "patterns": [
            "**/test_*_integration.py",
            "**/test_*_e2e.py",
            "**/test_*_workflow.py",
            "**/test_*_comprehensive.py",
        ],
        "requires_services": False,  # Can use mocks for integration
        "always_run": True
    },
    
    # Performance tests - optional, resource intensive
    "performance": {
        "description": "Performance and load tests",
        "patterns": [
            "**/test_*_performance.py",
            "**/test_*_load.py",
            "**/test_*_stress.py",
            "**/test_*_benchmark.py",
        ],
        "requires_services": False,
        "enabled": os.environ.get("RUN_PERFORMANCE_TESTS", "false").lower() == "true"
    }
}


def get_test_category(test_file: Path) -> str:
    """Determine which category a test file belongs to."""
    test_path = str(test_file)
    
    for category, config in TEST_CATEGORIES.items():
        for pattern in config["patterns"]:
            # Convert glob pattern to match test file
            if _matches_pattern(test_path, pattern):
                return category
    
    # Default to plumbing if no specific category matches
    return "plumbing"


def _matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if file path matches a glob pattern."""
    from fnmatch import fnmatch
    import os
    
    # Normalize paths for comparison
    file_path = os.path.normpath(file_path).replace("\\", "/")
    
    # Handle ** for recursive matching
    if "**" in pattern:
        pattern = pattern.replace("**/", "*/")
        # Check if any part of the path matches
        parts = file_path.split("/")
        for i in range(len(parts)):
            subpath = "/".join(parts[i:])
            if fnmatch(subpath, pattern.lstrip("*/")):
                return True
    else:
        # Simple pattern matching
        filename = os.path.basename(file_path)
        if fnmatch(filename, pattern):
            return True
    
    return False


def should_run_category(category: str) -> bool:
    """Determine if a test category should be run."""
    config = TEST_CATEGORIES.get(category, {})
    
    # Always run if marked as always_run
    if config.get("always_run", False):
        return True
    
    # Check if explicitly enabled
    if "enabled" in config:
        return config["enabled"]
    
    # Default to True for categories without explicit enable flag
    return True


def get_required_env_vars(category: str) -> List[str]:
    """Get required environment variables for a test category."""
    config = TEST_CATEGORIES.get(category, {})
    return config.get("required_env_vars", [])


def validate_environment_for_category(category: str) -> tuple[bool, List[str]]:
    """
    Validate if environment has required variables for a category.
    Returns (is_valid, missing_vars)
    """
    required_vars = get_required_env_vars(category)
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var, "")
        # Check if var exists and is not a test/mock value
        if not value or value.startswith("test-") or value == "mock":
            missing_vars.append(var)
    
    return len(missing_vars) == 0, missing_vars


def get_runnable_categories() -> Dict[str, bool]:
    """Get all categories and whether they can be run."""
    runnable = {}
    
    for category in TEST_CATEGORIES:
        if should_run_category(category):
            is_valid, missing = validate_environment_for_category(category)
            runnable[category] = is_valid
        else:
            runnable[category] = False
    
    return runnable


def categorize_test_files(test_dir: Path) -> Dict[str, List[Path]]:
    """Categorize all test files in a directory."""
    categorized = {category: [] for category in TEST_CATEGORIES}
    
    # Find all test files
    for test_file in test_dir.rglob("test_*.py"):
        if test_file.is_file():
            category = get_test_category(test_file)
            categorized[category].append(test_file)
    
    return categorized


def print_test_categories_report(test_dir: Path = None):
    """Print a report of test categories and their status."""
    if test_dir is None:
        test_dir = Path(__file__).parent
    
    print("\n" + "="*60)
    print("TEST CATEGORIES REPORT")
    print("="*60)
    
    categorized = categorize_test_files(test_dir)
    runnable = get_runnable_categories()
    
    for category, config in TEST_CATEGORIES.items():
        files = categorized.get(category, [])
        can_run = runnable.get(category, False)
        status = "ENABLED" if can_run else "DISABLED"
        
        print(f"\n{category.upper()} ({status})")
        print(f"  Description: {config['description']}")
        print(f"  Files: {len(files)} test files")
        print(f"  Requires Services: {config.get('requires_services', False)}")
        
        if not can_run and config.get("requires_services"):
            is_valid, missing = validate_environment_for_category(category)
            if missing:
                print(f"  Missing env vars: {', '.join(missing)}")
        
        if files and len(files) <= 5:
            print("  Test files:")
            for f in files[:5]:
                print(f"    - {f.name}")


if __name__ == "__main__":
    # When run directly, print the categories report
    print_test_categories_report()