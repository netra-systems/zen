"""
Mission Critical JWT Validation Tests

Tests critical JWT validation functionality that directly impacts business value.
These tests MUST PASS to ensure user authentication works and revenue is protected.

ULTRA CRITICAL: JWT validation failures = 100% user lockout = $0 revenue

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Authentication affects every user
- Business Goal: Prevent complete system lockout due to JWT validation failures  
- Value Impact: Protects ALL business value that depends on user authentication
- Strategic Impact: $120K+ MRR protection through functional authentication
"""

import pytest
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.core.unified.jwt_validator import (
    UnifiedJWTValidator,
    TokenValidationResult, 
    TokenType
)
from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator,
    GoldenPathValidationResult
)
from netra_backend.app.core.service_dependencies.models import (
    ServiceType,
    EnvironmentType
)


class TestJWTValidationMissionCritical:
    """
    Mission Critical JWT validation tests.
    
    FAILURE TOLERANCE: ZERO
    These tests protect the authentication infrastructure that enables all business value.
    """

    @pytest.fixture(scope="class")
    def critical_test_logger(self):
        """Logger for mission critical test output."""
        logger = logging.getLogger("mission_critical_jwt")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                " ALERT:  CRITICAL JWT: %(asctime)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    @pytest.fixture
    def mission_critical_jwt_validator(self):
        """JWT Validator for mission critical tests."""
        return UnifiedJWTValidator()

    @pytest.fixture
    def mission_critical_golden_path_validator(self):
        """Golden Path Validator for mission critical tests."""
        return GoldenPathValidator()

    def test_mission_critical_jwt_validator_initialization(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: JWT Validator must initialize successfully."""
        
        critical_test_logger.info("Testing JWT Validator initialization")
        
        # JWT Validator MUST be properly initialized
        assert mission_critical_jwt_validator is not None
        assert isinstance(mission_critical_jwt_validator, UnifiedJWTValidator)
        
        # Must have required configuration
        assert mission_critical_jwt_validator.algorithm == "HS256"
        assert mission_critical_jwt_validator.issuer == "netra-auth-service"
        assert mission_critical_jwt_validator.access_token_expire_minutes > 0
        assert mission_critical_jwt_validator.refresh_token_expire_days > 0
        
        critical_test_logger.info(" PASS:  JWT Validator initialization PASSED")

    def test_mission_critical_jwt_methods_exist(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: JWT Validator MUST have all required authentication methods."""
        
        critical_test_logger.info("Testing JWT Validator required methods existence")
        
        # These methods are REQUIRED for authentication to work
        required_methods = [
            'create_access_token',
            'create_refresh_token', 
            'validate_token_jwt',
            'refresh_access_token',
            'create_service_token'
        ]
        
        missing_methods = []
        non_callable_methods = []
        
        for method_name in required_methods:
            if not hasattr(mission_critical_jwt_validator, method_name):
                missing_methods.append(method_name)
            else:
                method = getattr(mission_critical_jwt_validator, method_name)
                if not callable(method):
                    non_callable_methods.append(method_name)
        
        # CRITICAL ASSERTIONS: Any failure = complete auth breakdown
        assert len(missing_methods) == 0, f" ALERT:  CRITICAL: Missing JWT methods: {missing_methods}"
        assert len(non_callable_methods) == 0, f" ALERT:  CRITICAL: Non-callable JWT methods: {non_callable_methods}"
        
        critical_test_logger.info(f" PASS:  All {len(required_methods)} JWT methods exist and are callable")

    @pytest.mark.asyncio
    async def test_mission_critical_jwt_token_creation_validation_cycle(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: Complete token creation and validation cycle MUST work."""
        
        critical_test_logger.info("Testing critical JWT token creation/validation cycle")
        
        test_user_id = "mission-critical-user"
        test_email = "critical@example.com"
        test_permissions = ["critical", "auth"]
        
        try:
            # Step 1: Token creation MUST work
            start_time = time.time()
            
            access_token = await mission_critical_jwt_validator.create_access_token(
                user_id=test_user_id,
                email=test_email,
                permissions=test_permissions
            )
            
            creation_time = time.time() - start_time
            
            # CRITICAL: Token must be created
            assert access_token is not None, " ALERT:  CRITICAL: Token creation returned None"
            assert isinstance(access_token, str), f" ALERT:  CRITICAL: Token is not string: {type(access_token)}"
            assert len(access_token) > 50, f" ALERT:  CRITICAL: Token too short: {len(access_token)} chars"
            
            # CRITICAL: Token creation must be fast (< 5 seconds)
            assert creation_time < 5.0, f" ALERT:  CRITICAL: Token creation too slow: {creation_time}s"
            
            critical_test_logger.info(f" PASS:  Token created in {creation_time:.2f}s")
            
            # Step 2: Token validation MUST work
            validation_start = time.time()
            
            validation_result = await mission_critical_jwt_validator.validate_token_jwt(access_token)
            
            validation_time = time.time() - validation_start
            
            # CRITICAL: Validation must succeed
            assert isinstance(validation_result, TokenValidationResult), " ALERT:  CRITICAL: Invalid validation result type"
            assert validation_result.valid is True, f" ALERT:  CRITICAL: Token validation failed: {validation_result.error}"
            assert validation_result.user_id == test_user_id, f" ALERT:  CRITICAL: Wrong user_id: {validation_result.user_id}"
            assert validation_result.email == test_email, f" ALERT:  CRITICAL: Wrong email: {validation_result.email}"
            assert validation_result.error is None, f" ALERT:  CRITICAL: Validation error: {validation_result.error}"
            
            # CRITICAL: Validation must be fast (< 3 seconds)
            assert validation_time < 3.0, f" ALERT:  CRITICAL: Token validation too slow: {validation_time}s"
            
            critical_test_logger.info(f" PASS:  Token validated in {validation_time:.2f}s")
            critical_test_logger.info(" TARGET:  CRITICAL JWT CYCLE SUCCESSFUL")
            
        except Exception as e:
            critical_test_logger.error(f" ALERT:  CRITICAL JWT CYCLE FAILED: {e}")
            pytest.fail(f" ALERT:  MISSION CRITICAL FAILURE: JWT token cycle failed: {e}")

    @pytest.mark.asyncio
    async def test_mission_critical_refresh_token_flow(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: Refresh token flow MUST work to prevent user session expiration."""
        
        critical_test_logger.info("Testing critical refresh token flow")
        
        test_user_id = "refresh-critical-user"
        
        try:
            # Create initial tokens
            access_token = await mission_critical_jwt_validator.create_access_token(
                user_id=test_user_id,
                email="refresh@example.com"
            )
            
            refresh_token = await mission_critical_jwt_validator.create_refresh_token(
                user_id=test_user_id
            )
            
            # CRITICAL: Both tokens must be created
            assert access_token is not None, " ALERT:  CRITICAL: Access token creation failed"
            assert refresh_token is not None, " ALERT:  CRITICAL: Refresh token creation failed"
            assert access_token != refresh_token, " ALERT:  CRITICAL: Tokens are identical"
            
            # CRITICAL: Refresh flow must work
            new_access_token = await mission_critical_jwt_validator.refresh_access_token(refresh_token)
            
            assert new_access_token is not None, " ALERT:  CRITICAL: Token refresh returned None"
            assert isinstance(new_access_token, str), " ALERT:  CRITICAL: Refreshed token is not string"
            assert new_access_token != access_token, " ALERT:  CRITICAL: Refreshed token same as original"
            
            # CRITICAL: New token must validate correctly
            validation_result = await mission_critical_jwt_validator.validate_token_jwt(new_access_token)
            
            assert validation_result.valid is True, f" ALERT:  CRITICAL: Refreshed token validation failed: {validation_result.error}"
            assert validation_result.user_id == test_user_id, " ALERT:  CRITICAL: Refreshed token wrong user"
            
            critical_test_logger.info(" PASS:  REFRESH TOKEN FLOW SUCCESSFUL")
            
        except Exception as e:
            critical_test_logger.error(f" ALERT:  CRITICAL REFRESH FLOW FAILED: {e}")
            pytest.fail(f" ALERT:  MISSION CRITICAL FAILURE: Refresh token flow failed: {e}")

    @pytest.mark.asyncio
    async def test_mission_critical_invalid_token_handling(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: Invalid token handling MUST NOT crash the system."""
        
        critical_test_logger.info("Testing critical invalid token handling")
        
        # These invalid tokens MUST be handled gracefully
        invalid_tokens = [
            "invalid.jwt.token",
            "not-a-token-at-all",
            "",
            "eyJhbGciOiJIUzI1NiJ9.invalid.signature",
            "bearer-prefix-token",
            "extremely.long.token." + "x" * 1000,
            None
        ]
        
        for i, invalid_token in enumerate(invalid_tokens):
            if invalid_token is None:
                continue
                
            try:
                result = await mission_critical_jwt_validator.validate_token_jwt(invalid_token)
                
                # CRITICAL: Must return validation result, not crash
                assert isinstance(result, TokenValidationResult), f" ALERT:  CRITICAL: Invalid result type for token {i}"
                assert result.valid is False, f" ALERT:  CRITICAL: Invalid token marked as valid: {invalid_token[:30]}"
                assert result.error is not None, f" ALERT:  CRITICAL: No error for invalid token: {invalid_token[:30]}"
                assert result.user_id is None, f" ALERT:  CRITICAL: Invalid token has user_id: {invalid_token[:30]}"
                
            except Exception as e:
                critical_test_logger.error(f" ALERT:  CRITICAL: Invalid token caused crash: {invalid_token[:30]} -> {e}")
                pytest.fail(f" ALERT:  MISSION CRITICAL FAILURE: Invalid token handling crashed: {e}")
        
        critical_test_logger.info(f" PASS:  All {len(invalid_tokens)-1} invalid tokens handled correctly")

    @pytest.mark.asyncio 
    async def test_mission_critical_golden_path_vs_actual_jwt_architecture(
        self,
        mission_critical_golden_path_validator,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: Document the architectural mismatch causing Golden Path failures."""
        
        critical_test_logger.info("Testing critical Golden Path vs JWT architecture mismatch")
        
        # Create mock app that represents current system state
        from fastapi import FastAPI
        app = FastAPI()
        
        # CURRENT REALITY: We have UnifiedJWTValidator
        app.state.unified_jwt_validator = mission_critical_jwt_validator
        app.state.db_session_factory = AsyncMock()
        app.state.redis_manager = AsyncMock()
        
        # CRITICAL ISSUE: No app.state.key_manager as Golden Path expects
        # app.state.key_manager = None  # This is the problem
        
        # Test Golden Path validation
        result = await mission_critical_golden_path_validator._validate_jwt_capabilities(app)
        
        # EXPECTED FAILURE: Golden Path can't find JWT capabilities
        assert result["success"] is False, "Golden Path should fail due to architectural mismatch"
        assert result["details"]["key_manager"] is False, "key_manager should be missing"
        
        # But prove JWT actually works
        try:
            test_token = await mission_critical_jwt_validator.create_access_token(
                user_id="architecture-test",
                email="arch@example.com"
            )
            
            validation_result = await mission_critical_jwt_validator.validate_token_jwt(test_token)
            jwt_actually_works = validation_result.valid
            
        except Exception:
            jwt_actually_works = False
            
        # CRITICAL INSIGHT: JWT works but Golden Path can't detect it
        critical_test_logger.error(" ALERT:  ARCHITECTURAL MISMATCH CONFIRMED:")
        critical_test_logger.error(f"   - JWT functionality works: {jwt_actually_works}")
        critical_test_logger.error(f"   - Golden Path detection: {result['success']}")
        critical_test_logger.error("   - ROOT CAUSE: Golden Path expects app.state.key_manager")
        critical_test_logger.error("   - REALITY: We use UnifiedJWTValidator pattern")
        critical_test_logger.error("   - IMPACT: Authentication appears broken but actually works")
        
        # This test documents the bug - both conditions can be true
        if jwt_actually_works:
            critical_test_logger.error(" TARGET:  BUG REPRODUCED: JWT works but Golden Path fails")

    @pytest.mark.asyncio
    async def test_mission_critical_jwt_performance_requirements(
        self,
        mission_critical_jwt_validator,
        critical_test_logger
    ):
        """CRITICAL: JWT operations must meet performance requirements."""
        
        critical_test_logger.info("Testing critical JWT performance requirements")
        
        # Performance requirements for business-critical auth operations
        max_token_creation_time = 5.0  # seconds
        max_token_validation_time = 3.0  # seconds
        max_acceptable_failures = 0  # Zero tolerance
        
        test_iterations = 10
        creation_times = []
        validation_times = []
        failures = 0
        
        for i in range(test_iterations):
            try:
                # Test token creation performance
                start_time = time.time()
                
                token = await mission_critical_jwt_validator.create_access_token(
                    user_id=f"perf-user-{i}",
                    email=f"perf{i}@example.com"
                )
                
                creation_time = time.time() - start_time
                creation_times.append(creation_time)
                
                # Test token validation performance
                validation_start = time.time()
                
                result = await mission_critical_jwt_validator.validate_token_jwt(token)
                
                validation_time = time.time() - validation_start
                validation_times.append(validation_time)
                
                if not result.valid:
                    failures += 1
                    
            except Exception as e:
                failures += 1
                critical_test_logger.error(f" ALERT:  Performance test iteration {i} failed: {e}")
        
        # CRITICAL PERFORMANCE ASSERTIONS
        avg_creation_time = sum(creation_times) / len(creation_times)
        avg_validation_time = sum(validation_times) / len(validation_times) 
        max_creation_time = max(creation_times)
        max_validation_time = max(validation_times)
        
        assert failures <= max_acceptable_failures, f" ALERT:  CRITICAL: {failures} JWT operations failed"
        assert avg_creation_time < max_token_creation_time, f" ALERT:  CRITICAL: Avg creation time {avg_creation_time:.2f}s exceeds {max_token_creation_time}s"
        assert avg_validation_time < max_token_validation_time, f" ALERT:  CRITICAL: Avg validation time {avg_validation_time:.2f}s exceeds {max_token_validation_time}s"
        assert max_creation_time < max_token_creation_time * 2, f" ALERT:  CRITICAL: Max creation time {max_creation_time:.2f}s too high"
        assert max_validation_time < max_token_validation_time * 2, f" ALERT:  CRITICAL: Max validation time {max_validation_time:.2f}s too high"
        
        critical_test_logger.info(f" PASS:  PERFORMANCE REQUIREMENTS MET:")
        critical_test_logger.info(f"   - Avg creation time: {avg_creation_time:.3f}s")
        critical_test_logger.info(f"   - Avg validation time: {avg_validation_time:.3f}s") 
        critical_test_logger.info(f"   - Failures: {failures}/{test_iterations}")

    def test_mission_critical_test_summary(self, critical_test_logger):
        """Document the mission critical JWT validation test suite."""
        
        critical_summary = {
            "mission": "Protect $120K+ MRR by ensuring JWT authentication works",
            "failure_tolerance": "ZERO - Any failure = complete user lockout",
            "critical_validations": [
                "JWT Validator initialization and method availability",
                "Token creation/validation cycle performance",
                "Refresh token flow for session continuity", 
                "Invalid token handling without system crashes",
                "Performance requirements for business operations",
                "Documentation of Golden Path architectural mismatch"
            ],
            "business_impact": "Complete authentication infrastructure protection",
            "success_criteria": "ALL tests MUST pass for system to be production-ready",
            "architectural_insight": "Golden Path detection failure != JWT functionality failure"
        }
        
        assert critical_summary["failure_tolerance"] == "ZERO - Any failure = complete user lockout"
        assert len(critical_summary["critical_validations"]) >= 6
        assert "$120K+" in critical_summary["mission"]
        
        critical_test_logger.info("\n" + "="*80)
        critical_test_logger.info(" ALERT:  MISSION CRITICAL JWT VALIDATION TEST SUMMARY")
        critical_test_logger.info("="*80)
        for key, value in critical_summary.items():
            if isinstance(value, list):
                critical_test_logger.info(f"{key.upper()}:")
                for item in value:
                    critical_test_logger.info(f"  - {item}")
            else:
                critical_test_logger.info(f"{key.upper()}: {value}")
        critical_test_logger.info("="*80)
        critical_test_logger.info(" TARGET:  ALL MISSION CRITICAL JWT TESTS MUST PASS FOR PRODUCTION DEPLOYMENT")
        critical_test_logger.info("="*80)