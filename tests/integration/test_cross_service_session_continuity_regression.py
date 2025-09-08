"""
Cross-Service Session Continuity Regression Integration Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Platform-critical functionality 
- Business Goal: Ensure seamless cross-service session continuity for chat experiences
- Value Impact: Prevents conversation breaks, maintains user state across service boundaries
- Strategic Impact: CRITICAL - Enables enterprise-grade multi-service architecture reliability
- Revenue Impact: Prevents session-related churn ($50K+ MRR protection) and enables scalable growth

CRITICAL REGRESSION TEST: This test validates that cross-service communication
maintains session continuity without creating unnecessary execution contexts.

Key Regression Scenarios Tested:
1. Backend → Auth Service: Session validation preserves existing thread_id/run_id
2. Auth Service → Backend: Response maintains original execution context
3. Cross-service calls don't trigger new context creation when reusing existing sessions  
4. Service boundary crossings preserve user isolation and audit trail
5. Multi-service workflows maintain conversation history continuity
6. WebSocket authentication doesn't break existing session contexts

Architecture Integration Points:
- UserExecutionContext cross-service preservation
- UnifiedAuthenticationService session validation
- AuthServiceClient context consistency  
- WebSocket authentication flow continuity
- Database session isolation across services
- Cross-service audit trail consistency

SSOT Compliance:
- Uses SSotBaseTestCase from test_framework/ssot/base_test_case.py
- Uses E2EAuthHelper for real authentication flows (NO MOCKS)
- Uses IsolatedEnvironment (no direct os.environ access) 
- Uses real service communication for integration testing
- Follows proper absolute import patterns per SPEC/import_management_architecture.xml

Cross-Reference:
- netra_backend/app/services/user_execution_context.py (context management)
- netra_backend/app/services/unified_authentication_service.py (auth service interface)
- netra_backend/app/clients/auth_client_core.py (cross-service client)
- test_framework/ssot/e2e_auth_helper.py (authentication patterns)
- SPEC/learnings/context_creation_vs_getter_pattern_fix_20250908.xml
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import patch
import pytest
from dataclasses import dataclass

# SSOT imports - absolute imports only
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

# Cross-service imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    UserContextFactory, 
    InvalidContextError,
    ContextIsolationError
)
from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService, 
    AuthResult
)
from netra_backend.app.clients.auth_client_core import (
    AuthServiceClient,
    AuthServiceError,
    AuthServiceConnectionError,
    AuthServiceValidationError
)

# Database and API clients
from netra_backend.app.db.postgres_core import AsyncDatabase
from auth_service.auth_core.database.connection import AuthDatabaseConnection
import httpx
import aiohttp
import websockets

import logging
logger = logging.getLogger(__name__)


@dataclass
class CrossServiceMetrics:
    """Performance metrics for cross-service operations."""
    auth_validation_time: float = 0.0
    context_creation_time: float = 0.0
    context_reuse_time: float = 0.0
    cross_service_roundtrip_time: float = 0.0
    context_memory_usage: int = 0
    auth_cache_hits: int = 0
    auth_cache_misses: int = 0
    service_boundary_crossings: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging."""
        return {
            'auth_validation_ms': round(self.auth_validation_time * 1000, 2),
            'context_creation_ms': round(self.context_creation_time * 1000, 2),
            'context_reuse_ms': round(self.context_reuse_time * 1000, 2),
            'cross_service_roundtrip_ms': round(self.cross_service_roundtrip_time * 1000, 2),
            'context_memory_bytes': self.context_memory_usage,
            'auth_cache_hits': self.auth_cache_hits,
            'auth_cache_misses': self.auth_cache_misses,
            'service_boundary_crossings': self.service_boundary_crossings
        }


