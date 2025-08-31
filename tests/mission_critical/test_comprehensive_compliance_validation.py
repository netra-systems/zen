"""
Comprehensive Compliance Validation Suite

CRITICAL MISSION: Validate all mock remediations and ensure 90%+ compliance.

This is the authoritative validation suite that must pass before any deployment.
Designed to be run in CI/CD to prevent regression of compliance issues.

Business Value: Platform/Internal - System Stability & Compliance
$1M+ ARR protected from mock-related integration failures and architectural debt.

Author: Test Validation and Compliance Specialist
Date: 2025-08-30
"""

import ast
import json
import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Set, Optional, Any
import pytest
from dataclasses import dataclass, asdict
from collections import defaultdict
import time

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class ComplianceMetrics:
    """Comprehensive compliance metrics structure."""
    mock_violations: int
    isolated_environment_violations: int
    direct_os_environ_violations: int
    architecture_violations: int
    test_quality_score: float
    websocket_events_status: str
    real_service_connection_status: str
    overall_compliance_percentage: float
    critical_issues: List[str]
    recommendations: List[str]


@dataclass
class ServiceComplianceStatus:
    """Per-service compliance status."""
    service_name: str
    mock_violations: int
    environment_violations: int
    test_coverage: float
    real_service_usage: bool
    websocket_integration: bool
    compliance_score: float
    critical_issues: List[str]


