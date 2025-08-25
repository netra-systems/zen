"""Unified test configuration validation

Test file to validate that the unified test configuration
works correctly and integrates with the test harness.
"""

import os

import pytest

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


def test_environment_variables_set():
    """Test that environment variables are properly set"""
    assert os.environ.get("TESTING") == "1"
    assert os.environ.get("ENVIRONMENT") == "test"
    assert os.environ.get("JWT_SECRET_KEY") is not None
    assert os.environ.get("FERNET_KEY") is not None
    assert os.environ.get("ENCRYPTION_KEY") is not None


def test_test_users_created():
    """Test that test users are created for all tiers"""
    for tier in CustomerTier:
        user = TEST_USERS[tier.value]
        assert user.id is not None
        assert user.email.endswith("@unified-test.com")
        assert user.plan_tier == tier.value
        assert user.is_active is True


def test_test_endpoints_configured():
    """Test that test endpoints are properly configured"""
    assert TEST_ENDPOINTS.ws_url.startswith("ws://")
    assert TEST_ENDPOINTS.api_base.startswith("http://")
    assert TEST_ENDPOINTS.auth_base.startswith("http://")


def test_secrets_configured():
    """Test that secrets are properly configured"""
    assert len(TEST_SECRETS.jwt_secret) >= 32
    assert TEST_SECRETS.fernet_key is not None
    assert len(TEST_SECRETS.encryption_key) >= 16


def test_factory_functions():
    """Test that data factory functions work correctly"""
    # Test message data creation
    msg_data = TestDataFactory.create_message_data("test-user", "test message")
    assert "user_id" in msg_data
    assert "content" in msg_data
    assert "timestamp" in msg_data
    assert "message_id" in msg_data
    
    # Test auth headers
    headers = TestDataFactory.create_websocket_auth("test-token")
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")
    
    # Test plan data
    plan_data = TestDataFactory.create_plan_data("enterprise")
    assert plan_data["plan_tier"] == "enterprise"
    assert "plan_expires_at" in plan_data
    assert plan_data["auto_renew"] is True


def test_database_manager():
    """Test that database manager provides correct configuration"""
    db_url = TestDatabaseManager.get_memory_db_url()
    assert "sqlite" in db_url
    assert ":memory:" in db_url
    
    db_config = TestDatabaseManager.get_test_db_config()
    assert "url" in db_config
    assert db_config["echo"] is False
    
    session_config = TestDatabaseManager.create_test_session_config()
    assert "autocommit" in session_config
    assert session_config["autocommit"] is False


def test_helper_functions():
    """Test that helper functions work correctly"""
    # Test get_test_user function
    free_user = get_test_user("free")
    assert free_user is not None
    assert free_user.plan_tier == "free"
    
    # Test with explicit config
    config = create_unified_config()
    enterprise_user = get_test_user("enterprise", config)
    assert enterprise_user is not None
    assert enterprise_user.plan_tier == "enterprise"


def test_token_manager():
    """Test that token manager works correctly"""
    token_manager = TestTokenManager(TEST_SECRETS)
    
    # Test with free tier user
    free_user = TEST_USERS["free"]
    token = token_manager.create_user_token(free_user)
    assert token is not None
    assert len(token) > 10  # Should be a reasonable token length


def test_configuration_isolation():
    """Test that configuration is properly isolated for testing"""
    # Ensure we're in test mode
    assert os.environ.get("TESTING") == "1"
    assert os.environ.get("ENVIRONMENT") == "test"
    
    # Ensure database is in-memory for isolation
    db_url = os.environ.get("DATABASE_URL")
    assert ":memory:" in db_url
    
    # Ensure we're using test secrets, not production
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    assert "test" in jwt_secret.lower()


if __name__ == "__main__":
    pytest.main([__file__])