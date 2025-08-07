import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid
import datetime

from app.main import app
from app.schemas import User
from app.auth.auth_dependencies import ActiveUserWsDep
from app.config import settings

@pytest.fixture
def superuser_client():
    mock_user = User(
        id=uuid.uuid4(),
        email="superuser@example.com",
        full_name="Super User",
        is_active=True,
        is_superuser=True,
    )
    app.dependency_overrides[ActiveUserWsDep] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[ActiveUserWsDep]

@pytest.fixture
def regular_user_client():
    mock_user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        full_name="Regular User",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[ActiveUserWsDep] = lambda: mock_user
    with TestClient(app) as client:
        yield client
    del app.dependency_overrides[ActiveUserWsDep]

def test_get_app_settings_as_superuser(superuser_client):
    response = superuser_client.get("/api/v3/settings")
    assert response.status_code == 200
    assert response.json()["environment"] == "development"

def test_get_app_settings_as_regular_user(regular_user_client):
    response = regular_user_client.get("/api/v3/settings")
    assert response.status_code == 403

# --- Log Table Management ---

def test_set_log_table_success(superuser_client):
    table_name = settings.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/v3/settings/log_table", json={"log_table": table_name})
    assert response.status_code == 200
    assert settings.clickhouse_logging.default_table == table_name

def test_set_log_table_not_available(superuser_client):
    response = superuser_client.post("/api/v3/settings/log_table", json={"log_table": "non_existent_table"})
    assert response.status_code == 400

def test_add_log_table_success(superuser_client):
    new_table = "new_test_table"
    response = superuser_client.post("/api/v3/settings/log_tables", json={"log_table": new_table})
    assert response.status_code == 200
    assert new_table in settings.clickhouse_logging.available_tables
    settings.clickhouse_logging.available_tables.remove(new_table) # cleanup

def test_add_log_table_already_exists(superuser_client):
    existing_table = settings.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/v3/settings/log_tables", json={"log_table": existing_table})
    assert response.status_code == 400

def test_remove_log_table_success(superuser_client):
    table_to_remove = "temp_table_to_remove"
    settings.clickhouse_logging.available_tables.append(table_to_remove)
    response = superuser_client.delete(f"/api/v3/settings/log_tables?log_table={table_to_remove}")
    assert response.status_code == 200
    assert table_to_remove not in settings.clickhouse_logging.available_tables

def test_remove_log_table_not_found(superuser_client):
    response = superuser_client.delete("/api/v3/settings/log_tables?log_table=not_a_real_table")
    assert response.status_code == 400

def test_remove_default_log_table(superuser_client):
    default_table = settings.clickhouse_logging.default_table
    response = superuser_client.delete(f"/api/v3/settings/log_tables?log_table={default_table}")
    assert response.status_code == 400

# --- Time Period Management ---

def test_set_time_period_success(superuser_client):
    days = settings.clickhouse_logging.available_time_periods[0]
    response = superuser_client.post("/api/v3/settings/time_period", json={"days": days})
    assert response.status_code == 200
    assert settings.clickhouse_logging.default_time_period_days == days

def test_set_time_period_not_available(superuser_client):
    response = superuser_client.post("/api/v3/settings/time_period", json={"days": 9999})
    assert response.status_code == 400

# --- Context-Specific Log Table Management ---

def test_set_default_log_table_for_context_success(superuser_client):
    context = "test_context"
    table_name = settings.clickhouse_logging.available_tables[0]
    response = superuser_client.post("/api/v3/settings/default_log_table", json={"context": context, "log_table": table_name})
    assert response.status_code == 200
    assert settings.clickhouse_logging.default_tables[context] == table_name
    del settings.clickhouse_logging.default_tables[context] # cleanup

def test_set_default_log_table_for_context_table_not_available(superuser_client):
    response = superuser_client.post("/api/v3/settings/default_log_table", json={"context": "test", "log_table": "not_a_table"})
    assert response.status_code == 400

def test_remove_default_log_table_for_context_success(superuser_client):
    context = "context_to_delete"
    table_name = settings.clickhouse_logging.available_tables[0]
    settings.clickhouse_logging.default_tables[context] = table_name
    response = superuser_client.delete(f"/api/v3/settings/default_log_table?context={context}&log_table={table_name}")
    assert response.status_code == 200
    assert context not in settings.clickhouse_logging.default_tables

def test_remove_default_log_table_for_context_not_found(superuser_client):
    response = superuser_client.delete("/api/v3/settings/default_log_table?context=non_existent_context&log_table=test")
    assert response.status_code == 400
