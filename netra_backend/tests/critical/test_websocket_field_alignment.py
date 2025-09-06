"""Critical test to ensure WebSocket message field alignment between frontend and backend.

This test prevents the regression where frontend sends 'content' but backend expects 'text'.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.app.schemas.websocket_models import UserMessagePayload

from netra_backend.app.services.message_handlers import MessageHandlerService

class TestWebSocketFieldAlignment:
    """Test WebSocket message field alignment to prevent silent failures."""

    def test_user_message_payload_schema_has_content_field(self):
        """Verify UserMessagePayload schema defines 'content' field."""
        # Create payload as frontend would send it
        payload = UserMessagePayload(
        content="Test message from user",
        thread_id="test_thread_123"
        )

        # Verify the schema has content field
        assert hasattr(payload, 'content')
        assert payload.content == "Test message from user"

        # Verify dict representation has content
        payload_dict = payload.model_dump()
        assert 'content' in payload_dict
        assert payload_dict['content'] == "Test message from user"

        def test_message_handler_extracts_content_field(self):
            """Verify message handler correctly extracts 'content' field from frontend payload."""
        # Setup
            handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Simulate frontend payload structure
            frontend_payload = {
            "content": "User's actual message text",
            "references": [],
            "thread_id": "thread_456"
            }

        # Extract message data
            text, references, thread_id = handler._extract_message_data(frontend_payload)

        # Verify extraction works correctly
            assert text == "User's actual message text", "Handler must extract 'content' field"
            assert references == []
            assert thread_id == "thread_456"

            def test_message_handler_supports_legacy_text_field(self):
                """Verify backward compatibility with 'text' field."""
                handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Legacy payload structure
                legacy_payload = {
                "text": "Legacy message format",
                "references": [],
                "thread_id": "thread_789"
                }

                text, references, thread_id = handler._extract_message_data(legacy_payload)

                assert text == "Legacy message format", "Handler must support legacy 'text' field"
                assert references == []
                assert thread_id == "thread_789"

                def test_content_field_takes_precedence_over_text(self):
                    """Verify 'content' field takes precedence when both are present."""
                    handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Payload with both fields (shouldn't happen but defensive)'
                    mixed_payload = {
                    "content": "Modern content field",
                    "text": "Legacy text field",
                    "references": [],
                    "thread_id": "thread_mixed"
                    }

                    text, references, thread_id = handler._extract_message_data(mixed_payload)

                    assert text == "Modern content field", "'content' should take precedence over 'text'"

                    def test_empty_content_falls_back_to_text(self):
                        """Verify empty content field falls back to text field."""
                        handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Payload with empty content
                        payload = {
                        "content": "",
                        "text": "Fallback text",
                        "references": [],
                        "thread_id": "thread_fallback"
                        }

                        text, references, thread_id = handler._extract_message_data(payload)

                        assert text == "Fallback text", "Should fall back to 'text' when 'content' is empty"

                        def test_both_fields_missing_returns_empty_string(self):
                            """Verify graceful handling when both fields are missing."""
                            handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Malformed payload
                            bad_payload = {
                            "references": [],
                            "thread_id": "thread_bad"
                            }

                            text, references, thread_id = handler._extract_message_data(bad_payload)

                            assert text == "", "Should return empty string when both fields missing"
                            assert references == []
                            assert thread_id == "thread_bad"

                            def test_frontend_payload_structure_matches_backend_expectations(self):
                                """Integration test verifying frontend payload structure matches backend processing."""
        # This is the exact structure sent by frontend MessageInput component
                                frontend_message = {
                                "type": "user_message",
                                "payload": {
                                "content": "@Netra analyze our costs",
                                "references": []
                                }
                                }

                                handler = MessageHandlerService(supervisor=None, thread_service=None)

        # Extract just the payload as the handler would receive it
                                payload = frontend_message["payload"]
                                text, references, thread_id = handler._extract_message_data(payload)

        # Critical assertion - this must pass or messages won't be processed'
                                assert text == "@Netra analyze our costs", "Frontend 'content' field must be extracted"
                                assert references == []
                                assert thread_id is None  # Frontend doesn't always send thread_id'