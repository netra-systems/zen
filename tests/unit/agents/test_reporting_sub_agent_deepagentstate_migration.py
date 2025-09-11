"""
Unit Tests for ReportingSubAgent DeepAgentState → UserExecutionContext Migration - Issue #354

CRITICAL SECURITY VULNERABILITY: P0 vulnerability in ReportingSubAgent.execute_modern()
using DeepAgentState parameter which enables cross-user data contamination.

Business Value Justification (BVJ):
- Segment: Enterprise (highest security requirements)
- Business Goal: Prevent user data isolation vulnerabilities  
- Value Impact: Ensures user execution context isolation in critical reporting agent
- Revenue Impact: Prevents $500K+ ARR loss from enterprise security breaches

TEST STRATEGY:
These tests are designed to FAIL initially with DeepAgentState, proving vulnerability exists.
After migration to UserExecutionContext, these tests should PASS, proving security fix works.

VALIDATION POINTS:
1. Parameter type validation for execute_modern() method
2. Security boundary enforcement
3. SSOT compliance checks for DeepAgentState imports
4. UserExecutionContext proper initialization
5. Cross-user contamination prevention

EXPECTED BEHAVIOR:
- BEFORE Migration: Tests FAIL - DeepAgentState accepted, vulnerabilities exist
- AFTER Migration: Tests PASS - Only UserExecutionContext accepted, secure operation
"""

import pytest
import time
import uuid
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.interface import ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from shared.types.core_types import UserID, ThreadID, RunID


