import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from datetime import datetime
from datetime import timezone
import uuid

import pytest
from netra_backend.app.auth_integration.auth import ActiveUserWsDep
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from netra_backend.app.schemas import User

from netra_backend.app.config import get_config
import json

@pytest.fixture(scope = "function", autouse = True)
def settings_override():
    """Use real service instance."""
    # TODO: Initialize real service
    config = get_config()
    original_tables = list(config.clickhouse_logging.available_tables)
    original_default_table = config.clickhouse_logging.default_table
    original_default_tables = dict(config.clickhouse_logging.default_tables)
    yield
    config.clickhouse_logging.available_tables = original_tables
    config.clickhouse_logging.default_table = original_default_table
    config.clickhouse_logging.default_tables = original_default_tables

@pytest.fixture
def superuser_client():
    """Use real service instance."""
    # TODO: Initialize real service
    mock_user = User(
        id = str(uuid.uuid4()),
        email = "superuser@example.com",
        full_name = "Super User",
        is_active = True,
        is_superuser = True,
        role = "admin",
        created_at = datetime.now(timezone.utc),
    )
    app.dependency_overrides[ActiveUserWsDep] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[ActiveUserWsDep]

@pytest.fixture
def regular_user_client():
    """Use real service instance."""
    # TODO: Initialize real service
    mock_user = User(
        id = str(uuid.uuid4()),
        email = "user@example.com",
        full_name = "Regular User",
        is_active = True,
        is_superuser = False,
    )
    app.dependency_overrides[ActiveUserWsDep] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[ActiveUserWsDep]

def test_get_app_settings_as_superuser(superuser_client):
    response = superuser_client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["environment"] == "testing"

def test_get_app_settings_as_regular_user(regular_user_client):
    response = regular_user_client.get("/api/settings")
    assert response.status_code == 403

# --- Log Table Management ---

def test_set_log_table_success(superuser_client):
    config = get_config()
    table_name = config.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/settings/log_table", json = {"log_table": table_name})
    assert response.status_code == 200
    assert config.clickhouse_logging.default_table == table_name

def test_set_log_table_not_available(superuser_client):
    response = superuser_client.post("/api/settings/log_table", json = {"log_table": "non_existent_table"})
    assert response.status_code == 400

def test_add_log_table_success(superuser_client):
    config = get_config()
    new_table = "new_test_table"
    response = superuser_client.post("/api/settings/log_tables", json = {"log_table": new_table})
    assert response.status_code == 200
    assert new_table in config.clickhouse_logging.available_tables

def test_add_log_table_already_exists(superuser_client):
    config = get_config()
    existing_table = config.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/settings/log_tables", json = {"log_table": existing_table})
    assert response.status_code == 400

def test_remove_log_table_success(superuser_client):
    config = get_config()
    table_to_remove = "temp_table_to_remove"
    config.clickhouse_logging.available_tables.append(table_to_remove)
    response = superuser_client.delete(f"/api/settings/log_tables?log_table = {table_to_remove}")
    assert response.status_code == 200
    assert table_to_remove not in config.clickhouse_logging.available_tables

def test_remove_log_table_not_found(superuser_client):
    response = superuser_client.delete("/api/settings/log_tables", params = {"log_table": "not_a_real_table"})
    assert response.status_code == 400

def test_remove_default_log_table(superuser_client):
    config = get_config()
    default_table = config.clickhouse_logging.default_table
    response = superuser_client.delete(f"/api/settings/log_tables", params = {"log_table": default_table})
    assert response.status_code == 400

# --- Time Period Management ---

def test_set_time_period_success(superuser_client):
    config = get_config()
    days = config.clickhouse_logging.available_time_periods[0]
    response = superuser_client.post("/api/settings/time_period", json = {"days": days})
    assert response.status_code == 200
    assert config.clickhouse_logging.default_time_period_days == days

def test_set_time_period_not_available(superuser_client):
    response = superuser_client.post("/api/settings/time_period", json = {"days": 9999})
    assert response.status_code == 400

# --- Context-Specific Log Table Management ---

def test_set_default_log_table_for_context_success(superuser_client):
    config = get_config()
    context = "test_context"
    table_name = config.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/settings/default_log_table", json = {"context": context, "log_table": table_name})
    assert response.status_code == 200
    assert config.clickhouse_logging.default_tables[context] == table_name

def test_set_default_log_table_for_context_table_not_available(superuser_client):
    response = superuser_client.post("/api/settings/default_log_table", json = {"context": "test", "log_table": "not_a_table"})
    assert response.status_code == 400

def test_remove_default_log_table_for_context_success(superuser_client):
    config = get_config()
    context = "context_to_delete"
    table_name = config.clickhouse_logging.available_tables[0]
    config.clickhouse_logging.default_tables[context] = table_name
    response = superuser_client.delete(f"/api/settings/default_log_table", params = {"context": context, "log_table": table_name})
    assert response.status_code == 200
    assert context not in config.clickhouse_logging.default_tables

def test_remove_default_log_table_for_context_not_found(superuser_client):
    response = superuser_client.delete("/api/settings/default_log_table", params = {"context": "non_existent_context", "log_table": "test"})
    assert response.status_code == 400