"""WebSocket Bridge Adapter SSOT Compliance Test Suite

MISSION: Create FAILING tests that detect SSOT violations in WebSocket message delivery patterns.
Tests MUST FAIL initially, proving that multiple patterns exist across agents.

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Architecture
- Business Goal: SSOT Compliance & Code Consistency
- Value Impact: Standardized WebSocket patterns = Reliable chat UX = $500K+ ARR protection
- Strategic Impact: Multiple WebSocket patterns create maintenance burden and inconsistent UX

CRITICAL SSOT VIOLATIONS TO DETECT:
1. WebSocketBridgeAdapter (BaseAgent) - CORRECT PATTERN
2. Direct WebSocket Event (_emit_websocket_event) - VIOLATION
3. Context WebSocket Manager (context.websocket_manager) - VIOLATION
4. User Context Emitter (user_emitter.notify_*) - VIOLATION
5. Multiple Bridge Factory Adapters - VIOLATION

TEST STRATEGY:
- Scan actual agent classes for WebSocket message delivery patterns
- Create tests that FAIL when multiple patterns are detected
- Focus on real agent implementation analysis (not mocks)
- Prepare foundation for SSOT remediation validation
"""

import ast
import inspect
import asyncio
import pytest
import os
from pathlib import Path
from typing import Dict, Set, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Import SSOT test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Import agents to analyze
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent
from netra_backend.app.agents.base.executor import BaseExecutionEngine
from netra_backend.app.agents.unified_tool_execution import EnhancedToolExecutionEngine
from netra_backend.app.factories.websocket_bridge_factory import StandardWebSocketBridge


