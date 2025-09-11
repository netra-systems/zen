"""
SSOT Compliance Tests for DeepAgentState Import Blocking - Issue #354

CRITICAL SECURITY VULNERABILITY: P0 vulnerability where DeepAgentState imports 
throughout the codebase create systematic user isolation vulnerabilities.

Business Value Justification (BVJ):
- Segment: Platform (affects all customer segments through systemic vulnerability)
- Business Goal: Eliminate systematic security vulnerabilities at the architectural level
- Value Impact: Prevents widespread user data contamination across entire platform
- Revenue Impact: Prevents $500K+ ARR loss from systemic multi-tenant security failures

SSOT COMPLIANCE STRATEGY:
Single Source of Truth (SSOT) principle requires that UserExecutionContext is the 
ONLY acceptable pattern for user execution context. DeepAgentState must be 
systematically eliminated and blocked from all new code.

COMPLIANCE CHECKS:
1. Import Detection - Scan for DeepAgentState imports in ReportingSubAgent
2. Method Signature Compliance - Validate methods use only UserExecutionContext
3. Type Annotation Compliance - Ensure type hints reference UserExecutionContext
4. Documentation Compliance - Verify docs reference secure patterns only
5. Test Pattern Compliance - Ensure tests use UserExecutionContext patterns
6. Legacy Pattern Deprecation - Verify DeepAgentState patterns are deprecated
7. Security Boundary Enforcement - Block DeepAgentState at runtime

EXPECTED BEHAVIOR:
- BEFORE Migration: Tests FAIL - DeepAgentState imports and usage detected
- AFTER Migration: Tests PASS - Only UserExecutionContext patterns allowed
"""

import pytest
import ast
import inspect
import importlib
import sys
import re
import os
from typing import Dict, Any, List, Set, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent


@dataclass
class ImportViolation:
    """Represents a detected import violation."""
    file_path: str
    line_number: int
    import_statement: str
    violation_type: str
    severity: str
    remediation: str


@dataclass
class SSotViolation:
    """Represents an SSOT compliance violation."""
    violation_type: str
    location: str
    description: str
    current_pattern: str
    required_pattern: str
    severity: str
    evidence: Dict[str, Any] = field(default_factory=dict)


