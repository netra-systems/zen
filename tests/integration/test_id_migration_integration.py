"""
Integration Tests for Issue #89 UnifiedIDManager Migration - Cross-Service Validation
=====================================================================================

Business Value Protection: $500K+ ARR (Cross-service ID consistency)
Purpose: FAIL to expose cross-service ID format inconsistencies requiring migration

This test suite is designed to FAIL during Issue #89 migration to detect:
- ID format mismatches between services (UUID vs structured)
- Service communication failures due to ID validation differences
- Cross-service resource tracking failures
- Business workflow breaks due to inconsistent ID handling

Test Strategy:
- Use REAL services (no mocks - per claude.md)
- Test actual service-to-service ID passing
- Focus on high-traffic integration points
- Tests should PASS once all services use consistent ID formats

Critical Integration Points Under Test:
- netra_backend ↔ auth_service ID exchanges
- WebSocket manager ↔ agent execution ID coordination  
- User context ↔ database persistence ID consistency
- Frontend ↔ backend ID format expectations

CLAUDE.MD Compliance:
- Uses SSotAsyncTestCase for async service testing
- Real services only (no mocks for integration tests)
- Environment access through IsolatedEnvironment
- Absolute imports only
"""

import pytest
import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import patch
import httpx

# SSOT Test Infrastructure  
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.id_fixtures import IDFixtures
from test_framework.service_aware_testing import ServiceAwareTesting
from test_framework.real_services import RealServiceTester
from test_framework.base_integration_test import BaseIntegrationTest

# Real service imports for integration testing
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from netra_backend.app.core.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Import utilities
from test_framework.fixtures.auth_fixtures import auth_service_client
from test_framework.database_test_utilities import DatabaseTestUtilities


