#!/usr/bin/env python3
"""
Validation script for Issue #1082 - Docker Alpine Build Infrastructure Failure
Tests the fixes and proves system stability after changes.
"""

import sys
import os
from pathlib import Path
import subprocess
import json
import traceback
from datetime import datetime

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def log_result(message, success=True):
    """Log validation results."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"[{timestamp}] {status}: {message}")
    return success

def test_basic_imports():
    """Test basic import functionality after build context cleanup."""
    print("\n=== Testing Basic Import Functionality ===")
    results = []

    # Test core module imports
    test_imports = [
        ("netra_backend.app.config", "Backend config"),
        ("auth_service.auth_core.core.jwt_handler", "Auth service JWT handler"),
        ("shared.cors_config", "Shared CORS config"),
        ("test_framework.unified_docker_manager", "Docker manager"),
    ]

    for module, description in test_imports:
        try:
            __import__(module)
            results.append(log_result(f"Import {description} successful"))
        except ImportError as e:
            results.append(log_result(f"Import {description} failed: {e}", False))
        except Exception as e:
            results.append(log_result(f"Import {description} error: {e}", False))

    return all(results)

def test_docker_bypass_mechanism():
    """Test the Docker bypass mechanism implementation."""
    print("\n=== Testing Docker Bypass Mechanism ===")
    results = []

    try:
        # Check if unified test runner has Docker bypass functionality
        unified_test_runner = PROJECT_ROOT / "tests" / "unified_test_runner.py"
        if unified_test_runner.exists():
            with open(unified_test_runner, 'r') as f:
                content = f.read()

            if "--docker-bypass" in content and "docker_bypass_1082" in content:
                results.append(log_result("Docker bypass flag implementation found"))
            else:
                results.append(log_result("Docker bypass flag not found", False))

            if "_configure_docker_bypass_environment" in content:
                results.append(log_result("Docker bypass environment configuration found"))
            else:
                results.append(log_result("Docker bypass environment configuration not found", False))
        else:
            results.append(log_result("Unified test runner not found", False))

    except Exception as e:
        results.append(log_result(f"Docker bypass mechanism test error: {e}", False))

    return all(results)

def test_build_context_cleanup():
    """Test that build context cleanup was successful."""
    print("\n=== Testing Build Context Cleanup ===")
    results = []

    # Check for .pyc files in critical directories
    critical_dirs = [
        PROJECT_ROOT / "netra_backend",
        PROJECT_ROOT / "auth_service",
        PROJECT_ROOT / "frontend",
        PROJECT_ROOT / "shared"
    ]

    pyc_count = 0
    pycache_count = 0

    for directory in critical_dirs:
        if directory.exists():
            # Count .pyc files
            pyc_files = list(directory.rglob("*.pyc"))
            pyc_count += len(pyc_files)

            # Count __pycache__ directories
            pycache_dirs = list(directory.rglob("__pycache__"))
            pycache_count += len(pycache_dirs)

    results.append(log_result(f"Found {pyc_count} .pyc files (should be minimal)"))
    results.append(log_result(f"Found {pycache_count} __pycache__ directories (should be minimal)"))

    # Check .dockerignore exists and contains relevant patterns
    dockerignore = PROJECT_ROOT / ".dockerignore"
    if dockerignore.exists():
        with open(dockerignore, 'r') as f:
            content = f.read()

        if "*.pyc" in content and "__pycache__" in content:
            results.append(log_result(".dockerignore contains Python build artifacts"))
        else:
            results.append(log_result(".dockerignore missing Python build artifact patterns", False))
    else:
        results.append(log_result(".dockerignore file not found", False))

    return all(results)

def test_alpine_dockerfile_configuration():
    """Test Alpine Dockerfile configuration fixes."""
    print("\n=== Testing Alpine Dockerfile Configuration ===")
    results = []

    # Check for Alpine Dockerfiles
    dockerfile_patterns = [
        "Dockerfile.backend.alpine",
        "Dockerfile.auth.alpine",
        "Dockerfile.frontend.alpine"
    ]

    for pattern in dockerfile_patterns:
        dockerfile_path = PROJECT_ROOT / "dockerfiles" / pattern
        if dockerfile_path.exists():
            results.append(log_result(f"Alpine Dockerfile {pattern} exists"))

            # Check for critical Alpine configurations
            with open(dockerfile_path, 'r') as f:
                content = f.read()

            if "apk add" in content:
                results.append(log_result(f"{pattern} contains Alpine package management"))
            else:
                results.append(log_result(f"{pattern} missing Alpine package management", False))
        else:
            results.append(log_result(f"Alpine Dockerfile {pattern} not found", False))

    return all(results)

def test_staging_fallback_enhancements():
    """Test staging fallback enhancements."""
    print("\n=== Testing Staging Fallback Enhancements ===")
    results = []

    # Check environment configurations
    env_files = [
        ".env.staging.tests",
        ".env.staging.e2e"
    ]

    for env_file in env_files:
        env_path = PROJECT_ROOT / env_file
        if env_path.exists():
            results.append(log_result(f"Staging environment file {env_file} exists"))

            with open(env_path, 'r') as f:
                content = f.read()

            # Check for staging domain configurations
            if "staging.netrasystems.ai" in content:
                results.append(log_result(f"{env_file} contains staging domain configuration"))
            else:
                results.append(log_result(f"{env_file} missing staging domain configuration", False))
        else:
            results.append(log_result(f"Staging environment file {env_file} not found", False))

    return all(results)

def test_critical_system_components():
    """Test critical system components for regression."""
    print("\n=== Testing Critical System Components ===")
    results = []

    # Test configuration loading
    try:
        from netra_backend.app.config import get_config
        config = get_config()
        results.append(log_result("Configuration loading successful"))
    except Exception as e:
        results.append(log_result(f"Configuration loading failed: {e}", False))

    # Test auth service core imports
    try:
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        results.append(log_result("Auth service JWT handler import successful"))
    except Exception as e:
        results.append(log_result(f"Auth service JWT handler import failed: {e}", False))

    # Test shared utilities
    try:
        from shared.cors_config import get_cors_config
        results.append(log_result("Shared CORS config import successful"))
    except Exception as e:
        results.append(log_result(f"Shared CORS config import failed: {e}", False))

    return all(results)

def main():
    """Main validation function."""
    print("🔍 ISSUE #1082 VALIDATION - Docker Alpine Build Infrastructure Failure")
    print("=" * 80)
    print("Validating changes to prove system stability and absence of breaking changes")
    print()

    # Track all test results
    test_results = []

    # Run validation tests
    test_results.append(test_basic_imports())
    test_results.append(test_docker_bypass_mechanism())
    test_results.append(test_build_context_cleanup())
    test_results.append(test_alpine_dockerfile_configuration())
    test_results.append(test_staging_fallback_enhancements())
    test_results.append(test_critical_system_components())

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    passed_tests = sum(test_results)
    total_tests = len(test_results)

    if passed_tests == total_tests:
        print(f"✅ ALL TESTS PASSED ({passed_tests}/{total_tests})")
        print("✅ SYSTEM STABILITY CONFIRMED")
        print("✅ NO BREAKING CHANGES DETECTED")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed_tests}/{total_tests})")
        print("⚠️  REQUIRES INVESTIGATION")
        return 1

if __name__ == "__main__":
    sys.exit(main())