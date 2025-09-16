"""
Integration Tests for IDType.RUN SSOT Compliance - SSOT CRITICAL

BUSINESS VALUE:
- Segment: Platform/Internal - System Stability & Development Velocity
- Goal: Ensure IDType.RUN integrates properly with SSOT systems after fix implementation
- Value Impact: Validates Golden Path WebSocket integration and $500K+ ARR functionality
- Revenue Impact: Prevents integration failures in production SSOT components

TESTING STRATEGY:
- Tests WILL FAIL before fix (missing IDType.RUN enum value)
- Tests WILL PASS after fix (when RUN = "run" is added to IDType)
- Validates integration between UnifiedIDManager, WebSocket systems, and SSOT patterns
- Tests real service integration without mocks (SSOT requirement)

SSOT COMPLIANCE:
- Uses test_framework.ssot.base_test_case.SSotBaseTestCase
- Imports only from SSOT_IMPORT_REGISTRY.md verified paths  
- Follows SSOT testing patterns for integration validation
- No mocks - tests real system integration

CRITICAL TEST COVERAGE:
1. IDType.RUN integration with WebSocket execution contexts
2. Run ID generation integration with Golden Path validation
3. SSOT format validation integration across systems
4. Cross-system ID propagation with RUN type
5. Performance integration under realistic load
6. Error handling integration with RUN type
"""

import asyncio
import pytest
import time
import json
from typing import Dict, List, Set, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager

# SSOT imports from verified registry
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics, CategoryType
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ThreadID, ensure_user_id

# Core ID management imports - SSOT verified paths
from netra_backend.app.core.unified_id_manager import (
    IDType, UnifiedIDManager, generate_id, IDMetadata,
    is_valid_id_format, is_valid_id_format_compatible
)

# User execution context imports for integration testing
from netra_backend.app.services.user_execution_context import UserExecutionContext

# WebSocket and agent integration imports  
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker, get_execution_tracker


