"""
Journey Validation Helper Functions

Validation functions for OAuth and chat journey test steps.
Extracted from test_complete_oauth_chat_journey.py for modularity.
"""

from typing import Any, Dict


def validate_oauth_authentication(oauth_data: Dict[str, Any]) -> None:
    """Validate OAuth authentication step."""
    assert oauth_data["success"], f"OAuth authentication failed: {oauth_data.get('error')}"
    assert "oauth_state" in oauth_data, "OAuth state must be provided"
    assert "oauth_code" in oauth_data, "OAuth code must be provided"
    assert oauth_data["user_data"]["email"], "OAuth user email required"


def validate_auth_callback(callback_data: Dict[str, Any]) -> None:
    """Validate auth service callback processing."""
    assert callback_data["success"], f"Auth callback failed: {callback_data.get('error')}"
    assert callback_data["status_code"] == 302, "Auth callback must redirect"
    assert callback_data["access_token"], "Access token must be provided"


def validate_user_sync(sync_data: Dict[str, Any]) -> None:
    """Validate user sync between services."""
    assert sync_data["success"], f"User sync failed: {sync_data.get('error')}"
    assert sync_data["auth_service_status"] == 200, "Auth service user retrieval failed"
    assert sync_data["email_consistent"], "Email consistency check failed"


def validate_websocket_connection(websocket_data: Dict[str, Any]) -> None:
    """Validate WebSocket connection with OAuth token."""
    assert websocket_data["success"], f"WebSocket connection failed: {websocket_data.get('error')}"
    assert websocket_data["connected"], "WebSocket must be connected"
    assert websocket_data["ping_successful"], "WebSocket ping must succeed"


def validate_chat_interaction(chat_data: Dict[str, Any]) -> None:
    """Validate chat interaction and AI response."""
    assert chat_data["success"], f"Chat interaction failed: {chat_data.get('error')}"
    assert chat_data["response_received"], "Must receive chat response"
    assert len(chat_data["message_sent"]) > 10, "Chat message must be substantial"


def validate_conversation_persistence(persistence_data: Dict[str, Any]) -> None:
    """Validate conversation persistence in database."""
    assert persistence_data["success"], f"Conversation persistence failed: {persistence_data.get('error')}"
    assert persistence_data["history_status"] == 200, "Chat history retrieval failed"


def validate_returning_user_flow(returning_data: Dict[str, Any]) -> None:
    """Validate returning user OAuth flow."""
    assert returning_data["success"], f"Returning user flow failed: {returning_data.get('error')}"
    assert returning_data["no_duplicate_created"], "Must prevent duplicate user creation"