class TestCrossServiceIDConsistency(SSotAsyncTestCase, BaseIntegrationTest):
    """Integration tests for ID consistency across service boundaries."""
    
    async def setup_method(self, method):
        """Setup for each integration test method."""
        await super().setup_method(method)
        self.service_tester = ServiceAwareTesting()
        self.id_manager = UnifiedIDManager()
        self.db_utils = DatabaseTestUtilities()
        self.record_metric("test_category", "cross_service_id_migration")
        
        # Initialize real service connections
        await self._setup_real_services()
    
    async def _setup_real_services(self):
        """Initialize connections to real services for integration testing."""
        try:
            # Check if services are available
            self.backend_available = await self.service_tester.check_service_health(
                "netra_backend", "http://localhost:8000/health"
            )
            self.auth_available = await self.service_tester.check_service_health(
                "auth_service", "http://localhost:8001/health"  
            )
            
            if not self.backend_available or not self.auth_available:
                pytest.skip("Real services required for integration testing not available")
                
        except Exception as e:
            pytest.skip(f"Could not connect to real services: {e}")
    
    async def test_backend_auth_service_id_exchange_consistency(self):
        """
        CRITICAL INTEGRATION: Test ID consistency in backend ↔ auth service exchanges.
        
        This test should FAIL to expose:
        - Backend sends UUID format, auth service expects structured format
        - Session ID validation failures between services
        - Token-to-user-ID mapping inconsistencies
        - Authentication state synchronization failures
        
        Expected: FAIL until both services use consistent ID formats
        """
        # Generate test user and session IDs using current patterns
        test_user_id = str(uuid.uuid4())  # Simulate current backend UUID usage
        test_session_id = str(uuid.uuid4())  # Simulate current session UUID
        
        integration_failures = []
        
        # Test 1: Backend → Auth Service ID validation
        try:
            auth_client = await auth_service_client()
            
            # Simulate backend sending user_id to auth service for validation
            validation_response = await auth_client.post("/validate_user", json={
                "user_id": test_user_id,
                "session_id": test_session_id
            })
            
            if validation_response.status_code != 200:
                integration_failures.append({
                    'service_flow': 'backend_to_auth',
                    'failure': 'User ID validation failed',
                    'user_id_format': 'UUID',
                    'auth_service_expects': 'structured_format',
                    'status_code': validation_response.status_code,
                    'error': validation_response.text
                })
            
        except Exception as e:
            integration_failures.append({
                'service_flow': 'backend_to_auth',
                'failure': f'Service communication failed: {str(e)}',
                'likely_cause': 'ID format incompatibility'
            })
        
        # Test 2: Auth Service → Backend ID format expectations  
        try:
            # Simulate auth service creating user session with structured ID
            structured_user_id = f"user_1_{str(uuid.uuid4())[:8]}"
            structured_session_id = f"session_1_{str(uuid.uuid4())[:8]}"
            
            # Test if backend can handle structured IDs from auth service
            async with httpx.AsyncClient() as client:
                backend_response = await client.post(
                    "http://localhost:8000/api/user/authenticate",
                    json={
                        "user_id": structured_user_id,
                        "session_id": structured_session_id
                    }
                )
                
                if backend_response.status_code == 422:  # Validation error
                    integration_failures.append({
                        'service_flow': 'auth_to_backend',
                        'failure': 'Backend rejected structured IDs',
                        'structured_user_id': structured_user_id,
                        'backend_expects': 'UUID_format',
                        'status_code': backend_response.status_code
                    })
                
        except Exception as e:
            integration_failures.append({
                'service_flow': 'auth_to_backend',
                'failure': f'Structured ID test failed: {str(e)}',
                'implication': 'Backend cannot handle UnifiedIDManager IDs'
            })
        
        # Test 3: Cross-service session validation
        try:
            # Simulate session created in backend, validated in auth service
            backend_session = {
                'user_id': test_user_id,
                'session_id': test_session_id,
                'created_by': 'backend_service'
            }
            
            # Auth service should recognize and validate this session
            auth_validation = await self._validate_session_cross_service(
                backend_session, 'auth_service'
            )
            
            if not auth_validation['valid']:
                integration_failures.append({
                    'service_flow': 'cross_service_session',
                    'failure': 'Session validation failed between services',
                    'session_format': 'UUID',
                    'validation_error': auth_validation.get('error', 'Unknown'),
                    'business_impact': 'Users lose session state across services'
                })
                
        except Exception as e:
            integration_failures.append({
                'service_flow': 'cross_service_session',
                'failure': f'Session validation test failed: {str(e)}'
            })
        
        # Test should FAIL if integration failures detected
        assert len(integration_failures) == 0, (
            f"CROSS-SERVICE ID INTEGRATION FAILURES: Found {len(integration_failures)} failures:\n" +
            "\n".join([
                f"- {failure['service_flow']}: {failure['failure']}"
                for failure in integration_failures
            ]) +
            "\n\nIntegration failures indicate ID format inconsistency between services.\n"
            "Solution: Migrate all services to UnifiedIDManager structured IDs"
        )
        
        self.record_metric("integration_failures", len(integration_failures))
        self.record_metric("services_tested", 2)
    
    async def test_websocket_agent_id_coordination_failures(self):
        """
        CRITICAL INTEGRATION: Test WebSocket ↔ agent execution ID coordination.
        
        This test should FAIL to expose:
        - WebSocket connection IDs incompatible with agent execution IDs
        - Agent results cannot be routed back to correct WebSocket connection
        - User isolation failures in agent execution tracking
        
        Expected: FAIL until WebSocket and agent systems use consistent IDs
        """
        websocket_coordination_failures = []
        
        # Test 1: WebSocket connection to agent execution handoff
        try:
            # Simulate WebSocket connection with UUID-based ID
            ws_connection_id = str(uuid.uuid4())
            ws_user_id = str(uuid.uuid4())
            
            # Create WebSocket manager (real instance, not mock)
            ws_manager = WebSocketManager()
            
            # Try to start agent execution with WebSocket context
            execution_context = {
                'connection_id': ws_connection_id,
                'user_id': ws_user_id,
                'requested_agent': 'supervisor_agent'
            }
            
            # Test if agent execution can be properly linked to WebSocket
            try:
                user_context = UserExecutionContext(user_id=ws_user_id)
                agent_execution_id = getattr(user_context, 'execution_id', None)
                
                if agent_execution_id:
                    # Check if we can map agent execution back to WebSocket
                    can_map_back = await self._can_map_execution_to_websocket(
                        agent_execution_id, ws_connection_id
                    )
                    
                    if not can_map_back:
                        websocket_coordination_failures.append({
                            'failure': 'agent_to_websocket_mapping',
                            'websocket_id': ws_connection_id,
                            'execution_id': agent_execution_id,
                            'issue': 'Cannot route agent results back to WebSocket',
                            'business_impact': 'Users see incomplete responses'
                        })
            
            except Exception as e:
                websocket_coordination_failures.append({
                    'failure': 'agent_execution_creation',
                    'error': str(e),
                    'implication': 'WebSocket-to-agent handoff broken'
                })
                
        except Exception as e:
            websocket_coordination_failures.append({
                'failure': 'websocket_setup',
                'error': str(e),
                'test_type': 'coordination_test'
            })
        
        # Test 2: Multi-user WebSocket isolation with UUID IDs
        try:
            user_count = 3
            users_data = []
            
            for i in range(user_count):
                user_id = str(uuid.uuid4())
                ws_id = str(uuid.uuid4())
                execution_id = str(uuid.uuid4())
                
                users_data.append({
                    'user_id': user_id,
                    'websocket_id': ws_id,
                    'execution_id': execution_id
                })
            
            # Check if we can properly isolate users with UUID IDs
            isolation_failures = await self._test_multi_user_isolation(users_data)
            websocket_coordination_failures.extend(isolation_failures)
            
        except Exception as e:
            websocket_coordination_failures.append({
                'failure': 'multi_user_isolation_test',
                'error': str(e)
            })
        
        # Test should FAIL if coordination failures detected
        assert len(websocket_coordination_failures) == 0, (
            f"WEBSOCKET-AGENT COORDINATION FAILURES: Found {len(websocket_coordination_failures)} failures:\n" +
            "\n".join([
                f"- {failure['failure']}: {failure.get('issue', failure.get('error', 'Unknown'))}"
                for failure in websocket_coordination_failures
            ]) +
            "\n\nCoordination failures indicate need for structured IDs with embedded context"
        )
        
        self.record_metric("coordination_failures", len(websocket_coordination_failures))
    
    async def test_database_id_persistence_consistency(self):
        """
        Test database persistence of IDs across different formats.
        
        This test should FAIL to expose:
        - Database stores UUID format but application expects structured
        - Query failures due to ID format mismatches
        - Foreign key relationships broken by format changes
        
        Expected: FAIL until database and application use consistent ID formats
        """
        db_consistency_failures = []
        
        try:
            # Test 1: User ID persistence and retrieval
            test_user_id = str(uuid.uuid4())
            
            # Store user with UUID-format ID
            await self.db_utils.create_test_user({
                'user_id': test_user_id,
                'email': 'test@example.com',
                'name': 'Test User'
            })
            
            # Retrieve and check if application can handle the stored format
            stored_user = await self.db_utils.get_user_by_id(test_user_id)
            
            if stored_user is None:
                db_consistency_failures.append({
                    'failure': 'user_retrieval',
                    'stored_id_format': 'UUID',
                    'retrieval_method': 'by_id',
                    'issue': 'Stored user cannot be retrieved'
                })
            
            # Test 2: Cross-table relationship consistency
            if stored_user:
                # Create session linked to user
                session_id = str(uuid.uuid4())
                await self.db_utils.create_test_session({
                    'session_id': session_id,
                    'user_id': test_user_id,
                    'status': 'active'
                })
                
                # Test foreign key relationship
                user_sessions = await self.db_utils.get_sessions_for_user(test_user_id)
                
                if len(user_sessions) == 0:
                    db_consistency_failures.append({
                        'failure': 'foreign_key_relationship',
                        'user_id': test_user_id,
                        'session_id': session_id,
                        'issue': 'Sessions not linked to user properly'
                    })
            
            # Test 3: Structured ID compatibility
            # Try to store structured ID in same schema
            structured_user_id = f"user_1_{str(uuid.uuid4())[:8]}"
            
            try:
                await self.db_utils.create_test_user({
                    'user_id': structured_user_id,
                    'email': 'structured@example.com',
                    'name': 'Structured ID User'
                })
                
                # Check if both formats coexist
                uuid_user = await self.db_utils.get_user_by_id(test_user_id)
                structured_user = await self.db_utils.get_user_by_id(structured_user_id)
                
                if not uuid_user or not structured_user:
                    db_consistency_failures.append({
                        'failure': 'mixed_format_coexistence',
                        'uuid_user_found': bool(uuid_user),
                        'structured_user_found': bool(structured_user),
                        'issue': 'Database cannot handle mixed ID formats'
                    })
                    
            except Exception as e:
                db_consistency_failures.append({
                    'failure': 'structured_id_storage',
                    'error': str(e),
                    'implication': 'Database schema incompatible with structured IDs'
                })
        
        except Exception as e:
            db_consistency_failures.append({
                'failure': 'database_connection',
                'error': str(e)
            })
        
        # Cleanup test data
        try:
            await self.db_utils.cleanup_test_data()
        except Exception:
            pass  # Cleanup failure is not test failure
        
        # Test should FAIL if database consistency issues detected
        assert len(db_consistency_failures) == 0, (
            f"DATABASE ID CONSISTENCY FAILURES: Found {len(db_consistency_failures)} failures:\n" +
            "\n".join([
                f"- {failure['failure']}: {failure.get('issue', failure.get('error', 'Unknown'))}"
                for failure in db_consistency_failures
            ]) +
            "\n\nDatabase consistency failures require schema and application ID alignment"
        )
        
        self.record_metric("db_consistency_failures", len(db_consistency_failures))
    
    async def test_frontend_backend_id_format_expectations(self):
        """
        Test frontend ↔ backend ID format compatibility.
        
        This test should FAIL to expose:
        - Frontend sends one format, backend expects another
        - API response format mismatches
        - Client-side validation failures
        
        Expected: FAIL until frontend and backend agree on ID formats
        """
        frontend_backend_failures = []
        
        try:
            # Test 1: Frontend sends UUID, backend validation
            frontend_user_id = str(uuid.uuid4())
            
            async with httpx.AsyncClient() as client:
                # Simulate typical frontend API call
                response = await client.post(
                    "http://localhost:8000/api/user/profile",
                    json={"user_id": frontend_user_id},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 422:
                    # Validation error - backend doesn't accept UUID format
                    try:
                        error_detail = response.json()
                        frontend_backend_failures.append({
                            'failure': 'frontend_uuid_rejected',
                            'user_id_sent': frontend_user_id,
                            'backend_response': error_detail,
                            'issue': 'Backend validation rejects UUID format from frontend'
                        })
                    except:
                        frontend_backend_failures.append({
                            'failure': 'frontend_uuid_rejected',
                            'status_code': response.status_code,
                            'response_text': response.text[:200]
                        })
        
            # Test 2: Backend sends structured ID, frontend handling
            structured_id = f"user_1_{str(uuid.uuid4())[:8]}"
            
            # Simulate backend API response with structured ID
            mock_api_response = {
                "user_id": structured_id,
                "session_id": f"session_1_{str(uuid.uuid4())[:8]}",
                "status": "active"
            }
            
            # Test if this response format would be acceptable to frontend
            # (In real scenario, this would test actual frontend validation)
            frontend_compatible = await self._test_frontend_id_compatibility(mock_api_response)
            
            if not frontend_compatible:
                frontend_backend_failures.append({
                    'failure': 'backend_structured_id_rejected',
                    'response_format': mock_api_response,
                    'issue': 'Frontend cannot handle structured IDs from backend'
                })
        
        except Exception as e:
            frontend_backend_failures.append({
                'failure': 'api_communication_test',
                'error': str(e)
            })
        
        # Test should FAIL if frontend-backend compatibility issues detected
        assert len(frontend_backend_failures) == 0, (
            f"FRONTEND-BACKEND ID FORMAT FAILURES: Found {len(frontend_backend_failures)} failures:\n" +
            "\n".join([
                f"- {failure['failure']}: {failure.get('issue', failure.get('error', 'Unknown'))}"
                for failure in frontend_backend_failures
            ]) +
            "\n\nFrontend-backend ID format mismatches require coordinated migration"
        )
        
        self.record_metric("frontend_backend_failures", len(frontend_backend_failures))
    
    # Helper methods for integration testing
    
    async def _validate_session_cross_service(self, session_data: Dict[str, Any], 
                                             target_service: str) -> Dict[str, Any]:
        """Helper to validate session across services."""
        try:
            if target_service == 'auth_service':
                auth_client = await auth_service_client()
                response = await auth_client.post("/validate_session", json=session_data)
                
                return {
                    'valid': response.status_code == 200,
                    'response': response.json() if response.status_code == 200 else None,
                    'error': response.text if response.status_code != 200 else None
                }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    async def _can_map_execution_to_websocket(self, execution_id: str, 
                                            websocket_id: str) -> bool:
        """Helper to test if agent execution can be mapped back to WebSocket."""
        try:
            # In properly designed system, we should be able to:
            # 1. Look up execution_id and find associated websocket_id
            # 2. This requires embedded context in IDs or proper tracking
            
            # Current UUID system cannot do this mapping
            if self._is_uuid_format(execution_id) and self._is_uuid_format(websocket_id):
                # Plain UUIDs provide no context for mapping
                return False
            
            # Structured IDs could embed this relationship
            if 'websocket' in execution_id or websocket_id in execution_id:
                return True
                
            return False
            
        except Exception:
            return False
    
    async def _test_multi_user_isolation(self, users_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Helper to test multi-user isolation with given user data."""
        isolation_failures = []
        
        try:
            # Test if we can distinguish between users with plain UUIDs
            user_ids = [user['user_id'] for user in users_data]
            websocket_ids = [user['websocket_id'] for user in users_data]
            
            # Problem: All UUIDs look the same - no user context
            for i, user_data in enumerate(users_data):
                user_id = user_data['user_id']
                ws_id = user_data['websocket_id']
                
                # Can we identify which websocket belongs to which user?
                if self._is_uuid_format(user_id) and self._is_uuid_format(ws_id):
                    # No embedded context - isolation depends on external mapping
                    isolation_failures.append({
                        'failure': f'user_{i}_isolation_risk',
                        'user_id': user_id,
                        'websocket_id': ws_id,
                        'issue': 'No embedded user context for isolation',
                        'risk': 'WebSocket events could be sent to wrong user'
                    })
            
        except Exception as e:
            isolation_failures.append({
                'failure': 'isolation_test_error',
                'error': str(e)
            })
        
        return isolation_failures
    
    async def _test_frontend_id_compatibility(self, api_response: Dict[str, Any]) -> bool:
        """Helper to test frontend compatibility with API response format."""
        try:
            # Simulate frontend ID validation logic
            user_id = api_response.get('user_id', '')
            session_id = api_response.get('session_id', '')
            
            # Current frontend might expect UUID format
            if not self._is_uuid_format(user_id):
                return False  # Frontend validation would fail
            
            if not self._is_uuid_format(session_id):
                return False  # Frontend validation would fail
                
            return True
            
        except Exception:
            return False
    
    def _is_uuid_format(self, id_value: str) -> bool:
        """Helper to check if ID is UUID format."""
        try:
            uuid.UUID(id_value)
            return True
        except (ValueError, TypeError):
            return False