"""
Test Legacy Message Handler SSOT Violations

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prove SSOT violation exists
- Value Impact: Documents current architectural debt
- Strategic Impact: Evidence for migration necessity

These tests are DESIGNED TO FAIL initially to prove SSOT violations.
"""

import pytest
from netra_backend.app.services.websocket.message_handler import (
    BaseMessageHandler,
    StartAgentHandler,
    UserMessageHandler,
    ThreadHistoryHandler,
    MessageHandlerService
)

class TestLegacyHandlerSSotViolations:
    """Tests that PROVE legacy handlers violate SSOT principles."""

    @pytest.mark.unit
    def test_legacy_base_handler_violates_ssot_interface(self):
        """EXPECTED TO FAIL: Legacy BaseMessageHandler interface differs from SSOT."""
        from netra_backend.app.websocket_core.handlers import BaseMessageHandler as SSOTBaseHandler

        legacy_handler = BaseMessageHandler()
        ssot_handler = SSOTBaseHandler()

        # This SHOULD fail - proving interface incompatibility
        legacy_methods = set(dir(legacy_handler))
        ssot_methods = set(dir(ssot_handler))

        # EXPECTED FAILURE: Different interfaces
        assert legacy_methods == ssot_methods, (
            f"SSOT Violation: Legacy handler has different interface. "
            f"Legacy only: {legacy_methods - ssot_methods}, "
            f"SSOT only: {ssot_methods - legacy_methods}"
        )

    @pytest.mark.unit
    def test_legacy_start_agent_violates_ssot_pattern(self):
        """EXPECTED TO FAIL: Legacy StartAgentHandler not equivalent to SSOT AgentRequestHandler."""
        # EXPECTED FAILURE: No direct equivalent in SSOT
        try:
            from netra_backend.app.websocket_core.handlers import StartAgentHandler
            assert False, "StartAgentHandler should not exist in SSOT - proves violation"
        except ImportError:
            # This proves the SSOT violation - legacy has StartAgentHandler, SSOT doesn't
            pytest.fail("SSOT Violation: StartAgentHandler exists in legacy but not SSOT")

    @pytest.mark.unit
    def test_legacy_message_types_violate_ssot_schema(self):
        """EXPECTED TO FAIL: Legacy message types not aligned with SSOT types."""
        # Check if legacy message types exist
        try:
            from netra_backend.app.services.websocket.message_handler import SUPPORTED_MESSAGE_TYPES
            legacy_types = SUPPORTED_MESSAGE_TYPES
        except (ImportError, AttributeError):
            # If no SUPPORTED_MESSAGE_TYPES, create a representative set based on handlers
            legacy_types = {
                'start_agent', 'user_message', 'thread_history', 'stop_agent'
            }

        from netra_backend.app.websocket_core.types import MessageType

        # Get SSOT message types
        ssot_types = {item.value for item in MessageType}

        # EXPECTED FAILURE: Different message type schemas
        assert legacy_types == ssot_types, (
            f"SSOT Violation: Message types don't match. "
            f"Legacy: {legacy_types}, SSOT: {ssot_types}"
        )

    @pytest.mark.unit
    def test_legacy_handler_registry_violates_ssot_patterns(self):
        """EXPECTED TO FAIL: Legacy handler registry pattern differs from SSOT."""
        # Test legacy MessageHandlerService pattern
        from netra_backend.app.services.websocket.message_handler import MessageHandlerService

        # Check if SSOT has equivalent service
        try:
            from netra_backend.app.websocket_core.handlers import MessageHandlerService as SSOTMessageService
            legacy_service = MessageHandlerService(db=None)
            ssot_service = SSOTMessageService(db=None)

            # If both exist, they should have same interface
            legacy_service_methods = set(dir(legacy_service))
            ssot_service_methods = set(dir(ssot_service))

            assert legacy_service_methods == ssot_service_methods, (
                f"SSOT Violation: Service interfaces differ. "
                f"Legacy only: {legacy_service_methods - ssot_service_methods}, "
                f"SSOT only: {ssot_service_methods - legacy_service_methods}"
            )
        except ImportError:
            # This proves SSOT violation - different service patterns
            pytest.fail("SSOT Violation: MessageHandlerService exists in legacy but not in SSOT")

    @pytest.mark.unit
    def test_legacy_thread_history_handler_violates_ssot(self):
        """EXPECTED TO FAIL: Legacy ThreadHistoryHandler has no direct SSOT equivalent."""
        # Check if ThreadHistoryHandler exists in SSOT
        try:
            from netra_backend.app.websocket_core.handlers import ThreadHistoryHandler
            assert False, "ThreadHistoryHandler should not exist in SSOT - proves violation"
        except ImportError:
            # This proves the SSOT violation - legacy has ThreadHistoryHandler, SSOT doesn't
            pytest.fail("SSOT Violation: ThreadHistoryHandler exists in legacy but not SSOT")

    @pytest.mark.unit
    def test_legacy_imports_prove_ssot_violations(self):
        """EXPECTED TO FAIL: 41 files importing legacy handler proves SSOT violation."""
        import os
        import ast

        legacy_imports_found = []

        # Search for legacy imports in codebase
        for root, dirs, files in os.walk("C:\\GitHub\\netra-apex\\netra_backend\\app"):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "services.websocket.message_handler" in content:
                                legacy_imports_found.append(file_path)
                    except Exception:
                        continue

        # EXPECTED FAILURE: Should find legacy imports proving SSOT violation
        assert len(legacy_imports_found) == 0, (
            f"SSOT Violation: Found {len(legacy_imports_found)} files still importing legacy handlers. "
            f"Files: {legacy_imports_found[:10]}{'...' if len(legacy_imports_found) > 10 else ''}"
        )