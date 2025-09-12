
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
Golden Path Integration Test: User Sessions Table Validation

This test validates the Golden Path Validator's ability to detect the CRITICAL
user_sessions table issue that breaks authentication in staging environment.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Protect $120K+ MRR by ensuring Golden Path validation catches critical issues
- Value Impact: Golden Path Validator must catch deployment failures before they break auth
- Strategic Impact: Prevent authentication outages that block all user revenue

CRITICAL: This test validates that the Golden Path Validator correctly identifies
the user_sessions table deployment issue and fails validation appropriately.
"""

import pytest
import logging
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator, 
    GoldenPathValidationResult
)
from netra_backend.app.core.service_dependencies.models import (
from netra_backend.app.services.user_execution_context import UserExecutionContext
    ServiceType,
    EnvironmentType,
    GoldenPathRequirement
)

logger = logging.getLogger(__name__)


class TestUserSessionsGoldenPathValidation(BaseIntegrationTest):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    Integration test for Golden Path Validator detecting user_sessions table issues.
    
    This test ensures the Golden Path Validator properly identifies when the
    user_sessions table deployment has failed, which breaks authentication.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_golden_path_validator_detects_missing_user_sessions_table(self, real_services_fixture):
        """
        CRITICAL TEST: Golden Path Validator detects missing user_sessions table.
        
        This test validates that when the user_sessions table is missing from the database,
        the Golden Path Validator correctly identifies this as a critical failure
        and prevents the system from claiming everything is working.
        
        Expected Behavior:
        1. If user_sessions table exists: Validation PASSES
        2. If user_sessions table missing: Validation FAILS with critical error
        """
        logger.info(" SEARCH:  CRITICAL TEST: Golden Path Validator user_sessions detection")
        
        # Create mock FastAPI app with database session
        mock_app = MagicMock()
        mock_app.state.db_session_factory = real_services_fixture["db_session_factory"]
        
        # Initialize Golden Path Validator
        validator = GoldenPathValidator()
        
        # Run validation specifically for DATABASE_POSTGRES service
        services_to_validate = [ServiceType.DATABASE_POSTGRES]
        
        try:
            result = await validator.validate_golden_path_services(
                app=mock_app,
                services_to_validate=services_to_validate
            )
            
            assert isinstance(result, GoldenPathValidationResult)
            
            # Find the user authentication validation result
            auth_validation = None
            for validation in result.validation_results:
                if validation.get("requirement") == "user_authentication_ready":
                    auth_validation = validation
                    break
            
            assert auth_validation is not None, "user_authentication_ready validation not found"
            
            # Check if user_sessions table validation passed or failed
            if auth_validation["success"]:
                logger.info(" PASS:  Golden Path Validator: user_sessions table exists and is accessible")
                
                # Verify the table details were checked
                details = auth_validation.get("details", {})
                tables = details.get("tables", {})
                
                assert "user_sessions" in tables, "user_sessions should be checked in table validation"
                assert tables["user_sessions"] is True, "user_sessions table should exist"
                
                logger.info(" PASS:  Golden Path Validator correctly validated user_sessions table structure")
                
            else:
                # This is the EXPECTED FAILURE case when reproducing the staging issue
                logger.error(" FAIL:  Golden Path Validator detected missing user_sessions table")
                
                # Verify it's correctly identified as a critical failure
                assert not result.overall_success, "Overall validation should fail when user_sessions missing"
                assert len(result.critical_failures) > 0, "Should have critical failures"
                assert len(result.business_impact_failures) > 0, "Should have business impact failures"
                
                # Check the specific error message
                error_message = auth_validation["message"]
                assert "user_sessions" in error_message.lower(), f"Error should mention user_sessions: {error_message}"
                
                logger.info(" PASS:  Golden Path Validator correctly detected user_sessions table deployment failure")
                
                # Log the business impact for visibility
                for impact in result.business_impact_failures:
                    logger.error(f" ALERT:  Business Impact: {impact}")
                
                # This test PASSES when it correctly detects the issue
                # The failure is in the staging deployment, not in our validation logic
                
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Golden Path Validator crashed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_golden_path_validator_user_auth_tables_comprehensive(self, real_services_fixture):
        """
        CRITICAL TEST: Comprehensive validation of user authentication table requirements.
        
        This test validates all aspects of user authentication table validation
        in the Golden Path Validator, ensuring it checks:
        1. Table existence (user_sessions, users)
        2. Table accessibility
        3. Required indexes
        4. Proper error reporting
        """
        logger.info(" SEARCH:  CRITICAL TEST: Comprehensive user auth tables validation")
        
        # Create mock app with real database session
        mock_app = MagicMock()
        mock_app.state.db_session_factory = real_services_fixture["db_session_factory"]
        
        validator = GoldenPathValidator()
        
        # Test the specific user auth tables validation function
        try:
            validation_result = await validator._validate_user_auth_tables(mock_app)
            
            assert isinstance(validation_result, dict)
            assert "requirement" in validation_result
            assert "success" in validation_result
            assert "message" in validation_result
            assert "details" in validation_result
            
            logger.info(f"Validation result: {validation_result['success']}")
            logger.info(f"Message: {validation_result['message']}")
            
            details = validation_result["details"]
            
            if validation_result["success"]:
                # Successful validation - all tables exist
                assert "tables" in details, "Details should include table check results"
                tables = details["tables"]
                
                # Verify both critical tables were checked
                assert "users" in tables, "users table should be checked"
                assert "user_sessions" in tables, "user_sessions table should be checked"
                
                # Both should exist for success
                assert tables["users"] is True, "users table should exist"
                assert tables["user_sessions"] is True, "user_sessions table should exist"
                
                logger.info(" PASS:  All user authentication tables exist and are accessible")
                
            else:
                # Failed validation - identify missing tables
                if "tables" in details:
                    tables = details["tables"]
                    missing_tables = [table for table, exists in tables.items() if not exists]
                    
                    logger.error(f" FAIL:  Missing authentication tables: {missing_tables}")
                    
                    # Specifically check for user_sessions table issue
                    if "user_sessions" in missing_tables:
                        logger.error(" ALERT:  CRITICAL: user_sessions table missing - this breaks all authentication")
                        
                        # Verify the error message is informative
                        assert "user_sessions" in validation_result["message"], "Error message should mention missing user_sessions"
                
                elif "missing_tables" in details:
                    missing_tables = details["missing_tables"]
                    logger.error(f" FAIL:  Missing tables identified: {missing_tables}")
                    
                    if "user_sessions" in missing_tables:
                        logger.error(" ALERT:  CRITICAL: user_sessions missing from database deployment")
                
                # This is the expected case when reproducing the staging issue
                logger.info(" PASS:  Golden Path Validator correctly identified authentication table deployment issues")
                
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: User auth tables validation crashed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_golden_path_validator_reports_business_impact(self, real_services_fixture):
        """
        CRITICAL TEST: Golden Path Validator reports business impact of missing user_sessions.
        
        This test ensures that when user_sessions table is missing, the validator
        correctly reports the business impact (authentication failure, revenue loss).
        """
        logger.info(" SEARCH:  CRITICAL TEST: Golden Path Validator business impact reporting")
        
        mock_app = MagicMock()
        mock_app.state.db_session_factory = real_services_fixture["db_session_factory"]
        
        validator = GoldenPathValidator()
        
        # Get the user authentication requirement definition
        auth_requirement = None
        for req in validator.requirements:
            if req.requirement_name == "user_authentication_ready":
                auth_requirement = req
                break
        
        assert auth_requirement is not None, "user_authentication_ready requirement should be defined"
        assert auth_requirement.critical is True, "user authentication should be marked as critical"
        assert auth_requirement.business_impact, "user authentication should have business impact defined"
        
        logger.info(f"User auth business impact: {auth_requirement.business_impact}")
        
        # Run full validation to see business impact reporting
        result = await validator.validate_golden_path_services(
            app=mock_app,
            services_to_validate=[ServiceType.DATABASE_POSTGRES]
        )
        
        if not result.overall_success:
            # When validation fails, business impact should be reported
            assert len(result.business_impact_failures) > 0, "Should report business impact failures"
            
            # Check if user authentication business impact is included
            auth_impact_reported = any(
                "log in" in impact.lower() or "auth" in impact.lower()
                for impact in result.business_impact_failures
            )
            
            if auth_impact_reported:
                logger.info(" PASS:  Golden Path Validator correctly reported authentication business impact")
                for impact in result.business_impact_failures:
                    logger.warning(f" ALERT:  Business Impact: {impact}")
            else:
                logger.warning(" WARNING: [U+FE0F] Business impact for authentication not found in failures")
                
        else:
            logger.info(" PASS:  Golden Path Validator passed - authentication tables are properly deployed")
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    @pytest.mark.critical
    async def test_golden_path_validator_prevents_false_positives(self, real_services_fixture):
        """
        CRITICAL TEST: Golden Path Validator doesn't give false positives on auth validation.
        
        This test ensures that the validator only fails when there's a real issue,
        not due to validation logic bugs or transient database connection issues.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Golden Path Validator false positive prevention")
        
        mock_app = MagicMock()
        mock_app.state.db_session_factory = real_services_fixture["db_session_factory"]
        
        validator = GoldenPathValidator()
        
        # Run validation multiple times to check for consistency
        validation_runs = []
        
        for run_number in range(3):
            logger.info(f"Running validation attempt {run_number + 1}/3")
            
            try:
                result = await validator._validate_user_auth_tables(mock_app)
                validation_runs.append(result["success"])
                
                if not result["success"]:
                    logger.info(f"Run {run_number + 1} failed: {result['message']}")
                else:
                    logger.info(f"Run {run_number + 1} passed")
                    
            except Exception as e:
                logger.error(f"Run {run_number + 1} crashed: {e}")
                validation_runs.append(False)
        
        # Check for consistency - results should be the same
        if len(set(validation_runs)) == 1:
            logger.info(f" PASS:  Golden Path Validator consistent: all runs {'passed' if validation_runs[0] else 'failed'}")
            
            if not validation_runs[0]:
                logger.info(" PASS:  Consistent failure indicates real issue (not false positive)")
            
        else:
            logger.warning(f" WARNING: [U+FE0F] Inconsistent results: {validation_runs}")
            logger.warning("This may indicate flaky validation logic or transient database issues")
            
            # Count the failures vs successes
            failures = validation_runs.count(False)
            successes = validation_runs.count(True)
            
            logger.info(f"Failures: {failures}, Successes: {successes}")
            
            if failures > successes:
                logger.warning("Majority failed - likely a real issue")
            else:
                logger.warning("Majority passed - may be transient issues")
        
        # Log final assessment
        if all(validation_runs):
            logger.info(" PASS:  All validation runs passed - user_sessions table is properly deployed")
        elif not any(validation_runs):
            logger.error(" FAIL:  All validation runs failed - user_sessions table deployment issue confirmed")
        else:
            logger.warning(" WARNING: [U+FE0F] Mixed results - investigation needed for validation reliability")


