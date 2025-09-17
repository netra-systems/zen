#!/usr/bin/env python3
"""
SSOT WebSocket Factory Dual Pattern Detection Tests - Issue #1103

TEST STRATEGY: These tests are designed to FAIL initially to detect the critical
SSOT violation in AgentInstanceFactory where both WebSocketManager and 
AgentWebSocketBridge patterns coexist, then PASS after remediation.

CRITICAL BUSINESS IMPACT:
- Revenue Protection: $500K+ ARR Golden Path WebSocket functionality  
- User Experience: Dual patterns cause race conditions and event delivery failures
- System Stability: Factory fragmentation undermines user isolation
- SSOT Compliance: Dual patterns violate Single Source of Truth architecture

DUAL PATTERN VIOLATION DETECTED:
In netra_backend/app/agents/supervisor/agent_instance_factory.py:
- Line 46: from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
- Line 41: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
- Line 48: from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge

This creates factory fragmentation where some code paths use direct WebSocketManager
while others use the SSOT AgentWebSocketBridge pattern, leading to inconsistent
WebSocket event delivery and potential user isolation failures.

EXPECTED BEHAVIOR:
- INITIAL STATE: All tests FAIL (detecting dual pattern violation)  
- POST-REMEDIATION: All tests PASS (SSOT compliance achieved)

Created: 2025-09-14
Priority: P0 Mission Critical
GitHub Issue: #1103 SSOT WebSocket Factory Fragmentation
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.unit
class WebSocketFactoryDualPatternDetectionTests(SSotBaseTestCase):
    """
    SSOT violation detection tests for dual WebSocket patterns in factories.

    These tests are designed to FAIL initially to detect current dual pattern
    violations, then PASS after remediation achieves SSOT compliance.
    """

    def setup_method(self, method=None):
        """Setup dual pattern detection test environment."""
        super().setup_method(method)

        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"
        self.agent_instance_factory_path = (
            self.netra_backend_root / "app" / "agents" / "supervisor" / "agent_instance_factory.py"
        )

        # Expected SSOT patterns (SHOULD BE THE ONLY ONES USED)
        self.ssot_websocket_patterns = [
            "from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge",
            "from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge",
        ]

        # Violation patterns (SHOULD BE ELIMINATED)
        self.dual_pattern_violations = [
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
            "from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager",
            "WebSocketManager(",
        ]

        # Critical factory files to validate
        self.critical_factory_files = [
            self.agent_instance_factory_path,
            self.netra_backend_root / "app" / "agents" / "supervisor" / "execution_engine_factory.py",
            self.netra_backend_root / "app" / "agents" / "tool_executor_factory.py",
        ]

    def _analyze_file_imports(self, file_path: Path) -> Tuple[List[str], List[str]]:
        """
        Analyze a Python file for WebSocket-related imports.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            Tuple[List[str], List[str]]: (ssot_imports, violation_imports)
        """
        if not file_path.exists():
            return [], []

        ssot_imports = []
        violation_imports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for SSOT patterns
            for pattern in self.ssot_websocket_patterns:
                if pattern in content:
                    ssot_imports.append(pattern)

            # Check for violation patterns
            for pattern in self.dual_pattern_violations:
                if pattern in content:
                    violation_imports.append(pattern)

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

        return ssot_imports, violation_imports

    def _get_import_line_numbers(self, file_path: Path) -> Dict[str, int]:
        """
        Get line numbers for specific import patterns.

        Args:
            file_path: Path to the Python file to analyze

        Returns:
            Dict[str, int]: Mapping of import patterns to line numbers
        """
        import_lines = {}

        if not file_path.exists():
            return import_lines

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            all_patterns = self.ssot_websocket_patterns + self.dual_pattern_violations

            for line_num, line in enumerate(lines, 1):
                for pattern in all_patterns:
                    if pattern in line.strip():
                        import_lines[pattern] = line_num

        except Exception as e:
            print(f"Error getting line numbers from {file_path}: {e}")

        return import_lines

    def test_agent_instance_factory_dual_websocket_pattern_violation(self):
        """
        TEST FAILS: AgentInstanceFactory contains both WebSocketManager and AgentWebSocketBridge imports.

        CRITICAL SSOT VIOLATION: Dual WebSocket access patterns in single factory violate 
        Single Source of Truth principle and create race condition risks.

        BUSINESS IMPACT: Factory fragmentation causes WebSocket event delivery failures,
        directly threatening $500K+ ARR Golden Path user experience reliability.

        EXPECTED FAILURE: Both direct WebSocketManager and AgentWebSocketBridge patterns found.
        PASSES AFTER: Only AgentWebSocketBridge SSOT pattern remains.
        """
        file_path = self.agent_instance_factory_path

        # Verify factory file exists
        self.assertTrue(file_path.exists(), 
            f"CRITICAL: AgentInstanceFactory not found at {file_path}")

        # Analyze imports
        ssot_imports, violation_imports = self._analyze_file_imports(file_path)
        import_lines = self._get_import_line_numbers(file_path)

        print(f"\n=== DUAL PATTERN ANALYSIS - {file_path.name} ===")
        print(f"SSOT Imports Found: {len(ssot_imports)}")
        for imp in ssot_imports:
            line_num = import_lines.get(imp, "?")
            print(f"  ✅ Line {line_num}: {imp}")

        print(f"\nViolation Imports Found: {len(violation_imports)}")
        for imp in violation_imports:
            line_num = import_lines.get(imp, "?")
            print(f"  ❌ Line {line_num}: {imp}")

        # CRITICAL ASSERTION: This should FAIL initially (dual pattern detected)
        if ssot_imports and violation_imports:
            # Dual pattern detected - this is the SSOT violation we're testing for
            violation_details = f"""
