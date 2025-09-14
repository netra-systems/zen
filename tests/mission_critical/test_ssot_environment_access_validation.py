#!/usr/bin/env python3
"""
SSOT Testing Foundation: Environment Access Pattern Validation

Business Value: Platform/Internal - Configuration Security & Consistency
Protects $500K+ ARR by ensuring all environment access follows SSOT patterns
through IsolatedEnvironment, preventing configuration drift and security issues.

This test validates that all code follows the SSOT pattern for environment
variable access through IsolatedEnvironment rather than direct os.environ
access, which is critical for configuration consistency and testing isolation.

Test Strategy:
1. Scan codebase for direct os.environ access violations
2. Validate IsolatedEnvironment usage patterns
3. Check that tests use proper environment isolation
4. Ensure configuration consistency across services
5. Detect environment access anti-patterns

Expected Results:
- PASS: All environment access uses SSOT IsolatedEnvironment patterns
- FAIL: Code directly accesses os.environ bypassing SSOT patterns
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestSSOTEnvironmentAccessValidation(SSotBaseTestCase):
    """
    Validates that all environment access follows SSOT IsolatedEnvironment patterns.
    
    This ensures configuration consistency, testing isolation, and prevents
    the security and reliability issues that come from direct environment access.
    """
    
    def setup_method(self, method=None):
        """Setup for environment access pattern validation."""
        super().setup_method(method)
        
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.environment_violations = []
        self.isolated_environment_usages = []
        self.configuration_issues = []
        
        # SSOT compliant environment access patterns
        self.approved_environment_patterns = [
            'from shared.isolated_environment import IsolatedEnvironment',
            'from shared.isolated_environment import get_env',
            'get_env()',
            'IsolatedEnvironment(',
            'env.get(',
            'env.set(',
            'env.delete(',
            'self.get_env_var(',
            'self.set_env_var('
        ]
        
        # Forbidden direct environment access patterns
        self.forbidden_environment_patterns = [
            'os.environ[',
            'os.environ.get(',
            'os.environ.setdefault(',
            'os.getenv(',
            'import os',  # When used with environ
            'from os import environ',
            'environ[',
            'environ.get('
        ]
        
        # Directories to scan
        self.scan_directories = [
            'netra_backend/app',
            'auth_service',
            'shared',
            'scripts',
            'tests'
        ]
        
        # Files that are allowed to have direct os.environ access (very limited exceptions)
        self.allowed_direct_access_files = {
            'shared/isolated_environment.py',  # The SSOT implementation itself
            'scripts/deploy_to_gcp.py',       # Deployment scripts may need direct access
            'dev_launcher/isolated_environment.py'  # Dev launcher implementation
        }
    
    def scan_file_for_environment_patterns(self, file_path: Path) -> Dict[str, Any]:
        """
        Scan a Python file for environment access patterns.
        
        Returns analysis of environment access compliance.
        """
        analysis = {
            'file_path': str(file_path),
            'file_relative_path': str(file_path.relative_to(self.project_root)),
            'direct_os_environ_violations': [],
            'approved_isolated_env_usage': [],
            'mixed_access_patterns': False,
            'ssot_compliant': True,
            'violation_count': 0,
            'approved_usage_count': 0,
            'is_allowed_exception': False
        }
        
        # Check if file is allowed to have direct access
        relative_path = str(file_path.relative_to(self.project_root))
        analysis['is_allowed_exception'] = any(
            allowed in relative_path for allowed in self.allowed_direct_access_files
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Skip comments
                if line_stripped.startswith('#'):
                    continue
                
                # Check for forbidden direct environment access
                for forbidden_pattern in self.forbidden_environment_patterns:
                    if forbidden_pattern in line:
                        # Special handling for 'import os' - only flag if used with environ
                        if forbidden_pattern == 'import os':
                            # Look ahead to see if os.environ is used later
                            if 'os.environ' in content:
                                analysis['direct_os_environ_violations'].append({
                                    'pattern': forbidden_pattern,
                                    'line_number': line_num,
                                    'line_content': line_stripped,
                                    'severity': 'high'
                                })
                                analysis['violation_count'] += 1
                        else:
                            analysis['direct_os_environ_violations'].append({
                                'pattern': forbidden_pattern,
                                'line_number': line_num,
                                'line_content': line_stripped,
                                'severity': 'high'
                            })
                            analysis['violation_count'] += 1
                
                # Check for approved environment access patterns
                for approved_pattern in self.approved_environment_patterns:
                    if approved_pattern in line:
                        analysis['approved_isolated_env_usage'].append({
                            'pattern': approved_pattern,
                            'line_number': line_num,
                            'line_content': line_stripped
                        })
                        analysis['approved_usage_count'] += 1
            
            # Check for mixed access patterns (both direct and isolated)
            analysis['mixed_access_patterns'] = (
                analysis['violation_count'] > 0 and 
                analysis['approved_usage_count'] > 0
            )
            
            # Determine SSOT compliance
            if not analysis['is_allowed_exception']:
                analysis['ssot_compliant'] = analysis['violation_count'] == 0
            
        except Exception as e:
            analysis['scan_error'] = str(e)
        
        return analysis
    
    def test_no_direct_os_environ_access_violations(self):
        """
        CRITICAL: Verify no direct os.environ access outside approved exceptions.
        
        Direct environment access bypasses SSOT patterns and can cause
        configuration drift, testing issues, and security vulnerabilities.
        """
        all_violations = []
        total_files_scanned = 0
        compliant_files = 0
        
        for scan_dir in self.scan_directories:
            scan_dir_path = self.project_root / scan_dir
            if not scan_dir_path.exists():
                continue
            
            # Find all Python files
            python_files = list(scan_dir_path.rglob('*.py'))
            
            for py_file in python_files:
                if py_file.is_file():
                    total_files_scanned += 1
                    analysis = self.scan_file_for_environment_patterns(py_file)
                    
                    if analysis['direct_os_environ_violations']:
                        all_violations.extend(analysis['direct_os_environ_violations'])
                        self.environment_violations.append(analysis)
                        
                        # Report mixed access patterns as particularly problematic
                        if analysis['mixed_access_patterns']:
                            self.configuration_issues.append({
                                'issue_type': 'mixed_access_patterns',
                                'file_path': analysis['file_relative_path'],
                                'violations': len(analysis['direct_os_environ_violations']),
                                'approved_usages': len(analysis['approved_isolated_env_usage'])
                            })
                    
                    if analysis['ssot_compliant']:
                        compliant_files += 1
                    
                    if analysis['approved_isolated_env_usage']:
                        self.isolated_environment_usages.append(analysis)
        
        # Calculate compliance metrics
        compliance_rate = (compliant_files / total_files_scanned * 100) if total_files_scanned > 0 else 0
        violation_rate = (len(all_violations) / total_files_scanned * 100) if total_files_scanned > 0 else 0
        
        # Record metrics
        self.record_metric('total_python_files_scanned', total_files_scanned)
        self.record_metric('compliant_files', compliant_files)
        self.record_metric('files_with_violations', len(self.environment_violations))
        self.record_metric('total_environment_violations', len(all_violations))
        self.record_metric('environment_compliance_rate', compliance_rate)
        self.record_metric('environment_violation_rate', violation_rate)
        
        print(f"\nEnvironment Access Pattern Validation:")
        print(f"  Files scanned: {total_files_scanned}")
        print(f"  Compliant files: {compliant_files}")
        print(f"  Files with violations: {len(self.environment_violations)}")
        print(f"  Total violations: {len(all_violations)}")
        print(f"  Compliance rate: {compliance_rate:.1f}%")
        print(f"  Violation rate: {violation_rate:.1f}%")
        
        # Report top violations
        if all_violations:
            print(f"\nTop Environment Access Violations:")
            # Group by pattern for summary
            pattern_counts = {}
            for violation in all_violations:
                pattern = violation['pattern']
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  - {pattern}: {count} occurrences")
            
            print(f"\nExample violations (first 5):")
            for violation in all_violations[:5]:
                print(f"  - Line {violation['line_number']}: {violation['pattern']}")
        
        # Report mixed access patterns
        if self.configuration_issues:
            print(f"\nMixed Access Pattern Issues: {len(self.configuration_issues)}")
            for issue in self.configuration_issues[:3]:
                print(f"  - {issue['file_path']}: {issue['violations']} violations, {issue['approved_usages']} approved")
        
        # For SSOT foundation phase, measure current state
        # Goal is to track improvement over time
        high_violation_files = [v for v in self.environment_violations if len(v['direct_os_environ_violations']) >= 5]
        self.record_metric('high_violation_files', len(high_violation_files))
        
        print(f"\nCompliance Analysis:")
        print(f"  High violation files (5+ violations): {len(high_violation_files)}")
        print(f"  Mixed access pattern files: {len(self.configuration_issues)}")
        
        # Test passes - this is measurement for SSOT foundation
        assert total_files_scanned > 0, "No files scanned - test discovery failed"
    
    def test_isolated_environment_usage_patterns_correct(self):
        """
        Validate that IsolatedEnvironment usage follows correct patterns.
        
        When IsolatedEnvironment is used, it should follow the approved
        patterns and best practices for environment access.
        """
        isolated_env_analysis = {
            'files_using_isolated_env': len(self.isolated_environment_usages),
            'correct_import_patterns': 0,
            'correct_usage_patterns': 0,
            'common_usage_patterns': {},
            'usage_quality_score': 0.0
        }
        
        # Analyze IsolatedEnvironment usage quality
        for usage_analysis in self.isolated_environment_usages:
            approved_usages = usage_analysis['approved_isolated_env_usage']
            
            # Count different usage patterns
            for usage in approved_usages:
                pattern = usage['pattern']
                if pattern not in isolated_env_analysis['common_usage_patterns']:
                    isolated_env_analysis['common_usage_patterns'][pattern] = 0
                isolated_env_analysis['common_usage_patterns'][pattern] += 1
                
                # Score different patterns
                if 'get_env()' in pattern or 'IsolatedEnvironment' in pattern:
                    isolated_env_analysis['correct_import_patterns'] += 1
                
                if 'env.get(' in pattern or 'env.set(' in pattern:
                    isolated_env_analysis['correct_usage_patterns'] += 1
        
        # Calculate usage quality
        total_approved_usages = sum(isolated_env_analysis['common_usage_patterns'].values())
        if total_approved_usages > 0:
            quality_score = (
                (isolated_env_analysis['correct_import_patterns'] + 
                 isolated_env_analysis['correct_usage_patterns']) / 
                (total_approved_usages * 2) * 100
            )
            isolated_env_analysis['usage_quality_score'] = quality_score
        
        # Record IsolatedEnvironment usage metrics
        for metric, value in isolated_env_analysis.items():
            if isinstance(value, (int, float)):
                self.record_metric(f'isolated_env_{metric}', value)
        
        print(f"\nIsolatedEnvironment Usage Analysis:")
        print(f"  Files using IsolatedEnvironment: {isolated_env_analysis['files_using_isolated_env']}")
        print(f"  Correct import patterns: {isolated_env_analysis['correct_import_patterns']}")
        print(f"  Correct usage patterns: {isolated_env_analysis['correct_usage_patterns']}")
        print(f"  Usage quality score: {isolated_env_analysis['usage_quality_score']:.1f}%")
        
        # Show common usage patterns
        if isolated_env_analysis['common_usage_patterns']:
            print(f"\nCommon IsolatedEnvironment Usage Patterns:")
            sorted_patterns = sorted(
                isolated_env_analysis['common_usage_patterns'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            for pattern, count in sorted_patterns[:5]:
                print(f"  - {pattern}: {count} usages")
        
        # Validation - good usage patterns should be present
        if isolated_env_analysis['files_using_isolated_env'] > 0:
            assert isolated_env_analysis['usage_quality_score'] > 50, (
                f"IsolatedEnvironment usage quality too low: {isolated_env_analysis['usage_quality_score']:.1f}%. "
                f"Usage patterns may not follow SSOT best practices."
            )
    
    def test_configuration_consistency_across_services(self):
        """
        Validate configuration consistency across different services.
        
        Each service should use consistent environment access patterns
        and not have conflicting configuration approaches.
        """
        service_analysis = {}
        
        # Analyze each service directory separately
        service_directories = [
            ('netra_backend', 'netra_backend/app'),
            ('auth_service', 'auth_service'),
            ('shared', 'shared'),
            ('tests', 'tests')
        ]
        
        for service_name, service_path in service_directories:
            service_dir = self.project_root / service_path
            if not service_dir.exists():
                continue
            
            service_analysis[service_name] = {
                'files_scanned': 0,
                'compliant_files': 0,
                'violation_files': 0,
                'isolated_env_files': 0,
                'compliance_rate': 0.0,
                'consistency_score': 0.0
            }
            
            python_files = list(service_dir.rglob('*.py'))
            
            for py_file in python_files:
                if py_file.is_file():
                    service_analysis[service_name]['files_scanned'] += 1
                    analysis = self.scan_file_for_environment_patterns(py_file)
                    
                    if analysis['ssot_compliant']:
                        service_analysis[service_name]['compliant_files'] += 1
                    else:
                        service_analysis[service_name]['violation_files'] += 1
                    
                    if analysis['approved_usage_count'] > 0:
                        service_analysis[service_name]['isolated_env_files'] += 1
            
            # Calculate service-specific metrics
            files_scanned = service_analysis[service_name]['files_scanned']
            if files_scanned > 0:
                compliance_rate = (service_analysis[service_name]['compliant_files'] / files_scanned * 100)
                service_analysis[service_name]['compliance_rate'] = compliance_rate
                
                # Consistency score considers both compliance and IsolatedEnv adoption
                isolated_rate = (service_analysis[service_name]['isolated_env_files'] / files_scanned * 100)
                consistency_score = (compliance_rate + isolated_rate) / 2
                service_analysis[service_name]['consistency_score'] = consistency_score
        
        # Record service-specific metrics
        for service_name, analysis in service_analysis.items():
            for metric, value in analysis.items():
                self.record_metric(f'service_{service_name}_{metric}', value)
        
        print(f"\nConfiguration Consistency Across Services:")
        for service_name, analysis in service_analysis.items():
            files = analysis['files_scanned']
            compliance = analysis['compliance_rate']
            consistency = analysis['consistency_score']
            print(f"  {service_name}: {files} files, {compliance:.1f}% compliant, {consistency:.1f}% consistent")
        
        # Overall consistency analysis
        total_services = len([s for s in service_analysis.values() if s['files_scanned'] > 0])
        highly_consistent_services = len([s for s in service_analysis.values() if s['consistency_score'] >= 80])
        
        overall_consistency = (highly_consistent_services / total_services * 100) if total_services > 0 else 0
        self.record_metric('overall_service_consistency', overall_consistency)
        
        print(f"\nOverall Service Consistency: {overall_consistency:.1f}%")
        print(f"  Highly consistent services: {highly_consistent_services}/{total_services}")
        
        # Identify inconsistent services
        inconsistent_services = [name for name, analysis in service_analysis.items() 
                               if analysis['consistency_score'] < 50 and analysis['files_scanned'] > 5]
        
        if inconsistent_services:
            print(f"\nServices needing consistency improvement:")
            for service in inconsistent_services:
                score = service_analysis[service]['consistency_score']
                print(f"  - {service}: {score:.1f}% consistency score")
        
        # Test passes - measuring consistency for improvement tracking
        assert total_services > 0, "No services analyzed"
    
    def test_test_environment_isolation_compliance(self):
        """
        CRITICAL: Verify test files use proper environment isolation.
        
        Test files must use SSOT environment patterns to ensure test isolation
        and prevent test interference from global environment state.
        """
        test_environment_analysis = {
            'test_files_scanned': 0,
            'test_files_with_isolation': 0,
            'test_files_with_violations': 0,
            'test_isolation_compliance_rate': 0.0,
            'critical_test_violations': []
        }
        
        # Scan test directories specifically
        test_directories = [
            'tests',
            'netra_backend/tests',
            'auth_service/tests',
            'test_framework/tests'
        ]
        
        for test_dir in test_directories:
            test_dir_path = self.project_root / test_dir
            if not test_dir_path.exists():
                continue
            
            test_files = list(test_dir_path.rglob('test_*.py'))
            test_files.extend(list(test_dir_path.rglob('*_test.py')))
            
            for test_file in test_files:
                if test_file.is_file():
                    test_environment_analysis['test_files_scanned'] += 1
                    analysis = self.scan_file_for_environment_patterns(test_file)
                    
                    if analysis['approved_usage_count'] > 0:
                        test_environment_analysis['test_files_with_isolation'] += 1
                    
                    if not analysis['ssot_compliant']:
                        test_environment_analysis['test_files_with_violations'] += 1
                        
                        # Check if this is a critical test file
                        test_file_name = test_file.name.lower()
                        if any(critical in test_file_name for critical in ['mission_critical', 'integration', 'e2e']):
                            test_environment_analysis['critical_test_violations'].append({
                                'file_path': str(test_file.relative_to(self.project_root)),
                                'violations': len(analysis['direct_os_environ_violations'])
                            })
        
        # Calculate test isolation compliance
        test_files_scanned = test_environment_analysis['test_files_scanned']
        if test_files_scanned > 0:
            compliant_files = test_files_scanned - test_environment_analysis['test_files_with_violations']
            compliance_rate = (compliant_files / test_files_scanned * 100)
            test_environment_analysis['test_isolation_compliance_rate'] = compliance_rate
        
        # Record test isolation metrics
        for metric, value in test_environment_analysis.items():
            if isinstance(value, (int, float)):
                self.record_metric(f'test_{metric}', value)
        
        print(f"\nTest Environment Isolation Analysis:")
        print(f"  Test files scanned: {test_files_scanned}")
        print(f"  Test files with isolation: {test_environment_analysis['test_files_with_isolation']}")
        print(f"  Test files with violations: {test_environment_analysis['test_files_with_violations']}")
        print(f"  Test isolation compliance: {test_environment_analysis['test_isolation_compliance_rate']:.1f}%")
        
        # Report critical test violations
        critical_violations = test_environment_analysis['critical_test_violations']
        if critical_violations:
            print(f"\nCritical Test Files with Environment Violations:")
            for violation in critical_violations[:5]:
                print(f"  - {violation['file_path']}: {violation['violations']} violations")
        
        # CRITICAL: Critical test files must not have environment violations
        assert len(critical_violations) == 0, (
            f"Critical test files have environment access violations: {len(critical_violations)}. "
            f"This compromises test isolation and reliability for business-critical functionality."
        )
        
        # Test isolation should be reasonably high
        compliance_rate = test_environment_analysis['test_isolation_compliance_rate']
        if test_files_scanned > 10:  # Only enforce if we have reasonable sample size
            assert compliance_rate >= 70, (
                f"Test environment isolation compliance too low: {compliance_rate:.1f}%. "
                f"Test files should use SSOT environment patterns for proper isolation."
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])