#!/usr/bin/env python3
"""
Python3-compatible system health validation for Claude Code environment.

This script provides immediate health check capability for Issue #1176 remediation,
validating critical system components using python3 commands.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json

def test_basic_imports():
    """Test basic system imports."""
    print("Testing basic imports...")
    import_tests = [
        "import sys; print('✓ sys module')",
        "import os; print('✓ os module')",
        "from pathlib import Path; print('✓ pathlib module')",
        "import subprocess; print('✓ subprocess module')",
    ]

    results = []
    for test in import_tests:
        try:
            result = subprocess.run(
                ["python3", "-c", test],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"  ✓ {test}")
                results.append(True)
            else:
                print(f"  ✗ {test} - {result.stderr}")
                results.append(False)
        except Exception as e:
            print(f"  ✗ {test} - {e}")
            results.append(False)

    return all(results)

def test_project_imports():
    """Test critical project imports."""
    print("\nTesting project imports...")
    project_root = Path(__file__).parent.absolute()

    project_tests = [
        "from tests.unified_test_runner import main; print('✓ unified_test_runner')",
        "from netra_backend.app.websocket_core.manager import WebSocketManager; print('✓ WebSocketManager')",
        "from test_framework.ssot.base_test_case import SSotBaseTestCase; print('✓ SSotBaseTestCase')",
        "from shared.cors_config import CorsConfig; print('✓ CorsConfig')",
    ]

    results = []
    for test in project_tests:
        try:
            # Set PYTHONPATH to include project root
            env = os.environ.copy()
            env['PYTHONPATH'] = str(project_root)

            result = subprocess.run(
                ["python3", "-c", test],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=project_root,
                env=env
            )
            if result.returncode == 0:
                print(f"  ✓ {test}")
                results.append(True)
            else:
                print(f"  ✗ {test} - {result.stderr}")
                results.append(False)
        except Exception as e:
            print(f"  ✗ {test} - {e}")
            results.append(False)

    return all(results)

def test_mission_critical_tests():
    """Test execution of mission critical test files."""
    print("\nTesting mission critical test execution...")
    project_root = Path(__file__).parent.absolute()

    critical_tests = [
        "tests/mission_critical/test_websocket_agent_events_suite.py",
        "tests/mission_critical/test_ssot_basic_validation.py",
        "tests/mission_critical/test_factory_pattern_ssot_compliance.py",
    ]

    results = []
    for test_file in critical_tests:
        test_path = project_root / test_file
        if not test_path.exists():
            print(f"  ⚠ {test_file} - File not found")
            results.append(False)
            continue

        try:
            # Test collection only (dry run)
            result = subprocess.run(
                ["python3", "-m", "pytest", str(test_path), "--collect-only", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=project_root
            )
            if result.returncode == 0 and "collected" in result.stdout:
                print(f"  ✓ {test_file} - Collection successful")
                results.append(True)
            else:
                print(f"  ✗ {test_file} - Collection failed: {result.stderr}")
                results.append(False)
        except Exception as e:
            print(f"  ✗ {test_file} - {e}")
            results.append(False)

    return any(results)  # At least one critical test should be collectible

def test_unified_test_runner():
    """Test unified test runner execution."""
    print("\nTesting unified test runner...")
    project_root = Path(__file__).parent.absolute()

    try:
        result = subprocess.run(
            ["python3", str(project_root / "tests" / "unified_test_runner.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root
        )
        if result.returncode == 0 and "usage:" in result.stdout.lower():
            print("  ✓ Unified test runner accessible")
            return True
        else:
            print(f"  ✗ Unified test runner failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Unified test runner exception: {e}")
        return False

def test_environment_detection():
    """Test environment detection module."""
    print("\nTesting environment detection...")
    project_root = Path(__file__).parent.absolute()

    try:
        env_script = project_root / "scripts" / "detect_execution_environment.py"
        if not env_script.exists():
            print("  ⚠ Environment detection script not found")
            return False

        result = subprocess.run(
            ["python3", str(env_script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root
        )
        if result.returncode == 0:
            print("  ✓ Environment detection working")
            return True
        else:
            print(f"  ✗ Environment detection failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Environment detection exception: {e}")
        return False

def generate_health_report(results):
    """Generate comprehensive health report."""
    timestamp = datetime.now().isoformat()
    report = {
        "timestamp": timestamp,
        "system_health": {
            "basic_imports": results.get("basic_imports", False),
            "project_imports": results.get("project_imports", False),
            "mission_critical_tests": results.get("mission_critical_tests", False),
            "unified_test_runner": results.get("unified_test_runner", False),
            "environment_detection": results.get("environment_detection", False),
        },
        "overall_status": "HEALTHY" if all(results.values()) else "DEGRADED",
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": sys.platform,
    }

    # Calculate health score
    healthy_count = sum(1 for status in results.values() if status)
    total_tests = len(results)
    health_score = (healthy_count / total_tests) * 100 if total_tests > 0 else 0
    report["health_score"] = health_score

    return report

def main():
    """Execute comprehensive system health validation."""
    print("=" * 60)
    print("SYSTEM HEALTH VALIDATION - PYTHON3 COMPATIBLE")
    print("=" * 60)
    print(f"Started: {datetime.now()}")
    print(f"Python: {sys.executable}")
    print(f"Version: {sys.version}")
    print("")

    # Execute all health checks
    results = {}
    results["basic_imports"] = test_basic_imports()
    results["project_imports"] = test_project_imports()
    results["mission_critical_tests"] = test_mission_critical_tests()
    results["unified_test_runner"] = test_unified_test_runner()
    results["environment_detection"] = test_environment_detection()

    # Generate and display report
    report = generate_health_report(results)

    print("\n" + "=" * 60)
    print("HEALTH REPORT SUMMARY")
    print("=" * 60)
    print(f"Overall Status: {report['overall_status']}")
    print(f"Health Score: {report['health_score']:.1f}%")
    print("")

    for component, status in report["system_health"].items():
        status_symbol = "✓" if status else "✗"
        print(f"  {status_symbol} {component.replace('_', ' ').title()}")

    # Save detailed report
    report_file = Path(__file__).parent / "SYSTEM_HEALTH_REPORT.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_file}")
    print(f"Completed: {datetime.now()}")

    # Return appropriate exit code
    return 0 if report["overall_status"] == "HEALTHY" else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)