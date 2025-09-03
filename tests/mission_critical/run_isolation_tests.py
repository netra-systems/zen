#!/usr/bin/env python3
"""
Mission Critical Data Layer Isolation Test Runner

This script runs the comprehensive data layer isolation security tests
that are designed to expose critical vulnerabilities in the current system.

IMPORTANT: These tests are EXPECTED TO FAIL initially, proving that
security vulnerabilities exist in the current implementation.

Usage:
    python tests/mission_critical/run_isolation_tests.py
    python tests/mission_critical/run_isolation_tests.py --real-services
    python tests/mission_critical/run_isolation_tests.py --concurrent-load 20
"""

import sys
import os
import asyncio
import argparse
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unified_test_runner import UnifiedTestRunner


class IsolationSecurityTestRunner:
    """Specialized test runner for data layer isolation security tests."""
    
    def __init__(self, args):
        self.args = args
        self.test_file = Path(__file__).parent / "test_data_layer_isolation.py"
        
    def run_tests(self):
        """Run the isolation security tests with appropriate configuration."""
        
        print("=" * 80)
        print("🔒 MISSION CRITICAL: Data Layer Isolation Security Tests")
        print("=" * 80)
        print()
        print("⚠️  WARNING: These tests are EXPECTED TO FAIL initially!")
        print("   They are designed to expose critical security vulnerabilities:")
        print("   1. ClickHouse cache contamination between users")
        print("   2. Redis key collision between users")
        print("   3. Missing user context propagation")
        print("   4. Session isolation failures")
        print("   5. Cross-tenant data leakage")
        print()
        print("🎯 Goal: Prove vulnerabilities exist before implementing fixes")
        print("=" * 80)
        print()
        
        # Build pytest command
        pytest_args = [
            str(self.test_file),
            "-v",
            "--tb=short",
            "-x",  # Stop on first failure
            "--no-cov",  # Don't measure coverage for security tests
            "-m", "mission_critical",
        ]
        
        # Add real services if requested
        if self.args.real_services:
            pytest_args.extend([
                "--real-services",
            ])
            print("🔧 Running with REAL SERVICES (Redis, ClickHouse, etc.)")
            print()
        
        # Add concurrent load parameter
        if self.args.concurrent_load:
            pytest_args.extend([
                "--concurrent-users", str(self.args.concurrent_load)
            ])
            print(f"⚡ Testing with {self.args.concurrent_load} concurrent users")
            print()
        
        # Add specific test filter if provided
        if self.args.test_filter:
            pytest_args.extend(["-k", self.args.test_filter])
            print(f"🔍 Running tests matching: {self.args.test_filter}")
            print()
        
        print("Running command:", " ".join(pytest_args))
        print("=" * 80)
        print()
        
        # Run the tests
        exit_code = pytest.main(pytest_args)
        
        print()
        print("=" * 80)
        
        if exit_code == 0:
            print("❌ UNEXPECTED: All tests passed!")
            print("   This suggests vulnerabilities may have been fixed already,")
            print("   or tests need to be made more comprehensive.")
            print("   Review test implementation for completeness.")
        else:
            print("✅ EXPECTED: Tests failed as designed!")
            print("   This confirms that security vulnerabilities exist.")
            print("   Next steps:")
            print("   1. Implement proper user context isolation")
            print("   2. Add user-scoped cache keys")
            print("   3. Implement session isolation")
            print("   4. Add cross-tenant data protection")
            print("   5. Re-run tests until they pass")
        
        print("=" * 80)
        
        return exit_code


def main():
    """Main entry point for isolation security test runner."""
    
    parser = argparse.ArgumentParser(
        description="Run mission critical data layer isolation security tests"
    )
    
    parser.add_argument(
        "--real-services",
        action="store_true",
        help="Run tests against real Redis, ClickHouse, PostgreSQL services"
    )
    
    parser.add_argument(
        "--concurrent-load",
        type=int,
        default=10,
        help="Number of concurrent users to simulate for load testing (default: 10)"
    )
    
    parser.add_argument(
        "--test-filter",
        type=str,
        help="Filter tests by name pattern (pytest -k option)"
    )
    
    parser.add_argument(
        "--show-vulnerabilities",
        action="store_true",
        help="Show detailed vulnerability information before running tests"
    )
    
    args = parser.parse_args()
    
    if args.show_vulnerabilities:
        show_vulnerability_details()
        return 0
    
    runner = IsolationSecurityTestRunner(args)
    return runner.run_tests()


def show_vulnerability_details():
    """Show detailed information about the vulnerabilities being tested."""
    
    print("=" * 80)
    print("🔒 DATA LAYER ISOLATION SECURITY VULNERABILITIES")
    print("=" * 80)
    print()
    
    vulnerabilities = [
        {
            "name": "ClickHouse Cache Contamination",
            "severity": "CRITICAL",
            "description": "Users can access cached query results from other users",
            "impact": "Data breach, unauthorized access to confidential information",
            "test": "test_clickhouse_cache_contamination_vulnerability"
        },
        {
            "name": "Redis Key Collision", 
            "severity": "CRITICAL",
            "description": "Session and cache keys collide between users",
            "impact": "Session hijacking, data leakage, privilege escalation",
            "test": "test_redis_key_collision_vulnerability"
        },
        {
            "name": "User Context Propagation Failure",
            "severity": "HIGH",
            "description": "User context is lost between system layers",
            "impact": "Unauthorized data access, audit trail corruption",
            "test": "test_user_context_propagation_failure"
        },
        {
            "name": "Session Isolation Failure",
            "severity": "HIGH", 
            "description": "User sessions bleed into each other",
            "impact": "Chat context contamination, private conversation exposure",
            "test": "test_session_isolation_vulnerability"
        },
        {
            "name": "Cache Key Predictability",
            "severity": "MEDIUM",
            "description": "Cache keys are predictable and don't include user context",
            "impact": "Enumeration attacks, unauthorized data access",
            "test": "test_cache_key_predictability_vulnerability"
        },
        {
            "name": "High Concurrency Race Conditions",
            "severity": "HIGH",
            "description": "Race conditions under concurrent load expose isolation failures",
            "impact": "Data contamination, unpredictable security failures",
            "test": "test_high_concurrency_isolation_failure"
        },
        {
            "name": "Cross-Tenant Data Leakage",
            "severity": "CRITICAL",
            "description": "Multi-tenant data bleeds between tenant boundaries",
            "impact": "Enterprise data breach, compliance violations",
            "test": "test_cross_tenant_data_leakage_vulnerability"
        }
    ]
    
    for vuln in vulnerabilities:
        print(f"🚨 {vuln['name']} [{vuln['severity']}]")
        print(f"   Description: {vuln['description']}")
        print(f"   Impact: {vuln['impact']}")
        print(f"   Test: {vuln['test']}")
        print()
    
    print("=" * 80)
    print("💡 These vulnerabilities exist because:")
    print("   - Shared global state between users")
    print("   - Cache keys without user context")
    print("   - Missing user isolation in data layer")
    print("   - Race conditions in concurrent execution")
    print("   - Inadequate session management")
    print("=" * 80)


if __name__ == "__main__":
    sys.exit(main())