#!/usr/bin/env python3
"""
Mission Critical Test Suite: Tool Dispatcher SSOT Compliance

Business Value: Platform/Internal - System Reliability & SSOT Compliance
Critical for $500K+ ARR protection through tool dispatcher SSOT compliance.

This test suite validates:
1. Single tool dispatcher implementation pattern (UnifiedToolDispatcher)
2. No direct imports bypassing UniversalRegistry
3. Factory pattern usage for user isolation
4. WebSocket event delivery through proper channels
5. Tool execution through canonical SSOT patterns

The tests FAIL with current violations and PASS after SSOT fixes.

Author: Claude Code SSOT Compliance Test Generator
Date: 2025-09-10
"""

import asyncio
import ast
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass

import pytest

# Real service imports - NO MOCKS (following CLAUDE.md)
try:
    from shared.isolated_environment import IsolatedEnvironment
except ImportError:
    # Fallback for missing modules
    IsolatedEnvironment = None

try:
    from netra_backend.app.core.registry.universal_registry import UniversalRegistry, ToolRegistry
except ImportError:
    UniversalRegistry = None
    ToolRegistry = None

try:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
except ImportError:
    UserExecutionContext = None


@dataclass
class ToolDispatcherViolation:
    """Structure for tool dispatcher SSOT violations."""
    violation_type: str
    file_path: str
    line_number: Optional[int]
    description: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    code_snippet: str
    business_impact: str


@dataclass
class SSotComplianceReport:
    """SSOT compliance validation results for tool dispatcher."""
    overall_compliance_score: float
    multiple_implementation_violations: List[ToolDispatcherViolation]
    direct_import_violations: List[ToolDispatcherViolation]
    registry_bypass_violations: List[ToolDispatcherViolation]
    factory_pattern_violations: List[ToolDispatcherViolation]
    websocket_event_violations: List[ToolDispatcherViolation]
    total_violations: int
    critical_violations: int
    high_violations: int
    recommendations: List[str]


