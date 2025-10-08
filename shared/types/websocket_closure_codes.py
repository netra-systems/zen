"""
WebSocket closure code definitions and categorization.

Provides enums and helper functions for validating and categorizing WebSocket
closure codes according to RFC 6455 and common extensions.
"""

from enum import IntEnum
from typing import Optional


class WebSocketClosureCode(IntEnum):
    """
    Standard WebSocket closure codes from RFC 6455 and extensions.

    See: https://datatracker.ietf.org/doc/html/rfc6455#section-7.4.1
    """
    # Standard codes (1000-1015)
    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    # 1004 is reserved
    NO_STATUS_RECEIVED = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_FRAME_PAYLOAD_DATA = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_SERVER_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    BAD_GATEWAY = 1014
    TLS_HANDSHAKE_FAILURE = 1015

    # Custom application codes (4000-4999)
    # These are application-specific and can be defined as needed


class WebSocketClosureCategory(IntEnum):
    """
    Categories for WebSocket closure codes to classify failure types.
    """
    NORMAL = 0           # Expected closures (1000, 1001)
    CLIENT_ERROR = 1     # Client-side errors (1002-1003, 1007-1010)
    SERVER_ERROR = 2     # Server-side errors (1011-1014)
    INFRASTRUCTURE = 3   # Infrastructure/network errors (1006, 1015)
    UNKNOWN = 4          # Unrecognized codes


def categorize_closure_code(code: int) -> WebSocketClosureCategory:
    """
    Categorize a WebSocket closure code into a failure category.

    Args:
        code: The WebSocket closure code

    Returns:
        The category of the closure code
    """
    # Normal closures
    if code in (1000, 1001):
        return WebSocketClosureCategory.NORMAL

    # Infrastructure/network errors
    if code in (1006, 1015):
        return WebSocketClosureCategory.INFRASTRUCTURE

    # Server errors
    if code in (1011, 1012, 1013, 1014):
        return WebSocketClosureCategory.SERVER_ERROR

    # Client errors
    if code in (1002, 1003, 1007, 1008, 1009, 1010):
        return WebSocketClosureCategory.CLIENT_ERROR

    # Unknown/unrecognized codes
    return WebSocketClosureCategory.UNKNOWN


def is_infrastructure_error(code: int) -> bool:
    """
    Check if a closure code represents an infrastructure/network error.

    Infrastructure errors are typically transient and may be retryable.

    Args:
        code: The WebSocket closure code

    Returns:
        True if the code represents an infrastructure error
    """
    return categorize_closure_code(code) == WebSocketClosureCategory.INFRASTRUCTURE


def get_closure_description(code: int) -> str:
    """
    Get a human-readable description of a WebSocket closure code.

    Args:
        code: The WebSocket closure code

    Returns:
        A description of what the closure code means
    """
    descriptions = {
        1000: "Normal closure - connection completed successfully",
        1001: "Going away - endpoint is going away (e.g., server shutdown, browser navigation)",
        1002: "Protocol error - endpoint received a malformed message",
        1003: "Unsupported data - endpoint received data of unsupported type",
        1005: "No status received - no status code was provided (internal use only)",
        1006: "Abnormal closure - connection closed without close frame (network/infrastructure issue)",
        1007: "Invalid frame payload data - message contains invalid UTF-8 or violates payload requirements",
        1008: "Policy violation - endpoint received message that violates its policy",
        1009: "Message too big - endpoint received message that is too large to process",
        1010: "Mandatory extension - client expected server to negotiate an extension",
        1011: "Internal server error - server encountered unexpected condition",
        1012: "Service restart - server is restarting",
        1013: "Try again later - server is temporarily overloaded or under maintenance",
        1014: "Bad gateway - server acting as gateway received invalid response",
        1015: "TLS handshake failure - TLS handshake failed (internal use only)",
    }

    return descriptions.get(code, f"Unknown closure code: {code}")