SSOT VIOLATION DETECTED: Dual WebSocket patterns in AgentInstanceFactory

SSOT Compliant Imports ({len(ssot_imports)}):
{chr(10).join(f"  Line {import_lines.get(imp, '?')}: {imp}" for imp in ssot_imports)}

VIOLATION Imports ({len(violation_imports)}):
{chr(10).join(f"  Line {import_lines.get(imp, '?')}: {imp}" for imp in violation_imports)}

BUSINESS IMPACT:
- WebSocket event delivery inconsistency
- User isolation race conditions  
- Golden Path reliability threatened ($500K+ ARR)

REMEDIATION REQUIRED:
1. Remove direct WebSocketManager imports (lines with violations)
2. Use only AgentWebSocketBridge SSOT pattern
3. Update all factory methods to use bridge exclusively

This test will PASS after dual pattern elimination.
"""
            print(violation_details)
            
            # This assertion should FAIL initially, PASS after remediation
            assert False, (f"SSOT VIOLATION: Dual WebSocket patterns detected in AgentInstanceFactory. "
                          f"Found {len(ssot_imports)} SSOT imports AND {len(violation_imports)} violation imports. "
                          f"See details above for remediation guidance.")

        elif violation_imports and not ssot_imports:
            # Only violations, no SSOT - still a failure
            assert False, f"CRITICAL: Only violation patterns found, no SSOT compliance detected. "\
                     f"Violations: {violation_imports}"

        elif ssot_imports and not violation_imports:
            # Only SSOT patterns - this is success state after remediation
            print(f"\n✅ SSOT COMPLIANCE ACHIEVED: Only canonical imports found")
            print(f"✅ Dual pattern violation eliminated")
            print(f"✅ AgentInstanceFactory follows SSOT WebSocket patterns")
            
            # Additional validation that factory is truly SSOT compliant
            self.assertGreater(len(ssot_imports), 0, "SSOT imports should be present")
            
        else:
            # No WebSocket imports at all - this might indicate an issue
            assert False, "UNEXPECTED: No WebSocket imports found in AgentInstanceFactory. "\
                     "Factory should have SSOT AgentWebSocketBridge imports."

    def test_factory_methods_use_single_websocket_access_pattern(self):
        """
        TEST FAILS: Factory methods use inconsistent WebSocket access patterns.

        BUSINESS IMPACT: Inconsistent patterns cause WebSocket event delivery failures,
        directly impacting $500K+ ARR Golden Path user experience.

        EXPECTED FAILURE: Factory contains mixed WebSocket access patterns.
        PASSES AFTER: All methods use AgentWebSocketBridge exclusively.
        """
        file_path = self.agent_instance_factory_path

        if not file_path.exists():
            assert False, f"CRITICAL: Factory file not found at {file_path}"

        # Read file content for pattern analysis
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            assert False, (f"Error reading factory file: {e}")

        # Analyze method-level WebSocket usage patterns
        websocket_manager_usage = []
        websocket_bridge_usage = []

        # Pattern detection for method usage
        manager_patterns = [
            r"self\._websocket_manager",
            r"websocket_manager\s*=.*WebSocketManager",
            r"WebSocketManager\s*\(",
            r"\.websocket_manager\.",
        ]

        bridge_patterns = [
            r"self\._websocket_bridge",
            r"websocket_bridge\s*=.*AgentWebSocketBridge", 
            r"AgentWebSocketBridge\s*\(",
            r"create_agent_websocket_bridge\s*\(",
        ]

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for WebSocketManager usage patterns
            for pattern in manager_patterns:
                if re.search(pattern, line_stripped):
                    websocket_manager_usage.append((line_num, pattern, line_stripped))
            
            # Check for WebSocket bridge usage patterns  
            for pattern in bridge_patterns:
                if re.search(pattern, line_stripped):
                    websocket_bridge_usage.append((line_num, pattern, line_stripped))

        print(f"\n=== METHOD PATTERN ANALYSIS - {file_path.name} ===")
        print(f"WebSocketManager usage patterns: {len(websocket_manager_usage)}")
        for line_num, pattern, line in websocket_manager_usage[:5]:  # Limit output
            print(f"  ❌ Line {line_num}: {line[:80]}...")

        print(f"\nWebSocket bridge usage patterns: {len(websocket_bridge_usage)}")
        for line_num, pattern, line in websocket_bridge_usage[:5]:  # Limit output
            print(f"  ✅ Line {line_num}: {line[:80]}...")

        # CRITICAL ASSERTION: Check for mixed patterns (should FAIL initially)
        if websocket_manager_usage and websocket_bridge_usage:
            # Mixed patterns detected - SSOT violation
            violation_summary = f"""
