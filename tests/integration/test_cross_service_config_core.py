"""Core Tests - Split from test_cross_service_config.py"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Generator
import httpx
from dev_launcher.service_discovery import ServiceDiscovery
from dev_launcher.health_monitor import HealthMonitor
from app.core.middleware_setup import CustomCORSMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient

        def __init__(self):
            self.backend_health = Mock()
            self.backend_health.status_code = 200
            self.backend_health.json.return_value = {"status": "healthy", "service": "backend"}
            
            self.frontend_health = Mock()
            self.frontend_health.status_code = 200
            self.frontend_health.json.return_value = {"status": "healthy", "service": "frontend"}
            
            self.auth_health = Mock()
            self.auth_health.status_code = 200
            self.auth_health.json.return_value = {"status": "healthy", "service": "auth"}
            
            self.auth_config = Mock()
            self.auth_config.status_code = 200
            self.auth_config.json.return_value = {
                "client_id": "test-client-id",
                "auth_url": "http://localhost:8081/auth/login",
                "token_url": "http://localhost:8081/auth/token"
            }
            
            self.token_validation = Mock()
            self.token_validation.status_code = 200
            self.token_validation.json.return_value = {
                "valid": True,
                "user_id": "test-user-123",
                "email": "test@example.com", 
                "permissions": ["read", "write"]
            }

        def __init__(self, responses):
            self.responses = responses
            self._closed = False

        def close(self):
            self._closed = True
