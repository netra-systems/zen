#!/usr/bin/env python3
"""
Test Discovery Script for Netra Apex
Discovers and lists available tests without running them
"""

import sys
import os
from pathlib import Path
import glob

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def discover_agent_tests():
    """Discover agent-related test files."""
    print("🔍 Discovering Agent-Related Tests")
    print("=" * 50)
    
    # Unit agent tests
    unit_agent_tests = list(Path("tests/unit").glob("*agent*.py"))
    print(f"\n📁 Unit Agent Tests ({len(unit_agent_tests)} files):")
    for test in sorted(unit_agent_tests):
        print(f"  • {test.name}")
    
    # Mission critical agent tests  
    mission_critical_agent_tests = list(Path("tests/mission_critical").glob("*agent*.py"))
    print(f"\n🎯 Mission Critical Agent Tests ({len(mission_critical_agent_tests)} files):")
    for test in sorted(mission_critical_agent_tests):
        print(f"  • {test.name}")
    
    # Staging agent tests
    staging_agent_tests = list(Path("tests/staging").glob("*agent*.py"))
    print(f"\n🏗️  Staging Agent Tests ({len(staging_agent_tests)} files):")
    for test in sorted(staging_agent_tests):
        print(f"  • {test.name}")
    
    return len(unit_agent_tests) + len(mission_critical_agent_tests) + len(staging_agent_tests)

def discover_e2e_staging_tests():
    """Discover E2E staging tests."""
    print("\n\n🌐 Discovering E2E Staging Tests")
    print("=" * 50)
    
    # E2E staging tests
    staging_e2e_tests = list(Path("tests/e2e/staging").glob("test_*.py"))
    print(f"\n📁 E2E Staging Tests ({len(staging_e2e_tests)} files):")
    
    # Group by priority if available
    priority_tests = {}
    other_tests = []
    
    for test in sorted(staging_e2e_tests):
        if "priority" in test.name:
            priority = "unknown"
            for p in ["priority1", "priority2", "priority3", "priority4", "priority5", "priority6"]:
                if p in test.name:
                    priority = p
                    break
            if priority not in priority_tests:
                priority_tests[priority] = []
            priority_tests[priority].append(test)
        else:
            other_tests.append(test)
    
    # Print priority tests first
    for priority in sorted(priority_tests.keys()):
        print(f"\n  🎯 {priority.upper()} Tests:")
        for test in sorted(priority_tests[priority]):
            print(f"    • {test.name}")
    
    # Print other tests
    if other_tests:
        print(f"\n  📋 Other E2E Staging Tests:")
        for test in sorted(other_tests):
            print(f"    • {test.name}")
    
    return len(staging_e2e_tests)

def show_test_runner_options():
    """Show unified test runner options."""
    print("\n\n⚙️  Unified Test Runner Options")
    print("=" * 50)
    
    example_commands = [
        "# Agent-related unit tests (fast-fail, no Docker)",
        "python tests/unified_test_runner.py --category unit --pattern agent --fast-fail --no-docker",
        "",
        "# E2E staging tests (fast-fail, no Docker)", 
        "python tests/unified_test_runner.py --category e2e --env staging --fast-fail --no-docker",
        "",
        "# Mission critical agent tests",
        "python tests/unified_test_runner.py --category mission_critical --pattern agent --fast-fail --no-docker",
        "",
        "# Specific test categories",
        "python tests/unified_test_runner.py --categories unit integration --fast-fail --no-docker",
        "",
        "# With keyword filtering",
        "python tests/unified_test_runner.py --category e2e --keyword agent --env staging --no-docker"
    ]
    
    for cmd in example_commands:
        print(cmd)

def check_environment():
    """Check if test environment is set up."""
    print("\n\n🔧 Environment Check")
    print("=" * 50)
    
    # Check for key files
    key_files = [
        "tests/unified_test_runner.py",
        "tests/staging/staging_config.py", 
        "test_framework/ssot/base_test_case.py",
        ".env.staging.tests"
    ]
    
    for file_path in key_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
    
    # Check for environment variables
    env_vars = [
        "NETRA_BACKEND_URL",
        "AUTH_SERVICE_URL", 
        "GCP_PROJECT_ID"
    ]
    
    print(f"\n📋 Environment Variables:")
    for var in env_vars:
        if var in os.environ:
            print(f"✅ {var} = {os.environ[var]}")
        else:
            print(f"❌ {var} (not set)")

def main():
    print("🔍 NETRA APEX TEST DISCOVERY")
    print("Identifying available agent and E2E tests for GCP staging")
    print("=" * 70)
    
    # Discover tests
    agent_test_count = discover_agent_tests()
    e2e_test_count = discover_e2e_staging_tests()
    
    # Show runner options
    show_test_runner_options()
    
    # Check environment
    check_environment()
    
    # Summary
    print(f"\n\n📊 DISCOVERY SUMMARY")
    print("=" * 50)
    print(f"🧪 Total Agent Tests: {agent_test_count}")
    print(f"🌐 Total E2E Staging Tests: {e2e_test_count}")
    print(f"📋 Total Tests Discovered: {agent_test_count + e2e_test_count}")
    
    print(f"\n✅ Ready to run tests with unified test runner")
    print(f"🎯 Focus: Agent functionality + GCP staging E2E validation")
    print(f"🚫 No Docker required for recommended commands")

if __name__ == "__main__":
    main()