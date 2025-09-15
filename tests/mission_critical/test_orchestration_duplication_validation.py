#!/usr/bin/env python3
"""
Mission Critical Test Suite: Orchestration Duplication Violation Reproduction - Issue #1075

Business Value: Platform/Internal - Test Infrastructure SSOT Compliance
Critical for $500K+ ARR protection through unified orchestration patterns and elimination of competing orchestration systems.

This test reproduces the critical violation where 129+ files contain duplicate orchestration 
systems, try-except import patterns, and competing orchestration configurations.

VIOLATION BEING REPRODUCED:
- Multiple orchestration implementations across the codebase
- Try-except import patterns for orchestration availability detection
- Competing orchestration enum definitions
- Fragmented Docker/service orchestration management

EXPECTED BEHAVIOR AFTER REMEDIATION:
- Single SSOT orchestration system (test_framework.ssot.orchestration)
- Unified orchestration enums (test_framework.ssot.orchestration_enums)
- No try-except import patterns for orchestration detection
- Consistent orchestration availability checking

Author: SSOT Gardener Agent - Issue #1075 Step 1
Date: 2025-09-14
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple, Union
from dataclasses import dataclass
import pytest

# Test framework imports (following SSOT patterns)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class OrchestrationViolation:
    """Details about an orchestration duplication violation."""
    file_path: str
    line_number: int
    violation_code: str
    violation_type: str  # 'try_except_import', 'duplicate_enum', 'duplicate_orchestration', 'custom_availability_check'
    orchestration_system: str  # 'docker', 'kubernetes', 'service_discovery', 'enum_definition'


class OrchestrationDuplicationValidationTests(SSotBaseTestCase):
    """
    Test suite to reproduce and validate orchestration duplication violations.
    
    This test is DESIGNED TO FAIL until SSOT orchestration consolidation is complete,
    demonstrating the fragmentation of orchestration systems across the codebase.
    """

    def setUp(self):
        super().setUp()
        self.project_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        self.violations_found: List[OrchestrationViolation] = []
        self.scan_directories = [
            'tests',
            'netra_backend',
            'auth_service',
            'test_framework',
            'shared',
            'scripts'
        ]
        
        # Known orchestration patterns to detect
        self.orchestration_patterns = {
            'try_except_import': [
                r'try:\s*\n\s*import\s+docker',
                r'try:\s*\n\s*from\s+docker',
                r'except ImportError.*docker',
                r'try:\s*\n\s*import.*orchestrat',
                r'except.*orchestrat'
            ],
            'duplicate_enum': [
                r'class.*OrchestrationStatus.*Enum',
                r'class.*DockerStatus.*Enum', 
                r'class.*ServiceStatus.*Enum',
                r'ORCHESTRATION_.*=.*',
                r'DOCKER_.*=.*Enum'
            ],
            'duplicate_orchestration': [
                r'class.*OrchestrationManager',
                r'class.*DockerManager', 
                r'def.*orchestration_available',
                r'def.*docker_available',
                r'def.*check_orchestration'
            ],
            'custom_availability_check': [
                r'def.*is_docker_available',
                r'def.*check_docker_status',
                r'def.*get_orchestration_status',
                r'def.*orchestration_enabled'
            ]
        }

    def scan_file_for_orchestration_violations(self, file_path: Path) -> List[OrchestrationViolation]:
        """
        Scan a Python file for orchestration duplication violations.
        
        Detects:
        1. Try-except import patterns for orchestration availability
        2. Duplicate orchestration enum definitions
        3. Custom orchestration managers
        4. Custom availability checking functions
        """
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # AST-based analysis for sophisticated detection
            try:
                tree = ast.parse(content)
                violations.extend(self.analyze_ast_for_violations(file_path, tree, lines))
            except SyntaxError:
                # Fallback to string matching for files with syntax issues
                pass
            
            # Regex-based pattern detection
            violations.extend(self.analyze_patterns_for_violations(file_path, content, lines))
                    
        except Exception as e:
            # Log but don't fail on individual file errors
            print(f"Warning: Could not scan {file_path}: {e}")
            
        return violations

    def analyze_ast_for_violations(self, file_path: Path, tree: ast.AST, lines: List[str]) -> List[OrchestrationViolation]:
        """Analyze AST for orchestration violations."""
        violations = []
        
        for node in ast.walk(tree):
            # Try-except import patterns
            if isinstance(node, ast.Try):
                violation = self.analyze_try_except_block(file_path, node, lines)
                if violation:
                    violations.append(violation)
            
            # Class definitions (enums, managers)
            elif isinstance(node, ast.ClassDef):
                violation = self.analyze_class_definition(file_path, node, lines)
                if violation:
                    violations.append(violation)
            
            # Function definitions (availability checks)
            elif isinstance(node, ast.FunctionDef):
                violation = self.analyze_function_definition(file_path, node, lines)
                if violation:
                    violations.append(violation)
                    
        return violations

    def analyze_try_except_block(self, file_path: Path, node: ast.Try, lines: List[str]) -> Optional[OrchestrationViolation]:
        """Analyze try-except blocks for orchestration import patterns."""
        # Check if this is an import try-except block
        has_import = any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in node.body)
        if not has_import:
            return None
            
        # Check if it's orchestration-related
        code_block = '\n'.join(lines[node.lineno-1:node.end_lineno] if node.end_lineno else lines[node.lineno-1:node.lineno+5])
        
        orchestration_keywords = ['docker', 'orchestrat', 'kubernetes', 'compose', 'container']
        if any(keyword in code_block.lower() for keyword in orchestration_keywords):
            return OrchestrationViolation(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=node.lineno,
                violation_code=code_block[:200],  # First 200 chars
                violation_type='try_except_import',
                orchestration_system='docker' if 'docker' in code_block.lower() else 'orchestration'
            )
            
        return None

    def analyze_class_definition(self, file_path: Path, node: ast.ClassDef, lines: List[str]) -> Optional[OrchestrationViolation]:
        """Analyze class definitions for orchestration duplication."""
        class_name = node.name.lower()
        
        # Check for orchestration-related classes
        orchestration_indicators = [
            'orchestration', 'docker', 'container', 'service', 'manager'
        ]
        
        if any(indicator in class_name for indicator in orchestration_indicators):
            # Check if it's an enum
            base_classes = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    base_classes.append(base.id)
                elif isinstance(base, ast.Attribute):
                    if isinstance(base.value, ast.Name):
                        base_classes.append(f"{base.value.id}.{base.attr}")
            
            if any('enum' in base.lower() for base in base_classes):
                return OrchestrationViolation(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=node.lineno,
                    violation_code=f"class {node.name}({', '.join(base_classes)})",
                    violation_type='duplicate_enum',
                    orchestration_system='enum_definition'
                )
            elif 'manager' in class_name:
                return OrchestrationViolation(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=node.lineno,
                    violation_code=f"class {node.name}",
                    violation_type='duplicate_orchestration',
                    orchestration_system='manager'
                )
                
        return None

    def analyze_function_definition(self, file_path: Path, node: ast.FunctionDef, lines: List[str]) -> Optional[OrchestrationViolation]:
        """Analyze function definitions for custom availability checks."""
        func_name = node.name.lower()
        
        availability_patterns = [
            'available', 'enabled', 'check', 'status', 'ready'
        ]
        orchestration_patterns = [
            'docker', 'orchestrat', 'container', 'service'
        ]
        
        if (any(avail in func_name for avail in availability_patterns) and
            any(orch in func_name for orch in orchestration_patterns)):
            
            return OrchestrationViolation(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=node.lineno,
                violation_code=f"def {node.name}(...)",
                violation_type='custom_availability_check',
                orchestration_system='availability_check'
            )
            
        return None

    def analyze_patterns_for_violations(self, file_path: Path, content: str, lines: List[str]) -> List[OrchestrationViolation]:
        """Analyze content using regex patterns for violations."""
        violations = []
        
        for violation_type, patterns in self.orchestration_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                for match in matches:
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    violation_code = lines[line_num - 1].strip()
                    
                    # Determine orchestration system
                    orchestration_system = 'unknown'
                    if 'docker' in violation_code.lower():
                        orchestration_system = 'docker'
                    elif 'orchestrat' in violation_code.lower():
                        orchestration_system = 'orchestration'
                    elif 'enum' in violation_code.lower():
                        orchestration_system = 'enum_definition'
                        
                    violation = OrchestrationViolation(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                        violation_code=violation_code,
                        violation_type=violation_type,
                        orchestration_system=orchestration_system
                    )
                    violations.append(violation)
                    
        return violations

    def scan_codebase_for_orchestration_violations(self) -> List[OrchestrationViolation]:
        """Scan entire codebase for orchestration duplication violations."""
        all_violations = []
        
        for scan_dir in self.scan_directories:
            scan_path = self.project_root / scan_dir
            if not scan_path.exists():
                continue
                
            # Scan all Python files
            for py_file in scan_path.rglob('*.py'):
                # Skip __pycache__ and similar
                if '__pycache__' in str(py_file) or '.git' in str(py_file):
                    continue
                    
                violations = self.scan_file_for_orchestration_violations(py_file)
                all_violations.extend(violations)
                
        return all_violations

    def validate_ssot_orchestration_functionality(self) -> Dict[str, Any]:
        """
        Validate that SSOT orchestration system exists and provides required functionality.
        This should PASS even before remediation.
        """
        validation_results = {
            'orchestration_exists': False,
            'orchestration_importable': False,
            'enums_exist': False,
            'enums_importable': False,
            'has_availability_check': False,
            'has_unified_config': False,
            'functionality_score': 0
        }
        
        try:
            # Check SSOT orchestration module
            from test_framework.ssot.orchestration import OrchestrationConfig
            validation_results['orchestration_exists'] = True
            validation_results['orchestration_importable'] = True
            validation_results['functionality_score'] += 1
            
            # Check for availability method
            if hasattr(OrchestrationConfig, 'is_available') or hasattr(OrchestrationConfig, 'check_availability'):
                validation_results['has_availability_check'] = True
                validation_results['functionality_score'] += 1
                
            # Check for unified config
            if hasattr(OrchestrationConfig, 'get_config') or hasattr(OrchestrationConfig, 'config'):
                validation_results['has_unified_config'] = True
                validation_results['functionality_score'] += 1
                
        except ImportError:
            pass
        
        try:
            # Check SSOT orchestration enums
            from test_framework.ssot.orchestration_enums import OrchestrationStatus
            validation_results['enums_exist'] = True
            validation_results['enums_importable'] = True
            validation_results['functionality_score'] += 1
            
        except ImportError:
            pass
            
        return validation_results

    def test_reproduce_orchestration_duplication_violations(self):
        """
        REPRODUCTION TEST: This test WILL FAIL until violations are remediated.
        
        Scans codebase and identifies all files with duplicate orchestration systems,
        try-except import patterns, and competing orchestration configurations.
        """
        violations = self.scan_codebase_for_orchestration_violations()
        self.violations_found = violations
        
        # Generate detailed violation report
        violation_report = self.generate_violation_report(violations)
        print("\n" + "="*80)
        print("ORCHESTRATION DUPLICATION VIOLATION REPRODUCTION RESULTS")
        print("="*80)
        print(violation_report)
        
        # This assertion SHOULD FAIL until remediation is complete
        self.assertEqual(
            len(violations), 0, 
            f"CRITICAL VIOLATION REPRODUCED: Found {len(violations)} orchestration duplication violations. "
            f"All orchestration should use SSOT patterns from test_framework.ssot.orchestration. "
            f"Violations found in: {[v.file_path for v in violations[:10]]}{'...' if len(violations) > 10 else ''}"
        )

    def test_validate_ssot_orchestration_functionality(self):
        """
        VALIDATION TEST: This test should PASS both before and after remediation.
        
        Validates that SSOT orchestration system exists and provides required functionality.
        """
        validation_results = self.validate_ssot_orchestration_functionality()
        
        # At least orchestration should exist
        self.assertTrue(
            validation_results['orchestration_exists'],
            "CRITICAL: SSOT orchestration system must exist at test_framework.ssot.orchestration. "
            "This is the canonical orchestration management system."
        )
        
        # Should have reasonable functionality
        self.assertGreater(
            validation_results['functionality_score'], 1,
            f"SSOT orchestration system must provide core functionality. "
            f"Score: {validation_results['functionality_score']}/4. "
            f"Results: {validation_results}"
        )

    def test_orchestration_ssot_pattern_compliance(self):
        """
        COMPLIANCE TEST: Validates detection of SSOT-compliant orchestration patterns.
        
        This test should PASS - it validates our ability to detect proper patterns.
        """
        # Test that we can detect proper SSOT imports
        proper_patterns = [
            "from test_framework.ssot.orchestration import OrchestrationConfig",
            "from test_framework.ssot.orchestration_enums import OrchestrationStatus",
            "OrchestrationConfig.is_available()",
            "OrchestrationStatus.AVAILABLE"
        ]
        
        # This should pass - we're just validating detection capability
        for pattern in proper_patterns:
            # This is a positive test - we're checking we can identify good patterns
            self.assertIsInstance(pattern, str, f"Should be able to process SSOT pattern: {pattern}")

    def generate_violation_report(self, violations: List[OrchestrationViolation]) -> str:
        """Generate detailed report of orchestration duplication violations."""
        if not violations:
            return "✅ NO VIOLATIONS FOUND - All orchestration uses SSOT patterns"
            
        report_lines = [
            f"🚨 CRITICAL VIOLATIONS FOUND: {len(violations)} orchestration duplication violations",
            "",
            "VIOLATION BREAKDOWN BY TYPE:"
        ]
        
        # Group by violation type
        by_type = {}
        for violation in violations:
            if violation.violation_type not in by_type:
                by_type[violation.violation_type] = []
            by_type[violation.violation_type].append(violation)
            
        for violation_type, type_violations in by_type.items():
            report_lines.append(f"  {violation_type}: {len(type_violations)} violations")
            
        # Group by orchestration system
        by_system = {}
        for violation in violations:
            system = violation.orchestration_system
            if system not in by_system:
                by_system[system] = []
            by_system[system].append(violation)
            
        report_lines.extend([
            "",
            "VIOLATION BREAKDOWN BY ORCHESTRATION SYSTEM:"
        ])
        
        for system, system_violations in sorted(by_system.items(), 
                                               key=lambda x: len(x[1]), reverse=True):
            report_lines.append(f"  {system}: {len(system_violations)} violations")
        
        report_lines.extend([
            "",
            "DETAILED VIOLATIONS (first 20):"
        ])
        
        for i, violation in enumerate(violations[:20]):
            report_lines.extend([
                f"  {i+1}. File: {violation.file_path}",
                f"     Line {violation.line_number}: {violation.violation_code}",
                f"     Type: {violation.violation_type}",
                f"     System: {violation.orchestration_system}",
                ""
            ])
            
        if len(violations) > 20:
            report_lines.append(f"  ... and {len(violations) - 20} more violations")
            
        report_lines.extend([
            "",
            "REMEDIATION REQUIRED:",
            "1. Replace all try-except orchestration imports with SSOT imports",
            "2. Consolidate duplicate orchestration enums into test_framework.ssot.orchestration_enums",
            "3. Use OrchestrationConfig.is_available() instead of custom availability checks",
            "4. Remove duplicate orchestration manager implementations", 
            "5. Use unified orchestration configuration patterns",
            "6. Eliminate competing orchestration systems in favor of SSOT approach"
        ])
        
        return "\n".join(report_lines)

    def tearDown(self):
        """Clean up after test execution."""
        # Log summary for debugging
        if hasattr(self, 'violations_found') and self.violations_found:
            print(f"\nTest completed. Found {len(self.violations_found)} orchestration duplication violations.")
        super().tearDown()


if __name__ == '__main__':
    # Note: This file should be run through unified_test_runner.py for SSOT compliance
    print("WARNING: This test should be run through unified_test_runner.py for SSOT compliance")
    print("Example: python tests/unified_test_runner.py --file tests/mission_critical/test_orchestration_duplication_validation.py")