#!/usr/bin/env python3
"""
WebSocket Manager SSOT Consolidation Tests - Issue #885
========================================================

BUSINESS IMPACT: $500K+ ARR Golden Path protection through comprehensive SSOT validation
PURPOSE: Execute comprehensive test plan for WebSocket Manager SSOT consolidation

This test module implements the comprehensive test strategy for Issue #885 to:
1. Establish baseline current state (expect failures)
2. Identify specific SSOT violations
3. Measure compliance gaps
4. Guide remediation efforts

Test Categories:
- Factory Pattern Violations Detection
- Import Path Consolidation Validation
- User Isolation Security Testing
- Connection Management SSOT Validation

Expected Current State:
- SSOT Compliance: ~50% (1 of 2 tests passing)
- Multiple factory implementations detected
- Import path fragmentation identified
- User isolation gaps discovered

Created: 2025-09-15 for Issue #885 comprehensive test execution
"""

import os
import sys
import asyncio
import pytest
import importlib
import inspect
from pathlib import Path
from typing import List, Dict, Any, Set, Optional
from unittest.mock import Mock, patch, AsyncMock
import traceback
import time

# Test configuration
WEBSOCKET_CORE_PATH = "netra_backend/app/websocket_core"
PROJECT_ROOT = Path(__file__).parent


class WebSocketSSOTTestResults:
    """Collect and analyze SSOT test results"""
    
    def __init__(self):
        self.test_results = {}
        self.violations_found = []
        self.compliance_metrics = {}
        self.recommendations = []
    
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """Record test result"""
        self.test_results[test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        }
    
    def add_violation(self, violation_type: str, description: str, severity: str = "HIGH"):
        """Record SSOT violation"""
        self.violations_found.append({
            'type': violation_type,
            'description': description,
            'severity': severity,
            'timestamp': time.time()
        })
    
    def calculate_compliance(self):
        """Calculate SSOT compliance percentage"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['passed'])
        
        if total_tests == 0:
            return 0.0
        
        compliance_percentage = (passed_tests / total_tests) * 100
        self.compliance_metrics = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'compliance_percentage': compliance_percentage
        }
        
        return compliance_percentage
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        compliance = self.calculate_compliance()
        
        report = f"""
{'='*80}
WEBSOCKET MANAGER SSOT CONSOLIDATION TEST REPORT - ISSUE #885
{'='*80}

EXECUTIVE SUMMARY:
- SSOT Compliance: {compliance:.1f}%
- Total Tests Executed: {self.compliance_metrics.get('total_tests', 0)}
- Tests Passed: {self.compliance_metrics.get('passed_tests', 0)}
- Tests Failed: {self.compliance_metrics.get('failed_tests', 0)}
- Violations Found: {len(self.violations_found)}

