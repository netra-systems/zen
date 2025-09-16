"""Test Issue #1186: UserExecutionEngine Constructor Dependency Injection Requirements - Phase 1 Baseline Detection

This test suite is designed to FAIL initially to expose current UserExecutionEngine
constructor violations and dependency injection issues. These tests demonstrate
mission critical infrastructure requirements before SSOT consolidation.

Expected Behavior: These tests SHOULD FAIL to demonstrate:
1. Constructor allows parameterless instantiation (violates dependency injection)
2. Missing required dependencies: UserExecutionContext, AgentInstanceFactory, WebSocketEmitter
3. Singleton pattern enforcement violations (allows direct instantiation)
4. User isolation requirements not enforced in constructor

Business Impact: Constructor violations prevent enterprise-grade multi-user isolation
and create security vulnerabilities that block $500K+ ARR functionality scalability.
"""

import ast
import os
import pytest
import re
import sys
import unittest
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional, Any
from collections import defaultdict
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
class UserExecutionEngineConstructorRequirementsTests(unittest.TestCase):
    """Test class to validate UserExecutionEngine constructor dependency injection requirements"""
    
    def setUp(self):
        """Set up test environment with constructor validation tracking"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.required_dependencies = [
            'UserExecutionContext',
            'AgentInstanceFactory', 
            'WebSocketEmitter'
        ]
        self.constructor_violations = {}
        self.baseline_metrics = {}
        
    def test_01_constructor_dependency_injection_requirement_validation(self):
        """
        Test 1: Validate constructor requires proper dependency injection
        
        EXPECTED TO FAIL: Should demonstrate constructor allows parameterless instantiation
        """
        print("\n🔍 BASELINE TEST 1: Validating constructor dependency injection requirements...")
        
        dependency_violations = self._scan_constructor_dependency_requirements()
        violation_count = len(dependency_violations)
        
        print(f"📊 Constructor Dependency Analysis:")
        print(f"   - Required dependencies: {len(self.required_dependencies)}")
        print(f"   - Dependency violations: {violation_count}")
        print(f"   - Target: 0 violations (all dependencies required)")
        
        # Store baseline for tracking
        self.baseline_metrics['dependency_violations'] = violation_count
        
        # This test should FAIL to demonstrate dependency injection violations
        self.assertEqual(
            violation_count,
            0,
            f"❌ BASELINE VIOLATION: Found {violation_count} constructor dependency injection violations. "
            f"Mission critical infrastructure requires all dependencies to be mandatory.\n"
            f"Required dependencies: {', '.join(self.required_dependencies)}\n"
            f"Violations detected:\n"
            + '\n'.join([f"  - {path}: {violation}" for path, violation in dependency_violations])
        )
        
    def test_02_parameterless_instantiation_prevention_validation(self):
        """
        Test 2: Validate constructor prevents parameterless instantiation
        
        EXPECTED TO FAIL: Should demonstrate constructor allows UserExecutionEngine()
        """
        print("\n🔍 BASELINE TEST 2: Validating parameterless instantiation prevention...")
        
        try:
            # Attempt to find and import UserExecutionEngine
            user_execution_engine_class = self._find_user_execution_engine_class()
            
            if user_execution_engine_class is None:
                self.fail("❌ CRITICAL: Cannot locate UserExecutionEngine class for testing")
            
            # Test parameterless instantiation
            parameterless_allowed = self._test_parameterless_instantiation(user_execution_engine_class)
            
            print(f"📊 Parameterless Instantiation Analysis:")
            print(f"   - Parameterless instantiation allowed: {parameterless_allowed}")
            print(f"   - Security target: False (must require dependencies)")
            
            # Store baseline for tracking
            self.baseline_metrics['parameterless_allowed'] = parameterless_allowed
            
            # This test should FAIL if parameterless instantiation is allowed
            self.assertFalse(
                parameterless_allowed,
                f"❌ BASELINE VIOLATION: UserExecutionEngine allows parameterless instantiation. "
                f"Mission critical security requires all constructor parameters to be mandatory.\n"
                f"This creates enterprise security vulnerabilities and violates dependency injection principles."
            )
            
        except Exception as e:
            # Expected in baseline - class may not be importable
            print(f"   - Import/instantiation analysis: {str(e)}")
            self.fail(f"❌ BASELINE VIOLATION: UserExecutionEngine constructor validation failed: {str(e)}")
        
    def test_03_user_context_isolation_enforcement_validation(self):
        """
        Test 3: Validate constructor enforces user context isolation
        
        EXPECTED TO FAIL: Should demonstrate missing UserExecutionContext requirement
        """
        print("\n🔍 BASELINE TEST 3: Validating user context isolation enforcement...")
        
        context_isolation_violations = self._scan_user_context_isolation_requirements()
        violation_count = len(context_isolation_violations)
        
        print(f"📊 User Context Isolation Analysis:")
        print(f"   - Context isolation violations: {violation_count}")
        print(f"   - Enterprise target: 0 violations (strict isolation)")
        
        # Store baseline for tracking
        self.baseline_metrics['context_isolation_violations'] = violation_count
        
        # This test should FAIL to demonstrate context isolation violations
        self.assertEqual(
            violation_count,
            0,
            f"❌ BASELINE VIOLATION: Found {violation_count} user context isolation violations. "
            f"Enterprise multi-user deployment requires strict user context isolation.\n"
            f"Context isolation violations:\n"
            + '\n'.join([f"  - {path}: {violation}" for path, violation in context_isolation_violations])
        )
        
    def test_04_factory_pattern_enforcement_validation(self):
        """
        Test 4: Validate constructor works exclusively with factory patterns
        
        EXPECTED TO FAIL: Should demonstrate direct instantiation is possible
        """
        print("\n🔍 BASELINE TEST 4: Validating factory pattern enforcement...")
        
        direct_instantiation_violations = self._scan_direct_instantiation_violations()
        violation_count = len(direct_instantiation_violations)
        
        print(f"📊 Factory Pattern Enforcement Analysis:")
        print(f"   - Direct instantiation violations: {violation_count}")
        print(f"   - SSOT target: 0 violations (factory-only instantiation)")
        
        # Store baseline for tracking
        self.baseline_metrics['direct_instantiation_violations'] = violation_count
        
        # This test should FAIL to demonstrate direct instantiation violations
        self.assertEqual(
            violation_count,
            0,
            f"❌ BASELINE VIOLATION: Found {violation_count} direct instantiation violations. "
            f"SSOT architecture requires factory-only instantiation patterns.\n"
            f"Direct instantiation violations:\n"
            + '\n'.join([f"  - {path}: {violation}" for path, violation in direct_instantiation_violations])
        )
        
    def test_05_constructor_signature_consistency_validation(self):
        """
        Test 5: Validate constructor signature consistency across implementations
        
        EXPECTED TO FAIL: Should demonstrate inconsistent constructor signatures
        """
        print("\n🔍 BASELINE TEST 5: Validating constructor signature consistency...")
        
        signature_inconsistencies = self._analyze_constructor_signature_consistency()
        inconsistency_count = len(signature_inconsistencies)
        
        print(f"📊 Constructor Signature Consistency Analysis:")
        print(f"   - Signature inconsistencies: {inconsistency_count}")
        print(f"   - Target: 0 inconsistencies (uniform signature)")
        
        # Store baseline for tracking
        self.baseline_metrics['signature_inconsistencies'] = inconsistency_count
        
        # This test should FAIL to demonstrate signature inconsistencies
        self.assertEqual(
            inconsistency_count,
            0,
            f"❌ BASELINE VIOLATION: Found {inconsistency_count} constructor signature inconsistencies. "
            f"SSOT requires uniform constructor signatures across all implementations.\n"
            f"Signature inconsistencies:\n"
            + '\n'.join([f"  - {path}: {inconsistency}" for path, inconsistency in signature_inconsistencies])
        )
    
    def _scan_constructor_dependency_requirements(self) -> List[Tuple[str, str]]:
        """Scan for constructor dependency requirement violations"""
        violations = []
        
        # Patterns that indicate dependency injection violations
        violation_patterns = [
            r'def __init__\(self\):',  # Parameterless constructor
            r'def __init__\(self, \*args\):',  # Variable args allowing empty
            r'def __init__\(self, .*=None',  # Optional dependencies
            r'def __init__\(self, .*=\[\]',  # Default values
        ]
        
        user_execution_engine_files = self._get_user_execution_engine_files()
        print(f"   - Scanning {len(user_execution_engine_files)} UserExecutionEngine files...")
        
        for py_file in user_execution_engine_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for UserExecutionEngine class definition
                if 'class UserExecutionEngine' in content:
                    for pattern in violation_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            violations.append((
                                str(py_file.relative_to(self.project_root)), 
                                f"Dependency injection violation: {match.group()}"
                            ))
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return violations
    
    def _find_user_execution_engine_class(self) -> Optional[type]:
        """Attempt to find and import UserExecutionEngine class"""
        try:
            # Try the canonical import path first
            sys.path.insert(0, str(self.project_root))
            
            # Multiple potential import paths to test
            import_attempts = [
                'netra_backend.app.agents.supervisor.user_execution_engine',
                'netra_backend.app.agents.user_execution_engine',
                'netra_backend.app.execution_engine',
                'execution_engine_consolidated',
            ]
            
            for import_path in import_attempts:
                try:
                    module = __import__(import_path, fromlist=['UserExecutionEngine'])
                    if hasattr(module, 'UserExecutionEngine'):
                        return getattr(module, 'UserExecutionEngine')
                except (ImportError, AttributeError, ModuleNotFoundError):
                    continue
                    
            return None
            
        except Exception:
            return None
        finally:
            # Clean up sys.path
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))
    
    def _test_parameterless_instantiation(self, user_execution_engine_class: type) -> bool:
        """Test if UserExecutionEngine allows parameterless instantiation"""
        try:
            # Attempt parameterless instantiation
            instance = user_execution_engine_class()
            return True  # If successful, parameterless instantiation is allowed
        except TypeError as e:
            # If TypeError due to missing required arguments, parameterless is prevented
            if "required" in str(e) or "missing" in str(e):
                return False
            return True  # Other TypeErrors might indicate parameterless is allowed
        except Exception:
            # Other exceptions suggest parameterless instantiation might be prevented
            return False
    
    def _scan_user_context_isolation_requirements(self) -> List[Tuple[str, str]]:
        """Scan for user context isolation requirement violations"""
        violations = []
        
        # Patterns that indicate missing user context isolation
        isolation_violation_patterns = [
            r'class UserExecutionEngine.*:(?:(?!UserExecutionContext).)*?def __init__',  # Constructor without UserExecutionContext
            r'def __init__\([^)]*\):(?!.*UserExecutionContext)',  # Constructor params without UserExecutionContext
            r'shared_context.*=',  # Shared context variables
            r'global.*context',  # Global context usage
        ]
        
        user_execution_engine_files = self._get_user_execution_engine_files()
        
        for py_file in user_execution_engine_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for UserExecutionEngine class definition
                if 'class UserExecutionEngine' in content:
                    for pattern in isolation_violation_patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
                        for match in matches:
                            violations.append((
                                str(py_file.relative_to(self.project_root)), 
                                f"User context isolation violation: {match.group()[:100]}..."
                            ))
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return violations
    
    def _scan_direct_instantiation_violations(self) -> List[Tuple[str, str]]:
        """Scan for direct instantiation violations (non-factory usage)"""
        violations = []
        
        # Patterns that indicate direct instantiation
        direct_instantiation_patterns = [
            r'UserExecutionEngine\(',  # Direct instantiation
            r'= UserExecutionEngine\(',  # Assignment with direct instantiation
            r'new UserExecutionEngine\(',  # New instance creation
        ]
        
        python_files = self._get_all_source_files()
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for pattern in direct_instantiation_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        # Skip if it's within the class definition itself
                        if 'class UserExecutionEngine' not in content:
                            violations.append((
                                str(py_file.relative_to(self.project_root)), 
                                f"Direct instantiation: {match.group()}"
                            ))
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
                
        return violations
    
    def _analyze_constructor_signature_consistency(self) -> List[Tuple[str, str]]:
        """Analyze constructor signature consistency across implementations"""
        inconsistencies = []
        
        user_execution_engine_files = self._get_user_execution_engine_files()
        constructor_signatures = {}
        
        for py_file in user_execution_engine_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract constructor signature
                class_match = re.search(r'class UserExecutionEngine.*?:', content, re.MULTILINE)
                if class_match:
                    # Find the constructor within the class
                    constructor_match = re.search(
                        r'def __init__\([^)]*\):',
                        content[class_match.end():],
                        re.MULTILINE
                    )
                    if constructor_match:
                        signature = constructor_match.group()
                        file_path = str(py_file.relative_to(self.project_root))
                        
                        if signature in constructor_signatures:
                            constructor_signatures[signature].append(file_path)
                        else:
                            constructor_signatures[signature] = [file_path]
                            
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
        
        # Check for inconsistencies
        if len(constructor_signatures) > 1:
            for signature, files in constructor_signatures.items():
                inconsistencies.append((
                    ', '.join(files),
                    f"Constructor signature: {signature}"
                ))
                
        return inconsistencies
    
    def _get_user_execution_engine_files(self) -> List[Path]:
        """Get files containing UserExecutionEngine class definitions"""
        engine_files = []
        
        search_paths = [
            self.project_root / 'netra_backend' / 'app',
            self.project_root / 'shared',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    try:
                        with open(py_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'class UserExecutionEngine' in content:
                                engine_files.append(py_file)
                    except (UnicodeDecodeError, PermissionError, OSError):
                        continue
                        
        return engine_files
    
    def _get_all_source_files(self) -> List[Path]:
        """Get all source files for direct instantiation analysis"""
        source_files = []
        
        search_paths = [
            self.project_root / 'netra_backend',
            self.project_root / 'auth_service',
            self.project_root / 'tests',
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for py_file in search_path.rglob('*.py'):
                    # Exclude certain directories
                    if any(excluded in py_file.parts for excluded in ['.venv', '__pycache__', '.git']):
                        continue
                    source_files.append(py_file)
                    
        return source_files[:200]  # Limit for performance


if __name__ == '__main__':
    print("🚨 Issue #1186 UserExecutionEngine Constructor Requirements - Baseline Detection")
    print("=" * 80)
    print("⚠️  WARNING: These tests are DESIGNED TO FAIL to establish baseline metrics")
    print("📊 Expected: 5 test failures showing constructor requirement violations")
    print("🎯 Goal: Baseline measurement for mission critical infrastructure validation")
    print("💰 Impact: Enables enterprise-grade dependency injection for $500K+ ARR")
    print("=" * 80)
    
    unittest.main(verbosity=2)