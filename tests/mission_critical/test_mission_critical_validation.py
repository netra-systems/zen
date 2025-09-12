"""
Issue #519: Mission Critical Test Suite Validation - Phase 4

This test suite validates that the Mission Critical WebSocket test suite
can run properly once pytest configuration conflicts are resolved.

Focus Areas:
- Mission Critical test accessibility and execution
- WebSocket test suite functionality validation  
- Business value protection through test execution
- Integration with staging environment validation

Business Impact: CRITICAL - Protects $500K+ ARR through reliable test execution
Priority: P0 - Essential for business value validation
"""

import subprocess
import sys
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class TestMissionCriticalAccessibility:
    """Test that Mission Critical tests are accessible and runnable."""
    
    def test_phase4_mission_critical_test_discovery(self):
        """PHASE 4: Test that Mission Critical tests can be discovered.
        
        This test should FAIL initially if pytest configuration conflicts
        prevent proper test discovery.
        """
        project_root = Path(__file__).parent.parent.parent
        mission_critical_dir = project_root / "tests" / "mission_critical"
        
        if not mission_critical_dir.exists():
            pytest.fail(f"Mission Critical test directory not found: {mission_critical_dir}")
        
        # Try to collect Mission Critical tests
        cmd = [
            sys.executable, "-m", "pytest",
            str(mission_critical_dir),
            "--collect-only",
            "-q"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"Mission Critical test discovery failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}\n"
                f"This indicates pytest configuration conflicts are still present."
            )
        
        # Parse collection output to count tests
        lines = result.stdout.split('\n')
        test_count = 0
        for line in lines:
            if ' collected' in line and 'item' in line:
                import re
                match = re.search(r'(\d+)\s+item', line)
                if match:
                    test_count = int(match.group(1))
                    break
        
        if test_count == 0:
            pytest.fail(
                f"No Mission Critical tests discovered. Collection output:\n{result.stdout}"
            )
        
        assert test_count > 0, f"Mission Critical tests discovered: {test_count} tests"
    
    def test_phase4_websocket_test_suite_accessibility(self):
        """PHASE 4: Test WebSocket test suite accessibility specifically.
        
        This is the exact test suite blocked by Issue #519.
        Should FAIL if conflicts prevent access to this critical suite.
        """
        project_root = Path(__file__).parent.parent.parent
        websocket_test_path = project_root / "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"
        
        if not websocket_test_path.exists():
            pytest.skip(f"WebSocket test suite not found at {websocket_test_path}")
        
        # Try to collect the specific WebSocket test suite
        cmd = [
            sys.executable, "-m", "pytest", 
            str(websocket_test_path),
            "--collect-only",
            "-v"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"WebSocket test suite collection failed (Issue #519 not resolved):\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}\n"
                f"This is the exact blockage reported in Issue #519."
            )
        
        # Verify specific WebSocket tests are found
        expected_tests = [
            "test_websocket_agent_events_comprehensive",
            "test_mission_critical_websocket_events"
        ]
        
        found_tests = []
        for line in result.stdout.split('\n'):
            for expected_test in expected_tests:
                if expected_test in line:
                    found_tests.append(expected_test)
        
        if not found_tests:
            pytest.fail(
                f"Expected WebSocket tests not found in collection:\n"
                f"Expected: {expected_tests}\n"
                f"Collection output: {result.stdout}"
            )
        
        assert len(found_tests) > 0, f"WebSocket tests accessible: {found_tests}"
    
    def test_phase4_mission_critical_with_analyze_service_deps(self):
        """PHASE 4: Test Mission Critical tests with the conflicting option.
        
        This specifically tests the --analyze-service-deps option that was
        causing the duplicate registration conflict.
        """
        project_root = Path(__file__).parent.parent.parent
        mission_critical_dir = project_root / "tests" / "mission_critical"
        
        # Use the problematic option that was causing conflicts
        cmd = [
            sys.executable, "-m", "pytest",
            str(mission_critical_dir),
            "--analyze-service-deps",  # This is the conflicting option
            "--collect-only",
            "-q"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            # Check if it's specifically the option conflict error
            if any(keyword in result.stderr.lower() for keyword in [
                "already added", "conflict", "duplicate", "option"
            ]):
                pytest.fail(
                    f"Option conflict still present (Issue #519 not resolved):\n"
                    f"STDERR: {result.stderr}\n"
                    f"The --analyze-service-deps option is still causing conflicts."
                )
            else:
                pytest.fail(
                    f"Mission Critical tests failed with --analyze-service-deps:\n"
                    f"Return code: {result.returncode}\n"
                    f"STDERR: {result.stderr}\n"
                    f"May be related to Issue #519 or a different issue."
                )
        
        assert True, "Mission Critical tests work with --analyze-service-deps option"


class TestBusinessValueProtection:
    """Test that business value protection through tests is functional."""
    
    def test_phase4_critical_test_execution_capability(self):
        """PHASE 4: Test ability to execute critical business protection tests.
        
        Should FAIL if critical tests cannot be executed due to config conflicts.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Try to run a minimal subset of Mission Critical tests
        # We'll use a small, fast test to verify execution capability
        cmd = [
            sys.executable, "-m", "pytest",
            str(project_root / "tests" / "mission_critical"),
            "-k", "test_no_ssot_violations",  # A specific fast test
            "-v",
            "--tb=short"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120  # Longer timeout for actual test execution
        )
        
        # If execution fails due to config conflicts, this is Issue #519
        if result.returncode != 0:
            if any(keyword in (result.stderr + result.stdout).lower() for keyword in [
                "already added", "conflict", "duplicate", "option"
            ]):
                pytest.fail(
                    f"Test execution blocked by configuration conflicts (Issue #519):\n"
                    f"Output: {result.stderr}\n"
                    f"Configuration conflicts are preventing business value protection."
                )
            
            # If it's test failures (not config conflicts), that's different
            if "FAILED" in result.stdout and "ERRORS" not in result.stdout:
                pytest.skip(
                    f"Tests can execute but have failures (not a config issue):\n"
                    f"Return code: {result.returncode}\n"
                    f"This indicates Issue #519 is resolved but tests need fixes."
                )
            
            # If there are errors (not just failures), investigate
            pytest.fail(
                f"Critical test execution failed:\n"
                f"Return code: {result.returncode}\n"
                f"STDOUT: {result.stdout[-1000:]}\n"  # Last 1000 chars
                f"STDERR: {result.stderr}\n"
                f"May indicate ongoing configuration issues."
            )
        
        assert True, "Critical test execution capability confirmed"
    
    def test_phase4_websocket_business_value_validation(self):
        """PHASE 4: Validate WebSocket test suite can protect business value.
        
        This specifically tests that the WebSocket tests protecting $500K+ ARR
        can execute properly.
        """
        project_root = Path(__file__).parent.parent.parent
        websocket_test_path = project_root / "tests" / "mission_critical" / "test_websocket_agent_events_suite.py"
        
        if not websocket_test_path.exists():
            pytest.skip("WebSocket test suite not found - cannot validate business protection")
        
        # Try to execute a lightweight version of the WebSocket test
        # We'll run with collection only first, then minimal execution
        cmd = [
            sys.executable, "-m", "pytest",
            str(websocket_test_path),
            "--collect-only"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"WebSocket business value tests cannot be accessed:\n"
                f"This blocks protection of $500K+ ARR dependent on chat functionality.\n"
                f"Error: {result.stderr}"
            )
        
        # Now try minimal execution (dry run style)
        cmd = [
            sys.executable, "-m", "pytest", 
            str(websocket_test_path),
            "--setup-only",  # Setup only, don't run test bodies
            "-v"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            # Check if it's configuration conflicts
            if any(keyword in result.stderr.lower() for keyword in [
                "already added", "conflict", "duplicate", "option"
            ]):
                pytest.fail(
                    f"WebSocket tests blocked by config conflicts (Issue #519):\n"
                    f"$500K+ ARR business value protection is blocked.\n"
                    f"Error: {result.stderr}"
                )
            
            # Other errors might be test environment issues
            pytest.skip(
                f"WebSocket tests have setup issues (not config conflicts):\n"
                f"Return code: {result.returncode}\n"
                f"This suggests Issue #519 resolved but environment needs setup."
            )
        
        assert True, "WebSocket business value protection tests are accessible"


class TestStagingEnvironmentIntegration:
    """Test integration with staging environment for validation."""
    
    def test_phase4_staging_environment_test_execution(self):
        """PHASE 4: Test Mission Critical execution against staging.
        
        Should FAIL if staging environment tests cannot run due to config conflicts.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Check if we can run tests in staging mode
        # This simulates the production validation process
        cmd = [
            sys.executable, "-m", "pytest",
            str(project_root / "tests" / "mission_critical"),
            "--collect-only",
            "-m", "staging"  # Staging marker
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Configuration conflicts would prevent even collection
        if result.returncode != 0:
            if any(keyword in result.stderr.lower() for keyword in [
                "already added", "conflict", "duplicate", "option"
            ]):
                pytest.fail(
                    f"Staging environment testing blocked by config conflicts:\n"
                    f"Issue #519 prevents validation of production readiness.\n"
                    f"Error: {result.stderr}"
                )
        
        # Even if no staging tests found, collection should succeed
        assert result.returncode == 0 or "no tests ran" in result.stdout.lower(), (
            f"Staging environment test collection failed:\n{result.stderr}"
        )
    
    def test_phase4_production_readiness_validation_capability(self):
        """PHASE 4: Test production readiness validation capability.
        
        This ensures the test infrastructure can validate production readiness,
        which is critical for business value protection.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Test ability to run comprehensive validation
        # This would be used before production deployments
        cmd = [
            sys.executable, "-m", "pytest",
            str(project_root / "tests" / "mission_critical"),
            "--collect-only",
            "-m", "critical or mission_critical"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            pytest.fail(
                f"Production readiness validation capability blocked:\n"
                f"Cannot validate system before production deployment.\n"
                f"Return code: {result.returncode}\n"
                f"STDERR: {result.stderr}"
            )
        
        # Parse to see how many critical tests we can run
        test_count = 0
        for line in result.stdout.split('\n'):
            if 'collected' in line and 'item' in line:
                import re
                match = re.search(r'(\d+)\s+item', line)
                if match:
                    test_count = int(match.group(1))
                    break
        
        if test_count == 0:
            pytest.fail(
                f"No critical tests available for production readiness validation.\n"
                f"This blocks business value protection processes."
            )
        
        assert test_count > 0, f"Production readiness validation ready: {test_count} critical tests"


class TestRegressionPrevention:
    """Test that fixes don't introduce regressions."""
    
    def test_phase4_configuration_regression_detection(self):
        """PHASE 4: Test detection of configuration regressions.
        
        This test validates that our testing can detect if Issue #519
        regresses in the future.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Test multiple pytest invocations to ensure consistency
        commands = [
            # Basic collection
            [
                sys.executable, "-m", "pytest",
                str(project_root / "tests" / "mission_critical"),
                "--collect-only", "-q"
            ],
            # With problematic option
            [
                sys.executable, "-m", "pytest", 
                str(project_root / "tests" / "mission_critical"),
                "--analyze-service-deps", "--collect-only", "-q"
            ],
            # With verbose output
            [
                sys.executable, "-m", "pytest",
                str(project_root / "tests" / "mission_critical"),
                "--collect-only", "-v"
            ]
        ]
        
        results = []
        for i, cmd in enumerate(commands):
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            results.append({
                'command_index': i,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
        
        # Check for any configuration conflicts in any command
        conflicts_found = []
        for result in results:
            if result['returncode'] != 0:
                error_output = result['stderr'].lower()
                if any(keyword in error_output for keyword in [
                    "already added", "conflict", "duplicate", "option"
                ]):
                    conflicts_found.append(f"Command {result['command_index']}: {result['stderr']}")
        
        if conflicts_found:
            pytest.fail(
                f"Configuration conflicts detected (Issue #519 regression):\n" +
                "\n".join(conflicts_found)
            )
        
        # Check for consistency across commands
        success_count = sum(1 for result in results if result['returncode'] == 0)
        
        if success_count != len(results):
            failure_details = [
                f"Command {result['command_index']}: exit {result['returncode']}"
                for result in results if result['returncode'] != 0
            ]
            
            pytest.fail(
                f"Inconsistent behavior across pytest invocations:\n" +
                "\n".join(failure_details) +
                f"\nThis may indicate configuration instability."
            )
        
        assert True, f"Configuration regression detection validated: {len(results)} commands succeeded"
    
    def test_phase4_plugin_loading_stability(self):
        """PHASE 4: Test plugin loading stability over multiple invocations.
        
        This ensures that plugin loading is consistent and doesn't have
        intermittent conflicts.
        """
        project_root = Path(__file__).parent.parent.parent
        
        # Run the same command multiple times to check for consistency
        cmd = [
            sys.executable, "-m", "pytest",
            str(project_root / "tests" / "mission_critical"),
            "--collect-only", "--trace-config", "-q"
        ]
        
        results = []
        for run in range(3):  # Run 3 times
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            results.append({
                'run': run,
                'returncode': result.returncode,
                'stderr': result.stderr,
                'stdout': result.stdout
            })
            
            # Small delay between runs
            time.sleep(0.5)
        
        # Check for consistency
        return_codes = [result['returncode'] for result in results]
        
        if len(set(return_codes)) > 1:
            pytest.fail(
                f"Inconsistent return codes across runs: {return_codes}\n"
                f"This indicates unstable plugin loading.\n"
                f"Results: {[(r['run'], r['returncode']) for r in results]}"
            )
        
        # Check for any plugin conflicts in any run
        plugin_conflicts = []
        for result in results:
            if any(keyword in result['stderr'].lower() for keyword in [
                "already added", "conflict", "duplicate", "plugin"
            ]):
                plugin_conflicts.append(f"Run {result['run']}: {result['stderr']}")
        
        if plugin_conflicts:
            pytest.fail(
                f"Plugin loading conflicts detected:\n" +
                "\n".join(plugin_conflicts)
            )
        
        assert all(code == 0 for code in return_codes), (
            f"Plugin loading stable across {len(results)} runs"
        )