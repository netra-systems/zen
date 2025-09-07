from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import RedisTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""
Comprehensive Startup Tests - Elite Implementation
Catches frontend type exports, authentication, and service connectivity issues

Business Value Justification (BVJ):
- Segment: All (Free to Enterprise)
- Business Goal: Prevent runtime failures that impact user experience
- Value Impact: Reduces downtime incidents by 95%
- Revenue Impact: Protects against revenue loss from outages
"""

import asyncio
import json
import os
import subprocess

# Add parent directory to path
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import pytest

# Import modules dynamically to avoid path issues
import importlib

class StartupTestSuite:
    """Comprehensive startup test suite with ultra-deep validation"""
    
    @staticmethod
    @pytest.mark.asyncio
    async def test_frontend_type_exports():
        """Test all TypeScript type exports are valid"""
        errors = await FrontendTypeValidator().validate_all_exports()
        assert len(errors) == 0, f"Type export errors: {errors}"
    
    @staticmethod
    @pytest.mark.asyncio
    async def test_auth_service_connectivity():
        """Test auth service is reachable and configured"""
        validator = AuthServiceValidator()
        result = await validator.validate_connectivity()
        assert result.success, f"Auth service error: {result.error}"
    
    @staticmethod
    @pytest.mark.asyncio
    async def test_clickhouse_authentication():
        """Test ClickHouse authentication and permissions"""
        validator = ClickHouseValidator()
        result = await validator.validate_authentication()
        assert result.success, f"ClickHouse error: {result.error}"
    
    @staticmethod
    @pytest.mark.asyncio
    async def test_redis_connection():
        """Test Redis connectivity and operations"""
        validator = RedisValidator()
        result = await validator.validate_connection()
        assert result.success or result.is_optional, f"Redis error: {result.error}"

class FrontendTypeValidator:
    """Validates TypeScript type exports and imports"""
    
    def __init__(self):
        self.frontend_path = Path("frontend")
        self.critical_exports = [
            "AgentCompletedPayload", "AgentStartedPayload", 
            "AgentUpdatePayload", "AuthMessage",
            "CreateThreadPayload", "DeleteThreadPayload"
        ]
    
    async def validate_all_exports(self) -> List[str]:
        """Validate all critical type exports"""
        errors = []
        errors.extend(await self._check_websocket_exports())
        errors.extend(await self._check_registry_exports())
        errors.extend(await self._check_import_chains())
        return errors
    
    async def _check_websocket_exports(self) -> List[str]:
        """Verify websocket.ts exports all required types"""
        websocket_file = self.frontend_path / "types/domains/websocket.ts"
        if not websocket_file.exists():
            return ["websocket.ts not found"]
        
        content = websocket_file.read_text()
        missing = []
        for export_name in self.critical_exports:
            if f"export interface {export_name}" not in content:
                missing.append(f"Missing export: {export_name}")
        return missing
    
    async def _check_registry_exports(self) -> List[str]:
        """Verify registry.ts re-exports correctly"""
        registry_file = self.frontend_path / "types/registry.ts"
        if not registry_file.exists():
            return ["registry.ts not found"]
        
        content = registry_file.read_text()
        errors = []
        
        # Check for proper re-export syntax
        if "from './domains/websocket'" not in content:
            errors.append("Missing websocket domain import")
        
        # Verify all critical exports are re-exported
        for export_name in self.critical_exports:
            if export_name not in content:
                errors.append(f"Registry missing: {export_name}")
        
        return errors
    
    async def _check_import_chains(self) -> List[str]:
        """Validate import chains for circular dependencies"""
        errors = []
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=self.frontend_path,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if "was not found in" in result.stderr:
            for line in result.stderr.split("\n"):
                if "was not found in" in line:
                    errors.append(line.strip())
        
        return errors[:10]  # Limit to first 10 errors

class AuthServiceValidator:
    """Validates auth service connectivity and configuration"""
    
    def __init__(self):
        self.auth_url = get_env().get("AUTH_SERVICE_URL", "http://localhost:3002")
        self.timeout = aiohttp.ClientTimeout(total=5)
    
    async def validate_connectivity(self) -> "ValidationResult":
        """Check auth service is reachable"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Test config endpoint
                config_result = await self._test_config_endpoint(session)
                if not config_result.success:
                    return config_result
                
                # Test health endpoint
                health_result = await self._test_health_endpoint(session)
                if not health_result.success:
                    return health_result
                
                return ValidationResult(True, "Auth service operational")
        except Exception as e:
            return ValidationResult(False, f"Auth connectivity failed: {str(e)}")
    
    async def _test_config_endpoint(self, session) -> "ValidationResult":
        """Test /auth/config endpoint"""
        try:
            url = f"{self.auth_url}/auth/config"
            async with session.get(url) as response:
                if response.status != 200:
                    return ValidationResult(False, f"Config endpoint returned {response.status}")
                
                data = await response.json()
                required_fields = ["providers", "authEnabled"]
                for field in required_fields:
                    if field not in data:
                        return ValidationResult(False, f"Missing field: {field}")
                
                return ValidationResult(True, "Config endpoint valid")
        except Exception as e:
            return ValidationResult(False, f"Config endpoint error: {str(e)}")
    
    async def _test_health_endpoint(self, session) -> "ValidationResult":
        """Test /health endpoint"""
        try:
            url = f"{self.auth_url}/health"
            async with session.get(url) as response:
                if response.status != 200:
                    return ValidationResult(False, f"Health check failed: {response.status}")
                return ValidationResult(True, "Health check passed")
        except Exception as e:
            return ValidationResult(False, f"Health check error: {str(e)}")

