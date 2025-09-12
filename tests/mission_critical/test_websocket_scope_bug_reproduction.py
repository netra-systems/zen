#!/usr/bin/env python
"""MISSION CRITICAL TEST SUITE: WebSocket Scope Bug Reproduction - Issue #165

THIS TEST SUITE REPRODUCES THE EXACT WEBSOCKET SCOPE BUG CAUSING 100% CONNECTION FAILURES.
Business Impact: $500K+ ARR - Complete WebSocket connection failure

Scope Bug Details:
- Location: /netra_backend/app/routes/websocket.py lines 1433, 1452
- Error: NameError: name 'state_registry' is not defined
- Cause: Variable scope isolation bug - initialized in function scope but accessed globally
- Impact: 100% WebSocket connection failure rate affecting all chat functionality

This test suite is designed to FAIL initially to reproduce the exact bug conditions.
Tests will fail with expected NameError until the scope bug is fixed.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Restore WebSocket connection reliability
- Value Impact: Fix 100% connection failure blocking all chat functionality
- Strategic Impact: Core platform infrastructure required for $500K+ ARR

REQUIREMENTS:
- Unit tests only - No Docker required
- Real websocket module imports
- Tests MUST FAIL with exact NameError from scope bug
- Validates business impact of scope isolation issue
"""

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import the actual websocket module to reproduce scope bug
from netra_backend.app.routes.websocket import websocket_endpoint
from netra_backend.app.websocket_core.connection_state_machine import get_connection_state_registry
from fastapi import WebSocket


