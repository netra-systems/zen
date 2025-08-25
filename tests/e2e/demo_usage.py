#!/usr/bin/env python3
"""Demo usage of Unified Test Configuration

This demonstrates how to use the unified test configuration 
system for consistent testing across all customer tiers.
"""

from tests.e2e.config import (
    TEST_CONFIG,
    TEST_ENDPOINTS,
    TEST_SECRETS,
    TEST_USERS,
    TestDatabaseManager,
    TestDataFactory,
    CustomerTier,
    TestTokenManager,
    create_unified_config,
    get_test_user,
)


def demo_basic_config():
    """Demonstrate basic configuration usage"""
    print("=== Basic Configuration ===")
    print(f"WebSocket URL: {TEST_ENDPOINTS.ws_url}")
    print(f"API Base URL: {TEST_ENDPOINTS.api_base}")
    print(f"Auth Base URL: {TEST_ENDPOINTS.auth_base}")
    print(f"JWT Secret: {TEST_SECRETS.jwt_secret[:20]}...")
    print()


def demo_tier_users():
    """Demonstrate tier-based user testing"""
    print("=== Test Users by Tier ===")
    for tier in CustomerTier:
        user = TEST_USERS[tier.value]
        print(f"{tier.value.upper()}: {user.email}")
        print(f"  ID: {user.id}")
        print(f"  Plan: {user.plan_tier}")
        print(f"  Active: {user.is_active}")
    print()


def demo_test_data_factory():
    """Demonstrate test data factory usage"""
    print("=== Test Data Factory ===")
    
    # Create message data
    free_user = TEST_USERS["free"]
    message_data = TestDataFactory.create_message_data(
        free_user.id, "Hello from free user!"
    )
    print(f"Message Data: {message_data}")
    
    # Create auth headers
    auth_headers = TestDataFactory.create_websocket_auth("test-token-123")
    print(f"WebSocket Auth: {auth_headers}")
    
    # Create plan data
    plan_data = TestDataFactory.create_plan_data("enterprise")
    print(f"Plan Data: {plan_data}")
    print()


def demo_token_manager():
    """Demonstrate token manager usage"""
    print("=== Token Manager ===")
    token_manager = TestTokenManager(TEST_SECRETS)
    
    # Create tokens for different tiers
    for tier in ["free", "enterprise"]:
        user = TEST_USERS[tier]
        token = token_manager.create_user_token(user)
        print(f"{tier.upper()} token: {token[:30]}...")
    print()


def demo_database_config():
    """Demonstrate database configuration"""
    print("=== Database Configuration ===")
    db_url = TestDatabaseManager.get_memory_db_url()
    print(f"Memory DB URL: {db_url}")
    
    db_config = TestDatabaseManager.get_test_db_config()
    print(f"DB Config: {db_config}")
    
    session_config = TestDatabaseManager.create_test_session_config()
    print(f"Session Config: {session_config}")
    print()


def demo_helper_functions():
    """Demonstrate helper function usage"""
    print("=== Helper Functions ===")
    
    # Get specific user
    enterprise_user = get_test_user("enterprise")
    print(f"Enterprise User: {enterprise_user.email}")
    
    # Create custom config
    custom_config = create_unified_config()
    print(f"Custom Config WebSocket: {custom_config.endpoints.ws_url}")
    print()


def demo_typical_test_usage():
    """Demonstrate typical test usage pattern"""
    print("=== Typical Test Usage Pattern ===")
    
    # 1. Get test user for specific tier
    free_user = get_test_user("free")
    print(f"1. Selected test user: {free_user.email}")
    
    # 2. Create auth token
    token_manager = TestTokenManager(TEST_SECRETS)
    token = token_manager.create_user_token(free_user)
    print(f"2. Generated token: {token[:20]}...")
    
    # 3. Create test message
    message_data = TestDataFactory.create_message_data(
        free_user.id, "Test message for free tier"
    )
    print(f"3. Test message: {message_data['content']}")
    
    # 4. Create headers for API call
    api_headers = TestDataFactory.create_api_headers(token)
    print(f"4. API headers ready: {list(api_headers.keys())}")
    
    # 5. WebSocket URL ready
    print(f"5. WebSocket URL: {TEST_ENDPOINTS.ws_url}")
    
    print("Ready for unified testing!")
    print()


if __name__ == "__main__":
    print("Unified Test Configuration Demo")
    print("===============================\n")
    
    demo_basic_config()
    demo_tier_users()
    demo_test_data_factory()
    demo_token_manager()
    demo_database_config()
    demo_helper_functions()
    demo_typical_test_usage()
    
    print("Demo completed successfully!")
    print("\nTo use in your tests:")
    print("from tests.e2e.config import TEST_USERS, get_test_user, TestDataFactory")