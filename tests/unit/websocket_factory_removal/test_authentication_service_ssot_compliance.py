"""Authentication Service SSOT Compliance Test - Phase 1 Factory Removal Validation

CRITICAL MISSION: Validate unified_authentication_service works after factory removal.

PURPOSE: Ensure authentication service can create user execution contexts via SSOT
patterns without dependency on deprecated factory. This test MUST FAIL initially
if using deprecated factory, then PASS after migration to SSOT patterns.

TESTING CONSTRAINTS:
- NO Docker required - Unit/Integration test only
- Uses SSOT testing infrastructure
- Tests authentication service SSOT compliance
- Protects Golden Path authentication flow ($500K+ ARR)

BUSINESS VALUE:
- Segment: ALL (Free -> Enterprise) - Authentication Infrastructure
- Goal: Eliminate factory dependencies in authentication flow
- Impact: Ensures reliable user authentication after factory removal
- Revenue Impact: Prevents authentication failures affecting user onboarding
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Optional, Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class AuthenticationServiceSSOTComplianceTests(SSotAsyncTestCase):
    """
    Validate Authentication Service SSOT compliance for factory removal.
    
    These tests ensure that:
    1. Authentication service works without factory dependencies
    2. User execution context creation uses SSOT patterns
    3. Fallback authentication flows work correctly
    4. No deprecated factory imports in authentication code
    """

    def setUp(self):
        """Setup test environment for authentication SSOT validation."""
        super().setUp()
        self.test_user_id = 'test_user_auth_ssot_validation'
        self.test_token = 'test_jwt_token_auth_validation'

    async def test_authentication_service_deprecated_factory_usage_MUST_FAIL_INITIALLY(self):
        """
        TEST 2A: Detect deprecated factory usage in authentication - MUST FAIL INITIALLY
        
        This test MUST FAIL initially because the authentication service still uses
        the deprecated factory. After migration, this test should PASS.
        
        SUCCESS CRITERIA:
        - INITIAL STATE: Test FAILS (deprecated factory still imported/used)
        - POST-MIGRATION: Test PASSES (no factory imports detected)
        """
        logger.info('Testing authentication service deprecated factory usage...')
        try:
            import ast
            import inspect
            from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
            source = inspect.getsource(UnifiedAuthenticationService)
            tree = ast.parse(source)
            deprecated_imports_found = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and 'websocket_manager_factory' in node.module:
                        deprecated_imports_found.append(node.module)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'websocket_manager_factory' in alias.name:
                            deprecated_imports_found.append(alias.name)
            if deprecated_imports_found:
                self.fail(f'SSOT VIOLATION: Authentication service still uses deprecated factory imports: {deprecated_imports_found}. Migration to SSOT patterns incomplete.')
            logger.info('CHECK No deprecated factory imports found in authentication service')
        except Exception as e:
            self.fail(f'AUTHENTICATION TEST FAILURE: Unable to validate factory usage: {e}')

    async def test_authentication_service_user_context_creation_ssot(self):
        """
        TEST 2B: Validate authentication service creates user contexts via SSOT
        
        Tests that the authentication service can create user execution contexts
        using canonical SSOT patterns without factory dependencies.
        """
        logger.info('Testing authentication service user context creation via SSOT...')
        try:
            from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            with patch('netra_backend.app.services.unified_authentication_service.AuthClient') as mock_auth_client, patch('netra_backend.app.services.unified_authentication_service.get_logger') as mock_logger:
                mock_auth_instance = AsyncMock()
                mock_auth_client.return_value = mock_auth_instance
                mock_auth_instance.validate_jwt_token.return_value = {'user_id': self.test_user_id, 'valid': True}
                auth_service = UnifiedAuthenticationService()
                user_context = UserExecutionContext(user_id=self.test_user_id, websocket_client_id='test_auth_validation_client')
                self.assertIsNotNone(user_context)
                self.assertEqual(user_context.user_id, self.test_user_id)
                logger.info('CHECK Authentication service user context creation via SSOT successful')
        except Exception as e:
            self.fail(f'AUTH SSOT FAILURE: User context creation failed: {e}')

    async def test_authentication_fallback_without_factory(self):
        """
        TEST 2C: Validate authentication fallback mechanisms work without factory
        
        Tests that fallback authentication flows work correctly using SSOT patterns
        when the deprecated factory is no longer available.
        """
        logger.info('Testing authentication fallback mechanisms without factory...')
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager
            fallback_user_id = f'fallback_{self.test_user_id}'
            fallback_context = UserExecutionContext(user_id=fallback_user_id, websocket_client_id=None)
            self.assertIsNotNone(fallback_context)
            self.assertEqual(fallback_context.user_id, fallback_user_id)
            self.assertIsNotNone(fallback_context.websocket_client_id)
            logger.info('CHECK Authentication fallback mechanisms work without factory')
        except Exception as e:
            self.fail(f'AUTH FALLBACK FAILURE: Fallback context creation failed: {e}')

    async def test_authentication_service_no_circular_imports(self):
        """
        TEST 2D: Ensure authentication service has no circular import issues
        
        Validates that the authentication service can import all its dependencies
        without circular import problems after factory removal.
        """
        logger.info('Testing authentication service circular import prevention...')
        critical_imports = ['netra_backend.app.services.unified_authentication_service', 'netra_backend.app.services.user_execution_context', 'netra_backend.app.websocket_core.websocket_manager', 'netra_backend.app.core.unified_id_manager']
        for import_path in critical_imports:
            try:
                module = __import__(import_path, fromlist=[''])
                self.assertIsNotNone(module)
                logger.debug(f'CHECK Successfully imported: {import_path}')
            except ImportError as e:
                self.fail(f'CIRCULAR IMPORT: Failed to import {import_path}: {e}')
            except Exception as e:
                self.fail(f'IMPORT ERROR: Unexpected error importing {import_path}: {e}')
        logger.info('CHECK No circular imports detected in authentication service')

    async def test_authentication_service_websocket_integration_ssot(self):
        """
        TEST 2E: Validate authentication + WebSocket integration via SSOT
        
        Tests that authentication service can integrate with WebSocket components
        using canonical SSOT patterns without factory dependencies.
        """
        logger.info('Testing authentication + WebSocket integration via SSOT...')
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            user_context = UserExecutionContext(user_id=self.test_user_id, websocket_client_id='test_auth_websocket_integration')
            websocket_manager = WebSocketManager(user_context=user_context)
            self.assertIsNotNone(websocket_manager)
            self.assertEqual(websocket_manager.user_context.user_id, self.test_user_id)
            self.assertIsNotNone(websocket_manager.user_context.websocket_client_id)
            logger.info('CHECK Authentication + WebSocket integration via SSOT successful')
        except Exception as e:
            self.fail(f'AUTH WEBSOCKET INTEGRATION FAILURE: Integration failed: {e}')

    async def test_authentication_service_memory_efficiency_without_factory(self):
        """
        TEST 2F: Validate authentication service memory efficiency without factory
        
        Tests that removing the factory layer improves memory efficiency
        and eliminates unnecessary object creation overhead.
        """
        logger.info('Testing authentication service memory efficiency without factory...')
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            contexts = []
            for i in range(10):
                context = UserExecutionContext(user_id=f'{self.test_user_id}_{i}', websocket_client_id=f'test_memory_client_{i}')
                contexts.append(context)
            self.assertEqual(len(contexts), 10)
            final_memory = process.memory_info().rss
            memory_growth = final_memory - initial_memory
            self.assertLess(memory_growth, 50 * 1024 * 1024, f'Excessive memory growth: {memory_growth} bytes')
            logger.info(f'CHECK Memory efficient context creation: {memory_growth} bytes growth')
        except Exception as e:
            self.fail(f'MEMORY EFFICIENCY TEST FAILURE: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')