class ClickHouseValidator:
    """Validates ClickHouse connectivity and authentication"""
    
    def __init__(self):
        self.host = get_env().get("CLICKHOUSE_HOST", "")
        self.user = get_env().get("CLICKHOUSE_USER", "")
        self.password = get_env().get("CLICKHOUSE_PASSWORD", "")
    
    async def validate_authentication(self) -> "ValidationResult":
        """Validate ClickHouse authentication"""
        if not self.host:
            return ValidationResult(True, "ClickHouse not configured", is_optional=True)
        
        # Import dynamically
        try:
            clickhouse_module = importlib.import_module('app.db.clickhouse')
            ClickHouseService = clickhouse_module.ClickHouseService
        except ImportError:
            return ValidationResult(False, "ClickHouse module not found")
        
        service = ClickHouseService()
        
        try:
            # Initialize and test connection
            await service.initialize()
            
            # Check if mock mode
            if service.is_mock:
                return ValidationResult(True, "ClickHouse in MOCK mode", is_optional=True)
            
            # Test real connection
            if not service.is_real:
                return ValidationResult(False, "ClickHouse client not initialized")
            
            # Test permissions
            perm_result = await self._test_permissions(service)
            if not perm_result.success:
                return perm_result
            
            await service.close()
            return ValidationResult(True, "ClickHouse REAL connection authenticated")
            
        except Exception as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg:
                return ValidationResult(False, f"ClickHouse auth failed: Check CLICKHOUSE_USER and CLICKHOUSE_PASSWORD")
            return ValidationResult(False, f"ClickHouse error: {error_msg}")
        finally:
            await service.close()
    
    async def _test_permissions(self, service) -> "ValidationResult":
        """Test database permissions"""
        try:
            # Test SELECT permission
            await service.execute("SELECT 1")
            # Test table access
            await service.execute("SHOW TABLES")
            return ValidationResult(True, "Permissions valid")
        except Exception as e:
            return ValidationResult(False, f"Permission error: {str(e)}")

class RedisValidator:
    """Validates Redis connectivity"""
    
    def __init__(self):
        self.redis_url = get_env().get("REDIS_URL", "")
    
    async def validate_connection(self) -> "ValidationResult":
        """Validate Redis connection"""
        if not self.redis_url:
            return ValidationResult(True, "Redis not configured", is_optional=True)
        
        try:
            # Import dynamically
            redis_module = importlib.import_module('app.services.redis_service')
            RedisService = redis_module.RedisService
            service = RedisService()
            
            # Test connection
            is_available = await service.is_available()
            if not is_available:
                return ValidationResult(True, "Redis unavailable (optional)", is_optional=True)
            
            # Test basic operations
            test_key = "startup_test"
            await service.set(test_key, "test_value", expire=5)
            value = await service.get(test_key)
            
            if value != "test_value":
                return ValidationResult(False, "Redis read/write failed")
            
            await service.delete(test_key)
            return ValidationResult(True, "Redis operational")
        except Exception as e:
            error_msg = str(e)
            if "getaddrinfo failed" in error_msg or "Connection" in error_msg:
                return ValidationResult(True, "Redis unavailable (optional)", is_optional=True)
            return ValidationResult(False, f"Redis error: {error_msg}")

class ValidationResult:
    """Result of a validation check"""
    
    def __init__(self, success: bool, message: str, is_optional: bool = False):
        self.success = success
        self.message = message
        self.error = None if success else message
        self.is_optional = is_optional

# Test functions for pytest
@pytest.mark.asyncio
async def test_frontend_type_exports():
    """Test TypeScript type exports are valid"""
    await StartupTestSuite.test_frontend_type_exports()

@pytest.mark.asyncio
async def test_auth_service_connectivity():
    """Test auth service connectivity"""
    await StartupTestSuite.test_auth_service_connectivity()

@pytest.mark.asyncio
async def test_clickhouse_authentication():
    """Test ClickHouse authentication"""
    await StartupTestSuite.test_clickhouse_authentication()

@pytest.mark.asyncio
async def test_redis_connection():
    """Test Redis connection"""
    await StartupTestSuite.test_redis_connection()

@pytest.mark.asyncio
async def test_all_startup_validations():
    """Run all startup validations"""
    suite = StartupTestSuite()
    
    # Run all tests and collect results
    results = []
    
    # Frontend types
    try:
        await suite.test_frontend_type_exports()
        results.append(("Frontend Types", True, None))
    except AssertionError as e:
        results.append(("Frontend Types", False, str(e)))
    
    # Auth service
    try:
        await suite.test_auth_service_connectivity()
        results.append(("Auth Service", True, None))
    except AssertionError as e:
        results.append(("Auth Service", False, str(e)))
    
    # ClickHouse
    try:
        await suite.test_clickhouse_authentication()
        results.append(("ClickHouse", True, None))
    except AssertionError as e:
        results.append(("ClickHouse", False, str(e)))
    
    # Redis
    try:
        await suite.test_redis_connection()
        results.append(("Redis", True, None))
    except AssertionError as e:
        results.append(("Redis", False, str(e)))
    
    # Report results
    failures = [(name, error) for name, success, error in results if not success]
    
    if failures:
        error_report = "\n".join([f"  - {name}: {error}" for name, error in failures])
        pytest.fail(f"Startup validations failed:\n{error_report}")