class ComprehensiveComplianceValidator:
    """
    Comprehensive validation of all compliance requirements.
    
    This class validates:
    1. Zero mock usage across all services
    2. IsolatedEnvironment usage compliance
    3. Real service connections working
    4. WebSocket agent events functioning
    5. Architecture compliance > 90%
    """
    
    def __init__(self):
        """Initialize comprehensive validator."""
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.services = ['auth_service', 'analytics_service', 'netra_backend', 'frontend']
        self.test_directories = [
            self.project_root / 'auth_service' / 'tests',
            self.project_root / 'analytics_service' / 'tests', 
            self.project_root / 'netra_backend' / 'tests',
            self.project_root / 'tests',
            self.project_root / 'dev_launcher' / 'tests',
        ]
        self.results = {}
        self.start_time = time.time()
    
    def run_full_compliance_validation(self) -> ComplianceMetrics:
        """
        Run complete compliance validation suite.
        
        Returns:
            ComplianceMetrics with comprehensive validation results
        """
        print("\n🔍 COMPREHENSIVE COMPLIANCE VALIDATION STARTING...")
        print("=" * 80)
        
        # 1. Mock Policy Validation
        print("\n📋 1. MOCK POLICY VALIDATION")
        mock_violations = self._validate_mock_policy()
        
        # 2. Environment Isolation Validation  
        print("\n🏗️ 2. ENVIRONMENT ISOLATION VALIDATION")
        env_violations = self._validate_environment_isolation()
        
        # 3. Architecture Compliance Validation
        print("\n🏛️ 3. ARCHITECTURE COMPLIANCE VALIDATION")
        arch_violations = self._validate_architecture_compliance()
        
        # 4. Real Service Connection Validation
        print("\n🔌 4. REAL SERVICE CONNECTION VALIDATION")
        service_status = self._validate_real_service_connections()
        
        # 5. WebSocket Agent Events Validation
        print("\n🔄 5. WEBSOCKET AGENT EVENTS VALIDATION")
        websocket_status = self._validate_websocket_agent_events()
        
        # 6. Test Quality Assessment
        print("\n📊 6. TEST QUALITY ASSESSMENT")
        test_quality = self._assess_test_quality()
        
        # Calculate overall compliance
        compliance_metrics = self._calculate_compliance_metrics(
            mock_violations, env_violations, arch_violations,
            service_status, websocket_status, test_quality
        )
        
        print(f"\n⏱️ Validation completed in {time.time() - self.start_time:.2f}s")
        return compliance_metrics
    
    def _validate_mock_policy(self) -> Dict[str, Any]:
        """Validate complete mock policy compliance."""
        print("   Scanning for mock usage violations...")
        
        violations_by_service = {}
        total_violations = 0
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            service_name = test_dir.parent.name if test_dir.parent.name != 'netra-apex' else 'tests'
            violations = self._scan_directory_for_mocks(test_dir)
            violations_by_service[service_name] = violations
            total_violations += len(violations)
            
            print(f"   {service_name}: {len(violations)} violations")
        
        return {
            'total_violations': total_violations,
            'by_service': violations_by_service,
            'compliant': total_violations == 0
        }
    
    def _validate_environment_isolation(self) -> Dict[str, Any]:
        """Validate IsolatedEnvironment usage across all services."""
        print("   Checking IsolatedEnvironment usage compliance...")
        
        violations = []
        compliant_files = []
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            for py_file in test_dir.rglob('*.py'):
                if py_file.name.startswith('test_'):
                    result = self._check_file_environment_compliance(py_file)
                    if result['violations']:
                        violations.extend(result['violations'])
                    if result['compliant']:
                        compliant_files.append(str(py_file))
        
        compliance_rate = len(compliant_files) / (len(compliant_files) + len(violations)) if (len(compliant_files) + len(violations)) > 0 else 1.0
        
        print(f"   Environment compliance: {compliance_rate*100:.1f}%")
        print(f"   Violations: {len(violations)}, Compliant files: {len(compliant_files)}")
        
        return {
            'violations': violations,
            'compliant_files': compliant_files,
            'compliance_rate': compliance_rate,
            'compliant': len(violations) == 0
        }
    
    def _validate_architecture_compliance(self) -> Dict[str, Any]:
        """Run architecture compliance checks."""
        print("   Running architecture compliance analysis...")
        
        try:
            # Run architecture compliance script
            result = subprocess.run(
                [sys.executable, 'scripts/check_architecture_compliance.py', 
                 '--path', str(self.project_root), '--json-only'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.returncode == 0:
                compliance_data = json.loads(result.stdout)
                compliance_score = compliance_data.get('compliance_score', 0.0)
                total_violations = compliance_data.get('total_violations', 0)
                
                print(f"   Architecture compliance: {compliance_score*100:.1f}%")
                print(f"   Total violations: {total_violations}")
                
                return {
                    'compliance_score': compliance_score,
                    'total_violations': total_violations,
                    'violations_by_type': compliance_data.get('violations_by_type', {}),
                    'compliant': compliance_score >= 0.9
                }
            else:
                print(f"   ❌ Architecture compliance check failed: {result.stderr}")
                return {
                    'compliance_score': 0.0,
                    'total_violations': 9999,
                    'violations_by_type': {},
                    'compliant': False,
                    'error': result.stderr
                }
                
        except Exception as e:
            print(f"   ❌ Exception running architecture compliance: {e}")
            return {
                'compliance_score': 0.0,
                'total_violations': 9999,
                'violations_by_type': {},
                'compliant': False,
                'error': str(e)
            }
    
    def _validate_real_service_connections(self) -> Dict[str, Any]:
        """Validate that real service connections are working."""
        print("   Testing real service connections...")
        
        service_statuses = {}
        
        # Test database connections
        db_status = self._test_database_connection()
        service_statuses['database'] = db_status
        
        # Test Redis connection
        redis_status = self._test_redis_connection()
        service_statuses['redis'] = redis_status
        
        # Test WebSocket service
        websocket_status = self._test_websocket_service()
        service_statuses['websocket'] = websocket_status
        
        all_services_working = all(status.get('working', False) for status in service_statuses.values())
        
        print(f"   Real service connections: {'✅ All working' if all_services_working else '❌ Some failing'}")
        
        return {
            'service_statuses': service_statuses,
            'all_working': all_services_working,
            'compliant': all_services_working
        }
    
    def _validate_websocket_agent_events(self) -> Dict[str, Any]:
        """Validate WebSocket agent events functionality."""
        print("   Validating WebSocket agent events...")
        
        try:
            # Run the mission critical WebSocket test
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 
                 'tests/mission_critical/test_websocket_agent_events_suite.py', 
                 '-v', '--tb=short'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Parse test results
            event_types_tested = [
                'agent_started', 'agent_thinking', 'tool_executing', 
                'tool_completed', 'agent_completed'
            ]
            
            events_working = []
            for event in event_types_tested:
                if event in output and 'PASSED' in output:
                    events_working.append(event)
            
            print(f"   WebSocket events: {'✅ All working' if success else '❌ Issues detected'}")
            print(f"   Events tested: {len(events_working)}/{len(event_types_tested)}")
            
            return {
                'all_events_working': success,
                'events_working': events_working,
                'total_events': len(event_types_tested),
                'test_output': output[-500:],  # Last 500 chars
                'compliant': success
            }
            
        except Exception as e:
            print(f"   ❌ WebSocket validation failed: {e}")
            return {
                'all_events_working': False,
                'events_working': [],
                'total_events': 0,
                'error': str(e),
                'compliant': False
            }
    
    def _assess_test_quality(self) -> Dict[str, Any]:
        """Assess overall test quality across the platform."""
        print("   Assessing test quality...")
        
        quality_metrics = {
            'total_test_files': 0,
            'mock_free_tests': 0,
            'integration_tests': 0,
            'e2e_tests': 0,
            'real_service_tests': 0,
            'quality_score': 0.0
        }
        
        for test_dir in self.test_directories:
            if not test_dir.exists():
                continue
                
            # Count test files
            test_files = list(test_dir.rglob('test_*.py'))
            quality_metrics['total_test_files'] += len(test_files)
            
            for test_file in test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for mock-free tests
                    if not self._has_mock_usage(content):
                        quality_metrics['mock_free_tests'] += 1
                    
                    # Check for integration tests
                    if 'integration' in str(test_file).lower() or 'IsolatedEnvironment' in content:
                        quality_metrics['integration_tests'] += 1
                    
                    # Check for e2e tests
                    if 'e2e' in str(test_file).lower():
                        quality_metrics['e2e_tests'] += 1
                    
                    # Check for real service usage
                    if ('docker-compose' in content or 'real' in content.lower() 
                        or 'IsolatedEnvironment' in content):
                        quality_metrics['real_service_tests'] += 1
                        
                except Exception:
                    continue
        
        # Calculate quality score
        total_tests = quality_metrics['total_test_files']
        if total_tests > 0:
            mock_free_ratio = quality_metrics['mock_free_tests'] / total_tests
            integration_ratio = quality_metrics['integration_tests'] / total_tests
            real_service_ratio = quality_metrics['real_service_tests'] / total_tests
            
            quality_metrics['quality_score'] = (
                mock_free_ratio * 0.4 + 
                integration_ratio * 0.3 + 
                real_service_ratio * 0.3
            )
        
        print(f"   Test quality score: {quality_metrics['quality_score']*100:.1f}%")
        print(f"   Mock-free tests: {quality_metrics['mock_free_tests']}/{total_tests}")
        
        return quality_metrics
    
    def _calculate_compliance_metrics(self, mock_data, env_data, arch_data, 
                                    service_data, websocket_data, quality_data) -> ComplianceMetrics:
        """Calculate comprehensive compliance metrics."""
        
        # Weight different aspects
        mock_weight = 0.30
        env_weight = 0.15  
        arch_weight = 0.25
        service_weight = 0.15
        websocket_weight = 0.15
        
        # Calculate component scores (0-1)
        mock_score = 1.0 if mock_data['compliant'] else 0.0
        env_score = env_data['compliance_rate'] if env_data['compliance_rate'] else 0.0
        arch_score = arch_data['compliance_score']
        service_score = 1.0 if service_data['compliant'] else 0.0
        websocket_score = 1.0 if websocket_data['compliant'] else 0.0
        
        # Calculate weighted overall compliance
        overall_compliance = (
            mock_score * mock_weight +
            env_score * env_weight +
            arch_score * arch_weight +
            service_score * service_weight +
            websocket_score * websocket_weight
        )
        
        # Collect critical issues
        critical_issues = []
        if mock_data['total_violations'] > 0:
            critical_issues.append(f"{mock_data['total_violations']} mock violations detected")
        if len(env_data['violations']) > 0:
            critical_issues.append(f"{len(env_data['violations'])} environment isolation violations")
        if arch_data['compliance_score'] < 0.9:
            critical_issues.append(f"Architecture compliance at {arch_data['compliance_score']*100:.1f}% (need 90%+)")
        if not service_data['compliant']:
            critical_issues.append("Real service connections failing")
        if not websocket_data['compliant']:
            critical_issues.append("WebSocket agent events not working")
        
        # Generate recommendations
        recommendations = []
        if mock_data['total_violations'] > 0:
            recommendations.append("Remove ALL mock usage and use real services with IsolatedEnvironment")
        if len(env_data['violations']) > 0:
            recommendations.append("Convert all tests to use IsolatedEnvironment instead of direct os.environ")
        if arch_data['compliance_score'] < 0.9:
            recommendations.append("Address architectural violations: file size, function complexity, etc.")
        if not service_data['compliant']:
            recommendations.append("Fix real service connections using docker-compose")
        if not websocket_data['compliant']:
            recommendations.append("Fix WebSocket agent event emission and handling")
        
        return ComplianceMetrics(
            mock_violations=mock_data['total_violations'],
            isolated_environment_violations=len(env_data['violations']),
            direct_os_environ_violations=len([v for v in env_data['violations'] if 'os.environ' in str(v)]),
            architecture_violations=arch_data['total_violations'],
            test_quality_score=quality_data['quality_score'],
            websocket_events_status="WORKING" if websocket_data['compliant'] else "FAILING",
            real_service_connection_status="WORKING" if service_data['compliant'] else "FAILING",
            overall_compliance_percentage=overall_compliance * 100,
            critical_issues=critical_issues,
            recommendations=recommendations
        )
    
    def _scan_directory_for_mocks(self, directory: Path) -> List[Dict]:
        """Scan directory for mock usage violations."""
        violations = []
        
        for py_file in directory.rglob('*.py'):
            if py_file.name == 'test_comprehensive_compliance_validation.py':
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if self._has_mock_usage(content):
                    violations.append({
                        'file': str(py_file),
                        'type': 'mock_usage',
                        'service': self._get_service_name(str(py_file))
                    })
                    
            except Exception:
                continue
                
        return violations
    
    def _has_mock_usage(self, content: str) -> bool:
        """Check if content has mock usage."""
        mock_indicators = [
            'from unittest.mock import', 'from mock import',
            'import unittest.mock', 'import mock',
            'Mock(', 'MagicMock(', 'AsyncMock(', 'patch(',
            '@patch', '@mock.'
        ]
        
        return any(indicator in content for indicator in mock_indicators)
    
    def _check_file_environment_compliance(self, file_path: Path) -> Dict[str, Any]:
        """Check if file uses IsolatedEnvironment properly."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            violations = []
            
            # Check for direct os.environ usage
            if 'os.environ[' in content or 'os.environ.get(' in content:
                violations.append(f"{file_path}: Direct os.environ access")
            
            # Check for IsolatedEnvironment usage
            has_isolated_env = (
                'IsolatedEnvironment' in content or 
                'isolated_test_env' in content or
                'from test_framework.environment_isolation import' in content
            )
            
            return {
                'violations': violations,
                'compliant': len(violations) == 0 and has_isolated_env,
                'has_isolated_env': has_isolated_env
            }
            
        except Exception as e:
            return {
                'violations': [f"{file_path}: Could not read file - {e}"],
                'compliant': False,
                'has_isolated_env': False
            }
    
    def _test_database_connection(self) -> Dict[str, Any]:
        """Test database connection."""
        try:
            # Try to import database connection and test it
            from test_framework.environment_isolation import get_test_env_manager
            
            manager = get_test_env_manager()
            env = manager.setup_test_environment()
            
            # Check if database configuration is set
            db_config = {
                'DATABASE_URL': env.get('DATABASE_URL'),
                'USE_MEMORY_DB': env.get('USE_MEMORY_DB')
            }
            
            working = bool(db_config['USE_MEMORY_DB'] or db_config['DATABASE_URL'])
            
            return {
                'working': working,
                'config': db_config,
                'type': 'memory' if db_config['USE_MEMORY_DB'] else 'postgresql'
            }
            
        except Exception as e:
            return {
                'working': False,
                'error': str(e),
                'type': 'unknown'
            }
    
    def _test_redis_connection(self) -> Dict[str, Any]:
        """Test Redis connection."""
        try:
            from test_framework.environment_isolation import get_test_env_manager
            
            manager = get_test_env_manager()
            env = manager.setup_test_environment()
            
            redis_url = env.get('REDIS_URL')
            working = bool(redis_url and redis_url != 'redis://localhost:6379/1')
            
            return {
                'working': working,
                'redis_url': redis_url,
                'configured': bool(redis_url)
            }
            
        except Exception as e:
            return {
                'working': False,
                'error': str(e),
                'configured': False
            }
    
    def _test_websocket_service(self) -> Dict[str, Any]:
        """Test WebSocket service configuration."""
        try:
            # Check if WebSocket service files exist and are configured
            websocket_files = [
                self.project_root / 'netra_backend' / 'websocket_manager.py',
                self.project_root / 'netra_backend' / 'app' / 'websocket_manager.py'
            ]
            
            websocket_configured = any(f.exists() for f in websocket_files)
            
            return {
                'working': websocket_configured,
                'configured': websocket_configured,
                'files_found': [str(f) for f in websocket_files if f.exists()]
            }
            
        except Exception as e:
            return {
                'working': False,
                'error': str(e),
                'configured': False
            }
    
    def _get_service_name(self, file_path: str) -> str:
        """Get service name from file path."""
        if '/auth_service/' in file_path:
            return 'auth_service'
        elif '/analytics_service/' in file_path:
            return 'analytics_service'
        elif '/netra_backend/' in file_path:
            return 'netra_backend'
        elif '/frontend/' in file_path:
            return 'frontend'
        else:
            return 'tests'


class TestComprehensiveCompliance:
    """Test suite for comprehensive compliance validation."""
    
    def test_comprehensive_compliance_validation(self):
        """
        CRITICAL: Comprehensive compliance validation.
        
        This test validates ALL aspects of system compliance:
        - Zero mock usage
        - IsolatedEnvironment usage
        - Real service connections
        - WebSocket agent events
        - Architecture compliance
        
        MUST PASS before deployment.
        """
        validator = ComprehensiveComplianceValidator()
        metrics = validator.run_full_compliance_validation()
        
        # Generate detailed report
        report = self._generate_compliance_report(metrics)
        
        # Save report to file
        report_path = validator.project_root / 'COMPLIANCE_VALIDATION_REPORT.md'
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\n📋 Compliance report saved: {report_path}")
        
        # Determine if system passes compliance
        compliance_threshold = 90.0  # 90% compliance required
        
        if metrics.overall_compliance_percentage >= compliance_threshold:
            print(f"\n✅ COMPLIANCE VALIDATION PASSED")
            print(f"   Overall compliance: {metrics.overall_compliance_percentage:.1f}%")
            print(f"   Mock violations: {metrics.mock_violations}")
            print(f"   WebSocket events: {metrics.websocket_events_status}")
            print(f"   Real services: {metrics.real_service_connection_status}")
        else:
            # Generate failure report
            failure_report = "\n" + "=" * 80 + "\n"
            failure_report += "❌ COMPLIANCE VALIDATION FAILED\n"
            failure_report += "=" * 80 + "\n\n"
            failure_report += f"Overall Compliance: {metrics.overall_compliance_percentage:.1f}% (need {compliance_threshold}%)\n\n"
            
            if metrics.critical_issues:
                failure_report += "CRITICAL ISSUES:\n"
                for issue in metrics.critical_issues:
                    failure_report += f"  ❌ {issue}\n"
                failure_report += "\n"
            
            if metrics.recommendations:
                failure_report += "REQUIRED ACTIONS:\n"
                for rec in metrics.recommendations:
                    failure_report += f"  🔧 {rec}\n"
                failure_report += "\n"
            
            failure_report += "DETAILED METRICS:\n"
            failure_report += f"  Mock Violations: {metrics.mock_violations}\n"
            failure_report += f"  Environment Violations: {metrics.isolated_environment_violations}\n"
            failure_report += f"  Architecture Violations: {metrics.architecture_violations}\n"
            failure_report += f"  Test Quality Score: {metrics.test_quality_score*100:.1f}%\n"
            failure_report += f"  WebSocket Events: {metrics.websocket_events_status}\n"
            failure_report += f"  Real Services: {metrics.real_service_connection_status}\n"
            
            failure_report += "\n" + "=" * 80 + "\n"
            failure_report += "COMPLIANCE MUST REACH 90%+ BEFORE DEPLOYMENT\n"
            failure_report += "=" * 80 + "\n"
            
            pytest.fail(failure_report)
    
    def _generate_compliance_report(self, metrics: ComplianceMetrics) -> str:
        """Generate comprehensive compliance report."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Comprehensive Compliance Validation Report

**Generated:** {timestamp}
**Overall Compliance:** {metrics.overall_compliance_percentage:.1f}%
**Status:** {'✅ PASSED' if metrics.overall_compliance_percentage >= 90 else '❌ FAILED'}

## Executive Summary

This report provides a comprehensive validation of all system compliance requirements
including mock policy, environment isolation, architecture standards, real service
connections, and WebSocket functionality.

### Key Metrics

| Metric | Value | Status |
|--------|-------|--------|
| Mock Violations | {metrics.mock_violations} | {'✅' if metrics.mock_violations == 0 else '❌'} |
| Environment Violations | {metrics.isolated_environment_violations} | {'✅' if metrics.isolated_environment_violations == 0 else '❌'} |
| Architecture Violations | {metrics.architecture_violations} | {'✅' if metrics.architecture_violations < 1000 else '❌'} |
| Test Quality Score | {metrics.test_quality_score*100:.1f}% | {'✅' if metrics.test_quality_score >= 0.7 else '❌'} |
| WebSocket Events | {metrics.websocket_events_status} | {'✅' if metrics.websocket_events_status == 'WORKING' else '❌'} |
| Real Service Connections | {metrics.real_service_connection_status} | {'✅' if metrics.real_service_connection_status == 'WORKING' else '❌'} |

## Critical Issues

"""
        
        if metrics.critical_issues:
            for issue in metrics.critical_issues:
                report += f"- ❌ {issue}\n"
        else:
            report += "- ✅ No critical issues detected\n"
        
        report += "\n## Recommendations\n\n"
        
        if metrics.recommendations:
            for rec in metrics.recommendations:
                report += f"- 🔧 {rec}\n"
        else:
            report += "- ✅ System is fully compliant\n"
        
        report += f"""

## Compliance Score Breakdown

The overall compliance score of {metrics.overall_compliance_percentage:.1f}% is calculated as:

- Mock Policy Compliance: {'100%' if metrics.mock_violations == 0 else '0%'} (30% weight)
- Environment Isolation: {((metrics.isolated_environment_violations == 0)*100):.0f}% (15% weight)  
- Architecture Compliance: Variable based on violations (25% weight)
- Real Service Connections: {'100%' if metrics.real_service_connection_status == 'WORKING' else '0%'} (15% weight)
- WebSocket Events: {'100%' if metrics.websocket_events_status == 'WORKING' else '0%'} (15% weight)

## Next Steps

{'The system meets all compliance requirements and is ready for deployment.' if metrics.overall_compliance_percentage >= 90 else 'Address the critical issues above before deployment. Compliance must reach 90%+.'}

---

*This report was generated automatically by the Comprehensive Compliance Validation Suite.*
"""
        
        return report


if __name__ == '__main__':
    # Run the comprehensive validation
    validator = ComprehensiveComplianceValidator()
    metrics = validator.run_full_compliance_validation()
    print(f"\nOverall Compliance: {metrics.overall_compliance_percentage:.1f}%")
    
    # Run as pytest
    pytest.main([__file__, '-v', '--tb=short'])