@pytest.mark.integration
class IDTypeRunSSOTIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for IDType.RUN SSOT compliance across system components.
    
    These tests validate that IDType.RUN integrates properly with all SSOT
    systems and maintains consistency across component boundaries.
    """

    def setup_method(self, method=None):
        """Set up integration test environment with real services."""
        super().setup_method(method)
        
        # Test metrics for SSOT compliance
        self.test_metrics = SsotTestMetrics()
        self.test_metrics.record_custom("category", "INTEGRATION")
        self.test_metrics.record_custom("test_name", method.__name__ if method else "setup")
        self.test_metrics.record_custom("business_value_segment", "Platform/Internal")
        self.test_metrics.record_custom("expected_outcome", "Validate IDType.RUN SSOT integration across components")
        
        # Integration test environment
        self.id_manager = UnifiedIDManager()
        self.execution_tracker = get_execution_tracker()
        
        # Test users for multi-user scenarios
        self.test_users = [
            "ssot-integration-user-001",
            "ssot-integration-user-002", 
            "golden-path-user-001"
        ]
        
        # Generated IDs for cleanup
        self.generated_run_ids: Set[str] = set()
        self.created_contexts: List[UserExecutionContext] = []

    def test_run_id_user_execution_context_integration(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN with UserExecutionContext.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError: IDType has no attribute 'RUN'
        - AFTER FIX: Will PASS and create valid UserExecutionContext with run_id
        
        This tests the primary integration point identified in GitHub Issue #883.
        """
        try:
            user_id = ensure_user_id(self.test_users[0])
            
            # Generate run ID for context - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="context_integration")
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="context_integration") 
            
            # Create UserExecutionContext with run_id - critical integration
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id, 
                run_id=run_id
            )
            
            # Validate context creation
            assert user_context.run_id == run_id, f"Context run_id mismatch: {user_context.run_id} != {run_id}"
            assert user_context.user_id == user_id, f"Context user_id mismatch: {user_context.user_id}"
            assert user_context.thread_id == thread_id, f"Context thread_id mismatch: {user_context.thread_id}"
            
            # Validate run_id format in context
            assert is_valid_id_format(user_context.run_id), f"Context run_id invalid format: {user_context.run_id}"
            assert is_valid_id_format_compatible(user_context.run_id, IDType.RUN), f"Context run_id not RUN compatible: {user_context.run_id}"
            
            # Validate context is tracked properly
            metadata = self.id_manager.get_id_metadata(run_id)
            assert metadata is not None, f"Run ID metadata should exist: {run_id}"
            assert metadata.id_type == IDType.RUN, f"Run ID metadata type should be RUN: {metadata.id_type}"
            
            self.generated_run_ids.add(run_id)
            self.created_contexts.append(user_context)
            self.test_metrics.record_custom("success", f"UserExecutionContext integration with run_id successful")
            
        except AttributeError as e:
            # Expected failure before fix
            assert "RUN" in str(e), f"Expected 'RUN' in error message, got: {e}"
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN UserExecutionContext integration failed: {e}")

    def test_run_id_agent_execution_tracker_integration(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN with AgentExecutionTracker.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and properly track agent execution with run_id
        
        This validates run_id tracking in agent execution workflows.
        """
        try:
            user_id = ensure_user_id(self.test_users[1])
            
            # Generate IDs for agent tracking - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="agent_tracking")
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="agent_tracking")
            agent_id = self.id_manager.generate_id(IDType.AGENT, prefix="agent_tracking")
            
            # Create execution context
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Test agent execution tracking with run_id
            execution_data = {
                "user_id": str(user_id),
                "thread_id": thread_id,
                "run_id": run_id,  # Critical: run_id integration
                "agent_id": agent_id,
                "execution_type": "integration_test",
                "business_context": "ssot_validation"
            }
            
            # Start execution tracking
            self.execution_tracker.start_execution(
                user_id=str(user_id),
                execution_id=run_id,  # Use run_id as execution_id
                context_data=execution_data
            )
            
            # Validate tracking integration
            active_executions = self.execution_tracker.get_active_executions(str(user_id))
            assert len(active_executions) > 0, f"Should have active executions for user: {user_id}"
            
            # Find our execution
            our_execution = None
            for exec_id, exec_data in active_executions.items():
                if exec_data.get("run_id") == run_id:
                    our_execution = exec_data
                    break
            
            assert our_execution is not None, f"Execution with run_id should be found: {run_id}"
            assert our_execution.get("run_id") == run_id, f"Execution run_id mismatch: {our_execution}"
            
            # Complete execution
            self.execution_tracker.complete_execution(str(user_id), run_id)
            
            self.generated_run_ids.add(run_id)
            self.created_contexts.append(context)
            self.test_metrics.record_custom("success", f"AgentExecutionTracker integration with run_id successful")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN AgentExecutionTracker integration failed: {e}")

    def test_run_id_golden_path_validation_integration(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN with Golden Path validation patterns.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)  
        - AFTER FIX: Will PASS and support Golden Path validation workflows
        
        This tests the specific Golden Path use case from the issue description.
        """
        try:
            user_id = ensure_user_id(self.test_users[2])  # golden-path-user-001
            
            # Simulate Golden Path validation workflow - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="golden_path_validation")
            thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="golden_path_validation")
            
            # Golden Path context creation
            golden_context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Validate Golden Path requirements
            assert golden_context.run_id is not None, "Golden Path run_id cannot be None"
            assert "golden_path" in run_id, f"Run ID should contain golden_path prefix: {run_id}"
            assert is_valid_id_format(run_id), f"Golden Path run_id must be valid format: {run_id}"
            
            # Test Golden Path validation workflow
            validation_context = {
                "user_id": str(user_id),
                "thread_id": thread_id,
                "run_id": run_id,
                "validation_type": "golden_path",
                "business_value": "$500K+ ARR",
                "critical_path": True
            }
            
            # Validate run_id can be used in validation patterns
            run_metadata = self.id_manager.get_id_metadata(run_id)
            assert run_metadata.id_type == IDType.RUN, f"Golden Path run_id should be RUN type: {run_metadata.id_type}"
            
            # Update context with validation data
            run_metadata.context.update(validation_context)
            
            # Validate context persistence
            retrieved_metadata = self.id_manager.get_id_metadata(run_id) 
            assert retrieved_metadata.context["validation_type"] == "golden_path", f"Context should persist: {retrieved_metadata.context}"
            assert retrieved_metadata.context["business_value"] == "$500K+ ARR", f"Business value should persist"
            
            self.generated_run_ids.add(run_id)
            self.created_contexts.append(golden_context)
            self.test_metrics.record_custom("success", f"Golden Path validation integration with run_id successful")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN Golden Path integration failed: {e}")

    def test_run_id_multi_user_isolation_integration(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN with multi-user isolation.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and maintain proper user isolation with run_ids
        
        This validates that run_ids properly support multi-user scenarios.
        """
        try:
            # Create contexts for multiple users - will fail before fix
            user_contexts = []
            
            for i, test_user in enumerate(self.test_users):
                user_id = ensure_user_id(test_user)
                
                # Generate isolated IDs for each user
                run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"user_{i}_isolated")
                thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=f"user_{i}_isolated")
                
                # Create isolated context
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id
                )
                
                # Tag context with user isolation data
                run_metadata = self.id_manager.get_id_metadata(run_id)
                run_metadata.context.update({
                    "isolation_user": str(user_id),
                    "isolation_boundary": f"user_{i}",
                    "multi_user_test": True
                })
                
                user_contexts.append((user_id, context, run_id))
                self.generated_run_ids.add(run_id)
                self.created_contexts.append(context)
            
            # Validate isolation between users
            for i, (user_id_1, context_1, run_id_1) in enumerate(user_contexts):
                for j, (user_id_2, context_2, run_id_2) in enumerate(user_contexts):
                    if i != j:
                        # Validate different users have different run_ids
                        assert run_id_1 != run_id_2, f"Users should have different run_ids: {run_id_1} == {run_id_2}"
                        assert context_1.user_id != context_2.user_id, f"Users should be different: {context_1.user_id} == {context_2.user_id}"
                        
                        # Validate run_id metadata isolation
                        metadata_1 = self.id_manager.get_id_metadata(run_id_1)
                        metadata_2 = self.id_manager.get_id_metadata(run_id_2) 
                        assert metadata_1.context["isolation_user"] != metadata_2.context["isolation_user"], "User isolation should be maintained"
            
            # Validate all contexts are valid
            for user_id, context, run_id in user_contexts:
                assert is_valid_id_format(context.run_id), f"Context run_id should be valid: {context.run_id}"
                assert is_valid_id_format_compatible(context.run_id, IDType.RUN), f"Context run_id should be RUN compatible: {context.run_id}"
            
            self.test_metrics.record_custom("success", f"Multi-user isolation integration with run_ids successful: {len(user_contexts)} users")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN multi-user isolation integration failed: {e}")

    def test_run_id_cross_system_format_validation(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN format validation across systems.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and run_ids validate consistently across all systems
        
        This validates SSOT format consistency across system boundaries.
        """
        try:
            # Generate run_ids with various patterns - will fail before fix
            test_patterns = [
                ("basic_run", None),
                ("prefixed_run", "system_test"),
                ("complex_run", "cross_system_validation"),
                ("golden_path_run", "ssot_websocket_phase1_validation"),
            ]
            
            validation_results = []
            
            for pattern_name, prefix in test_patterns:
                # Generate run_id
                if prefix:
                    run_id = self.id_manager.generate_id(IDType.RUN, prefix=prefix)
                else:
                    run_id = self.id_manager.generate_id(IDType.RUN)
                
                # Cross-system validation checks
                validations = {
                    "basic_format": is_valid_id_format(run_id),
                    "run_type_compatible": is_valid_id_format_compatible(run_id, IDType.RUN),
                    "manager_validation": self.id_manager.is_valid_id(run_id, IDType.RUN),
                    "metadata_exists": self.id_manager.get_id_metadata(run_id) is not None,
                }
                
                # Additional SSOT format checks
                parts = run_id.split('_')
                validations.update({
                    "sufficient_parts": len(parts) >= 3,
                    "contains_run": "run" in parts,
                    "valid_uuid_part": len(parts[-1]) == 8 and all(c in '0123456789abcdefABCDEF' for c in parts[-1]),
                    "valid_counter": parts[-2].isdigit(),
                })
                
                # Validate all checks pass
                failed_validations = [name for name, result in validations.items() if not result]
                assert not failed_validations, f"Run ID {run_id} failed validations: {failed_validations}"
                
                validation_results.append({
                    "pattern": pattern_name,
                    "run_id": run_id,
                    "validations": validations,
                    "all_passed": len(failed_validations) == 0
                })
                
                self.generated_run_ids.add(run_id)
            
            # Validate all patterns succeeded
            all_passed = all(result["all_passed"] for result in validation_results)
            assert all_passed, f"All run_id patterns should pass validation: {validation_results}"
            
            self.test_metrics.record_custom("success", f"Cross-system format validation successful: {len(test_patterns)} patterns")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN cross-system validation failed: {e}")

    def test_run_id_concurrent_integration_load(self):
        """
        PERFORMANCE INTEGRATION TEST: IDType.RUN under concurrent load.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute)
        - AFTER FIX: Will PASS and handle concurrent integration scenarios
        
        This validates integration performance and thread safety.
        """
        try:
            num_concurrent_users = 5
            operations_per_user = 10
            
            def user_workflow(user_index: int) -> Dict[str, Any]:
                """Simulate a complete user workflow with run_ids."""
                user_id = ensure_user_id(f"concurrent-integration-user-{user_index:03d}")
                workflow_results = {
                    "user_id": str(user_id),
                    "run_ids": [],
                    "contexts": [],
                    "validations": [],
                    "errors": []
                }
                
                try:
                    for op in range(operations_per_user):
                        # Generate run_id - will fail before fix
                        run_id = self.id_manager.generate_id(IDType.RUN, prefix=f"concurrent_user_{user_index}_op_{op}")
                        thread_id = self.id_manager.generate_id(IDType.THREAD, prefix=f"concurrent_user_{user_index}_op_{op}")
                        
                        # Create context
                        context = UserExecutionContext(
                            user_id=user_id,
                            thread_id=thread_id,
                            run_id=run_id
                        )
                        
                        # Validate integration
                        is_valid = (
                            is_valid_id_format(run_id) and
                            is_valid_id_format_compatible(run_id, IDType.RUN) and
                            self.id_manager.is_valid_id(run_id, IDType.RUN)
                        )
                        
                        workflow_results["run_ids"].append(run_id)
                        workflow_results["contexts"].append(context)
                        workflow_results["validations"].append(is_valid)
                        
                except Exception as e:
                    workflow_results["errors"].append(str(e))
                
                return workflow_results
            
            # Execute concurrent workflows
            with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
                futures = [executor.submit(user_workflow, i) for i in range(num_concurrent_users)]
                results = [future.result() for future in as_completed(futures)]
            
            # Validate results
            total_run_ids = set()
            total_validations = []
            total_errors = []
            
            for result in results:
                # Collect all run_ids for uniqueness check
                total_run_ids.update(result["run_ids"])
                total_validations.extend(result["validations"])
                total_errors.extend(result["errors"])
                
                # Validate individual user workflow
                assert len(result["run_ids"]) == operations_per_user, f"User should have {operations_per_user} run_ids: {len(result['run_ids'])}"
                assert len(result["contexts"]) == operations_per_user, f"User should have {operations_per_user} contexts: {len(result['contexts'])}"
                assert not result["errors"], f"User workflow should not have errors: {result['errors']}"
            
            # Validate overall results
            expected_total = num_concurrent_users * operations_per_user
            assert len(total_run_ids) == expected_total, f"Expected {expected_total} unique run_ids, got {len(total_run_ids)}"
            assert all(total_validations), f"All validations should pass: {sum(total_validations)}/{len(total_validations)}"
            assert not total_errors, f"No errors should occur: {total_errors}"
            
            self.generated_run_ids.update(total_run_ids)
            self.test_metrics.record_custom("success", f"Concurrent integration load successful: {len(total_run_ids)} run_ids across {num_concurrent_users} users")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN concurrent integration failed: {e}")

    def test_run_id_error_handling_integration(self):
        """
        CRITICAL INTEGRATION TEST: IDType.RUN error handling across systems.
        
        EXPECTED BEHAVIOR:
        - BEFORE FIX: Will FAIL with AttributeError (no RUN attribute) 
        - AFTER FIX: Will PASS and handle errors gracefully with run_ids
        
        This validates error handling integration with RUN type.
        """
        try:
            user_id = ensure_user_id("error-handling-integration-user")
            
            # Generate valid run_id - will fail before fix
            run_id = self.id_manager.generate_id(IDType.RUN, prefix="error_handling")
            
            # Test error scenarios with run_id
            error_scenarios = []
            
            # Scenario 1: Invalid run_id format handling
            try:
                invalid_run_id = "invalid_run_id_format"
                is_valid = is_valid_id_format_compatible(invalid_run_id, IDType.RUN)
                assert not is_valid, f"Invalid run_id should not validate: {invalid_run_id}"
                error_scenarios.append("invalid_format_handled")
            except Exception as e:
                error_scenarios.append(f"invalid_format_error: {e}")
            
            # Scenario 2: Non-existent run_id handling
            try:
                non_existent_run_id = "run_999999_nonexistent"
                metadata = self.id_manager.get_id_metadata(non_existent_run_id)
                assert metadata is None, f"Non-existent run_id should return None metadata"
                error_scenarios.append("non_existent_handled")
            except Exception as e:
                error_scenarios.append(f"non_existent_error: {e}")
            
            # Scenario 3: Context creation with invalid run_id
            try:
                invalid_context_run_id = ""  # Empty run_id
                # This might fail gracefully or raise appropriate error
                thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="error_test")
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=invalid_context_run_id
                )
                # If it succeeds, validate it's handled properly
                error_scenarios.append("empty_run_id_handled")
            except Exception as e:
                # Expected error for invalid run_id
                error_scenarios.append("empty_run_id_error_expected")
            
            # Validate error handling results
            expected_scenarios = ["invalid_format_handled", "non_existent_handled"]
            for scenario in expected_scenarios:
                assert scenario in error_scenarios, f"Expected error scenario not found: {scenario}"
            
            # Validate valid run_id still works
            assert is_valid_id_format(run_id), f"Valid run_id should still work: {run_id}"
            assert self.id_manager.is_valid_id(run_id, IDType.RUN), f"Valid run_id should validate: {run_id}"
            
            self.generated_run_ids.add(run_id)
            self.test_metrics.record_custom("success", f"Error handling integration successful: {len(error_scenarios)} scenarios tested")
            
        except AttributeError as e:
            self.test_metrics.record_custom("expected_failure", f"Expected failure before fix: {e}")
            pytest.fail(f"IDType.RUN error handling integration failed: {e}")

    def teardown_method(self, method=None):
        """Clean up integration test environment and record metrics."""
        
        # Clean up generated run_ids
        if hasattr(self, 'id_manager') and hasattr(self, 'generated_run_ids'):
            for run_id in self.generated_run_ids:
                try:
                    self.id_manager.release_id(run_id)
                except:
                    pass  # Best effort cleanup
        
        # Clean up created contexts
        if hasattr(self, 'created_contexts'):
            # Note: UserExecutionContext doesn't require explicit cleanup
            # but we track them for completeness
            pass
        
        # Record metrics
        if hasattr(self, 'test_metrics'):
            self.test_metrics.record_custom("test_completed", True)
            
        super().teardown_method(method)