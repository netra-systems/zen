"""
Cross-service integration tests for UnifiedIDManager compliance.

This test file validates that ID generation and validation works consistently
across service boundaries and that auth service integrates properly with
the central UnifiedIDManager from netra_backend.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Cross-Service ID Consistency
- Value Impact: Ensures IDs generated in auth service work across all services
- Strategic Impact: Prevents cross-service ID validation failures and integration issues

CRITICAL: These tests MUST FAIL initially to prove cross-service violations exist.
"""

import asyncio
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager


class TestUnifiedIDCrossServiceIntegration(SSotAsyncTestCase):
    """Test cross-service UnifiedIDManager integration compliance."""
    
    async def asyncSetUp(self):
        """Set up cross-service test environment."""
        await super().asyncSetUp()
        self.backend_id_manager = get_id_manager()
        self.backend_id_manager.clear_all()
        self.integration_violations = []
    
    def test_auth_service_id_compatibility_with_backend(self):
        """
        INTEGRATION VIOLATION TEST: Auth service IDs must be compatible with backend.
        
        This test MUST FAIL initially because auth service generates raw UUIDs
        that are not compatible with backend's structured ID validation.
        
        Expected violations:
        - Auth service generates IDs that backend ID manager cannot validate
        - Cross-service ID passing fails due to format incompatibility
        """
        # Generate ID using auth service pattern (current violation)
        auth_service_user_id = self._simulate_auth_service_id_generation()
        
        # Test if backend ID manager can validate auth service IDs
        is_valid_in_backend = self.backend_id_manager.is_valid_id(auth_service_user_id, IDType.USER)
        
        # This should FAIL initially - auth service IDs not recognized by backend
        self.assertTrue(is_valid_in_backend,
                       f"Auth service generated ID '{auth_service_user_id}' not recognized by backend UnifiedIDManager. "
                       f"This indicates cross-service ID compatibility violation.")
        
        # Test reverse compatibility - backend ID in auth service context
        backend_user_id = self.backend_id_manager.generate_id(IDType.USER, prefix="backend")
        auth_can_validate = self._simulate_auth_service_id_validation(backend_user_id)
        
        self.assertTrue(auth_can_validate,
                       f"Backend generated ID '{backend_user_id}' not validated by auth service logic. "
                       f"This indicates bidirectional compatibility violation.")
    
    def test_websocket_id_cross_service_usage(self):
        """
        WEBSOCKET INTEGRATION VIOLATION TEST: WebSocket IDs must work across services.
        
        This test MUST FAIL initially because auth service WebSocket handling
        uses incompatible ID patterns with the backend WebSocket manager.
        
        Expected violations:
        - Auth service cannot validate WebSocket IDs from backend
        - Backend cannot process WebSocket connection IDs from auth service
        """
        # Generate WebSocket ID from backend
        backend_ws_id = self.backend_id_manager.generate_id(IDType.WEBSOCKET, 
                                                            context={"user_id": "test_user"})
        
        # Test if auth service can handle backend WebSocket IDs
        auth_service_compatible = self._simulate_auth_websocket_validation(backend_ws_id)
        
        # This should FAIL initially due to cross-service WebSocket ID incompatibility
        self.assertTrue(auth_service_compatible,
                       f"Auth service cannot validate backend WebSocket ID '{backend_ws_id}'. "
                       f"This breaks WebSocket authentication across services.")
        
        # Test reverse - auth service WebSocket ID in backend
        auth_ws_id = self._simulate_auth_service_websocket_id()
        backend_can_validate = self.backend_id_manager.is_valid_id(auth_ws_id, IDType.WEBSOCKET)
        
        self.assertTrue(backend_can_validate,
                       f"Backend cannot validate auth service WebSocket ID '{auth_ws_id}'. "
                       f"This breaks WebSocket resource management.")
    
    def test_session_id_cross_service_persistence(self):
        """
        SESSION INTEGRATION VIOLATION TEST: Session IDs must persist across services.
        
        This test MUST FAIL initially because auth service session IDs
        are not compatible with backend session tracking systems.
        
        Expected violations:
        - Session IDs from auth service not recognized by backend tracking
        - Cross-service session validation fails
        - Session cleanup cannot find auth service generated sessions
        """
        # Generate session ID using auth service pattern (violation)
        auth_session_id = self._simulate_auth_service_session_generation()
        
        # Test backend session tracking compatibility
        backend_can_track = self.backend_id_manager.is_valid_id(auth_session_id, IDType.SESSION)
        
        # This should FAIL initially due to session ID incompatibility
        self.assertTrue(backend_can_track,
                       f"Backend cannot track auth service session ID '{auth_session_id}'. "
                       f"This breaks cross-service session management.")
        
        # Test session cleanup compatibility
        cleanup_count = self._simulate_cross_service_session_cleanup([auth_session_id])
        
        self.assertGreater(cleanup_count, 0,
                          f"Cross-service session cleanup failed for auth session '{auth_session_id}'. "
                          f"This indicates ID format incompatibility preventing resource cleanup.")
    
    def test_jwt_token_id_cross_service_validation(self):
        """
        JWT INTEGRATION VIOLATION TEST: JWT token IDs must validate across services.
        
        This test MUST FAIL initially because auth service JWT token IDs (jti fields)
        are not compatible with backend token validation and blacklisting.
        
        Expected violations:
        - JWT token IDs from auth service not recognized by backend validation
        - Token blacklisting fails due to ID format mismatch
        - Cross-service token tracking breaks
        """
        # Generate JWT token ID using auth service factory pattern (violation)
        auth_jwt_id = self._simulate_auth_service_jwt_id_generation()
        
        # Test backend JWT validation compatibility
        backend_jwt_valid = self.backend_id_manager.is_valid_id_format_compatible(auth_jwt_id)
        
        # This should FAIL initially due to JWT ID format incompatibility
        self.assertTrue(backend_jwt_valid,
                       f"Backend cannot validate auth service JWT ID '{auth_jwt_id}'. "
                       f"This breaks cross-service JWT token management.")
        
        # Test JWT blacklisting compatibility
        can_blacklist = self._simulate_jwt_cross_service_blacklisting(auth_jwt_id)
        
        self.assertTrue(can_blacklist,
                       f"Cannot blacklist auth service JWT ID '{auth_jwt_id}' in backend. "
                       f"This creates security vulnerability - tokens cannot be revoked globally.")
    
    def test_user_context_id_cross_service_execution(self):
        """
        USER CONTEXT INTEGRATION VIOLATION TEST: User context IDs must work in backend execution.
        
        This test MUST FAIL initially because auth service user context IDs
        are incompatible with backend agent execution context tracking.
        
        Expected violations:
        - User context IDs from auth cannot be tracked by backend execution engine
        - Cross-service execution context fails
        - Resource isolation breaks due to ID format mismatch
        """
        # Generate user context IDs from auth service (violation pattern)
        auth_thread_id, auth_run_id, auth_request_id = self._simulate_auth_service_context_generation()
        
        # Test backend execution context compatibility
        backend_thread_valid = self.backend_id_manager.is_valid_id(auth_thread_id, IDType.THREAD)
        backend_run_valid = self.backend_id_manager.is_valid_id(auth_run_id, IDType.EXECUTION)  
        backend_request_valid = self.backend_id_manager.is_valid_id(auth_request_id, IDType.REQUEST)
        
        # These should FAIL initially due to context ID incompatibility
        self.assertTrue(backend_thread_valid,
                       f"Backend cannot validate auth service thread ID '{auth_thread_id}'. "
                       f"This breaks cross-service execution context tracking.")
        
        self.assertTrue(backend_run_valid,
                       f"Backend cannot validate auth service run ID '{auth_run_id}'. "
                       f"This breaks cross-service agent execution tracking.")
        
        self.assertTrue(backend_request_valid,
                       f"Backend cannot validate auth service request ID '{auth_request_id}'. "
                       f"This breaks cross-service request correlation.")
    
    def test_id_registry_synchronization_across_services(self):
        """
        REGISTRY SYNCHRONIZATION VIOLATION TEST: ID registries must stay synchronized.
        
        This test MUST FAIL initially because auth service and backend maintain
        separate, unsynchronized ID registries leading to ID conflicts.
        
        Expected violations:
        - Same ID registered in both services with different metadata
        - Cross-service ID lookups fail
        - Registry consistency violations
        """
        # Register ID in backend
        backend_id = self.backend_id_manager.generate_id(IDType.USER, prefix="sync_test")
        
        # Simulate auth service attempting to register same ID differently
        auth_registration_conflict = self._simulate_auth_service_id_registration(
            backend_id, {"auth_service": True, "conflict": True}
        )
        
        # This should FAIL initially due to registry synchronization issues
        self.assertFalse(auth_registration_conflict,
                        f"Auth service can register already-used backend ID '{backend_id}'. "
                        f"This indicates registry synchronization violation.")
        
        # Test cross-service ID lookup consistency
        backend_metadata = self.backend_id_manager.get_id_metadata(backend_id)
        auth_metadata = self._simulate_auth_service_id_lookup(backend_id)
        
        # Metadata should be consistent across services
        metadata_consistent = (auth_metadata is not None and 
                             backend_metadata is not None and
                             self._metadata_equivalent(backend_metadata, auth_metadata))
        
        self.assertTrue(metadata_consistent,
                       f"ID metadata inconsistent between services for '{backend_id}'. "
                       f"Backend: {backend_metadata}, Auth: {auth_metadata}")
    
    def test_cross_service_resource_cleanup_integration(self):
        """
        RESOURCE CLEANUP INTEGRATION VIOLATION TEST: Resource cleanup must work across services.
        
        This test MUST FAIL initially because auth service resources cannot be
        properly cleaned up by backend resource management due to ID incompatibility.
        
        Expected violations:
        - Backend cannot find auth service resources for cleanup
        - User resource isolation fails across services
        - Memory leaks due to incomplete cross-service cleanup
        """
        # Create resources in both services for same user
        user_id = "cross_service_test_user"
        
        # Generate resources in auth service (violation pattern)
        auth_session_id = self._simulate_auth_service_session_generation(user_id)
        auth_ws_id = self._simulate_auth_service_websocket_id(user_id)
        
        # Generate resources in backend
        backend_session_id = self.backend_id_manager.generate_id(
            IDType.SESSION, context={"user_id": user_id}
        )
        backend_ws_id = self.backend_id_manager.generate_id(
            IDType.WEBSOCKET, context={"user_id": user_id}
        )
        
        # Test cross-service resource discovery
        backend_found_resources = self.backend_id_manager.find_resources_by_user_pattern_safe(
            user_id, ["session", "websocket"]
        )
        
        # Backend should find ALL user resources, including auth service ones
        total_expected_resources = 4  # 2 from auth + 2 from backend
        
        # This should FAIL initially - backend cannot find auth service resources
        self.assertEqual(len(backend_found_resources), total_expected_resources,
                        f"Backend resource discovery found {len(backend_found_resources)} resources "
                        f"but expected {total_expected_resources}. Missing auth service resources: "
                        f"auth_session={auth_session_id}, auth_ws={auth_ws_id}")
        
        # Test cross-service cleanup
        cleanup_count = self.backend_id_manager.cleanup_websocket_resources_secure(user_id)
        
        # Should clean up resources from both services
        self.assertEqual(cleanup_count, total_expected_resources,
                        f"Cross-service cleanup only handled {cleanup_count} resources "
                        f"but should have cleaned up {total_expected_resources}")
    
    def test_correct_cross_service_integration_pattern(self):
        """
        POSITIVE TEST: Demonstrate correct cross-service UnifiedIDManager usage.
        
        This test shows how services SHOULD integrate after violations are fixed.
        This test should PASS to validate the correct integration pattern.
        """
        # Both services should use the same UnifiedIDManager instance
        auth_manager = get_id_manager()  # Same as backend
        
        # Generate ID in one service
        user_id = auth_manager.generate_id(IDType.USER, prefix="auth", 
                                          context={"service": "auth_service"})
        
        # Validate in other service - should work seamlessly
        self.assertTrue(self.backend_id_manager.is_valid_id(user_id, IDType.USER))
        
        # Metadata should be accessible from both services
        auth_metadata = auth_manager.get_id_metadata(user_id)
        backend_metadata = self.backend_id_manager.get_id_metadata(user_id)
        
        self.assertEqual(auth_metadata, backend_metadata,
                        "ID metadata should be identical across services")
        
        # Cross-service operations should work
        cleanup_count = self.backend_id_manager.cleanup_websocket_resources_secure(user_id[:8])
        # Should not fail even if no resources to cleanup
        self.assertGreaterEqual(cleanup_count, 0)
    
    # Helper methods to simulate auth service behavior (current violation patterns)
    
    def _simulate_auth_service_id_generation(self) -> str:
        """Simulate how auth service currently generates IDs (with violations)."""
        import uuid
        return str(uuid.uuid4())  # This is the violation pattern
    
    def _simulate_auth_service_id_validation(self, id_value: str) -> bool:
        """Simulate how auth service currently validates IDs."""
        try:
            import uuid
            uuid.UUID(id_value)  # Only accepts UUIDs - violation
            return True
        except ValueError:
            return False
    
    def _simulate_auth_websocket_validation(self, ws_id: str) -> bool:
        """Simulate auth service WebSocket ID validation."""
        # Currently only accepts UUID format - violation
        try:
            import uuid
            uuid.UUID(ws_id)
            return True
        except ValueError:
            return False
    
    def _simulate_auth_service_websocket_id(self, user_id: str = None) -> str:
        """Simulate auth service WebSocket ID generation."""
        import uuid
        return str(uuid.uuid4())  # Violation - no user context
    
    def _simulate_auth_service_session_generation(self, user_id: str = None) -> str:
        """Simulate auth service session ID generation."""
        import uuid
        return str(uuid.uuid4())  # Violation pattern
    
    def _simulate_cross_service_session_cleanup(self, session_ids: List[str]) -> int:
        """Simulate cross-service session cleanup attempt."""
        # Currently fails for non-structured IDs - violation
        cleanup_count = 0
        for session_id in session_ids:
            if self.backend_id_manager.is_valid_id(session_id, IDType.SESSION):
                cleanup_count += 1
        return cleanup_count
    
    def _simulate_auth_service_jwt_id_generation(self) -> str:
        """Simulate auth service JWT ID (jti) generation."""
        import uuid
        return str(uuid.uuid4())  # Violation pattern
    
    def _simulate_jwt_cross_service_blacklisting(self, jwt_id: str) -> bool:
        """Simulate cross-service JWT blacklisting."""
        # Only works with structured IDs - violation for raw UUIDs
        return self.backend_id_manager.is_valid_id_format_compatible(jwt_id)
    
    def _simulate_auth_service_context_generation(self) -> tuple[str, str, str]:
        """Simulate auth service user context ID generation."""
        import uuid
        thread_id = f"thread_{uuid.uuid4()}"  # Violation pattern
        run_id = f"run_{uuid.uuid4()}"        # Violation pattern  
        request_id = str(uuid.uuid4())        # Violation pattern
        return thread_id, run_id, request_id
    
    def _simulate_auth_service_id_registration(self, id_value: str, context: Dict) -> bool:
        """Simulate auth service attempting to register an ID."""
        # Would conflict if same ID registered differently - violation
        return True  # Simulates successful registration (violation)
    
    def _simulate_auth_service_id_lookup(self, id_value: str) -> Optional[Dict]:
        """Simulate auth service ID metadata lookup."""
        # Auth service doesn't have same registry - violation
        return None  # Simulates not found (registry synchronization violation)
    
    def _metadata_equivalent(self, metadata1, metadata2) -> bool:
        """Check if two metadata objects are equivalent."""
        if metadata1 is None and metadata2 is None:
            return True
        if metadata1 is None or metadata2 is None:
            return False
        
        # Compare key fields
        return (metadata1.id_value == metadata2.id_value and
                metadata1.id_type == metadata2.id_type)
    
    async def asyncTearDown(self):
        """Clean up and report integration violations."""
        await super().asyncTearDown()
        
        if self.integration_violations:
            print(f"\nCROSS-SERVICE INTEGRATION VIOLATION SUMMARY: ")
            print(f"Found {len(self.integration_violations)} violations:")
            for violation in self.integration_violations:
                print(f"  {violation}")


