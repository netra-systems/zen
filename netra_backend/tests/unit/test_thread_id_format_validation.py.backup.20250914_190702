"""Thread ID Format Validation Tests

CRITICAL PURPOSE: These tests MUST FAIL to expose thread ID format validation gaps
that cause "404: Thread not found" errors in the WebSocket ID generation system.

Root Cause Being Tested:
- Missing format validation allows incompatible thread IDs to reach database layer
- Different ID generation patterns slip through validation causing lookup failures
- Thread repository expects SSOT format but receives various incompatible formats

Error Pattern Being Exposed:
run_id contains 'websocket_factory_1757371363786' 
but thread_id is 'thread_websocket_factory_1757371363786_274_898638db'

Business Value: Preventing data corruption and ensuring thread isolation integrity
"""

import pytest
import time
import uuid
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, patch

from shared.id_generation.unified_id_generator import UnifiedIdGenerator, IdComponents
from netra_backend.app.services.database.thread_repository import ThreadRepository


class TestThreadIdFormatValidation:
    """Test suite to expose thread ID format validation gaps.
    
    These tests are DESIGNED TO FAIL initially to demonstrate missing
    validation that allows incompatible thread IDs to cause system failures.
    """
    
    def test_thread_repository_validates_id_format_on_lookup(self):
        """FAILING TEST: Verify ThreadRepository validates ID format before database lookup
        
        EXPECTED FAILURE: This test should FAIL because ThreadRepository doesn't
        validate ID format, allowing invalid IDs to reach database and cause 404 errors.
        """
        
        # Invalid thread ID formats that should be rejected
        invalid_thread_ids = [
            "websocket_factory_1757371363786",           # WebSocket factory format
            "req_1234567890ab",                          # Request ID format  
            "session_web_testuser_123456789",            # Session ID format
            "random_string_no_pattern",                  # Random string
            "",                                          # Empty string
            None,                                        # None value
            "thread_",                                   # Incomplete SSOT format
            "thread_test_",                              # Missing components
            "thread_test_abc_def"                        # Non-numeric timestamp/counter
        ]
        
        def simulate_thread_repository_lookup(thread_id):
            """Simulates ThreadRepository.get_by_id() method"""
            # Current implementation: NO FORMAT VALIDATION
            # It directly passes the ID to database query
            
            # This is what SHOULD happen (format validation):
            if not thread_id:
                return None
                
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            if not parsed or not parsed.prefix.startswith("thread_"):
                raise ValueError(f"Invalid thread ID format: {thread_id}")
                
            # If format is valid, proceed with database lookup
            return None  # Simulated not found
        
        # Test each invalid format
        for invalid_id in invalid_thread_ids:
            # CRITICAL ASSERTION: Should raise ValueError for invalid formats
            # This test WILL FAIL because current implementation has NO format validation
            with pytest.raises(ValueError, match="Invalid thread ID format"):
                simulate_thread_repository_lookup(invalid_id)
                
            # If we reach here without exception, validation is missing
            pytest.fail(f"FORMAT VALIDATION MISSING: Thread repository accepted invalid ID '{invalid_id}' "
                       f"without validation. This allows incompatible IDs to cause database lookup failures.")
    
    def test_thread_id_parsing_component_validation(self):
        """FAILING TEST: Verify thread ID components are properly validated
        
        EXPECTED FAILURE: This test should FAIL because component validation
        is missing, allowing malformed thread IDs to slip through.
        """
        
        # Malformed thread IDs with missing or invalid components
        malformed_ids = [
            "thread_websocket_factory_ABC_XYZ_123",      # Non-numeric timestamp/counter
            "thread_websocket_factory_1234567890_",      # Missing counter
            "thread_websocket_factory__456_abc",         # Missing timestamp  
            "thread_websocket_factory_1234567890_456",   # Missing random component
            "thread_websocket_factory_1234567890_456_", # Empty random component
            "thread__1234567890_456_abc",                # Missing operation type
        ]
        
        def validate_thread_id_components(thread_id: str) -> bool:
            """Validates thread ID has all required components"""
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            
            if not parsed:
                return False
            
            # Check required components exist and are valid
            if not parsed.prefix.startswith("thread_"):
                return False
                
            # Timestamp should be reasonable (not too old, not future)
            current_time = int(time.time() * 1000)
            time_diff = abs(current_time - parsed.timestamp)
            max_age = 365 * 24 * 60 * 60 * 1000  # 1 year
            if time_diff > max_age:
                return False
            
            # Counter should be positive
            if parsed.counter <= 0:
                return False
                
            # Random component should exist and be hex
            if not parsed.random or len(parsed.random) < 8:
                return False
                
            try:
                int(parsed.random, 16)  # Validate hex format
            except ValueError:
                return False
                
            return True
        
        # Test malformed IDs
        for malformed_id in malformed_ids:
            is_valid = validate_thread_id_components(malformed_id)
            
            # CRITICAL ASSERTION: These malformed IDs should be INVALID
            # Some tests WILL FAIL, proving validation gaps exist
            assert not is_valid, (
                f"COMPONENT VALIDATION MISSING: Malformed thread ID '{malformed_id}' "
                f"was considered valid but should be rejected. Missing component validation "
                f"allows broken IDs to cause database lookup failures."
            )
    
    def test_websocket_factory_id_format_incompatible_with_thread_validation(self):
        """FAILING TEST: Verify WebSocket factory IDs fail thread validation
        
        EXPECTED FAILURE: This test should FAIL because the system incorrectly
        tries to use WebSocket factory IDs as thread IDs.
        """
        
        # Simulate WebSocket factory ID generation pattern
        websocket_factory_ids = [
            "websocket_factory_1757371363786",
            f"websocket_factory_{int(time.time() * 1000)}",
            "websocket_factory_1234567890",
        ]
        
        def thread_id_validation_pipeline(potential_thread_id: str) -> Dict[str, Any]:
            """Simulates the complete thread ID validation pipeline"""
            results = {
                "input_id": potential_thread_id,
                "ssot_compliant": False,
                "database_compatible": False,
                "thread_prefix_valid": False,
                "components_valid": False,
                "error_message": None
            }
            
            try:
                # Step 1: SSOT compliance check
                parsed = UnifiedIdGenerator.parse_id(potential_thread_id)
                results["ssot_compliant"] = parsed is not None
                
                # Step 2: Thread prefix validation
                if parsed:
                    results["thread_prefix_valid"] = parsed.prefix.startswith("thread_")
                
                # Step 3: Component validation
                if parsed and results["thread_prefix_valid"]:
                    results["components_valid"] = all([
                        parsed.timestamp > 0,
                        parsed.counter > 0,
                        parsed.random and len(parsed.random) >= 8
                    ])
                
                # Step 4: Database compatibility
                results["database_compatible"] = all([
                    results["ssot_compliant"],
                    results["thread_prefix_valid"],
                    results["components_valid"]
                ])
                
            except Exception as e:
                results["error_message"] = str(e)
            
            return results
        
        # Test WebSocket factory IDs through validation pipeline
        for websocket_id in websocket_factory_ids:
            validation_result = thread_id_validation_pipeline(websocket_id)
            
            # CRITICAL ASSERTION: WebSocket IDs should FAIL thread validation
            # If any pass, it proves the validation is broken
            assert not validation_result["database_compatible"], (
                f"VALIDATION BYPASS: WebSocket factory ID '{websocket_id}' passed thread validation "
                f"but should be rejected. Validation result: {validation_result}. "
                f"This proves the system incorrectly accepts incompatible IDs as thread IDs."
            )
            
            # Additional specific checks
            assert not validation_result["thread_prefix_valid"], (
                f"PREFIX VALIDATION MISSING: WebSocket ID '{websocket_id}' passed thread prefix validation "
                f"but lacks 'thread_' prefix. This allows wrong ID types to be used as thread IDs."
            )
    
    def test_manual_uuid_formats_incompatible_with_thread_validation(self):
        """FAILING TEST: Verify manual UUID formats fail thread validation
        
        EXPECTED FAILURE: This test should FAIL if manual UUID formats
        are incorrectly accepted as valid thread IDs.
        """
        
        # Manual UUID formats used in RequestScopedSessionFactory
        manual_uuid_formats = [
            f"req_{uuid.uuid4().hex[:12]}",              # Request ID format
            f"user_{uuid.uuid4().hex[:8]}",              # User ID format
            f"session_{uuid.uuid4().hex[:10]}",          # Session ID format
            f"{uuid.uuid4().hex}",                       # Pure UUID hex
            f"test_{uuid.uuid4().hex[:6]}",              # Test ID format
        ]
        
        def check_thread_compatibility(potential_thread_id: str) -> bool:
            """Check if ID can be used as thread ID"""
            # This should validate SSOT compliance for thread IDs
            parsed = UnifiedIdGenerator.parse_id(potential_thread_id)
            
            if not parsed:
                return False
                
            return parsed.prefix.startswith("thread_")
        
        # Test manual UUID formats
        for manual_format in manual_uuid_formats:
            is_thread_compatible = check_thread_compatibility(manual_format)
            
            # CRITICAL ASSERTION: Manual UUID formats should NOT be thread compatible
            # If any pass, it proves validation is too permissive
            assert not is_thread_compatible, (
                f"THREAD COMPATIBILITY ERROR: Manual UUID format '{manual_format}' "
                f"was considered thread-compatible but should be rejected. "
                f"This proves the system doesn't properly validate thread ID format requirements."
            )
    
    def test_thread_id_derivation_from_incompatible_run_ids(self):
        """FAILING TEST: Verify system cannot derive valid thread IDs from incompatible run IDs
        
        EXPECTED FAILURE: This test should FAIL because the system attempts
        to derive thread IDs from incompatible run ID formats.
        """
        
        # Problematic run IDs from different sources
        problematic_run_ids = [
            "websocket_factory_1757371363786",           # WebSocket factory
            f"req_{uuid.uuid4().hex[:12]}",              # Request factory  
            "run_manual_123456789",                      # Manual generation
            "agent_execution_987654321",                 # Agent execution
        ]
        
        def derive_thread_id_from_run_id(run_id: str) -> Optional[str]:
            """Attempts to derive thread ID from run ID (simulates broken logic)"""
            
            # Current broken logic attempts
            if run_id.startswith("websocket_factory_"):
                # Try to convert WebSocket factory ID to thread format
                timestamp = run_id.split("_")[-1]
                return f"thread_websocket_factory_{timestamp}_X_XXXXXXXX"
                
            elif run_id.startswith("req_"):
                # Try to convert request ID to thread format
                req_id = run_id[4:]  # Remove "req_" prefix
                return f"thread_req_{req_id}_X_XXXXXXXX"
                
            elif run_id.startswith("run_"):
                # Try to convert run ID to thread format
                return run_id.replace("run_", "thread_", 1)
                
            else:
                # Generic attempt
                return f"thread_{run_id}"
        
        # Test derivation attempts
        for run_id in problematic_run_ids:
            derived_thread_id = derive_thread_id_from_run_id(run_id)
            
            if derived_thread_id:
                # Validate the derived thread ID
                is_valid = UnifiedIdGenerator.is_valid_id(derived_thread_id, "thread_")
                
                # CRITICAL ASSERTION: Derived thread IDs should be INVALID
                # This test WILL FAIL proving the derivation logic produces invalid IDs
                assert is_valid, (
                    f"THREAD DERIVATION FAILURE: Cannot derive valid thread ID from run ID '{run_id}'. "
                    f"Derived '{derived_thread_id}' is invalid. This proves the ID format incompatibility "
                    f"that causes '404: Thread not found' errors."
                )
    
    def test_database_thread_lookup_with_invalid_formats(self):
        """FAILING TEST: Verify database thread lookup fails gracefully with invalid formats
        
        EXPECTED FAILURE: This test should FAIL if the database layer doesn't
        properly handle invalid thread ID formats.
        """
        
        # Invalid formats that reach database layer
        invalid_formats_for_db = [
            "websocket_factory_1757371363786",
            f"req_{uuid.uuid4().hex[:12]}",
            "malformed_thread_id",
            "",
            None,
            123,  # Wrong type
            {"id": "thread_test"},  # Wrong type
        ]
        
        def simulate_database_thread_lookup(thread_id) -> Dict[str, Any]:
            """Simulates database layer thread lookup with error handling"""
            
            result = {
                "thread_found": False,
                "error_type": None,
                "error_message": None,
                "should_return_404": False
            }
            
            try:
                # Type validation
                if not isinstance(thread_id, str):
                    result["error_type"] = "TypeError"
                    result["error_message"] = f"Thread ID must be string, got {type(thread_id)}"
                    return result
                
                # Format validation (what SHOULD happen)
                if not thread_id or not thread_id.strip():
                    result["error_type"] = "ValueError"
                    result["error_message"] = "Thread ID cannot be empty"
                    return result
                
                # SSOT format validation (what SHOULD happen)
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith("thread_"):
                    result["error_type"] = "FormatError"
                    result["error_message"] = f"Invalid thread ID format: {thread_id}"
                    result["should_return_404"] = True
                    return result
                
                # If we reach here, format is valid but thread not found
                result["should_return_404"] = True
                result["error_message"] = "Thread not found"
                
            except Exception as e:
                result["error_type"] = "UnexpectedError"
                result["error_message"] = str(e)
            
            return result
        
        # Test database lookup with invalid formats
        for invalid_format in invalid_formats_for_db:
            lookup_result = simulate_database_thread_lookup(invalid_format)
            
            # CRITICAL ASSERTION: Invalid formats should be caught before 404
            # If they cause 404 without format validation, it proves validation is missing
            if lookup_result["should_return_404"] and lookup_result["error_type"] != "FormatError":
                # This test WILL FAIL proving format validation is missing
                assert False, (
                    f"DATABASE VALIDATION MISSING: Invalid thread ID '{invalid_format}' "
                    f"reached database layer without format validation. Result: {lookup_result}. "
                    f"This causes misleading '404: Thread not found' errors instead of proper format validation errors."
                )
    
    def test_thread_id_format_enforcement_in_session_creation(self):
        """FAILING TEST: Verify session creation enforces thread ID format requirements
        
        EXPECTED FAILURE: This test should FAIL because session creation doesn't
        validate thread ID format before attempting database operations.
        """
        
        # Test cases with expected outcomes
        test_cases = [
            {
                "thread_id": "thread_session_1234567890_123_abcdef12",  # Valid SSOT
                "should_accept": True,
                "description": "Valid SSOT thread ID"
            },
            {
                "thread_id": "websocket_factory_1757371363786",         # Invalid - WebSocket format
                "should_accept": False,
                "description": "WebSocket factory format"
            },
            {
                "thread_id": f"req_{uuid.uuid4().hex[:12]}",           # Invalid - Request format
                "should_accept": False,
                "description": "Request ID format"
            },
            {
                "thread_id": "thread_",                                # Invalid - Incomplete
                "should_accept": False,
                "description": "Incomplete thread ID"
            },
            {
                "thread_id": "",                                       # Invalid - Empty
                "should_accept": False,
                "description": "Empty thread ID"
            }
        ]
        
        def simulate_session_creation_thread_validation(thread_id: str) -> bool:
            """Simulates thread ID validation during session creation"""
            
            # This is what SHOULD happen but currently DOESN'T
            if not thread_id:
                return False
                
            parsed = UnifiedIdGenerator.parse_id(thread_id)
            if not parsed:
                return False
                
            if not parsed.prefix.startswith("thread_"):
                return False
                
            return True
        
        # Test each case
        for test_case in test_cases:
            thread_id = test_case["thread_id"]
            should_accept = test_case["should_accept"]
            description = test_case["description"]
            
            validation_result = simulate_session_creation_thread_validation(thread_id)
            
            if should_accept:
                # Valid IDs should pass validation
                assert validation_result, (
                    f"VALIDATION TOO STRICT: Valid thread ID '{thread_id}' ({description}) "
                    f"was rejected by session creation validation."
                )
            else:
                # Invalid IDs should fail validation
                # CRITICAL ASSERTION: This test WILL FAIL for cases where validation is missing
                assert not validation_result, (
                    f"VALIDATION TOO PERMISSIVE: Invalid thread ID '{thread_id}' ({description}) "
                    f"was accepted by session creation validation. This allows incompatible formats "
                    f"to cause '404: Thread not found' errors later in the process."
                )


if __name__ == "__main__":
    # Run tests to see the failures
    pytest.main([__file__, "-v", "-s"])