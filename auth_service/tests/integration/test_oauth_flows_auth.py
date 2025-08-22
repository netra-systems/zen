"""Auth Tests - Split from test_oauth_flows.py"""

import json
import secrets
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from main import app

from auth_service.auth_core.models.auth_models import AuthProvider

# Test client
client = TestClient(app)


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def test_google_oauth_config(self):
        """Test Google OAuth configuration"""
        response = client.get("/auth/config")
        assert response.status_code == 200
        
        config = response.json()
        assert "google_client_id" in config
        assert "endpoints" in config
        assert config["endpoints"]["login"] is not None

    def test_oauth_endpoints_configuration(self):
        """Test OAuth endpoints are properly configured"""
        response = client.get("/auth/config") 
        assert response.status_code == 200
        
        config = response.json()
        endpoints = config["endpoints"]
        
        # Verify required endpoints exist
        required_endpoints = ["login", "logout", "callback", "token"]
        for endpoint in required_endpoints:
            assert endpoint in endpoints
            assert endpoints[endpoint] is not None