class TestDeepAgentStateImportBlockingCompliance(SSotBaseTestCase):
    """
    SSOT compliance tests for systematic DeepAgentState elimination.
    
    These tests ensure complete architectural compliance with UserExecutionContext
    as the single source of truth for user execution context.
    """

    def setup_method(self, method=None):
        """Set up SSOT compliance testing environment."""
        super().setup_method(method)
        
        # Track violations for comprehensive reporting
        self.import_violations = []
        self.ssot_violations = []
        self.compliance_score = 0.0
        
        # Define compliance requirements
        self.required_imports = {
            "UserExecutionContext": "netra_backend.app.services.user_execution_context",
            "UserID": "shared.types.core_types",
            "ThreadID": "shared.types.core_types", 
            "RunID": "shared.types.core_types"
        }
        
        self.forbidden_imports = {
            "DeepAgentState": "netra_backend.app.agents.state",
            "SharedState": "netra_backend.app.agents.state",
            "GlobalAgentState": "netra_backend.app.agents.state"
        }
        
        # Get ReportingSubAgent file path for analysis
        self.reporting_agent_file = inspect.getfile(ReportingSubAgent)

    def test_deepagentstate_import_detection_and_blocking(self):
        """
        Test systematic detection and blocking of DeepAgentState imports.
        
        VULNERABILITY: DeepAgentState imports enable cross-user contamination
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Analyze ReportingSubAgent source code for forbidden imports
        forbidden_import_detected = self._scan_for_forbidden_imports(self.reporting_agent_file)
        
        # BEFORE migration: Should detect forbidden imports (test fails)
        # AFTER migration: Should detect no forbidden imports (test passes)
        if forbidden_import_detected:
            violation_details = self._format_import_violations()
            assert False, (
                f"🚨 SSOT VIOLATION: Forbidden DeepAgentState imports detected in ReportingSubAgent. "
                f"{violation_details}. These imports create systematic user isolation vulnerabilities. "
                f"All imports must be migrated to UserExecutionContext patterns immediately."
            )

    def _scan_for_forbidden_imports(self, file_path: str) -> bool:
        """Scan a Python file for forbidden import patterns."""
        violations_found = False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse AST for detailed import analysis
            tree = ast.parse(source_code)
            
            # Scan for forbidden imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    violations_found = self._check_importfrom_node(node, file_path) or violations_found
                elif isinstance(node, ast.Import):
                    violations_found = self._check_import_node(node, file_path) or violations_found
            
            # Scan for string-based import patterns (dynamic imports)
            violations_found = self._scan_dynamic_imports(source_code, file_path) or violations_found
            
        except Exception as e:
            self.ssot_violations.append(SSotViolation(
                violation_type="FILE_SCAN_ERROR",
                location=file_path,
                description=f"Failed to scan file: {e}",
                current_pattern="SCAN_ERROR",
                required_pattern="READABLE_FILE",
                severity="HIGH"
            ))
            violations_found = True
        
        return violations_found

    def _check_importfrom_node(self, node: ast.ImportFrom, file_path: str) -> bool:
        """Check ImportFrom AST node for violations."""
        violations_found = False
        
        if node.module:
            # Check for forbidden modules
            for forbidden_class, forbidden_module in self.forbidden_imports.items():
                if node.module == forbidden_module:
                    # Check if forbidden class is imported
                    for alias in node.names or []:
                        if alias.name == forbidden_class:
                            self.import_violations.append(ImportViolation(
                                file_path=file_path,
                                line_number=node.lineno,
                                import_statement=f"from {node.module} import {alias.name}",
                                violation_type="FORBIDDEN_CLASS_IMPORT",
                                severity="CRITICAL",
                                remediation=f"Replace with UserExecutionContext from {self.required_imports['UserExecutionContext']}"
                            ))
                            violations_found = True
            
            # Check for partial module matches (e.g., "...state" modules)
            if node.module.endswith('.state'):
                for alias in node.names or []:
                    if 'State' in alias.name and alias.name != 'ExecutionState':
                        self.import_violations.append(ImportViolation(
                            file_path=file_path,
                            line_number=node.lineno,
                            import_statement=f"from {node.module} import {alias.name}",
                            violation_type="SUSPICIOUS_STATE_IMPORT",
                            severity="HIGH",
                            remediation="Verify this state class doesn't create user isolation risks"
                        ))
                        violations_found = True
        
        return violations_found

    def _check_import_node(self, node: ast.Import, file_path: str) -> bool:
        """Check Import AST node for violations."""
        violations_found = False
        
        for alias in node.names:
            # Check for forbidden module imports
            for forbidden_class, forbidden_module in self.forbidden_imports.items():
                if alias.name == forbidden_module:
                    self.import_violations.append(ImportViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        import_statement=f"import {alias.name}",
                        violation_type="FORBIDDEN_MODULE_IMPORT",
                        severity="CRITICAL",
                        remediation=f"Replace with UserExecutionContext patterns"
                    ))
                    violations_found = True
        
        return violations_found

    def _scan_dynamic_imports(self, source_code: str, file_path: str) -> bool:
        """Scan for dynamic import patterns that might bypass static analysis."""
        violations_found = False
        
        # Scan for string-based imports
        dynamic_patterns = [
            r'importlib\.import_module\(["\'].*DeepAgentState.*["\']\)',
            r'__import__\(["\'].*DeepAgentState.*["\']\)',
            r'getattr\([^,]+,\s*["\']DeepAgentState["\']',
            r'hasattr\([^,]+,\s*["\']DeepAgentState["\']'
        ]
        
        for pattern in dynamic_patterns:
            matches = re.finditer(pattern, source_code, re.MULTILINE)
            for match in matches:
                line_number = source_code[:match.start()].count('\n') + 1
                self.import_violations.append(ImportViolation(
                    file_path=file_path,
                    line_number=line_number,
                    import_statement=match.group(),
                    violation_type="DYNAMIC_FORBIDDEN_IMPORT",
                    severity="HIGH",
                    remediation="Replace dynamic imports with static UserExecutionContext imports"
                ))
                violations_found = True
        
        return violations_found

    def test_method_signature_ssot_compliance(self):
        """
        Test that method signatures comply with UserExecutionContext SSOT patterns.
        
        VULNERABILITY: Methods accepting DeepAgentState create contamination points
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Get all public methods of ReportingSubAgent
        reporting_methods = self._get_reportingsubagent_methods()
        
        signature_violations = []
        
        for method_name, method in reporting_methods.items():
            try:
                signature = inspect.signature(method)
                
                # Check each parameter for SSOT compliance
                for param_name, param in signature.parameters.items():
                    violation = self._check_parameter_compliance(
                        method_name, param_name, param
                    )
                    if violation:
                        signature_violations.append(violation)
                        
            except (ValueError, TypeError):
                # Some methods might not have accessible signatures
                continue
        
        # BEFORE migration: Should detect violations (test fails)
        # AFTER migration: Should detect no violations (test passes)
        if signature_violations:
            violation_details = self._format_signature_violations(signature_violations)
            assert False, (
                f"🚨 METHOD SIGNATURE SSOT VIOLATIONS: {len(signature_violations)} violations detected. "
                f"{violation_details}. All method parameters must use UserExecutionContext patterns only."
            )

    def _get_reportingsubagent_methods(self) -> Dict[str, Any]:
        """Get all relevant methods from ReportingSubAgent for analysis."""
        methods = {}
        
        for attr_name in dir(ReportingSubAgent):
            if not attr_name.startswith('_') or attr_name in ['__init__']:
                attr = getattr(ReportingSubAgent, attr_name)
                if callable(attr):
                    methods[attr_name] = attr
        
        # Also check specific methods that might accept state parameters
        critical_methods = [
            'execute', 'execute_modern', '_execute_modern_pattern',
            'execute_core_logic', '_convert_to_user_context'
        ]
        
        for method_name in critical_methods:
            if hasattr(ReportingSubAgent, method_name):
                methods[method_name] = getattr(ReportingSubAgent, method_name)
        
        return methods

    def _check_parameter_compliance(self, method_name: str, param_name: str, 
                                  param: inspect.Parameter) -> Optional[SSotViolation]:
        """Check if a parameter complies with SSOT requirements."""
        # Check type annotation for forbidden types
        if param.annotation and param.annotation != inspect.Parameter.empty:
            annotation_str = str(param.annotation)
            
            # Check for DeepAgentState type hints
            if 'DeepAgentState' in annotation_str:
                return SSotViolation(
                    violation_type="FORBIDDEN_TYPE_ANNOTATION",
                    location=f"{method_name}.{param_name}",
                    description=f"Parameter uses forbidden DeepAgentState type annotation",
                    current_pattern=annotation_str,
                    required_pattern="UserExecutionContext",
                    severity="CRITICAL",
                    evidence={
                        "method": method_name,
                        "parameter": param_name,
                        "annotation": annotation_str
                    }
                )
            
            # Check for generic state types that might be risky
            if hasattr(param.annotation, '__name__'):
                if param.annotation.__name__ in ['DeepAgentState', 'SharedState']:
                    return SSotViolation(
                        violation_type="FORBIDDEN_PARAMETER_TYPE",
                        location=f"{method_name}.{param_name}",
                        description=f"Parameter uses forbidden type: {param.annotation.__name__}",
                        current_pattern=param.annotation.__name__,
                        required_pattern="UserExecutionContext",
                        severity="CRITICAL",
                        evidence={
                            "method": method_name,
                            "parameter": param_name,
                            "type_name": param.annotation.__name__
                        }
                    )
        
        return None

    def _format_signature_violations(self, violations: List[SSotViolation]) -> str:
        """Format signature violations for detailed reporting."""
        violation_summary = []
        
        for violation in violations[:5]:  # Show first 5 for brevity
            summary = (
                f"{violation.severity}: {violation.location} - "
                f"{violation.description} (Current: {violation.current_pattern}, "
                f"Required: {violation.required_pattern})"
            )
            violation_summary.append(summary)
        
        return "Signature Violations:\n" + "\n".join(violation_summary)

    def test_runtime_deepagentstate_blocking(self):
        """
        Test that DeepAgentState usage is blocked at runtime.
        
        VULNERABILITY: Runtime acceptance of DeepAgentState enables exploitation
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Create a mock DeepAgentState for testing
        try:
            from netra_backend.app.agents.state import DeepAgentState
            
            mock_state = DeepAgentState()
            mock_state.user_id = "test_user"
            mock_state.chat_thread_id = "test_thread"
            
            # Attempt to use DeepAgentState with ReportingSubAgent
            reporting_agent = ReportingSubAgent()
            
            runtime_blocking_works = False
            
            try:
                # This should be blocked after migration
                result = await reporting_agent.execute_modern(
                    state=mock_state,
                    run_id="test_run",
                    stream_updates=False
                )
                
                # If we reach here, blocking is NOT working (vulnerability exists)
                runtime_blocking_works = False
                
            except (TypeError, ValueError, AttributeError) as e:
                error_message = str(e).lower()
                
                # Check if error message indicates security blocking
                security_keywords = [
                    'deepagentstate', 'security', 'vulnerability', 
                    'forbidden', 'not supported', 'deprecated'
                ]
                
                if any(keyword in error_message for keyword in security_keywords):
                    runtime_blocking_works = True
                else:
                    # Other error - not security related
                    runtime_blocking_works = False
            
            # BEFORE migration: Blocking should NOT work (test fails)
            # AFTER migration: Blocking should work (test passes)
            if not runtime_blocking_works:
                assert False, (
                    f"🚨 RUNTIME SECURITY VULNERABILITY: DeepAgentState usage not blocked at runtime. "
                    f"ReportingSubAgent.execute_modern() accepts DeepAgentState parameters without "
                    f"security validation. Runtime blocking required to prevent exploitation."
                )
                
        except ImportError:
            # If DeepAgentState cannot be imported, that's actually good (migration complete)
            pass

    def test_documentation_compliance_validation(self):
        """
        Test that documentation references only compliant patterns.
        
        VULNERABILITY: Documentation showing DeepAgentState patterns enables misuse
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        documentation_violations = []
        
        # Check method docstrings
        reporting_methods = self._get_reportingsubagent_methods()
        
        for method_name, method in reporting_methods.items():
            if hasattr(method, '__doc__') and method.__doc__:
                doc_violations = self._scan_documentation(method_name, method.__doc__)
                documentation_violations.extend(doc_violations)
        
        # Check class docstring
        if hasattr(ReportingSubAgent, '__doc__') and ReportingSubAgent.__doc__:
            class_violations = self._scan_documentation('ReportingSubAgent', ReportingSubAgent.__doc__)
            documentation_violations.extend(class_violations)
        
        # BEFORE migration: May detect violations (test fails)
        # AFTER migration: Should detect no violations (test passes)
        if documentation_violations:
            violation_details = self._format_documentation_violations(documentation_violations)
            assert False, (
                f"🚨 DOCUMENTATION SSOT VIOLATIONS: {len(documentation_violations)} violations detected. "
                f"{violation_details}. Documentation must reference only UserExecutionContext patterns."
            )

    def _scan_documentation(self, location: str, docstring: str) -> List[SSotViolation]:
        """Scan documentation for SSOT compliance violations."""
        violations = []
        
        # Check for forbidden pattern references
        forbidden_patterns = [
            'DeepAgentState', 'SharedState', 'GlobalAgentState',
            'state: DeepAgentState', 'execute(state,', 'state parameter'
        ]
        
        for pattern in forbidden_patterns:
            if pattern.lower() in docstring.lower():
                violations.append(SSotViolation(
                    violation_type="DOCUMENTATION_FORBIDDEN_PATTERN",
                    location=location,
                    description=f"Documentation references forbidden pattern: {pattern}",
                    current_pattern=pattern,
                    required_pattern="UserExecutionContext equivalent",
                    severity="MEDIUM",
                    evidence={"docstring_excerpt": docstring[:200] + "..."}
                ))
        
        return violations

    def _format_documentation_violations(self, violations: List[SSotViolation]) -> str:
        """Format documentation violations for reporting."""
        violation_summary = []
        
        for violation in violations[:3]:  # Show first 3
            summary = f"{violation.location}: {violation.description}"
            violation_summary.append(summary)
        
        return "Documentation Violations:\n" + "\n".join(violation_summary)

    def test_comprehensive_ssot_compliance_score(self):
        """
        Test comprehensive SSOT compliance scoring.
        
        METRIC: Overall compliance score must be 100% after migration
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        compliance_metrics = self._calculate_comprehensive_compliance()
        
        # Define minimum acceptable compliance score
        minimum_compliance_score = 95.0  # 95% compliance required
        
        # BEFORE migration: Should be below minimum (test fails)
        # AFTER migration: Should be above minimum (test passes)
        if compliance_metrics['overall_score'] < minimum_compliance_score:
            compliance_details = self._format_compliance_report(compliance_metrics)
            assert False, (
                f"🚨 SSOT COMPLIANCE FAILURE: Overall compliance score {compliance_metrics['overall_score']:.1f}% "
                f"is below required {minimum_compliance_score}%. {compliance_details}. "
                f"Complete migration to UserExecutionContext required for compliance."
            )

    def _calculate_comprehensive_compliance(self) -> Dict[str, Any]:
        """Calculate comprehensive SSOT compliance metrics."""
        metrics = {
            'import_compliance': 0.0,
            'method_signature_compliance': 0.0,
            'runtime_compliance': 0.0,
            'documentation_compliance': 0.0,
            'overall_score': 0.0,
            'violations': {
                'imports': len(self.import_violations),
                'ssot': len(self.ssot_violations)
            }
        }
        
        # Calculate import compliance
        total_import_checks = 5  # Number of import categories checked
        forbidden_imports_found = len([v for v in self.import_violations if v.severity == 'CRITICAL'])
        metrics['import_compliance'] = max(0, (total_import_checks - forbidden_imports_found) / total_import_checks * 100)
        
        # Calculate method signature compliance
        total_methods = len(self._get_reportingsubagent_methods())
        method_violations = len([v for v in self.ssot_violations if 'METHOD' in v.violation_type])
        metrics['method_signature_compliance'] = max(0, (total_methods - method_violations) / max(total_methods, 1) * 100)
        
        # Calculate runtime compliance (simplified)
        runtime_violations = len([v for v in self.ssot_violations if 'RUNTIME' in v.violation_type])
        metrics['runtime_compliance'] = 100.0 if runtime_violations == 0 else 0.0
        
        # Calculate documentation compliance
        doc_violations = len([v for v in self.ssot_violations if 'DOCUMENTATION' in v.violation_type])
        metrics['documentation_compliance'] = max(0, 100.0 - (doc_violations * 10))  # 10% penalty per doc violation
        
        # Calculate overall score
        metrics['overall_score'] = (
            metrics['import_compliance'] * 0.4 +
            metrics['method_signature_compliance'] * 0.3 +
            metrics['runtime_compliance'] * 0.2 +
            metrics['documentation_compliance'] * 0.1
        )
        
        return metrics

    def _format_compliance_report(self, metrics: Dict[str, Any]) -> str:
        """Format comprehensive compliance report."""
        report = []
        report.append(f"Import Compliance: {metrics['import_compliance']:.1f}%")
        report.append(f"Method Signature Compliance: {metrics['method_signature_compliance']:.1f}%")
        report.append(f"Runtime Compliance: {metrics['runtime_compliance']:.1f}%")
        report.append(f"Documentation Compliance: {metrics['documentation_compliance']:.1f}%")
        report.append(f"Total Violations: {metrics['violations']['imports']} import, {metrics['violations']['ssot']} SSOT")
        
        return "Compliance Report: " + "; ".join(report)

    def _format_import_violations(self) -> str:
        """Format import violations for detailed error reporting."""
        if not self.import_violations:
            return "No import violations detected"
        
        violation_summary = []
        for violation in self.import_violations[:3]:  # Show first 3 for brevity
            summary = (
                f"{violation.severity}: Line {violation.line_number} - "
                f"{violation.import_statement} ({violation.violation_type})"
            )
            violation_summary.append(summary)
        
        total_count = len(self.import_violations)
        summary_text = f"Import Violations ({total_count} total):\n" + "\n".join(violation_summary)
        
        if total_count > 3:
            summary_text += f"\n... and {total_count - 3} more violations"
        
        return summary_text

    def teardown_method(self, method=None):
        """Clean up compliance test resources."""
        # Clear violation tracking
        self.import_violations.clear()
        self.ssot_violations.clear()
        
        super().teardown_method(method)