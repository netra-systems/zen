"""
E2E Thread Routing Test Suite

This module contains comprehensive E2E tests for thread routing functionality,
validating multi-user isolation, agent event delivery, and thread switching consistency.

Test Files:
- test_multi_user_thread_isolation_e2e.py: Multi-user thread isolation with concurrent access
- test_agent_websocket_thread_events_e2e.py: Agent WebSocket event routing with all 5 critical events
- test_thread_switching_consistency_e2e.py: Thread context preservation across switches

All tests follow CLAUDE.md requirements:
✅ Real authentication via e2e_auth_helper.py
✅ Full Docker stack + Real services
✅ Tests designed to initially FAIL (find system gaps)
✅ Business value focus on Chat platform functionality
"""