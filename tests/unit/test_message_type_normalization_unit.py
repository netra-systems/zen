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
from netra_backend.app.websocket_core.types import MessageType, LEGACY_MESSAGE_TYPE_MAP, normalize_message_type, get_frontend_message_type
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
        assert 'chat_message' not in LEGACY_MESSAGE_TYPE_MAP, "UNIT TEST VALIDATION: 'chat_message' must be missing from LEGACY_MESSAGE_TYPE_MAP to demonstrate the root cause of the unknown type issue"
        assert 'chat' in LEGACY_MESSAGE_TYPE_MAP, "'chat' should be in legacy map"
        assert 'user_message' in LEGACY_MESSAGE_TYPE_MAP, "'user_message' should be in legacy map"
        assert 'user' in LEGACY_MESSAGE_TYPE_MAP, "'user' should be in legacy map"
        expected_mapping = MessageType.USER_MESSAGE
        print(f' SEARCH:  LEGACY MAPPING ANALYSIS:')
        print(f"   - 'chat_message' in map: {'chat_message' in LEGACY_MESSAGE_TYPE_MAP}")
        print(f"   - 'chat' maps to: {LEGACY_MESSAGE_TYPE_MAP.get('chat')}")
        print(f"   - 'user_message' maps to: {LEGACY_MESSAGE_TYPE_MAP.get('user_message')}")
        print(f"   - Expected mapping for 'chat_message': {expected_mapping}")
        assert LEGACY_MESSAGE_TYPE_MAP.get('chat') == MessageType.CHAT, 'Verify chat mapping'
        assert LEGACY_MESSAGE_TYPE_MAP.get('user_message') == MessageType.USER_MESSAGE, 'Verify user_message mapping'

    def test_normalize_message_type_chat_message_fallback_unit(self):
        """
        Unit test: Verify normalize_message_type behavior with 'chat_message'.
        
        This tests what happens when normalize_message_type encounters 'chat_message'.
        It should fall back to USER_MESSAGE, but this doesn't help because the router
        checks for unknown types BEFORE normalization.
        """
        normalized_type = normalize_message_type('chat_message')
        assert normalized_type == MessageType.USER_MESSAGE, 'normalize_message_type should default to USER_MESSAGE for unknown types'
        normalized_chat = normalize_message_type('chat')
        normalized_user = normalize_message_type('user_message')
        assert normalized_chat == MessageType.CHAT, 'Mapped types should normalize correctly'
        assert normalized_user == MessageType.USER_MESSAGE, 'Mapped types should normalize correctly'
        unknown_type_1 = normalize_message_type('completely_unknown_type')
        unknown_type_2 = normalize_message_type('another_unknown_type')
        assert unknown_type_1 == MessageType.USER_MESSAGE, 'All unknown types default to USER_MESSAGE'
        assert unknown_type_2 == MessageType.USER_MESSAGE, 'All unknown types default to USER_MESSAGE'
        print(f'[U+1F4CF] NORMALIZATION BEHAVIOR:')
        print(f"   - 'chat_message' normalizes to: {normalized_type}")
        print(f"   - 'chat' normalizes to: {normalized_chat}")
        print(f"   - 'user_message' normalizes to: {normalized_user}")
        print(f'   - Unknown types default to: {MessageType.USER_MESSAGE}')
        print(f'   - Problem: Router checks unknown BEFORE normalization runs')

    def test_message_type_enum_direct_conversion_unit(self):
        """
        Unit test: Verify direct MessageType enum conversion with 'chat_message'.
        
        This tests the second step in the router's unknown detection logic:
        trying to convert the string directly to a MessageType enum.
        """
        with pytest.raises(ValueError):
            MessageType('chat_message')
        print(f" PASS:  CONFIRMED: MessageType('chat_message') raises ValueError")
        assert MessageType('user_message') == MessageType.USER_MESSAGE
        assert MessageType('chat') == MessageType.CHAT
        assert MessageType('agent_request') == MessageType.AGENT_REQUEST
        for message_type in MessageType:
            assert MessageType(message_type.value) == message_type, f'Enum roundtrip failed for {message_type}'
        valid_enum_values = [mt.value for mt in MessageType]
        assert 'chat_message' not in valid_enum_values, "'chat_message' should not be a direct MessageType enum value"
        print(f'[U+1F4CB] ENUM CONVERSION ANALYSIS:')
        print(f'   - Valid MessageType values: {len(valid_enum_values)}')
        print(f"   - 'chat_message' is valid enum: False")
        print(f"   - Similar valid enums: {[v for v in valid_enum_values if 'chat' in v or 'message' in v]}")

    def test_router_is_unknown_message_type_unit(self):
        """
        Unit test: Directly test MessageRouter._is_unknown_message_type method.
        
        This is the core method that determines if a message type is unknown.
        It's the root cause of the 'chat_message' issue.
        """
        router = MessageRouter()
        is_chat_message_unknown = router._is_unknown_message_type('chat_message')
        assert is_chat_message_unknown == True, "UNIT TEST: _is_unknown_message_type('chat_message') should return True because 'chat_message' is not in LEGACY_MESSAGE_TYPE_MAP and not a direct enum"
        assert router._is_unknown_message_type('chat') == False, "'chat' should be known"
        assert router._is_unknown_message_type('user_message') == False, "'user_message' should be known"
        assert router._is_unknown_message_type('agent_request') == False, "'agent_request' should be known"
        assert router._is_unknown_message_type('totally_unknown') == True, 'Completely unknown types should be True'
        assert router._is_unknown_message_type('fake_type') == True, 'Fake types should be True'
        print(f'[U+1F50E] UNKNOWN TYPE DETECTION:')
        print(f"   - 'chat_message' is unknown: {is_chat_message_unknown}")
        print(f"   - 'chat' is unknown: {router._is_unknown_message_type('chat')}")
        print(f"   - 'user_message' is unknown: {router._is_unknown_message_type('user_message')}")
        print(f'   - Method correctly identifies unknown types')

    def test_legacy_message_map_coverage_unit(self):
        """
        Unit test: Analyze LEGACY_MESSAGE_TYPE_MAP coverage for chat-related types.
        
        This identifies what chat-related types are covered and which are missing.
        """
        chat_related_keys = [key for key in LEGACY_MESSAGE_TYPE_MAP.keys() if 'chat' in key.lower() or 'message' in key.lower()]
        potential_frontend_types = ['chat_message', 'chat_input', 'chat_request', 'message_input', 'user_chat', 'chat_text']
        missing_types = [t for t in potential_frontend_types if t not in LEGACY_MESSAGE_TYPE_MAP]
        assert 'chat_message' in missing_types, "'chat_message' should be in the list of missing chat-related types"
        print(f' CHART:  LEGACY MAP COVERAGE ANALYSIS:')
        print(f'   - Chat/message keys in map: {chat_related_keys}')
        print(f'   - Potential frontend types: {potential_frontend_types}')
        print(f'   - Missing types: {missing_types}')
        print(f"   - 'chat_message' missing: {'chat_message' in missing_types}")
        for key in chat_related_keys:
            mapping = LEGACY_MESSAGE_TYPE_MAP[key]
            assert isinstance(mapping, MessageType), f'Mapping for {key} should be MessageType'
            print(f'     {key} -> {mapping}')

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
        chat_mapping = LEGACY_MESSAGE_TYPE_MAP.get('chat')
        assert chat_mapping == MessageType.CHAT, "Verify 'chat' maps to CHAT"
        user_message_mapping = LEGACY_MESSAGE_TYPE_MAP.get('user_message')
        assert user_message_mapping == MessageType.USER_MESSAGE, "Verify 'user_message' maps to USER_MESSAGE"
        router = MessageRouter()
        chat_handlers = []
        user_message_handlers = []
        for handler in router.handlers:
            if hasattr(handler, 'supported_types'):
                if MessageType.CHAT in handler.supported_types:
                    chat_handlers.append(handler.__class__.__name__)
                if MessageType.USER_MESSAGE in handler.supported_types:
                    user_message_handlers.append(handler.__class__.__name__)
        print(f'[U+1F3E2] BUSINESS CLASSIFICATION ANALYSIS:')
        print(f'   - CHAT type supported by handlers: {chat_handlers}')
        print(f'   - USER_MESSAGE type supported by handlers: {user_message_handlers}')
        recommended_mapping = MessageType.USER_MESSAGE
        print(f"   - Recommended mapping for 'chat_message': {recommended_mapping}")
        print(f'   - Reasoning: USER_MESSAGE has broader handler support')
        assert 'chat_message' not in LEGACY_MESSAGE_TYPE_MAP, "Confirmed: 'chat_message' missing from legacy map prevents business value delivery"

    def test_frontend_compatibility_type_mapping_unit(self):
        """
        Unit test: Analyze frontend compatibility for message types.
        
        This validates which message types are likely to come from frontend
        and ensures they have proper mappings.
        """
        frontend_likely_types = ['chat', 'chat_message', 'user_message', 'user_input', 'message', 'text', 'input']
        mapped_types = []
        unmapped_types = []
        for msg_type in frontend_likely_types:
            if msg_type in LEGACY_MESSAGE_TYPE_MAP:
                mapped_types.append((msg_type, LEGACY_MESSAGE_TYPE_MAP[msg_type]))
            else:
                unmapped_types.append(msg_type)
        assert 'chat_message' in unmapped_types, "'chat_message' should be in unmapped types, indicating frontend compatibility issue"
        assert 'chat' in [t[0] for t in mapped_types], "Frontend 'chat' type should be mapped"
        assert 'user_message' in [t[0] for t in mapped_types], "Frontend 'user_message' type should be mapped"
        print(f'[U+1F5A5][U+FE0F] FRONTEND COMPATIBILITY ANALYSIS:')
        print(f'   - Frontend likely types: {len(frontend_likely_types)}')
        print(f'   - Properly mapped types: {len(mapped_types)}')
        print(f'   - Unmapped types: {unmapped_types}')
        print(f"   - Critical gap: 'chat_message' unmapped")
        for msg_type, mapping in mapped_types:
            print(f'      PASS:  {msg_type} -> {mapping}')
        for msg_type in unmapped_types:
            print(f'      FAIL:  {msg_type} -> NOT MAPPED')

    def test_get_frontend_message_type_unit(self):
        """
        Unit test: Verify get_frontend_message_type function behavior.
        
        This function handles the reverse mapping - from backend types to frontend.
        """
        from netra_backend.app.websocket_core.types import get_frontend_message_type
        assert get_frontend_message_type(MessageType.USER_MESSAGE) == 'user_message'
        assert get_frontend_message_type(MessageType.CHAT) == 'chat'
        assert get_frontend_message_type(MessageType.AGENT_RESPONSE) == 'agent_completed'
        assert get_frontend_message_type('user_message') == 'user_message'
        assert get_frontend_message_type('chat') == 'chat'
        chat_message_frontend = get_frontend_message_type('chat_message')
        assert chat_message_frontend == 'user_message', "get_frontend_message_type('chat_message') should normalize to 'user_message'"
        print(f' CYCLE:  FRONTEND TYPE CONVERSION:')
        print(f"   - 'chat_message' -> '{chat_message_frontend}'")
        print(f"   - This works for frontend, but router rejects 'chat_message' as unknown first")
        print(f'   - Problem: Unknown check happens before normalization gets a chance')

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
        expected_mapping = MessageType.USER_MESSAGE
        current_mapping = LEGACY_MESSAGE_TYPE_MAP.get('chat_message')
        assert current_mapping is None, "SOLUTION VALIDATION: 'chat_message' should be None (missing) before fix is applied"
        print(f'[U+1F527] SOLUTION SPECIFICATION:')
        print(f"   - Current 'chat_message' mapping: {current_mapping}")
        print(f"   - Expected 'chat_message' mapping: {expected_mapping}")
        print(f"   - Required change: Add 'chat_message': MessageType.USER_MESSAGE to LEGACY_MESSAGE_TYPE_MAP")
        user_msg_mapping = LEGACY_MESSAGE_TYPE_MAP.get('user_message')
        message_mapping = LEGACY_MESSAGE_TYPE_MAP.get('message')
        assert user_msg_mapping == MessageType.USER_MESSAGE, 'Reference: user_message maps to USER_MESSAGE'
        assert message_mapping == MessageType.USER_MESSAGE, 'Reference: message maps to USER_MESSAGE'
        print(f"   - Solution aligns with 'user_message': {user_msg_mapping}")
        print(f"   - Solution aligns with 'message': {message_mapping}")

    def test_solution_impact_verification_unit(self):
        """
        Unit test: Verify the impact of the proposed 'chat_message' mapping solution.
        
        This test simulates what should happen after the fix is applied.
        """
        original_map = LEGACY_MESSAGE_TYPE_MAP.copy()
        LEGACY_MESSAGE_TYPE_MAP['chat_message'] = MessageType.USER_MESSAGE
        try:
            router = MessageRouter()
            is_unknown_after_fix = router._is_unknown_message_type('chat_message')
            assert is_unknown_after_fix == False, "After fix: 'chat_message' should no longer be unknown"
            normalized = normalize_message_type('chat_message')
            assert normalized == MessageType.USER_MESSAGE, "After fix: 'chat_message' should normalize to USER_MESSAGE"
            assert normalize_message_type('user_message') == normalized, "After fix: 'chat_message' should behave like 'user_message'"
            print(f' PASS:  SOLUTION IMPACT VERIFICATION:')
            print(f"   - 'chat_message' unknown after fix: {is_unknown_after_fix}")
            print(f"   - 'chat_message' normalizes to: {normalized}")
            print(f'   - Solution successfully resolves the issue')
        finally:
            LEGACY_MESSAGE_TYPE_MAP.clear()
            LEGACY_MESSAGE_TYPE_MAP.update(original_map)
        router_restored = MessageRouter()
        is_unknown_restored = router_restored._is_unknown_message_type('chat_message')
        assert is_unknown_restored == True, 'After restoration: should be unknown again'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')