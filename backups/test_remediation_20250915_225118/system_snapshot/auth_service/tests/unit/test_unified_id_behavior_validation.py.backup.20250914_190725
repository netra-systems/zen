"""
Behavioral validation tests for UnifiedIDManager compliance in auth service.

This test file validates that ID generation behavior matches UnifiedIDManager patterns
and detects behavioral violations where raw UUIDs are used instead of structured IDs.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and ID Consistency  
- Value Impact: Ensures ID behavior is consistent across auth service components
- Strategic Impact: Prevents ID-related bugs and enables proper resource tracking

CRITICAL: These tests MUST FAIL initially to prove behavioral violations exist.
"""

import re
import uuid
from typing import Dict, List, Optional
from unittest.mock import patch, MagicMock

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, get_id_manager


class TestUnifiedIDManagerBehaviorValidation(SSotAsyncTestCase):
    """Test behavioral compliance with UnifiedIDManager patterns."""
    
    async def asyncSetUp(self):
        """Set up test environment with clean ID manager."""
        await super().asyncSetUp()
        self.id_manager = get_id_manager()
        self.id_manager.clear_all()  # Clean slate for testing
        self.behavioral_violations = []
    
    def test_oauth_handler_id_generation_behavior(self):
        """
        BEHAVIORAL VIOLATION TEST: OAuth handler should use structured IDs.
        
        Tests the actual behavior of oauth_handler.py ID generation.
        This test MUST FAIL initially because oauth_handler uses raw UUID.
        
        Expected violations:
        - state_token generation uses uuid.uuid4() instead of UnifiedIDManager
        - session_id generation uses uuid.uuid4() instead of structured format
        - user_id generation uses uuid.uuid4() instead of USER type ID
        """
        # Import the actual oauth handler to test its behavior
        try:
            from auth_service.auth_core.oauth.oauth_handler import OAuthHandler
            
            # Test state token generation behavior
            handler = OAuthHandler()
            
            # CRITICAL TEST: This should fail because state tokens use raw UUID
            with patch('auth_service.auth_core.oauth.oauth_handler.uuid') as mock_uuid:
                mock_uuid.uuid4.return_value = MagicMock()
                mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value="test-uuid-string")
                
                # Attempt to generate state token - this calls the violation code
                try:
                    # This will trigger uuid.uuid4() call if violation exists
                    result = handler._generate_state_token() if hasattr(handler, '_generate_state_token') else None
                    
                    # If this doesn't fail, it means the violation still exists
                    if mock_uuid.uuid4.called:
                        self.behavioral_violations.append(
                            "oauth_handler._generate_state_token() uses uuid.uuid4() instead of UnifiedIDManager"
                        )
                    
                except Exception as e:
                    # Expected - the method might not exist or have different signature
                    pass
            
            # ASSERTION: This should FAIL initially due to behavioral violations
            self.assertEqual(len(self.behavioral_violations), 0,
                           f"Found behavioral violations in OAuth handler: {self.behavioral_violations}")
            
        except ImportError:
            self.skipTest("OAuth handler not available for behavioral testing")
    
    def test_session_service_id_generation_behavior(self):
        """
        BEHAVIORAL VIOLATION TEST: Session service should use UnifiedIDManager for session IDs.
        
        This test MUST FAIL initially because session service uses raw uuid.uuid4().
        
        Expected violations:
        - session_id generation uses uuid.uuid4() instead of IDType.SESSION
        """
        try:
            from auth_service.services.session_service import SessionService
            
            # Test session ID generation behavior
            with patch('auth_service.services.session_service.uuid') as mock_uuid:
                mock_uuid.uuid4.return_value = MagicMock()
                mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value="session-uuid-test")
                
                # Attempt to create session - should trigger uuid.uuid4() violation
                service = SessionService()
                
                # Try to call session creation methods that might use uuid.uuid4()
                try:
                    # This will expose the behavioral violation
                    if hasattr(service, 'create_session'):
                        service.create_session("test_user")
                    
                    if mock_uuid.uuid4.called:
                        self.behavioral_violations.append(
                            "SessionService uses uuid.uuid4() instead of UnifiedIDManager.generate_id(IDType.SESSION)"
                        )
                        
                except Exception as e:
                    # Expected - service might need different parameters
                    pass
            
            # ASSERTION: This should FAIL initially due to behavioral violations  
            self.assertEqual(len(self.behavioral_violations), 0,
                           f"Found behavioral violations in SessionService: {self.behavioral_violations}")
            
        except ImportError:
            self.skipTest("SessionService not available for behavioral testing")
    
    def test_token_factory_id_generation_behavior(self):
        """
        BEHAVIORAL VIOLATION TEST: Token factory should use structured IDs.
        
        This test MUST FAIL initially because token factories use raw uuid.uuid4().
        
        Expected violations:
        - JWT ID (jti) generation uses uuid.uuid4() instead of structured format
        - User ID defaults use uuid.uuid4() instead of IDType.USER
        """
        try:
            from auth_service.tests.factories.token_factory import TokenFactory
            
            # Test token factory behavior
            factory = TokenFactory()
            
            # Generate token and check ID format
            token_data = factory.create_jwt_token()
            
            # Check if jti field looks like raw UUID vs structured ID
            jti = token_data.get('jti')
            if jti:
                # Raw UUID pattern: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx  
                uuid_pattern = re.compile(
                    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                )
                
                # UnifiedIDManager structured pattern: type_counter_uuid8
                structured_pattern = re.compile(r'^[a-z]+_\d+_[0-9a-f]{8}$')
                
                if uuid_pattern.match(jti):
                    self.behavioral_violations.append(
                        f"TokenFactory.create_jwt_token() generates raw UUID jti '{jti}' instead of structured ID"
                    )
                elif not structured_pattern.match(jti):
                    # Neither pattern - still a violation
                    self.behavioral_violations.append(
                        f"TokenFactory.create_jwt_token() generates non-standard jti '{jti}' - should use UnifiedIDManager"
                    )
            
            # ASSERTION: This should FAIL initially due to behavioral violations
            self.assertEqual(len(self.behavioral_violations), 0,
                           f"Found behavioral violations in TokenFactory: {self.behavioral_violations}")
            
        except ImportError:
            self.skipTest("TokenFactory not available for behavioral testing")
    
    def test_user_factory_id_generation_behavior(self):
        """
        BEHAVIORAL VIOLATION TEST: User factory should use UnifiedIDManager for user IDs.
        
        This test MUST FAIL initially because user factory uses raw uuid.uuid4().
        
        Expected violations:
        - User ID generation uses uuid.uuid4() instead of IDType.USER
        - Provider user IDs use uuid fragments instead of structured format
        """
        try:
            from auth_service.tests.factories.user_factory import UserFactory
            
            # Test user factory behavior
            factory = UserFactory()
            
            # Generate user and check ID format
            user_data = factory.create_user()
            
            # Check user ID format
            user_id = user_data.get('id')
            if user_id:
                # Check if it's a raw UUID vs structured ID
                uuid_pattern = re.compile(
                    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                )
                
                if uuid_pattern.match(user_id):
                    self.behavioral_violations.append(
                        f"UserFactory.create_user() generates raw UUID user_id '{user_id}' instead of structured ID"
                    )
                elif not user_id.startswith('user_'):
                    self.behavioral_violations.append(
                        f"UserFactory.create_user() generates non-standard user_id '{user_id}' - should use IDType.USER"
                    )
            
            # ASSERTION: This should FAIL initially due to behavioral violations
            self.assertEqual(len(self.behavioral_violations), 0,
                           f"Found behavioral violations in UserFactory: {self.behavioral_violations}")
            
        except ImportError:
            self.skipTest("UserFactory not available for behavioral testing")
    
    def test_id_format_consistency_across_factories(self):
        """
        CONSISTENCY VIOLATION TEST: All factories should use consistent ID patterns.
        
        This comprehensive test checks that all factory-generated IDs follow
        UnifiedIDManager patterns instead of random UUID generation.
        
        This test MUST FAIL initially due to inconsistent ID generation across factories.
        """
        factory_violations = []
        
        factories_to_test = [
            ('TokenFactory', 'auth_service.tests.factories.token_factory'),
            ('UserFactory', 'auth_service.tests.factories.user_factory'),  
            ('SessionFactory', 'auth_service.tests.factories.session_factory'),
            ('AuditFactory', 'auth_service.tests.factories.audit_factory'),
        ]
        
        for factory_name, module_path in factories_to_test:
            try:
                # Import and test factory
                module = __import__(module_path, fromlist=[factory_name])
                factory_class = getattr(module, factory_name)
                factory = factory_class()
                
                # Test different creation methods
                test_methods = [
                    'create_user', 'create_jwt_token', 'create_session', 
                    'create_audit_event', 'create_token_data'
                ]
                
                for method_name in test_methods:
                    if hasattr(factory, method_name):
                        try:
                            result = getattr(factory, method_name)()
                            
                            # Check all ID fields in result
                            id_fields = ['id', 'user_id', 'session_id', 'jti', 'token_id']
                            
                            for field in id_fields:
                                if isinstance(result, dict) and field in result:
                                    id_value = result[field]
                                    if self._is_raw_uuid(id_value):
                                        factory_violations.append(
                                            f"{factory_name}.{method_name}() field '{field}' "
                                            f"uses raw UUID '{id_value}' instead of structured ID"
                                        )
                                        
                        except Exception as e:
                            # Skip methods that require parameters
                            continue
                            
            except ImportError:
                continue
        
        # ASSERTION: This should FAIL initially due to widespread violations
        self.assertEqual(len(factory_violations), 0,
                        f"Found {len(factory_violations)} ID consistency violations across factories: "
                        f"{factory_violations}")
    
    def test_service_layer_id_generation_patterns(self):
        """
        SERVICE VIOLATION TEST: Service layer should use UnifiedIDManager consistently.
        
        This test checks service classes for consistent ID generation patterns.
        
        This test MUST FAIL initially due to service layer uuid.uuid4() violations.
        """
        service_violations = []
        
        services_to_test = [
            ('UserService', 'auth_service.services.user_service'),
            ('SessionService', 'auth_service.services.session_service'),
            ('TokenRefreshService', 'auth_service.services.token_refresh_service'),
        ]
        
        for service_name, module_path in services_to_test:
            try:
                # Import service
                module = __import__(module_path, fromlist=[service_name])
                service_class = getattr(module, service_name)
                
                # Mock uuid.uuid4 to detect direct usage
                with patch(f'{module_path}.uuid') as mock_uuid:
                    mock_uuid.uuid4.return_value = MagicMock()
                    mock_uuid.uuid4.return_value.__str__ = MagicMock(return_value="service-violation-test")
                    
                    try:
                        # Instantiate service (may trigger uuid.uuid4() calls)
                        service = service_class()
                        
                        if mock_uuid.uuid4.called:
                            service_violations.append(
                                f"{service_name} instantiation uses uuid.uuid4() instead of UnifiedIDManager"
                            )
                            
                    except Exception as e:
                        # Service may require dependencies - that's okay
                        pass
                        
            except ImportError:
                continue
        
        # ASSERTION: This should FAIL initially due to service violations
        self.assertEqual(len(service_violations), 0,
                        f"Found service layer violations: {service_violations}")
    
    def test_correct_unified_id_manager_usage_patterns(self):
        """
        POSITIVE TEST: Demonstrate correct UnifiedIDManager usage patterns.
        
        This test shows what the code SHOULD do after violations are fixed.
        This test should PASS to prove UnifiedIDManager works correctly.
        """
        manager = get_id_manager()
        
        # Correct patterns for different ID types
        correct_patterns = {
            IDType.USER: manager.generate_id(IDType.USER, prefix="auth"),
            IDType.SESSION: manager.generate_id(IDType.SESSION, context={"service": "auth"}),
            IDType.REQUEST: manager.generate_id(IDType.REQUEST),
            IDType.WEBSOCKET: manager.generate_id(IDType.WEBSOCKET),
        }
        
        # Verify all generated IDs follow structured patterns
        for id_type, generated_id in correct_patterns.items():
            # Should contain type name
            self.assertIn(id_type.value, generated_id, 
                         f"Generated ID '{generated_id}' should contain type '{id_type.value}'")
            
            # Should be valid according to manager
            self.assertTrue(manager.is_valid_id(generated_id, id_type),
                           f"Generated ID '{generated_id}' should be valid for type {id_type}")
            
            # Should NOT be a raw UUID
            self.assertFalse(self._is_raw_uuid(generated_id),
                            f"Generated ID '{generated_id}' should not be a raw UUID")
    
    def test_migration_compatibility_behavior(self):
        """
        MIGRATION TEST: Test backward compatibility during UUID->structured migration.
        
        This test validates that UnifiedIDManager can handle both old UUIDs
        and new structured IDs during the migration period.
        
        This test should PASS to validate migration compatibility.
        """
        manager = get_id_manager()
        
        # Test raw UUID validation (backward compatibility)
        raw_uuid = str(uuid.uuid4())
        self.assertTrue(manager.is_valid_id_format_compatible(raw_uuid),
                       "UnifiedIDManager should accept raw UUIDs during migration")
        
        # Test structured ID validation (forward compatibility)
        structured_id = manager.generate_id(IDType.USER)
        self.assertTrue(manager.is_valid_id_format_compatible(structured_id),
                       "UnifiedIDManager should accept structured IDs")
        
        # Test conversion capability
        converted_id = manager.convert_uuid_to_structured(raw_uuid, IDType.USER)
        self.assertIn("user_", converted_id)
        self.assertNotEqual(raw_uuid, converted_id)
    
    def _is_raw_uuid(self, value: str) -> bool:
        """Check if value is a raw UUID format."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False
    
    async def asyncTearDown(self):
        """Clean up and report behavioral violations."""
        await super().asyncTearDown()
        
        if self.behavioral_violations:
            print(f"\nBEHAVIORAL VIOLATION SUMMARY: Found {len(self.behavioral_violations)} violations:")
            for violation in self.behavioral_violations:
                print(f"  {violation}")


class TestUnifiedIDManagerMigrationBehavior(SSotAsyncTestCase):
    """Test migration behavior from UUID to UnifiedIDManager patterns."""
    
    async def asyncSetUp(self):
        """Set up migration test environment."""
        await super().asyncSetUp()
        self.manager = get_id_manager()
        self.manager.clear_all()
    
    def test_dual_id_system_compatibility(self):
        """
        MIGRATION TEST: Test that both old and new ID systems work together.
        
        During migration, the system must handle both UUID and structured IDs.
        This test validates the compatibility bridge functionality.
        """
        # Test old UUID format acceptance
        old_uuid = "550e8400-e29b-41d4-a716-446655440000"
        self.assertTrue(self.manager.is_valid_id_format_compatible(old_uuid))
        
        # Test new structured format
        new_id = self.manager.generate_id(IDType.USER, prefix="migrate")
        self.assertTrue(self.manager.is_valid_id_format_compatible(new_id))
        
        # Test conversion between formats
        converted = self.manager.convert_uuid_to_structured(old_uuid, IDType.USER)
        self.assertNotEqual(old_uuid, converted)
        self.assertIn("user_", converted)
    
    def test_performance_impact_measurement(self):
        """
        PERFORMANCE TEST: Measure performance impact of UnifiedIDManager vs raw UUID.
        
        This test quantifies the performance difference to validate that
        structured ID generation is not significantly slower than raw UUID.
        """
        import time
        
        # Measure raw UUID generation time
        start_time = time.time()
        raw_uuids = [str(uuid.uuid4()) for _ in range(1000)]
        raw_time = time.time() - start_time
        
        # Measure UnifiedIDManager generation time
        start_time = time.time()
        structured_ids = [self.manager.generate_id(IDType.USER) for _ in range(1000)]
        structured_time = time.time() - start_time
        
        # Performance should be reasonable (less than 5x slower)
        performance_ratio = structured_time / raw_time if raw_time > 0 else float('inf')
        
        self.assertLess(performance_ratio, 5.0,
                       f"UnifiedIDManager is {performance_ratio:.2f}x slower than raw UUID - "
                       f"this may indicate performance issues")
        
        # Verify all generated IDs are unique and valid
        self.assertEqual(len(set(structured_ids)), 1000, "All structured IDs should be unique")
        
        print(f"\nPerformance comparison: UnifiedIDManager is {performance_ratio:.2f}x raw UUID time")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])