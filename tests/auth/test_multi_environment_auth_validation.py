"""
Multi-Environment Authentication Validation Test Strategy
========================================================

This comprehensive test suite ensures JWT authentication works consistently 
across all environments (development, staging, production) and prevents
the type of JWT secret inconsistency issues identified in the Five Whys analysis.

Business Value: Prevents $120K+ MRR loss from authentication failures
Technical Value: Ensures 95%+ authentication success rate across environments
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import pytest
import httpx

from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service

logger = logging.getLogger(__name__)


class EnvironmentAuthTester:
    """Comprehensive authentication tester for multiple environments."""
    
    def __init__(self, environment: str):
        self.environment = environment.lower()
        self.env = get_env()
        self.jwt_manager = get_jwt_secret_manager()
        
        # Environment-specific configurations
        self.config = self._get_environment_config()
        
    def _get_environment_config(self) -> Dict[str, str]:
        """Get environment-specific URLs and configurations."""
        configs = {
            "development": {
                "auth_service_url": "http://localhost:8081",
                "backend_url": "http://localhost:8000",
                "test_user_email": "dev-user@test.local"
            },
            "staging": {
                "auth_service_url": "https://auth.staging.netrasystems.ai",
                "backend_url": "https://api.staging.netrasystems.ai",
                "test_user_email": "staging-e2e-user-001@test.local"
            },
            "production": {
                "auth_service_url": "https://auth.netrasystems.ai",
                "backend_url": "https://api.netrasystems.ai",
                "test_user_email": None  # No test tokens in production
            }
        }
        
        return configs.get(self.environment, configs["development"])
    
    async def test_service_health(self) -> Dict[str, Any]:
        """Test health of auth and backend services."""
        results = {}
        
        # Test auth service health
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config['auth_service_url']}/health")
                results["auth_service"] = {
                    "accessible": True,
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            results["auth_service"] = {
                "accessible": False,
                "error": str(e)
            }
        
        # Test backend service health
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.config['backend_url']}/health")
                results["backend_service"] = {
                    "accessible": True,
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None
                }
        except Exception as e:
            results["backend_service"] = {
                "accessible": False,
                "error": str(e)
            }
        
        return results
    
    def test_jwt_secret_configuration(self) -> Dict[str, Any]:
        """Test JWT secret configuration consistency."""
        try:
            # Get unified JWT secret
            unified_secret = get_unified_jwt_secret()
            
            # Get JWT manager debug info
            debug_info = self.jwt_manager.get_debug_info()
            
            # Check environment-specific requirements
            env_specific_key = f"JWT_SECRET_{self.environment.upper()}"
            has_env_specific = bool(self.env.get(env_specific_key))
            has_generic = bool(self.env.get("JWT_SECRET_KEY"))
            has_legacy = bool(self.env.get("JWT_SECRET"))
            
            # Determine expected behavior based on environment
            expected_sources = []
            if self.environment == "production":
                expected_sources = [f"JWT_SECRET_PRODUCTION", "JWT_SECRET_KEY"]
            elif self.environment == "staging":
                expected_sources = [f"JWT_SECRET_STAGING", "JWT_SECRET_KEY"]
            else:
                expected_sources = ["JWT_SECRET_KEY", "JWT_SECRET"]
            
            available_sources = [
                source for source in expected_sources
                if self.env.get(source)
            ]
            
            return {
                "unified_secret_available": True,
                "unified_secret_length": len(unified_secret),
                "environment_specific_available": has_env_specific,
                "generic_available": has_generic,
                "legacy_available": has_legacy,
                "expected_sources": expected_sources,
                "available_sources": available_sources,
                "configuration_valid": len(available_sources) > 0,
                "debug_info": debug_info
            }
            
        except Exception as e:
            return {
                "unified_secret_available": False,
                "error": str(e)
            }
    
    async def test_token_generation_validation_cycle(self) -> Dict[str, Any]:
        """Test complete token generation and validation cycle."""
        if self.environment == "production":
            return {
                "skipped": True,
                "reason": "Token generation testing not allowed in production"
            }
        
        try:
            # Generate test token
            test_email = self.config["test_user_email"]
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.config['auth_service_url']}/auth/dev-login", json={
                    "email": test_email,
                    "provider": "test"
                })
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "step": "token_generation",
                        "error": f"Status {response.status_code}: {response.text}"
                    }
                
                token_data = response.json()
                test_token = token_data.get("access_token")
                
                if not test_token:
                    return {
                        "success": False,
                        "step": "token_generation",
                        "error": "No access token in response"
                    }
            
            # Validate with auth service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.config['auth_service_url']}/auth/validate", json={
                    "token": test_token,
                    "token_type": "access"
                })
                
                auth_validation_success = response.status_code == 200
                auth_validation_data = response.json() if response.status_code == 200 else response.text
            
            # Validate with backend service
            auth_client = AuthServiceClient()
            backend_validation_result = await auth_client.validate_token(test_token)
            backend_validation_success = (
                backend_validation_result is not None and 
                backend_validation_result.get("valid", False)
            )
            
            return {
                "success": auth_validation_success and backend_validation_success,
                "token_generated": True,
                "auth_service_validation": {
                    "success": auth_validation_success,
                    "data": auth_validation_data
                },
                "backend_service_validation": {
                    "success": backend_validation_success,
                    "data": backend_validation_result
                },
                "cross_service_consistency": auth_validation_success and backend_validation_success
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive authentication validation for this environment."""
        logger.info(f"Running comprehensive auth validation for {self.environment}")
        
        validation_results = {
            "environment": self.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tests": {}
        }
        
        # Test 1: Service health
        validation_results["tests"]["service_health"] = await self.test_service_health()
        
        # Test 2: JWT configuration
        validation_results["tests"]["jwt_configuration"] = self.test_jwt_secret_configuration()
        
        # Test 3: Token generation and validation cycle
        validation_results["tests"]["token_cycle"] = await self.test_token_generation_validation_cycle()
        
        # Overall assessment
        service_health = validation_results["tests"]["service_health"]
        jwt_config = validation_results["tests"]["jwt_configuration"]
        token_cycle = validation_results["tests"]["token_cycle"]
        
        services_healthy = all([
            service_health.get("auth_service", {}).get("healthy", False),
            service_health.get("backend_service", {}).get("healthy", False)
        ])
        
        jwt_properly_configured = jwt_config.get("configuration_valid", False)
        
        if token_cycle.get("skipped", False):
            # Production - can't test token cycle
            overall_success = services_healthy and jwt_properly_configured
        else:
            # Development/staging - can test token cycle
            token_cycle_works = token_cycle.get("cross_service_consistency", False)
            overall_success = services_healthy and jwt_properly_configured and token_cycle_works
        
        validation_results["overall_assessment"] = {
            "success": overall_success,
            "services_healthy": services_healthy,
            "jwt_properly_configured": jwt_properly_configured,
            "token_validation_works": token_cycle.get("cross_service_consistency", None),
            "issues": []
        }
        
        # Identify specific issues
        if not services_healthy:
            validation_results["overall_assessment"]["issues"].append("Services not healthy")
        
        if not jwt_properly_configured:
            validation_results["overall_assessment"]["issues"].append("JWT configuration invalid")
        
        if not token_cycle.get("skipped", False) and not token_cycle.get("cross_service_consistency", False):
            validation_results["overall_assessment"]["issues"].append("Cross-service token validation failing")
        
        return validation_results


