"""
Frontend Test Category to Test Level Mapping
Maps frontend test categories to unified test levels for consistent execution.
"""

# Mapping of frontend test categories to test levels
FRONTEND_TEST_MAPPING = {
    "smoke": {
        "categories": ["critical", "smoke"],
        "patterns": ["**/critical/**/*.test.*", "**/smoke/**/*.test.*"],
        "max_duration": 30,
        "description": "Quick validation tests"
    },
    
    "unit": {
        "categories": ["components", "hooks", "utils", "services", "store"],
        "patterns": [
            "**/components/**/*.test.*",
            "**/hooks/**/*.test.*", 
            "**/utils/**/*.test.*",
            "**/services/**/*.test.*",
            "**/store/**/*.test.*"
        ],
        "max_duration": 120,
        "description": "Isolated component and utility tests"
    },
    
    "critical": {
        "categories": ["critical", "auth", "chat/send-flow"],
        "patterns": [
            "**/critical/**/*.test.*",
            "**/auth/**/*.test.*",
            "**/chat/send-flow.test.*"
        ],
        "max_duration": 120,
        "description": "Business-critical functionality"
    },
    
    "integration": {
        "categories": ["integration", "chat", "unified_system"],
        "patterns": [
            "**/integration/**/*.test.*",
            "**/chat/**/*.test.*",
            "**/unified_system/**/*.test.*"
        ],
        "max_duration": 300,
        "description": "Feature integration tests"
    },
    
    "performance": {
        "categories": ["performance", "load"],
        "patterns": [
            "**/performance/**/*.test.*",
            "**/load/**/*.test.*",
            "**/*.performance.test.*"
        ],
        "max_duration": 300,
        "description": "Performance and load tests"
    },
    
    "a11y": {
        "categories": ["a11y", "accessibility"],
        "patterns": [
            "**/a11y/**/*.test.*",
            "**/accessibility/**/*.test.*",
            "**/*.a11y.test.*"
        ],
        "max_duration": 180,
        "description": "Accessibility compliance tests"
    },
    
    "e2e": {
        "categories": ["e2e", "integration/comprehensive"],
        "patterns": [
            "**/e2e/**/*.test.*",
            "**/integration/comprehensive/**/*.test.*"
        ],
        "max_duration": 600,
        "description": "End-to-end user flows"
    },
    
    "comprehensive": {
        "categories": ["*"],  # All categories
        "patterns": ["**/*.test.*"],
        "max_duration": 1800,
        "description": "All frontend tests"
    }
}

# Category priority for conflict resolution
# Higher priority categories override lower ones
CATEGORY_PRIORITY = {
    "critical": 100,
    "smoke": 90,
    "auth": 80,
    "chat": 70,
    "integration": 60,
    "components": 50,
    "store": 40,
    "hooks": 30,
    "utils": 20,
    "services": 10,
    "a11y": 5,
    "performance": 5,
    "e2e": 1
}

def get_test_categories_for_level(level: str) -> list:
    """Get frontend test categories for a given test level."""
    if level not in FRONTEND_TEST_MAPPING:
        return []
    return FRONTEND_TEST_MAPPING[level]["categories"]

def get_test_patterns_for_level(level: str) -> list:
    """Get Jest test patterns for a given test level."""
    if level not in FRONTEND_TEST_MAPPING:
        return ["**/*.test.*"]  # Default to all tests
    return FRONTEND_TEST_MAPPING[level]["patterns"]

def get_jest_command_for_level(level: str) -> str:
    """Build Jest command for a specific test level."""
    patterns = get_test_patterns_for_level(level)
    
    if level == "smoke":
        return "npm test -- --bail --maxWorkers=2"
    elif level == "unit":
        return f"npm test -- --testPathPattern='({'|'.join(patterns)})'"
    elif level == "critical":
        return f"npm test -- --testPathPattern='({'|'.join(patterns)})' --bail"
    elif level == "integration":
        return f"npm test -- --testPathPattern='({'|'.join(patterns)})'"
    elif level == "performance":
        return f"npm test -- --testPathPattern='({'|'.join(patterns)})' --runInBand"
    elif level == "comprehensive":
        return "npm test -- --coverage"
    else:
        return "npm test"

def categorize_test_file(file_path: str) -> str:
    """Determine the category of a test file based on its path."""
    path_lower = file_path.lower()
    
    # Check for specific patterns
    if "critical" in path_lower:
        return "critical"
    elif "smoke" in path_lower:
        return "smoke"
    elif "integration/comprehensive" in path_lower:
        return "e2e"
    elif "integration/critical" in path_lower:
        return "critical"
    elif "integration" in path_lower:
        return "integration"
    elif "components" in path_lower:
        return "components"
    elif "store" in path_lower:
        return "store"
    elif "hooks" in path_lower:
        return "hooks"
    elif "utils" in path_lower:
        return "utils"
    elif "services" in path_lower:
        return "services"
    elif "chat" in path_lower:
        return "chat"
    elif "auth" in path_lower:
        return "auth"
    elif "a11y" in path_lower or "accessibility" in path_lower:
        return "a11y"
    elif "performance" in path_lower or "load" in path_lower:
        return "performance"
    elif "e2e" in path_lower:
        return "e2e"
    elif "unified_system" in path_lower:
        return "integration"
    else:
        return "other"

def should_run_test_for_level(test_file: str, level: str) -> bool:
    """Determine if a test file should run for a given test level."""
    if level == "comprehensive":
        return True  # Run all tests
    
    category = categorize_test_file(test_file)
    allowed_categories = get_test_categories_for_level(level)
    
    # Check if category matches or if wildcard is present
    if "*" in allowed_categories:
        return True
    
    return category in allowed_categories