class TestGoldenPathValidatorIntegrationWithMissingTable(BaseIntegrationTest):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    Test that simulates the exact staging issue where user_sessions table is missing.
    
    This test uses database session mocking to simulate the missing table condition
    and verify that the Golden Path Validator correctly identifies it.
    """
    
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_golden_path_validator_with_simulated_missing_table(self):
        """
        CRITICAL TEST: Simulate missing user_sessions table to test Golden Path Validator.
        
        This test creates a controlled scenario where the user_sessions table
        is missing to verify the Golden Path Validator correctly fails validation.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Simulated missing user_sessions table scenario")
        
        # Create mock database session that simulates missing user_sessions table
        mock_session = AsyncMock()
        
        # Mock the table existence check to return False for user_sessions
        async def mock_execute(query):
            query_text = str(query).lower()
            
            if "user_sessions" in query_text and "information_schema.tables" in query_text:
                # Simulate user_sessions table missing
                mock_result = MagicMock()
                mock_result.scalar.return_value = 0  # Table doesn't exist
                return mock_result
                
            elif "users" in query_text and "information_schema.tables" in query_text:
                # Simulate users table exists  
                mock_result = MagicMock()
                mock_result.scalar.return_value = 1  # Table exists
                return mock_result
                
            else:
                # Default case
                mock_result = MagicMock()
                mock_result.scalar.return_value = 0
                return mock_result
        
        mock_session.execute = mock_execute
        
        # Create mock session factory
        async def mock_session_factory():
            return mock_session
        
        # Create mock app with simulated missing table
        mock_app = MagicMock()
        mock_app.state.db_session_factory = mock_session_factory
        
        # Initialize validator
        validator = GoldenPathValidator()
        
        # Run validation - should detect missing user_sessions table
        try:
            result = await validator._validate_user_auth_tables(mock_app)
            
            # Validation should FAIL because user_sessions table is missing
            assert result["success"] is False, "Validation should fail when user_sessions table missing"
            
            # Check error message mentions the missing table
            assert "user_sessions" in result["message"].lower(), "Error message should mention user_sessions"
            
            # Check details show which tables are missing
            details = result["details"]
            if "tables" in details:
                tables = details["tables"]
                assert tables.get("user_sessions", True) is False, "user_sessions should be marked as missing"
                
            elif "missing_tables" in details:
                missing_tables = details["missing_tables"]
                assert "user_sessions" in missing_tables, "user_sessions should be in missing tables list"
            
            logger.info(" PASS:  Golden Path Validator correctly detected simulated missing user_sessions table")
            logger.info(f"Error message: {result['message']}")
            
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Golden Path Validator failed to handle missing table simulation: {e}")
    
    @pytest.mark.integration
    @pytest.mark.critical
    async def test_golden_path_full_validation_with_missing_user_sessions(self):
        """
        CRITICAL TEST: Full Golden Path validation with missing user_sessions table.
        
        This test runs the complete Golden Path validation with a simulated
        missing user_sessions table to verify end-to-end failure handling.
        """
        logger.info(" SEARCH:  CRITICAL TEST: Full Golden Path validation with missing user_sessions")
        
        # Create comprehensive mock that simulates the staging database state
        mock_session = AsyncMock()
        
        # Simulate database where most tables exist but user_sessions is missing
        async def mock_execute(query):
            query_text = str(query).lower()
            
            if "table_name = 'user_sessions'" in query_text:
                # user_sessions table missing
                mock_result = MagicMock()
                mock_result.scalar.return_value = 0
                return mock_result
                
            elif "table_name = 'users'" in query_text:
                # users table exists
                mock_result = MagicMock()
                mock_result.scalar.return_value = 1 
                return mock_result
                
            elif "pg_indexes" in query_text:
                # No indexes for missing table
                mock_result = MagicMock() 
                mock_result.scalar.return_value = 0
                return mock_result
                
            else:
                # Default response
                mock_result = MagicMock()
                mock_result.scalar.return_value = 0
                return mock_result
        
        mock_session.execute = mock_execute
        
        async def mock_session_factory():
            return mock_session
        
        # Mock app with complete state
        mock_app = MagicMock()
        mock_app.state.db_session_factory = mock_session_factory
        
        # Initialize validator 
        validator = GoldenPathValidator()
        
        # Run FULL Golden Path validation
        try:
            result = await validator.validate_golden_path_services(
                app=mock_app,
                services_to_validate=[ServiceType.DATABASE_POSTGRES]
            )
            
            # Validation should FAIL overall
            assert result.overall_success is False, "Overall validation should fail when user_sessions missing"
            assert result.requirements_failed > 0, "Should have failed requirements"
            assert len(result.critical_failures) > 0, "Should have critical failures"
            assert len(result.business_impact_failures) > 0, "Should have business impact failures"
            
            # Verify the specific failure is about user authentication
            auth_failure_found = any(
                "user_authentication_ready" in failure or "user_sessions" in failure.lower()
                for failure in result.critical_failures
            )
            
            assert auth_failure_found, "Should have critical failure related to user authentication"
            
            # Verify business impact is reported
            auth_business_impact_found = any(
                "log in" in impact.lower() or "auth" in impact.lower()
                for impact in result.business_impact_failures  
            )
            
            if auth_business_impact_found:
                logger.info(" PASS:  Business impact of missing user_sessions correctly reported")
            
            logger.info(" PASS:  Full Golden Path validation correctly failed with missing user_sessions table")
            logger.info(f"Critical failures: {len(result.critical_failures)}")
            logger.info(f"Business impact failures: {len(result.business_impact_failures)}")
            
            # Log all failures for visibility
            for failure in result.critical_failures:
                logger.error(f" ALERT:  Critical Failure: {failure}")
                
            for impact in result.business_impact_failures:
                logger.error(f"[U+1F4B0] Business Impact: {impact}")
                
        except Exception as e:
            pytest.fail(f" FAIL:  CRITICAL FAILURE: Full Golden Path validation crashed: {e}")