@pytest.mark.asyncio
class TestMultiEnvironmentAuthValidation:
    """Test suite for multi-environment authentication validation."""
    
    @pytest.fixture(params=["development", "staging"])
    def environment(self, request):
        """Environment fixture - tests development and staging."""
        return request.param
    
    @pytest.fixture
    def auth_tester(self, environment):
        """Auth tester fixture."""
        return EnvironmentAuthTester(environment)
    
    async def test_environment_service_health(self, auth_tester):
        """Test that services are healthy in each environment."""
        health_results = await auth_tester.test_service_health()
        
        # Log results for debugging
        logger.info(f"Service health for {auth_tester.environment}:")
        logger.info(json.dumps(health_results, indent=2))
        
        # Both services should be accessible
        assert health_results.get("auth_service", {}).get("accessible", False), \
            f"Auth service not accessible in {auth_tester.environment}"
        
        assert health_results.get("backend_service", {}).get("accessible", False), \
            f"Backend service not accessible in {auth_tester.environment}"
        
        # Both services should be healthy
        assert health_results.get("auth_service", {}).get("healthy", False), \
            f"Auth service not healthy in {auth_tester.environment}"
        
        assert health_results.get("backend_service", {}).get("healthy", False), \
            f"Backend service not healthy in {auth_tester.environment}"
    
    def test_environment_jwt_configuration(self, auth_tester):
        """Test JWT configuration consistency in each environment."""
        jwt_config = auth_tester.test_jwt_secret_configuration()
        
        # Log results for debugging
        logger.info(f"JWT configuration for {auth_tester.environment}:")
        logger.info(json.dumps(jwt_config, indent=2))
        
        # Unified JWT secret should be available
        assert jwt_config.get("unified_secret_available", False), \
            f"Unified JWT secret not available in {auth_tester.environment}"
        
        # JWT secret should meet minimum length requirement
        assert jwt_config.get("unified_secret_length", 0) >= 32, \
            f"JWT secret too short in {auth_tester.environment}: {jwt_config.get('unified_secret_length', 0)} chars"
        
        # Configuration should be valid (at least one expected source available)
        assert jwt_config.get("configuration_valid", False), \
            f"JWT configuration invalid in {auth_tester.environment}: expected {jwt_config.get('expected_sources', [])}, got {jwt_config.get('available_sources', [])}"
    
    @pytest.mark.asyncio
    async def test_environment_token_validation_consistency(self, auth_tester):
        """Test token validation consistency between services in each environment."""
        if auth_tester.environment == "production":
            pytest.skip("Token generation testing not allowed in production")
        
        token_cycle = await auth_tester.test_token_generation_validation_cycle()
        
        # Log results for debugging
        logger.info(f"Token validation cycle for {auth_tester.environment}:")
        logger.info(json.dumps(token_cycle, indent=2))
        
        # Token should be generated successfully
        assert token_cycle.get("token_generated", False), \
            f"Token generation failed in {auth_tester.environment}: {token_cycle.get('error', 'Unknown error')}"
        
        # Auth service should validate its own tokens
        auth_validation = token_cycle.get("auth_service_validation", {})
        assert auth_validation.get("success", False), \
            f"Auth service failed to validate its own token in {auth_tester.environment}: {auth_validation.get('data', 'No data')}"
        
        # Backend service should validate auth service tokens
        backend_validation = token_cycle.get("backend_service_validation", {})
        assert backend_validation.get("success", False), \
            f"Backend service failed to validate auth service token in {auth_tester.environment}: {backend_validation.get('data', 'No data')}"
        
        # Cross-service consistency is critical
        assert token_cycle.get("cross_service_consistency", False), \
            f"Cross-service token validation inconsistent in {auth_tester.environment} - This indicates JWT secret mismatch!"
    
    @pytest.mark.asyncio
    async def test_comprehensive_environment_validation(self, auth_tester):
        """Run comprehensive validation suite for each environment."""
        results = await auth_tester.run_comprehensive_validation()
        
        # Log comprehensive results
        logger.info(f"Comprehensive validation results for {auth_tester.environment}:")
        logger.info(json.dumps(results, indent=2))
        
        # Overall assessment should be successful
        overall_assessment = results.get("overall_assessment", {})
        
        if not overall_assessment.get("success", False):
            issues = overall_assessment.get("issues", [])
            pytest.fail(
                f"Comprehensive validation failed in {auth_tester.environment}. "
                f"Issues: {issues}"
            )
        
        assert overall_assessment.get("success", False), \
            f"Comprehensive validation failed in {auth_tester.environment}"