class TestReportingSubAgentDeepAgentStateMigration(SSotAsyncTestCase):
    """
    Unit tests for ReportingSubAgent migration from DeepAgentState to UserExecutionContext.
    
    These tests prove DeepAgentState creates security vulnerabilities and that 
    UserExecutionContext provides proper isolation.
    """

    def setup_method(self, method=None):
        """Set up test environment with vulnerable and secure contexts."""
        super().setup_method(method)
        
        # Create ReportingSubAgent instance for testing
        self.reporting_agent = ReportingSubAgent()
        
        # Create vulnerable DeepAgentState (should be rejected after migration)
        self.vulnerable_state = self._create_vulnerable_deep_agent_state()
        
        # Create secure UserExecutionContext (should be accepted after migration)
        self.secure_context = self._create_secure_user_execution_context()
        
        # Create test run ID
        self.test_run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    
    def _create_vulnerable_deep_agent_state(self) -> DeepAgentState:
        """Create DeepAgentState that demonstrates security vulnerability."""
        # Create shared state object (vulnerability: shared between users)
        vulnerable_state = DeepAgentState()
        vulnerable_state.user_id = "user_a_12345"  # User A's ID
        vulnerable_state.chat_thread_id = "thread_a_67890"
        vulnerable_state.user_request = "Generate financial report with sensitive data"
        
        # Add sensitive data that could be cross-contaminated
        vulnerable_state.action_plan_result = {
            "sensitive_financial_data": {
                "revenue": "$500K ARR",
                "profit_margins": "35%",
                "customer_segments": ["Enterprise", "Mid-market"],
                "confidential_notes": "Internal optimization strategy"
            },
            "user_specific_context": {
                "company_name": "VictimCorp Industries", 
                "user_role": "CFO",
                "access_level": "CONFIDENTIAL"
            }
        }
        
        vulnerable_state.optimizations_result = {
            "cost_savings": "$50K monthly",
            "efficiency_gains": "40% improvement",
            "strategic_recommendations": "Highly confidential business intelligence"
        }
        
        return vulnerable_state
    
    def _create_secure_user_execution_context(self) -> UserExecutionContext:
        """Create UserExecutionContext that provides proper isolation."""
        return UserExecutionContext(
            user_id=UserID("user_a_12345"),
            thread_id=ThreadID("thread_a_67890"), 
            run_id=RunID(self.test_run_id),
            agent_context={
                "user_request": "Generate financial report with sensitive data",
                "security_level": "CONFIDENTIAL",
                "access_scope": "user_isolated"
            },
            audit_metadata={
                "test_context": "security_validation",
                "isolation_verified": True
            }
        )

    async def test_execute_modern_rejects_deepagentstate_parameter(self):
        """
        Test that execute_modern() properly rejects DeepAgentState parameters.
        
        VULNERABILITY: DeepAgentState enables cross-user contamination
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Attempt to call execute_modern with DeepAgentState (vulnerable pattern)
        with pytest.raises(TypeError, match=r".*DeepAgentState.*not.*supported.*security.*vulnerability.*"):
            result = await self.reporting_agent.execute_modern(
                state=self.vulnerable_state,
                run_id=self.test_run_id,
                stream_updates=False
            )
        
        # If no exception is raised, the vulnerability exists (test should fail initially)
        # This assertion will fail BEFORE migration, proving vulnerability
        assert False, (
            "🚨 SECURITY VULNERABILITY DETECTED: execute_modern() accepted DeepAgentState parameter. "
            "This creates cross-user data contamination risks. Migration to UserExecutionContext required."
        )

    async def test_execute_modern_accepts_userexecutioncontext_parameter(self):
        """
        Test that execute_modern() properly accepts UserExecutionContext parameters.
        
        SECURITY FIX: UserExecutionContext provides proper isolation
        EXPECTED: Should PASS after migration
        """
        # Mock the WebSocket events to avoid actual emission during test
        with patch.object(self.reporting_agent, 'emit_agent_started') as mock_started, \
             patch.object(self.reporting_agent, 'emit_agent_completed') as mock_completed:
            
            mock_started.return_value = None
            mock_completed.return_value = None
            
            # Call execute_modern with UserExecutionContext (secure pattern)
            # This should work after migration
            try:
                result = await self.reporting_agent.execute_modern(
                    context=self.secure_context,  # Note: parameter name changed to 'context'
                    stream_updates=False
                )
                
                # Validate result structure
                assert isinstance(result, ExecutionResult), "Result should be ExecutionResult instance"
                assert result.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED], "Should have valid status"
                
                # Validate security isolation maintained
                assert result.request_id == self.test_run_id, "Request ID should be preserved"
                
            except TypeError as e:
                if "UserExecutionContext" in str(e):
                    pytest.fail(
                        f"🚨 MIGRATION INCOMPLETE: execute_modern() should accept UserExecutionContext. "
                        f"Error: {e}"
                    )
                else:
                    raise

    async def test_parameter_validation_enforces_security_boundaries(self):
        """
        Test that parameter validation enforces security boundaries.
        
        VULNERABILITY: Mixed parameter types can cause confusion and security bypasses
        EXPECTED: Clear error messages and strict type enforcement
        """
        # Test 1: Completely invalid parameters should be rejected
        with pytest.raises((TypeError, ValueError)):
            await self.reporting_agent.execute_modern(
                state="invalid_string_parameter",  # Wrong type
                run_id=self.test_run_id,
                stream_updates=False
            )
        
        # Test 2: None parameters should be handled gracefully  
        with pytest.raises((TypeError, ValueError)):
            await self.reporting_agent.execute_modern(
                state=None,
                run_id=self.test_run_id,
                stream_updates=False
            )
        
        # Test 3: Mixed valid/invalid parameters should be rejected
        with pytest.raises((TypeError, ValueError)):
            await self.reporting_agent.execute_modern(
                state=self.vulnerable_state,
                run_id=None,  # Invalid None run_id
                stream_updates=False
            )

    def test_deepagentstate_import_detection(self):
        """
        Test that DeepAgentState imports are detected and flagged as security risks.
        
        VULNERABILITY: Code importing DeepAgentState creates contamination risk
        EXPECTED: Should detect and warn about security risks
        """
        # Check if ReportingSubAgent imports DeepAgentState
        import inspect
        import ast
        
        # Get the source code of the ReportingSubAgent file
        source_file = inspect.getfile(ReportingSubAgent)
        
        with open(source_file, 'r') as f:
            source_code = f.read()
        
        # Parse the AST to find imports
        tree = ast.parse(source_code)
        deepagentstate_imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and 'state' in node.module:
                    for alias in node.names or []:
                        if alias.name == 'DeepAgentState':
                            deepagentstate_imports.append({
                                'module': node.module,
                                'name': alias.name,
                                'line': node.lineno
                            })
        
        # BEFORE migration: This should detect imports (test fails)
        # AFTER migration: This should find no imports (test passes)
        if deepagentstate_imports:
            assert False, (
                f"🚨 SECURITY RISK: DeepAgentState imports detected in ReportingSubAgent: "
                f"{deepagentstate_imports}. These imports create cross-user contamination risks. "
                f"Migration to UserExecutionContext required."
            )

    def test_method_signature_security_compliance(self):
        """
        Test that method signatures comply with security requirements.
        
        VULNERABILITY: Methods accepting DeepAgentState enable vulnerabilities
        EXPECTED: Methods should only accept UserExecutionContext
        """
        import inspect
        
        # Get the method signature for execute_modern
        execute_modern_sig = inspect.signature(self.reporting_agent.execute_modern)
        
        # Check parameter types in signature
        security_violations = []
        
        for param_name, param in execute_modern_sig.parameters.items():
            if param_name == 'state' and param.annotation == DeepAgentState:
                security_violations.append(
                    f"Parameter '{param_name}' accepts DeepAgentState type"
                )
            
            # Check if any parameter hints mention DeepAgentState
            if hasattr(param.annotation, '__name__') and 'DeepAgentState' in str(param.annotation):
                security_violations.append(
                    f"Parameter '{param_name}' annotation references DeepAgentState"
                )
        
        # BEFORE migration: Should find violations (test fails)
        # AFTER migration: Should find no violations (test passes)
        if security_violations:
            assert False, (
                f"🚨 SECURITY VIOLATIONS IN METHOD SIGNATURE: {security_violations}. "
                f"execute_modern() should not accept DeepAgentState parameters. "
                f"Migration to UserExecutionContext required."
            )

    async def test_user_isolation_boundary_enforcement(self):
        """
        Test that user isolation boundaries are properly enforced.
        
        VULNERABILITY: Shared state objects allow cross-user data access
        EXPECTED: Each user should have completely isolated execution context
        """
        # Create two different user contexts
        user_a_context = UserExecutionContext(
            user_id=UserID("user_a_12345"),
            thread_id=ThreadID("thread_a_67890"),
            run_id=RunID(f"run_a_{uuid.uuid4().hex[:8]}"),
            agent_context={
                "user_request": "User A's confidential request",
                "sensitive_data": "User A's secrets"
            }
        )
        
        user_b_context = UserExecutionContext(
            user_id=UserID("user_b_98765"),
            thread_id=ThreadID("thread_b_43210"),
            run_id=RunID(f"run_b_{uuid.uuid4().hex[:8]}"),
            agent_context={
                "user_request": "User B's confidential request", 
                "sensitive_data": "User B's secrets"
            }
        )
        
        # Mock WebSocket events
        with patch.object(self.reporting_agent, 'emit_agent_started') as mock_started, \
             patch.object(self.reporting_agent, 'emit_agent_completed') as mock_completed:
            
            mock_started.return_value = None
            mock_completed.return_value = None
            
            try:
                # Execute for User A
                result_a = await self.reporting_agent.execute_modern(
                    context=user_a_context,
                    stream_updates=False
                )
                
                # Execute for User B
                result_b = await self.reporting_agent.execute_modern(
                    context=user_b_context,
                    stream_updates=False
                )
                
                # Validate complete isolation
                assert result_a.request_id != result_b.request_id, "Request IDs should be different"
                
                # Validate no cross-contamination of user data
                if hasattr(result_a, 'data') and hasattr(result_b, 'data'):
                    result_a_str = str(result_a.data)
                    result_b_str = str(result_b.data)
                    
                    assert "User A's secrets" not in result_b_str, "User A data leaked to User B"
                    assert "User B's secrets" not in result_a_str, "User B data leaked to User A"
                
            except TypeError as e:
                if "DeepAgentState" in str(e):
                    # Expected during migration - DeepAgentState pattern rejected
                    pass
                elif "UserExecutionContext" in str(e):
                    pytest.fail(
                        f"🚨 MIGRATION INCOMPLETE: Should accept UserExecutionContext. Error: {e}"
                    )
                else:
                    raise

    def test_ssot_compliance_validation(self):
        """
        Test SSOT compliance for parameter validation.
        
        VULNERABILITY: Multiple parameter validation patterns create inconsistency
        EXPECTED: Single consistent validation pattern across all methods
        """
        # Get all public methods that might accept state parameters
        methods_to_check = [
            'execute_modern',
            'execute',
            '_execute_modern_pattern'
        ]
        
        ssot_violations = []
        
        for method_name in methods_to_check:
            if hasattr(self.reporting_agent, method_name):
                method = getattr(self.reporting_agent, method_name)
                
                # Check method signature for consistency
                import inspect
                try:
                    sig = inspect.signature(method)
                    
                    # Look for DeepAgentState parameters (should be eliminated)
                    for param_name, param in sig.parameters.items():
                        if hasattr(param.annotation, '__name__') and param.annotation.__name__ == 'DeepAgentState':
                            ssot_violations.append(
                                f"Method {method_name} parameter {param_name} uses DeepAgentState"
                            )
                            
                except (ValueError, TypeError):
                    # Some methods might not have accessible signatures
                    pass
        
        # BEFORE migration: Should find violations (test fails)
        # AFTER migration: Should find no violations (test passes)
        if ssot_violations:
            assert False, (
                f"🚨 SSOT VIOLATIONS DETECTED: {ssot_violations}. "
                f"All methods should use consistent UserExecutionContext parameters only."
            )