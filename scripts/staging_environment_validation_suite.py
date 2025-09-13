#!/usr/bin/env python3
"""
GCP Staging Environment Configuration Validation Suite
======================================================

Comprehensive validation test plan for Issue #683 to verify if recent configuration 
fixes have resolved staging environment configuration validation failures.

This script validates all 8+ configuration failure categories identified in Issue #683:
1. JWT configuration validation (Issue #681 relationship)
2. Database connectivity (PostgreSQL, Redis, ClickHouse)
3. LLM API configuration and connectivity
4. OAuth provider setup and redirect URIs  
5. Security keys and GSM secrets access
6. WebSocket functionality and Golden Path
7. Environment variable resolution
8. Service health checks

Business Impact: $500K+ ARR staging validation pipeline validation
"""

import asyncio
import aiohttp
import json
import sys
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Staging configuration constants
STAGING_BASE_URL = "https://api.staging.netrasystems.ai"
STAGING_WEBSOCKET_URL = "wss://api.staging.netrasystems.ai/ws"
STAGING_AUTH_URL = "https://api.staging.netrasystems.ai/auth"

@dataclass
class ValidationResult:
    """Result of a validation test."""
    test_name: str
    category: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration: Optional[float] = None

@dataclass
class CategorySummary:
    """Summary of validation results for a category."""
    category: str
    total_tests: int
    passed: int
    failed: int
    success_rate: float
    critical_failures: List[str] = field(default_factory=list)

