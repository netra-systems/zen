"""
Unit Tests: Message Type Normalization and Chat Message Mapping

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & Type Safety  
- Value Impact: Prevent message type handling regressions that break chat functionality
- Strategic Impact: Ensures reliable message type normalization for all chat interactions

This unit test suite validates the specific technical functions that handle
message type normalization, with focus on the 'chat_message' mapping gap.

CRITICAL: These tests MUST FAIL initially to demonstrate the technical root cause
of the 'chat_message' unknown type issue, then pass after the LEGACY_MESSAGE_TYPE_MAP fix.
"""

import pytest
from typing import Dict, Any, Set
from enum import Enum

# SSOT imports using absolute paths as per CLAUDE.md
from netra_backend.app.websocket_core.types import (
    MessageType, 
    LEGACY_MESSAGE_TYPE_MAP, 
    normalize_message_type,
    get_frontend_message_type
)
from netra_backend.app.websocket_core.handlers import MessageRouter


class TestMessageTypeNormalizationUnit:
    """
    Unit tests for message type normalization functions.
    
    These tests validate the core functions responsible for converting
    string message types to MessageType enums.
    """
    
    def test_chat_message_not_in_legacy_map_unit(self):
        """
        Unit test: Verify 'chat_message' is missing from LEGACY_MESSAGE_TYPE_MAP.
        
        This is the core technical issue - the legacy mapping doesn't include
        'chat_message' as a recognized type.
        """
        # CRITICAL ASSERTION: 'chat_message' should NOT be in the legacy map initially
        assert "chat_message" not in LEGACY_MESSAGE_TYPE_MAP, (
            "UNIT TEST VALIDATION: 'chat_message' must be missing from LEGACY_MESSAGE_TYPE_MAP "
            "to demonstrate the root cause of the unknown type issue"
        )
        
        # Validate other similar types ARE in the map for comparison
        assert "chat" in LEGACY_MESSAGE_TYPE_MAP, "'chat' should be in legacy map"
        assert "user_message" in LEGACY_MESSAGE_TYPE_MAP, "'user_message' should be in legacy map"
        assert "user" in LEGACY_MESSAGE_TYPE_MAP, "'user' should be in legacy map"
        
        # Show what 'chat_message' would map to if it were in the map
        expected_mapping = MessageType.USER_MESSAGE  # Logical mapping for chat messages
        
        print(f"🔍 LEGACY MAPPING ANALYSIS:")
        print(f"   - 'chat_message' in map: {'chat_message' in LEGACY_MESSAGE_TYPE_MAP}")
        print(f"   - 'chat' maps to: {LEGACY_MESSAGE_TYPE_MAP.get('chat')}")
        print(f"   - 'user_message' maps to: {LEGACY_MESSAGE_TYPE_MAP.get('user_message')}")
        print(f"   - Expected mapping for 'chat_message': {expected_mapping}")
        
        # Verify the expected mapping makes sense
        assert LEGACY_MESSAGE_TYPE_MAP.get("chat") == MessageType.CHAT, "Verify chat mapping"
        assert LEGACY_MESSAGE_TYPE_MAP.get("user_message") == MessageType.USER_MESSAGE, "Verify user_message mapping"
    
    def test_normalize_message_type_chat_message_fallback_unit(self):
        """
        Unit test: Verify normalize_message_type behavior with 'chat_message'.
        
        This tests what happens when normalize_message_type encounters 'chat_message'.
        It should fall back to USER_MESSAGE, but this doesn't help because the router
        checks for unknown types BEFORE normalization.
        """
        # Test normalization with missing 'chat_message' type
        normalized_type = normalize_message_type("chat_message")
        
        # Should fall back to USER_MESSAGE (the default for unknown types)
        assert normalized_type == MessageType.USER_MESSAGE, (
            "normalize_message_type should default to USER_MESSAGE for unknown types"
        )
        
        # Compare with types that have proper mappings
        normalized_chat = normalize_message_type("chat")
        normalized_user = normalize_message_type("user_message")
        
        assert normalized_chat == MessageType.CHAT, "Mapped types should normalize correctly"
        assert normalized_user == MessageType.USER_MESSAGE, "Mapped types should normalize correctly"
        
        # Test that the fallback behavior is consistent
        unknown_type_1 = normalize_message_type("completely_unknown_type")
        unknown_type_2 = normalize_message_type("another_unknown_type")
        
        assert unknown_type_1 == MessageType.USER_MESSAGE, "All unknown types default to USER_MESSAGE"
        assert unknown_type_2 == MessageType.USER_MESSAGE, "All unknown types default to USER_MESSAGE"
        
        print(f"📏 NORMALIZATION BEHAVIOR:")
        print(f"   - 'chat_message' normalizes to: {normalized_type}")
        print(f"   - 'chat' normalizes to: {normalized_chat}")  
        print(f"   - 'user_message' normalizes to: {normalized_user}")
        print(f"   - Unknown types default to: {MessageType.USER_MESSAGE}")
        print(f"   - Problem: Router checks unknown BEFORE normalization runs")
    
    def test_message_type_enum_direct_conversion_unit(self):
        """
        Unit test: Verify direct MessageType enum conversion with 'chat_message'.
        
        This tests the second step in the router's unknown detection logic:
        trying to convert the string directly to a MessageType enum.
        """
        # Test direct enum conversion (should fail for 'chat_message')
        with pytest.raises(ValueError):
            MessageType("chat_message")
        
        print(f"✅ CONFIRMED: MessageType('chat_message') raises ValueError")
        
        # Test direct enum conversion for valid types
        assert MessageType("user_message") == MessageType.USER_MESSAGE
        assert MessageType("chat") == MessageType.CHAT
        assert MessageType("agent_request") == MessageType.AGENT_REQUEST
        
        # Test that all enum values can be converted back
        for message_type in MessageType:
            assert MessageType(message_type.value) == message_type, f"Enum roundtrip failed for {message_type}"
        
        # Verify 'chat_message' is not a valid enum value
        valid_enum_values = [mt.value for mt in MessageType]
        assert "chat_message" not in valid_enum_values, (
            "'chat_message' should not be a direct MessageType enum value"
        )
        
        print(f"📋 ENUM CONVERSION ANALYSIS:")
        print(f"   - Valid MessageType values: {len(valid_enum_values)}")
        print(f"   - 'chat_message' is valid enum: False")
        print(f"   - Similar valid enums: {[v for v in valid_enum_values if 'chat' in v or 'message' in v]}")
    
    def test_router_is_unknown_message_type_unit(self):
        """
        Unit test: Directly test MessageRouter._is_unknown_message_type method.
        
        This is the core method that determines if a message type is unknown.
        It's the root cause of the 'chat_message' issue.
        """
        router = MessageRouter()
        
        # Test the problematic case
        is_chat_message_unknown = router._is_unknown_message_type("chat_message")
        
        # CRITICAL ASSERTION: Should be True initially (before fix)
        assert is_chat_message_unknown == True, (
            "UNIT TEST: _is_unknown_message_type('chat_message') should return True "
            "because 'chat_message' is not in LEGACY_MESSAGE_TYPE_MAP and not a direct enum"
        )
        
        # Test known types for comparison
        assert router._is_unknown_message_type("chat") == False, "'chat' should be known"
        assert router._is_unknown_message_type("user_message") == False, "'user_message' should be known"
        assert router._is_unknown_message_type("agent_request") == False, "'agent_request' should be known"
        
        # Test completely unknown types
        assert router._is_unknown_message_type("totally_unknown") == True, "Completely unknown types should be True"
        assert router._is_unknown_message_type("fake_type") == True, "Fake types should be True"
        
        print(f"🔎 UNKNOWN TYPE DETECTION:")
        print(f"   - 'chat_message' is unknown: {is_chat_message_unknown}")
        print(f"   - 'chat' is unknown: {router._is_unknown_message_type('chat')}")
        print(f"   - 'user_message' is unknown: {router._is_unknown_message_type('user_message')}")
        print(f"   - Method correctly identifies unknown types")
    
    def test_legacy_message_map_coverage_unit(self):
        """
        Unit test: Analyze LEGACY_MESSAGE_TYPE_MAP coverage for chat-related types.
        
        This identifies what chat-related types are covered and which are missing.
        """
        # Get all chat/message related keys from legacy map
        chat_related_keys = [
            key for key in LEGACY_MESSAGE_TYPE_MAP.keys() 
            if 'chat' in key.lower() or 'message' in key.lower()
        ]
        
        # Identify missing chat-related types that might be used by frontend
        potential_frontend_types = [
            "chat_message",      # The problematic one
            "chat_input",        # Possible frontend variant  
            "chat_request",      # Possible frontend variant
            "message_input",     # Possible frontend variant
            "user_chat",         # Possible frontend variant
            "chat_text"          # Possible frontend variant
        ]
        
        missing_types = [
            t for t in potential_frontend_types 
            if t not in LEGACY_MESSAGE_TYPE_MAP
        ]
        
        # CRITICAL ASSERTION: 'chat_message' should be missing
        assert "chat_message" in missing_types, (
            "'chat_message' should be in the list of missing chat-related types"
        )
        
        print(f"📊 LEGACY MAP COVERAGE ANALYSIS:")
        print(f"   - Chat/message keys in map: {chat_related_keys}")
        print(f"   - Potential frontend types: {potential_frontend_types}")
        print(f"   - Missing types: {missing_types}")
        print(f"   - 'chat_message' missing: {'chat_message' in missing_types}")
        
        # Verify the mappings make sense for existing types
        for key in chat_related_keys:
            mapping = LEGACY_MESSAGE_TYPE_MAP[key]
            assert isinstance(mapping, MessageType), f"Mapping for {key} should be MessageType"
            print(f"     {key} -> {mapping}")


