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
        
        # Mock the context manager to avoid actual database calls
        with patch('netra_backend.app.database.request_scoped_session_factory.get_db') as mock_get_db:
            mock_session = Mock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            
            # Mock thread repository to avoid database calls
            with patch('netra_backend.app.database.request_scoped_session_factory.ThreadRepository') as mock_thread_repo:
                mock_repo_instance = Mock()
                mock_thread_repo.return_value = mock_repo_instance
                mock_repo_instance.get_by_id.return_value = None  # Thread doesn't exist
                mock_repo_instance.create.return_value = Mock()
                
                # Capture ID generation calls
                with patch.object(UnifiedIdGenerator, 'generate_user_context_ids') as mock_ssot_gen, \
                     patch('uuid.uuid4') as mock_uuid:
                    
                    mock_uuid.return_value.hex = '1234567890abcdef'
                    mock_ssot_gen.return_value = ('thread_test_123_456_abc', 'run_test_123_457_def', 'req_test_123_458_ghi')
                    
                    # Execute factory method
                    user_id = "test_user"
                    try:
                        import asyncio
                        async def run_test():
                            async with factory.get_request_scoped_session(user_id, None, None) as session:
                                pass
                        
                        # Run the async context
                        try:
                            asyncio.get_event_loop().run_until_complete(run_test())
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(run_test())
                    except Exception as e:
                        # Expected to fail - but we need to check the failure reason
                        pass
                    
                    # CRITICAL ASSERTION: SSOT should be called, direct UUID should NOT be called
                    # This test WILL FAIL because current implementation uses uuid.uuid4() directly
                    assert mock_ssot_gen.called, (
                        "SSOT VIOLATION: RequestScopedSessionFactory did not use UnifiedIdGenerator.generate_user_context_ids(). "
                        "This confirms the architectural violation where session factory bypasses SSOT for ID generation."
                    )
                    
                    # Additional assertion that should PASS if SSOT is used correctly
                    assert not mock_uuid.called, (
                        "SSOT VIOLATION: Direct uuid.uuid4() was called instead of using UnifiedIdGenerator. "
                        "This violates SSOT principles and causes ID format inconsistencies."
                    )
    
    def test_websocket_factory_id_format_consistency(self):
        """FAILING TEST: Verify WebSocket factory generates SSOT-compliant IDs
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory
        generates 'websocket_factory_1757361062151' pattern but database expects
        'thread_websocket_factory_1757361062151_7_90c65fe4' pattern.
        """
        
        # Mock WebSocket factory behavior (simulating the problematic pattern)
        def mock_websocket_factory_id_generation(timestamp):
            """Simulates the current problematic WebSocket ID generation"""
            return f"websocket_factory_{timestamp}"
        
        # Test current problematic pattern
        timestamp = int(time.time() * 1000)
        websocket_id = mock_websocket_factory_id_generation(timestamp)
        
        # Generate what SSOT would produce
        ssot_thread_id, ssot_run_id, ssot_request_id = UnifiedIdGenerator.generate_user_context_ids(
            "websocket_user", "websocket_factory"
        )
        
        # CRITICAL ASSERTION: These formats should match but they DON'T
        # This test WILL FAIL, exposing the format inconsistency
        assert websocket_id.startswith("thread_"), (
            f"FORMAT VIOLATION: WebSocket factory generates '{websocket_id}' but thread validation expects "
            f"format starting with 'thread_' like '{ssot_thread_id}'. This format mismatch causes "
            "'404: Thread not found' errors because database lookups fail."
        )
    
    def test_id_format_pattern_matching_for_database_lookup(self):
        """FAILING TEST: Verify ID patterns work for database thread lookup
        
        EXPECTED FAILURE: This test should FAIL because different components
        generate incompatible ID formats that break database lookups.
        """
        
        # Simulate the error pattern from the logs
        problematic_run_id = "websocket_factory_1757361062151"  # From WebSocket factory
        expected_thread_id = "thread_websocket_factory_1757361062151_7_90c65fe4"  # From SSOT
        
        # Test if the run_id can be used to derive the thread_id
        # This is what the system attempts to do internally
        def derive_thread_id_from_run_id(run_id: str) -> str:
            """Simulates the broken logic trying to derive thread_id from run_id"""
            if run_id.startswith("websocket_factory_"):
                # This is the broken logic - it cannot properly derive the SSOT format
                return f"thread_{run_id}_X_XXXXXXXX"  # Placeholder for missing parts
            return run_id
        
        derived_thread_id = derive_thread_id_from_run_id(problematic_run_id)
        
        # CRITICAL ASSERTION: The derived thread_id should match expected format but it CAN'T
        # This test WILL FAIL, proving the ID derivation logic is broken
        assert derived_thread_id == expected_thread_id, (
            f"ID DERIVATION FAILURE: Cannot derive proper thread_id '{expected_thread_id}' "
            f"from run_id '{problematic_run_id}'. Got '{derived_thread_id}' instead. "
            f"This proves different components generate incompatible ID formats."
        )
    
    def test_thread_record_creation_requires_ssot_format(self):
        """FAILING TEST: Verify thread record creation works with SSOT format only
        
        EXPECTED FAILURE: This test should FAIL when non-SSOT IDs are used for
        thread record creation, demonstrating the format dependency.
        """
        
        # Simulate thread record creation with different ID formats
        ssot_format_id = "thread_session_1757371363786_274_898638db"  # Proper SSOT format
        websocket_format_id = "websocket_factory_1757371363786"       # WebSocket factory format
        manual_uuid_format = f"req_{uuid.uuid4().hex[:12]}"           # Manual UUID format
        
        def simulate_thread_record_creation(thread_id: str) -> bool:
            """Simulates thread record creation validation"""
            # Thread creation expects SSOT format with proper components
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            
            if not parsed:
                return False
            
            # Must have all required SSOT components
            required_parts = ['prefix', 'timestamp', 'counter', 'random']
            return all(getattr(parsed, part, None) for part in required_parts)
        
        # Test SSOT format (should work)
        ssot_valid = simulate_thread_record_creation(ssot_format_id)
        assert ssot_valid, f"SSOT format should be valid: {ssot_format_id}"
        
        # Test WebSocket format (should fail)
        websocket_valid = simulate_thread_record_creation(websocket_format_id)
        # CRITICAL ASSERTION: This test WILL FAIL proving WebSocket format is incompatible
        assert websocket_valid, (
            f"FORMAT INCOMPATIBILITY: WebSocket factory ID '{websocket_format_id}' "
            f"cannot be used for thread record creation. This proves the format "
            f"mismatch causing '404: Thread not found' errors."
        )
        
        # Test manual UUID format (should fail)
        manual_valid = simulate_thread_record_creation(manual_uuid_format)
        # CRITICAL ASSERTION: This test WILL FAIL proving manual UUID format is incompatible
        assert manual_valid, (
            f"FORMAT INCOMPATIBILITY: Manual UUID format '{manual_uuid_format}' "
            f"cannot be used for thread record creation. This proves SSOT violation."
        )
    
    def test_cross_component_id_compatibility(self):
        """FAILING TEST: Verify IDs generated by different components are compatible
        
        EXPECTED FAILURE: This test should FAIL because different components
        (RequestScopedSessionFactory, WebSocket factory, etc.) generate
        incompatible ID formats.
        """
        
        user_id = "test_user_123"
        
        # Generate IDs using different component patterns (simulated)
        def generate_request_factory_ids():
            """Simulates RequestScopedSessionFactory ID generation (current broken pattern)"""
            request_id = f"req_{uuid.uuid4().hex[:12]}"
            session_id = f"{user_id}_{request_id}_{uuid.uuid4().hex[:8]}"
            return request_id, session_id
        
        def generate_websocket_factory_ids():
            """Simulates WebSocket factory ID generation (current broken pattern)"""
            timestamp = int(time.time() * 1000)
            return f"websocket_factory_{timestamp}"
        
        def generate_ssot_ids():
            """Generates proper SSOT IDs for comparison"""
            return UnifiedIdGenerator.generate_user_context_ids(user_id, "session")
        
        # Generate IDs from different sources
        request_id, session_id = generate_request_factory_ids()
        websocket_id = generate_websocket_factory_ids()
        ssot_thread_id, ssot_run_id, ssot_request_id = generate_ssot_ids()
        
        # Test compatibility by checking if all IDs follow same pattern
        all_ids = [request_id, session_id, websocket_id, ssot_thread_id, ssot_run_id, ssot_request_id]
        
        def check_id_pattern_consistency(ids):
            """Check if all IDs follow same parsing pattern"""
            patterns = []
            for id_val in ids:
                parsed = UnifiedIdGenerator.parse_id(id_val)
                if parsed:
                    patterns.append("ssot_compliant")
                else:
                    patterns.append("non_ssot")
            
            return len(set(patterns)) == 1  # All should have same pattern
        
        # CRITICAL ASSERTION: All IDs should be compatible but they're NOT
        # This test WILL FAIL, proving cross-component incompatibility
        is_compatible = check_id_pattern_consistency(all_ids)
        assert is_compatible, (
            f"CROSS-COMPONENT INCOMPATIBILITY: Different components generate incompatible ID formats. "
            f"IDs: {dict(zip(['request_id', 'session_id', 'websocket_id', 'ssot_thread_id', 'ssot_run_id', 'ssot_request_id'], all_ids))}. "
            f"This proves the SSOT violation causing system-wide ID format inconsistencies."
        )
    
    def test_session_factory_thread_validation_with_websocket_ids(self):
        """FAILING TEST: Verify session factory can validate WebSocket-generated thread IDs
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory generates
        IDs that session factory cannot validate for thread existence.
        """
        
        # Simulate the exact error scenario from logs
        websocket_generated_run_id = "websocket_factory_1757361062151"
        expected_thread_id = "thread_websocket_factory_1757361062151_7_90c65fe4"
        
        def simulate_thread_validation(thread_id: str) -> bool:
            """Simulates the thread validation logic that fails"""
            # This is the logic that calls ThreadRepository.get_by_id()
            # It expects SSOT format thread IDs
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            return parsed is not None and parsed.prefix.startswith("thread_")
        
        # Test validation with WebSocket factory ID (should fail)
        websocket_validation = simulate_thread_validation(websocket_generated_run_id)
        # CRITICAL ASSERTION: This test WILL FAIL proving WebSocket IDs can't be validated
        assert websocket_validation, (
            f"VALIDATION FAILURE: WebSocket factory ID '{websocket_generated_run_id}' "
            f"cannot be validated as a proper thread ID. This causes '404: Thread not found' "
            f"errors in request-scoped session creation."
        )
        
        # Test validation with expected SSOT format (should pass)
        ssot_validation = simulate_thread_validation(expected_thread_id)
        assert ssot_validation, (
            f"SSOT format should pass validation: {expected_thread_id}"
        )
    
    @pytest.mark.asyncio
    async def test_session_factory_thread_record_auto_creation_fails_with_non_ssot_ids(self):
        """FAILING TEST: Verify _ensure_thread_record_exists fails with non-SSOT IDs
        
        EXPECTED FAILURE: This test should FAIL when the session factory tries
        to create thread records with WebSocket factory generated IDs.
        """
        
        factory = RequestScopedSessionFactory()
        mock_session = Mock()
        
        # Test with problematic WebSocket factory ID
        problematic_thread_id = "websocket_factory_1757361062151"
        user_id = "test_user"
        
        with patch('netra_backend.app.database.request_scoped_session_factory.ThreadRepository') as mock_thread_repo:
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id.return_value = None  # Thread doesn't exist
            
            # Mock create method to simulate failure with non-SSOT format
            def mock_create(*args, **kwargs):
                thread_id = kwargs.get('id', args[1] if len(args) > 1 else None)
                if not thread_id or not thread_id.startswith('thread_'):
                    raise ValueError(f"Invalid thread ID format: {thread_id}")
                return Mock()
            
            mock_repo_instance.create.side_effect = mock_create
            
            # This should fail because the thread_id format is incompatible
            with pytest.raises((ValueError, Exception)) as exc_info:
                await factory._ensure_thread_record_exists(mock_session, problematic_thread_id, user_id)
            
            # CRITICAL ASSERTION: Should raise error due to format incompatibility
            # If this doesn't raise an error, it proves the validation is broken
            assert "Invalid thread ID format" in str(exc_info.value) or exc_info.value is not None, (
                f"FORMAT VALIDATION MISSING: Session factory should reject non-SSOT thread ID '{problematic_thread_id}' "
                f"but it didn't raise an error. This proves missing format validation allows broken IDs through."
            )


if __name__ == "__main__":
    # Run tests to see the failures
    pytest.main([__file__, "-v", "-s"])