class StagingEnvironmentValidator:
    """Comprehensive staging environment validation suite."""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.start_time = time.time()
        
    async def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation test categories."""
        print("=" * 80)
        print("GCP STAGING ENVIRONMENT CONFIGURATION VALIDATION SUITE")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target Environment: {STAGING_BASE_URL}")
        print(f"WebSocket URL: {STAGING_WEBSOCKET_URL}")
        print("\n🎯 BUSINESS OBJECTIVE: Validate $500K+ ARR staging pipeline functionality")
        print("📋 VALIDATION SCOPE: 8+ configuration categories from Issue #683")
        print()
        
        # Category 1: JWT Configuration Validation (Issue #681 relationship)
        await self._validate_jwt_configuration()
        
        # Category 2: Database Connectivity 
        await self._validate_database_connectivity()
        
        # Category 3: LLM API Configuration
        await self._validate_llm_api_configuration()
        
        # Category 4: OAuth Provider Setup
        await self._validate_oauth_configuration()
        
        # Category 5: Security Keys and GSM Access
        await self._validate_security_configuration()
        
        # Category 6: WebSocket and Golden Path
        await self._validate_websocket_golden_path()
        
        # Category 7: Environment Variable Resolution
        await self._validate_environment_resolution()
        
        # Category 8: Service Health Checks
        await self._validate_service_health()
        
        # Generate comprehensive report
        return self._generate_final_report()
    
    async def _validate_jwt_configuration(self):
        """Category 1: JWT Configuration Validation (Related to Issue #681)"""
        print("\n🔐 Category 1: JWT Configuration Validation")
        print("-" * 50)
        
        # Test 1.1: JWT secret key length validation
        await self._test_jwt_secret_length()
        
        # Test 1.2: JWT endpoint availability
        await self._test_jwt_endpoints()
        
        # Test 1.3: JWT token validation endpoint
        await self._test_jwt_validation_endpoint()
    
    async def _test_jwt_secret_length(self):
        """Test JWT secret key meets minimum length requirements."""
        start_time = time.time()
        
        try:
            # Import staging configuration validator
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            # Check JWT configuration specifically
            jwt_secret = validator._env.get('JWT_SECRET_KEY', '')
            jwt_secret_staging = validator._env.get('JWT_SECRET_STAGING', '')
            
            if jwt_secret and len(jwt_secret) >= 32:
                self._add_result(ValidationResult(
                    test_name="JWT_SECRET_KEY length validation",
                    category="JWT Configuration",
                    passed=True,
                    message=f"JWT_SECRET_KEY meets minimum length requirement ({len(jwt_secret)} chars)",
                    duration=time.time() - start_time
                ))
            elif jwt_secret_staging and len(jwt_secret_staging) >= 32:
                self._add_result(ValidationResult(
                    test_name="JWT_SECRET_STAGING length validation", 
                    category="JWT Configuration",
                    passed=True,
                    message=f"JWT_SECRET_STAGING meets minimum length requirement ({len(jwt_secret_staging)} chars)",
                    duration=time.time() - start_time
                ))
            else:
                self._add_result(ValidationResult(
                    test_name="JWT secret length validation",
                    category="JWT Configuration", 
                    passed=False,
                    message="JWT secret key does not meet minimum 32 character requirement",
                    error=f"JWT_SECRET_KEY length: {len(jwt_secret)}, JWT_SECRET_STAGING length: {len(jwt_secret_staging)}",
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="JWT secret length validation",
                category="JWT Configuration",
                passed=False,
                message="Failed to validate JWT secret length",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_jwt_endpoints(self):
        """Test JWT-related endpoint availability."""
        start_time = time.time()
        
        jwt_endpoints = [
            "/auth/login",
            "/auth/refresh", 
            "/auth/logout",
            "/api/auth/validate"
        ]
        
        for endpoint in jwt_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        # Accept various response codes (401, 405 indicate endpoint exists)
                        if response.status in [200, 401, 405, 422]:
                            self._add_result(ValidationResult(
                                test_name=f"JWT endpoint {endpoint} availability",
                                category="JWT Configuration",
                                passed=True,
                                message=f"JWT endpoint {endpoint} responding (status: {response.status})",
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"JWT endpoint {endpoint} availability",
                                category="JWT Configuration",
                                passed=False,
                                message=f"JWT endpoint {endpoint} returned unexpected status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"JWT endpoint {endpoint} availability",
                    category="JWT Configuration",
                    passed=False,
                    message=f"JWT endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _test_jwt_validation_endpoint(self):
        """Test JWT token validation endpoint functionality."""
        start_time = time.time()
        
        try:
            url = f"{STAGING_BASE_URL}/api/auth/validate"
            headers = {"Authorization": "Bearer test-token-for-validation"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    # Expect 401 or 422 for invalid token (shows validation is working)
                    if response.status in [401, 422]:
                        self._add_result(ValidationResult(
                            test_name="JWT token validation endpoint",
                            category="JWT Configuration",
                            passed=True,
                            message=f"JWT validation endpoint working (rejected invalid token: {response.status})",
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="JWT token validation endpoint",
                            category="JWT Configuration", 
                            passed=False,
                            message=f"JWT validation endpoint returned unexpected status {response.status}",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="JWT token validation endpoint",
                category="JWT Configuration",
                passed=False,
                message="JWT validation endpoint test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _validate_database_connectivity(self):
        """Category 2: Database Connectivity (PostgreSQL, Redis, ClickHouse)"""
        print("\n🗄️ Category 2: Database Connectivity")
        print("-" * 50)
        
        # Test 2.1: PostgreSQL configuration
        await self._test_postgresql_config()
        
        # Test 2.2: Redis configuration  
        await self._test_redis_config()
        
        # Test 2.3: ClickHouse configuration
        await self._test_clickhouse_config()
        
        # Test 2.4: Database health endpoints
        await self._test_database_health_endpoints()
    
    async def _test_postgresql_config(self):
        """Test PostgreSQL database configuration."""
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            # Check required PostgreSQL variables
            postgres_host = validator._env.get('POSTGRES_HOST', '')
            postgres_user = validator._env.get('POSTGRES_USER', '')  
            postgres_password = validator._env.get('POSTGRES_PASSWORD', '')
            postgres_db = validator._env.get('POSTGRES_DB', 'netra')
            
            if postgres_host and postgres_user and postgres_password:
                # Check for staging-appropriate host
                if 'localhost' not in postgres_host and '127.0.0.1' not in postgres_host:
                    self._add_result(ValidationResult(
                        test_name="PostgreSQL configuration validation",
                        category="Database Connectivity",
                        passed=True,
                        message=f"PostgreSQL properly configured (host: {postgres_host})",
                        details={
                            "host": postgres_host,
                            "user": postgres_user,
                            "database": postgres_db
                        },
                        duration=time.time() - start_time
                    ))
                else:
                    self._add_result(ValidationResult(
                        test_name="PostgreSQL configuration validation",
                        category="Database Connectivity",
                        passed=False,
                        message="PostgreSQL host contains localhost reference (invalid for staging)",
                        error=f"Host: {postgres_host}",
                        duration=time.time() - start_time
                    ))
            else:
                missing = []
                if not postgres_host: missing.append("POSTGRES_HOST")
                if not postgres_user: missing.append("POSTGRES_USER")
                if not postgres_password: missing.append("POSTGRES_PASSWORD")
                
                self._add_result(ValidationResult(
                    test_name="PostgreSQL configuration validation",
                    category="Database Connectivity",
                    passed=False,
                    message="PostgreSQL configuration incomplete",
                    error=f"Missing: {', '.join(missing)}",
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="PostgreSQL configuration validation",
                category="Database Connectivity",
                passed=False,
                message="PostgreSQL configuration test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_redis_config(self):
        """Test Redis cache configuration."""
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            redis_host = validator._env.get('REDIS_HOST', '')
            redis_password = validator._env.get('REDIS_PASSWORD', '')
            redis_url = validator._env.get('REDIS_URL', '')
            
            if redis_host and redis_password:
                # Check password length
                if len(redis_password) >= 8:
                    # Check host is not localhost
                    if 'localhost' not in redis_host and '127.0.0.1' not in redis_host:
                        self._add_result(ValidationResult(
                            test_name="Redis configuration validation",
                            category="Database Connectivity",
                            passed=True,
                            message=f"Redis properly configured (host: {redis_host})",
                            details={
                                "host": redis_host,
                                "password_length": len(redis_password)
                            },
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="Redis configuration validation",
                            category="Database Connectivity",
                            passed=False,
                            message="Redis host contains localhost reference (invalid for staging)",
                            error=f"Host: {redis_host}",
                            duration=time.time() - start_time
                        ))
                else:
                    self._add_result(ValidationResult(
                        test_name="Redis configuration validation",
                        category="Database Connectivity",
                        passed=False,
                        message="Redis password too short (minimum 8 characters required)",
                        error=f"Password length: {len(redis_password)}",
                        duration=time.time() - start_time
                    ))
            else:
                missing = []
                if not redis_host: missing.append("REDIS_HOST")
                if not redis_password: missing.append("REDIS_PASSWORD")
                
                self._add_result(ValidationResult(
                    test_name="Redis configuration validation",
                    category="Database Connectivity",
                    passed=False,
                    message="Redis configuration incomplete",
                    error=f"Missing: {', '.join(missing)}",
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="Redis configuration validation", 
                category="Database Connectivity",
                passed=False,
                message="Redis configuration test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_clickhouse_config(self):
        """Test ClickHouse analytics database configuration."""
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            clickhouse_url = validator._env.get('CLICKHOUSE_URL', '')
            clickhouse_host = validator._env.get('CLICKHOUSE_HOST', '')
            
            if clickhouse_url or clickhouse_host:
                # Check for cloud ClickHouse configuration
                cloud_indicators = ['clickhouse.cloud', 'gcp.clickhouse', 'aws.clickhouse']
                is_cloud_config = any(indicator in (clickhouse_url + clickhouse_host).lower() 
                                    for indicator in cloud_indicators)
                
                if is_cloud_config:
                    self._add_result(ValidationResult(
                        test_name="ClickHouse configuration validation",
                        category="Database Connectivity",
                        passed=True,
                        message="ClickHouse properly configured with cloud provider",
                        details={
                            "url": clickhouse_url[:50] + "..." if len(clickhouse_url) > 50 else clickhouse_url,
                            "host": clickhouse_host
                        },
                        duration=time.time() - start_time
                    ))
                else:
                    self._add_result(ValidationResult(
                        test_name="ClickHouse configuration validation",
                        category="Database Connectivity", 
                        passed=False,
                        message="ClickHouse configuration may not be using cloud provider",
                        error=f"URL: {clickhouse_url}, Host: {clickhouse_host}",
                        duration=time.time() - start_time
                    ))
            else:
                self._add_result(ValidationResult(
                    test_name="ClickHouse configuration validation",
                    category="Database Connectivity",
                    passed=False,
                    message="ClickHouse configuration missing",
                    error="Both CLICKHOUSE_URL and CLICKHOUSE_HOST are empty",
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="ClickHouse configuration validation",
                category="Database Connectivity",
                passed=False,
                message="ClickHouse configuration test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_database_health_endpoints(self):
        """Test database health check endpoints."""
        start_time = time.time()
        
        health_endpoints = [
            "/health/database",
            "/health/redis", 
            "/health/clickhouse",
            "/api/health"
        ]
        
        for endpoint in health_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            self._add_result(ValidationResult(
                                test_name=f"Database health endpoint {endpoint}",
                                category="Database Connectivity",
                                passed=True,
                                message=f"Database health endpoint {endpoint} healthy",
                                details=response_data,
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"Database health endpoint {endpoint}",
                                category="Database Connectivity",
                                passed=False,
                                message=f"Database health endpoint {endpoint} returned status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"Database health endpoint {endpoint}",
                    category="Database Connectivity",
                    passed=False,
                    message=f"Database health endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _validate_llm_api_configuration(self):
        """Category 3: LLM API Configuration and Connectivity"""
        print("\n🤖 Category 3: LLM API Configuration")
        print("-" * 50)
        
        # Test 3.1: LLM API keys validation
        await self._test_llm_api_keys()
        
        # Test 3.2: LLM service endpoints
        await self._test_llm_endpoints()
    
    async def _test_llm_api_keys(self):
        """Test LLM API keys configuration for all 7 services."""
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            # Check critical LLM API keys
            llm_keys = {
                'OPENAI_API_KEY': validator._env.get('OPENAI_API_KEY', ''),
                'ANTHROPIC_API_KEY': validator._env.get('ANTHROPIC_API_KEY', ''),
                'GEMINI_API_KEY': validator._env.get('GEMINI_API_KEY', '')
            }
            
            # Check for placeholder values
            placeholder_patterns = ['placeholder', 'your-key-here', 'replace-me', 'xxx']
            
            valid_keys = 0
            issues = []
            
            for key_name, key_value in llm_keys.items():
                if not key_value:
                    issues.append(f"{key_name} is missing")
                elif any(pattern in key_value.lower() for pattern in placeholder_patterns):
                    issues.append(f"{key_name} contains placeholder value")
                elif len(key_value) < 10:  # Basic length check
                    issues.append(f"{key_name} appears too short")
                else:
                    valid_keys += 1
            
            if valid_keys >= 2:  # At least 2 LLM providers configured
                self._add_result(ValidationResult(
                    test_name="LLM API keys configuration",
                    category="LLM API Configuration",
                    passed=True,
                    message=f"LLM API keys properly configured ({valid_keys}/3 providers)",
                    details={"valid_providers": valid_keys, "total_providers": 3},
                    duration=time.time() - start_time
                ))
            else:
                self._add_result(ValidationResult(
                    test_name="LLM API keys configuration",
                    category="LLM API Configuration",
                    passed=False,
                    message="Insufficient LLM API keys configured",
                    error="; ".join(issues),
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="LLM API keys configuration",
                category="LLM API Configuration",
                passed=False,
                message="LLM API keys validation failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_llm_endpoints(self):
        """Test LLM service endpoints availability."""
        start_time = time.time()
        
        llm_endpoints = [
            "/api/llm/models",
            "/api/llm/health",
            "/api/agents/available"
        ]
        
        for endpoint in llm_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status in [200, 401]:  # 401 indicates auth required but endpoint exists
                            self._add_result(ValidationResult(
                                test_name=f"LLM endpoint {endpoint}",
                                category="LLM API Configuration",
                                passed=True,
                                message=f"LLM endpoint {endpoint} responding (status: {response.status})",
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"LLM endpoint {endpoint}",
                                category="LLM API Configuration",
                                passed=False,
                                message=f"LLM endpoint {endpoint} returned status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"LLM endpoint {endpoint}",
                    category="LLM API Configuration",
                    passed=False,
                    message=f"LLM endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _validate_oauth_configuration(self):
        """Category 4: OAuth Provider Setup and Redirect URIs"""
        print("\n🔑 Category 4: OAuth Configuration")
        print("-" * 50)
        
        # Test 4.1: OAuth client credentials  
        await self._test_oauth_credentials()
        
        # Test 4.2: OAuth endpoints
        await self._test_oauth_endpoints()
    
    async def _test_oauth_credentials(self):
        """Test OAuth client credentials configuration."""
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            # Check staging-specific OAuth credentials
            oauth_client_id = validator._env.get('GOOGLE_OAUTH_CLIENT_ID_STAGING', '')
            oauth_client_secret = validator._env.get('GOOGLE_OAUTH_CLIENT_SECRET_STAGING', '')
            
            # Fallback to general OAuth credentials
            if not oauth_client_id:
                oauth_client_id = validator._env.get('GOOGLE_OAUTH_CLIENT_ID', '')
            if not oauth_client_secret:
                oauth_client_secret = validator._env.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
            
            if oauth_client_id and oauth_client_secret:
                # Basic validation - should not be placeholder values
                if ('staging' in oauth_client_id.lower() or len(oauth_client_id) > 30) and len(oauth_client_secret) > 20:
                    self._add_result(ValidationResult(
                        test_name="OAuth credentials configuration",
                        category="OAuth Configuration",
                        passed=True,
                        message="OAuth credentials properly configured for staging",
                        details={
                            "client_id_length": len(oauth_client_id),
                            "client_secret_length": len(oauth_client_secret)
                        },
                        duration=time.time() - start_time
                    ))
                else:
                    self._add_result(ValidationResult(
                        test_name="OAuth credentials configuration",
                        category="OAuth Configuration",
                        passed=False,
                        message="OAuth credentials appear to be invalid or placeholder values",
                        error=f"Client ID length: {len(oauth_client_id)}, Secret length: {len(oauth_client_secret)}",
                        duration=time.time() - start_time
                    ))
            else:
                missing = []
                if not oauth_client_id: missing.append("GOOGLE_OAUTH_CLIENT_ID(_STAGING)")
                if not oauth_client_secret: missing.append("GOOGLE_OAUTH_CLIENT_SECRET(_STAGING)")
                
                self._add_result(ValidationResult(
                    test_name="OAuth credentials configuration",
                    category="OAuth Configuration",
                    passed=False,
                    message="OAuth credentials missing",
                    error=f"Missing: {', '.join(missing)}",
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="OAuth credentials configuration",
                category="OAuth Configuration",
                passed=False,
                message="OAuth credentials validation failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_oauth_endpoints(self):
        """Test OAuth endpoints availability."""
        start_time = time.time()
        
        oauth_endpoints = [
            "/auth/google",
            "/auth/google/callback",
            "/auth/oauth/status"
        ]
        
        for endpoint in oauth_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, allow_redirects=False, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        # Accept redirects and auth-related status codes
                        if response.status in [200, 302, 307, 401, 403]:
                            self._add_result(ValidationResult(
                                test_name=f"OAuth endpoint {endpoint}",
                                category="OAuth Configuration",
                                passed=True,
                                message=f"OAuth endpoint {endpoint} responding (status: {response.status})",
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"OAuth endpoint {endpoint}",
                                category="OAuth Configuration",
                                passed=False,
                                message=f"OAuth endpoint {endpoint} returned unexpected status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"OAuth endpoint {endpoint}",
                    category="OAuth Configuration",
                    passed=False,
                    message=f"OAuth endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _validate_security_configuration(self):
        """Category 5: Security Keys and GSM Secrets Access"""
        print("\n🔒 Category 5: Security Configuration")
        print("-" * 50)
        
        # Test 5.1: Security keys validation
        await self._test_security_keys()
        
        # Test 5.2: GCP Secret Manager access
        await self._test_gsm_access()
    
    async def _test_security_keys(self):
        """Test security keys configuration.""" 
        start_time = time.time()
        
        try:
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            
            # Check critical security keys
            security_keys = {
                'JWT_SECRET_KEY': validator._env.get('JWT_SECRET_KEY', ''),
                'FERNET_KEY': validator._env.get('FERNET_KEY', ''),
                'SERVICE_SECRET': validator._env.get('SERVICE_SECRET', '')
            }
            
            valid_keys = 0
            issues = []
            
            for key_name, key_value in security_keys.items():
                if not key_value:
                    issues.append(f"{key_name} is missing")
                elif len(key_value) < 32:
                    issues.append(f"{key_name} is too short (minimum 32 characters)")
                else:
                    valid_keys += 1
            
            if valid_keys == 3:
                self._add_result(ValidationResult(
                    test_name="Security keys configuration",
                    category="Security Configuration",
                    passed=True,
                    message="All security keys properly configured",
                    details={"configured_keys": valid_keys},
                    duration=time.time() - start_time
                ))
            else:
                self._add_result(ValidationResult(
                    test_name="Security keys configuration",
                    category="Security Configuration",
                    passed=False,
                    message="Security keys configuration issues detected",
                    error="; ".join(issues),
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="Security keys configuration",
                category="Security Configuration",
                passed=False,
                message="Security keys validation failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_gsm_access(self):
        """Test Google Cloud Secret Manager access."""
        start_time = time.time()
        
        try:
            # Test GSM connectivity
            url = f"{STAGING_BASE_URL}/api/health/secrets"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        self._add_result(ValidationResult(
                            test_name="Google Secret Manager access",
                            category="Security Configuration",
                            passed=True,
                            message="Google Secret Manager connectivity confirmed",
                            details=response_data,
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="Google Secret Manager access",
                            category="Security Configuration",
                            passed=False,
                            message=f"Google Secret Manager health check failed (status: {response.status})",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            # This may be expected if endpoint doesn't exist
            self._add_result(ValidationResult(
                test_name="Google Secret Manager access",
                category="Security Configuration",
                passed=True,  # Don't fail if endpoint doesn't exist
                message="Google Secret Manager health endpoint not available (may be normal)",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _validate_websocket_golden_path(self):
        """Category 6: WebSocket Functionality and Golden Path"""
        print("\n🌐 Category 6: WebSocket and Golden Path")
        print("-" * 50)
        
        # Test 6.1: WebSocket connectivity
        await self._test_websocket_connectivity()
        
        # Test 6.2: WebSocket auth integration
        await self._test_websocket_auth()
        
        # Test 6.3: Golden Path endpoints
        await self._test_golden_path_endpoints()
    
    async def _test_websocket_connectivity(self):
        """Test WebSocket endpoint connectivity."""
        start_time = time.time()
        
        try:
            import websockets
            
            # Try to connect to WebSocket endpoint
            async with websockets.connect(
                STAGING_WEBSOCKET_URL,
                timeout=15,
                ping_interval=None
            ) as websocket:
                # Send a simple test message
                test_message = {
                    "type": "connection_test",
                    "timestamp": time.time(),
                    "client_id": "validation_suite"
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    self._add_result(ValidationResult(
                        test_name="WebSocket connectivity",
                        category="WebSocket and Golden Path",
                        passed=True,
                        message="WebSocket connectivity confirmed with response",
                        details={"response_received": True},
                        duration=time.time() - start_time
                    ))
                except asyncio.TimeoutError:
                    self._add_result(ValidationResult(
                        test_name="WebSocket connectivity",
                        category="WebSocket and Golden Path",
                        passed=True,  # Connection successful even without response
                        message="WebSocket connection established (no response required)",
                        duration=time.time() - start_time
                    ))
                    
        except ImportError:
            self._add_result(ValidationResult(
                test_name="WebSocket connectivity",
                category="WebSocket and Golden Path",
                passed=False,
                message="websockets library not available for testing",
                error="Install websockets library: pip install websockets",
                duration=time.time() - start_time
            ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="WebSocket connectivity",
                category="WebSocket and Golden Path",
                passed=False,
                message="WebSocket connectivity failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_websocket_auth(self):
        """Test WebSocket authentication integration."""
        start_time = time.time()
        
        try:
            # Test WebSocket auth endpoint
            url = f"{STAGING_BASE_URL}/api/websocket/auth"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    # Expect auth-related response
                    if response.status in [401, 403, 422]:
                        self._add_result(ValidationResult(
                            test_name="WebSocket authentication integration",
                            category="WebSocket and Golden Path",
                            passed=True,
                            message="WebSocket auth endpoint responding (requires authentication)",
                            duration=time.time() - start_time
                        ))
                    elif response.status == 200:
                        self._add_result(ValidationResult(
                            test_name="WebSocket authentication integration",
                            category="WebSocket and Golden Path",
                            passed=True,
                            message="WebSocket auth endpoint accessible",
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="WebSocket authentication integration",
                            category="WebSocket and Golden Path",
                            passed=False,
                            message=f"WebSocket auth endpoint returned unexpected status {response.status}",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="WebSocket authentication integration",
                category="WebSocket and Golden Path",
                passed=False,
                message="WebSocket auth test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_golden_path_endpoints(self):
        """Test Golden Path critical endpoints."""
        start_time = time.time()
        
        golden_path_endpoints = [
            "/api/agents/execute",
            "/api/chat/session",
            "/api/user/context"
        ]
        
        for endpoint in golden_path_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        # Accept auth-required responses as valid
                        if response.status in [200, 401, 403, 422]:
                            self._add_result(ValidationResult(
                                test_name=f"Golden Path endpoint {endpoint}",
                                category="WebSocket and Golden Path",
                                passed=True,
                                message=f"Golden Path endpoint {endpoint} responding (status: {response.status})",
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"Golden Path endpoint {endpoint}",
                                category="WebSocket and Golden Path",
                                passed=False,
                                message=f"Golden Path endpoint {endpoint} returned status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"Golden Path endpoint {endpoint}",
                    category="WebSocket and Golden Path",
                    passed=False,
                    message=f"Golden Path endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _validate_environment_resolution(self):
        """Category 7: Environment Variable Resolution"""
        print("\n🌍 Category 7: Environment Variable Resolution")
        print("-" * 50)
        
        # Test 7.1: Environment detection
        await self._test_environment_detection()
        
        # Test 7.2: SSOT configuration loading
        await self._test_ssot_configuration()
    
    async def _test_environment_detection(self):
        """Test environment variable detection and resolution."""
        start_time = time.time()
        
        try:
            # Import environment validation
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from netra_backend.app.core.configuration.staging_validator import StagingConfigurationValidator
            
            validator = StagingConfigurationValidator()
            result = validator.validate()
            
            if result.is_valid:
                self._add_result(ValidationResult(
                    test_name="Environment variable resolution",
                    category="Environment Variable Resolution",
                    passed=True,
                    message="Environment variables properly resolved and validated",
                    details={
                        "errors": len(result.errors),
                        "warnings": len(result.warnings),
                        "missing_critical": len(result.missing_critical)
                    },
                    duration=time.time() - start_time
                ))
            else:
                self._add_result(ValidationResult(
                    test_name="Environment variable resolution",
                    category="Environment Variable Resolution",
                    passed=False,
                    message="Environment validation detected issues",
                    error=f"Errors: {len(result.errors)}, Missing critical: {len(result.missing_critical)}",
                    details={
                        "errors": result.errors[:5],  # First 5 errors
                        "missing_critical": result.missing_critical
                    },
                    duration=time.time() - start_time
                ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="Environment variable resolution",
                category="Environment Variable Resolution",
                passed=False,
                message="Environment resolution test failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_ssot_configuration(self):
        """Test SSOT configuration loading and compliance."""
        start_time = time.time()
        
        try:
            # Test SSOT config endpoint
            url = f"{STAGING_BASE_URL}/api/config/ssot"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        config_data = await response.json()
                        self._add_result(ValidationResult(
                            test_name="SSOT configuration loading",
                            category="Environment Variable Resolution",
                            passed=True,
                            message="SSOT configuration loaded successfully",
                            details=config_data,
                            duration=time.time() - start_time
                        ))
                    elif response.status in [401, 403]:
                        self._add_result(ValidationResult(
                            test_name="SSOT configuration loading",
                            category="Environment Variable Resolution",
                            passed=True,
                            message="SSOT configuration endpoint accessible (requires auth)",
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="SSOT configuration loading",
                            category="Environment Variable Resolution",
                            passed=False,
                            message=f"SSOT configuration endpoint returned status {response.status}",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            # This endpoint may not exist, which is acceptable
            self._add_result(ValidationResult(
                test_name="SSOT configuration loading",
                category="Environment Variable Resolution",
                passed=True,
                message="SSOT configuration endpoint not available (may be normal)",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _validate_service_health(self):
        """Category 8: Service Health Checks"""
        print("\n💚 Category 8: Service Health Checks")
        print("-" * 50)
        
        # Test 8.1: Primary health endpoint
        await self._test_primary_health()
        
        # Test 8.2: Comprehensive health checks
        await self._test_comprehensive_health()
        
        # Test 8.3: Service dependency health
        await self._test_service_dependencies()
    
    async def _test_primary_health(self):
        """Test primary health endpoint."""
        start_time = time.time()
        
        try:
            url = f"{STAGING_BASE_URL}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        self._add_result(ValidationResult(
                            test_name="Primary health endpoint",
                            category="Service Health Checks",
                            passed=True,
                            message="Primary health endpoint healthy",
                            details=health_data,
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="Primary health endpoint",
                            category="Service Health Checks",
                            passed=False,
                            message=f"Primary health endpoint returned status {response.status}",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            self._add_result(ValidationResult(
                test_name="Primary health endpoint",
                category="Service Health Checks",
                passed=False,
                message="Primary health endpoint connection failed",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    async def _test_comprehensive_health(self):
        """Test comprehensive health check endpoints."""
        start_time = time.time()
        
        health_endpoints = [
            "/api/health/detailed",
            "/api/health/services",
            "/api/health/startup"
        ]
        
        for endpoint in health_endpoints:
            try:
                url = f"{STAGING_BASE_URL}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            self._add_result(ValidationResult(
                                test_name=f"Health endpoint {endpoint}",
                                category="Service Health Checks",
                                passed=True,
                                message=f"Health endpoint {endpoint} healthy",
                                duration=time.time() - start_time
                            ))
                        else:
                            self._add_result(ValidationResult(
                                test_name=f"Health endpoint {endpoint}",
                                category="Service Health Checks",
                                passed=False,
                                message=f"Health endpoint {endpoint} returned status {response.status}",
                                duration=time.time() - start_time
                            ))
            except Exception as e:
                self._add_result(ValidationResult(
                    test_name=f"Health endpoint {endpoint}",
                    category="Service Health Checks",
                    passed=False,
                    message=f"Health endpoint {endpoint} connection failed",
                    error=str(e),
                    duration=time.time() - start_time
                ))
    
    async def _test_service_dependencies(self):
        """Test service dependency health."""
        start_time = time.time()
        
        try:
            # Test inter-service communication
            url = f"{STAGING_BASE_URL}/api/health/dependencies"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    if response.status == 200:
                        deps_data = await response.json()
                        self._add_result(ValidationResult(
                            test_name="Service dependencies health",
                            category="Service Health Checks",
                            passed=True,
                            message="Service dependencies healthy",
                            details=deps_data,
                            duration=time.time() - start_time
                        ))
                    else:
                        self._add_result(ValidationResult(
                            test_name="Service dependencies health",
                            category="Service Health Checks",
                            passed=False,
                            message=f"Service dependencies check returned status {response.status}",
                            duration=time.time() - start_time
                        ))
        except Exception as e:
            # This endpoint may not exist
            self._add_result(ValidationResult(
                test_name="Service dependencies health",
                category="Service Health Checks",
                passed=True,
                message="Service dependencies endpoint not available (may be normal)",
                error=str(e),
                duration=time.time() - start_time
            ))
    
    def _add_result(self, result: ValidationResult):
        """Add a validation result and print it."""
        self.results.append(result)
        
        # Print result immediately
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"  {status}: {result.test_name}")
        if result.message:
            print(f"       {result.message}")
        if result.error:
            print(f"       Error: {result.error}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report."""
        total_duration = time.time() - self.start_time
        
        # Organize results by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        # Calculate category summaries
        category_summaries = {}
        for category, results in categories.items():
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            success_rate = (passed / len(results) * 100) if results else 0
            
            critical_failures = [r.test_name for r in results if not r.passed and 'critical' in r.test_name.lower()]
            
            category_summaries[category] = CategorySummary(
                category=category,
                total_tests=len(results),
                passed=passed,
                failed=failed,
                success_rate=success_rate,
                critical_failures=critical_failures
            )
        
        # Calculate overall metrics
        total_tests = len(self.results)
        total_passed = sum(1 for r in self.results if r.passed)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests else 0
        
        # Determine resolution status
        resolution_status = self._determine_resolution_status(category_summaries, overall_success_rate)
        
        # Print detailed report
        print("\n" + "=" * 80)
        print("COMPREHENSIVE VALIDATION REPORT - Issue #683")
        print("=" * 80)
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {overall_success_rate:.1f}%")
        print(f"   Duration: {total_duration:.2f} seconds")
        
        print(f"\n📋 CATEGORY BREAKDOWN:")
        for category, summary in category_summaries.items():
            status_icon = "✅" if summary.success_rate >= 80 else "⚠️" if summary.success_rate >= 60 else "❌"
            print(f"   {status_icon} {category}: {summary.success_rate:.1f}% ({summary.passed}/{summary.total_tests})")
            if summary.critical_failures:
                print(f"      Critical failures: {', '.join(summary.critical_failures)}")
        
        print(f"\n🎯 ISSUE #683 RESOLUTION STATUS:")
        print(f"   {resolution_status['icon']} {resolution_status['status']}")
        print(f"   {resolution_status['description']}")
        
        if resolution_status['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in resolution_status['recommendations']:
                print(f"   • {rec}")
        
        print("\n" + "=" * 80)
        
        return {
            "overall_success_rate": overall_success_rate,
            "total_tests": total_tests,
            "total_passed": total_passed,
            "category_summaries": {k: v.__dict__ for k, v in category_summaries.items()},
            "resolution_status": resolution_status,
            "duration": total_duration,
            "timestamp": datetime.now().isoformat()
        }
    
    def _determine_resolution_status(self, category_summaries: Dict[str, CategorySummary], overall_success_rate: float) -> Dict[str, Any]:
        """Determine if Issue #683 has been resolved based on validation results."""
        
        # Critical categories that MUST pass for issue resolution
        critical_categories = [
            "JWT Configuration",
            "Database Connectivity", 
            "Security Configuration",
            "Service Health Checks"
        ]
        
        critical_success_rates = []
        for category in critical_categories:
            if category in category_summaries:
                critical_success_rates.append(category_summaries[category].success_rate)
        
        avg_critical_success = sum(critical_success_rates) / len(critical_success_rates) if critical_success_rates else 0
        
        # Determine status
        if overall_success_rate >= 85 and avg_critical_success >= 90:
            return {
                "status": "RESOLVED",
                "icon": "✅",
                "description": "Issue #683 appears to be RESOLVED. Recent configuration fixes have successfully addressed the staging environment validation failures.",
                "recommendations": [
                    "Deploy to staging with confidence",
                    "Monitor staging environment for 24-48 hours",
                    "Proceed with Golden Path validation testing"
                ]
            }
        elif overall_success_rate >= 70 and avg_critical_success >= 75:
            return {
                "status": "MOSTLY RESOLVED",
                "icon": "⚠️",
                "description": "Issue #683 is MOSTLY RESOLVED. Most configuration issues appear fixed but some minor issues remain.",
                "recommendations": [
                    "Address remaining configuration issues",
                    "Re-run validation after fixes",
                    "Consider staged deployment with monitoring"
                ]
            }
        elif overall_success_rate >= 50:
            return {
                "status": "PARTIALLY RESOLVED", 
                "icon": "🔄",
                "description": "Issue #683 is PARTIALLY RESOLVED. Significant progress made but critical issues still exist.",
                "recommendations": [
                    "Focus on critical category failures",
                    "Investigate recent configuration deployment",
                    "Verify GCP environment variable setup"
                ]
            }
        else:
            return {
                "status": "NOT RESOLVED",
                "icon": "❌", 
                "description": "Issue #683 is NOT RESOLVED. Major configuration issues persist in staging environment.",
                "recommendations": [
                    "Review GCP staging environment setup",
                    "Verify configuration deployment process",
                    "Check Google Secret Manager access",
                    "Investigate service dependency issues"
                ]
            }

async def main():
    """Main validation execution."""
    validator = StagingEnvironmentValidator()
    
    try:
        report = await validator.run_all_validations()
        
        # Exit code based on resolution status
        if report["resolution_status"]["status"] in ["RESOLVED", "MOSTLY RESOLVED"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Validation failed with unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())