class TestUnifiedIDManagerServiceBoundaryCompliance(SSotAsyncTestCase):
    """Test service boundary compliance for UnifiedIDManager."""
    
    async def asyncSetUp(self):
        """Set up service boundary test environment."""
        await super().asyncSetUp()
        self.manager = get_id_manager()
        self.manager.clear_all()
    
    def test_service_boundary_id_isolation(self):
        """
        SERVICE ISOLATION TEST: IDs should maintain service boundary information.
        
        Tests that IDs generated for different services maintain proper isolation
        while still being compatible with the central UnifiedIDManager.
        """
        # Generate IDs for different services
        auth_user_id = self.manager.generate_id(IDType.USER, prefix="auth",
                                               context={"service": "auth_service"})
        backend_user_id = self.manager.generate_id(IDType.USER, prefix="backend", 
                                                  context={"service": "netra_backend"})
        
        # IDs should be different
        self.assertNotEqual(auth_user_id, backend_user_id)
        
        # Both should be valid
        self.assertTrue(self.manager.is_valid_id(auth_user_id, IDType.USER))
        self.assertTrue(self.manager.is_valid_id(backend_user_id, IDType.USER))
        
        # Service context should be preserved
        auth_metadata = self.manager.get_id_metadata(auth_user_id)
        backend_metadata = self.manager.get_id_metadata(backend_user_id)
        
        self.assertEqual(auth_metadata.context.get("service"), "auth_service")
        self.assertEqual(backend_metadata.context.get("service"), "netra_backend")
    
    def test_cross_service_id_sharing_security(self):
        """
        SECURITY TEST: Cross-service ID sharing should maintain security boundaries.
        
        Tests that user-specific resources cannot be accessed across service
        boundaries without proper authorization.
        """
        # Create user-specific resources in different services
        user_a_id = "user_a_test"
        user_b_id = "user_b_test" 
        
        # Generate resources for user A in auth service context
        auth_resource = self.manager.generate_id(IDType.SESSION, prefix=user_a_id[:8],
                                                context={"user_id": user_a_id, "service": "auth"})
        
        # Generate resources for user B in backend context  
        backend_resource = self.manager.generate_id(IDType.WEBSOCKET, prefix=user_b_id[:8],
                                                   context={"user_id": user_b_id, "service": "backend"})
        
        # User A resources should not be accessible when querying for user B
        user_a_resources = self.manager.find_resources_by_user_pattern_safe(user_a_id)
        user_b_resources = self.manager.find_resources_by_user_pattern_safe(user_b_id)
        
        self.assertIn(auth_resource, user_a_resources)
        self.assertNotIn(auth_resource, user_b_resources)
        self.assertIn(backend_resource, user_b_resources)  
        self.assertNotIn(backend_resource, user_a_resources)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])