@pytest.mark.staging
class TestStagingSpecificValidation:
    """Staging-specific validation tests based on Five Whys analysis."""
    
    @pytest.fixture
    def staging_tester(self):
        """Staging auth tester fixture."""
        return EnvironmentAuthTester("staging")
    
    @pytest.mark.asyncio
    async def test_staging_jwt_secret_regression_prevention(self, staging_tester):
        """Test that prevents the specific JWT secret issue identified in Five Whys analysis."""
        
        # Run comprehensive validation
        results = await staging_tester.run_comprehensive_validation()
        
        # Check for specific issues identified in Five Whys
        jwt_config = results["tests"]["jwt_configuration"]
        token_cycle = results["tests"]["token_cycle"]
        
        # JWT_SECRET_STAGING should be available (as configured in Cloud Run)
        available_sources = jwt_config.get("available_sources", [])
        assert "JWT_SECRET_STAGING" in available_sources or "JWT_SECRET_KEY" in available_sources, \
            f"Neither JWT_SECRET_STAGING nor JWT_SECRET_KEY available. Found: {available_sources}"
        
        # Cross-service validation MUST work (this was the main issue)
        if not token_cycle.get("skipped", False):
            cross_service_works = token_cycle.get("cross_service_consistency", False)
            
            if not cross_service_works:
                # Provide detailed failure information for debugging
                auth_validation = token_cycle.get("auth_service_validation", {})
                backend_validation = token_cycle.get("backend_service_validation", {})
                
                failure_details = {
                    "auth_service_validation": auth_validation,
                    "backend_service_validation": backend_validation,
                    "jwt_configuration": jwt_config,
                    "environment_debug": staging_tester.jwt_manager.get_debug_info()
                }
                
                pytest.fail(
                    f"STAGING JWT SECRET CONSISTENCY FAILURE DETECTED!\n"
                    f"This is the same issue identified in the Five Whys analysis.\n"
                    f"Auth service validates: {auth_validation.get('success', False)}\n"
                    f"Backend service validates: {backend_validation.get('success', False)}\n"
                    f"Failure details: {json.dumps(failure_details, indent=2)}"
                )
            
            assert cross_service_works, "Cross-service token validation must work to prevent $120K+ MRR loss"
    
    @pytest.mark.asyncio
    async def test_staging_authentication_success_rate(self, staging_tester):
        """Test that authentication success rate meets business requirements (95%+)."""
        
        # Run multiple validation cycles to test success rate
        success_count = 0
        total_tests = 10
        
        for i in range(total_tests):
            token_cycle = await staging_tester.test_token_generation_validation_cycle()
            if token_cycle.get("cross_service_consistency", False):
                success_count += 1
        
        success_rate = (success_count / total_tests) * 100
        
        logger.info(f"Staging authentication success rate: {success_rate}% ({success_count}/{total_tests})")
        
        # Business requirement: >95% success rate
        assert success_rate >= 95, \
            f"Staging authentication success rate too low: {success_rate}% (required: 95%+). " \
            f"This indicates the JWT secret consistency issue is still present."


if __name__ == "__main__":
    # Run the multi-environment validation tests
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))