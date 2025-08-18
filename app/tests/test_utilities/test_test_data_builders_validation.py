"""
Test validation for the test data builders module.

Validates that all builders work correctly and follow patterns.
Each test function is ≤8 lines as required.
"""

import pytest
from .test_data_builders import (
    UserDataBuilder, ThreadDataBuilder, MessageDataBuilder,
    MetricsDataBuilder, EventDataBuilder, BatchDataGenerator,
    create_test_conversation, create_test_user_session,
    create_performance_test_data, mock_repository_responses
)


def test_user_data_builder_basic():
    """Test basic user data generation."""
    user = UserDataBuilder.create_basic_user()
    assert user["id"].startswith("user_")
    assert user["role"] == "user"
    assert "permissions" in user
    assert len(user["permissions"]) >= 2


def test_user_data_builder_admin():
    """Test admin user generation."""
    admin = UserDataBuilder.create_admin_user()
    assert admin["role"] == "admin"
    assert "admin" in admin["permissions"]


def test_thread_data_builder():
    """Test thread data generation."""
    thread = ThreadDataBuilder.create_basic_thread()
    assert thread["id"].startswith("thread_")
    assert thread["status"] == "active"
    assert "created_at" in thread


def test_message_data_builder():
    """Test message data generation."""
    message = MessageDataBuilder.create_user_message()
    assert message["id"].startswith("msg_")
    assert message["role"] == "user"
    assert len(message["content"]) > 0


def test_metrics_data_builder():
    """Test metrics data generation."""
    metrics = MetricsDataBuilder.create_performance_metrics(5)
    assert len(metrics) == 5
    assert all("cpu_usage" in m for m in metrics)


def test_event_data_builder():
    """Test event data generation."""
    event = EventDataBuilder.create_workload_event()
    assert "event_id" in event
    assert event["event_type"] in ["request", "response", "error"]


def test_batch_data_generator():
    """Test batch data generation."""
    users = BatchDataGenerator.generate_users(3)
    threads = BatchDataGenerator.generate_threads(2)
    assert len(users) == 3
    assert len(threads) == 2


def test_helper_functions():
    """Test helper function data generation."""
    conversation = create_test_conversation(4)
    session = create_test_user_session()
    perf_data = create_performance_test_data("small")
    mock_responses = mock_repository_responses()
    
    assert len(conversation["messages"]) == 4
    assert len(session["threads"]) == 3
    assert "users" in perf_data
    assert "success_response" in mock_responses