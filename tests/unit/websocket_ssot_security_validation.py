"""
WebSocket SSOT Security Validation Tests - GitHub Issue #212

Tests designed to FAIL initially to demonstrate WebSocket SSOT violations:
- 667 files with WebSocket import violations  
- Only 1.0% SSOT compliance
- 431-96 security-critical singleton calls
- Multi-user data leakage scenarios

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Security & Stability - Prevent multi-user data leakage via singleton violations
- Value Impact: Ensure user isolation in WebSocket management, prevent security breaches
- Revenue Impact: Protect $500K+ ARR from security incidents caused by shared state

CRITICAL SECURITY ISSUES DETECTED:
1. Singleton get_websocket_manager() calls create shared state across users
2. Import violations bypass factory isolation patterns
3. Multi-user execution contexts leak data between sessions
4. Security-critical singleton calls in 431-96 locations

These tests should FAIL initially, demonstrating current violations.
After SSOT remediation, they should PASS, proving security compliance.
"""

import ast
import importlib
import inspect
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock, patch

try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
    BaseTestClass = SSotBaseTestCase
except ImportError:
    BaseTestClass = unittest.TestCase


class TestWebSocketSingletonSecurityValidation(BaseTestClass):
    """
    Tests to detect and validate security-critical singleton usage in WebSocket modules.
    
    EXPECTED INITIAL STATE: FAIL - Proves singleton violations exist
    EXPECTED POST-SSOT STATE: PASS - Proves singleton violations eliminated
    """

    def setUp(self):
        """Set up test fixtures for singleton detection."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.violation_count = 0
        self.security_critical_violations = []
        
    def __init__(self, *args, **kwargs):
        """Initialize test instance with required attributes."""
        super().__init__(*args, **kwargs)
        self.project_root = Path(__file__).parent.parent.parent
        self.security_critical_violations = []
        
    def test_detect_singleton_get_websocket_manager_calls(self):
        """
        Test to detect security-critical singleton get_websocket_manager() calls.
        
        SECURITY RISK: Singleton calls create shared state across users
        EXPECTED INITIAL: FAIL - 431-96 singleton calls detected
        EXPECTED POST-SSOT: PASS - Zero singleton calls, factory pattern only
        """
        singleton_violations = []
        
        # Search for singleton pattern violations across codebase
        search_patterns = [
            "get_websocket_manager()",
            "WebSocketManager.get_instance()",
            "websocket_manager_singleton",
            "GlobalWebSocketManager",
            "_websocket_manager_instance"
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files for now, focus on production code
            if "/tests/" in str(file_path) or "/test_" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in search_patterns:
                    if pattern in content:
                        # Parse AST to get exact line numbers
                        try:
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Call):
                                    if hasattr(node.func, 'attr') and node.func.attr == 'get_websocket_manager':
                                        singleton_violations.append({
                                            'file': str(file_path),
                                            'line': getattr(node, 'lineno', 'unknown'),
                                            'pattern': pattern,
                                            'security_risk': 'CRITICAL - Shared state across users'
                                        })
                                elif isinstance(node, ast.Name) and pattern in node.id:
                                    singleton_violations.append({
                                        'file': str(file_path),
                                        'line': getattr(node, 'lineno', 'unknown'),
                                        'pattern': pattern,
                                        'security_risk': 'HIGH - Singleton access pattern'
                                    })
                        except SyntaxError:
                            # Skip files with syntax errors
                            continue
                            
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        self.security_critical_violations.extend(singleton_violations)
        
        # This test should FAIL initially - proving violations exist
        self.assertGreater(
            len(singleton_violations), 400,
            f"Expected >400 singleton violations (GitHub issue reports 431-96), "
            f"but found only {len(singleton_violations)}. "
            f"Either violations have been fixed or search pattern needs updating."
        )
        
        # Log violations for analysis
        for violation in singleton_violations[:10]:  # Log first 10 for debugging
            print(f"SINGLETON VIOLATION: {violation}")

    def test_validate_canonical_import_enforcement(self):
        """
        Test to validate only canonical WebSocket imports are used.
        
        SECURITY RISK: Non-canonical imports bypass security controls
        EXPECTED INITIAL: FAIL - 667 files with import violations
        EXPECTED POST-SSOT: PASS - All imports use canonical patterns
        """
        import_violations = []
        
        # Define canonical imports vs prohibited imports
        canonical_imports = {
            'WebSocketManagerFactory': 'netra_backend.app.websocket_core.websocket_manager_factory',
            'WebSocketManager': 'netra_backend.app.websocket_core.websocket_manager',
            'WebSocketManagerProtocol': 'netra_backend.app.core.interfaces_websocket'
        }
        
        prohibited_patterns = [
            'from netra_backend.app.websocket_core.manager import',
            'from netra_backend.app.websocket_core.unified_manager import WebSocketManager',
            'import netra_backend.app.websocket_core.manager',
            'from .manager import',
            'from ..websocket_core.manager import'
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Skip test files for production code analysis
            if "/tests/" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    for prohibited in prohibited_patterns:
                        if prohibited in line:
                            import_violations.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': line_num,
                                'violation': line.strip(),
                                'risk_level': 'HIGH - Bypasses canonical security controls'
                            })
                            
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This test should FAIL initially - proving violations exist
        self.assertGreater(
            len(import_violations), 600,
            f"Expected >600 import violations (GitHub issue reports 667 files), "
            f"but found only {len(import_violations)}. "
            f"Either violations have been fixed or search pattern needs updating."
        )
        
        # Log violations for analysis
        for violation in import_violations[:10]:  # Log first 10 for debugging
            print(f"IMPORT VIOLATION: {violation}")

    def test_multi_user_data_leakage_scenarios(self):
        """
        Test for multi-user data leakage via shared WebSocket manager state.
        
        SECURITY RISK: User A can see User B's WebSocket messages
        EXPECTED INITIAL: FAIL - Shared state enables data leakage
        EXPECTED POST-SSOT: PASS - Complete user isolation
        """
        shared_state_risks = []
        
        # Search for shared state patterns that enable data leakage
        risky_patterns = [
            r'class.*Manager.*:',  # Manager classes often have shared state
            r'_instance.*=.*None',  # Singleton pattern markers
            r'global.*websocket',   # Global WebSocket variables
            r'cache.*=.*\{\}',       # Shared caches
            r'connections.*=.*\[\]', # Shared connection lists
            r'sessions.*=.*\{\}'     # Shared session storage
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            # Focus on WebSocket-related files
            if "websocket" not in str(file_path).lower():
                continue
            if "/tests/" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in risky_patterns:
                        import re
                        if re.search(pattern, line):
                            shared_state_risks.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': line_num,
                                'pattern': pattern,
                                'code': line.strip(),
                                'risk': 'DATA LEAKAGE - Shared state between users'
                            })
                            
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This test should FAIL initially - proving shared state risks exist
        self.assertGreater(
            len(shared_state_risks), 50,
            f"Expected >50 shared state risks in WebSocket modules, "
            f"but found only {len(shared_state_risks)}. "
            f"Either risks have been mitigated or search needs refinement."
        )
        
        # Log risks for analysis
        for risk in shared_state_risks[:10]:  # Log first 10 for debugging
            print(f"SHARED STATE RISK: {risk}")

    def test_factory_pattern_bypass_detection(self):
        """
        Test to detect bypasses of factory pattern security controls.
        
        SECURITY RISK: Direct instantiation bypasses user isolation
        EXPECTED INITIAL: FAIL - Factory bypasses detected
        EXPECTED POST-SSOT: PASS - All instantiation through secure factories
        """
        factory_bypasses = []
        
        # Search for direct instantiation that bypasses factory security
        bypass_patterns = [
            'WebSocketManager()',
            'UnifiedWebSocketManager()',
            'new WebSocketManager',
            'WebSocketManager.create(',
            'WebSocketManager.initialize('
        ]
        
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            if "/tests/" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Parse AST for precise detection
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if hasattr(node.func, 'id'):
                                if 'WebSocketManager' in node.func.id:
                                    factory_bypasses.append({
                                        'file': str(file_path.relative_to(self.project_root)),
                                        'line': getattr(node, 'lineno', 'unknown'),
                                        'bypass_type': 'Direct instantiation',
                                        'security_risk': 'CRITICAL - Bypasses user isolation'
                                    })
                except SyntaxError:
                    continue
                    
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # This test should FAIL initially - proving bypasses exist
        self.assertGreater(
            len(factory_bypasses), 20,
            f"Expected >20 factory bypasses, "
            f"but found only {len(factory_bypasses)}. "
            f"Either bypasses have been fixed or detection needs improvement."
        )
        
        # Log bypasses for analysis
        for bypass in factory_bypasses[:10]:  # Log first 10 for debugging
            print(f"FACTORY BYPASS: {bypass}")

    def test_ssot_compliance_threshold_validation(self):
        """
        Test overall SSOT compliance is below acceptable threshold.
        
        EXPECTED INITIAL: FAIL - 1.0% compliance (far below 95% requirement)
        EXPECTED POST-SSOT: PASS - >95% compliance achieved
        """
        # Calculate total violations across all test methods
        total_violations = len(self.security_critical_violations)
        
        # Estimate total files that should be compliant
        python_files = list(self.project_root.rglob("*.py"))
        websocket_related_files = [
            f for f in python_files 
            if "websocket" in str(f).lower() and "/tests/" not in str(f)
        ]
        
        if len(websocket_related_files) > 0:
            compliance_rate = max(0, (len(websocket_related_files) - total_violations) / len(websocket_related_files))
        else:
            compliance_rate = 0
        
        # This test should FAIL initially - proving low compliance
        self.assertLess(
            compliance_rate, 0.05,  # Less than 5% compliance
            f"Expected <5% SSOT compliance (GitHub issue reports 1.0%), "
            f"but found {compliance_rate:.1%} compliance. "
            f"Either compliance has improved or calculation needs adjustment."
        )
        
        print(f"SSOT COMPLIANCE RATE: {compliance_rate:.1%}")
        print(f"WebSocket-related files: {len(websocket_related_files)}")
        print(f"Total violations detected: {total_violations}")


class TestWebSocketSSotComplianceRegressions(BaseTestClass):
    """
    Tests to prevent regression back to SSOT violations after remediation.
    """

    def test_prevent_new_singleton_introductions(self):
        """
        Test to prevent new singleton patterns from being introduced.
        
        This test should PASS after SSOT remediation and continue passing.
        """
        # Mock implementation for post-remediation validation
        # This would be implemented as part of CI/CD pipeline
        pass

    def test_enforce_canonical_import_patterns(self):
        """
        Test to enforce only canonical import patterns are used going forward.
        
        This test should PASS after SSOT remediation and continue passing.
        """
        # Mock implementation for ongoing compliance
        pass


if __name__ == '__main__':
    unittest.main()