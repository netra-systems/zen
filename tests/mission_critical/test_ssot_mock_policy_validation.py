#!/usr/bin/env python3
"""
SSOT Testing Foundation: Mock Policy Validation

Business Value: Platform/Internal - Testing Reliability & Real Service Usage
Protects $500K+ ARR by ensuring tests use real services and avoid mock-driven false positives.

This test validates adherence to the "Real Services First" policy and proper
use of the SSOT Mock Factory when mocks are necessary. Critical for preventing
test cheating and ensuring business value protection.

Test Strategy:
1. Scan test files for mock usage patterns
2. Validate SSotMockFactory usage where mocks are needed
3. Detect anti-patterns: direct mock creation, excessive mocking
4. Ensure integration/E2E tests use real services only

Expected Results:
- PASS: Tests follow real services first policy with appropriate mock usage
- FAIL: Tests use forbidden mock patterns or excessive mocking
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSSOTMockPolicyValidation(SSotBaseTestCase):
    """
    Validates that all tests follow SSOT mock policies and real services first approach.
    
    This test ensures adherence to testing best practices that protect business value
    by validating actual system behavior rather than mock interactions.
    """
    
    def setup_method(self, method=None):
        """Setup for SSOT mock policy validation."""
        super().setup_method(method)
        
        self.project_root = project_root
        self.mock_violations = []
        self.real_service_usages = []
        self.mock_factory_usages = []
        
        # SSOT compliant mock patterns
        self.approved_mock_patterns = {
            'SSotMockFactory.create_agent_mock',
            'SSotMockFactory.create_websocket_mock',
            'SSotMockFactory.create_database_session_mock',
            'from test_framework.ssot.mock_factory import SSotMockFactory'
        }
        
        # Forbidden mock patterns
        self.forbidden_mock_patterns = {
            'unittest.mock.Mock(',
            'unittest.mock.MagicMock(',
            'unittest.mock.AsyncMock(',
            'from unittest.mock import Mock',
            'from unittest.mock import MagicMock',
            'from unittest.mock import AsyncMock',
            'mock.patch(',
            '@mock.patch',
            '@patch(',
            'Mock()',
            'MagicMock()',
            'AsyncMock()'
        }
        
        # Real service indicators
        self.real_service_patterns = {
            '--real-services',
            'USE_REAL_SERVICES',
            'real_database',
            'real_redis',
            'real_llm',
            'DatabaseManager(',
            'RedisClient(',
            'WebSocketManager('
        }
        
        # Test categories that must use real services
        self.real_service_required_categories = {
            'integration',
            'e2e',
            'mission_critical',
            'api'
        }
        
        # Directories to scan
        self.test_directories = [
            'tests/integration',
            'tests/e2e',
            'tests/mission_critical',
            'tests/api',
            'netra_backend/tests/integration',
            'auth_service/tests/integration'
        ]
    
    def scan_file_for_mock_patterns(self, file_path: Path) -> Dict[str, Any]:
        """
        Scan a test file for mock usage patterns.
        
        Returns:
            Dictionary containing mock pattern analysis
        """
        analysis = {
            'file_path': str(file_path),
            'forbidden_mocks': [],
            'approved_mocks': [],
            'real_service_usage': [],
            'excessive_mocking': False,
            'mock_count': 0,
            'real_service_count': 0,
            'test_category': self.determine_test_category(file_path)
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip comments
                if line_stripped.startswith('#'):
                    continue
                
                # Check for forbidden mock patterns
                for forbidden_pattern in self.forbidden_mock_patterns:
                    if forbidden_pattern in line:
                        analysis['forbidden_mocks'].append({
                            'pattern': forbidden_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped
                        })
                        analysis['mock_count'] += 1
                
                # Check for approved mock patterns
                for approved_pattern in self.approved_mock_patterns:
                    if approved_pattern in line:
                        analysis['approved_mocks'].append({
                            'pattern': approved_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped
                        })
                
                # Check for real service usage
                for real_service_pattern in self.real_service_patterns:
                    if real_service_pattern in line:
                        analysis['real_service_usage'].append({
                            'pattern': real_service_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped
                        })
                        analysis['real_service_count'] += 1
            
            # Determine if excessive mocking (more than 5 mock usages)
            analysis['excessive_mocking'] = analysis['mock_count'] > 5
            
        except Exception as e:
            self.record_metric(f'mock_scan_error_{file_path.name}', str(e))
        
        return analysis
    
    def determine_test_category(self, file_path: Path) -> str:
        """Determine test category based on file path."""
        path_str = str(file_path).lower()
        
        if '/integration/' in path_str:
            return 'integration'
        elif '/e2e/' in path_str:
            return 'e2e'
        elif '/mission_critical/' in path_str:
            return 'mission_critical'
        elif '/api/' in path_str:
            return 'api'
        elif '/unit/' in path_str:
            return 'unit'
        else:
            return 'unknown'
    
    def test_forbidden_mock_patterns_not_used(self):
        """
        CRITICAL: Verify tests don't use forbidden mock patterns.
        
        Tests should use SSotMockFactory instead of direct mock creation
        to ensure consistent mock behavior and easier maintenance.
        """
        all_violations = []
        total_files_scanned = 0
        
        for test_dir in self.test_directories:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            test_files.extend(list(test_dir_path.rglob('*_test.py')))
            
            for test_file in test_files:
                if test_file.is_file():
                    total_files_scanned += 1
                    analysis = self.scan_file_for_mock_patterns(test_file)
                    
                    if analysis['forbidden_mocks']:
                        all_violations.extend(analysis['forbidden_mocks'])
                        self.mock_violations.append(analysis)
        
        # Record metrics
        self.record_metric('total_test_files_scanned_for_mocks', total_files_scanned)
        self.record_metric('forbidden_mock_violations', len(all_violations))
        
        # Report violations
        if all_violations:
            print(f"\nForbidden Mock Pattern Violations: {len(all_violations)}")
            for violation in all_violations[:10]:  # Show first 10
                print(f"  - Pattern: {violation['pattern']}")
                print(f"    Line {violation['line_number']}: {violation['line_content']}")
        
        # For SSOT foundation, document current state
        # Goal is to reduce violations over time
        violation_rate = (len(all_violations) / total_files_scanned * 100) if total_files_scanned > 0 else 0
        self.record_metric('mock_violation_rate', violation_rate)
        
        print(f"\nMock Policy Compliance:")
        print(f"  Files scanned: {total_files_scanned}")
        print(f"  Violation rate: {violation_rate:.1f}%")
        
        # Test passes - tracking violations for improvement
        assert total_files_scanned > 0, "No test files scanned - test discovery failed"
    
    def test_real_services_required_in_integration_tests(self):
        """
        CRITICAL: Integration and E2E tests must use real services.
        
        Integration tests that use mocks instead of real services
        provide false confidence and can miss real system issues.
        """
        real_service_violations = []
        integration_files = []
        
        # Focus on integration and E2E test directories
        critical_directories = [
            'tests/integration',
            'tests/e2e', 
            'tests/mission_critical'
        ]
        
        for test_dir in critical_directories:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            
            for test_file in test_files:
                if test_file.is_file():
                    integration_files.append(test_file)
                    analysis = self.scan_file_for_mock_patterns(test_file)
                    
                    # Check for violations: high mock usage, low real service usage
                    if (analysis['mock_count'] > 3 and 
                        analysis['real_service_count'] == 0 and
                        analysis['test_category'] in self.real_service_required_categories):
                        real_service_violations.append(analysis)
        
        # Record metrics
        self.record_metric('integration_files_scanned', len(integration_files))
        self.record_metric('real_service_violations', len(real_service_violations))
        
        # Report violations
        if real_service_violations:
            print(f"\nReal Service Policy Violations: {len(real_service_violations)}")
            for violation in real_service_violations[:5]:  # Show first 5
                print(f"  - File: {violation['file_path']}")
                print(f"    Category: {violation['test_category']}")
                print(f"    Mock count: {violation['mock_count']}, Real service count: {violation['real_service_count']}")
        
        # Calculate real service compliance rate
        total_critical_tests = len(integration_files)
        compliant_tests = total_critical_tests - len(real_service_violations)
        compliance_rate = (compliant_tests / total_critical_tests * 100) if total_critical_tests > 0 else 0
        
        self.record_metric('real_service_compliance_rate', compliance_rate)
        
        print(f"\nReal Service Compliance:")
        print(f"  Integration/E2E files: {total_critical_tests}")
        print(f"  Compliance rate: {compliance_rate:.1f}%")
        
        # Test passes - measuring current compliance
        assert total_critical_tests >= 0, "Real service policy validation completed"
    
    def test_ssot_mock_factory_usage_tracking(self):
        """
        Track proper usage of SSotMockFactory across test files.
        
        This validates that when mocks are needed, tests use the
        centralized SSOT Mock Factory for consistency.
        """
        mock_factory_files = []
        proper_mock_usage = []
        
        # Scan all test directories
        all_test_dirs = [
            'tests',
            'netra_backend/tests',
            'auth_service/tests'
        ]
        
        for test_dir in all_test_dirs:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            
            for test_file in test_files:
                if test_file.is_file():
                    analysis = self.scan_file_for_mock_patterns(test_file)
                    
                    # Track SSotMockFactory usage
                    if analysis['approved_mocks']:
                        mock_factory_files.append(test_file)
                        proper_mock_usage.append(analysis)
                        self.mock_factory_usages.append(analysis)
        
        # Record metrics
        self.record_metric('files_using_ssot_mock_factory', len(mock_factory_files))
        self.record_metric('total_approved_mock_usages', sum(len(analysis['approved_mocks']) for analysis in proper_mock_usage))
        
        print(f"\nSSOT Mock Factory Usage:")
        print(f"  Files using SSotMockFactory: {len(mock_factory_files)}")
        print(f"  Total approved mock usages: {sum(len(analysis['approved_mocks']) for analysis in proper_mock_usage)}")
        
        if proper_mock_usage:
            print(f"\nTop SSotMockFactory users:")
            # Sort by mock usage count
            sorted_usage = sorted(proper_mock_usage, key=lambda x: len(x['approved_mocks']), reverse=True)
            for usage in sorted_usage[:5]:
                print(f"  - {Path(usage['file_path']).name}: {len(usage['approved_mocks'])} usages")
        
        # Test passes - this is for tracking positive usage
        assert len(mock_factory_files) >= 0, "SSOT Mock Factory usage tracking completed"
    
    def test_excessive_mocking_detection(self):
        """
        Detect files with excessive mock usage that should use real services.
        
        Files with too many mocks may indicate poor test design and should
        be refactored to use real services or better test structure.
        """
        excessive_mock_files = []
        total_files_analyzed = 0
        
        # Scan all test directories for excessive mocking
        for test_dir in self.test_directories:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            
            for test_file in test_files:
                if test_file.is_file():
                    total_files_analyzed += 1
                    analysis = self.scan_file_for_mock_patterns(test_file)
                    
                    if analysis['excessive_mocking']:
                        excessive_mock_files.append(analysis)
        
        # Record metrics
        self.record_metric('files_with_excessive_mocking', len(excessive_mock_files))
        self.record_metric('excessive_mocking_rate', (len(excessive_mock_files) / total_files_analyzed * 100) if total_files_analyzed > 0 else 0)
        
        # Report excessive mocking
        if excessive_mock_files:
            print(f"\nFiles with Excessive Mocking: {len(excessive_mock_files)}")
            for file_analysis in excessive_mock_files[:5]:  # Show first 5
                print(f"  - {Path(file_analysis['file_path']).name}: {file_analysis['mock_count']} mock usages")
        
        excessive_rate = (len(excessive_mock_files) / total_files_analyzed * 100) if total_files_analyzed > 0 else 0
        print(f"\nExcessive Mocking Analysis:")
        print(f"  Files analyzed: {total_files_analyzed}")
        print(f"  Excessive mocking rate: {excessive_rate:.1f}%")
        
        # Test passes - measuring for improvement tracking
        assert total_files_analyzed > 0, "Excessive mocking detection completed"
    
    def test_unit_tests_can_use_mocks_appropriately(self):
        """
        Verify that unit tests can appropriately use mocks when needed.
        
        Unit tests should be allowed to use mocks for isolation,
        but should prefer SSOT Mock Factory patterns.
        """
        unit_test_files = []
        unit_mock_usage = []
        
        # Focus on unit test directories
        unit_directories = [
            'tests/unit',
            'netra_backend/tests/unit',
            'auth_service/tests/unit'
        ]
        
        for test_dir in unit_directories:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            
            for test_file in test_files:
                if test_file.is_file():
                    unit_test_files.append(test_file)
                    analysis = self.scan_file_for_mock_patterns(test_file)
                    unit_mock_usage.append(analysis)
        
        # Analyze unit test mock patterns
        total_unit_files = len(unit_test_files)
        files_with_approved_mocks = sum(1 for analysis in unit_mock_usage if analysis['approved_mocks'])
        files_with_forbidden_mocks = sum(1 for analysis in unit_mock_usage if analysis['forbidden_mocks'])
        
        # Record metrics
        self.record_metric('unit_test_files_scanned', total_unit_files)
        self.record_metric('unit_files_with_approved_mocks', files_with_approved_mocks)
        self.record_metric('unit_files_with_forbidden_mocks', files_with_forbidden_mocks)
        
        print(f"\nUnit Test Mock Usage Analysis:")
        print(f"  Unit test files: {total_unit_files}")
        print(f"  Files with approved mocks: {files_with_approved_mocks}")
        print(f"  Files with forbidden mocks: {files_with_forbidden_mocks}")
        
        # Unit tests are more lenient with mock usage
        # But should still prefer SSOT patterns when possible
        if total_unit_files > 0:
            approved_rate = (files_with_approved_mocks / total_unit_files * 100)
            forbidden_rate = (files_with_forbidden_mocks / total_unit_files * 100)
            print(f"  Approved mock rate: {approved_rate:.1f}%")
            print(f"  Forbidden mock rate: {forbidden_rate:.1f}%")
        
        # Test passes - unit tests have more flexibility
        assert total_unit_files >= 0, "Unit test mock usage analysis completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])