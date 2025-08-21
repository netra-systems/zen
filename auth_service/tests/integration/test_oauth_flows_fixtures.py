"""Fixtures Tests - Split from test_oauth_flows.py"""

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


def mock_google_tokens():
    """Mock Google OAuth token response"""
    return {
        "access_token": "google_access_token_123",
        "refresh_token": "google_refresh_token_123",
        "id_token": "google_id_token_123",
        "token_type": "Bearer",
        "expires_in": 3600
    }

def mock_github_tokens():
    """Mock GitHub OAuth token response"""
    return {
        "access_token": "github_access_token_123",
        "refresh_token": "github_refresh_token_123", 
        "token_type": "Bearer",
        "scope": "user:email"
    }

def mock_microsoft_tokens():
    """Mock Microsoft OAuth token response"""
    return {
        "access_token": "microsoft_access_token_123",
        "refresh_token": "microsoft_refresh_token_123",
        "id_token": "microsoft_id_token_123", 
        "token_type": "Bearer",
        "expires_in": 3600
    }

def oauth_state():
    """Generate secure OAuth state parameter"""
    return secrets.token_urlsafe(32)

def oauth_code():
    """Mock OAuth authorization code"""
    return "mock_auth_code_123"
