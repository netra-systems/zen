"""
First-time user provider connections and permissions integration tests.

BVJ (Business Value Justification):
1. Segment: Early → Mid (Integration and optimization capabilities)  
2. Business Goal: Protect $85K MRR by enabling AI provider integrations
3. Value Impact: Validates provider connection flows and optimization workflows
4. Strategic Impact: Foundation for advanced optimization features
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import uuid
from typing import Any, Dict
from unittest.mock import patch, AsyncMock, MagicMock

import httpx
import pytest
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.tests.integration.first_time_user_fixtures import (
    get_mock_optimization_request,
    get_mock_provider_configs,
    simulate_oauth_callback,
)

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_openai_provider_connection(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test OpenAI API key provider connection."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Add OpenAI credentials
    provider_configs = get_mock_provider_configs()
    response = await async_client.post(
        "/api/v1/providers/openai/connect",
        json=provider_configs["openai"],
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["provider"] == "openai"
    assert response.json()["status"] == "connected"
    
    # Test provider connection
    response = await async_client.post("/api/v1/providers/openai/test", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    test_result = response.json()
    assert test_result["connection_valid"] is True
    assert "models_available" in test_result

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
@pytest.mark.asyncio
async def test_anthropic_provider_connection(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test Anthropic API key provider connection."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Add Anthropic credentials
    provider_configs = get_mock_provider_configs()
    response = await async_client.post(
        "/api/v1/providers/anthropic/connect",
        json=provider_configs["anthropic"],
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["provider"] == "anthropic"
    assert response.json()["status"] == "connected"

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(25)
@pytest.mark.asyncio
async def test_provider_listing_and_management(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test listing and managing connected providers."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Connect multiple providers
    provider_configs = get_mock_provider_configs()
    await async_client.post("/api/v1/providers/openai/connect", 
                           json=provider_configs["openai"], headers=headers)
    await async_client.post("/api/v1/providers/anthropic/connect", 
                           json=provider_configs["anthropic"], headers=headers)
    
    # List connected providers
    response = await async_client.get("/api/v1/providers", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    providers = response.json()
    assert len(providers) >= 2
    assert any(p["name"] == "openai" for p in providers)
    assert any(p["name"] == "anthropic" for p in providers)

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
@pytest.mark.asyncio
async def test_provider_settings_update(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test updating provider configuration settings."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Connect OpenAI first
    provider_configs = get_mock_provider_configs()
    await async_client.post("/api/v1/providers/openai/connect", 
                           json=provider_configs["openai"], headers=headers)
    
    # Update provider settings
    settings_update = {
        "default_model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    response = await async_client.patch(
        "/api/v1/providers/openai/settings",
        json=settings_update,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
@pytest.mark.asyncio
async def test_provider_key_rotation(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test API key rotation for providers."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Connect provider
    provider_configs = get_mock_provider_configs()
    await async_client.post("/api/v1/providers/openai/connect", 
                           json=provider_configs["openai"], headers=headers)
    
    # Rotate API key
    response = await async_client.post(
        "/api/v1/providers/openai/rotate-key",
        json={"new_api_key": "sk-test-new-key-9876543210"},
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "API key rotated successfully"

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(15)
@pytest.mark.asyncio
async def test_provider_disconnection(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test provider disconnection workflow."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Connect and then disconnect
    provider_configs = get_mock_provider_configs()
    await async_client.post("/api/v1/providers/anthropic/connect", 
                           json=provider_configs["anthropic"], headers=headers)
    
    # Disconnect provider
    response = await async_client.delete("/api/v1/providers/anthropic/disconnect", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify disconnection
    response = await async_client.get("/api/v1/providers", headers=headers)
    providers = response.json()
    anthropic_providers = [p for p in providers if p["name"] == "anthropic"]
    assert len(anthropic_providers) == 0 or anthropic_providers[0]["status"] == "disconnected"

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(45)
@pytest.mark.asyncio
async def test_google_oauth_provider_flow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test Google OAuth provider integration."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Initiate Google OAuth flow
    response = await async_client.get("/api/v1/providers/google/oauth/authorize", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    oauth_data = response.json()
    assert "authorization_url" in oauth_data
    assert "state" in oauth_data
    assert "google.com/o/oauth2" in oauth_data["authorization_url"]
    
    # Simulate OAuth callback
    with patch("app.services.oauth_service.exchange_code_for_token") as mock_exchange:
        mock_exchange.return_value = {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600
        }
        
        response = await async_client.get(
            "/api/v1/providers/google/oauth/callback",
            params={"code": "test-auth-code", "state": oauth_data["state"]},
            headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["provider"] == "google"
        assert response.json()["status"] == "connected"

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_optimization_workflow_with_providers(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any],
    async_session: AsyncSession
):
    """Test end-to-end optimization workflow with connected providers."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Connect providers first
    provider_configs = get_mock_provider_configs()
    await async_client.post("/api/v1/providers/openai/connect", 
                           json=provider_configs["openai"], headers=headers)
    
    # Submit optimization request
    optimization_request = get_mock_optimization_request()
    response = await async_client.post(
        "/api/v1/optimizations/analyze",
        json=optimization_request,
        headers=headers
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    job_data = response.json()
    assert "job_id" in job_data
    job_id = job_data["job_id"]
    
    # Poll for completion
    max_polls = 15
    analysis_complete = False
    
    for _ in range(max_polls):
        response = await async_client.get(f"/api/v1/optimizations/status/{job_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        status_data = response.json()
        
        if status_data["status"] == "completed":
            analysis_complete = True
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Optimization failed: {status_data.get('error')}")
        
        await asyncio.sleep(2)
    
    assert analysis_complete

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(30)
@pytest.mark.asyncio
async def test_optimization_results_validation(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test optimization results contain required data."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Mock completed optimization
    job_id = "test_job_123"
    mock_results = {
        "recommendations": [
            {
                "action": "Switch to GPT-3.5 for simple queries",
                "expected_savings": 1000,
                "quality_impact": 0.02,
                "confidence_score": 0.85
            }
        ],
        "cost_analysis": {
            "current_cost": 5000,
            "projected_cost": 4000,
            "savings_amount": 1000
        },
        "quality_assessment": {
            "current_quality_score": 0.98,
            "projected_quality_score": 0.96
        },
        "follow_up_questions": ["What are your peak usage hours?"]
    }
    
    with patch("app.services.optimization_service.get_results") as mock_get:
        mock_get.return_value = mock_results
        
        response = await async_client.get(f"/api/v1/optimizations/results/{job_id}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        results = response.json()
        
        # Validate optimization recommendations
        assert "recommendations" in results
        assert len(results["recommendations"]) > 0
        
        for rec in results["recommendations"]:
            assert "action" in rec
            assert "expected_savings" in rec
            assert "confidence_score" in rec
            assert rec["confidence_score"] >= 0.6
        
        # Verify cost and quality analysis
        assert "cost_analysis" in results
        assert results["cost_analysis"]["savings_amount"] > 0
        assert "quality_assessment" in results
        assert results["quality_assessment"]["projected_quality_score"] >= 0.95

@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.timeout(20)
@pytest.mark.asyncio
async def test_optimization_follow_up_workflow(
    async_client: httpx.AsyncClient,
    authenticated_user: Dict[str, Any]
):
    """Test optimization follow-up question workflow."""
    access_token = authenticated_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    job_id = "test_job_123"
    
    # Submit follow-up response
    response = await async_client.post(
        f"/api/v1/optimizations/{job_id}/follow-up",
        json={
            "question": "What are your peak hours?",
            "additional_context": {"peak_hours": "9am-5pm PST"}
        },
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify optimization saved to history
    response = await async_client.get("/api/v1/optimizations/history", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    history = response.json()
    assert len(history) >= 1