MIXED WEBSOCKET PATTERNS DETECTED in Factory Methods

Direct WebSocketManager Usage: {len(websocket_manager_usage)} occurrences
SSOT Bridge Usage: {len(websocket_bridge_usage)} occurrences  

BUSINESS IMPACT:
- Inconsistent event delivery behavior
- Race conditions between different access patterns
- User isolation failures
- Golden Path reliability issues ($500K+ ARR)

REMEDIATION:
- Eliminate all direct WebSocketManager usage
- Convert to AgentWebSocketBridge pattern exclusively
- Ensure consistent factory method behavior
"""
            print(violation_summary)
            
            assert False, (f"MIXED PATTERNS VIOLATION: Factory methods use both direct WebSocketManager "
                     f"({len(websocket_manager_usage)} usages) AND bridge patterns "
                     f"({len(websocket_bridge_usage)} usages). SSOT requires single access pattern.")

        elif websocket_manager_usage and not websocket_bridge_usage:
            # Only manager usage - violation, needs bridge pattern
            assert False, (f"SSOT VIOLATION: Factory uses only direct WebSocketManager patterns "
                     f"({len(websocket_manager_usage)} usages). Must use AgentWebSocketBridge SSOT pattern.")

        elif websocket_bridge_usage and not websocket_manager_usage:
            # Only bridge usage - this is the success state
            print(f"\n✅ CONSISTENT PATTERN ACHIEVED: Only bridge patterns found")
            print(f"✅ Factory methods use SSOT AgentWebSocketBridge exclusively") 
            print(f"✅ No direct WebSocketManager usage detected")
            
            self.assertGreater(len(websocket_bridge_usage), 0, "Bridge usage should be present")
            
        else:
            # No WebSocket usage patterns found - might indicate issue
            assert False, ("UNEXPECTED: No WebSocket usage patterns found in factory methods. "
                     "Factory should have bridge pattern usage.")

    def test_factory_runtime_websocket_pattern_consistency(self):
        """
        TEST FAILS: Factory creates instances with inconsistent WebSocket access patterns.

        SSOT REQUIREMENT: All factory-created instances must use identical WebSocket
        access patterns for user isolation and event delivery consistency.

        EXPECTED FAILURE: Factory initialization uses mixed patterns.  
        PASSES AFTER: All initialization uses unified WebSocket bridge pattern.
        """
        file_path = self.agent_instance_factory_path

        if not file_path.exists():
            assert False, f"CRITICAL: Factory file not found at {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            assert False, (f"Error reading factory file: {e}")

        # Analyze factory initialization patterns
        initialization_patterns = {
            'websocket_manager': [],
            'websocket_bridge': [],
            'mixed_initialization': []
        }

        lines = content.splitlines()
        in_init_method = False
        in_configure_method = False
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Track method context
            if 'def __init__(' in line_stripped or 'def configure(' in line_stripped:
                in_init_method = True
                in_configure_method = True
                continue
            elif line_stripped.startswith('def ') and (in_init_method or in_configure_method):
                in_init_method = False
                in_configure_method = False
                continue
            
            # Analyze initialization patterns within relevant methods
            if in_init_method or in_configure_method:
                # Check for WebSocketManager initialization
                if re.search(r'self\._websocket_manager.*=', line_stripped) or \
                   re.search(r'websocket_manager.*=.*WebSocketManager', line_stripped):
                    initialization_patterns['websocket_manager'].append((line_num, line_stripped))
                
                # Check for WebSocket bridge initialization
                if re.search(r'self\._websocket_bridge.*=', line_stripped) or \
                   re.search(r'websocket_bridge.*=.*AgentWebSocketBridge', line_stripped) or \
                   re.search(r'websocket_bridge.*=.*create_agent_websocket_bridge', line_stripped):
                    initialization_patterns['websocket_bridge'].append((line_num, line_stripped))
                
                # Check for mixed initialization in same method
                if ('websocket_manager' in line_stripped and 'websocket_bridge' in line_stripped):
                    initialization_patterns['mixed_initialization'].append((line_num, line_stripped))

        print(f"\n=== FACTORY INITIALIZATION ANALYSIS - {file_path.name} ===")
        print(f"WebSocketManager initialization: {len(initialization_patterns['websocket_manager'])}")
        for line_num, line in initialization_patterns['websocket_manager']:
            print(f"  ❌ Line {line_num}: {line[:80]}...")
            
        print(f"\nWebSocket bridge initialization: {len(initialization_patterns['websocket_bridge'])}")
        for line_num, line in initialization_patterns['websocket_bridge']:
            print(f"  ✅ Line {line_num}: {line[:80]}...")
            
        print(f"\nMixed initialization patterns: {len(initialization_patterns['mixed_initialization'])}")
        for line_num, line in initialization_patterns['mixed_initialization']:
            print(f"  ⚠️  Line {line_num}: {line[:80]}...")

        # CRITICAL ASSERTION: Check initialization consistency
        manager_init = initialization_patterns['websocket_manager']
        bridge_init = initialization_patterns['websocket_bridge']
        mixed_init = initialization_patterns['mixed_initialization']

        if (manager_init and bridge_init) or mixed_init:
            # Inconsistent initialization - SSOT violation
            violation_summary = f"""
