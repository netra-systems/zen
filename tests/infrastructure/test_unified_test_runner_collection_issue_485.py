#!/usr/bin/env python3
"""
Test Unified Test Runner Collection for Issue #485

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Ensure reliable test collection for $500K+ ARR protection validation
- Value Impact: Reliable test collection enables comprehensive business value validation
- Strategic Impact: Foundation for validating all business-critical functionality

CRITICAL: These tests are designed to INITIALLY FAIL to demonstrate the
unified test runner collection issues identified in Issue #485. After fixes
are implemented, all tests should PASS.
"""

import sys
import os
import subprocess
import pytest
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import patch, MagicMock
import json

# Setup project root for consistent imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()  
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUnifiedTestRunnerCollection(SSotBaseTestCase):
    """
    Test unified test runner collection reliability.
    
    These tests validate that the unified test runner can consistently collect
    and categorize tests across different scenarios and execution contexts.
    """
    
    def test_unified_runner_collects_all_test_categories(self):
        """
        FAIL FIRST: Test unified runner collects expected test categories.
        
        This test should initially FAIL to demonstrate collection completeness
        issues when the unified test runner attempts to discover tests across
        different categories.
        """
        try:
            from tests.unified_test_runner import UnifiedTestRunner
        except ImportError as e:
            pytest.fail(f"Cannot import UnifiedTestRunner: {e}")
        
        # Initialize runner for testing
        runner = UnifiedTestRunner()
        
        # Expected test categories that should be discoverable
        expected_categories = [
            "unit", 
            "integration",
            "e2e",
            "mission_critical", 
            "websocket",
            "agent",
            "database",
            "api"
        ]
        
        collection_failures = []
        
        for category in expected_categories:
            try:
                # Test category collection
                if hasattr(runner, 'collect_tests_for_category'):
                    result = runner.collect_tests_for_category(category)
                elif hasattr(runner, 'discover_tests'):
                    result = runner.discover_tests(categories=[category])
                else:
                    collection_failures.append(f"{category}: No collection method found on UnifiedTestRunner")
                    continue
                
                # Validate collection result
                if result is None:
                    collection_failures.append(f"{category}: Collection returned None")
                elif isinstance(result, (list, tuple)) and len(result) == 0:
                    collection_failures.append(f"{category}: No tests collected (empty result)")
                elif hasattr(result, 'collected') and len(result.collected) == 0:
                    collection_failures.append(f"{category}: No tests in collected results")
                    
            except AttributeError as e:
                collection_failures.append(f"{category}: AttributeError - {e}")
            except Exception as e:
                collection_failures.append(f"{category}: Unexpected error - {e}")
        
        # This assertion should initially FAIL, demonstrating collection issues
        assert len(collection_failures) == 0, (
            f"Unified test runner collection failures detected in {len(collection_failures)} categories:\n" +
            "\n".join(f"  - {failure}" for failure in collection_failures) +
            "\n\nThis indicates test collection reliability issues in Issue #485."
        )
    
    def test_fast_feedback_mode_collection_complete(self):
        """
        FAIL FIRST: Test fast feedback mode collects expected tests.
        
        This test should initially FAIL to demonstrate issues with fast feedback
        mode test collection, which is critical for rapid development cycles.
        """
        try:
            from tests.unified_test_runner import UnifiedTestRunner
        except ImportError as e:
            pytest.fail(f"Cannot import UnifiedTestRunner: {e}")
        
        runner = UnifiedTestRunner()
        fast_feedback_issues = []
        
        try:
            # Test fast feedback mode collection
            if hasattr(runner, 'setup_fast_feedback_mode'):
                runner.setup_fast_feedback_mode()
            
            # Expected fast feedback categories (smoke + unit typically)
            fast_feedback_categories = ["smoke", "unit", "startup"]
            
            for category in fast_feedback_categories:
                try:
                    # Attempt collection for fast feedback
                    if hasattr(runner, 'collect_tests_for_category'):
                        result = runner.collect_tests_for_category(category)
                        
                        if not result or (hasattr(result, '__len__') and len(result) == 0):
                            fast_feedback_issues.append(f"{category}: No tests collected for fast feedback")
                    else:
                        fast_feedback_issues.append(f"{category}: Collection method not available")
                        
                except Exception as e:
                    fast_feedback_issues.append(f"{category}: Collection failed - {e}")
            
            # Test execution time estimation (should be under 2 minutes for fast feedback)
            if hasattr(runner, 'estimate_execution_time'):
                try:
                    estimated_time = runner.estimate_execution_time(mode="fast_feedback")
                    if estimated_time > 120:  # 2 minutes in seconds
                        fast_feedback_issues.append(f"Fast feedback estimated time too high: {estimated_time}s > 120s")
                except Exception as e:
                    fast_feedback_issues.append(f"Time estimation failed: {e}")
                    
        except Exception as e:
            fast_feedback_issues.append(f"Fast feedback mode setup failed: {e}")
        
        # This assertion should initially FAIL, demonstrating fast feedback collection issues
        assert len(fast_feedback_issues) == 0, (
            f"Fast feedback mode collection issues detected ({len(fast_feedback_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in fast_feedback_issues) +
            "\n\nThis indicates fast feedback mode reliability issues affecting development velocity."
        )
    
    def test_real_services_mode_collection_reliable(self):
        """
        FAIL FIRST: Test real services mode collection works reliably.
        
        This test should initially FAIL to demonstrate issues with collecting
        tests that require real services (Docker infrastructure).
        """
        try:
            from tests.unified_test_runner import UnifiedTestRunner
        except ImportError as e:
            pytest.fail(f"Cannot import UnifiedTestRunner: {e}")
        
        runner = UnifiedTestRunner()
        real_services_issues = []
        
        try:
            # Test real services mode setup
            if hasattr(runner, 'setup_real_services_mode'):
                runner.setup_real_services_mode()
            
            # Categories that require real services
            real_services_categories = ["integration", "e2e", "websocket"]
            
            for category in real_services_categories:
                try:
                    # Test collection with real services flag
                    if hasattr(runner, 'collect_tests_with_real_services'):
                        result = runner.collect_tests_with_real_services(category)
                    elif hasattr(runner, 'collect_tests_for_category'):
                        result = runner.collect_tests_for_category(category, real_services=True)
                    else:
                        real_services_issues.append(f"{category}: No real services collection method")
                        continue
                    
                    # Validate result
                    if not result:
                        real_services_issues.append(f"{category}: No real services tests collected")
                    
                    # Validate tests are marked for real services
                    if hasattr(result, 'items') or isinstance(result, (list, tuple)):
                        test_items = result.items() if hasattr(result, 'items') else result
                        
                        real_service_tests = 0
                        for item in (test_items if isinstance(test_items, (list, tuple)) else [test_items]):
                            if hasattr(item, 'markers') or hasattr(item, 'pytestmark'):
                                markers = getattr(item, 'markers', getattr(item, 'pytestmark', []))
                                if any(marker.name == 'real_services' for marker in markers if hasattr(marker, 'name')):
                                    real_service_tests += 1
                        
                        if real_service_tests == 0:
                            real_services_issues.append(f"{category}: No tests marked with @pytest.mark.real_services")
                            
                except Exception as e:
                    real_services_issues.append(f"{category}: Real services collection error - {e}")
            
        except Exception as e:
            real_services_issues.append(f"Real services mode setup failed: {e}")
        
        # This assertion should initially FAIL, demonstrating real services collection issues
        assert len(real_services_issues) == 0, (
            f"Real services mode collection issues detected ({len(real_services_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in real_services_issues) +
            "\n\nThis indicates real services test collection reliability issues."
        )
    
    def test_mission_critical_tests_always_collected(self):
        """
        FAIL FIRST: Test mission critical tests are NEVER missed in collection.
        
        This test should initially FAIL to demonstrate that mission critical tests
        (which protect business value) might not be collected reliably.
        """
        mission_critical_issues = []
        
        # Known mission critical test files that MUST be collected
        expected_mission_critical_tests = [
            "tests/mission_critical/test_websocket_agent_events_suite.py",
            "tests/mission_critical/test_ssot_compliance_suite.py"
        ]
        
        try:
            from tests.unified_test_runner import UnifiedTestRunner
            runner = UnifiedTestRunner()
            
            # Test mission critical collection
            for critical_test in expected_mission_critical_tests:
                test_path = PROJECT_ROOT / critical_test
                
                if not test_path.exists():
                    mission_critical_issues.append(f"Mission critical test not found: {critical_test}")
                    continue
                
                try:
                    # Test if mission critical test can be collected
                    if hasattr(runner, 'collect_mission_critical_tests'):
                        result = runner.collect_mission_critical_tests()
                    elif hasattr(runner, 'collect_tests_for_category'):
                        result = runner.collect_tests_for_category("mission_critical")
                    else:
                        mission_critical_issues.append("No mission critical collection method available")
                        break
                    
                    # Validate mission critical tests are in collection
                    if not result:
                        mission_critical_issues.append("No mission critical tests collected")
                        continue
                    
                    # Check if specific critical test is included
                    test_collected = False
                    if isinstance(result, (list, tuple)):
                        for item in result:
                            item_path = str(getattr(item, 'fspath', getattr(item, 'nodeid', '')))
                            if critical_test in item_path:
                                test_collected = True
                                break
                    
                    if not test_collected:
                        mission_critical_issues.append(f"Mission critical test not collected: {critical_test}")
                        
                except Exception as e:
                    mission_critical_issues.append(f"Mission critical collection error for {critical_test}: {e}")
            
            # Test that mission critical tests are NEVER skipped
            if hasattr(runner, 'can_skip_mission_critical'):
                can_skip = runner.can_skip_mission_critical()
                if can_skip:
                    mission_critical_issues.append("Mission critical tests can be skipped - THIS IS FORBIDDEN")
                    
        except ImportError as e:
            mission_critical_issues.append(f"Cannot import UnifiedTestRunner: {e}")
        
        # This assertion should initially FAIL if mission critical collection is unreliable
        assert len(mission_critical_issues) == 0, (
            f"Mission critical test collection issues detected ({len(mission_critical_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in mission_critical_issues) +
            "\n\nMission critical tests protect $500K+ ARR - collection MUST be 100% reliable."
        )


