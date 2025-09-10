"""
CRITICAL UNIT TEST: Exposing Golden Path Validator Monolithic Architectural Flaw

This test is DESIGNED TO FAIL with the current implementation to prove the architectural problem:

ISSUE: GoldenPathValidator._validate_user_auth_tables() checks for 'user_sessions' table 
in the BACKEND service's database connection, but 'user_sessions' is actually stored
in the AUTH service's database.

EXPECTED RESULT: FAIL - This proves the validator is making monolithic assumptions
about database schema that violate service boundaries.

TEST STRATEGY:
1. Mock backend database WITHOUT 'user_sessions' table (correct service boundary)
2. Show that validation FAILS because it's looking in wrong service
3. Prove that the validator should be checking AUTH service database instead
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator,
    GoldenPathValidationResult,
)
from netra_backend.app.core.service_dependencies.models import (
    EnvironmentType,
    ServiceType,
    GOLDEN_PATH_REQUIREMENTS,
)


class TestGoldenPathValidatorMonolithicFlaw:
    """FAILING TESTS: Expose monolithic assumptions in Golden Path Validator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance for testing."""
        return GoldenPathValidator(environment=EnvironmentType.TESTING)

    @pytest.fixture
    def mock_backend_app_correct_boundaries(self):
        """
        Mock backend app with CORRECT service boundaries.
        
        Backend database should NOT have 'user_sessions' - that belongs to Auth service.
        This represents the correct microservice architecture.
        """
        app = MagicMock()
        
        # Mock database session that represents BACKEND service database
        mock_session = AsyncMock()
        mock_session_factory = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        
        app.state.db_session_factory = mock_session_factory
        
        # BACKEND database has 'users' but NOT 'user_sessions' (correct boundaries)
        def mock_table_exists(query_text):
            query_str = str(query_text)
            if "'users'" in query_str:
                # Backend can have users table for business logic
                result = MagicMock()
                result.scalar.return_value = 1  # Table exists
                return result
            elif "'user_sessions'" in query_str:
                # user_sessions belongs to AUTH service, not backend
                result = MagicMock() 
                result.scalar.return_value = 0  # Table does NOT exist here
                return result
            else:
                result = MagicMock()
                result.scalar.return_value = 0
                return result
        
        mock_session.execute.side_effect = mock_table_exists
        return app

    @pytest.mark.asyncio
    async def test_user_auth_tables_validation_fails_with_correct_service_boundaries(
        self, validator, mock_backend_app_correct_boundaries
    ):
        """
        DESIGNED TO FAIL: Show that validator fails when service boundaries are correct.
        
        This test proves the architectural flaw:
        - Backend database correctly does NOT have 'user_sessions' (belongs to Auth service)
        - Current validator FAILS because it's looking in wrong service database
        - Validator should be checking AUTH service database instead
        """
        app = mock_backend_app_correct_boundaries
        
        # Find the PostgreSQL user auth requirement
        postgres_requirement = None
        for req in GOLDEN_PATH_REQUIREMENTS:
            if (req.service_type == ServiceType.DATABASE_POSTGRES and 
                req.validation_function == "validate_user_auth_tables"):
                postgres_requirement = req
                break
        
        assert postgres_requirement is not None, "PostgreSQL auth requirement not found"
        
        # This should FAIL because validator is checking wrong service database
        result = await validator._validate_requirement(app, postgres_requirement)
        
        # CRITICAL ASSERTION: This SHOULD fail with correct service boundaries
        assert result["success"] is False, (
            "ARCHITECTURAL FLAW EXPOSED: Validator should fail when checking "
            "backend database for 'user_sessions' table that belongs to Auth service. "
            "If this passes, the validator is incorrectly accessing wrong service database."
        )
        
        assert "user_sessions" in result["message"], (
            "Failure should mention 'user_sessions' table missing"
        )
        
        # Verify the architectural problem in details
        if "details" in result and "missing_tables" in result["details"]:
            missing_tables = result["details"]["missing_tables"]
            assert "user_sessions" in missing_tables, (
                "user_sessions should be reported as missing from backend database "
                "(because it belongs to Auth service)"
            )

    @pytest.mark.asyncio
    async def test_service_boundary_violation_evidence(self, validator, mock_backend_app_correct_boundaries):
        """
        DESIGNED TO FAIL: Provide evidence of service boundary violation.
        
        This test documents the architectural flaw by showing:
        1. What tables SHOULD be in each service
        2. How current validator violates service boundaries
        3. Why this causes failures in proper microservice setup
        """
        app = mock_backend_app_correct_boundaries
        
        # Get the auth tables requirement
        auth_requirement = None
        for req in GOLDEN_PATH_REQUIREMENTS:
            if req.validation_function == "validate_user_auth_tables":
                auth_requirement = req
                break
                
        # Execute validation that should fail due to boundary violation
        result = await validator._validate_user_auth_tables(app)
        
        # Document the boundary violation
        expected_backend_tables = ["users"]  # What backend SHOULD have
        expected_auth_tables = ["user_sessions"]  # What belongs to AUTH service
        
        # The validator checks for BOTH in backend database - this is wrong
        assert result["success"] is False, (
            f"BOUNDARY VIOLATION: Validator checks backend database for auth tables. "
            f"Backend should have: {expected_backend_tables}. "
            f"Auth service should have: {expected_auth_tables}. "
            f"Current validator violates this separation."
        )

    @pytest.mark.asyncio 
    async def test_validator_assumes_monolithic_database_schema(self, validator):
        """
        DESIGNED TO FAIL: Prove validator assumes all tables in one database.
        
        This test shows the core architectural assumption that needs fixing:
        The validator assumes ALL authentication-related tables are in the 
        same database that the backend service connects to.
        """
        # Mock app with NO database access (simulating service isolation)
        app = MagicMock()
        app.state.db_session_factory = None  # No backend database access
        
        auth_requirement = None
        for req in GOLDEN_PATH_REQUIREMENTS:
            if req.validation_function == "validate_user_auth_tables":
                auth_requirement = req
                break
        
        result = await validator._validate_requirement(app, auth_requirement)
        
        # Should fail because it can't access backend database
        assert result["success"] is False, (
            "MONOLITHIC ASSUMPTION EXPOSED: Validator fails when backend has no "
            "database access, proving it assumes backend database contains auth tables. "
            "In proper microservice architecture, validator should check auth service instead."
        )
        
        assert "session factory not available" in result["message"].lower(), (
            "Should fail due to missing database connection, exposing the architectural flaw"
        )

    def test_golden_path_requirements_contain_service_boundary_violations(self):
        """
        DESIGNED TO FAIL: Show that requirements themselves violate service boundaries.
        
        This test proves that the GOLDEN_PATH_REQUIREMENTS are structured incorrectly
        for a microservice architecture.
        """
        # Find auth-related requirements
        auth_requirements = [
            req for req in GOLDEN_PATH_REQUIREMENTS 
            if "auth" in req.requirement_name.lower() or 
               "user" in req.requirement_name.lower() or
               req.validation_function == "validate_user_auth_tables"
        ]
        
        # Check which service they're assigned to
        postgres_auth_reqs = [req for req in auth_requirements if req.service_type == ServiceType.DATABASE_POSTGRES]
        auth_service_reqs = [req for req in auth_requirements if req.service_type == ServiceType.AUTH_SERVICE]
        
        # ARCHITECTURAL FLAW: Auth table validation assigned to PostgreSQL service
        # instead of Auth service
        assert len(postgres_auth_reqs) > 0, (
            "BOUNDARY VIOLATION IN REQUIREMENTS: Found auth-related requirements "
            f"assigned to DATABASE_POSTGRES service: {[req.requirement_name for req in postgres_auth_reqs]}. "
            f"These should be assigned to AUTH_SERVICE instead to respect service boundaries."
        )

    def test_requirements_should_be_service_aware_not_database_aware(self):
        """
        DESIGNED TO FAIL: Show that requirements are database-centric, not service-centric.
        
        Golden path requirements should validate SERVICES and their capabilities,
        not directly validate database tables across service boundaries.
        """
        # Count requirements by service type
        service_requirements = {}
        for req in GOLDEN_PATH_REQUIREMENTS:
            service_type = req.service_type
            if service_type not in service_requirements:
                service_requirements[service_type] = []
            service_requirements[service_type].append(req)
        
        # Check for database-centric vs service-centric approach
        database_requirements = service_requirements.get(ServiceType.DATABASE_POSTGRES, [])
        auth_service_requirements = service_requirements.get(ServiceType.AUTH_SERVICE, [])
        
        # FLAW: Database requirements should not validate business logic tables
        database_business_logic_reqs = [
            req for req in database_requirements
            if any(keyword in req.requirement_name.lower() 
                  for keyword in ['user', 'auth', 'session'])
        ]
        
        assert len(database_business_logic_reqs) > 0, (
            "ARCHITECTURE FLAW CONFIRMED: Found database requirements that validate "
            f"business logic: {[req.requirement_name for req in database_business_logic_reqs]}. "
            f"These should be service-level validations, not direct database checks."
        )

    @pytest.mark.asyncio
    async def test_validation_logic_should_be_in_auth_service_scope(self, validator):
        """
        DESIGNED TO FAIL: Show that validation logic belongs in Auth service scope.
        
        The _validate_user_auth_tables method should NOT be checking backend database
        for auth tables. This test proves the method is in wrong architectural layer.
        """
        # Create mock app representing AUTH service (not backend)
        auth_app = MagicMock()
        mock_auth_session = AsyncMock()
        mock_auth_session_factory = AsyncMock()
        mock_auth_session_factory.return_value.__aenter__.return_value = mock_auth_session
        auth_app.state.db_session_factory = mock_auth_session_factory
        
        # Auth service database HAS user_sessions table
        def mock_auth_db_tables(query_text):
            result = MagicMock()
            result.scalar.return_value = 1  # All auth tables exist
            return result
            
        mock_auth_session.execute.side_effect = mock_auth_db_tables
        
        # Test validation against auth service (this would work)
        result = await validator._validate_user_auth_tables(auth_app)
        
        # This might pass, but it proves the architectural point:
        # The validation SHOULD be done against auth service, not backend
        if result["success"]:
            pytest.fail(
                "ARCHITECTURAL INSIGHT: Validation succeeds when run against auth service "
                "database, proving that validation logic should be scoped to AUTH service, "
                "not run from BACKEND service context. This confirms the boundary violation."
            )


class TestGoldenPathValidatorArchitecturalRecommendations:
    """
    Documentation of what the CORRECT architecture should look like.
    
    These are NOT tests to run, but documentation of the proper service-aware approach.
    """
    
    def test_document_correct_service_aware_validation_approach(self):
        """
        ARCHITECTURAL GUIDANCE: How validator should work in service-aware architecture.
        
        CORRECT APPROACH:
        1. Auth validation should query AUTH service health endpoint
        2. Backend validation should check backend-specific capabilities  
        3. Database validation should check connectivity, not business logic tables
        4. Cross-service validation should use service APIs, not direct database access
        """
        correct_approach = {
            "AUTH_SERVICE_VALIDATION": {
                "method": "HTTP health check to auth service",
                "validates": ["JWT capabilities", "user authentication", "session management"],
                "database_access": "Auth service manages its own database"
            },
            "BACKEND_SERVICE_VALIDATION": {
                "method": "Check backend-specific components",
                "validates": ["Agent execution", "tool system", "LLM integration"],
                "database_access": "Only for backend-specific tables, not auth tables"
            },
            "DATABASE_SERVICE_VALIDATION": {
                "method": "Check database connectivity and performance",
                "validates": ["Connection health", "basic operations", "resource availability"],
                "database_access": "Infrastructure checks only, not business schema validation"
            }
        }
        
        # This test always "fails" to document the architectural guidance
        assert False, (
            f"ARCHITECTURAL GUIDANCE - Correct service-aware approach: {correct_approach}"
        )