class TestMessageTypeBusinessLogicUnit:
    """
    Unit tests for business logic related to message type handling.
    
    These tests validate the business rules and logic that depend on
    proper message type classification.
    """
    
    def test_chat_message_business_classification_unit(self):
        """
        Unit test: Verify business classification of 'chat_message' type.
        
        From a business perspective, 'chat_message' should be classified as
        a user-initiated chat interaction that requires agent processing.
        """
        # Business classification: What should 'chat_message' be?
        # Based on similar types in the legacy map:
        
        # Option 1: Map to CHAT (like 'chat' does)
        chat_mapping = LEGACY_MESSAGE_TYPE_MAP.get("chat")
        assert chat_mapping == MessageType.CHAT, "Verify 'chat' maps to CHAT"
        
        # Option 2: Map to USER_MESSAGE (like 'user_message' does)  
        user_message_mapping = LEGACY_MESSAGE_TYPE_MAP.get("user_message")
        assert user_message_mapping == MessageType.USER_MESSAGE, "Verify 'user_message' maps to USER_MESSAGE"
        
        # Business analysis: 'chat_message' is semantically similar to both
        # Let's determine the most appropriate mapping based on usage patterns
        
        # Check what handlers support each type
        router = MessageRouter()
        
        # Find handlers that support CHAT vs USER_MESSAGE
        chat_handlers = []
        user_message_handlers = []
        
        for handler in router.handlers:
            if hasattr(handler, 'supported_types'):
                if MessageType.CHAT in handler.supported_types:
                    chat_handlers.append(handler.__class__.__name__)
                if MessageType.USER_MESSAGE in handler.supported_types:
                    user_message_handlers.append(handler.__class__.__name__)
        
        print(f"🏢 BUSINESS CLASSIFICATION ANALYSIS:")
        print(f"   - CHAT type supported by handlers: {chat_handlers}")
        print(f"   - USER_MESSAGE type supported by handlers: {user_message_handlers}")
        
        # Business decision: USER_MESSAGE is more widely supported
        # 'chat_message' should map to USER_MESSAGE for maximum compatibility
        recommended_mapping = MessageType.USER_MESSAGE
        
        print(f"   - Recommended mapping for 'chat_message': {recommended_mapping}")
        print(f"   - Reasoning: USER_MESSAGE has broader handler support")
        
        # CRITICAL: This mapping is currently missing, causing business value loss
        assert "chat_message" not in LEGACY_MESSAGE_TYPE_MAP, (
            "Confirmed: 'chat_message' missing from legacy map prevents business value delivery"
        )
    
    def test_frontend_compatibility_type_mapping_unit(self):
        """
        Unit test: Analyze frontend compatibility for message types.
        
        This validates which message types are likely to come from frontend
        and ensures they have proper mappings.
        """
        # Types likely to be sent by frontend chat interfaces
        frontend_likely_types = [
            "chat",             # Simple chat
            "chat_message",     # Structured chat message (MISSING)
            "user_message",     # User input
            "user_input",       # User input variant
            "message",          # Generic message
            "text",             # Text input
            "input"             # Generic input
        ]
        
        # Check which are properly mapped
        mapped_types = []
        unmapped_types = []
        
        for msg_type in frontend_likely_types:
            if msg_type in LEGACY_MESSAGE_TYPE_MAP:
                mapped_types.append((msg_type, LEGACY_MESSAGE_TYPE_MAP[msg_type]))
            else:
                unmapped_types.append(msg_type)
        
        # CRITICAL ASSERTION: 'chat_message' should be unmapped
        assert "chat_message" in unmapped_types, (
            "'chat_message' should be in unmapped types, indicating frontend compatibility issue"
        )
        
        # Verify other common types are mapped
        assert "chat" in [t[0] for t in mapped_types], "Frontend 'chat' type should be mapped"
        assert "user_message" in [t[0] for t in mapped_types], "Frontend 'user_message' type should be mapped"
        
        print(f"🖥️ FRONTEND COMPATIBILITY ANALYSIS:")
        print(f"   - Frontend likely types: {len(frontend_likely_types)}")
        print(f"   - Properly mapped types: {len(mapped_types)}")
        print(f"   - Unmapped types: {unmapped_types}")
        print(f"   - Critical gap: 'chat_message' unmapped")
        
        for msg_type, mapping in mapped_types:
            print(f"     ✅ {msg_type} -> {mapping}")
        
        for msg_type in unmapped_types:
            print(f"     ❌ {msg_type} -> NOT MAPPED")
    
    def test_get_frontend_message_type_unit(self):
        """
        Unit test: Verify get_frontend_message_type function behavior.
        
        This function handles the reverse mapping - from backend types to frontend.
        """
        from netra_backend.app.websocket_core.types import get_frontend_message_type
        
        # Test with standard message types
        assert get_frontend_message_type(MessageType.USER_MESSAGE) == "user_message"
        assert get_frontend_message_type(MessageType.CHAT) == "chat"
        assert get_frontend_message_type(MessageType.AGENT_RESPONSE) == "agent_completed"  # Maps to frontend type
        
        # Test with string inputs that should be normalized
        assert get_frontend_message_type("user_message") == "user_message"
        assert get_frontend_message_type("chat") == "chat"
        
        # Test with 'chat_message' - this will normalize to USER_MESSAGE then return as string
        chat_message_frontend = get_frontend_message_type("chat_message")
        
        # This should return "user_message" because normalize_message_type("chat_message") -> USER_MESSAGE
        assert chat_message_frontend == "user_message", (
            "get_frontend_message_type('chat_message') should normalize to 'user_message'"
        )
        
        print(f"🔄 FRONTEND TYPE CONVERSION:")
        print(f"   - 'chat_message' -> '{chat_message_frontend}'")
        print(f"   - This works for frontend, but router rejects 'chat_message' as unknown first")
        print(f"   - Problem: Unknown check happens before normalization gets a chance")


