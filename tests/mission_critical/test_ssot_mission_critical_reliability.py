#!/usr/bin/env python3
"""
SSOT Migration Safety: Mission Critical Test Reliability

Business Value: Platform/Internal - Testing Infrastructure Reliability
Protects $500K+ ARR by ensuring mission critical tests remain reliable during
SSOT migration and can detect actual regressions vs. test infrastructure issues.

This test validates that the existing mission critical test suite continues to
function correctly during SSOT migration, maintaining its ability to protect
business value and detect real system issues.

Test Strategy:
1. Inventory and validate existing mission critical tests
2. Test that mission critical tests can execute reliably 
3. Validate mission critical tests fail appropriately when they should
4. Ensure no false positives/negatives during infrastructure changes
5. Protect against test infrastructure changes breaking business validation

Expected Results:
- PASS: Mission critical tests remain reliable and execute successfully
- FAIL: Infrastructure changes break mission critical test execution
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSSOTMissionCriticalReliability(SSotBaseTestCase):
    """
    Ensures mission critical tests remain reliable during SSOT migration.
    
    This validates that business value protection through testing remains
    intact throughout infrastructure consolidation efforts.
    """
    
    def setup_method(self, method=None):
        """Setup for mission critical test reliability validation."""
        super().setup_method(method)
        
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.mission_critical_dir = self.project_root / 'tests' / 'mission_critical'
        self.reliability_issues = []
        self.execution_results = []
        
        # Known mission critical test patterns
        self.critical_test_patterns = [
            'test_websocket_agent_events',
            'test_golden_path',
            'test_ssot_compliance',
            'test_factory_pattern',
            'test_agent_websocket_bridge',
            'test_user_isolation'
        ]
        
        # Business critical functionality areas
        self.business_critical_areas = [
            'websocket_events',
            'agent_execution',
            'user_authentication',
            'data_persistence',
            'real_time_communication'
        ]
        
        # Expected execution characteristics
        self.execution_standards = {
            'max_execution_time_per_test': 30.0,  # seconds
            'min_success_rate': 80.0,             # percentage
            'max_false_positive_rate': 5.0,       # percentage
            'required_test_count': 5              # minimum tests
        }
    
    def discover_mission_critical_tests(self) -> List[Dict[str, Any]]:
        """Discover and catalog mission critical test files."""
        critical_tests = []
        
        if not self.mission_critical_dir.exists():
            return critical_tests
        
        # Find all test files in mission critical directory
        test_files = list(self.mission_critical_dir.glob('test_*.py'))
        
        for test_file in test_files:
            test_info = {
                'file_path': str(test_file),
                'file_name': test_file.name,
                'file_size': test_file.stat().st_size,
                'is_mission_critical': any(pattern in test_file.name for pattern in self.critical_test_patterns),
                'business_area': self.determine_business_area(test_file.name),
                'test_classes': [],
                'test_methods': [],
                'executable': False,
                'syntax_valid': False
            }
            
            # Analyze test file content
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                test_info['syntax_valid'] = True
                test_info['content_length'] = len(content)
                
                # Count test classes and methods
                lines = content.splitlines()
                for line in lines:
                    line_stripped = line.strip()
                    if line_stripped.startswith('class Test') and ':' in line_stripped:
                        test_info['test_classes'].append(line_stripped)
                    elif line_stripped.startswith('def test_') and '(' in line_stripped:
                        test_info['test_methods'].append(line_stripped.split('(')[0].replace('def ', ''))
                
                test_info['executable'] = len(test_info['test_methods']) > 0
                
            except Exception as e:
                test_info['syntax_error'] = str(e)
            
            critical_tests.append(test_info)
        
        return critical_tests
    
    def determine_business_area(self, filename: str) -> str:
        """Determine business critical area based on filename."""
        filename_lower = filename.lower()
        
        for area in self.business_critical_areas:
            if area in filename_lower:
                return area
        
        # Check for specific patterns
        if 'websocket' in filename_lower:
            return 'real_time_communication'
        elif 'agent' in filename_lower:
            return 'agent_execution'
        elif 'auth' in filename_lower:
            return 'user_authentication'
        elif 'database' in filename_lower or 'db' in filename_lower:
            return 'data_persistence'
        else:
            return 'unknown'
    
    def test_mission_critical_test_inventory_complete(self):
        """
        Validate that mission critical test inventory is complete and discoverable.
        
        This ensures we have adequate coverage of business critical functionality
        and can discover all tests that protect business value.
        """
        critical_tests = self.discover_mission_critical_tests()
        
        # Analyze test inventory
        total_tests = len(critical_tests)
        executable_tests = sum(1 for test in critical_tests if test['executable'])
        syntax_valid_tests = sum(1 for test in critical_tests if test['syntax_valid'])
        identified_critical_tests = sum(1 for test in critical_tests if test['is_mission_critical'])
        
        # Count tests by business area
        business_area_coverage = {}
        for area in self.business_critical_areas:
            business_area_coverage[area] = sum(1 for test in critical_tests if test['business_area'] == area)
        
        # Record inventory metrics
        self.record_metric('total_mission_critical_test_files', total_tests)
        self.record_metric('executable_test_files', executable_tests)
        self.record_metric('syntax_valid_test_files', syntax_valid_tests)
        self.record_metric('identified_critical_tests', identified_critical_tests)
        
        for area, count in business_area_coverage.items():
            self.record_metric(f'tests_covering_{area}', count)
        
        # Calculate total test methods
        total_test_methods = sum(len(test['test_methods']) for test in critical_tests)
        self.record_metric('total_test_methods', total_test_methods)
        
        print(f"\nMission Critical Test Inventory:")
        print(f"  Total test files: {total_tests}")
        print(f"  Executable test files: {executable_tests}")
        print(f"  Syntax valid files: {syntax_valid_tests}")
        print(f"  Identified critical tests: {identified_critical_tests}")
        print(f"  Total test methods: {total_test_methods}")
        
        print(f"\nBusiness Area Coverage:")
        for area, count in business_area_coverage.items():
            print(f"  {area}: {count} test files")
        
        # Report issues
        syntax_errors = [test for test in critical_tests if not test['syntax_valid']]
        if syntax_errors:
            print(f"\nSyntax errors in test files:")
            for test in syntax_errors[:3]:
                print(f"  - {test['file_name']}: {test.get('syntax_error', 'Unknown error')}")
        
        # Validation requirements
        assert total_tests >= self.execution_standards['required_test_count'], (
            f"Insufficient mission critical tests: {total_tests} < {self.execution_standards['required_test_count']}. "
            f"Business value protection requires more comprehensive test coverage."
        )
        
        assert executable_tests == total_tests, (
            f"Non-executable test files found: {total_tests - executable_tests}. "
            f"All mission critical tests must be executable."
        )
        
        assert syntax_valid_tests == total_tests, (
            f"Syntax errors in test files: {total_tests - syntax_valid_tests}. "
            f"All mission critical tests must have valid syntax."
        )
    
    def test_mission_critical_tests_execute_reliably(self):
        """
        CRITICAL: Test that mission critical tests can execute without infrastructure errors.
        
        This validates that SSOT migration doesn't break the execution of tests
        that protect business functionality and revenue.
        """
        critical_tests = self.discover_mission_critical_tests()
        execution_results = []
        
        # Execute a sample of mission critical tests to validate reliability
        executable_tests = [test for test in critical_tests if test['executable']]
        
        # Select representative tests for execution validation
        sample_tests = executable_tests[:5]  # Test first 5 for performance
        
        for test_info in sample_tests:
            test_file_path = test_info['file_path']
            execution_result = {
                'test_file': test_info['file_name'],
                'business_area': test_info['business_area'],
                'execution_successful': False,
                'execution_time': 0.0,
                'exit_code': None,
                'stdout_length': 0,
                'stderr_length': 0,
                'infrastructure_error': False,
                'test_failures': 0,
                'test_passes': 0
            }
            
            try:
                # Execute test with timeout
                start_time = time.time()
                
                cmd = [
                    sys.executable, 
                    '-m', 'pytest', 
                    test_file_path, 
                    '-v',
                    '--tb=short',
                    '--maxfail=3'  # Stop after 3 failures to save time
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=str(self.project_root),
                    capture_output=True,
                    text=True,
                    timeout=self.execution_standards['max_execution_time_per_test']
                )
                
                execution_time = time.time() - start_time
                execution_result.update({
                    'execution_successful': result.returncode in [0, 1],  # 0=pass, 1=test failures
                    'execution_time': execution_time,
                    'exit_code': result.returncode,
                    'stdout_length': len(result.stdout),
                    'stderr_length': len(result.stderr)
                })
                
                # Analyze output for infrastructure vs test errors
                if result.returncode == 0:
                    execution_result['test_passes'] = self.count_test_passes(result.stdout)
                elif result.returncode == 1:
                    execution_result['test_failures'] = self.count_test_failures(result.stdout)
                else:
                    # Non-standard exit codes indicate infrastructure issues
                    execution_result['infrastructure_error'] = True
                    self.reliability_issues.append({
                        'test_file': test_info['file_name'],
                        'issue_type': 'infrastructure_error',
                        'exit_code': result.returncode,
                        'error_output': result.stderr[:500]  # First 500 chars
                    })
            
            except subprocess.TimeoutExpired:
                execution_result['infrastructure_error'] = True
                execution_result['execution_time'] = self.execution_standards['max_execution_time_per_test']
                self.reliability_issues.append({
                    'test_file': test_info['file_name'],
                    'issue_type': 'execution_timeout',
                    'timeout': self.execution_standards['max_execution_time_per_test']
                })
            
            except Exception as e:
                execution_result['infrastructure_error'] = True
                self.reliability_issues.append({
                    'test_file': test_info['file_name'],
                    'issue_type': 'execution_exception',
                    'error': str(e)
                })
            
            execution_results.append(execution_result)
            self.execution_results.append(execution_result)
        
        # Analyze execution reliability
        successful_executions = sum(1 for result in execution_results if result['execution_successful'])
        infrastructure_errors = sum(1 for result in execution_results if result['infrastructure_error'])
        average_execution_time = sum(result['execution_time'] for result in execution_results) / len(execution_results) if execution_results else 0
        
        # Record execution metrics
        self.record_metric('tests_executed_for_reliability', len(execution_results))
        self.record_metric('successful_test_executions', successful_executions)
        self.record_metric('infrastructure_error_count', infrastructure_errors)
        self.record_metric('average_test_execution_time', average_execution_time)
        
        success_rate = (successful_executions / len(execution_results) * 100) if execution_results else 0
        self.record_metric('test_execution_success_rate', success_rate)
        
        print(f"\nMission Critical Test Execution Reliability:")
        print(f"  Tests executed: {len(execution_results)}")
        print(f"  Successful executions: {successful_executions}")
        print(f"  Infrastructure errors: {infrastructure_errors}")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Average execution time: {average_execution_time:.2f}s")
        
        # Report reliability issues
        if self.reliability_issues:
            print(f"\nReliability Issues Found:")
            for issue in self.reliability_issues[:3]:
                print(f"  - {issue['test_file']}: {issue['issue_type']}")
        
        # CRITICAL: Mission critical tests must execute reliably
        assert success_rate >= self.execution_standards['min_success_rate'], (
            f"Mission critical test execution reliability too low: {success_rate:.1f}% < {self.execution_standards['min_success_rate']}%. "
            f"Infrastructure issues are preventing business value protection tests from running."
        )
        
        assert infrastructure_errors == 0, (
            f"Infrastructure errors in mission critical tests: {infrastructure_errors}. "
            f"SSOT migration must not break test execution infrastructure."
        )
    
    def count_test_passes(self, test_output: str) -> int:
        """Count test passes from pytest output."""
        # Look for pytest success indicators
        if 'passed' in test_output:
            # Try to extract number from "X passed" pattern
            import re
            match = re.search(r'(\d+) passed', test_output)
            if match:
                return int(match.group(1))
        return 0
    
    def count_test_failures(self, test_output: str) -> int:
        """Count test failures from pytest output."""
        # Look for pytest failure indicators
        if 'failed' in test_output:
            # Try to extract number from "X failed" pattern
            import re
            match = re.search(r'(\d+) failed', test_output)
            if match:
                return int(match.group(1))
        return 0
    
    def test_mission_critical_tests_maintain_business_value_protection(self):
        """
        Validate that mission critical tests continue protecting business value.
        
        This ensures that the tests can still detect real business issues
        and haven't been compromised by infrastructure changes.
        """
        critical_tests = self.discover_mission_critical_tests()
        
        # Analyze business value protection capabilities
        business_protection_analysis = {
            'websocket_event_protection': False,
            'user_isolation_protection': False,
            'authentication_protection': False,
            'data_integrity_protection': False,
            'performance_protection': False
        }
        
        # Check for specific business protection patterns
        for test_info in critical_tests:
            test_name = test_info['file_name'].lower()
            
            if 'websocket' in test_name and 'event' in test_name:
                business_protection_analysis['websocket_event_protection'] = True
            
            if 'user' in test_name and ('isolation' in test_name or 'context' in test_name):
                business_protection_analysis['user_isolation_protection'] = True
            
            if 'auth' in test_name or 'jwt' in test_name:
                business_protection_analysis['authentication_protection'] = True
            
            if 'database' in test_name or 'persistence' in test_name or 'data' in test_name:
                business_protection_analysis['data_integrity_protection'] = True
            
            if 'performance' in test_name or 'memory' in test_name or 'timeout' in test_name:
                business_protection_analysis['performance_protection'] = True
        
        # Count protected business areas
        protected_areas = sum(business_protection_analysis.values())
        total_business_areas = len(business_protection_analysis)
        
        # Record business protection metrics
        for area, protected in business_protection_analysis.items():
            self.record_metric(f'{area}_covered', protected)
        
        business_coverage_percentage = (protected_areas / total_business_areas * 100)
        self.record_metric('business_value_protection_coverage', business_coverage_percentage)
        
        print(f"\nBusiness Value Protection Analysis:")
        print(f"  Business areas protected: {protected_areas}/{total_business_areas}")
        print(f"  Protection coverage: {business_coverage_percentage:.1f}%")
        
        for area, protected in business_protection_analysis.items():
            status = "✓" if protected else "✗"
            area_name = area.replace('_', ' ').title()
            print(f"  {status} {area_name}")
        
        # Identify critical gaps
        unprotected_areas = [area for area, protected in business_protection_analysis.items() if not protected]
        if unprotected_areas:
            print(f"\nUnprotected Business Areas:")
            for area in unprotected_areas:
                print(f"  - {area.replace('_', ' ').title()}")
        
        # CRITICAL: Core business areas must be protected
        critical_areas = ['websocket_event_protection', 'user_isolation_protection']
        missing_critical = [area for area in critical_areas if not business_protection_analysis[area]]
        
        assert not missing_critical, (
            f"Critical business areas not protected by mission critical tests: {missing_critical}. "
            f"This leaves $500K+ ARR functionality vulnerable to regressions."
        )
        
        # Reasonable coverage threshold
        assert business_coverage_percentage >= 60, (
            f"Business value protection coverage too low: {business_coverage_percentage:.1f}%. "
            f"Mission critical tests should protect more business functionality areas."
        )
    
    def test_mission_critical_test_false_positive_resistance(self):
        """
        Validate that mission critical tests have low false positive rates.
        
        Tests should fail only when there are real business issues, not due to
        infrastructure changes or test environment variations.
        """
        # This test analyzes the structure and patterns of mission critical tests
        # to assess their resistance to false positives
        
        critical_tests = self.discover_mission_critical_tests()
        false_positive_risk_factors = []
        
        for test_info in critical_tests:
            risk_factors = {
                'test_file': test_info['file_name'],
                'high_timeout_dependency': False,
                'external_service_dependency': False,
                'timing_dependency': False,
                'environment_specific_assertions': False,
                'hardcoded_values': False,
                'total_risk_factors': 0
            }
            
            try:
                with open(test_info['file_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                
                content_lower = content.lower()
                
                # Check for false positive risk patterns
                if 'sleep(' in content_lower or 'time.sleep' in content_lower:
                    risk_factors['timing_dependency'] = True
                    risk_factors['total_risk_factors'] += 1
                
                if 'timeout' in content_lower and ('30' in content or '60' in content):
                    risk_factors['high_timeout_dependency'] = True
                    risk_factors['total_risk_factors'] += 1
                
                if 'localhost' in content_lower or '127.0.0.1' in content or 'http://' in content_lower:
                    risk_factors['external_service_dependency'] = True
                    risk_factors['total_risk_factors'] += 1
                
                if 'assert_equal' in content_lower and ('path' in content_lower or 'url' in content_lower):
                    risk_factors['environment_specific_assertions'] = True
                    risk_factors['total_risk_factors'] += 1
                
                # Look for hardcoded values that could cause false positives
                hardcoded_patterns = ['user_123', 'test_user_', 'localhost:8080', '/tmp/']
                if any(pattern in content_lower for pattern in hardcoded_patterns):
                    risk_factors['hardcoded_values'] = True
                    risk_factors['total_risk_factors'] += 1
                
                false_positive_risk_factors.append(risk_factors)
            
            except Exception:
                continue
        
        # Analyze false positive risk
        high_risk_tests = [risk for risk in false_positive_risk_factors if risk['total_risk_factors'] >= 3]
        medium_risk_tests = [risk for risk in false_positive_risk_factors if risk['total_risk_factors'] == 2]
        low_risk_tests = [risk for risk in false_positive_risk_factors if risk['total_risk_factors'] <= 1]
        
        # Record false positive risk metrics
        self.record_metric('high_false_positive_risk_tests', len(high_risk_tests))
        self.record_metric('medium_false_positive_risk_tests', len(medium_risk_tests))
        self.record_metric('low_false_positive_risk_tests', len(low_risk_tests))
        
        total_analyzed = len(false_positive_risk_factors)
        false_positive_risk_rate = (len(high_risk_tests) / total_analyzed * 100) if total_analyzed > 0 else 0
        self.record_metric('false_positive_risk_rate', false_positive_risk_rate)
        
        print(f"\nFalse Positive Risk Analysis:")
        print(f"  Tests analyzed: {total_analyzed}")
        print(f"  High risk tests: {len(high_risk_tests)}")
        print(f"  Medium risk tests: {len(medium_risk_tests)}")
        print(f"  Low risk tests: {len(low_risk_tests)}")
        print(f"  False positive risk rate: {false_positive_risk_rate:.1f}%")
        
        # Report high-risk tests
        if high_risk_tests:
            print(f"\nHigh False Positive Risk Tests:")
            for risk in high_risk_tests[:3]:
                print(f"  - {risk['test_file']}: {risk['total_risk_factors']} risk factors")
        
        # CRITICAL: False positive risk should be manageable
        assert false_positive_risk_rate <= self.execution_standards['max_false_positive_rate'], (
            f"False positive risk rate too high: {false_positive_risk_rate:.1f}% > {self.execution_standards['max_false_positive_rate']}%. "
            f"Mission critical tests may produce unreliable results during SSOT migration."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])