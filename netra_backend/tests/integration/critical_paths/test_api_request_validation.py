"""
L3 Integration Test: API Request Validation
Tests API request validation and sanitization
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json

import httpx
import pytest

from netra_backend.app.config import get_config

# Get settings instance
settings = get_config()

class TestAPIRequestValidationL3:
    """Test API request validation scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    @pytest.mark.asyncio
    async def test_required_fields_validation(self):
        """Test validation of required fields"""
        async with httpx.AsyncClient() as client:
            # Missing required field
            incomplete_data = {
            "type": "document"
                # Missing 'name' field
            }

            response = await client.post(
            f"{settings.API_BASE_URL}/api/resources",
            json=incomplete_data,
            headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 400
            error = response.json()
            assert "error" in error
            assert "name" in error["error"].lower() or "required" in error["error"].lower()

            @pytest.mark.asyncio
            @pytest.mark.integration
            @pytest.mark.l3
            @pytest.mark.asyncio
            async def test_data_type_validation(self):
                """Test data type validation"""
                async with httpx.AsyncClient() as client:
                    invalid_data = {
                    "name": "Test",
                    "type": "document",
                    "priority": "high"  # Should be integer
                    }

                    response = await client.post(
                    f"{settings.API_BASE_URL}/api/resources",
                    json=invalid_data,
                    headers={"Authorization": "Bearer test_token"}
                    )

                    if response.status_code == 400:
                        error = response.json()
                        assert "error" in error
                        assert "type" in error["error"].lower() or "priority" in error["error"].lower()

                        @pytest.mark.asyncio
                        @pytest.mark.integration
                        @pytest.mark.l3
                        @pytest.mark.asyncio
                        async def test_string_length_validation(self):
                            """Test string length constraints"""
                            async with httpx.AsyncClient() as client:
            # Excessively long string
                                long_data = {
                                "name": "x" * 1000,  # Too long
                                "type": "document"
                                }

                                response = await client.post(
                                f"{settings.API_BASE_URL}/api/resources",
                                json=long_data,
                                headers={"Authorization": "Bearer test_token"}
                                )

                                assert response.status_code == 400
                                error = response.json()
                                assert "error" in error
                                assert "length" in error["error"].lower() or "too long" in error["error"].lower()

                                @pytest.mark.asyncio
                                @pytest.mark.integration
                                @pytest.mark.l3
                                @pytest.mark.asyncio
                                async def test_enum_value_validation(self):
                                    """Test enum/choice field validation"""
                                    async with httpx.AsyncClient() as client:
                                        invalid_enum = {
                                        "name": "Test",
                                        "type": "invalid_type",  # Not in allowed values
                                        "status": "unknown"  # Not in allowed statuses
                                        }

                                        response = await client.post(
                                        f"{settings.API_BASE_URL}/api/resources",
                                        json=invalid_enum,
                                        headers={"Authorization": "Bearer test_token"}
                                        )

                                        assert response.status_code == 400
                                        error = response.json()
                                        assert "error" in error

                                        @pytest.mark.asyncio
                                        @pytest.mark.integration
                                        @pytest.mark.l3
                                        @pytest.mark.asyncio
                                        async def test_injection_attack_prevention(self):
                                            """Test prevention of injection attacks"""
                                            async with httpx.AsyncClient() as client:
            # SQL injection attempt
                                                malicious_data = {
                                                "name": "'; DROP TABLE users; --",
                                                "type": "document",
                                                "query": "1' OR '1'='1"
                                                }

                                                response = await client.post(
                                                f"{settings.API_BASE_URL}/api/resources",
                                                json=malicious_data,
                                                headers={"Authorization": "Bearer test_token"}
                                                )

            # Should either sanitize or reject
                                                if response.status_code == 201:
                                                    data = response.json()
                # Check if sanitized
                                                    assert "DROP TABLE" not in data["name"]
                                                else:
                                                    assert response.status_code in [400, 422]