"""
Warning Upgrade Test Suite - Integration Tests

This module contains comprehensive integration tests for upgrading warnings to errors
in critical system components. These tests ensure that business value is protected
by properly failing when critical systems cannot function properly.

BUSINESS VALUE: Platform/Internal - System Stability & Multi-User Isolation
Ensures that critical failures are properly escalated to errors instead of silent warnings,
protecting chat functionality and multi-user isolation.

Test Categories:
1. WebSocket Event Failures (upgrade to ERROR) - Critical for chat functionality
2. Agent State Reset Failures (upgrade to ERROR) - Critical for multi-user isolation
3. Global Tool Dispatcher (upgrade to ERROR) - Critical for production safety
4. Agent Entry Conditions (enhanced WARNING) - Better diagnostics
5. LLM Processing Failures (enhanced WARNING) - Better diagnostics

CLAUDE.md Compliance:
- All tests use real services (no mocks in integration tests)
- All E2E tests use proper authentication
- Tests designed to fail hard (no cheating)
- SSOT patterns used throughout
"""