class TestWebSocketBridgeAdapterSSOTCompliance(SSotAsyncTestCase):
    """SSOT compliance tests for WebSocket bridge adapter patterns - MUST FAIL initially."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        # Track WebSocket patterns found during analysis
        self.detected_patterns = {}
        self.violations_found = []

        # Agent classes to analyze
        self.agent_classes = [
            BaseAgent,
            UnifiedDataAgent,
            BaseExecutionEngine,
            EnhancedToolExecutionEngine,
        ]

    def teardown_method(self, method):
        """Clean up test fixtures."""
        super().teardown_method(method)

    def _analyze_websocket_patterns_in_class(self, agent_class) -> Dict[str, List[str]]:
        """Analyze WebSocket message delivery patterns in agent class.

        Args:
            agent_class: Agent class to analyze

        Returns:
            Dict mapping pattern types to method names using that pattern
        """
        patterns = {
            'websocket_adapter': [],      # CORRECT: self._websocket_adapter.emit_*
            'direct_websocket_event': [], # VIOLATION: _emit_websocket_event
            'context_manager': [],        # VIOLATION: context.websocket_manager.send_*
            'user_emitter': [],          # VIOLATION: user_emitter.notify_*
            'multiple_adapters': []       # VIOLATION: Multiple adapter types
        }

        try:
            # Get source code for the class
            source = inspect.getsource(agent_class)
            tree = ast.parse(source)

            # Walk the AST to find WebSocket patterns
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_name = node.name
                    method_source = ast.get_source_segment(source, node) or ""

                    # Detect WebSocket adapter pattern (CORRECT)
                    if 'self._websocket_adapter.emit_' in method_source:
                        patterns['websocket_adapter'].append(method_name)

                    # Detect direct WebSocket event pattern (VIOLATION)
                    if '_emit_websocket_event' in method_source:
                        patterns['direct_websocket_event'].append(method_name)

                    # Detect context manager pattern (VIOLATION)
                    if 'context.websocket_manager' in method_source:
                        patterns['context_manager'].append(method_name)

                    # Detect user emitter pattern (VIOLATION)
                    if 'user_emitter.notify_' in method_source:
                        patterns['user_emitter'].append(method_name)

                    # Detect multiple adapter types (VIOLATION)
                    adapter_types = 0
                    if 'AgentWebSocketBridge' in method_source:
                        adapter_types += 1
                    if 'WebSocketEventEmitter' in method_source:
                        adapter_types += 1
                    if 'UnifiedWebSocketManager' in method_source:
                        adapter_types += 1

                    if adapter_types > 1:
                        patterns['multiple_adapters'].append(method_name)

        except Exception as e:
            # If we can't analyze the source, that's a test failure too
            patterns['analysis_errors'] = [str(e)]

        return patterns

    def _analyze_file_patterns(self, file_path: str) -> Dict[str, List[str]]:
        """Analyze WebSocket patterns in source file directly.

        Args:
            file_path: Path to source file to analyze

        Returns:
            Dict mapping pattern types to line numbers using that pattern
        """
        patterns = {
            'websocket_adapter': [],
            'direct_websocket_event': [],
            'context_manager': [],
            'user_emitter': [],
            'multiple_adapters': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Detect WebSocket adapter pattern (CORRECT)
                if 'self._websocket_adapter.emit_' in line:
                    patterns['websocket_adapter'].append(f"line_{line_num}")

                # Detect direct WebSocket event pattern (VIOLATION)
                if '_emit_websocket_event' in line and 'async def _emit_websocket_event' not in line:
                    patterns['direct_websocket_event'].append(f"line_{line_num}")

                # Detect context manager pattern (VIOLATION)
                if 'context.websocket_manager' in line:
                    patterns['context_manager'].append(f"line_{line_num}")

                # Detect user emitter pattern (VIOLATION)
                if 'user_emitter.notify_' in line:
                    patterns['user_emitter'].append(f"line_{line_num}")

                # Detect multiple adapter configurations (VIOLATION)
                if 'set_agent_bridge(' in line or 'set_websocket_emitter(' in line or 'set_websocket_manager(' in line:
                    patterns['multiple_adapters'].append(f"line_{line_num}")

        except Exception as e:
            patterns['analysis_errors'] = [str(e)]

        return patterns

    def test_detect_multiple_websocket_patterns_in_agents(self):
        """TEST MUST FAIL: Detect multiple WebSocket message delivery patterns across agents.

        This test scans agent classes and MUST FAIL if multiple patterns are found,
        proving SSOT violations exist that need remediation.
        """
        violation_count = 0
        pattern_summary = {}

        # Analyze each agent class for WebSocket patterns
        for agent_class in self.agent_classes:
            class_name = agent_class.__name__
            patterns = self._analyze_websocket_patterns_in_class(agent_class)
            pattern_summary[class_name] = patterns

            # Count violations (non-adapter patterns)
            for pattern_type, methods in patterns.items():
                if pattern_type != 'websocket_adapter' and methods:
                    violation_count += len(methods)
                    self.violations_found.append({
                        'agent_class': class_name,
                        'violation_type': pattern_type,
                        'methods': methods
                    })

        # Store detected patterns for reporting
        self.detected_patterns = pattern_summary

        # TEST ASSERTION: This MUST FAIL if SSOT violations exist
        # When test fails, it proves multiple patterns exist (SSOT violation)
        assert violation_count == 0, (
            f"SSOT VIOLATION DETECTED: Found {violation_count} WebSocket pattern violations across agents. "
            f"Multiple message delivery patterns violate SSOT principle. "
            f"Violations: {self.violations_found}. "
            f"Pattern summary: {pattern_summary}. "
            f"REMEDIATION REQUIRED: Standardize all agents to use WebSocketBridgeAdapter pattern only."
        )

    def test_detect_direct_websocket_event_violations(self):
        """TEST MUST FAIL: Detect direct _emit_websocket_event usage violations.

        Scans UnifiedDataAgent and other classes that use direct WebSocket events
        instead of the SSOT WebSocketBridgeAdapter pattern.
        """
        # Analyze UnifiedDataAgent source file directly
        unified_data_agent_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',  # Go up to netra_backend
            'app', 'agents', 'data', 'unified_data_agent.py'
        )

        violations = []

        if os.path.exists(unified_data_agent_path):
            patterns = self._analyze_file_patterns(unified_data_agent_path)

            # Check for direct WebSocket event violations
            if patterns['direct_websocket_event']:
                violations.extend([
                    f"unified_data_agent.py:{line}" for line in patterns['direct_websocket_event']
                ])

        # TEST ASSERTION: This MUST FAIL if direct event violations exist
        assert len(violations) == 0, (
            f"DIRECT WEBSOCKET EVENT VIOLATIONS DETECTED: Found {len(violations)} instances "
            f"of direct _emit_websocket_event usage. This violates SSOT WebSocketBridgeAdapter pattern. "
            f"Violations: {violations}. "
            f"REMEDIATION REQUIRED: Replace direct _emit_websocket_event calls with WebSocketBridgeAdapter."
        )

    def test_detect_context_manager_websocket_violations(self):
        """TEST MUST FAIL: Detect context.websocket_manager usage violations.

        Scans BaseExecutionEngine and other classes that access WebSocket via context
        instead of the SSOT WebSocketBridgeAdapter pattern.
        """
        # Analyze BaseExecutionEngine source file directly
        base_executor_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',  # Go up to netra_backend
            'app', 'agents', 'base', 'executor.py'
        )

        violations = []

        if os.path.exists(base_executor_path):
            patterns = self._analyze_file_patterns(base_executor_path)

            # Check for context manager violations
            if patterns['context_manager']:
                violations.extend([
                    f"executor.py:{line}" for line in patterns['context_manager']
                ])

        # TEST ASSERTION: This MUST FAIL if context manager violations exist
        assert len(violations) == 0, (
            f"CONTEXT MANAGER WEBSOCKET VIOLATIONS DETECTED: Found {len(violations)} instances "
            f"of context.websocket_manager usage. This violates SSOT WebSocketBridgeAdapter pattern. "
            f"Violations: {violations}. "
            f"REMEDIATION REQUIRED: Replace context.websocket_manager calls with WebSocketBridgeAdapter."
        )

    def test_detect_user_emitter_websocket_violations(self):
        """TEST MUST FAIL: Detect user_emitter.notify_* usage violations.

        Scans EnhancedToolExecutionEngine and other classes that use user emitters
        instead of the SSOT WebSocketBridgeAdapter pattern.
        """
        # Analyze UnifiedToolExecution source file directly
        tool_execution_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',  # Go up to netra_backend
            'app', 'agents', 'unified_tool_execution.py'
        )

        violations = []

        if os.path.exists(tool_execution_path):
            patterns = self._analyze_file_patterns(tool_execution_path)

            # Check for user emitter violations
            if patterns['user_emitter']:
                violations.extend([
                    f"unified_tool_execution.py:{line}" for line in patterns['user_emitter']
                ])

        # TEST ASSERTION: This MUST FAIL if user emitter violations exist
        assert len(violations) == 0, (
            f"USER EMITTER WEBSOCKET VIOLATIONS DETECTED: Found {len(violations)} instances "
            f"of user_emitter.notify_* usage. This violates SSOT WebSocketBridgeAdapter pattern. "
            f"Violations: {violations}. "
            f"REMEDIATION REQUIRED: Replace user_emitter.notify_* calls with WebSocketBridgeAdapter."
        )

    def test_detect_multiple_adapter_factory_violations(self):
        """TEST MUST FAIL: Detect multiple WebSocket bridge adapter types in factory.

        Scans WebSocketBridgeFactory for multiple adapter configuration methods
        that violate SSOT principle by providing multiple patterns.
        """
        # Analyze WebSocketBridgeFactory source file directly
        factory_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..',  # Go up to netra_backend
            'app', 'factories', 'websocket_bridge_factory.py'
        )

        violations = []
        adapter_config_methods = []

        if os.path.exists(factory_path):
            patterns = self._analyze_file_patterns(factory_path)

            # Check for multiple adapter configuration methods
            if patterns['multiple_adapters']:
                adapter_config_methods.extend(patterns['multiple_adapters'])

            # Count distinct adapter configuration methods as violations
            if len(adapter_config_methods) > 1:
                violations.extend(adapter_config_methods)

        # TEST ASSERTION: This MUST FAIL if multiple adapter types exist
        assert len(violations) <= 1, (
            f"MULTIPLE ADAPTER FACTORY VIOLATIONS DETECTED: Found {len(violations)} different "
            f"adapter configuration methods. This violates SSOT principle by supporting multiple patterns. "
            f"Adapter config methods: {adapter_config_methods}. "
            f"REMEDIATION REQUIRED: Standardize on single WebSocketBridgeAdapter pattern only."
        )

    def test_websocket_pattern_consistency_across_critical_events(self):
        """TEST MUST FAIL: Verify all 5 critical WebSocket events use consistent patterns.

        Tests that agent_started, agent_thinking, tool_executing, tool_completed,
        and agent_completed events all use the same SSOT pattern.
        """
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        pattern_inconsistencies = []

        # Check BaseAgent for pattern consistency
        try:
            source = inspect.getsource(BaseAgent)
            event_patterns = {}

            for event in critical_events:
                # Look for emit methods for each event
                method_name = f"emit_{event}"
                if method_name in source:
                    # Count different pattern types in the method
                    method_start = source.find(f"def {method_name}(")
                    if method_start != -1:
                        # Find the end of the method (next def or class)
                        method_end = source.find("\n    def ", method_start + 1)
                        if method_end == -1:
                            method_end = source.find("\n    async def ", method_start + 1)
                        if method_end == -1:
                            method_end = len(source)

                        method_body = source[method_start:method_end]

                        # Count patterns in this method
                        patterns_in_method = 0
                        patterns_found = []

                        if 'self._websocket_adapter.' in method_body:
                            patterns_in_method += 1
                            patterns_found.append('websocket_adapter')

                        if 'WebSocketEmitterFactory' in method_body:
                            patterns_in_method += 1
                            patterns_found.append('emitter_factory')

                        if '_emit_websocket_event' in method_body:
                            patterns_in_method += 1
                            patterns_found.append('direct_event')

                        event_patterns[event] = {
                            'pattern_count': patterns_in_method,
                            'patterns': patterns_found
                        }

                        # If multiple patterns in one method, it's an inconsistency
                        if patterns_in_method > 1:
                            pattern_inconsistencies.append({
                                'event': event,
                                'method': method_name,
                                'pattern_count': patterns_in_method,
                                'patterns': patterns_found
                            })

        except Exception as e:
            pattern_inconsistencies.append({
                'error': f"Failed to analyze BaseAgent patterns: {e}"
            })

        # TEST ASSERTION: This MUST FAIL if pattern inconsistencies exist
        assert len(pattern_inconsistencies) == 0, (
            f"WEBSOCKET PATTERN INCONSISTENCIES DETECTED: Found {len(pattern_inconsistencies)} "
            f"inconsistencies in critical WebSocket event patterns. "
            f"Inconsistencies: {pattern_inconsistencies}. "
            f"REMEDIATION REQUIRED: Standardize all critical events to use single SSOT pattern."
        )


if __name__ == "__main__":
    # Run the tests to detect SSOT violations
    pytest.main([__file__, "-v", "--tb=short"])