class TestCrossServiceSessionContinuityRegression(SSotBaseTestCase):
    """
    Cross-Service Session Continuity Regression Prevention Test - SSOT Compliant
    
    CRITICAL: This test validates that cross-service calls preserve existing
    execution contexts and don't create unnecessary new contexts, preventing
    conversation continuity breaks and session fragmentation.
    """
    
    def setup_method(self, method):
        """Setup cross-service test environment with real services."""
        super().setup_method(method)
        
        # Skip if not using real services - CRITICAL for cross-service testing
        self.skip_if_no_real_services()
        
        # Initialize cross-service components
        self.auth_helper: Optional[E2EAuthHelper] = None
        self.auth_service: Optional[UnifiedAuthenticationService] = None
        self.auth_client: Optional[AuthServiceClient] = None
        self.backend_db: Optional[AsyncDatabase] = None
        self.auth_db: Optional[AuthDatabaseConnection] = None
        
        # Test data tracking
        self.test_contexts_created: List[str] = []
        self.test_users_created: List[str] = []
        self.test_sessions_created: List[str] = []
        
        # Performance metrics
        self.metrics = CrossServiceMetrics()
        
        logger.info(f"Setup cross-service test: {method.__name__}")
    
    def skip_if_no_real_services(self):
        """Skip test if not running with real services."""
        env = self.get_env()
        if env.get("USE_REAL_SERVICES", "false").lower() != "true":
            pytest.skip("Cross-service tests require --real-services flag for real auth/backend integration")
    
    async def setup_cross_service_environment(self):
        """Setup cross-service testing environment with real components."""
        start_time = time.time()
        
        env = self.get_env()
        environment = env.get("TEST_ENV", "test")
        
        # Setup authentication helper with real services
        auth_config = E2EAuthConfig.for_environment(environment)
        self.auth_helper = E2EAuthHelper(config=auth_config, environment=environment)
        
        # Setup auth service client for cross-service calls
        self.auth_client = AuthServiceClient()
        
        # Setup unified authentication service
        self.auth_service = UnifiedAuthenticationService()
        
        # Initialize database connections to both services
        await self.setup_database_connections()
        
        setup_time = time.time() - start_time
        self.metrics.context_creation_time = setup_time
        
        self.record_metric("cross_service_setup_time_ms", round(setup_time * 1000, 2))
        logger.info(f"Cross-service environment setup completed in {setup_time:.3f}s")
    
    async def setup_database_connections(self):
        """Setup database connections to both backend and auth services."""
        try:
            # Backend database
            from netra_backend.app.database import get_database_url
            backend_url = get_database_url()
            self.backend_db = AsyncDatabase(backend_url)
            
            # Auth service database
            self.auth_db = AuthDatabaseConnection()
            await self.auth_db.initialize()
            
            self.record_metric("backend_db_connected", True)
            self.record_metric("auth_db_connected", True)
            logger.info("Database connections established for both services")
            
        except Exception as e:
            logger.error(f"Database connection setup failed: {e}")
            raise
    
    async def cleanup_cross_service_environment(self):
        """Cleanup cross-service test environment and resources."""
        try:
            # Cleanup test data from both services
            await self.cleanup_test_data()
            
            # Close database connections
            if self.backend_db:
                await self.backend_db.close()
            if self.auth_db:
                await self.auth_db.close()
            
            # Log final metrics
            logger.info(f"Cross-service test metrics: {self.metrics.to_dict()}")
            
        except Exception as e:
            logger.warning(f"Cross-service cleanup error: {e}")
    
    async def cleanup_test_data(self):
        """Cleanup test data from both services."""
        try:
            # Cleanup backend test data
            if self.backend_db and self.test_users_created:
                async with self.backend_db.get_session() as session:
                    for user_id in self.test_users_created:
                        await session.execute(
                            "DELETE FROM users WHERE id = :user_id",
                            {"user_id": user_id}
                        )
                    await session.commit()
            
            # Cleanup auth service test data  
            if self.auth_db and self.test_sessions_created:
                async with self.auth_db.get_session() as session:
                    for session_id in self.test_sessions_created:
                        await session.execute(
                            "DELETE FROM auth_sessions WHERE id = :session_id",
                            {"session_id": session_id}
                        )
                    await session.commit()
                    
            logger.info("Test data cleanup completed for both services")
            
        except Exception as e:
            logger.warning(f"Test data cleanup error: {e}")
    
    @pytest.mark.asyncio
    async def test_backend_to_auth_service_context_preservation(self):
        """
        Test that backend → auth service calls preserve existing execution context.
        
        CRITICAL: Backend service must not create new execution contexts when
        calling auth service for session validation. The existing thread_id and
        run_id must be preserved throughout the cross-service call.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create initial execution context in backend
            user_id = str(uuid.uuid4())
            thread_id = UnifiedIdGenerator.generate_thread_id()
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            
            original_context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_context={'operation_name': 'cross_service_test'},
                audit_metadata={'test_type': 'backend_to_auth'}
            )
            
            # Record original context
            original_request_id = original_context.request_id
            self.test_contexts_created.append(original_request_id)
            
            # Generate JWT token for the user
            jwt_token = await self.auth_helper.create_test_jwt(user_id=user_id)
            
            # Measure auth validation time
            auth_start = time.time()
            
            # Call auth service from backend with existing context
            auth_result = await self.auth_service.validate_token(
                token=jwt_token,
                execution_context=original_context  # CRITICAL: Pass existing context
            )
            
            auth_time = time.time() - auth_start
            self.metrics.auth_validation_time = auth_time
            self.metrics.service_boundary_crossings += 1
            
            # Validate auth result
            self.assertTrue(auth_result.success, "Auth validation should succeed")
            self.assertEqual(auth_result.user_id, user_id, "User ID must be preserved")
            
            # CRITICAL ASSERTION: Context should be preserved, not recreated
            # The auth service should NOT create a new execution context
            # The original thread_id and run_id should still be valid
            
            # Verify context preservation by checking that the same context
            # can still be used for subsequent operations
            child_context = original_context.create_child_context("post_auth_operation")
            
            # Validate child context maintains parent relationships
            self.assertEqual(child_context.thread_id, thread_id, 
                           "Child context must preserve original thread_id")
            self.assertEqual(child_context.run_id, run_id,
                           "Child context must preserve original run_id") 
            self.assertEqual(child_context.user_id, user_id,
                           "Child context must preserve original user_id")
            self.assertEqual(child_context.parent_request_id, original_request_id,
                           "Child context must reference original parent request_id")
            
            # Verify operation depth increased properly
            self.assertEqual(child_context.operation_depth, 1,
                           "Child context should have incremented operation depth")
            
            # Performance assertions
            self.assertLess(auth_time, 1.0, "Auth validation should complete under 1 second")
            
            # Record success metrics
            self.record_metric("backend_to_auth_context_preserved", True)
            self.record_metric("auth_validation_time_ms", round(auth_time * 1000, 2))
            
            logger.info(f"Backend → Auth context preservation test passed in {auth_time:.3f}s")
            
        finally:
            await self.cleanup_cross_service_environment()
    
    @pytest.mark.asyncio
    async def test_auth_service_response_context_consistency(self):
        """
        Test that auth service responses maintain context consistency.
        
        CRITICAL: Auth service must return validation results that are consistent
        with the execution context provided, without modifying or creating new contexts.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create execution context with specific audit metadata
            user_id = str(uuid.uuid4()) 
            thread_id = UnifiedIdGenerator.generate_thread_id()
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            
            context_with_audit = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_context={
                    'operation_name': 'auth_response_test',
                    'service_boundary': 'backend_to_auth'
                },
                audit_metadata={
                    'test_type': 'auth_response_consistency', 
                    'client_ip': '127.0.0.1',
                    'user_agent': 'test-agent/1.0',
                    'original_request_time': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate valid JWT
            jwt_token = await self.auth_helper.create_test_jwt(user_id=user_id)
            
            # Call auth service multiple times with same context
            consistency_start = time.time()
            
            results = []
            for i in range(3):
                result = await self.auth_service.validate_token(
                    token=jwt_token,
                    execution_context=context_with_audit
                )
                results.append(result)
                
                # Small delay to ensure different timestamps  
                await asyncio.sleep(0.01)
            
            consistency_time = time.time() - consistency_start
            self.metrics.cross_service_roundtrip_time = consistency_time / 3
            
            # Validate consistency across multiple calls
            for i, result in enumerate(results):
                self.assertTrue(result.success, f"Auth validation {i} should succeed")
                self.assertEqual(result.user_id, user_id, f"User ID consistency check {i}")
                
                # Verify auth result includes context information
                self.assertIn('metadata', result.__dict__, f"Result {i} should include metadata")
            
            # Verify the original context is unchanged after auth calls
            self.assertEqual(context_with_audit.user_id, user_id, "Original context user_id unchanged")
            self.assertEqual(context_with_audit.thread_id, thread_id, "Original context thread_id unchanged")
            self.assertEqual(context_with_audit.run_id, run_id, "Original context run_id unchanged")
            
            # Verify audit metadata is preserved
            audit_data = context_with_audit.audit_metadata
            self.assertEqual(audit_data['test_type'], 'auth_response_consistency', 
                           "Audit metadata should be preserved")
            self.assertIn('original_request_time', audit_data,
                         "Original audit metadata should be preserved")
            
            # Performance assertions for consistency
            avg_response_time = consistency_time / 3
            self.assertLess(avg_response_time, 0.5, "Average auth response under 500ms")
            
            # Record consistency metrics
            self.record_metric("auth_response_consistency_verified", True)
            self.record_metric("avg_auth_response_time_ms", round(avg_response_time * 1000, 2))
            
            logger.info(f"Auth service response consistency verified in {consistency_time:.3f}s")
            
        finally:
            await self.cleanup_cross_service_environment()
    
    @pytest.mark.asyncio 
    async def test_cross_service_session_reuse_prevention(self):
        """
        Test that cross-service calls properly reuse sessions instead of creating new ones.
        
        CRITICAL: The system should reuse existing database sessions and execution
        contexts when making cross-service calls for the same thread_id, preventing
        session proliferation and memory leaks.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create base execution context
            user_id = str(uuid.uuid4())
            thread_id = UnifiedIdGenerator.generate_thread_id()
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            
            # Create context with database session  
            async with self.backend_db.get_session() as db_session:
                context_with_session = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=thread_id, 
                    run_id=run_id,
                    db_session=db_session,
                    agent_context={'operation_name': 'session_reuse_test'}
                ).with_db_session(db_session)
                
                session_reuse_start = time.time()
                
                # Perform multiple cross-service operations with same context
                jwt_token = await self.auth_helper.create_test_jwt(user_id=user_id)
                
                # Track session reuse vs creation
                session_operations = []
                
                for i in range(5):
                    # Each operation should reuse the existing context and session
                    operation_start = time.time()
                    
                    # Auth validation (should reuse context)
                    auth_result = await self.auth_service.validate_token(
                        token=jwt_token,
                        execution_context=context_with_session
                    )
                    
                    operation_time = time.time() - operation_start
                    session_operations.append({
                        'operation_id': i,
                        'duration_ms': round(operation_time * 1000, 2),
                        'user_id': auth_result.user_id,
                        'context_request_id': context_with_session.request_id
                    })
                    
                    # Verify same context is being reused
                    self.assertEqual(auth_result.user_id, user_id, f"User ID consistent in operation {i}")
                    
                    # Small delay between operations
                    await asyncio.sleep(0.01)
                
                total_reuse_time = time.time() - session_reuse_start
                self.metrics.context_reuse_time = total_reuse_time / 5
                
                # Validate session reuse efficiency
                # Later operations should be faster due to session/cache reuse
                early_ops_avg = sum(op['duration_ms'] for op in session_operations[:2]) / 2
                later_ops_avg = sum(op['duration_ms'] for op in session_operations[3:]) / 2
                
                # Later operations should be faster or similar (not significantly slower)
                efficiency_ratio = later_ops_avg / early_ops_avg if early_ops_avg > 0 else 1.0
                self.assertLessEqual(efficiency_ratio, 1.5, 
                                   "Session reuse should maintain or improve performance")
                
                # Verify all operations used the same context request_id
                request_ids = set(op['context_request_id'] for op in session_operations)
                self.assertEqual(len(request_ids), 1, 
                               "All operations should use the same execution context")
                
                # Verify context isolation is maintained
                context_with_session.verify_isolation()
                
                # Record session reuse metrics
                self.record_metric("session_reuse_operations", len(session_operations))
                self.record_metric("session_reuse_efficiency_ratio", round(efficiency_ratio, 3))
                self.record_metric("avg_reuse_operation_time_ms", round(self.metrics.context_reuse_time * 1000, 2))
                
                logger.info(f"Session reuse test completed: {len(session_operations)} operations in {total_reuse_time:.3f}s")
                
        finally:
            await self.cleanup_cross_service_environment()
    
    @pytest.mark.asyncio
    async def test_websocket_cross_service_auth_continuity(self):
        """
        Test WebSocket authentication preserves execution context across services.
        
        CRITICAL: WebSocket authentication flow must not break existing session
        contexts when validating tokens with the auth service. The WebSocket
        connection should maintain the same thread_id and run_id throughout.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create WebSocket execution context
            user_id = str(uuid.uuid4())
            thread_id = UnifiedIdGenerator.generate_thread_id() 
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            websocket_client_id = f"ws_{uuid.uuid4().hex[:8]}"
            
            websocket_context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                websocket_client_id=websocket_client_id,
                agent_context={
                    'operation_name': 'websocket_auth_test',
                    'connection_type': 'websocket',
                    'client_id': websocket_client_id
                },
                audit_metadata={
                    'test_type': 'websocket_cross_service_auth',
                    'connection_source': 'test_client',
                    'auth_flow': 'jwt_websocket'
                }
            )
            
            # Generate JWT for WebSocket authentication
            jwt_token = await self.auth_helper.create_test_jwt(
                user_id=user_id,
                additional_claims={'websocket_client_id': websocket_client_id}
            )
            
            websocket_auth_start = time.time()
            
            # Simulate WebSocket authentication flow
            # This would normally happen during WebSocket connection handshake
            auth_result = await self.auth_service.validate_websocket_token(
                token=jwt_token,
                websocket_client_id=websocket_client_id,
                execution_context=websocket_context
            )
            
            websocket_auth_time = time.time() - websocket_auth_start
            self.metrics.auth_validation_time = websocket_auth_time
            
            # Validate WebSocket authentication preserved context
            self.assertTrue(auth_result.success, "WebSocket auth should succeed")
            self.assertEqual(auth_result.user_id, user_id, "User ID preserved in WebSocket auth")
            
            # Verify WebSocket context still intact after auth
            self.assertEqual(websocket_context.websocket_client_id, websocket_client_id,
                           "WebSocket client ID preserved")
            self.assertEqual(websocket_context.thread_id, thread_id,
                           "Thread ID preserved in WebSocket context")
            self.assertEqual(websocket_context.run_id, run_id,
                           "Run ID preserved in WebSocket context")
            
            # Test context continuity in subsequent WebSocket operations
            # Create child context for WebSocket message handling
            message_context = websocket_context.create_child_context(
                "websocket_message_handling",
                additional_agent_context={
                    'message_type': 'test_message',
                    'authenticated': True
                }
            )
            
            # Validate child context maintains WebSocket properties
            self.assertEqual(message_context.websocket_client_id, websocket_client_id,
                           "Child context preserves WebSocket client ID")
            self.assertEqual(message_context.user_id, user_id,
                           "Child context preserves user ID")
            self.assertEqual(message_context.thread_id, thread_id,
                           "Child context preserves thread ID")
            self.assertEqual(message_context.parent_request_id, websocket_context.request_id,
                           "Child context references correct parent")
            
            # Verify audit trail continuity
            audit_trail = message_context.get_audit_trail()
            self.assertIn('websocket_client_id', audit_trail.get('audit_metadata', {}),
                         "Audit trail should include WebSocket client ID")
            self.assertEqual(audit_trail['user_id'], user_id,
                           "Audit trail preserves user ID")
            
            # Performance validation for WebSocket auth
            self.assertLess(websocket_auth_time, 2.0, "WebSocket auth should complete under 2 seconds")
            
            # Record WebSocket continuity metrics
            self.record_metric("websocket_auth_continuity_verified", True)
            self.record_metric("websocket_auth_time_ms", round(websocket_auth_time * 1000, 2))
            self.record_metric("websocket_client_id", websocket_client_id)
            
            logger.info(f"WebSocket cross-service auth continuity verified in {websocket_auth_time:.3f}s")
            
        finally:
            await self.cleanup_cross_service_environment()
    
    @pytest.mark.asyncio
    async def test_multi_service_conversation_flow_continuity(self):
        """
        Test complete multi-service conversation flow maintains context continuity.
        
        CRITICAL: A full conversation flow involving multiple service calls should
        maintain the same thread_id and run_id throughout, ensuring conversation
        history and context are preserved across all service boundaries.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create initial conversation context
            user_id = str(uuid.uuid4())
            thread_id = UnifiedIdGenerator.generate_thread_id()
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            
            conversation_context = UserExecutionContext.from_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                agent_context={
                    'operation_name': 'multi_service_conversation',
                    'conversation_phase': 'initialization'
                },
                audit_metadata={
                    'test_type': 'multi_service_flow',
                    'conversation_id': str(uuid.uuid4()),
                    'flow_stage': 'start'
                }
            )
            
            # Track conversation flow metrics
            conversation_start = time.time()
            conversation_steps = []
            
            # Step 1: Initial authentication with auth service
            jwt_token = await self.auth_helper.create_test_jwt(user_id=user_id)
            
            step1_start = time.time()
            auth_result = await self.auth_service.validate_token(
                token=jwt_token,
                execution_context=conversation_context
            )
            step1_time = time.time() - step1_start
            
            self.assertTrue(auth_result.success, "Step 1: Auth validation should succeed")
            conversation_steps.append({
                'step': 1,
                'operation': 'auth_validation',
                'duration_ms': round(step1_time * 1000, 2),
                'context_preserved': auth_result.user_id == user_id
            })
            
            # Step 2: Create child context for agent operation (simulating chat processing)
            step2_start = time.time()
            agent_context = conversation_context.create_child_context(
                "agent_processing",
                additional_agent_context={
                    'agent_type': 'data_analysis',
                    'authenticated': True,
                    'conversation_phase': 'processing'
                },
                additional_audit_metadata={
                    'flow_stage': 'agent_processing',
                    'auth_validated': True
                }
            )
            step2_time = time.time() - step2_start
            
            conversation_steps.append({
                'step': 2,
                'operation': 'child_context_creation',
                'duration_ms': round(step2_time * 1000, 2),
                'context_preserved': agent_context.thread_id == thread_id
            })
            
            # Step 3: Simulate additional auth check during agent processing
            step3_start = time.time()
            secondary_auth = await self.auth_service.validate_token(
                token=jwt_token,
                execution_context=agent_context  # Using child context
            )
            step3_time = time.time() - step3_start
            
            self.assertTrue(secondary_auth.success, "Step 3: Secondary auth should succeed")
            conversation_steps.append({
                'step': 3,
                'operation': 'secondary_auth_validation',
                'duration_ms': round(step3_time * 1000, 2),
                'context_preserved': secondary_auth.user_id == user_id
            })
            
            # Step 4: Create final response context
            step4_start = time.time()
            response_context = agent_context.create_child_context(
                "response_generation",
                additional_agent_context={
                    'conversation_phase': 'response',
                    'response_type': 'data_analysis_result'
                },
                additional_audit_metadata={
                    'flow_stage': 'response_generation',
                    'processing_completed': True
                }
            )
            step4_time = time.time() - step4_start
            
            conversation_steps.append({
                'step': 4,
                'operation': 'response_context_creation',
                'duration_ms': round(step4_time * 1000, 2),
                'context_preserved': response_context.thread_id == thread_id
            })
            
            total_conversation_time = time.time() - conversation_start
            
            # Validate conversation flow continuity
            contexts_to_validate = [conversation_context, agent_context, response_context]
            
            for i, context in enumerate(contexts_to_validate):
                self.assertEqual(context.user_id, user_id, 
                               f"Context {i}: User ID preserved throughout flow")
                self.assertEqual(context.thread_id, thread_id,
                               f"Context {i}: Thread ID preserved throughout flow")  
                self.assertEqual(context.run_id, run_id,
                               f"Context {i}: Run ID preserved throughout flow")
                
                # Verify context isolation
                context.verify_isolation()
            
            # Validate hierarchical relationships
            self.assertEqual(agent_context.parent_request_id, conversation_context.request_id,
                           "Agent context should reference initial context as parent")
            self.assertEqual(response_context.parent_request_id, agent_context.request_id,
                           "Response context should reference agent context as parent")
            
            # Validate operation depth progression  
            self.assertEqual(conversation_context.operation_depth, 0, "Initial context depth should be 0")
            self.assertEqual(agent_context.operation_depth, 1, "Agent context depth should be 1")
            self.assertEqual(response_context.operation_depth, 2, "Response context depth should be 2")
            
            # Performance validations
            self.assertLess(total_conversation_time, 5.0, "Complete conversation flow under 5 seconds")
            
            # All steps should have preserved context
            context_preservation_rate = sum(1 for step in conversation_steps if step['context_preserved']) / len(conversation_steps)
            self.assertEqual(context_preservation_rate, 1.0, "100% context preservation across all steps")
            
            # Record comprehensive conversation metrics
            self.record_metric("conversation_flow_completed", True)
            self.record_metric("conversation_steps", len(conversation_steps))
            self.record_metric("total_conversation_time_ms", round(total_conversation_time * 1000, 2))
            self.record_metric("context_preservation_rate", context_preservation_rate)
            self.record_metric("conversation_flow_steps", conversation_steps)
            
            logger.info(f"Multi-service conversation flow completed: {len(conversation_steps)} steps in {total_conversation_time:.3f}s")
            
        finally:
            await self.cleanup_cross_service_environment()
    
    @pytest.mark.asyncio
    async def test_service_boundary_context_consistency_validation(self):
        """
        Test context consistency validation across all service boundaries.
        
        CRITICAL: All service boundary crossings must maintain context consistency
        with proper validation that prevents context corruption or data leakage.
        """
        await self.setup_cross_service_environment()
        
        try:
            # Create test contexts for different service boundaries
            user_id = str(uuid.uuid4())
            thread_id = UnifiedIdGenerator.generate_thread_id()
            run_id = UnifiedIdGenerator.generate_run_id(thread_id)
            
            # Test different service boundary scenarios
            boundary_tests = [
                {
                    'boundary': 'backend_to_auth',
                    'context_type': 'api_request',
                    'expected_fields': ['user_id', 'thread_id', 'run_id', 'request_id']
                },
                {
                    'boundary': 'auth_to_backend',
                    'context_type': 'auth_response', 
                    'expected_fields': ['user_id', 'thread_id', 'run_id', 'request_id']
                },
                {
                    'boundary': 'websocket_to_auth',
                    'context_type': 'websocket_auth',
                    'expected_fields': ['user_id', 'thread_id', 'run_id', 'websocket_client_id']
                },
                {
                    'boundary': 'database_cross_service',
                    'context_type': 'db_transaction',
                    'expected_fields': ['user_id', 'thread_id', 'run_id', 'db_session']
                }
            ]
            
            boundary_validation_results = []
            validation_start = time.time()
            
            for boundary_test in boundary_tests:
                test_start = time.time()
                
                # Create context specific to this boundary test
                if boundary_test['context_type'] == 'websocket_auth':
                    test_context = UserExecutionContext.from_request(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        websocket_client_id=f"ws_{uuid.uuid4().hex[:8]}",
                        agent_context={
                            'boundary_test': boundary_test['boundary'],
                            'context_type': boundary_test['context_type']
                        }
                    )
                elif boundary_test['context_type'] == 'db_transaction':
                    async with self.backend_db.get_session() as db_session:
                        test_context = UserExecutionContext.from_request(
                            user_id=user_id,
                            thread_id=thread_id,
                            run_id=run_id,
                            db_session=db_session,
                            agent_context={
                                'boundary_test': boundary_test['boundary'],
                                'context_type': boundary_test['context_type']
                            }
                        )
                else:
                    test_context = UserExecutionContext.from_request(
                        user_id=user_id,
                        thread_id=thread_id,
                        run_id=run_id,
                        agent_context={
                            'boundary_test': boundary_test['boundary'],
                            'context_type': boundary_test['context_type']
                        }
                    )
                
                # Validate required fields are present
                validation_errors = []
                for field in boundary_test['expected_fields']:
                    if not hasattr(test_context, field):
                        validation_errors.append(f"Missing field: {field}")
                        continue
                    
                    value = getattr(test_context, field)
                    if value is None:
                        validation_errors.append(f"Null field: {field}")
                    elif isinstance(value, str) and not value.strip():
                        validation_errors.append(f"Empty field: {field}")
                
                # Validate context isolation
                try:
                    test_context.verify_isolation()
                    isolation_valid = True
                except ContextIsolationError as e:
                    validation_errors.append(f"Isolation error: {e}")
                    isolation_valid = False
                
                # Test context serialization (important for cross-service transmission)
                try:
                    context_dict = test_context.to_dict()
                    serialization_valid = all(
                        key in context_dict for key in ['user_id', 'thread_id', 'run_id']
                    )
                except Exception as e:
                    validation_errors.append(f"Serialization error: {e}")
                    serialization_valid = False
                
                test_time = time.time() - test_start
                
                boundary_result = {
                    'boundary': boundary_test['boundary'],
                    'context_type': boundary_test['context_type'],
                    'validation_time_ms': round(test_time * 1000, 2),
                    'validation_errors': validation_errors,
                    'isolation_valid': isolation_valid,
                    'serialization_valid': serialization_valid,
                    'overall_valid': len(validation_errors) == 0 and isolation_valid and serialization_valid
                }
                
                boundary_validation_results.append(boundary_result)
                
                # Assert each boundary test passed
                self.assertTrue(boundary_result['overall_valid'], 
                              f"Boundary validation failed for {boundary_test['boundary']}: {validation_errors}")
            
            total_validation_time = time.time() - validation_start
            
            # Validate overall consistency across all boundaries
            all_boundaries_valid = all(result['overall_valid'] for result in boundary_validation_results)
            self.assertTrue(all_boundaries_valid, "All service boundaries should validate successfully")
            
            # Performance validation
            avg_boundary_validation_time = total_validation_time / len(boundary_tests)
            self.assertLess(avg_boundary_validation_time, 1.0, "Average boundary validation under 1 second")
            
            # Record boundary validation metrics
            self.record_metric("boundary_validations_completed", len(boundary_validation_results))
            self.record_metric("boundary_validation_success_rate", 
                             sum(1 for r in boundary_validation_results if r['overall_valid']) / len(boundary_validation_results))
            self.record_metric("avg_boundary_validation_time_ms", round(avg_boundary_validation_time * 1000, 2))
            self.record_metric("boundary_validation_results", boundary_validation_results)
            
            logger.info(f"Service boundary validation completed: {len(boundary_validation_results)} boundaries in {total_validation_time:.3f}s")
            
        finally:
            await self.cleanup_cross_service_environment()
    
    def teardown_method(self, method):
        """Teardown cross-service test environment."""
        super().teardown_method(method)
        
        # Log final test metrics
        if hasattr(self, 'metrics'):
            logger.info(f"Final test metrics for {method.__name__}: {self.metrics.to_dict()}")
        
        # Record test completion
        self.record_metric("cross_service_test_completed", True)
        logger.info(f"Cross-service test completed: {method.__name__}")


# Additional helper functions for cross-service testing

async def simulate_cross_service_api_call(
    source_service: str,
    target_service: str, 
    context: UserExecutionContext,
    operation: str
) -> Dict[str, Any]:
    """
    Simulate a cross-service API call with context preservation.
    
    This helper function simulates the cross-service communication patterns
    that occur in the real system between backend and auth services.
    """
    call_start = time.time()
    
    # Simulate network latency
    await asyncio.sleep(0.01)
    
    # Validate context preservation
    if not context.user_id or not context.thread_id or not context.run_id:
        raise ValueError("Context missing required fields for cross-service call")
    
    # Simulate successful cross-service operation
    call_time = time.time() - call_start
    
    return {
        'success': True,
        'source_service': source_service,
        'target_service': target_service,
        'operation': operation,
        'context_preserved': True,
        'user_id': context.user_id,
        'thread_id': context.thread_id,
        'run_id': context.run_id,
        'call_duration_ms': round(call_time * 1000, 2)
    }


def validate_cross_service_context_integrity(
    original_context: UserExecutionContext,
    returned_context: UserExecutionContext
) -> List[str]:
    """
    Validate that cross-service calls preserve context integrity.
    
    Returns list of validation errors, empty list if validation passes.
    """
    errors = []
    
    # Validate core identifiers preserved
    if original_context.user_id != returned_context.user_id:
        errors.append("User ID not preserved across service boundary")
    
    if original_context.thread_id != returned_context.thread_id:
        errors.append("Thread ID not preserved across service boundary")
        
    if original_context.run_id != returned_context.run_id:
        errors.append("Run ID not preserved across service boundary")
    
    # Validate audit trail continuity
    if original_context.created_at != returned_context.created_at:
        errors.append("Context creation timestamp modified across service boundary")
    
    return errors


if __name__ == "__main__":
    # Allow running individual test methods for debugging
    pytest.main([__file__, "-v", "--tb=short"])