INCONSISTENT FACTORY INITIALIZATION DETECTED

WebSocketManager Initialization: {len(manager_init)} patterns
Bridge Initialization: {len(bridge_init)} patterns
Mixed Patterns: {len(mixed_init)} patterns

RUNTIME IMPACT:
- Factory creates instances with different WebSocket access patterns
- Race conditions during instance creation
- Unpredictable event delivery behavior
- User isolation compromised

SSOT REQUIREMENT VIOLATION:
Factory must use single, consistent initialization pattern for all instances.
"""
            print(violation_summary)
            
            assert False, (f"INITIALIZATION INCONSISTENCY: Factory uses mixed WebSocket initialization patterns. "
                     f"Manager: {len(manager_init)}, Bridge: {len(bridge_init)}, Mixed: {len(mixed_init)}. "
                     f"SSOT requires consistent pattern.")

        elif manager_init and not bridge_init:
            # Only manager initialization - violation
            assert False, (f"SSOT VIOLATION: Factory initialization uses only WebSocketManager pattern "
                     f"({len(manager_init)} occurrences). Must use AgentWebSocketBridge SSOT pattern.")

        elif bridge_init and not manager_init:
            # Only bridge initialization - success state
            print(f"\n✅ CONSISTENT INITIALIZATION: Only bridge pattern found")
            print(f"✅ Factory creates instances with consistent WebSocket access")
            print(f"✅ SSOT compliance in runtime behavior achieved")
            
            self.assertGreater(len(bridge_init), 0, "Bridge initialization should be present")
            
        else:
            # No initialization patterns found
            # For AgentInstanceFactory, this might be acceptable if it doesn't directly initialize WebSocket components
            print(f"\n⚠️ NO WEBSOCKET INITIALIZATION: Factory may delegate WebSocket setup to other components")
            print(f"This may be acceptable if WebSocket setup is properly delegated")
            
            # This is not necessarily a failure - just document the finding
            pass

    def test_websocket_factory_ssot_remediation_complete(self):
        """
        TEST FAILS: WebSocket factory fragmentation SSOT violation not fully remediated.

        MISSION CRITICAL: This test validates Issue #1103 complete resolution and
        ensures no regression back to dual pattern violations.

        EXPECTED FAILURE: SSOT violations still detected in factory.
        PASSES AFTER: Complete SSOT compliance achieved.
        """
        file_path = self.agent_instance_factory_path

        if not file_path.exists():
            assert False, (f"CRITICAL: AgentInstanceFactory not found at {file_path}")

        # Comprehensive SSOT compliance check
        ssot_imports, violation_imports = self._analyze_file_imports(file_path)
        import_lines = self._get_import_line_numbers(file_path)

        # Additional checks for complete remediation
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            assert False, (f"Error reading factory file: {e}")

        # Check for any remaining violation patterns in comments or strings
        violation_in_comments = []
        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            if ('websocket_manager' in line_lower and 
                'websocketmanager' in line and
                'bridge' not in line_lower):
                violation_in_comments.append((line_num, line.strip()))

        print(f"\n=== COMPLETE SSOT REMEDIATION VALIDATION - {file_path.name} ===")
        print(f"Import Analysis:")
        print(f"  SSOT Compliant Imports: {len(ssot_imports)}")
        print(f"  Violation Imports: {len(violation_imports)}")
        print(f"  Potential violations in content: {len(violation_in_comments)}")

        # REMEDIATION COMPLETENESS CHECK
        remediation_issues = []
        
        if violation_imports:
            remediation_issues.append(f"Direct WebSocketManager imports still present: {violation_imports}")
            
        if violation_in_comments:
            issue_lines = [f"Line {line_num}: {line}" for line_num, line in violation_in_comments[:3]]
            remediation_issues.append(f"Potential WebSocketManager references in content: {issue_lines}")
            
        if not ssot_imports:
            remediation_issues.append("No SSOT AgentWebSocketBridge imports detected")

        if remediation_issues:
            # Remediation not complete - test should FAIL
            remediation_summary = f"""
