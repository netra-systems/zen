#!/usr/bin/env python3
"""
SSOT Agent Direct WebSocket Violation Detection Tests for Issue #1070

Tests designed to FAIL initially to detect current direct WebSocket access violations
in agent implementations and PASS after remediation. These tests enforce SSOT
compliance by detecting agents that directly access WebSocket functionality instead
of using the AgentRegistry bridge pattern for proper user isolation.

Created for GitHub Issue #1070: WebSocket bridge bypass violations - Anti-pattern detection
Part of: SSOT violation detection and prevention system

Business Value: Platform/Internal - System Stability & User Isolation
Prevents direct WebSocket access patterns that break user isolation and multi-tenancy.

DESIGN CRITERIA:
- Tests FAIL initially to prove anti-patterns exist in agent code
- Tests PASS after agents eliminate direct WebSocket access patterns
- Provides specific pattern detection and remediation guidance
- Uses SSOT test infrastructure patterns
- Focuses on runtime usage patterns vs import analysis

TEST CATEGORIES:
- Direct WebSocket manager instantiation detection
- WebSocket method call pattern analysis
- Constructor parameter violation detection
- Agent implementation anti-pattern identification

EXPECTED BEHAVIOR:
- INITIAL STATE: All primary tests FAIL (detecting direct access patterns)
- POST-REMEDIATION: All tests PASS (bridge pattern enforced exclusively)
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

import pytest

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestAgentDirectWebSocketViolations(SSotBaseTestCase):
    """
    SSOT violation detection tests for agent direct WebSocket access patterns.

    These tests are designed to FAIL initially to detect current anti-patterns,
    then PASS after remediation. They enforce AgentRegistry bridge compliance
    by detecting specific code patterns that violate user isolation.
    """

    def setup_method(self, method=None):
        """Setup agent direct WebSocket violation detection test environment."""
        super().setup_method(method)

        # Project paths
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.netra_backend_root = self.project_root / "netra_backend"
        self.agents_path = self.netra_backend_root / "app" / "agents"

        # Direct WebSocket instantiation patterns (ANTI-PATTERNS)
        self.direct_instantiation_patterns = [
            r"WebSocketManager\s*\(\s*\)",
            r"websocket_manager\s*=\s*WebSocketManager\s*\(",
            r"manager\s*=\s*get_websocket_manager\s*\(",
            r"websocket.*=.*WebSocketManager",
        ]

        # Direct WebSocket method call patterns (ANTI-PATTERNS)
        self.direct_method_call_patterns = [
            r"websocket_manager\.send_agent_started\s*\(",
            r"websocket_manager\.send_agent_thinking\s*\(",
            r"websocket_manager\.send_agent_completed\s*\(",
            r"websocket_manager\.send_tool_executing\s*\(",
            r"websocket_manager\.send_tool_completed\s*\(",
            r"websocket_manager\.send_progress_update\s*\(",
            r"websocket_manager\.send_agent_error\s*\(",
        ]

        # Constructor parameter anti-patterns (SHOULD BE ELIMINATED)
        self.constructor_anti_patterns = [
            r"def\s+__init__\s*\(.*websocket_manager\s*:",
            r"def\s+__init__\s*\(.*websocket_manager\s*\)",
            r"websocket_manager\s*:\s*WebSocketManager",
            r"websocket_manager\s*:\s*Optional\[WebSocketManager\]",
        ]

        # Context access anti-patterns (SHOULD BE ELIMINATED)
        self.context_access_anti_patterns = [
            r"context\.websocket_manager\.send_",
            r"self\.context\.websocket_manager",
            r"execution_context\.websocket_manager",
            r"user_context\.websocket_manager\.send_",
        ]

        # Canonical bridge patterns (SHOULD BE USED INSTEAD)
        self.canonical_bridge_patterns = [
            r"registry\.websocket_bridge",
            r"bridge\.send_agent_",
            r"await.*bridge\.send_",
            r"get_websocket_bridge\s*\(",
            r"registry\s*:\s*AgentRegistry",
        ]

        # Known violation files with specific patterns
        self.known_violation_patterns = {
            "netra_backend/app/agents/optimizations_core_sub_agent.py": [
                "websocket_manager.send_agent_started",
                "websocket_manager.send_agent_completed",
                "websocket_manager.send_agent_thinking",
                "websocket_manager.send_tool_executing",
                "websocket_manager.send_tool_completed",
            ],
            "netra_backend/app/agents/github_analyzer/agent.py": [
                "websocket_manager.send_agent_progress",
            ],
            "netra_backend/app/agents/supervisor/pipeline_executor.py": [
                "websocket_manager: 'WebSocketManager'",
            ],
        }

        # Record test start metrics
        self.record_metric("test_category", "unit")
        self.record_metric("ssot_focus", "agent_direct_websocket_violations")
        self.record_metric("anti_pattern_categories", 4)
        self.record_metric("expected_violation_files", len(self.known_violation_patterns))

    def _scan_file_for_patterns(self, file_path: Path, patterns: List[str]) -> List[Tuple[int, str, str]]:
        """
        Scan file for matching patterns and return detailed matches.

        Args:
            file_path: Path to file to scan
            patterns: List of regex patterns to search for

        Returns:
            List of (line_number, match_text, pattern_matched) tuples
        """
        matches = []
        if not file_path.exists() or not file_path.is_file():
            return matches

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line):
                        matches.append((line_num, line.strip(), pattern))
        except Exception:
            # Skip files that can't be read
            pass

        return matches

    def _scan_directory_for_patterns(self, directory: Path, patterns: List[str],
                                   file_extensions: Set[str] = {'.py'}) -> Dict[str, List[Tuple[int, str, str]]]:
        """
        Recursively scan directory for pattern matches with detailed results.

        Args:
            directory: Directory to scan recursively
            patterns: List of regex patterns to search for
            file_extensions: Set of file extensions to include

        Returns:
            Dictionary mapping relative file paths to list of (line_number, match, pattern) tuples
        """
        matches = {}

        if not directory.exists():
            return matches

        for file_path in directory.rglob('*'):
            if file_path.suffix in file_extensions and file_path.is_file():
                # Skip test files and deprecated backups
                relative_path = str(file_path.relative_to(self.project_root))
                if any(skip in relative_path for skip in ['test_', 'tests/', '.deprecated_backup']):
                    continue

                file_matches = self._scan_file_for_patterns(file_path, patterns)
                if file_matches:
                    matches[relative_path] = file_matches

        return matches

    def _analyze_constructor_parameters(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Analyze constructor parameters using AST to find WebSocket parameter patterns.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            List of constructor analysis results
        """
        if not file_path.exists() or not file_path.suffix == '.py':
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except:
            return []

        constructor_issues = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == '__init__':
                for arg in node.args.args:
                    if 'websocket' in arg.arg.lower():
                        constructor_issues.append({
                            'line': node.lineno,
                            'parameter': arg.arg,
                            'function': '__init__',
                            'issue': 'direct_websocket_parameter'
                        })

                # Check for type annotations
                for arg in node.args.args:
                    if hasattr(arg, 'annotation') and arg.annotation:
                        if hasattr(arg.annotation, 'id') and 'WebSocket' in getattr(arg.annotation, 'id', ''):
                            constructor_issues.append({
                                'line': node.lineno,
                                'parameter': arg.arg,
                                'type': arg.annotation.id,
                                'issue': 'websocket_type_annotation'
                            })

        return constructor_issues

    def test_no_direct_websocket_instantiation_in_agents(self):
        """
        Test that agents don't directly instantiate WebSocket managers.

        **EXPECTED TO FAIL INITIALLY** - Should detect direct instantiation patterns
        **EXPECTED TO PASS AFTER REMEDIATION** - All instantiation through bridge

        This test detects agents that create WebSocketManager instances directly
        instead of using the AgentRegistry bridge pattern for proper isolation.
        """
        self.record_metric("test_method", "no_direct_websocket_instantiation_in_agents")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for direct WebSocket instantiation patterns
        instantiation_violations = self._scan_directory_for_patterns(
            self.agents_path,
            self.direct_instantiation_patterns
        )

        # Calculate violation statistics
        violation_files = len(instantiation_violations)
        violation_instances = sum(len(matches) for matches in instantiation_violations.values())

        self.record_metric("instantiation_violation_files", violation_files)
        self.record_metric("instantiation_violation_instances", violation_instances)

        # Analyze violation patterns
        pattern_breakdown = defaultdict(int)
        for file_path, matches in instantiation_violations.items():
            for line_num, match_text, pattern in matches:
                if "WebSocketManager(" in match_text:
                    pattern_breakdown["direct_constructor"] += 1
                elif "get_websocket_manager(" in match_text:
                    pattern_breakdown["factory_function"] += 1
                elif "websocket_manager =" in match_text:
                    pattern_breakdown["variable_assignment"] += 1

        for pattern_type, count in pattern_breakdown.items():
            self.record_metric(f"instantiation_pattern_{pattern_type}", count)

        # Violation detection requires zero direct instantiation
        if violation_instances > 0:
            failure_message = [
                f"❌ DIRECT WEBSOCKET INSTANTIATION VIOLATIONS DETECTED ❌",
                f"",
                f"Found {violation_instances} direct WebSocket instantiation patterns across {violation_files} agent files.",
                f"These violations break user isolation and must be eliminated.",
                f"",
                f"🚨 USER ISOLATION VIOLATION: Agents creating WebSocket managers directly",
                f"",
                f"INSTANTIATION PATTERN BREAKDOWN:",
            ]

            for pattern_type, count in pattern_breakdown.items():
                failure_message.append(f"• {pattern_type.replace('_', ' ').title()}: {count} instances")

            failure_message.append(f"")
            failure_message.append(f"INSTANTIATION VIOLATIONS FOUND:")

            for file_path, matches in instantiation_violations.items():
                failure_message.append(f"")
                failure_message.append(f"📁 File: {file_path}")
                for line_num, match_text, pattern in matches:
                    failure_message.append(f"   Line {line_num}: {match_text}")

            failure_message.extend([
                f"",
                f"🔧 BRIDGE PATTERN REMEDIATION:",
                f"",
                f"❌ ELIMINATE DIRECT INSTANTIATION:",
                f"   websocket_manager = WebSocketManager()",
                f"   manager = get_websocket_manager()",
                f"   self.websocket_manager = WebSocketManager(config)",
                f"",
                f"✅ USE BRIDGE PATTERN:",
                f"   # Get bridge from registry instead",
                f"   bridge = await registry.get_websocket_bridge(user_id)",
                f"   # Use bridge for all WebSocket operations",
                f"   await bridge.send_agent_started(...)",
                f"",
                f"🏗️ ARCHITECTURAL CHANGES:",
                f"• Remove WebSocket manager parameters from constructors",
                f"• Pass AgentRegistry instead of WebSocket manager",
                f"• Access bridge dynamically per user context",
                f"• Ensure proper user isolation via bridge pattern",
                f"",
                f"🎯 USER ISOLATION BENEFITS:",
                f"• Each user gets isolated WebSocket bridge",
                f"• Prevents cross-user data contamination",
                f"• Enables proper multi-tenant execution",
                f"• Maintains SSOT bridge pattern compliance",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("direct_instantiation_eliminated", True)
        print("✅ NO DIRECT WEBSOCKET INSTANTIATION IN AGENTS")
        print("✅ All WebSocket access through bridge pattern")

    def test_no_direct_websocket_method_calls_in_agents(self):
        """
        Test that agents don't make direct websocket_manager.send_* method calls.

        **EXPECTED TO FAIL INITIALLY** - Should detect direct method call patterns
        **EXPECTED TO PASS AFTER REMEDIATION** - All calls through bridge

        This test identifies agents that call WebSocket methods directly instead
        of using the isolated bridge pattern for proper user separation.
        """
        self.record_metric("test_method", "no_direct_websocket_method_calls_in_agents")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for direct WebSocket method call patterns
        method_call_violations = self._scan_directory_for_patterns(
            self.agents_path,
            self.direct_method_call_patterns
        )

        # Calculate violation statistics
        violation_files = len(method_call_violations)
        violation_instances = sum(len(matches) for matches in method_call_violations.values())

        self.record_metric("method_call_violation_files", violation_files)
        self.record_metric("method_call_violation_instances", violation_instances)

        # Analyze method call patterns
        method_breakdown = defaultdict(int)
        for file_path, matches in method_call_violations.items():
            for line_num, match_text, pattern in matches:
                if "send_agent_started" in match_text:
                    method_breakdown["agent_started"] += 1
                elif "send_agent_thinking" in match_text:
                    method_breakdown["agent_thinking"] += 1
                elif "send_agent_completed" in match_text:
                    method_breakdown["agent_completed"] += 1
                elif "send_tool_executing" in match_text:
                    method_breakdown["tool_executing"] += 1
                elif "send_tool_completed" in match_text:
                    method_breakdown["tool_completed"] += 1
                elif "send_progress_update" in match_text:
                    method_breakdown["progress_update"] += 1
                elif "send_agent_error" in match_text:
                    method_breakdown["agent_error"] += 1

        for method_type, count in method_breakdown.items():
            self.record_metric(f"method_call_{method_type}", count)

        # Verify known violation patterns are detected
        detected_known_patterns = 0
        total_expected_patterns = sum(len(patterns) for patterns in self.known_violation_patterns.values())

        for known_file, expected_patterns in self.known_violation_patterns.items():
            if known_file in method_call_violations:
                file_content = ""
                file_path = self.project_root / known_file
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                    except:
                        pass

                for expected_pattern in expected_patterns:
                    if expected_pattern in file_content:
                        detected_known_patterns += 1

        detection_ratio = detected_known_patterns / total_expected_patterns if total_expected_patterns > 0 else 0
        self.record_metric("known_pattern_detection_ratio", detection_ratio)

        # Method call violation detection requires zero direct calls
        if violation_instances > 0:
            failure_message = [
                f"❌ DIRECT WEBSOCKET METHOD CALL VIOLATIONS DETECTED ❌",
                f"",
                f"Found {violation_instances} direct websocket_manager.send_* calls across {violation_files} agent files.",
                f"These direct calls bypass user isolation and violate bridge pattern requirements.",
                f"",
                f"🚨 BRIDGE PATTERN VIOLATION: {violation_instances} direct method calls detected",
                f"Known Pattern Detection: {detection_ratio:.1%} ({detected_known_patterns}/{total_expected_patterns})",
                f"",
                f"METHOD CALL BREAKDOWN:",
            ]

            for method_type, count in method_breakdown.items():
                failure_message.append(f"• {method_type.replace('_', ' ').title()}: {count} calls")

            failure_message.append(f"")
            failure_message.append(f"DIRECT METHOD CALL VIOLATIONS:")

            for file_path, matches in method_call_violations.items():
                failure_message.append(f"")
                failure_message.append(f"📁 File: {file_path}")
                for line_num, match_text, pattern in matches[:5]:  # Show first 5 per file
                    failure_message.append(f"   Line {line_num}: {match_text}")
                if len(matches) > 5:
                    failure_message.append(f"   ... and {len(matches) - 5} more violations")

            failure_message.extend([
                f"",
                f"🔧 BRIDGE METHOD CALL CONVERSION:",
                f"",
                f"❌ ELIMINATE DIRECT CALLS:",
                f"   await websocket_manager.send_agent_started(...)",
                f"   await self.websocket_manager.send_agent_thinking(...)",
                f"   websocket_manager.send_tool_executing(...)",
                f"",
                f"✅ USE BRIDGE CALLS:",
                f"   bridge = await registry.get_websocket_bridge(user_id)",
                f"   await bridge.send_agent_started(...)",
                f"   await bridge.send_agent_thinking(...)",
                f"   await bridge.send_tool_executing(...)",
                f"",
                f"🔄 SYSTEMATIC CONVERSION PROCESS:",
                f"1. Identify all websocket_manager.send_* calls",
                f"2. Replace with bridge = await registry.get_websocket_bridge(user_id)",
                f"3. Convert calls to bridge.send_* equivalents",
                f"4. Ensure user_id is properly passed through call chain",
                f"5. Test user isolation is maintained",
                f"",
                f"💡 BRIDGE PATTERN BENEFITS:",
                f"• Proper user isolation per WebSocket bridge",
                f"• Prevention of cross-user message delivery",
                f"• Consistent SSOT architecture compliance",
                f"• Enhanced multi-tenant security",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("direct_method_calls_eliminated", True)
        print("✅ NO DIRECT WEBSOCKET METHOD CALLS IN AGENTS")
        print(f"✅ Known Pattern Detection: {detection_ratio:.1%}")

    def test_no_websocket_constructor_parameters_in_agents(self):
        """
        Test that agent constructors don't accept WebSocket manager parameters.

        **EXPECTED TO FAIL INITIALLY** - Should detect constructor anti-patterns
        **EXPECTED TO PASS AFTER REMEDIATION** - All constructors use registry

        This test identifies agent constructors that accept WebSocket managers
        directly instead of using AgentRegistry for proper dependency injection.
        """
        self.record_metric("test_method", "no_websocket_constructor_parameters_in_agents")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for constructor parameter anti-patterns
        constructor_violations = self._scan_directory_for_patterns(
            self.agents_path,
            self.constructor_anti_patterns
        )

        # Use AST analysis for more precise constructor analysis
        ast_constructor_issues = {}
        if self.agents_path.exists():
            for file_path in self.agents_path.rglob('*.py'):
                relative_path = str(file_path.relative_to(self.project_root))
                if any(skip in relative_path for skip in ['test_', 'tests/', '.deprecated_backup']):
                    continue

                issues = self._analyze_constructor_parameters(file_path)
                if issues:
                    ast_constructor_issues[relative_path] = issues

        # Calculate violation statistics
        pattern_violation_files = len(constructor_violations)
        pattern_violation_instances = sum(len(matches) for matches in constructor_violations.values())
        ast_violation_files = len(ast_constructor_issues)
        ast_violation_instances = sum(len(issues) for issues in ast_constructor_issues.values())

        total_violation_files = len(set(list(constructor_violations.keys()) + list(ast_constructor_issues.keys())))
        total_violation_instances = pattern_violation_instances + ast_violation_instances

        self.record_metric("constructor_pattern_violations", pattern_violation_instances)
        self.record_metric("constructor_ast_violations", ast_violation_instances)
        self.record_metric("constructor_total_violations", total_violation_instances)
        self.record_metric("constructor_violation_files", total_violation_files)

        # Analyze constructor violation types
        violation_types = defaultdict(int)
        for file_path, matches in constructor_violations.items():
            for line_num, match_text, pattern in matches:
                if "websocket_manager:" in match_text:
                    violation_types["typed_parameter"] += 1
                elif "websocket_manager)" in match_text:
                    violation_types["untyped_parameter"] += 1
                elif "Optional[WebSocketManager]" in match_text:
                    violation_types["optional_parameter"] += 1

        for issue_file, issues in ast_constructor_issues.items():
            for issue in issues:
                violation_types[issue['issue']] += 1

        for violation_type, count in violation_types.items():
            self.record_metric(f"constructor_violation_{violation_type}", count)

        # Constructor parameter violation detection requires zero WebSocket parameters
        if total_violation_instances > 0:
            failure_message = [
                f"❌ WEBSOCKET CONSTRUCTOR PARAMETER VIOLATIONS DETECTED ❌",
                f"",
                f"Found {total_violation_instances} WebSocket constructor parameters across {total_violation_files} agent files.",
                f"These parameters violate dependency injection patterns and prevent proper user isolation.",
                f"",
                f"🚨 DEPENDENCY INJECTION VIOLATION: Agents accepting WebSocket managers directly",
                f"Pattern Violations: {pattern_violation_instances} | AST Violations: {ast_violation_instances}",
                f"",
                f"CONSTRUCTOR VIOLATION TYPES:",
            ]

            for violation_type, count in violation_types.items():
                failure_message.append(f"• {violation_type.replace('_', ' ').title()}: {count} instances")

            failure_message.append(f"")
            failure_message.append(f"PATTERN-DETECTED VIOLATIONS:")

            for file_path, matches in constructor_violations.items():
                failure_message.append(f"")
                failure_message.append(f"📁 File: {file_path}")
                for line_num, match_text, pattern in matches:
                    failure_message.append(f"   Line {line_num}: {match_text}")

            if ast_constructor_issues:
                failure_message.append(f"")
                failure_message.append(f"AST-DETECTED VIOLATIONS:")

                for file_path, issues in ast_constructor_issues.items():
                    failure_message.append(f"")
                    failure_message.append(f"📁 File: {file_path}")
                    for issue in issues:
                        if issue['issue'] == 'direct_websocket_parameter':
                            failure_message.append(f"   Line {issue['line']}: Parameter '{issue['parameter']}' contains 'websocket'")
                        elif issue['issue'] == 'websocket_type_annotation':
                            failure_message.append(f"   Line {issue['line']}: Parameter '{issue['parameter']}' typed as '{issue['type']}'")

            failure_message.extend([
                f"",
                f"🔧 CONSTRUCTOR DEPENDENCY INJECTION REMEDIATION:",
                f"",
                f"❌ ELIMINATE WEBSOCKET PARAMETERS:",
                f"   def __init__(self, websocket_manager: WebSocketManager, ...):",
                f"   def __init__(self, websocket_manager: Optional[WebSocketManager] = None, ...):",
                f"   def __init__(self, ..., websocket_manager, ...):",
                f"",
                f"✅ USE REGISTRY INJECTION:",
                f"   def __init__(self, registry: AgentRegistry, ...):",
                f"       self.registry = registry",
                f"       # Bridge accessed dynamically per user",
                f"",
                f"🏗️ CONSTRUCTOR REFACTORING STEPS:",
                f"1. Remove websocket_manager parameters from all agent constructors",
                f"2. Add registry: AgentRegistry parameter instead",
                f"3. Store registry as instance variable",
                f"4. Access bridge dynamically: registry.get_websocket_bridge(user_id)",
                f"5. Update all agent factory creation calls",
                f"",
                f"💡 DEPENDENCY INJECTION BENEFITS:",
                f"• Proper separation of concerns",
                f"• Dynamic bridge creation per user",
                f"• Enhanced testability with registry mocks",
                f"• Consistent SSOT architecture compliance",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("constructor_parameters_eliminated", True)
        print("✅ NO WEBSOCKET CONSTRUCTOR PARAMETERS IN AGENTS")
        print("✅ All agents use registry-based dependency injection")

    def test_no_context_websocket_access_patterns_in_agents(self):
        """
        Test that agents don't access WebSocket managers through context objects.

        **EXPECTED TO FAIL INITIALLY** - Should detect context access anti-patterns
        **EXPECTED TO PASS AFTER REMEDIATION** - All access through bridge

        This test identifies agents that access WebSocket functionality through
        execution contexts instead of using the proper AgentRegistry bridge.
        """
        self.record_metric("test_method", "no_context_websocket_access_patterns_in_agents")
        self.record_metric("expected_initial_result", "FAIL")

        # Scan for context WebSocket access patterns
        context_access_violations = self._scan_directory_for_patterns(
            self.agents_path,
            self.context_access_anti_patterns
        )

        # Calculate violation statistics
        violation_files = len(context_access_violations)
        violation_instances = sum(len(matches) for matches in context_access_violations.values())

        self.record_metric("context_access_violation_files", violation_files)
        self.record_metric("context_access_violation_instances", violation_instances)

        # Analyze context access patterns
        context_patterns = defaultdict(int)
        for file_path, matches in context_access_violations.items():
            for line_num, match_text, pattern in matches:
                if "context.websocket_manager" in match_text:
                    context_patterns["context_direct"] += 1
                elif "self.context.websocket_manager" in match_text:
                    context_patterns["self_context_direct"] += 1
                elif "execution_context.websocket_manager" in match_text:
                    context_patterns["execution_context"] += 1
                elif "user_context.websocket_manager" in match_text:
                    context_patterns["user_context"] += 1

        for pattern_type, count in context_patterns.items():
            self.record_metric(f"context_pattern_{pattern_type}", count)

        # Context access violation detection requires zero context WebSocket access
        if violation_instances > 0:
            failure_message = [
                f"❌ CONTEXT WEBSOCKET ACCESS VIOLATIONS DETECTED ❌",
                f"",
                f"Found {violation_instances} context WebSocket access patterns across {violation_files} agent files.",
                f"These patterns bypass bridge isolation and violate user separation requirements.",
                f"",
                f"🚨 CONTEXT ACCESS VIOLATION: Agents accessing WebSocket through context objects",
                f"",
                f"CONTEXT ACCESS PATTERN BREAKDOWN:",
            ]

            for pattern_type, count in context_patterns.items():
                failure_message.append(f"• {pattern_type.replace('_', ' ').title()}: {count} instances")

            failure_message.append(f"")
            failure_message.append(f"CONTEXT ACCESS VIOLATIONS:")

            for file_path, matches in context_access_violations.items():
                failure_message.append(f"")
                failure_message.append(f"📁 File: {file_path}")
                for line_num, match_text, pattern in matches:
                    failure_message.append(f"   Line {line_num}: {match_text}")

            failure_message.extend([
                f"",
                f"🔧 CONTEXT ACCESS REMEDIATION:",
                f"",
                f"❌ ELIMINATE CONTEXT WEBSOCKET ACCESS:",
                f"   await context.websocket_manager.send_*(...)",
                f"   self.context.websocket_manager.send_*(...)",
                f"   execution_context.websocket_manager.send_*(...)",
                f"   user_context.websocket_manager.send_*(...)",
                f"",
                f"✅ USE REGISTRY BRIDGE ACCESS:",
                f"   bridge = await self.registry.get_websocket_bridge(user_id)",
                f"   await bridge.send_*(...)",
                f"",
                f"🏗️ CONTEXT REFACTORING STRATEGY:",
                f"1. Remove websocket_manager from context objects",
                f"2. Ensure agents have registry access",
                f"3. Replace context.websocket_manager with bridge pattern",
                f"4. Pass user_id through method call chains",
                f"5. Validate user isolation is maintained",
                f"",
                f"💡 CONTEXT SEPARATION BENEFITS:",
                f"• Clean separation between execution context and WebSocket bridge",
                f"• Proper user isolation per bridge instance",
                f"• Enhanced security through controlled access",
                f"• Consistent SSOT architecture compliance",
            ])

            pytest.fail("\n".join(failure_message))

        # Success state
        self.record_metric("context_access_eliminated", True)
        print("✅ NO CONTEXT WEBSOCKET ACCESS IN AGENTS")
        print("✅ All WebSocket access through proper bridge pattern")

    def test_agent_websocket_anti_pattern_comprehensive_validation(self):
        """
        Comprehensive validation of all agent WebSocket anti-pattern elimination.

        **EXPECTED TO PASS AFTER REMEDIATION** - Overall anti-pattern validation

        Validates that agents have eliminated all direct WebSocket access patterns:
        - No direct WebSocket instantiation
        - No direct method calls
        - No WebSocket constructor parameters
        - No context WebSocket access
        """
        self.record_metric("test_method", "agent_websocket_anti_pattern_comprehensive_validation")
        self.record_metric("test_type", "comprehensive_validation")

        # Collect all anti-pattern violations
        all_anti_patterns = []
        all_anti_patterns.extend(self.direct_instantiation_patterns)
        all_anti_patterns.extend(self.direct_method_call_patterns)
        all_anti_patterns.extend(self.constructor_anti_patterns)
        all_anti_patterns.extend(self.context_access_anti_patterns)

        # Scan for all anti-pattern violations
        all_violations = self._scan_directory_for_patterns(
            self.agents_path,
            all_anti_patterns
        )

        # Scan for canonical bridge usage
        bridge_usage = self._scan_directory_for_patterns(
            self.agents_path,
            self.canonical_bridge_patterns
        )

        # Calculate comprehensive metrics
        total_violation_files = len(all_violations)
        total_violation_instances = sum(len(matches) for matches in all_violations.values())
        bridge_usage_files = len(bridge_usage)
        bridge_usage_instances = sum(len(matches) for matches in bridge_usage.values())

        # Categorize violations by type
        violation_categories = {
            "instantiation": 0,
            "method_calls": 0,
            "constructor": 0,
            "context_access": 0,
        }

        for file_path, matches in all_violations.items():
            for line_num, match_text, pattern in matches:
                if any(p in pattern for p in self.direct_instantiation_patterns):
                    violation_categories["instantiation"] += 1
                elif any(p in pattern for p in self.direct_method_call_patterns):
                    violation_categories["method_calls"] += 1
                elif any(p in pattern for p in self.constructor_anti_patterns):
                    violation_categories["constructor"] += 1
                elif any(p in pattern for p in self.context_access_anti_patterns):
                    violation_categories["context_access"] += 1

        # Record comprehensive metrics
        self.record_metric("comprehensive_violation_files", total_violation_files)
        self.record_metric("comprehensive_violation_instances", total_violation_instances)
        self.record_metric("comprehensive_bridge_usage_files", bridge_usage_files)
        self.record_metric("comprehensive_bridge_usage_instances", bridge_usage_instances)

        for category, count in violation_categories.items():
            self.record_metric(f"comprehensive_violations_{category}", count)

        # Calculate anti-pattern elimination score
        total_websocket_usage = total_violation_instances + bridge_usage_instances
        if total_websocket_usage > 0:
            anti_pattern_elimination_score = (bridge_usage_instances / total_websocket_usage) * 100
        else:
            anti_pattern_elimination_score = 0.0

        self.record_metric("anti_pattern_elimination_score", anti_pattern_elimination_score)

        # Anti-pattern elimination requirements
        elimination_requirements = {
            "Zero instantiation violations": violation_categories["instantiation"] == 0,
            "Zero method call violations": violation_categories["method_calls"] == 0,
            "Zero constructor violations": violation_categories["constructor"] == 0,
            "Zero context access violations": violation_categories["context_access"] == 0,
            "Bridge pattern usage present": bridge_usage_instances > 0,
            "100% anti-pattern elimination": anti_pattern_elimination_score == 100.0,
        }

        failed_requirements = [req for req, passed in elimination_requirements.items() if not passed]

        if failed_requirements:
            failure_message = [
                f"❌ AGENT WEBSOCKET ANTI-PATTERN ELIMINATION VALIDATION FAILED ❌",
                f"",
                f"Anti-Pattern Elimination Score: {anti_pattern_elimination_score:.1f}% (Target: 100%)",
                f"",
                f"COMPREHENSIVE VIOLATION METRICS:",
                f"• Total Violation Files: {total_violation_files}",
                f"• Total Violation Instances: {total_violation_instances}",
                f"• Bridge Usage Files: {bridge_usage_files}",
                f"• Bridge Usage Instances: {bridge_usage_instances}",
                f"",
                f"VIOLATION CATEGORY BREAKDOWN:",
            ]

            for category, count in violation_categories.items():
                failure_message.append(f"• {category.replace('_', ' ').title()}: {count} violations")

            failure_message.append(f"")
            failure_message.append(f"FAILED REQUIREMENTS:")

            for requirement in failed_requirements:
                failure_message.append(f"❌ {requirement}")

            failure_message.extend([
                f"",
                f"🎯 COMPLETE ANTI-PATTERN ELIMINATION REMEDIATION:",
                f"• Run all individual anti-pattern detection tests",
                f"• Fix all instantiation, method call, constructor, and context violations",
                f"• Migrate all agents to AgentRegistry bridge pattern",
                f"• Achieve 100% anti-pattern elimination score",
                f"• Validate all requirements pass",
                f"",
                f"📋 SYSTEMATIC REMEDIATION PROCESS:",
                f"1. Fix direct instantiation violations",
                f"2. Convert method calls to bridge pattern",
                f"3. Update constructors to use registry injection",
                f"4. Eliminate context WebSocket access",
                f"5. Validate comprehensive anti-pattern elimination",
            ])

            pytest.fail("\n".join(failure_message))

        # Success - Complete anti-pattern elimination achieved
        self.record_metric("agent_websocket_anti_patterns_eliminated", True)

        print("🏆 AGENT WEBSOCKET ANTI-PATTERN ELIMINATION COMPLETE")
        print(f"✅ Anti-Pattern Elimination Score: {anti_pattern_elimination_score:.1f}%")
        print("✅ All anti-pattern requirements satisfied")
        print("✅ Bridge pattern compliance achieved across all agents")

    def teardown_method(self, method=None):
        """Clean up after agent direct WebSocket violation tests."""
        # Record final test metrics
        self.record_metric("test_completed", True)

        super().teardown_method(method)