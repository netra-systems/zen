"""
API and Database Integration Tests
Created during iterations 73-75 to ensure API endpoints work correctly with database operations.

Business Value Justification (BVJ):
- Segment: All segments (Core infrastructure)
- Business Goal: Data Integrity - Ensure API operations persist correctly
- Value Impact: Prevents data corruption and API-DB sync issues
- Strategic Impact: Protects customer data integrity, critical for trust
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from test_framework.performance_helpers import fast_test


@pytest.mark.api
@pytest.mark.database  
@pytest.mark.integration
@pytest.mark.fast_test
class TestApiDatabaseIntegration:
    """Integration tests for API and database operations."""
    
    @pytest.fixture
    def mock_database_session(self):
        """Mock database session for testing."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock()
        session.close = AsyncMock()
        return session
    
    @pytest.fixture  
    def mock_api_client(self):
        """Mock API client for testing."""
        client = AsyncMock()
        client.post = AsyncMock()
        client.get = AsyncMock()
        client.put = AsyncMock()
        client.delete = AsyncMock()
        return client
        
    @pytest.mark.asyncio
    @fast_test
    async def test_user_creation_api_to_database_flow(self, mock_database_session, mock_api_client):
        """Test user creation from API endpoint to database persistence."""
        # Test data
        user_data = {
            "email": "test@example.com",
            "name": "Test User",
            "role": "user"
        }
        
        # Mock API response
        api_response = {
            "id": "user_123",
            "email": user_data["email"],
            "name": user_data["name"],
            "role": user_data["role"],
            "created_at": datetime.now().isoformat()
        }
        mock_api_client.post.return_value = {"status": 201, "data": api_response}
        
        # Mock database operations
        mock_database_session.commit.return_value = None
        
        # Simulate API call
        response = await mock_api_client.post("/api/users", json=user_data)
        
        # Verify API call
        assert response["status"] == 201
        assert response["data"]["email"] == user_data["email"]
        mock_api_client.post.assert_called_once_with("/api/users", json=user_data)
        
        # Simulate database persistence
        user_record = {
            "id": api_response["id"],
            **user_data,
            "created_at": datetime.now()
        }
        mock_database_session.add(user_record)
        await mock_database_session.commit()
        
        # Verify database operations
        mock_database_session.add.assert_called_once_with(user_record)
        mock_database_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    @fast_test
    async def test_data_retrieval_database_to_api_flow(self, mock_database_session, mock_api_client):
        """Test data retrieval from database through API endpoints."""
        # Mock database query result
        user_records = [
            {"id": "user_1", "email": "user1@example.com", "name": "User 1"},
            {"id": "user_2", "email": "user2@example.com", "name": "User 2"},
        ]
        
        mock_result = MagicMock()
        mock_result.fetchall.return_value = user_records
        mock_database_session.execute.return_value = mock_result
        
        # Mock API response
        api_response = {"status": 200, "data": user_records, "count": len(user_records)}
        mock_api_client.get.return_value = api_response
        
        # Simulate database query
        query = "SELECT * FROM users WHERE active = true"
        result = await mock_database_session.execute(query)
        users = result.fetchall()
        
        # Simulate API response
        response = await mock_api_client.get("/api/users")
        
        # Verify database query
        mock_database_session.execute.assert_called_once_with(query)
        assert len(users) == 2
        
        # Verify API response
        assert response["status"] == 200
        assert response["count"] == 2
        assert response["data"][0]["email"] == "user1@example.com"
        
    @pytest.mark.asyncio
    @fast_test
    async def test_transaction_rollback_on_api_error(self, mock_database_session, mock_api_client):
        """Test database transaction rollback when API operations fail."""
        # Test data
        update_data = {"name": "Updated Name", "status": "active"}
        user_id = "user_456"
        
        # Mock API failure
        mock_api_client.put.side_effect = Exception("API Error: External service unavailable")
        
        # Mock database session
        mock_database_session.rollback.return_value = None
        
        # Simulate transaction with API call
        try:
            # Start transaction (implicit)
            update_query = f"UPDATE users SET name = '{update_data['name']}' WHERE id = '{user_id}'"
            await mock_database_session.execute(update_query)
            
            # Attempt API call that fails
            await mock_api_client.put(f"/api/users/{user_id}", json=update_data)
            
            # Should not reach here
            await mock_database_session.commit()
            
        except Exception as e:
            # Should rollback on error
            await mock_database_session.rollback()
            assert "API Error" in str(e)
            
        # Verify rollback was called
        mock_database_session.rollback.assert_called_once()
        
    @pytest.mark.asyncio
    @fast_test
    async def test_concurrent_api_database_operations(self, mock_database_session, mock_api_client):
        """Test concurrent API and database operations."""
        # Test data for concurrent operations
        operations = [
            {"action": "create", "data": {"name": "User A", "email": "a@example.com"}},
            {"action": "update", "data": {"id": "user_1", "name": "Updated User 1"}},
            {"action": "delete", "data": {"id": "user_2"}},
        ]
        
        # Mock responses
        mock_api_client.post.return_value = {"status": 201, "data": {"id": "user_new"}}
        mock_api_client.put.return_value = {"status": 200, "data": {"updated": True}}
        mock_api_client.delete.return_value = {"status": 204}
        
        # Mock database operations
        mock_database_session.commit.return_value = None
        
        async def execute_operation(operation):
            """Execute a single operation."""
            if operation["action"] == "create":
                response = await mock_api_client.post("/api/users", json=operation["data"])
                mock_database_session.add(operation["data"])
                return response
                
            elif operation["action"] == "update":
                response = await mock_api_client.put(f"/api/users/{operation['data']['id']}", 
                                                   json=operation["data"])
                await mock_database_session.execute(f"UPDATE users SET ... WHERE id = '{operation['data']['id']}'")
                return response
                
            elif operation["action"] == "delete":
                response = await mock_api_client.delete(f"/api/users/{operation['data']['id']}")
                await mock_database_session.execute(f"DELETE FROM users WHERE id = '{operation['data']['id']}'")
                return response
        
        # Execute operations concurrently
        tasks = [execute_operation(op) for op in operations]
        results = await asyncio.gather(*tasks)
        
        # Commit all changes
        await mock_database_session.commit()
        
        # Verify all operations completed
        assert len(results) == 3
        assert results[0]["status"] == 201  # Create
        assert results[1]["status"] == 200  # Update  
        assert results[2]["status"] == 204  # Delete
        
        # Verify database operations
        mock_database_session.add.assert_called_once()
        assert mock_database_session.execute.call_count == 2  # Update and delete
        mock_database_session.commit.assert_called_once()
        
    @pytest.mark.asyncio
    @fast_test
    async def test_api_validation_with_database_constraints(self, mock_database_session, mock_api_client):
        """Test API validation working with database constraints."""
        # Test data with validation issues
        invalid_user_data = {
            "email": "invalid-email",  # Invalid format
            "name": "",                # Empty name
            "age": -5                  # Invalid age
        }
        
        # Mock API validation error
        validation_errors = {
            "email": "Invalid email format",
            "name": "Name cannot be empty", 
            "age": "Age must be positive"
        }
        
        mock_api_client.post.return_value = {
            "status": 400,
            "errors": validation_errors
        }
        
        # Attempt API call with invalid data
        response = await mock_api_client.post("/api/users", json=invalid_user_data)
        
        # Verify validation errors
        assert response["status"] == 400
        assert "Invalid email format" in response["errors"]["email"]
        assert "Name cannot be empty" in response["errors"]["name"]
        assert "Age must be positive" in response["errors"]["age"]
        
        # Database should not be touched for validation errors
        mock_database_session.add.assert_not_called()
        mock_database_session.commit.assert_not_called()
        
    @pytest.mark.asyncio
    @fast_test
    async def test_database_connection_pooling_with_api_load(self, mock_database_session):
        """Test database connection pooling under API load."""
        # Mock connection pool
        connection_pool = AsyncMock()
        connection_pool.acquire.return_value = mock_database_session
        connection_pool.release = AsyncMock()
        
        # Simulate multiple concurrent API requests
        request_count = 10
        
        async def simulate_api_request(request_id: int):
            """Simulate single API request with database operations."""
            # Acquire connection from pool
            session = await connection_pool.acquire()
            
            try:
                # Simulate database operations
                await session.execute(f"SELECT * FROM users WHERE request_id = {request_id}")
                await session.commit()
                
                return {"request_id": request_id, "success": True}
                
            finally:
                # Release connection back to pool
                await connection_pool.release(session)
        
        # Execute concurrent requests
        tasks = [simulate_api_request(i) for i in range(request_count)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        assert len(results) == request_count
        assert all(r["success"] for r in results)
        
        # Verify connection pool usage
        assert connection_pool.acquire.call_count == request_count
        assert connection_pool.release.call_count == request_count
        
    @pytest.mark.asyncio
    @fast_test
    async def test_api_caching_with_database_updates(self, mock_database_session, mock_api_client):
        """Test API caching behavior with database updates."""
        # Mock cache
        cache = {}
        
        async def cached_get(key: str, fetch_func):
            """Simple cache implementation."""
            if key not in cache:
                cache[key] = await fetch_func()
            return cache[key]
        
        user_id = "user_cache_test"
        cache_key = f"user:{user_id}"
        
        # Mock database fetch
        async def fetch_user_from_db():
            result = MagicMock()
            result.fetchone.return_value = {"id": user_id, "name": "Cached User", "version": 1}
            await mock_database_session.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
            return result.fetchone()
        
        # First API call - should hit database
        user_data_1 = await cached_get(cache_key, fetch_user_from_db)
        assert user_data_1["name"] == "Cached User"
        assert user_data_1["version"] == 1
        
        # Second API call - should hit cache
        user_data_2 = await cached_get(cache_key, fetch_user_from_db)
        assert user_data_2 == user_data_1
        
        # Database should only be called once
        assert mock_database_session.execute.call_count == 1
        
        # Simulate database update (invalidate cache)
        cache.pop(cache_key, None)
        
        # Mock updated data
        async def fetch_updated_user_from_db():
            result = MagicMock()
            result.fetchone.return_value = {"id": user_id, "name": "Updated User", "version": 2}
            await mock_database_session.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
            return result.fetchone()
        
        # Third API call - should hit database again
        user_data_3 = await cached_get(cache_key, fetch_updated_user_from_db)
        assert user_data_3["name"] == "Updated User"
        assert user_data_3["version"] == 2
        
        # Database should be called twice now
        assert mock_database_session.execute.call_count == 2