ISSUE #1103 REMEDIATION INCOMPLETE

Issues Found:
{chr(10).join(f"  - {issue}" for issue in remediation_issues)}

COMPLETE REMEDIATION REQUIRES:
1. Remove all direct WebSocketManager imports  
2. Ensure AgentWebSocketBridge imports are present
3. Clean up any remaining WebSocketManager references
4. Validate all usage patterns use bridge exclusively

BUSINESS IMPACT: Incomplete remediation leaves system vulnerable to:
- WebSocket event delivery inconsistencies  
- User isolation race conditions
- Golden Path reliability issues ($500K+ ARR)

This test will PASS when Issue #1103 is fully resolved.
"""
            print(remediation_summary)
            
            assert False, (f"REMEDIATION INCOMPLETE: Issue #1103 not fully resolved. "
                     f"{len(remediation_issues)} remaining issues: {remediation_issues}")

        else:
            # Complete remediation achieved - success state
            print(f"\n🎉 ISSUE #1103 REMEDIATION COMPLETE")
            print(f"✅ All direct WebSocketManager imports eliminated")  
            print(f"✅ SSOT AgentWebSocketBridge pattern implemented")
            print(f"✅ No remaining violation patterns detected")
            print(f"✅ Factory fragmentation SSOT violation resolved")
            
            # Validate positive indicators of success
            self.assertGreater(len(ssot_imports), 0, "SSOT imports should be present after remediation")
            self.assertEqual(len(violation_imports), 0, "No violation imports should remain")
            
            print(f"\n🏆 BUSINESS VALUE PROTECTED:")
            print(f"  - $500K+ ARR Golden Path WebSocket functionality secured")
            print(f"  - User isolation race conditions eliminated") 
            print(f"  - Event delivery consistency ensured")
            print(f"  - SSOT architecture compliance maintained")

    def test_websocket_manager_direct_import_eliminated(self):
        """
        Validate that direct WebSocketManager imports are eliminated from AgentInstanceFactory.

        Static analysis test ensuring SSOT compliance through import pattern validation.
        This test should PASS immediately after remediation.
        """
        file_path = self.agent_instance_factory_path

        if not file_path.exists():
            assert False, (f"CRITICAL: AgentInstanceFactory not found at {file_path}")

        # Static import analysis using AST parsing for precision
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST to get exact import information
            tree = ast.parse(content)
        except Exception as e:
            assert False, (f"Error parsing factory file: {e}")

        direct_websocket_imports = []
        ssot_bridge_imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and 'websocket_core.websocket_manager' in node.module:
                    for alias in node.names:
                        if alias.name == 'WebSocketManager':
                            direct_websocket_imports.append({
                                'module': node.module,
                                'name': alias.name,
                                'line': node.lineno
                            })
                
                elif node.module and 'agent_websocket_bridge' in node.module:
                    for alias in node.names:
                        if alias.name in ['AgentWebSocketBridge', 'create_agent_websocket_bridge']:
                            ssot_bridge_imports.append({
                                'module': node.module, 
                                'name': alias.name,
                                'line': node.lineno
                            })

        print(f"\n=== STATIC IMPORT ANALYSIS - {file_path.name} ===")
        print(f"Direct WebSocketManager imports: {len(direct_websocket_imports)}")
        for imp in direct_websocket_imports:
            print(f"  ❌ Line {imp['line']}: from {imp['module']} import {imp['name']}")
        
        print(f"\nSSOT Bridge imports: {len(ssot_bridge_imports)}")
        for imp in ssot_bridge_imports:
            print(f"  ✅ Line {imp['line']}: from {imp['module']} import {imp['name']}")

        # Validation assertions
        if direct_websocket_imports:
            import_details = [f"Line {imp['line']}: {imp['module']}.{imp['name']}" 
                             for imp in direct_websocket_imports]
            
            assert False, (f"DIRECT IMPORT VIOLATION: WebSocketManager imports still present. "
                     f"Found {len(direct_websocket_imports)} violations: {import_details}. "
                     f"Must be eliminated for SSOT compliance.")

        # Ensure SSOT imports are present (factory should use bridge pattern)
        self.assertGreater(len(ssot_bridge_imports), 0,
            "SSOT AgentWebSocketBridge imports should be present for proper factory pattern")

        print(f"\n✅ STATIC ANALYSIS PASSED:")
        print(f"  - No direct WebSocketManager imports detected")  
        print(f"  - SSOT AgentWebSocketBridge imports present ({len(ssot_bridge_imports)})")
        print(f"  - Import pattern SSOT compliance achieved")


if __name__ == '__main__':
    # Run as standalone test with detailed output for Issue #1103 validation
    import unittest
    
    print("SSOT WebSocket Factory Dual Pattern Detection - Issue #1103")
    print("=" * 65)
    print("Testing for dual WebSocket pattern violations in AgentInstanceFactory")
    print("EXPECTED: Tests FAIL initially, PASS after remediation\n")
    
    # Run the test suite
    unittest.main(argv=[''], verbosity=2, exit=False)
    
    print("\n" + "=" * 65)
    print("REMEDIATION GUIDANCE:")
    print("1. Remove direct WebSocketManager imports from AgentInstanceFactory")
    print("2. Ensure only AgentWebSocketBridge SSOT pattern is used")
    print("3. Update all factory methods to use bridge exclusively") 
    print("4. Validate tests PASS after changes")
    print("5. Add to mission critical regression suite")
    print("=" * 65)