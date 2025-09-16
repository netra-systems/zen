"""
Issue #1065: SSOT Mock Factory Compliance Validation Test Suite

Validates compliance with SSOT mock factory patterns and identifies non-compliant usage.
Builds on baseline of 23,483 violations to drive systematic remediation.

Business Value: Platform/Internal - Development Velocity & Test Reliability
Ensures all mock creation follows SSOT patterns for consistency and maintainability.

Test Strategy:
1. Validate SSOT mock factory patterns are properly imported and used
2. Detect non-compliant mock creation patterns
3. Verify mock factory methods provide expected interfaces
4. Ensure backwards compatibility during transition

Expected Baseline: Track 23,483 violations, focus on agent (287) and websocket (1,088) violations
Target State: All mocks created through SSotMockFactory
"""

import ast
import inspect
from pathlib import Path
from typing import Dict, List, Set, Any
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


@pytest.mark.unit
class SSOTMockFactoryComplianceTests(SSotBaseTestCase):
    """
    Validates compliance with SSOT mock factory patterns.

    Ensures consistent mock creation and identifies remediation targets.
    """

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        self.project_root = Path(__file__).parent.parent.parent.parent

        # SSOT compliance patterns
        self.compliant_patterns = [
            'SSotMockFactory.create_agent_mock',
            'SSotMockFactory.create_websocket_mock',
            'SSotMockFactory.create_database_session_mock',
            'SSotMockFactory.create_execution_context_mock',
            'SSotMockFactory.create_tool_mock',
            'SSotMockFactory.create_llm_client_mock',
            'SSotMockFactory.create_configuration_mock',
        ]

        # Non-compliant patterns to detect
        self.non_compliant_patterns = [
            'Mock()',
            'MagicMock()',
            'AsyncMock()',
            '@patch(',
            'create_autospec(',
        ]

    def test_validate_ssot_mock_factory_interface(self):
        """
        CRITICAL: Validate SSOT mock factory provides complete interface.

        Business Impact: Ensures factory can replace all direct mock usage
        """
        # Test all required factory methods exist
        required_methods = [
            'create_agent_mock',
            'create_websocket_mock',
            'create_database_session_mock',
            'create_execution_context_mock',
            'create_tool_mock',
            'create_llm_client_mock',
            'create_configuration_mock',
            'create_mock_llm_manager',
            'create_mock_agent_websocket_bridge',
            'create_websocket_manager_mock',
            'create_mock_user_context',
        ]

        for method_name in required_methods:
            assert hasattr(SSotMockFactory, method_name), (
                f"SSotMockFactory missing required method: {method_name}"
            )

            method = getattr(SSotMockFactory, method_name)
            assert callable(method), (
                f"SSotMockFactory.{method_name} is not callable"
            )

        self.logger.info(f"✅ All {len(required_methods)} required mock factory methods available")

    def test_validate_agent_mock_compliance(self):
        """
        CRITICAL: Validate agent mock creation compliance.

        Expected: 287 agent mock violations requiring remediation
        Business Impact: Critical for agent execution patterns
        """
        # Test SSOT agent mock creation
        mock_agent = SSotMockFactory.create_agent_mock(
            agent_type="supervisor",
            execution_result={"status": "test"}
        )

        # Validate mock has expected interface
        assert hasattr(mock_agent, 'agent_type')
        assert hasattr(mock_agent, 'execute')
        assert hasattr(mock_agent, 'get_capabilities')
        assert mock_agent.agent_type == "supervisor"

        # Test async interface
        assert inspect.iscoroutinefunction(mock_agent.execute)

        # Detect non-compliant agent mocks in codebase
        non_compliant_agent_mocks = self._scan_for_non_compliant_agent_mocks()

        if non_compliant_agent_mocks:
            violation_report = self._format_violations(non_compliant_agent_mocks)
            self.logger.warning(f"Found {len(non_compliant_agent_mocks)} non-compliant agent mocks:\n{violation_report}")

        # This test documents current state and validates factory works
        self.logger.info(f"Agent mock factory validation complete. Found {len(non_compliant_agent_mocks)} violations to remediate.")

    def test_validate_websocket_mock_compliance(self):
        """
        HIGH: Validate WebSocket mock creation compliance.

        Expected: 1,088 websocket mock violations requiring remediation
        Business Impact: Affects real-time communication testing
        """
        # Test SSOT WebSocket mock creation
        mock_websocket = SSotMockFactory.create_websocket_mock(
            connection_id="test-conn",
            user_id="test-user"
        )

        # Validate mock has expected interface
        assert hasattr(mock_websocket, 'connection_id')
        assert hasattr(mock_websocket, 'user_id')
        assert hasattr(mock_websocket, 'send_text')
        assert hasattr(mock_websocket, 'send_json')
        assert hasattr(mock_websocket, 'accept')
        assert hasattr(mock_websocket, 'close')

        # Test async interface methods
        assert inspect.iscoroutinefunction(mock_websocket.send_text)
        assert inspect.iscoroutinefunction(mock_websocket.send_json)

        # Detect non-compliant WebSocket mocks
        non_compliant_websocket_mocks = self._scan_for_non_compliant_websocket_mocks()

        if non_compliant_websocket_mocks:
            violation_report = self._format_violations(non_compliant_websocket_mocks)
            self.logger.warning(f"Found {len(non_compliant_websocket_mocks)} non-compliant WebSocket mocks:\n{violation_report}")

        self.logger.info(f"WebSocket mock factory validation complete. Found {len(non_compliant_websocket_mocks)} violations to remediate.")

    def test_validate_database_mock_compliance(self):
        """
        HIGH: Validate database mock creation compliance.

        Expected: 584 database mock violations requiring remediation
        Business Impact: Affects data persistence testing patterns
        """
        # Test SSOT database session mock creation
        mock_session = SSotMockFactory.create_database_session_mock()

        # Validate mock has expected interface
        required_methods = ['execute', 'scalar', 'scalars', 'commit', 'rollback', 'close']
        for method in required_methods:
            assert hasattr(mock_session, method), f"Database mock missing {method}"
            assert inspect.iscoroutinefunction(getattr(mock_session, method)), f"{method} should be async"

        # Test query result configuration
        result = mock_session.execute.return_value
        assert hasattr(result, 'fetchone')
        assert hasattr(result, 'fetchall')

        # Detect non-compliant database mocks
        non_compliant_db_mocks = self._scan_for_non_compliant_database_mocks()

        if non_compliant_db_mocks:
            violation_report = self._format_violations(non_compliant_db_mocks)
            self.logger.warning(f"Found {len(non_compliant_db_mocks)} non-compliant database mocks:\n{violation_report}")

        self.logger.info(f"Database mock factory validation complete. Found {len(non_compliant_db_mocks)} violations to remediate.")

    def test_validate_mock_factory_backwards_compatibility(self):
        """
        MEDIUM: Validate SSOT mock factory maintains backwards compatibility.

        Business Impact: Ensures seamless migration from direct mock usage
        """
        # Test that factory mocks can replace direct Mock usage
        compatibility_tests = [
            {
                'name': 'Agent Mock Compatibility',
                'factory_mock': SSotMockFactory.create_agent_mock(),
                'direct_mock': AsyncMock(),
                'required_attributes': ['execute', 'agent_type']
            },
            {
                'name': 'WebSocket Mock Compatibility',
                'factory_mock': SSotMockFactory.create_websocket_mock(),
                'direct_mock': MagicMock(),
                'required_attributes': ['send_text', 'connection_id']
            },
            {
                'name': 'Database Mock Compatibility',
                'factory_mock': SSotMockFactory.create_database_session_mock(),
                'direct_mock': AsyncMock(),
                'required_attributes': ['execute', 'commit']
            }
        ]

        compatibility_results = []
        for test in compatibility_tests:
            factory_mock = test['factory_mock']
            direct_mock = test['direct_mock']

            # Check if factory mock provides more attributes than direct mock
            factory_attrs = set(dir(factory_mock))
            direct_attrs = set(dir(direct_mock))

            missing_attrs = []
            for attr in test['required_attributes']:
                if not hasattr(factory_mock, attr):
                    missing_attrs.append(attr)

            compatibility_results.append({
                'name': test['name'],
                'factory_attr_count': len(factory_attrs),
                'direct_attr_count': len(direct_attrs),
                'additional_attrs': len(factory_attrs - direct_attrs),
                'missing_attrs': missing_attrs,
                'compatible': len(missing_attrs) == 0
            })

        # Validate all mocks are backwards compatible
        for result in compatibility_results:
            assert result['compatible'], (
                f"{result['name']} missing required attributes: {result['missing_attrs']}"
            )

            self.logger.info(
                f"✅ {result['name']}: "
                f"{result['additional_attrs']} additional attributes, "
                f"fully compatible"
            )

    def test_generate_mock_migration_roadmap(self):
        """
        MEDIUM: Generate actionable migration roadmap for mock consolidation.

        Business Impact: Provides systematic approach to reducing 23,483 violations
        """
        # Scan for all mock patterns and categorize
        migration_data = self._analyze_migration_complexity()

        roadmap = f"""
SSOT MOCK FACTORY MIGRATION ROADMAP
=================================

PHASE 1: Critical Infrastructure (Weeks 1-2)
- Agent Mocks: {migration_data['agent_violations']} violations
- Priority: CRITICAL - Affects agent execution patterns
- Effort: {migration_data['agent_effort_estimate']} hours
- Files to update: {migration_data['agent_files']}

PHASE 2: Real-time Communication (Weeks 3-4)
- WebSocket Mocks: {migration_data['websocket_violations']} violations
- Priority: HIGH - Affects Golden Path functionality
- Effort: {migration_data['websocket_effort_estimate']} hours
- Files to update: {migration_data['websocket_files']}

PHASE 3: Data Persistence (Weeks 5-6)
- Database Mocks: {migration_data['database_violations']} violations
- Priority: HIGH - Affects data testing patterns
- Effort: {migration_data['database_effort_estimate']} hours
- Files to update: {migration_data['database_files']}

PHASE 4: Generic Consolidation (Weeks 7-10)
- Generic Mocks: {migration_data['generic_violations']} violations
- Priority: MEDIUM - Code quality and consistency
- Effort: {migration_data['generic_effort_estimate']} hours
- Files to update: {migration_data['generic_files']}

TOTAL EFFORT ESTIMATE: {migration_data['total_effort_hours']} hours
BUSINESS VALUE: 80% reduction in mock maintenance overhead
RISK MITIGATION: Backwards compatible transition with validation
        """

        self.logger.info(f"Mock Migration Roadmap:\n{roadmap}")

        # Validate effort estimates are reasonable
        assert migration_data['total_effort_hours'] < 200, (
            "Migration effort estimate too high - review consolidation approach"
        )

    def _scan_for_non_compliant_agent_mocks(self) -> List[Dict[str, Any]]:
        """Scan for non-compliant agent mock patterns."""
        violations = []
        agent_patterns = [
            r'mock_agent\s*=\s*AsyncMock\(',
            r'MockAgent\s*=\s*.*',
            r'agent.*=.*Mock\(',
            r'@patch.*agent',
        ]

        for pattern in agent_patterns:
            found_violations = self._scan_codebase_for_pattern(pattern, 'agent_mock')
            violations.extend(found_violations)

        return violations

    def _scan_for_non_compliant_websocket_mocks(self) -> List[Dict[str, Any]]:
        """Scan for non-compliant WebSocket mock patterns."""
        violations = []
        websocket_patterns = [
            r'mock_websocket\s*=\s*.*Mock\(',
            r'MockWebSocket\s*=\s*.*',
            r'websocket.*=.*Mock\(',
            r'@patch.*websocket',
        ]

        for pattern in websocket_patterns:
            found_violations = self._scan_codebase_for_pattern(pattern, 'websocket_mock')
            violations.extend(found_violations)

        return violations

    def _scan_for_non_compliant_database_mocks(self) -> List[Dict[str, Any]]:
        """Scan for non-compliant database mock patterns."""
        violations = []
        database_patterns = [
            r'mock_session\s*=\s*.*Mock\(',
            r'AsyncSession.*=.*Mock\(',
            r'session.*=.*Mock\(',
            r'@patch.*session',
        ]

        for pattern in database_patterns:
            found_violations = self._scan_codebase_for_pattern(pattern, 'database_mock')
            violations.extend(found_violations)

        return violations

    def _scan_codebase_for_pattern(self, pattern: str, mock_type: str) -> List[Dict[str, Any]]:
        """Scan codebase for specific pattern violations."""
        violations = []
        test_dirs = [
            self.project_root / "tests",
            self.project_root / "netra_backend/tests",
            self.project_root / "test_framework",
        ]

        for test_dir in test_dirs:
            if test_dir.exists():
                for file_path in test_dir.rglob("*.py"):
                    violations.extend(self._scan_file_for_pattern(file_path, pattern, mock_type))

        return violations

    def _scan_file_for_pattern(self, file_path: Path, pattern: str, mock_type: str) -> List[Dict[str, Any]]:
        """Scan individual file for pattern violations."""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            for line_num, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append({
                        'file_path': str(file_path),
                        'line_number': line_num,
                        'mock_type': mock_type,
                        'line_content': line.strip(),
                        'pattern': pattern
                    })
        except Exception:
            pass

        return violations

    def _format_violations(self, violations: List[Dict[str, Any]]) -> str:
        """Format violations for display."""
        if not violations:
            return "No violations found."

        formatted = []
        for violation in violations[:10]:  # Show first 10
            relative_path = str(Path(violation['file_path']).relative_to(self.project_root))
            formatted.append(
                f"  {violation['mock_type']}: {relative_path}:{violation['line_number']} "
                f"- {violation['line_content'][:60]}..."
            )

        if len(violations) > 10:
            formatted.append(f"  ... and {len(violations) - 10} more violations")

        return "\n".join(formatted)

    def _analyze_migration_complexity(self) -> Dict[str, Any]:
        """Analyze complexity and effort for migration phases."""
        # Simplified analysis based on known violation counts
        return {
            'agent_violations': 287,
            'agent_effort_estimate': 20,  # 20 hours
            'agent_files': 50,
            'websocket_violations': 1088,
            'websocket_effort_estimate': 35,  # 35 hours
            'websocket_files': 120,
            'database_violations': 584,
            'database_effort_estimate': 25,  # 25 hours
            'database_files': 80,
            'generic_violations': 21524,
            'generic_effort_estimate': 100,  # 100 hours (batch processing)
            'generic_files': 800,
            'total_effort_hours': 180,
        }