class TestTestDiscoveryReliability(SSotBaseTestCase):
    """
    Test discovery reliability validation.
    
    Tests that validate test discovery works consistently across different
    execution modes and environments.
    """
    
    def test_pytest_collection_vs_unified_runner_consistency(self):
        """
        FAIL FIRST: Test pytest vs unified runner collection consistency.
        
        This test should initially FAIL to demonstrate inconsistencies between
        direct pytest collection and unified test runner collection.
        """
        consistency_issues = []
        
        # Test categories to check for consistency
        test_categories = ["unit", "integration", "e2e"]
        
        for category in test_categories:
            try:
                # Collection via pytest directly
                pytest_cmd = [
                    sys.executable, "-m", "pytest", 
                    "--collect-only", "-q",
                    f"-m", category,
                    str(PROJECT_ROOT / "tests")
                ]
                
                pytest_result = subprocess.run(
                    pytest_cmd,
                    capture_output=True, 
                    text=True,
                    cwd=PROJECT_ROOT,
                    timeout=30
                )
                
                pytest_collected = len([
                    line for line in pytest_result.stdout.split('\n') 
                    if '::' in line and not line.startswith('=')
                ])
                
                # Collection via unified runner
                try:
                    from tests.unified_test_runner import UnifiedTestRunner
                    runner = UnifiedTestRunner()
                    
                    if hasattr(runner, 'collect_tests_for_category'):
                        unified_result = runner.collect_tests_for_category(category)
                        unified_collected = len(unified_result) if unified_result else 0
                    else:
                        consistency_issues.append(f"{category}: UnifiedTestRunner lacks collection method")
                        continue
                    
                    # Compare collection counts
                    if abs(pytest_collected - unified_collected) > 5:  # Allow small variance
                        consistency_issues.append(
                            f"{category}: Collection mismatch - "
                            f"pytest: {pytest_collected}, unified: {unified_collected}"
                        )
                        
                except Exception as e:
                    consistency_issues.append(f"{category}: Unified runner collection failed - {e}")
                    
            except subprocess.TimeoutExpired:
                consistency_issues.append(f"{category}: Pytest collection timeout")
            except Exception as e:
                consistency_issues.append(f"{category}: Collection comparison failed - {e}")
        
        # This assertion should initially FAIL if there are consistency issues
        assert len(consistency_issues) == 0, (
            f"Collection consistency issues detected ({len(consistency_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in consistency_issues) +
            "\n\nThis indicates collection method inconsistencies affecting test reliability."
        )
    
    def test_collection_works_with_different_pythonpath_configs(self):
        """
        FAIL FIRST: Test collection with different PYTHONPATH configurations.
        
        This test should initially FAIL to demonstrate how different PYTHONPATH
        configurations can affect test discovery and collection reliability.
        """
        pythonpath_issues = []
        original_pythonpath = os.environ.get('PYTHONPATH', '')
        
        # Test different PYTHONPATH configurations
        pythonpath_configs = [
            ("empty", ""),
            ("project_root_only", str(PROJECT_ROOT)),
            ("project_root_and_test_framework", f"{PROJECT_ROOT}{os.pathsep}{PROJECT_ROOT}/test_framework"),
            ("with_extra_paths", f"{PROJECT_ROOT}{os.pathsep}/fake/path{os.pathsep}{PROJECT_ROOT}/test_framework")
        ]
        
        try:
            for config_name, pythonpath_value in pythonpath_configs:
                try:
                    # Set PYTHONPATH configuration
                    os.environ['PYTHONPATH'] = pythonpath_value
                    
                    # Test collection with this PYTHONPATH
                    collection_cmd = [
                        sys.executable, "-m", "pytest",
                        "--collect-only", "-q",
                        str(PROJECT_ROOT / "tests" / "infrastructure")
                    ]
                    
                    result = subprocess.run(
                        collection_cmd,
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_ROOT,
                        timeout=20
                    )
                    
                    if result.returncode != 0:
                        pythonpath_issues.append(f"{config_name}: Collection failed with PYTHONPATH={pythonpath_value}")
                    
                    # Check if any tests were collected
                    collected_count = len([
                        line for line in result.stdout.split('\n')
                        if '::' in line and not line.startswith('=')
                    ])
                    
                    if collected_count == 0:
                        pythonpath_issues.append(f"{config_name}: No tests collected with PYTHONPATH={pythonpath_value}")
                        
                except subprocess.TimeoutExpired:
                    pythonpath_issues.append(f"{config_name}: Collection timeout with PYTHONPATH={pythonpath_value}")
                except Exception as e:
                    pythonpath_issues.append(f"{config_name}: Collection error - {e}")
                    
        finally:
            # Restore original PYTHONPATH
            if original_pythonpath:
                os.environ['PYTHONPATH'] = original_pythonpath
            elif 'PYTHONPATH' in os.environ:
                del os.environ['PYTHONPATH']
        
        # This assertion should initially FAIL if PYTHONPATH affects collection reliability
        assert len(pythonpath_issues) == 0, (
            f"PYTHONPATH configuration collection issues detected ({len(pythonpath_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in pythonpath_issues) +
            "\n\nThis indicates PYTHONPATH sensitivity in test collection affecting reliability."
        )
    
    def test_collection_performance_consistency(self):
        """
        FAIL FIRST: Test collection performance is consistent.
        
        This test should initially FAIL to demonstrate collection performance
        inconsistencies that could indicate underlying reliability issues.
        """
        import time
        performance_issues = []
        
        # Test collection performance across multiple runs
        collection_times = []
        
        for run_number in range(3):  # Test 3 collection runs
            try:
                start_time = time.time()
                
                # Perform test collection
                collection_cmd = [
                    sys.executable, "-m", "pytest",
                    "--collect-only", "-q",
                    str(PROJECT_ROOT / "tests")
                ]
                
                result = subprocess.run(
                    collection_cmd,
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT,
                    timeout=60
                )
                
                end_time = time.time()
                collection_time = end_time - start_time
                collection_times.append(collection_time)
                
                if result.returncode != 0:
                    performance_issues.append(f"Run {run_number + 1}: Collection failed")
                    
            except subprocess.TimeoutExpired:
                performance_issues.append(f"Run {run_number + 1}: Collection timeout (>60s)")
            except Exception as e:
                performance_issues.append(f"Run {run_number + 1}: Collection error - {e}")
        
        # Analyze performance consistency
        if len(collection_times) >= 2:
            avg_time = sum(collection_times) / len(collection_times)
            max_deviation = max(abs(t - avg_time) for t in collection_times)
            
            # Performance should be consistent (deviation < 50% of average)
            if max_deviation > (avg_time * 0.5):
                performance_issues.append(
                    f"Collection time inconsistency: avg={avg_time:.2f}s, max_deviation={max_deviation:.2f}s"
                )
            
            # Collection should be reasonably fast (< 30 seconds)
            if avg_time > 30:
                performance_issues.append(f"Collection too slow: avg={avg_time:.2f}s > 30s")
        
        # This assertion should initially FAIL if performance is inconsistent
        assert len(performance_issues) == 0, (
            f"Collection performance issues detected ({len(performance_issues)} problems):\n" +
            "\n".join(f"  - {issue}" for issue in performance_issues) +
            "\n\nCollection times: " + ", ".join(f"{t:.2f}s" for t in collection_times) +
            "\n\nPerformance inconsistencies may indicate underlying collection reliability issues."
        )


if __name__ == "__main__":
    # Enable verbose output for debugging
    pytest.main([__file__, "-v", "--tb=short", "--no-header"])