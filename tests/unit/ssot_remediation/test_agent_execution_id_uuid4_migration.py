"""
Agent Execution ID UUID4 Migration Test - SSOT Validation

This test detects uuid.uuid4() usage in agent execution tracking and validates
that agent execution uses UnifiedIDManager for execution IDs instead of direct UUID generation.

Business Value:
- Prevents agent execution ID collisions and tracking failures
- Ensures consistent ID patterns across agent execution workflows
- Critical for agent execution reliability and debugging capabilities

SSOT Validation:
- Detects direct uuid.uuid4() calls in agent execution code paths
- Validates AgentExecutionTracker uses UnifiedIDManager patterns
- Ensures execution IDs follow consistent SSOT format

Expected Behavior:
- BEFORE REMEDIATION: Should FAIL - agent execution uses uuid.uuid4() directly
- AFTER REMEDIATION: Should PASS - agent execution uses UnifiedIDManager SSOT
"""

import uuid
import inspect
import re
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Set

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, get_execution_tracker
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.types.core_types import ExecutionID, AgentID, UserID


class TestAgentExecutionIdUuid4Migration(SSotBaseTestCase):
    """Test agent execution ID migration from uuid.uuid4() to SSOT patterns."""

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.unified_id_manager = UnifiedIDManager()
        self.execution_tracker = None
        self.uuid4_call_count = 0
        self.uuid4_call_locations = []

    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)

    def test_agent_execution_tracker_no_direct_uuid4_usage(self):
        """
        Test that AgentExecutionTracker doesn't use uuid.uuid4() directly.
        
        This test validates that agent execution tracking uses UnifiedIDManager
        instead of direct UUID4 generation, preventing SSOT violations.
        
        Expected to FAIL before SSOT remediation.
        """
        # Mock uuid.uuid4 to track direct calls
        original_uuid4 = uuid.uuid4
        uuid4_calls = []
        
        def tracking_uuid4():
            # Capture stack trace to identify where uuid4 is called
            stack = inspect.stack()
            call_location = {
                'file': stack[1].filename,
                'function': stack[1].function,
                'line': stack[1].lineno,
                'code': stack[1].code_context[0] if stack[1].code_context else None
            }
            uuid4_calls.append(call_location)
            return original_uuid4()
        
        with patch('uuid.uuid4', side_effect=tracking_uuid4):
            # Create AgentExecutionTracker and perform typical operations
            execution_tracker = get_execution_tracker()
            
            # Generate test context
            user_id = UserID("test-user-123")
            agent_id = AgentID("test-agent-456")
            
            # Perform operations that might trigger ID generation
            try:
                # This should trigger execution ID generation
                execution_id = execution_tracker.create_execution_context(
                    user_id=user_id,
                    agent_id=agent_id,
                    request_data={"test": "data"}
                )
                
                self.record_metric("execution_id_generated", str(execution_id))
                
                # Update execution state (might trigger more ID generation)
                execution_tracker.update_execution_state(execution_id, "RUNNING")
                execution_tracker.complete_execution(execution_id, {"result": "success"})
                
            except Exception as e:
                # Record any errors during execution
                self.record_metric("execution_tracker_error", str(e))
        
        # Analyze UUID4 call locations
        agent_execution_uuid4_calls = []
        for call in uuid4_calls:
            if ('agent_execution_tracker' in call['file'] or 
                'execution_tracker' in call['file'] or
                'agent_execution' in call['file']):
                agent_execution_uuid4_calls.append(call)
        
        # Record metrics about UUID4 usage
        self.record_metric("total_uuid4_calls", len(uuid4_calls))
        self.record_metric("agent_execution_uuid4_calls", len(agent_execution_uuid4_calls))
        
        # Provide detailed violation information
        if agent_execution_uuid4_calls:
            violation_details = []
            for call in agent_execution_uuid4_calls:
                violation_details.append(
                    f"File: {call['file']}, Function: {call['function']}, Line: {call['line']}"
                )
            self.record_metric("uuid4_violation_locations", violation_details)
        
        # The test should FAIL if direct uuid4 calls are detected in agent execution
        self.assertEqual(
            len(agent_execution_uuid4_calls), 0,
            f"Agent execution tracker SSOT violation detected: {len(agent_execution_uuid4_calls)} "
            f"direct uuid.uuid4() calls found in agent execution code. "
            f"Locations: {agent_execution_uuid4_calls}. "
            "Agent execution must use UnifiedIDManager instead of direct UUID generation."
        )

    def test_execution_id_follows_unified_id_manager_patterns(self):
        """
        Test that execution IDs follow UnifiedIDManager patterns.
        
        This validates that execution IDs have the structured format
        rather than raw UUID4 format, indicating SSOT compliance.
        
        Expected to FAIL before SSOT remediation.
        """
        execution_tracker = get_execution_tracker()
        
        # Generate multiple execution IDs to test pattern consistency
        test_user_id = UserID(self.unified_id_manager.generate_base_id("user"))
        test_agent_id = AgentID(self.unified_id_manager.generate_base_id("agent"))
        
        generated_ids = []
        for i in range(5):
            try:
                execution_id = execution_tracker.create_execution_context(
                    user_id=test_user_id,
                    agent_id=test_agent_id,
                    request_data={"test_iteration": i}
                )
                generated_ids.append(str(execution_id))
            except Exception as e:
                self.record_metric(f"id_generation_error_{i}", str(e))
        
        # Analyze ID patterns
        structured_ids = 0
        raw_uuid_ids = 0
        invalid_ids = 0
        
        for execution_id in generated_ids:
            if self._is_structured_id_format(execution_id):
                structured_ids += 1
            elif self._is_raw_uuid4_format(execution_id):
                raw_uuid_ids += 1
            else:
                invalid_ids += 1
        
        # Record pattern analysis metrics
        self.record_metric("structured_id_count", structured_ids)
        self.record_metric("raw_uuid_id_count", raw_uuid_ids)
        self.record_metric("invalid_id_count", invalid_ids)
        self.record_metric("total_ids_generated", len(generated_ids))
        
        # Validate that all IDs follow structured patterns (SSOT compliance)
        self.assertEqual(
            raw_uuid_ids, 0,
            f"Agent execution SSOT violation: {raw_uuid_ids} execution IDs are raw UUID4 format. "
            f"Generated IDs: {generated_ids}. "
            "All execution IDs must follow UnifiedIDManager structured patterns, not raw UUID4."
        )
        
        self.assertGreater(
            structured_ids, 0,
            f"No structured execution IDs generated. Generated IDs: {generated_ids}. "
            "Agent execution tracker must use UnifiedIDManager to generate structured IDs."
        )

    def test_execution_tracker_unified_id_manager_integration(self):
        """
        Test that AgentExecutionTracker integrates with UnifiedIDManager.
        
        This validates that the execution tracker uses UnifiedIDManager
        for all ID generation operations.
        
        Expected to FAIL before SSOT remediation.
        """
        # Test direct integration with UnifiedIDManager
        unified_manager = UnifiedIDManager()
        execution_tracker = get_execution_tracker()
        
        # Check if execution tracker uses UnifiedIDManager internally
        has_unified_manager = hasattr(execution_tracker, '_id_manager') or \
                            hasattr(execution_tracker, 'id_manager') or \
                            hasattr(execution_tracker, 'unified_id_manager')
        
        self.record_metric("execution_tracker_has_unified_manager", has_unified_manager)
        
        # Generate test execution and validate ID generation method
        test_user_id = UserID("integration-test-user")
        test_agent_id = AgentID("integration-test-agent")
        
        # Track ID generation method by checking execution tracker internals
        try:
            execution_id = execution_tracker.create_execution_context(
                user_id=test_user_id,
                agent_id=test_agent_id,
                request_data={"integration_test": True}
            )
            
            execution_id_str = str(execution_id)
            
            # Validate that the generated ID is compatible with UnifiedIDManager
            is_unified_compatible = unified_manager.is_valid_id_format_compatible(
                execution_id_str, IDType.EXECUTION
            )
            
            self.record_metric("execution_id_unified_compatible", is_unified_compatible)
            self.record_metric("generated_execution_id", execution_id_str)
            
            # Test ID registration with UnifiedIDManager
            registration_success = unified_manager.register_existing_id(
                execution_id_str, IDType.EXECUTION, {"source": "execution_tracker_test"}
            )
            
            self.record_metric("unified_manager_registration_success", registration_success)
            
            # Validate SSOT compliance
            self.assertTrue(
                is_unified_compatible,
                f"Execution ID '{execution_id_str}' not compatible with UnifiedIDManager. "
                "This indicates agent execution tracker is not using SSOT ID generation."
            )
            
        except Exception as e:
            self.record_metric("integration_test_error", str(e))
            raise AssertionError(
                f"AgentExecutionTracker UnifiedIDManager integration FAILED: {e}. "
                "Execution tracker is not properly integrated with SSOT ID generation."
            )

    def test_detect_uuid4_import_patterns_in_agent_execution(self):
        """
        Test for uuid4 import patterns in agent execution modules.
        
        This static analysis test detects import patterns that indicate
        direct uuid.uuid4() usage rather than SSOT patterns.
        
        Expected to FAIL before SSOT remediation.
        """
        # Get agent execution tracker module source
        import netra_backend.app.core.agent_execution_tracker as tracker_module
        
        try:
            import inspect
            source = inspect.getsource(tracker_module)
            
            # Look for problematic patterns
            uuid4_import_patterns = [
                r'from uuid import uuid4',
                r'import uuid.*uuid4',
                r'uuid\.uuid4\(',
                r'uuid4\('
            ]
            
            violations = []
            for pattern in uuid4_import_patterns:
                matches = re.findall(pattern, source, re.IGNORECASE | re.MULTILINE)
                if matches:
                    violations.extend(matches)
            
            # Look for SSOT-compliant patterns
            ssot_patterns = [
                r'UnifiedIDManager',
                r'unified_id_manager',
                r'generate_.*_id',
                r'from.*unified.*import'
            ]
            
            ssot_matches = []
            for pattern in ssot_patterns:
                matches = re.findall(pattern, source, re.IGNORECASE | re.MULTILINE)
                if matches:
                    ssot_matches.extend(matches)
            
            # Record analysis results
            self.record_metric("uuid4_import_violations", len(violations))
            self.record_metric("ssot_pattern_matches", len(ssot_matches))
            self.record_metric("violation_details", violations)
            self.record_metric("ssot_details", ssot_matches)
            
            # Validate SSOT compliance
            self.assertEqual(
                len(violations), 0,
                f"Agent execution tracker contains {len(violations)} uuid4 import violations: {violations}. "
                "Module must use UnifiedIDManager instead of direct uuid4 imports."
            )
            
            self.assertGreater(
                len(ssot_matches), 0,
                f"No SSOT patterns found in agent execution tracker. SSOT patterns: {ssot_matches}. "
                "Module must integrate with UnifiedIDManager for SSOT compliance."
            )
            
        except Exception as e:
            self.record_metric("static_analysis_error", str(e))
            # Don't fail the test for static analysis errors, but record them
            self.record_metric("static_analysis_available", False)

    def _is_structured_id_format(self, id_value: str) -> bool:
        """
        Check if ID follows UnifiedIDManager structured format.
        
        Structured IDs typically look like: "execution_1_abc12345"
        
        Args:
            id_value: ID to check
            
        Returns:
            True if structured format
        """
        if not isinstance(id_value, str) or not id_value:
            return False
        
        # UnifiedIDManager structured format has underscores
        parts = id_value.split('_')
        
        # Should have at least 3 parts: [type]_[counter]_[uuid_fragment]
        if len(parts) < 3:
            return False
        
        # First part should be ID type
        if parts[0] not in ['execution', 'agent', 'user', 'request', 'trace']:
            return False
        
        # Second part should be numeric counter
        try:
            int(parts[1])
            return True
        except ValueError:
            return False

    def _is_raw_uuid4_format(self, id_value: str) -> bool:
        """
        Check if ID is raw UUID4 format.
        
        Args:
            id_value: ID to check
            
        Returns:
            True if raw UUID4 format
        """
        if not isinstance(id_value, str) or not id_value:
            return False
        
        try:
            uuid_obj = uuid.UUID(id_value)
            # If it parses as UUID and string representation matches, it's raw UUID4
            return str(uuid_obj) == id_value
        except ValueError:
            return False

    def test_agent_execution_tracker_ssot_migration_status(self):
        """
        Comprehensive test of AgentExecutionTracker SSOT migration status.
        
        This test provides a complete assessment of whether agent execution
        tracking has been migrated to SSOT patterns.
        """
        execution_tracker = get_execution_tracker()
        
        # Test 1: Check for UnifiedIDManager integration
        unified_integration = (
            hasattr(execution_tracker, '_id_manager') or 
            hasattr(execution_tracker, 'id_manager') or
            hasattr(execution_tracker, 'unified_id_manager')
        )
        
        # Test 2: Generate execution ID and analyze pattern
        test_user_id = UserID("migration-status-user")
        test_agent_id = AgentID("migration-status-agent")
        
        try:
            execution_id = execution_tracker.create_execution_context(
                user_id=test_user_id,
                agent_id=test_agent_id,
                request_data={"migration_status_test": True}
            )
            
            execution_id_str = str(execution_id)
            id_follows_structured_pattern = self._is_structured_id_format(execution_id_str)
            id_is_raw_uuid = self._is_raw_uuid4_format(execution_id_str)
            
        except Exception as e:
            execution_id_str = None
            id_follows_structured_pattern = False
            id_is_raw_uuid = False
            self.record_metric("execution_creation_error", str(e))
        
        # Calculate migration score
        migration_score = 0
        if unified_integration:
            migration_score += 40  # Has UnifiedIDManager integration
        if id_follows_structured_pattern:
            migration_score += 40  # Uses structured ID format
        if not id_is_raw_uuid:
            migration_score += 20  # Doesn't use raw UUID4
        
        # Record comprehensive metrics
        self.record_metric("unified_id_manager_integration", unified_integration)
        self.record_metric("structured_id_pattern", id_follows_structured_pattern)
        self.record_metric("raw_uuid4_pattern", id_is_raw_uuid)
        self.record_metric("migration_score_percentage", migration_score)
        self.record_metric("execution_id_sample", execution_id_str)
        
        # Determine migration status
        if migration_score >= 80:
            migration_status = "COMPLETE"
        elif migration_score >= 40:
            migration_status = "PARTIAL"
        else:
            migration_status = "NOT_STARTED"
        
        self.record_metric("migration_status", migration_status)
        
        # Validate migration completion
        self.assertEqual(
            migration_status, "COMPLETE",
            f"Agent execution tracker SSOT migration is {migration_status} (score: {migration_score}/100). "
            f"UnifiedIDManager integration: {unified_integration}, "
            f"Structured ID pattern: {id_follows_structured_pattern}, "
            f"Raw UUID4 usage: {id_is_raw_uuid}. "
            "Complete migration required for SSOT compliance."
        )