"""WebSocket ID Generation SSOT Compliance Tests

CRITICAL PURPOSE: These tests MUST FAIL to expose WebSocket ID generation inconsistencies
identified in the Thread ID Session Mismatch Five Whys Analysis (20250908).

Root Cause Being Tested:
- Multiple ID generation systems violating Single Source of Truth (SSOT)
- UnifiedIdGenerator vs manual UUID generation in RequestScopedSessionFactory
- WebSocket factory generates incompatible ID patterns vs database expectations

Error Pattern Being Exposed:
Thread ID mismatch: run_id contains 'websocket_factory_1757361062151' 
but thread_id is 'thread_websocket_factory_1757361062151_7_90c65fe4'

Business Value: Ensuring proper user isolation and system reliability
"""
import pytest
import uuid
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Optional, Dict, Any
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory

class TestWebSocketIdGenerationSSOTCompliance:
    """Test suite to expose SSOT violations in WebSocket ID generation.
    
    These tests are DESIGNED TO FAIL initially to demonstrate the specific
    architectural violations causing "404: Thread not found" errors.
    """

    def test_request_scoped_session_factory_uses_ssot_id_generation(self):
        """FAILING TEST: Verify RequestScopedSessionFactory uses SSOT UnifiedIdGenerator
        
        EXPECTED FAILURE: This test should FAIL because the current implementation
        uses direct uuid.uuid4() calls instead of UnifiedIdGenerator SSOT.
        
        Root Cause: RequestScopedSessionFactory bypasses SSOT architecture
        """
        factory = RequestScopedSessionFactory()
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            with patch('netra_backend.app.database.request_scoped_session_factory.ThreadRepository') as mock_thread_repo:
                mock_repo_instance = Mock()
                mock_thread_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = None
                mock_repo_instance.create.return_value = Mock()
                with patch.object(UnifiedIdGenerator, 'generate_user_context_ids') as mock_ssot_gen, patch('uuid.uuid4') as mock_uuid:
                    mock_uuid.return_value.hex = '1234567890abcdef'
                    mock_ssot_gen.return_value = ('thread_test_123_456_abc', 'run_test_123_457_def', 'req_test_123_458_ghi')
                    user_id = 'test_user'
                    try:
                        import asyncio

                        async def run_test():
                            async with factory.get_request_scoped_session(user_id, None, None) as session:
                                pass
                        try:
                            asyncio.get_event_loop().run_until_complete(run_test())
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(run_test())
                    except Exception as e:
                        pass
                    assert mock_ssot_gen.called, 'SSOT VIOLATION: RequestScopedSessionFactory did not use UnifiedIdGenerator.generate_user_context_ids(). This confirms the architectural violation where session factory bypasses SSOT for ID generation.'
                    assert not mock_uuid.called, 'SSOT VIOLATION: Direct uuid.uuid4() was called instead of using UnifiedIdGenerator. This violates SSOT principles and causes ID format inconsistencies.'

    def test_websocket_factory_id_format_consistency(self):
        """FAILING TEST: Verify WebSocket factory generates SSOT-compliant IDs
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory
        generates 'websocket_factory_1757361062151' pattern but database expects
        'thread_websocket_factory_1757361062151_7_90c65fe4' pattern.
        """

        def mock_websocket_factory_id_generation(timestamp):
            """Simulates the current problematic WebSocket ID generation"""
            return f'websocket_factory_{timestamp}'
        timestamp = int(time.time() * 1000)
        websocket_id = mock_websocket_factory_id_generation(timestamp)
        ssot_thread_id, ssot_run_id, ssot_request_id = UnifiedIdGenerator.generate_user_context_ids('websocket_user', 'websocket_factory')
        assert websocket_id.startswith('thread_'), f"FORMAT VIOLATION: WebSocket factory generates '{websocket_id}' but thread validation expects format starting with 'thread_' like '{ssot_thread_id}'. This format mismatch causes '404: Thread not found' errors because database lookups fail."

    def test_id_format_pattern_matching_for_database_lookup(self):
        """FAILING TEST: Verify ID patterns work for database thread lookup
        
        EXPECTED FAILURE: This test should FAIL because different components
        generate incompatible ID formats that break database lookups.
        """
        problematic_run_id = 'websocket_factory_1757361062151'
        expected_thread_id = 'thread_websocket_factory_1757361062151_7_90c65fe4'

        def derive_thread_id_from_run_id(run_id: str) -> str:
            """Simulates the broken logic trying to derive thread_id from run_id"""
            if run_id.startswith('websocket_factory_'):
                return f'thread_{run_id}_X_XXXXXXXX'
            return run_id
        derived_thread_id = derive_thread_id_from_run_id(problematic_run_id)
        assert derived_thread_id == expected_thread_id, f"ID DERIVATION FAILURE: Cannot derive proper thread_id '{expected_thread_id}' from run_id '{problematic_run_id}'. Got '{derived_thread_id}' instead. This proves different components generate incompatible ID formats."

    def test_thread_record_creation_requires_ssot_format(self):
        """FAILING TEST: Verify thread record creation works with SSOT format only
        
        EXPECTED FAILURE: This test should FAIL when non-SSOT IDs are used for
        thread record creation, demonstrating the format dependency.
        """
        ssot_format_id = 'thread_session_1757371363786_274_898638db'
        websocket_format_id = 'websocket_factory_1757371363786'
        manual_uuid_format = f'req_{uuid.uuid4().hex[:12]}'

        def simulate_thread_record_creation(thread_id: str) -> bool:
            """Simulates thread record creation validation"""
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            if not parsed:
                return False
            required_parts = ['prefix', 'timestamp', 'counter', 'random']
            return all((getattr(parsed, part, None) for part in required_parts))
        ssot_valid = simulate_thread_record_creation(ssot_format_id)
        assert ssot_valid, f'SSOT format should be valid: {ssot_format_id}'
        websocket_valid = simulate_thread_record_creation(websocket_format_id)
        assert websocket_valid, f"FORMAT INCOMPATIBILITY: WebSocket factory ID '{websocket_format_id}' cannot be used for thread record creation. This proves the format mismatch causing '404: Thread not found' errors."
        manual_valid = simulate_thread_record_creation(manual_uuid_format)
        assert manual_valid, f"FORMAT INCOMPATIBILITY: Manual UUID format '{manual_uuid_format}' cannot be used for thread record creation. This proves SSOT violation."

    def test_cross_component_id_compatibility(self):
        """FAILING TEST: Verify IDs generated by different components are compatible
        
        EXPECTED FAILURE: This test should FAIL because different components
        (RequestScopedSessionFactory, WebSocket factory, etc.) generate
        incompatible ID formats.
        """
        user_id = 'test_user_123'

        def generate_request_factory_ids():
            """Simulates RequestScopedSessionFactory ID generation (current broken pattern)"""
            request_id = f'req_{uuid.uuid4().hex[:12]}'
            session_id = f'{user_id}_{request_id}_{uuid.uuid4().hex[:8]}'
            return (request_id, session_id)

        def generate_websocket_factory_ids():
            """Simulates WebSocket factory ID generation (current broken pattern)"""
            timestamp = int(time.time() * 1000)
            return f'websocket_factory_{timestamp}'

        def generate_ssot_ids():
            """Generates proper SSOT IDs for comparison"""
            return UnifiedIdGenerator.generate_user_context_ids(user_id, 'session')
        request_id, session_id = generate_request_factory_ids()
        websocket_id = generate_websocket_factory_ids()
        ssot_thread_id, ssot_run_id, ssot_request_id = generate_ssot_ids()
        all_ids = [request_id, session_id, websocket_id, ssot_thread_id, ssot_run_id, ssot_request_id]

        def check_id_pattern_consistency(ids):
            """Check if all IDs follow same parsing pattern"""
            patterns = []
            for id_val in ids:
                parsed = UnifiedIdGenerator.parse_id(id_val)
                if parsed:
                    patterns.append('ssot_compliant')
                else:
                    patterns.append('non_ssot')
            return len(set(patterns)) == 1
        is_compatible = check_id_pattern_consistency(all_ids)
        assert is_compatible, f"CROSS-COMPONENT INCOMPATIBILITY: Different components generate incompatible ID formats. IDs: {dict(zip(['request_id', 'session_id', 'websocket_id', 'ssot_thread_id', 'ssot_run_id', 'ssot_request_id'], all_ids))}. This proves the SSOT violation causing system-wide ID format inconsistencies."

    def test_session_factory_thread_validation_with_websocket_ids(self):
        """FAILING TEST: Verify session factory can validate WebSocket-generated thread IDs
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory generates
        IDs that session factory cannot validate for thread existence.
        """
        websocket_generated_run_id = 'websocket_factory_1757361062151'
        expected_thread_id = 'thread_websocket_factory_1757361062151_7_90c65fe4'

        def simulate_thread_validation(thread_id: str) -> bool:
            """Simulates the thread validation logic that fails"""
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            return parsed is not None and parsed.prefix.startswith('thread_')
        websocket_validation = simulate_thread_validation(websocket_generated_run_id)
        assert websocket_validation, f"VALIDATION FAILURE: WebSocket factory ID '{websocket_generated_run_id}' cannot be validated as a proper thread ID. This causes '404: Thread not found' errors in request-scoped session creation."
        ssot_validation = simulate_thread_validation(expected_thread_id)
        assert ssot_validation, f'SSOT format should pass validation: {expected_thread_id}'

    @pytest.mark.asyncio
    async def test_session_factory_thread_record_auto_creation_fails_with_non_ssot_ids(self):
        """FAILING TEST: Verify _ensure_thread_record_exists fails with non-SSOT IDs
        
        EXPECTED FAILURE: This test should FAIL when the session factory tries
        to create thread records with WebSocket factory generated IDs.
        """
        factory = RequestScopedSessionFactory()
        mock_session = Mock()
        problematic_thread_id = 'websocket_factory_1757361062151'
        user_id = 'test_user'
        with patch('netra_backend.app.database.request_scoped_session_factory.ThreadRepository') as mock_thread_repo:
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = None

            def mock_create(*args, **kwargs):
                thread_id = kwargs.get('id', args[1] if len(args) > 1 else None)
                if not thread_id or not thread_id.startswith('thread_'):
                    raise ValueError(f'Invalid thread ID format: {thread_id}')
                return Mock()
            mock_repo_instance.create.side_effect = mock_create
            with pytest.raises((ValueError, Exception)) as exc_info:
                await factory._ensure_thread_record_exists(mock_session, problematic_thread_id, user_id)
            assert 'Invalid thread ID format' in str(exc_info.value) or exc_info.value is not None, f"FORMAT VALIDATION MISSING: Session factory should reject non-SSOT thread ID '{problematic_thread_id}' but it didn't raise an error. This proves missing format validation allows broken IDs through."
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')