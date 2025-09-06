#!/usr/bin/env python3
"""
L3 Integration Test: API Basic Operations
Tests fundamental API operations including CRUD, filtering, sorting,
and error handling across different endpoints.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

import aiohttp
import pytest

from test_framework.test_patterns import L3IntegrationTest

@pytest.mark.skip(reason="L3 integration tests require backend service running - temporarily skipped for test runner stability")
class TestAPIBasicOperations(L3IntegrationTest):
    """Test API basic operations from multiple angles."""

    @pytest.mark.asyncio
    async def test_api_health_check(self):
        """Test API health check endpoint."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.backend_url}/api/health") as resp:
                assert resp.status == 200
                data = await resp.json()

                assert data["status"] == "healthy"
                assert "version" in data
                assert "timestamp" in data
                assert "services" in data

                @pytest.mark.asyncio
                async def test_api_version_endpoint(self):
                    """Test API version information endpoint."""
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.backend_url}/api/version") as resp:
                            assert resp.status == 200
                            data = await resp.json()

                            assert "api_version" in data
                            assert "build_number" in data
                            assert "git_commit" in data

                            @pytest.mark.asyncio
                            async def test_api_cors_headers(self):
                                """Test CORS headers on API responses."""
                                async with aiohttp.ClientSession() as session:
                                    headers = {"Origin": "https://example.com"}

                                    async with session.options(
                                    f"{self.backend_url}/api/health",
                                    headers=headers
                                    ) as resp:
                                        assert resp.status == 200
                                        assert "Access-Control-Allow-Origin" in resp.headers
                                        assert "Access-Control-Allow-Methods" in resp.headers
                                        assert "Access-Control-Allow-Headers" in resp.headers

                                        @pytest.mark.asyncio
                                        async def test_api_content_type_negotiation(self):
                                            """Test content type negotiation."""
                                            user_data = await self.create_test_user("api1@test.com")
                                            token = await self.get_auth_token(user_data)

                                            async with aiohttp.ClientSession() as session:
            # Request JSON
                                                headers = {
                                                "Authorization": f"Bearer {token}",
                                                "Accept": "application/json"
                                                }

                                                async with session.get(
                                                f"{self.backend_url}/api/users/me",
                                                headers=headers
                                                ) as resp:
                                                    assert resp.status == 200
                                                    assert "application/json" in resp.headers["Content-Type"]

                                                    @pytest.mark.asyncio
                                                    async def test_api_pagination_parameters(self):
                                                        """Test API pagination with different parameters."""
                                                        user_data = await self.create_test_user("api2@test.com")
                                                        token = await self.get_auth_token(user_data)

                                                        async with aiohttp.ClientSession() as session:
            # Create multiple items
                                                            for i in range(25):
                                                                thread_data = {"title": f"Thread {i:02d}"}

                                                                async with session.post(
                                                                f"{self.backend_url}/api/threads",
                                                                json=thread_data,
                                                                headers={"Authorization": f"Bearer {token}"}
                                                                ) as resp:
                                                                    assert resp.status == 201

            # Test different pagination parameters
                                                                    test_cases = [
                                                                    {"limit": 5, "offset": 0},
                                                                    {"limit": 10, "offset": 5},
                                                                    {"limit": 100, "offset": 0},  # Exceeds total
                                                                    {"limit": 10, "offset": 20}
                                                                    ]

                                                                    for params in test_cases:
                                                                        async with session.get(
                                                                        f"{self.backend_url}/api/threads",
                                                                        params=params,
                                                                        headers={"Authorization": f"Bearer {token}"}
                                                                        ) as resp:
                                                                            assert resp.status == 200
                                                                            data = await resp.json()

                                                                            assert "threads" in data
                                                                            assert "total" in data
                                                                            assert "limit" in data
                                                                            assert "offset" in data

                    # Verify pagination logic
                                                                            expected_count = min(params["limit"], max(0, data["total"] - params["offset"]))
                                                                            assert len(data["threads"]) == expected_count

                                                                            @pytest.mark.asyncio
                                                                            async def test_api_sorting_parameters(self):
                                                                                """Test API sorting with different fields."""
                                                                                user_data = await self.create_test_user("api3@test.com")
                                                                                token = await self.get_auth_token(user_data)

                                                                                async with aiohttp.ClientSession() as session:
            # Create threads with different dates
                                                                                    thread_ids = []
                                                                                    for i in range(5):
                                                                                        thread_data = {
                                                                                        "title": f"Thread {chr(69-i)}",  # E, D, C, B, A
                                                                                        "priority": i
                                                                                        }

                                                                                        async with session.post(
                                                                                        f"{self.backend_url}/api/threads",
                                                                                        json=thread_data,
                                                                                        headers={"Authorization": f"Bearer {token}"}
                                                                                        ) as resp:
                                                                                            assert resp.status == 201
                                                                                            data = await resp.json()
                                                                                            thread_ids.append(data["id"])

                                                                                            await asyncio.sleep(0.1)  # Ensure different timestamps

            # Test sorting by title ascending
                                                                                            async with session.get(
                                                                                            f"{self.backend_url}/api/threads?sort=title&order=asc",
                                                                                            headers={"Authorization": f"Bearer {token}"}
                                                                                            ) as resp:
                                                                                                assert resp.status == 200
                                                                                                data = await resp.json()

                                                                                                titles = [t["title"] for t in data["threads"]]
                                                                                                assert titles == sorted(titles)

            # Test sorting by created_at descending
                                                                                                async with session.get(
                                                                                                f"{self.backend_url}/api/threads?sort=created_at&order=desc",
                                                                                                headers={"Authorization": f"Bearer {token}"}
                                                                                                ) as resp:
                                                                                                    assert resp.status == 200
                                                                                                    data = await resp.json()

                                                                                                    dates = [t["created_at"] for t in data["threads"]]
                                                                                                    assert dates == sorted(dates, reverse=True)

                                                                                                    @pytest.mark.asyncio
                                                                                                    async def test_api_filtering_operations(self):
                                                                                                        """Test API filtering with different operators."""
                                                                                                        user_data = await self.create_test_user("api4@test.com")
                                                                                                        token = await self.get_auth_token(user_data)

                                                                                                        async with aiohttp.ClientSession() as session:
            # Create threads with different properties
                                                                                                            threads_data = [
                                                                                                            {"title": "Python Guide", "status": "active", "priority": 5},
                                                                                                            {"title": "JavaScript Tutorial", "status": "archived", "priority": 3},
                                                                                                            {"title": "Python Advanced", "status": "active", "priority": 8},
                                                                                                            {"title": "Database Design", "status": "draft", "priority": 6}
                                                                                                            ]

                                                                                                            for thread_data in threads_data:
                                                                                                                async with session.post(
                                                                                                                f"{self.backend_url}/api/threads",
                                                                                                                json=thread_data,
                                                                                                                headers={"Authorization": f"Bearer {token}"}
                                                                                                                ) as resp:
                                                                                                                    assert resp.status == 201

            # Test filtering by status
                                                                                                                    async with session.get(
                                                                                                                    f"{self.backend_url}/api/threads?status=active",
                                                                                                                    headers={"Authorization": f"Bearer {token}"}
                                                                                                                    ) as resp:
                                                                                                                        assert resp.status == 200
                                                                                                                        data = await resp.json()

                                                                                                                        for thread in data["threads"]:
                                                                                                                            assert thread["status"] == "active"

            # Test filtering by priority range
                                                                                                                            async with session.get(
                                                                                                                            f"{self.backend_url}/api/threads?priority_min=5&priority_max=8",
                                                                                                                            headers={"Authorization": f"Bearer {token}"}
                                                                                                                            ) as resp:
                                                                                                                                assert resp.status == 200
                                                                                                                                data = await resp.json()

                                                                                                                                for thread in data["threads"]:
                                                                                                                                    assert 5 <= thread["priority"] <= 8

                                                                                                                                    @pytest.mark.asyncio
                                                                                                                                    async def test_api_field_selection(self):
                                                                                                                                        """Test API field selection/projection."""
                                                                                                                                        user_data = await self.create_test_user("api5@test.com")
                                                                                                                                        token = await self.get_auth_token(user_data)

                                                                                                                                        async with aiohttp.ClientSession() as session:
            # Create thread
                                                                                                                                            thread_data = {
                                                                                                                                            "title": "Full Thread",
                                                                                                                                            "description": "Detailed description",
                                                                                                                                            "metadata": {"key": "value"}
                                                                                                                                            }

                                                                                                                                            async with session.post(
                                                                                                                                            f"{self.backend_url}/api/threads",
                                                                                                                                            json=thread_data,
                                                                                                                                            headers={"Authorization": f"Bearer {token}"}
                                                                                                                                            ) as resp:
                                                                                                                                                assert resp.status == 201
                                                                                                                                                thread = await resp.json()
                                                                                                                                                thread_id = thread["id"]

            # Request specific fields
                                                                                                                                                async with session.get(
                                                                                                                                                f"{self.backend_url}/api/threads/{thread_id}?fields=id,title",
                                                                                                                                                headers={"Authorization": f"Bearer {token}"}
                                                                                                                                                ) as resp:
                                                                                                                                                    assert resp.status == 200
                                                                                                                                                    data = await resp.json()

                                                                                                                                                    assert "id" in data
                                                                                                                                                    assert "title" in data
                                                                                                                                                    assert "description" not in data
                                                                                                                                                    assert "metadata" not in data

                                                                                                                                                    @pytest.mark.asyncio
                                                                                                                                                    async def test_api_batch_operations(self):
                                                                                                                                                        """Test API batch operations."""
                                                                                                                                                        user_data = await self.create_test_user("api6@test.com")
                                                                                                                                                        token = await self.get_auth_token(user_data)

                                                                                                                                                        async with aiohttp.ClientSession() as session:
            # Batch create
                                                                                                                                                            batch_data = {
                                                                                                                                                            "operations": [
                                                                                                                                                            {"action": "create", "data": {"title": "Thread 1"}},
                                                                                                                                                            {"action": "create", "data": {"title": "Thread 2"}},
                                                                                                                                                            {"action": "create", "data": {"title": "Thread 3"}}
                                                                                                                                                            ]
                                                                                                                                                            }

                                                                                                                                                            async with session.post(
                                                                                                                                                            f"{self.backend_url}/api/threads/batch",
                                                                                                                                                            json=batch_data,
                                                                                                                                                            headers={"Authorization": f"Bearer {token}"}
                                                                                                                                                            ) as resp:
                                                                                                                                                                assert resp.status == 200
                                                                                                                                                                data = await resp.json()

                                                                                                                                                                assert "results" in data
                                                                                                                                                                assert len(data["results"]) == 3

                                                                                                                                                                for result in data["results"]:
                                                                                                                                                                    assert result["status"] == "success"
                                                                                                                                                                    assert "id" in result["data"]

                                                                                                                                                                    @pytest.mark.asyncio
                                                                                                                                                                    async def test_api_error_response_format(self):
                                                                                                                                                                        """Test standardized error response format."""
                                                                                                                                                                        async with aiohttp.ClientSession() as session:
            # Unauthorized request
                                                                                                                                                                            async with session.get(f"{self.backend_url}/api/users/me") as resp:
                                                                                                                                                                                assert resp.status == 401
                                                                                                                                                                                data = await resp.json()

                                                                                                                                                                                assert "error" in data
                                                                                                                                                                                assert "code" in data
                                                                                                                                                                                assert "message" in data
                                                                                                                                                                                assert data["code"] == "UNAUTHORIZED"

            # Not found
                                                                                                                                                                                async with session.get(
                                                                                                                                                                                f"{self.backend_url}/api/threads/nonexistent"
                                                                                                                                                                                ) as resp:
                                                                                                                                                                                    assert resp.status == 404
                                                                                                                                                                                    data = await resp.json()

                                                                                                                                                                                    assert "error" in data
                                                                                                                                                                                    assert "code" in data
                                                                                                                                                                                    assert data["code"] == "NOT_FOUND"

                                                                                                                                                                                    if __name__ == "__main__":
                                                                                                                                                                                        pytest.main([__file__, "-v"])