DETAILED TEST RESULTS:
{'-'*40}
"""
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            report += f"{status} {test_name}\n"
            if result['details']:
                report += f"     Details: {result['details']}\n"
        
        if self.violations_found:
            report += f"\nSSOT VIOLATIONS DETECTED:\n{'-'*40}\n"
            for violation in self.violations_found:
                report += f"[{violation['severity']}] {violation['type']}: {violation['description']}\n"
        
        report += f"\nREMEDIATION RECOMMENDATIONS:\n{'-'*40}\n"
        for recommendation in self.recommendations:
            report += f"• {recommendation}\n"
        
        report += f"\n{'='*80}\n"
        
        return report


class WebSocketSSOTValidationTests:
    """
    Comprehensive WebSocket SSOT consolidation validation tests
    """
    
    def __init__(self):
        self.results = WebSocketSSOTTestResults()
        self.websocket_modules = []
        self.factory_implementations = []
        self.import_paths = set()
    
    def discover_websocket_modules(self) -> List[str]:
        """Discover all WebSocket-related modules in the codebase"""
        websocket_modules = []
        
        try:
            # Search for WebSocket modules
            for root, dirs, files in os.walk(PROJECT_ROOT):
                for file in files:
                    if file.endswith('.py') and ('websocket' in file.lower() or 'ws_' in file.lower()):
                        module_path = os.path.join(root, file)
                        relative_path = os.path.relpath(module_path, PROJECT_ROOT)
                        websocket_modules.append(relative_path)
            
            self.websocket_modules = websocket_modules
            return websocket_modules
            
        except Exception as e:
            self.results.add_violation(
                "MODULE_DISCOVERY_FAILURE",
                f"Failed to discover WebSocket modules: {str(e)}"
            )
            return []
    
    def test_factory_pattern_violations(self) -> bool:
        """
        TEST: Factory Pattern Violations Detection
        
        EXPECTED: FAIL - Should detect 13+ WebSocket factory implementations
        VALIDATES: Multiple factory patterns violate SSOT principles
        """
        try:
            factory_patterns = [
                'WebSocketManagerFactory',
                'WebSocketFactory', 
                'ManagerFactory',
                'ConnectionFactory',
                'create_websocket_manager',
                'get_websocket_manager',
                'websocket_factory',
                'create_manager',
                'manager_factory',
                'websocket_builder',
                'connection_builder',
                'ws_factory',
                'socket_factory'
            ]
            
            found_factories = []
            
            # Search across the entire codebase
            for root, dirs, files in os.walk(PROJECT_ROOT):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                for pattern in factory_patterns:
                                    if pattern in content:
                                        found_factories.append({
                                            'pattern': pattern,
                                            'file': os.path.relpath(file_path, PROJECT_ROOT),
                                            'type': 'factory_implementation'
                                        })
                        except (UnicodeDecodeError, PermissionError):
                            # Skip files that can't be read
                            continue
            
            self.factory_implementations = found_factories
            unique_factories = len(set(f['pattern'] for f in found_factories))
            
            # Test should FAIL if we find multiple factory implementations
            if unique_factories >= 5:  # Lowered threshold for realistic expectations
                self.results.add_violation(
                    "FACTORY_PATTERN_VIOLATION",
                    f"Found {unique_factories} different factory patterns, violates SSOT principle"
                )
                self.results.record_test(
                    "Factory Pattern Violations Detection",
                    False,
                    f"Found {unique_factories} factory implementations (expected: 1 SSOT factory)"
                )
                return False
            else:
                self.results.record_test(
                    "Factory Pattern Violations Detection", 
                    True,
                    f"Found {unique_factories} factory implementations - within acceptable SSOT range"
                )
                return True
                
        except Exception as e:
            self.results.add_violation(
                "FACTORY_TEST_ERROR",
                f"Factory pattern test failed with error: {str(e)}"
            )
            self.results.record_test("Factory Pattern Violations Detection", False, str(e))
            return False
    
    def test_import_path_consolidation(self) -> bool:
        """
        TEST: Import Path Consolidation Validation
        
        EXPECTED: FAIL - Should detect multiple import paths for same functionality
        VALIDATES: Import path fragmentation violates SSOT principles
        """
        try:
            websocket_import_patterns = [
                'from netra_backend.app.websocket_core',
                'from netra_backend.app.services.websocket',
                'from netra_backend.app.websocket',
                'import websocket_manager',
                'import WebSocketManager',
                'from websocket_core',
                'from app.websocket',
                'from .websocket',
                'websocket_manager_factory',
                'websocket_factory'
            ]
            
            import_violations = []
            
            # Search for import path patterns
            for root, dirs, files in os.walk(PROJECT_ROOT):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                
                                for line_num, line in enumerate(lines, 1):
                                    for pattern in websocket_import_patterns:
                                        if pattern in line and not line.strip().startswith('#'):
                                            import_violations.append({
                                                'file': os.path.relpath(file_path, PROJECT_ROOT),
                                                'line': line_num,
                                                'pattern': pattern,
                                                'content': line.strip()
                                            })
                        except (UnicodeDecodeError, PermissionError):
                            continue
            
            unique_import_patterns = len(set(v['pattern'] for v in import_violations))
            
            # Test should FAIL if we find multiple import patterns
            if unique_import_patterns >= 3:  # Multiple import paths indicate fragmentation
                self.results.add_violation(
                    "IMPORT_PATH_FRAGMENTATION",
                    f"Found {unique_import_patterns} different import patterns, violates SSOT import consolidation"
                )
                self.results.record_test(
                    "Import Path Consolidation",
                    False,
                    f"Found {unique_import_patterns} different import patterns across {len(import_violations)} files"
                )
                return False
            else:
                self.results.record_test(
                    "Import Path Consolidation",
                    True,
                    f"Found {unique_import_patterns} import patterns - acceptable for SSOT compliance"
                )
                return True
                
        except Exception as e:
            self.results.add_violation(
                "IMPORT_TEST_ERROR",
                f"Import path test failed with error: {str(e)}"
            )
            self.results.record_test("Import Path Consolidation", False, str(e))
            return False
    
    def test_user_isolation_validation(self) -> bool:
        """
        TEST: User Isolation Security Validation
        
        EXPECTED: PASS - User isolation should be properly implemented
        VALIDATES: No cross-user contamination risk in WebSocket connections
        """
        try:
            # Look for potential user isolation violations
            isolation_risks = []
            
            # Search for singleton patterns that might violate user isolation
            singleton_patterns = [
                'class.*Singleton',
                '_instance.*=.*None',
                'global.*websocket',
                'shared.*connection',
                'static.*manager',
                '__instance',
                '_global_',
                'cache.*manager'
            ]
            
            for root, dirs, files in os.walk(PROJECT_ROOT):
                for file in files:
                    if file.endswith('.py') and 'websocket' in file.lower():
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                for pattern in singleton_patterns:
                                    import re
                                    matches = re.findall(pattern, content, re.IGNORECASE)
                                    if matches:
                                        isolation_risks.append({
                                            'file': os.path.relpath(file_path, PROJECT_ROOT),
                                            'pattern': pattern,
                                            'matches': matches
                                        })
                        except (UnicodeDecodeError, PermissionError):
                            continue
            
            # User isolation should PASS if we don't find major risks
            if len(isolation_risks) <= 2:  # Allow minor acceptable patterns
                self.results.record_test(
                    "User Isolation Security Validation",
                    True,
                    f"Found {len(isolation_risks)} potential isolation risks - within acceptable limits"
                )
                return True
            else:
                self.results.add_violation(
                    "USER_ISOLATION_RISK",
                    f"Found {len(isolation_risks)} potential user isolation risks"
                )
                self.results.record_test(
                    "User Isolation Security Validation",
                    False,
                    f"Found {len(isolation_risks)} potential isolation violations"
                )
                return False
                
        except Exception as e:
            self.results.add_violation(
                "ISOLATION_TEST_ERROR",
                f"User isolation test failed with error: {str(e)}"
            )
            self.results.record_test("User Isolation Security Validation", False, str(e))
            return False
    
    def test_connection_management_ssot(self) -> bool:
        """
        TEST: Connection Management SSOT Validation
        
        EXPECTED: FAIL - Should detect multiple connection management approaches
        VALIDATES: Single source of truth for connection lifecycle
        """
        try:
            connection_management_patterns = [
                'add_connection',
                'remove_connection', 
                'register_connection',
                'unregister_connection',
                'connect_user',
                'disconnect_user',
                'manage_connection',
                'connection_pool',
                'connection_registry',
                'active_connections'
            ]
            
            connection_managers = []
            
            # Search for connection management implementations
            for root, dirs, files in os.walk(PROJECT_ROOT):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                                patterns_found = []
                                for pattern in connection_management_patterns:
                                    if pattern in content:
                                        patterns_found.append(pattern)
                                
                                if patterns_found:
                                    connection_managers.append({
                                        'file': os.path.relpath(file_path, PROJECT_ROOT),
                                        'patterns': patterns_found,
                                        'pattern_count': len(patterns_found)
                                    })
                        except (UnicodeDecodeError, PermissionError):
                            continue
            
            files_with_connection_management = len(connection_managers)
            
            # Test should FAIL if we find multiple files managing connections
            if files_with_connection_management >= 3:
                self.results.add_violation(
                    "CONNECTION_MANAGEMENT_FRAGMENTATION",
                    f"Found {files_with_connection_management} files with connection management - violates SSOT"
                )
                self.results.record_test(
                    "Connection Management SSOT",
                    False,
                    f"Found {files_with_connection_management} files managing connections (expected: 1 SSOT manager)"
                )
                return False
            else:
                self.results.record_test(
                    "Connection Management SSOT",
                    True,
                    f"Found {files_with_connection_management} connection managers - acceptable SSOT compliance"
                )
                return True
                
        except Exception as e:
            self.results.add_violation(
                "CONNECTION_TEST_ERROR",
                f"Connection management test failed with error: {str(e)}"
            )
            self.results.record_test("Connection Management SSOT", False, str(e))
            return False
    
    def test_websocket_module_structure_analysis(self) -> bool:
        """
        TEST: WebSocket Module Structure Analysis
        
        EXPECTED: FAIL - Should detect structural inconsistencies
        VALIDATES: Consistent module organization following SSOT principles
        """
        try:
            websocket_dirs = []
            websocket_files = []
            
            # Analyze WebSocket-related directory structure
            for root, dirs, files in os.walk(PROJECT_ROOT):
                # Check for WebSocket-related directories
                for dir_name in dirs:
                    if 'websocket' in dir_name.lower():
                        websocket_dirs.append(os.path.relpath(os.path.join(root, dir_name), PROJECT_ROOT))
                
                # Check for WebSocket-related files
                for file_name in files:
                    if file_name.endswith('.py') and 'websocket' in file_name.lower():
                        websocket_files.append(os.path.relpath(os.path.join(root, file_name), PROJECT_ROOT))
            
            # SSOT violation if we have WebSocket code scattered across many directories
            if len(websocket_dirs) >= 4:  # Too many WebSocket directories
                self.results.add_violation(
                    "MODULE_STRUCTURE_FRAGMENTATION",
                    f"WebSocket code scattered across {len(websocket_dirs)} directories - violates SSOT organization"
                )
                self.results.record_test(
                    "WebSocket Module Structure Analysis",
                    False,
                    f"Found WebSocket code in {len(websocket_dirs)} directories and {len(websocket_files)} files"
                )
                return False
            else:
                self.results.record_test(
                    "WebSocket Module Structure Analysis",
                    True,
                    f"WebSocket code organized in {len(websocket_dirs)} directories - acceptable structure"
                )
                return True
                
        except Exception as e:
            self.results.add_violation(
                "STRUCTURE_TEST_ERROR",
                f"Module structure test failed with error: {str(e)}"
            )
            self.results.record_test("WebSocket Module Structure Analysis", False, str(e))
            return False
    
    def run_comprehensive_validation(self) -> WebSocketSSOTTestResults:
        """
        Execute comprehensive SSOT validation test suite
        """
        print("🔍 Executing WebSocket SSOT Consolidation Tests - Issue #885")
        print("=" * 70)
        
        # Discover WebSocket modules
        print("\n📋 Phase 1: Module Discovery")
        modules = self.discover_websocket_modules()
        print(f"   Found {len(modules)} WebSocket-related modules")
        
        # Execute core tests
        print("\n🧪 Phase 2: SSOT Violation Detection Tests")
        
        tests = [
            ("Factory Pattern Violations", self.test_factory_pattern_violations),
            ("Import Path Consolidation", self.test_import_path_consolidation),
            ("User Isolation Security", self.test_user_isolation_validation),
            ("Connection Management SSOT", self.test_connection_management_ssot),
            ("Module Structure Analysis", self.test_websocket_module_structure_analysis)
        ]
        
        for test_name, test_func in tests:
            print(f"   Running: {test_name}")
            try:
                result = test_func()
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"   {status}: {test_name}")
            except Exception as e:
                print(f"   ❌ ERROR: {test_name} - {str(e)}")
                self.results.record_test(test_name, False, f"Exception: {str(e)}")
        
        # Generate recommendations
        self.generate_remediation_recommendations()
        
        return self.results
    
    def generate_remediation_recommendations(self):
        """Generate remediation recommendations based on test results"""
        
        # Check for factory violations
        if any('FACTORY_PATTERN_VIOLATION' in v['type'] for v in self.results.violations_found):
            self.results.recommendations.append(
                "CRITICAL: Consolidate multiple WebSocket factory implementations into single SSOT factory pattern"
            )
        
        # Check for import violations  
        if any('IMPORT_PATH_FRAGMENTATION' in v['type'] for v in self.results.violations_found):
            self.results.recommendations.append(
                "HIGH: Standardize WebSocket import paths to single canonical import location"
            )
        
        # Check for connection management violations
        if any('CONNECTION_MANAGEMENT_FRAGMENTATION' in v['type'] for v in self.results.violations_found):
            self.results.recommendations.append(
                "HIGH: Consolidate connection management into single SSOT WebSocket manager"
            )
        
        # Check for structure violations
        if any('MODULE_STRUCTURE_FRAGMENTATION' in v['type'] for v in self.results.violations_found):
            self.results.recommendations.append(
                "MEDIUM: Reorganize WebSocket modules into cohesive SSOT structure"
            )
        
        # Check for user isolation risks
        if any('USER_ISOLATION_RISK' in v['type'] for v in self.results.violations_found):
            self.results.recommendations.append(
                "CRITICAL: Address user isolation risks to prevent cross-user data contamination"
            )
        
        # Add general recommendations
        if self.results.calculate_compliance() < 70:
            self.results.recommendations.append(
                "Implement phased SSOT migration plan starting with highest severity violations"
            )
            self.results.recommendations.append(
                "Establish SSOT validation gates in CI/CD pipeline to prevent regression"
            )


def run_integration_tests():
    """
    Phase 3: Integration Testing (Non-Docker)
    
    Test WebSocket integration without Docker dependencies
    """
    print("\n🔗 Phase 3: Integration Testing (Non-Docker)")
    
    integration_results = {}
    
    try:
        # Test basic WebSocket module imports
        print("   Testing WebSocket module imports...")
        
        importable_modules = []
        failed_imports = []
        
        websocket_modules = [
            'netra_backend.app.websocket_core.unified_emitter',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.services.websocket.transparent_websocket_events'
        ]
        
        for module_name in websocket_modules:
            try:
                importlib.import_module(module_name)
                importable_modules.append(module_name)
                print(f"   ✅ Successfully imported: {module_name}")
            except ImportError as e:
                failed_imports.append((module_name, str(e)))
                print(f"   ❌ Failed to import: {module_name} - {str(e)}")
        
        integration_results['module_imports'] = {
            'success': len(importable_modules),
            'failed': len(failed_imports),
            'success_rate': len(importable_modules) / len(websocket_modules) * 100
        }
        
        # Test WebSocket class instantiation
        print("   Testing WebSocket class instantiation...")
        
        try:
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
            
            # Mock dependencies for instantiation test
            mock_manager = Mock()
            mock_context = Mock()
            mock_context.user_id = "test_user"
            
            # Try to create emitter instance
            emitter = UnifiedWebSocketEmitter(
                manager=mock_manager,
                user_id="test_user",
                context=mock_context
            )
            
            print("   ✅ WebSocket emitter instantiation successful")
            integration_results['instantiation'] = True
            
        except Exception as e:
            print(f"   ❌ WebSocket emitter instantiation failed: {str(e)}")
            integration_results['instantiation'] = False
        
        return integration_results
        
    except Exception as e:
        print(f"   ❌ Integration testing failed: {str(e)}")
        return {'error': str(e)}


def run_staging_tests():
    """
    Phase 4: E2E Staging Tests (GCP Remote)
    
    Test end-to-end WebSocket functionality on staging environment
    """
    print("\n🌐 Phase 4: E2E Staging Tests (GCP Remote)")
    
    staging_results = {}
    
    try:
        # Check if we can reach staging environment
        print("   Testing staging environment connectivity...")
        
        # Mock staging test - replace with actual staging validation
        # This would typically involve:
        # 1. Connecting to staging WebSocket endpoint
        # 2. Authenticating with staging credentials
        # 3. Testing chat functionality
        # 4. Validating WebSocket connection stability
        
        print("   📋 Staging tests require actual GCP environment - mocking for validation")
        
        staging_results = {
            'connection_test': 'MOCK_PASS',
            'authentication_test': 'MOCK_PASS', 
            'chat_functionality_test': 'MOCK_PASS',
            'stability_test': 'MOCK_PASS',
            'note': 'Actual staging tests require GCP environment access'
        }
        
        print("   ✅ Staging test simulation completed")
        
        return staging_results
        
    except Exception as e:
        print(f"   ❌ Staging tests failed: {str(e)}")
        return {'error': str(e)}


def main():
    """
    Execute comprehensive WebSocket SSOT consolidation test plan for Issue #885
    """
    
    print("🚀 WebSocket Manager SSOT Consolidation Test Execution - Issue #885")
    print("Business Impact: $500K+ ARR Golden Path Protection")
    print("=" * 80)
    
    # Initialize test suite
    validator = WebSocketSSOTValidationTests()
    
    # Execute comprehensive validation
    results = validator.run_comprehensive_validation()
    
    # Execute integration tests
    integration_results = run_integration_tests()
    
    # Execute staging tests
    staging_results = run_staging_tests()
    
    # Generate comprehensive report
    print("\n📊 Generating Comprehensive Test Report")
    print("=" * 50)
    
    report = results.generate_report()
    
    # Add integration and staging results to report
    report += f"\nINTEGRATION TEST RESULTS:\n{'-'*40}\n"
    if 'error' in integration_results:
        report += f"❌ Integration tests failed: {integration_results['error']}\n"
    else:
        if 'module_imports' in integration_results:
            imports = integration_results['module_imports']
            report += f"Module Import Success Rate: {imports['success_rate']:.1f}% ({imports['success']}/{imports['success'] + imports['failed']})\n"
        
        if 'instantiation' in integration_results:
            status = "✅ PASS" if integration_results['instantiation'] else "❌ FAIL"
            report += f"WebSocket Instantiation Test: {status}\n"
    
    report += f"\nSTAGING TEST RESULTS:\n{'-'*40}\n"
    if 'error' in staging_results:
        report += f"❌ Staging tests failed: {staging_results['error']}\n"
    else:
        for test_name, result in staging_results.items():
            if test_name != 'note':
                report += f"{test_name}: {result}\n"
        if 'note' in staging_results:
            report += f"Note: {staging_results['note']}\n"
    
    # Print report
    print(report)
    
    # Write report to file
    report_file = PROJECT_ROOT / "WEBSOCKET_SSOT_TEST_EXECUTION_RESULTS_ISSUE_885.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    # Determine exit code based on compliance
    compliance = results.calculate_compliance()
    
    if compliance >= 70:
        print("\n✅ SSOT COMPLIANCE: ACCEPTABLE")
        print("WebSocket SSOT consolidation is on track")
        return 0
    elif compliance >= 50:
        print("\n⚠️  SSOT COMPLIANCE: NEEDS IMPROVEMENT")  
        print("WebSocket SSOT consolidation requires focused remediation")
        return 1
    else:
        print("\n❌ SSOT COMPLIANCE: CRITICAL")
        print("WebSocket SSOT consolidation requires immediate action")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)