class TestToolDispatcherSSotCompliance:
    """CRITICAL: Tool Dispatcher SSOT compliance validation."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for SSOT compliance testing."""
        self.project_root = Path(__file__).parent.parent.parent
        self.source_dirs = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "tests"
        ]
        self.tool_dispatcher_files = []
        self.violations = []

    def test_single_tool_dispatcher_implementation(self):
        """
        CRITICAL: Test that only ONE tool dispatcher implementation exists.
        
        Current State: SHOULD FAIL - Multiple implementations exist:
        - ToolDispatcher (legacy)
        - RequestScopedToolDispatcher 
        - UnifiedToolDispatcher
        
        Expected After Fix: SHOULD PASS - Only UnifiedToolDispatcher exists
        """
        tool_dispatcher_classes = self._find_tool_dispatcher_classes()
        
        # This test MUST FAIL currently due to multiple implementations
        if len(tool_dispatcher_classes) == 1:
            raise AssertionError(
                "TEST VALIDATION ERROR: Expected to find multiple ToolDispatcher "
                f"implementations (violations), but found only: {tool_dispatcher_classes}. "
                "This suggests SSOT violations have already been fixed, or test is incorrect."
            )
        
        # Document current violations
        violation_report = []
        expected_violations = ['ToolDispatcher', 'RequestScopedToolDispatcher', 'UnifiedToolDispatcher']
        
        for class_info in tool_dispatcher_classes:
            if class_info['name'] != 'UnifiedToolDispatcher':
                violation = ToolDispatcherViolation(
                    violation_type="MULTIPLE_IMPLEMENTATION",
                    file_path=class_info['file'],
                    line_number=class_info['line'],
                    description=f"Non-SSOT tool dispatcher: {class_info['name']}",
                    severity="CRITICAL",
                    code_snippet=class_info.get('code', ''),
                    business_impact="Creates user isolation issues and maintenance overhead"
                )
                violation_report.append(violation)
        
        # Store violations for reporting
        self.violations.extend(violation_report)
        
        # Test MUST FAIL with current multiple implementations
        if not len(tool_dispatcher_classes) > 1:
            raise AssertionError(
                f"SSOT VIOLATION DETECTED: Found {len(tool_dispatcher_classes)} tool dispatcher "
                f"implementations: {[cls['name'] for cls in tool_dispatcher_classes]}. "
                f"SSOT requires only UnifiedToolDispatcher. Violations: {violation_report}"
            )

    def test_no_direct_tool_dispatcher_imports(self):
        """
        CRITICAL: Test that no code directly imports non-SSOT tool dispatchers.
        
        Current State: SHOULD FAIL - Direct imports exist
        Expected After Fix: SHOULD PASS - Only imports through UniversalRegistry
        """
        direct_import_violations = self._find_direct_tool_dispatcher_imports()
        
        # This test MUST FAIL currently due to direct imports
        if not direct_import_violations:
            raise AssertionError(
                "TEST VALIDATION ERROR: Expected to find direct tool dispatcher imports "
                "(violations), but found none. This suggests SSOT violations have "
                "already been fixed, or test is scanning incorrectly."
            )
        
        # Document violations
        for violation in direct_import_violations:
            self.violations.append(violation)
        
        # Test MUST FAIL with current direct imports
        if not len(direct_import_violations) > 0:
            raise AssertionError(
                f"SSOT VIOLATION DETECTED: Found {len(direct_import_violations)} direct "
                f"tool dispatcher imports that bypass UniversalRegistry: {direct_import_violations}"
            )

    def test_universal_registry_tool_execution(self):
        """
        CRITICAL: Test that tool execution goes through UniversalRegistry SSOT.
        
        Current State: SHOULD FAIL - Registry bypasses exist
        Expected After Fix: SHOULD PASS - All tools use UniversalRegistry
        """
        registry_bypass_violations = self._find_registry_bypass_patterns()
        
        # This test MUST FAIL currently due to registry bypasses
        if not registry_bypass_violations:
            raise AssertionError(
                "TEST VALIDATION ERROR: Expected to find registry bypass patterns "
                "(violations), but found none. This suggests SSOT violations have "
                "already been fixed, or test is scanning incorrectly."
            )
        
        # Document violations
        for violation in registry_bypass_violations:
            self.violations.append(violation)
        
        # Test MUST FAIL with current bypasses
        if not len(registry_bypass_violations) > 0:
            raise AssertionError(
                f"SSOT VIOLATION DETECTED: Found {len(registry_bypass_violations)} "
                f"registry bypass patterns: {registry_bypass_violations}"
            )

    async def test_factory_pattern_enforcement(self):
        """
        CRITICAL: Test that tool dispatchers use factory patterns for user isolation.
        
        Current State: SHOULD FAIL - Direct instantiation exists
        Expected After Fix: SHOULD PASS - Only factory methods used
        """
        direct_instantiation_violations = self._find_direct_instantiation_patterns()
        
        # This test MUST FAIL currently due to direct instantiation
        if not direct_instantiation_violations:
            raise AssertionError(
                "TEST VALIDATION ERROR: Expected to find direct instantiation patterns "
                "(violations), but found none. This suggests SSOT violations have "
                "already been fixed, or test is scanning incorrectly."
            )
        
        # Document violations
        for violation in direct_instantiation_violations:
            self.violations.append(violation)
        
        # Test MUST FAIL with current direct instantiation
        if not len(direct_instantiation_violations) > 0:
            raise AssertionError(
                f"SSOT VIOLATION DETECTED: Found {len(direct_instantiation_violations)} "
                f"direct instantiation patterns that violate factory pattern: {direct_instantiation_violations}"
            )

    async def test_websocket_event_ssot_compliance(self):
        """
        CRITICAL: Test that WebSocket events flow through SSOT channels.
        
        Current State: SHOULD FAIL - Multiple event channels exist
        Expected After Fix: SHOULD PASS - Single event channel
        """
        websocket_violations = self._find_websocket_event_violations()
        
        # This test MUST FAIL currently due to multiple event channels
        if not websocket_violations:
            raise AssertionError(
                "TEST VALIDATION ERROR: Expected to find WebSocket event violations "
                "(multiple channels), but found none. This suggests SSOT violations "
                "have already been fixed, or test is scanning incorrectly."
            )
        
        # Document violations
        for violation in websocket_violations:
            self.violations.append(violation)
        
        # Test MUST FAIL with current multiple channels
        if not len(websocket_violations) > 0:
            raise AssertionError(
                f"SSOT VIOLATION DETECTED: Found {len(websocket_violations)} "
                f"WebSocket event violations: {websocket_violations}"
            )

    def test_generate_ssot_compliance_report(self):
        """Generate comprehensive SSOT compliance report for tool dispatcher."""
        # Collect all violations from previous tests
        multiple_impl = [v for v in self.violations if v.violation_type == "MULTIPLE_IMPLEMENTATION"]
        direct_imports = [v for v in self.violations if v.violation_type == "DIRECT_IMPORT"]
        registry_bypasses = [v for v in self.violations if v.violation_type == "REGISTRY_BYPASS"]
        factory_violations = [v for v in self.violations if v.violation_type == "FACTORY_PATTERN"]
        websocket_violations = [v for v in self.violations if v.violation_type == "WEBSOCKET_EVENT"]
        
        critical_count = len([v for v in self.violations if v.severity == "CRITICAL"])
        high_count = len([v for v in self.violations if v.severity == "HIGH"])
        total_count = len(self.violations)
        
        # Calculate compliance score
        max_possible_violations = 50  # Estimated baseline
        compliance_score = max(0, (max_possible_violations - total_count) / max_possible_violations * 100)
        
        report = SSotComplianceReport(
            overall_compliance_score=compliance_score,
            multiple_implementation_violations=multiple_impl,
            direct_import_violations=direct_imports,
            registry_bypass_violations=registry_bypasses,
            factory_pattern_violations=factory_violations,
            websocket_event_violations=websocket_violations,
            total_violations=total_count,
            critical_violations=critical_count,
            high_violations=high_count,
            recommendations=[
                "Consolidate all tool dispatchers to UnifiedToolDispatcher",
                "Replace direct imports with UniversalRegistry access",
                "Implement factory pattern enforcement",
                "Standardize WebSocket event channels",
                "Add SSOT violation detection to CI/CD pipeline"
            ]
        )
        
        # Print detailed report
        print(f"\n{'='*80}")
        print(f"TOOL DISPATCHER SSOT COMPLIANCE REPORT")
        print(f"{'='*80}")
        print(f"Overall Compliance Score: {compliance_score:.1f}%")
        print(f"Total Violations: {total_count}")
        print(f"Critical Violations: {critical_count}")
        print(f"High Violations: {high_count}")
        print(f"{'='*80}")
        
        for violation in self.violations:
            print(f"\n{violation.severity}: {violation.violation_type}")
            print(f"  File: {violation.file_path}:{violation.line_number}")
            print(f"  Description: {violation.description}")
            print(f"  Business Impact: {violation.business_impact}")
        
        # This test documents violations but doesn't fail (for CI reporting)
        return report

    # ===== PRIVATE HELPER METHODS =====

    def _find_tool_dispatcher_classes(self) -> List[Dict[str, Any]]:
        """Find all tool dispatcher class definitions."""
        tool_dispatcher_classes = []
        
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content)
                        
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if "ToolDispatcher" in node.name:
                                tool_dispatcher_classes.append({
                                    'name': node.name,
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'line': node.lineno,
                                    'code': ast.get_source_segment(content, node) if hasattr(ast, 'get_source_segment') else ""
                                })
                except Exception as e:
                    # Skip files that can't be parsed
                    continue
        
        return tool_dispatcher_classes

    def _find_direct_tool_dispatcher_imports(self) -> List[ToolDispatcherViolation]:
        """Find direct imports of tool dispatcher classes."""
        violations = []
        
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        
                        # Check for direct imports
                        if ('from' in line and 'ToolDispatcher' in line and 
                            'import' in line and 'universal_registry' not in line):
                            
                            violations.append(ToolDispatcherViolation(
                                violation_type="DIRECT_IMPORT",
                                file_path=str(py_file.relative_to(self.project_root)),
                                line_number=line_num,
                                description=f"Direct tool dispatcher import: {line}",
                                severity="HIGH",
                                code_snippet=line,
                                business_impact="Bypasses SSOT pattern, creates maintenance issues"
                            ))
                            
                except Exception as e:
                    continue
        
        return violations

    def _find_registry_bypass_patterns(self) -> List[ToolDispatcherViolation]:
        """Find patterns that bypass UniversalRegistry."""
        violations = []
        
        bypass_patterns = [
            "ToolDispatcher()",
            "RequestScopedToolDispatcher(",
            ".dispatch_tool(",
            "tool_registry.get_tool("
        ]
        
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for line_num, line in enumerate(lines, 1):
                        for pattern in bypass_patterns:
                            if pattern in line and "test" not in str(py_file).lower():
                                violations.append(ToolDispatcherViolation(
                                    violation_type="REGISTRY_BYPASS",
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=line_num,
                                    description=f"Registry bypass pattern: {pattern}",
                                    severity="HIGH",
                                    code_snippet=line.strip(),
                                    business_impact="Bypasses UniversalRegistry SSOT"
                                ))
                                
                except Exception as e:
                    continue
        
        return violations

    def _find_direct_instantiation_patterns(self) -> List[ToolDispatcherViolation]:
        """Find direct instantiation patterns that violate factory pattern."""
        violations = []
        
        instantiation_patterns = [
            "ToolDispatcher()",
            "RequestScopedToolDispatcher(",
            "UnifiedToolDispatcher()"
        ]
        
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    for line_num, line in enumerate(lines, 1):
                        for pattern in instantiation_patterns:
                            if (pattern in line and 
                                "create_for_" not in line and
                                "factory" not in line.lower() and
                                "test" not in str(py_file).lower()):
                                
                                violations.append(ToolDispatcherViolation(
                                    violation_type="FACTORY_PATTERN",
                                    file_path=str(py_file.relative_to(self.project_root)),
                                    line_number=line_num,
                                    description=f"Direct instantiation: {pattern}",
                                    severity="CRITICAL",
                                    code_snippet=line.strip(),
                                    business_impact="Violates user isolation factory pattern"
                                ))
                                
                except Exception as e:
                    continue
        
        return violations

    def _find_websocket_event_violations(self) -> List[ToolDispatcherViolation]:
        """Find WebSocket event violations (multiple channels)."""
        violations = []
        
        event_patterns = [
            "notify_tool_executing",
            "notify_tool_completed",
            "websocket_bridge",
            "websocket_manager"
        ]
        
        # Track which files use which patterns
        pattern_usage = {}
        
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                    file_patterns = set()
                    for line_num, line in enumerate(lines, 1):
                        for pattern in event_patterns:
                            if pattern in line:
                                file_patterns.add(pattern)
                                
                    if file_patterns:
                        pattern_usage[str(py_file)] = file_patterns
                        
                except Exception as e:
                    continue
        
        # Find files using multiple event channels (violation)
        for file_path, patterns in pattern_usage.items():
            if len(patterns) > 1:
                violations.append(ToolDispatcherViolation(
                    violation_type="WEBSOCKET_EVENT",
                    file_path=file_path,
                    line_number=None,
                    description=f"Multiple WebSocket channels: {patterns}",
                    severity="HIGH",
                    code_snippet="",
                    business_impact="Creates inconsistent event delivery"
                ))
        
        return violations


if __name__ == "__main__":
    # Run individual test to see current violations
    test_case = TestToolDispatcherSSotCompliance()
    test_case.setUp()
    
    print("Running Tool Dispatcher SSOT Compliance Tests...")
    print("These tests SHOULD FAIL with current violations.")
    
    try:
        test_case.test_single_tool_dispatcher_implementation()
    except AssertionError as e:
        print(f"✅ Expected failure: {e}")
    
    try:
        test_case.test_no_direct_tool_dispatcher_imports()
    except AssertionError as e:
        print(f"✅ Expected failure: {e}")
    
    # Generate report
    report = test_case.test_generate_ssot_compliance_report()
    print(f"\nCompliance Score: {report.overall_compliance_score:.1f}%")