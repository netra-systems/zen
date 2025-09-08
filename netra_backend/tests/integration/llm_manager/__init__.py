"""
LLM Manager Integration Tests Package

This package contains comprehensive integration tests for LLM Manager Multi-User Context Isolation,
focusing on the second highest priority area for business value.

Test Modules:
- test_llm_manager_multi_user_isolation.py: Factory pattern and user isolation
- test_llm_conversation_context_isolation.py: Conversation security and context isolation  
- test_llm_provider_failover_integration.py: Provider failover during active sessions
- test_llm_resource_management_integration.py: Memory cleanup and resource management

Business Value:
These tests prevent catastrophic conversation mixing between users that would destroy 
trust and violate privacy - enabling 90% of current business value through secure chat.

Usage:
    # Run all LLM Manager integration tests
    python tests/unified_test_runner.py --category integration --test-path netra_backend/tests/integration/llm_manager/
    
    # Run with real services
    python tests/unified_test_runner.py --real-services --test-path netra_backend/tests/integration/llm_manager/
    
    # Run specific test file
    python tests/unified_test_runner.py --test-file netra_backend/tests/integration/llm_manager/test_llm_manager_multi_user_isolation.py
"""