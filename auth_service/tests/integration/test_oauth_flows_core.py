"""Core Tests - Split from test_oauth_flows.py"""

import pytest
import httpx
from unittest.mock import patch, Mock, AsyncMock
import json
from typing import Dict, Any
import secrets
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from auth_core.models.auth_models import AuthProvider
import sys
from pathlib import Path
from main import app

    def test_state_parameter_generation(self):
        """Test secure state parameter generation"""
        state1 = secrets.token_urlsafe(32)
        state2 = secrets.token_urlsafe(32)
        
        assert len(state1) >= 32
        assert len(state2) >= 32
        assert state1 != state2

    def test_state_parameter_generation(self):
        """Test secure state parameter generation"""
        state1 = secrets.token_urlsafe(32)
        state2 = secrets.token_urlsafe(32)
        
        assert len(state1) >= 32
        assert len(state2) >= 32
        assert state1 != state2

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