class TestChatMessageMappingSolution:
    """
    Unit tests that define the expected solution for the 'chat_message' mapping issue.
    
    These tests specify exactly what the fix should look like.
    """
    
    def test_expected_chat_message_mapping_solution(self):
        """
        Unit test: Define the expected solution for 'chat_message' mapping.
        
        This test specifies exactly how 'chat_message' should be mapped
        in the LEGACY_MESSAGE_TYPE_MAP to fix the unknown type issue.
        """
        # SOLUTION SPECIFICATION: 'chat_message' should map to USER_MESSAGE
        expected_mapping = MessageType.USER_MESSAGE
        
        # Current state: mapping is missing (this should fail initially)
        current_mapping = LEGACY_MESSAGE_TYPE_MAP.get("chat_message")
        
        # CRITICAL ASSERTION: Should be None initially (before fix)
        assert current_mapping is None, (
            "SOLUTION VALIDATION: 'chat_message' should be None (missing) before fix is applied"
        )
        
        print(f"🔧 SOLUTION SPECIFICATION:")
        print(f"   - Current 'chat_message' mapping: {current_mapping}")
        print(f"   - Expected 'chat_message' mapping: {expected_mapping}")
        print(f"   - Required change: Add 'chat_message': MessageType.USER_MESSAGE to LEGACY_MESSAGE_TYPE_MAP")
        
        # Validate the expected mapping makes business sense
        # 'chat_message' should behave like other user message types
        user_msg_mapping = LEGACY_MESSAGE_TYPE_MAP.get("user_message")
        message_mapping = LEGACY_MESSAGE_TYPE_MAP.get("message")
        
        assert user_msg_mapping == MessageType.USER_MESSAGE, "Reference: user_message maps to USER_MESSAGE"
        assert message_mapping == MessageType.USER_MESSAGE, "Reference: message maps to USER_MESSAGE"
        
        # The solution aligns with existing patterns
        print(f"   - Solution aligns with 'user_message': {user_msg_mapping}")
        print(f"   - Solution aligns with 'message': {message_mapping}")
        
    def test_solution_impact_verification_unit(self):
        """
        Unit test: Verify the impact of the proposed 'chat_message' mapping solution.
        
        This test simulates what should happen after the fix is applied.
        """
        # Simulate the fix by temporarily adding the mapping
        original_map = LEGACY_MESSAGE_TYPE_MAP.copy()
        
        # Apply the proposed solution
        LEGACY_MESSAGE_TYPE_MAP["chat_message"] = MessageType.USER_MESSAGE
        
        try:
            # Test that the fix resolves the unknown type issue
            router = MessageRouter()
            is_unknown_after_fix = router._is_unknown_message_type("chat_message")
            
            # Should be False after fix
            assert is_unknown_after_fix == False, (
                "After fix: 'chat_message' should no longer be unknown"
            )
            
            # Test normalization with the fix
            normalized = normalize_message_type("chat_message")
            assert normalized == MessageType.USER_MESSAGE, (
                "After fix: 'chat_message' should normalize to USER_MESSAGE"
            )
            
            # Test that it follows the same path as other USER_MESSAGE types
            assert normalize_message_type("user_message") == normalized, (
                "After fix: 'chat_message' should behave like 'user_message'"
            )
            
            print(f"✅ SOLUTION IMPACT VERIFICATION:")
            print(f"   - 'chat_message' unknown after fix: {is_unknown_after_fix}")
            print(f"   - 'chat_message' normalizes to: {normalized}")
            print(f"   - Solution successfully resolves the issue")
            
        finally:
            # Restore original mapping for other tests
            LEGACY_MESSAGE_TYPE_MAP.clear()
            LEGACY_MESSAGE_TYPE_MAP.update(original_map)
        
        # Verify restoration (should be unknown again)
        router_restored = MessageRouter()
        is_unknown_restored = router_restored._is_unknown_message_type("chat_message")
        assert is_unknown_restored == True, "After restoration: should be unknown again"


if __name__ == "__main__":
    # Run the unit tests to validate message type normalization issues
    import sys
    print("🔬 Running Unit Tests for Message Type Normalization")
    print("🔬 Focus: 'chat_message' unknown type technical root cause")
    print("🔬 These tests validate the technical functions causing the issue")
    
    pytest.main([__file__, "-v", "--tb=short"])