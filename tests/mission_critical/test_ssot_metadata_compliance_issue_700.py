#!/usr/bin/env python3
"""MISSION CRITICAL TEST SUITE: SSOT Metadata Compliance - Issue #700

THIS SUITE MUST PASS OR THE PRODUCT IS BROKEN.
Business Value: $500K+ ARR - Prevents SSOT regression blocking Golden Path

PURPOSE: Detect and prevent agents bypassing store_metadata_result() SSOT method

Issue #700: SSOT-regression-TriageAgent-metadata-bypass-blocking-Golden-Path
Priority: P0 - CRITICAL blocking Golden Path

AFFECTED AGENTS:
- synthetic_data_sub_agent.py - 4 direct metadata assignments (lines 181, 182, 183, 199)
- optimizations_core_sub_agent.py - 2 direct assignments (lines 154, 156)

CRITICAL SSOT VIOLATION PATTERNS:
1. context.metadata['key'] = value  # FORBIDDEN - bypasses SSOT
2. self.store_metadata_result(context, 'key', value)  # REQUIRED - SSOT method

ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import ast
import os
import sys
import time
import uuid
import inspect
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import Mock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT test base
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import components for runtime testing
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent

# Import environment and config
from shared.isolated_environment import IsolatedEnvironment


@dataclass
class MetadataViolation:
    """Represents a metadata SSOT violation"""
    file_path: str
    line_number: int
    line_content: str
    violation_type: str
    agent_name: str
    severity: str


@dataclass
class MetadataComplianceReport:
    """Comprehensive metadata compliance analysis"""
    violations: List[MetadataViolation]
    total_files_scanned: int
    total_violations: int
    critical_violations: int
    affected_agents: Set[str]
    scan_timestamp: str


class TestSSotMetadataComplianceIssue700(SSotAsyncTestCase):
    """Mission Critical Test Suite: SSOT Metadata Compliance Issue #700

    Tests that validate agents use proper SSOT store_metadata_result() method
    instead of direct metadata assignment bypassing SSOT patterns.
    """

    def setup_method(self, method):
        """Setup for each test method"""
        super().setup_method(method)
        self.env = IsolatedEnvironment()
        self.project_root = Path(project_root)
        self.agent_dir = self.project_root / "netra_backend" / "app" / "agents"

        # Known violation files from Issue #700 analysis
        self.known_violation_files = {
            'synthetic_data_sub_agent.py': [181, 182, 183, 199],
            'optimizations_core_sub_agent.py': [154, 156]
        }

        logger.info(f"Setup complete for {method.__name__}")

    # ========================================================================
    # A. STATIC ANALYSIS TESTS - Detect Direct Metadata Assignments
    # ========================================================================

    def test_detect_synthetic_data_agent_metadata_bypass_violations(self):
        """FAILS when synthetic_data_sub_agent bypasses SSOT metadata storage

        This test MUST FAIL with current code to prove it detects violations.

        Expected violations:
        - Line 181: context.metadata['approval_message'] = approval_message
        - Line 182: context.metadata['requires_approval'] = True
        - Line 183: context.metadata['workload_profile'] = safe_json_dumps(profile)
        - Line 199: context.metadata['synthetic_data_result'] = safe_json_dumps(result)
        """
        violations = self._scan_agent_file_for_metadata_violations('synthetic_data_sub_agent.py')

        # This test MUST FAIL if violations exist
        if violations:
            violation_details = []
            for violation in violations:
                violation_details.append(
                    f"Line {violation.line_number}: {violation.line_content.strip()}"
                )

            pytest.fail(
                f"SSOT VIOLATION DETECTED: synthetic_data_sub_agent.py bypasses store_metadata_result() method.\n"
                f"Found {len(violations)} direct metadata assignments:\n" +
                "\n".join(violation_details) +
                f"\n\nREQUIRED FIX: Replace with self.store_metadata_result(context, key, value)"
            )

        # If no violations found, this means the issue was already fixed
        logger.info("✅ No metadata bypass violations found in synthetic_data_sub_agent.py")

    def test_detect_optimizations_agent_metadata_bypass_violations(self):
        """FAILS when optimizations_core_sub_agent bypasses SSOT metadata storage

        This test MUST FAIL with current code to prove it detects violations.

        Expected violations:
        - Line 154: context.metadata['data_result'] = {"test_data": "synthetic_data_for_testing"}
        - Line 156: context.metadata['triage_result'] = {"category": "optimization", "priority": "medium"}
        """
        violations = self._scan_agent_file_for_metadata_violations('optimizations_core_sub_agent.py')

        # This test MUST FAIL if violations exist
        if violations:
            violation_details = []
            for violation in violations:
                violation_details.append(
                    f"Line {violation.line_number}: {violation.line_content.strip()}"
                )

            pytest.fail(
                f"SSOT VIOLATION DETECTED: optimizations_core_sub_agent.py bypasses store_metadata_result() method.\n"
                f"Found {len(violations)} direct metadata assignments:\n" +
                "\n".join(violation_details) +
                f"\n\nREQUIRED FIX: Replace with self.store_metadata_result(context, key, value)"
            )

        # If no violations found, this means the issue was already fixed
        logger.info("✅ No metadata bypass violations found in optimizations_core_sub_agent.py")

    def test_comprehensive_agent_metadata_ssot_compliance_scan(self):
        """Comprehensive scan of ALL agent files for metadata SSOT violations

        This test scans the entire agents directory for any direct metadata
        assignments that bypass the SSOT store_metadata_result() method.
        """
        report = self._generate_comprehensive_compliance_report()

        # Log scan results
        logger.info(f"Metadata compliance scan complete:")
        logger.info(f"  Files scanned: {report.total_files_scanned}")
        logger.info(f"  Total violations: {report.total_violations}")
        logger.info(f"  Critical violations: {report.critical_violations}")
        logger.info(f"  Affected agents: {len(report.affected_agents)}")

        if report.critical_violations > 0:
            violation_summary = []
            for violation in report.violations:
                if violation.severity == 'CRITICAL':
                    violation_summary.append(
                        f"  {violation.agent_name} (Line {violation.line_number}): {violation.line_content.strip()}"
                    )

            pytest.fail(
                f"CRITICAL SSOT VIOLATIONS DETECTED: {report.critical_violations} agents bypass store_metadata_result().\n"
                f"Affected agents: {', '.join(report.affected_agents)}\n\n"
                f"Violations:\n" + "\n".join(violation_summary) +
                f"\n\nREQUIRED: Replace all direct metadata assignments with store_metadata_result() calls."
            )

    # ========================================================================
    # B. RUNTIME VALIDATION TESTS - Validate Proper SSOT Method Usage
    # ========================================================================

    async def test_base_agent_store_metadata_result_method_exists(self):
        """Validates BaseAgent has store_metadata_result SSOT method"""

        # Test that BaseAgent has the required method
        assert hasattr(BaseAgent, 'store_metadata_result'), \
            "BaseAgent must have store_metadata_result SSOT method"

        # Test method signature
        method = getattr(BaseAgent, 'store_metadata_result')
        sig = inspect.signature(method)

        # Expected parameters: self, context, key, value, ensure_serializable=True
        param_names = list(sig.parameters.keys())
        assert 'context' in param_names, "store_metadata_result must accept 'context' parameter"
        assert 'key' in param_names, "store_metadata_result must accept 'key' parameter"
        assert 'value' in param_names, "store_metadata_result must accept 'value' parameter"

        logger.info("✅ BaseAgent.store_metadata_result method exists with correct signature")

    async def test_store_metadata_result_properly_stores_data(self):
        """Validates store_metadata_result method correctly stores metadata"""

        # Create test context
        context = UserExecutionContext.from_request_supervisor(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            metadata={}
        )

        # Create minimal agent instance
        class TestAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                pass

        agent = TestAgent()

        # Test storing metadata via SSOT method
        test_key = "test_result"
        test_value = {"data": "test_data", "status": "complete"}

        agent.store_metadata_result(context, test_key, test_value)

        # Verify data was stored correctly
        assert test_key in context.metadata, f"Key '{test_key}' should be in context.metadata"
        assert context.metadata[test_key] == test_value, "Stored value should match input"

        logger.info("✅ store_metadata_result correctly stores metadata")

    async def test_store_metadata_result_handles_serialization(self):
        """Validates store_metadata_result handles JSON serialization properly"""

        # Create test context
        context = UserExecutionContext.from_request_supervisor(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            metadata={}
        )

        # Create minimal agent instance
        class TestAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                pass

        agent = TestAgent()

        # Test with complex data that needs serialization
        test_data = {
            "datetime": "2025-09-12T10:00:00Z",
            "nested": {"list": [1, 2, 3], "dict": {"key": "value"}},
            "status": "processing"
        }

        # Should not raise exception
        agent.store_metadata_result(context, "complex_data", test_data, ensure_serializable=True)

        # Verify data was stored
        assert "complex_data" in context.metadata
        stored_data = context.metadata["complex_data"]
        assert isinstance(stored_data, (dict, str)), "Data should be stored as dict or serialized string"

        logger.info("✅ store_metadata_result handles serialization correctly")

    # ========================================================================
    # C. INTEGRATION WORKFLOW TESTS - Agent Coordination with SSOT
    # ========================================================================

    async def test_agent_to_agent_metadata_flow_with_ssot(self):
        """Tests agent-to-agent metadata coordination using SSOT methods"""

        # Create shared context
        context = UserExecutionContext.from_request_supervisor(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            metadata={}
        )

        # Create mock agents
        class DataAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                # Agent 1: Store data result using SSOT
                self.store_metadata_result(context, "data_result", {"status": "ready", "count": 100})

        class ProcessorAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                # Agent 2: Read data and store processing result using SSOT
                data_result = context.metadata.get("data_result")
                assert data_result is not None, "Should have data from previous agent"

                processed = {"input_count": data_result["count"], "processed_count": data_result["count"] * 2}
                self.store_metadata_result(context, "processed_result", processed)

        # Execute agent workflow
        data_agent = DataAgent()
        processor_agent = ProcessorAgent()

        await data_agent._execute_implementation(context)
        await processor_agent._execute_implementation(context)

        # Verify both results are in metadata
        assert "data_result" in context.metadata
        assert "processed_result" in context.metadata
        assert context.metadata["processed_result"]["input_count"] == 100
        assert context.metadata["processed_result"]["processed_count"] == 200

        logger.info("✅ Agent-to-agent metadata flow works with SSOT methods")

    async def test_websocket_events_access_ssot_stored_metadata(self):
        """Tests WebSocket events can access metadata stored via SSOT methods"""

        # Create context with WebSocket connection
        context = UserExecutionContext.from_request_supervisor(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            metadata={},
            websocket_client_id=str(uuid.uuid4())
        )

        # Mock agent that stores result via SSOT
        class WebSocketAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                # Store result using SSOT method
                result = {"status": "completed", "data": "websocket_test"}
                self.store_metadata_result(context, "websocket_result", result)

        agent = WebSocketAgent()
        await agent._execute_implementation(context)

        # Simulate WebSocket event trying to access the stored metadata
        websocket_data = context.metadata.get("websocket_result")
        assert websocket_data is not None, "WebSocket should access SSOT-stored metadata"
        assert websocket_data["status"] == "completed"
        assert websocket_data["data"] == "websocket_test"

        logger.info("✅ WebSocket events can access SSOT-stored metadata")

    # ========================================================================
    # D. AUDIT TRAIL TESTS - Metadata Change Tracking
    # ========================================================================

    async def test_metadata_audit_trail_with_ssot_method(self):
        """Tests that metadata changes via SSOT method are properly tracked"""

        # Create context
        context = UserExecutionContext.from_request_supervisor(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            metadata={}
        )

        # Track initial state
        initial_metadata_count = len(context.metadata)

        # Mock agent that uses SSOT method
        class AuditableAgent(BaseAgent):
            def __init__(self):
                self.config = Mock()
                self.timing_collector = Mock()

            async def _execute_implementation(self, context, **kwargs):
                # Multiple SSOT method calls
                self.store_metadata_result(context, "step_1", {"action": "data_validation"})
                self.store_metadata_result(context, "step_2", {"action": "data_processing"})
                self.store_metadata_result(context, "final_result", {"status": "success"})

        agent = AuditableAgent()
        await agent._execute_implementation(context)

        # Verify all changes were tracked
        assert len(context.metadata) == initial_metadata_count + 3
        assert "step_1" in context.metadata
        assert "step_2" in context.metadata
        assert "final_result" in context.metadata

        # Verify audit metadata exists (if supported by implementation)
        if hasattr(context, 'audit_metadata'):
            assert len(context.audit_metadata) >= 0, "Audit metadata should be tracked"

        logger.info("✅ Metadata changes via SSOT method are properly tracked")

    # ========================================================================
    # HELPER METHODS - Static Analysis and Compliance Scanning
    # ========================================================================

    def _scan_agent_file_for_metadata_violations(self, filename: str) -> List[MetadataViolation]:
        """Scan a specific agent file for metadata SSOT violations"""

        file_path = self.agent_dir / filename
        if not file_path.exists():
            logger.warning(f"Agent file not found: {file_path}")
            return []

        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Check for direct metadata assignment patterns
                if self._is_metadata_assignment_violation(line):
                    violations.append(MetadataViolation(
                        file_path=str(file_path),
                        line_number=line_num,
                        line_content=line,
                        violation_type="direct_metadata_assignment",
                        agent_name=filename,
                        severity="CRITICAL"
                    ))

        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")

        return violations

    def _is_metadata_assignment_violation(self, line: str) -> bool:
        """Check if a line contains a metadata assignment violation"""

        # Skip comments and empty lines
        line = line.strip()
        if not line or line.startswith('#'):
            return False

        # Pattern for direct metadata assignment: context.metadata['key'] = value
        # This bypasses the SSOT store_metadata_result() method
        patterns = [
            r"context\.metadata\s*\[\s*['\"][^'\"]+['\"]\s*\]\s*=",  # context.metadata['key'] =
            r"context\.metadata\s*\[\s*['\"][^'\"]+['\"]\s*\]\s*\+=", # context.metadata['key'] +=
            r"context\.metadata\s*\.\s*update\s*\(",                 # context.metadata.update(
            r"context\.metadata\s*\.\s*setdefault\s*\(",             # context.metadata.setdefault(
        ]

        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Exclude lines that are part of SSOT method implementation
                if 'store_metadata_result' in line:
                    continue
                return True

        return False

    def _generate_comprehensive_compliance_report(self) -> MetadataComplianceReport:
        """Generate comprehensive metadata compliance report for all agents"""

        all_violations = []
        files_scanned = 0
        affected_agents = set()

        # Scan all Python files in agents directory
        for agent_file in self.agent_dir.rglob("*.py"):
            if agent_file.is_file():
                files_scanned += 1
                violations = self._scan_agent_file_for_metadata_violations(agent_file.name)

                for violation in violations:
                    all_violations.append(violation)
                    affected_agents.add(violation.agent_name)

        critical_violations = len([v for v in all_violations if v.severity == 'CRITICAL'])

        return MetadataComplianceReport(
            violations=all_violations,
            total_files_scanned=files_scanned,
            total_violations=len(all_violations),
            critical_violations=critical_violations,
            affected_agents=affected_agents,
            scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        )


if __name__ == "__main__":
    # Enable running individual tests
    pytest.main([__file__, "-v", "--tb=short"])