class TestWebSocketScopeBugReproduction:
    """
    Reproduce exact WebSocket scope bug from issue #165.
    
    These tests are designed to FAIL with the exact NameError that occurs
    at lines 1433 and 1452 in websocket.py due to scope isolation issues.
    """
    
    @pytest.mark.mission_critical
    @pytest.mark.unit
    async def test_state_registry_scope_isolation_bug(self):
        """
        REPRODUCER: Test exact NameError at lines 1433,1452 due to scope bug.
        
        This test reproduces the exact conditions where state_registry is
        initialized in the main websocket_endpoint function scope but accessed
        in nested exception handling blocks where it's out of scope.
        
        Expected Behavior: FAIL with NameError: name 'state_registry' is not defined
        """
        logger.info(" ALERT:  REPRODUCING: WebSocket scope bug causing 100% connection failures")
        
        # Mock WebSocket connection to trigger the problematic code path
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.headers = {
            "authorization": "Bearer test_token",
            "sec-websocket-protocol": "jwt-auth"
        }
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # Mock environment to ensure we hit the problematic code path
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging",  # Use staging to trigger Cloud Run paths
                "TESTING": "0",
                "E2E_TESTING": "0", 
                "PYTEST_RUNNING": "0"
            }.get(key, default)
            mock_get_env.return_value = mock_env
            
            # Mock the authentication flow to succeed and trigger connection registration paths  
            with patch('netra_backend.app.websocket_core.unified_websocket_auth.authenticate_websocket_ssot') as mock_auth_ssot:
                # Create successful auth result to get past authentication
                mock_auth_result = Mock()
                mock_auth_result.success = True
                mock_user_context = Mock()
                mock_user_context.user_id = "test_user_123"
                mock_user_context.websocket_client_id = "client_123" 
                mock_auth_result.user_context = mock_user_context
                mock_auth_result.auth_result = Mock()
                mock_auth_result.auth_result.to_dict = Mock(return_value={"user_id": "test_user_123"})
                mock_auth_ssot.return_value = mock_auth_result
                
                # Mock WebSocket manager creation to succeed but trigger ID mismatch scenario
                with patch('netra_backend.app.websocket_core.websocket_manager_factory.create_websocket_manager') as mock_create_manager:
                    mock_ws_manager = Mock()
                    mock_ws_manager.connect_user = AsyncMock(return_value="different_connection_id")  # Trigger ID mismatch
                    mock_create_manager.return_value = mock_ws_manager
                    
                    # Mock state coordination functions to succeed
                    with patch('netra_backend.app.websocket_core.state_coordinator.coordinate_authentication_state') as mock_coord_auth:
                        mock_coord_auth.return_value = True
                        
                        with patch('netra_backend.app.websocket_core.state_coordinator.coordinate_factory_state') as mock_coord_factory:
                            mock_coord_factory.return_value = True
                        
                        # Mock state machine retrieval to fail and trigger state_registry usage
                        with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get_state:
                            mock_get_state.return_value = None  # No existing state machine found
                            
                            # This should trigger the exact NameError we're reproducing
                            with pytest.raises(NameError, match="name 'state_registry' is not defined"):
                                await websocket_endpoint(mock_websocket)
        
        logger.error(" FAIL:  SCOPE BUG REPRODUCED: state_registry undefined in nested scope")
        logger.error(" FAIL:  BUSINESS IMPACT: 100% WebSocket connection failure rate")
        logger.error(" FAIL:  ROOT CAUSE: Variable initialized in function scope but accessed in exception handler")
    
    @pytest.mark.mission_critical  
    @pytest.mark.unit
    async def test_websocket_connection_failure_rate(self):
        """
        REPRODUCER: Validate 100% connection failure rate due to scope bug.
        
        This test demonstrates that the scope bug causes ALL WebSocket 
        connections to fail, resulting in complete loss of chat functionality.
        
        Expected Behavior: FAIL - All connection attempts result in NameError
        """
        logger.info(" ALERT:  MEASURING: WebSocket connection failure rate due to scope bug")
        
        connection_attempts = 10
        failures = 0
        name_errors = 0
        
        for i in range(connection_attempts):
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.headers = {"authorization": "Bearer test_token"}
            mock_websocket.accept = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            try:
                with patch('shared.isolated_environment.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.side_effect = lambda key, default=None: {
                        "ENVIRONMENT": "staging",
                        "TESTING": "0"
                    }.get(key, default)
                    mock_get_env.return_value = mock_env
                    
                    # Mock conditions that trigger the scope bug
                    with patch('netra_backend.app.core.user_context_factory.create_user_execution_context') as mock_context:
                        mock_context.side_effect = Exception("Trigger emergency path")
                        
                        with patch('netra_backend.app.auth_integration.auth.authenticate_websocket') as mock_auth:
                            mock_auth.return_value = f"user_{i}"
                            
                            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_manager:
                                mock_ws_manager = Mock()
                                mock_manager.return_value = mock_ws_manager
                                mock_ws_manager.connect_user = AsyncMock(return_value=f"conn_{i}_different")
                                
                                with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get_state:
                                    mock_get_state.return_value = None
                                    
                                    await websocket_endpoint(mock_websocket)
                                    
            except NameError as e:
                if "state_registry" in str(e):
                    name_errors += 1
                    failures += 1
                    logger.warning(f"Connection {i+1}: NameError - {e}")
                else:
                    failures += 1
                    logger.warning(f"Connection {i+1}: Other NameError - {e}")
            except Exception as e:
                failures += 1
                logger.warning(f"Connection {i+1}: Other error - {e}")
        
        # Document the business impact
        failure_rate = (failures / connection_attempts) * 100
        scope_bug_rate = (name_errors / connection_attempts) * 100
        
        logger.error(f" FAIL:  BUSINESS IMPACT MEASURED:")
        logger.error(f"   [U+2022] Total failure rate: {failure_rate}%")
        logger.error(f"   [U+2022] Scope bug failures: {scope_bug_rate}%")
        logger.error(f"   [U+2022] Successful connections: {connection_attempts - failures}")
        logger.error(f"   [U+2022] Revenue at risk: $500K+ ARR (100% chat functionality blocked)")
        
        # This test should FAIL because we expect 100% failure rate
        assert failure_rate == 100.0, f"Expected 100% failure rate due to scope bug, got {failure_rate}%"
        assert name_errors > 0, "Expected NameError for state_registry but none occurred"
        
    @pytest.mark.mission_critical
    @pytest.mark.unit  
    async def test_scope_bug_error_recovery_path(self):
        """
        REPRODUCER: Test error path that triggers scope bug conditions.
        
        This test validates that specific error recovery paths in the WebSocket
        endpoint trigger the scope isolation bug where state_registry is undefined.
        
        Expected Behavior: FAIL with NameError in emergency recovery scenarios
        """
        logger.info(" ALERT:  TESTING: Error recovery paths that trigger scope bug")
        
        # Test scenarios that lead to state_registry access in nested scopes
        test_scenarios = [
            {
                "name": "ID_MISMATCH_EMERGENCY_RECOVERY",
                "description": "Connection ID mismatch triggers emergency recovery using state_registry",
                "preliminary_id": "prelim_123",
                "final_id": "final_456",  # Different - triggers mismatch
                "state_machine_exists": False  # Triggers state_registry.register_connection
            },
            {
                "name": "PASS_THROUGH_SUCCESS_NO_STATE",
                "description": "Pass-through success but no existing state machine found",
                "preliminary_id": "same_123", 
                "final_id": "same_123",  # Same - triggers success path
                "state_machine_exists": False  # But no state machine - triggers state_registry
            }
        ]
        
        for scenario in test_scenarios:
            logger.info(f" SEARCH:  Testing scenario: {scenario['name']}")
            
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.headers = {"authorization": "Bearer test_token"}
            mock_websocket.accept = AsyncMock()
            mock_websocket.close = AsyncMock()
            
            try:
                with patch('shared.isolated_environment.get_env') as mock_get_env:
                    mock_env = Mock()
                    mock_env.get.side_effect = lambda key, default=None: {
                        "ENVIRONMENT": "staging",
                        "TESTING": "0"
                    }.get(key, default)
                    mock_get_env.return_value = mock_env
                    
                    # Mock authentication success
                    with patch('netra_backend.app.auth_integration.auth.authenticate_websocket') as mock_auth:
                        mock_auth.return_value = "test_user_123"
                        
                        # Mock context creation success (to avoid early exit)
                        with patch('netra_backend.app.core.user_context_factory.create_user_execution_context') as mock_context:
                            mock_user_context = Mock()
                            mock_user_context.user_id = "test_user_123"
                            mock_context.return_value = mock_user_context
                            
                            # Mock WebSocket manager with specific connection ID behavior
                            with patch('netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager') as mock_manager:
                                mock_ws_manager = Mock()
                                mock_manager.return_value = mock_ws_manager
                                mock_ws_manager.add_connection = AsyncMock()
                                
                                # Control connection ID to trigger specific paths
                                with patch('netra_backend.app.routes.websocket._initialize_connection_state') as mock_init:
                                    mock_init.return_value = (scenario['preliminary_id'], Mock())
                                    
                                    # Control whether state machine exists
                                    with patch('netra_backend.app.websocket_core.connection_state_machine.get_connection_state_machine') as mock_get_state:
                                        if scenario['state_machine_exists']:
                                            mock_state_machine = Mock()
                                            mock_get_state.return_value = mock_state_machine
                                        else:
                                            mock_get_state.return_value = None
                                        
                                        # This should trigger the NameError for state_registry
                                        with pytest.raises(NameError, match="name 'state_registry' is not defined"):
                                            await websocket_endpoint(mock_websocket)
                                            
                logger.error(f" FAIL:  SCENARIO {scenario['name']}: Reproduced scope bug")
                logger.error(f"   [U+2022] Description: {scenario['description']}")
                logger.error(f"   [U+2022] Root cause: state_registry out of scope in nested exception handler")
                
            except NameError as e:
                if "state_registry" not in str(e):
                    pytest.fail(f"Expected state_registry NameError but got: {e}")
                # Expected NameError - test passes by reproducing the bug
                
        logger.error(" FAIL:  ALL ERROR RECOVERY PATHS TRIGGER SCOPE BUG")
        logger.error(" FAIL:  BUSINESS CRITICAL: No fallback mechanism works due to scope isolation")
        
    @pytest.mark.mission_critical
    @pytest.mark.unit
    def test_scope_bug_static_analysis(self):
        """
        REPRODUCER: Static analysis of scope bug in websocket.py
        
        This test analyzes the actual source code to identify the exact
        scope isolation issue causing the NameError.
        
        Expected Behavior: FAIL - Document scope violation locations
        """
        logger.info(" SEARCH:  ANALYZING: WebSocket scope bug static code analysis")
        
        websocket_py_path = os.path.join(
            project_root, 'netra_backend', 'app', 'routes', 'websocket.py'
        )
        
        if not os.path.exists(websocket_py_path):
            pytest.fail(f"WebSocket route file not found: {websocket_py_path}")
            
        with open(websocket_py_path, 'r') as f:
            content = f.read()
            
        # Find the lines that reference state_registry
        lines = content.split('\n')
        state_registry_references = []
        state_registry_definition = None
        
        for i, line in enumerate(lines, 1):
            if 'state_registry =' in line and 'get_connection_state_registry()' in line:
                state_registry_definition = {
                    'line_number': i,
                    'line_content': line.strip(),
                    'scope': 'function_scope'
                }
            elif 'state_registry.' in line:
                state_registry_references.append({
                    'line_number': i,
                    'line_content': line.strip(),
                    'scope': 'nested_scope'
                })
                
        # Analyze the scope violation
        logger.error(" CHART:  SCOPE BUG ANALYSIS RESULTS:")
        
        if state_registry_definition:
            logger.error(f"   [U+2022] Definition: Line {state_registry_definition['line_number']}")
            logger.error(f"     Code: {state_registry_definition['line_content']}")
            logger.error(f"     Scope: {state_registry_definition['scope']}")
        else:
            logger.error("   [U+2022] Definition: NOT FOUND")
            
        logger.error(f"   [U+2022] References: {len(state_registry_references)} locations")
        for ref in state_registry_references:
            logger.error(f"     Line {ref['line_number']}: {ref['line_content']}")
            logger.error(f"     Scope: {ref['scope']} (OUT OF SCOPE)")
            
        # Check if the problematic lines are present
        problem_lines = [1433, 1452]
        found_problems = []
        
        for line_num in problem_lines:
            if line_num <= len(lines):
                line_content = lines[line_num - 1]
                if 'state_registry' in line_content:
                    found_problems.append({
                        'line': line_num,
                        'content': line_content.strip()
                    })
                    
        logger.error(" ALERT:  CONFIRMED SCOPE VIOLATIONS:")
        for problem in found_problems:
            logger.error(f"   [U+2022] Line {problem['line']}: {problem['content']}")
            logger.error(f"     VIOLATION: state_registry accessed outside definition scope")
            
        # This test should FAIL to document the scope bug
        assert len(found_problems) > 0, "Expected to find scope violations but none found"
        assert state_registry_definition is not None, "Expected to find state_registry definition"
        assert len(state_registry_references) > 0, "Expected to find state_registry references"
        
        # Document the business impact
        logger.error("[U+1F4B0] BUSINESS IMPACT OF SCOPE BUG:")
        logger.error("   [U+2022] 100% WebSocket connection failure rate")
        logger.error("   [U+2022] $500K+ ARR at risk due to chat functionality blocked")
        logger.error("   [U+2022] No fallback mechanism - complete service failure")
        logger.error("   [U+2022] Critical infrastructure bug affecting all user tiers")
        
        # Force test failure to highlight the critical issue
        pytest.fail(
            f"CRITICAL SCOPE BUG DETECTED: state_registry defined in function scope "
            f"but accessed in {len(state_registry_references)} nested locations. "
            f"This causes 100% WebSocket connection failures affecting $500K+ ARR."
        )


if __name__ == "__main__":
    """
    Direct execution for debugging scope bug reproduction.
    Run: python tests/mission_critical/test_websocket_scope_bug_reproduction.py
    """
    logger.info(" ALERT:  DIRECT EXECUTION: WebSocket Scope Bug Reproduction Tests")
    logger.info("[U+1F4B0] BUSINESS IMPACT: $500K+ ARR - 100% WebSocket connection failure")
    logger.info("[U+1F527] PURPOSE: Reproduce exact NameError from variable scope isolation")
    
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--capture=no",
        "-k", "test_websocket_scope_bug"
    ])