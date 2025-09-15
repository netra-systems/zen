
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
INTEGRATION TEST: Golden Path Validator Service Boundary Violations

This test is DESIGNED TO FAIL to expose how the Golden Path Validator
violates microservice boundaries by directly accessing database tables
that belong to different services.

ISSUE BEING EXPOSED:
- Backend service validator checks for 'user_sessions' table in backend database
- 'user_sessions' table belongs to Auth service, not Backend service  
- This creates tight coupling between services and fails in proper microservice setup

EXPECTED RESULT: FAIL - Proves that validator makes incorrect assumptions
about database schema across service boundaries.

KEY INTEGRATION POINTS TESTED:
1. Backend service attempting to validate Auth service concerns
2. Database connections being used across service boundaries
3. Validation logic assuming monolithic database schema
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from netra_backend.app.core.service_dependencies.golden_path_validator import (
    GoldenPathValidator,
    GoldenPathValidationResult,
)
from netra_backend.app.core.service_dependencies.models import (
    EnvironmentType,
    ServiceType,
    GOLDEN_PATH_REQUIREMENTS,
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestGoldenPathServiceBoundaries:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """FAILING INTEGRATION TESTS: Expose service boundary violations."""

    @pytest.fixture
    def validator(self):
        """Create validator for integration testing."""
        return GoldenPathValidator()

    @pytest.fixture
    def backend_service_app_mock(self):
        """
        Mock of Backend service app with realistic service boundaries.
        
        Backend service should:
        - Have access to its own database tables
        - NOT have access to Auth service tables
        - Validate only backend-specific functionality
        """
        app = MagicMock()
        
        # Mock backend database session (realistic separation)
        backend_session = AsyncMock()
        backend_session_factory = AsyncMock()
        backend_session_factory.return_value.__aenter__.return_value = backend_session
        
        app.state.db_session_factory = backend_session_factory
        
        # Backend database schema (what SHOULD exist in backend)
        backend_tables = {
            'agent_executions': True,
            'chat_threads': True, 
            'agent_results': True,
            'tool_usage_logs': True,
            # Auth tables should NOT be here
            'users': False,           # Belongs to Auth service
            'user_sessions': False,   # Belongs to Auth service
            'auth_tokens': False,     # Belongs to Auth service
        }
        
        def mock_backend_db_query(query_text):
            """Simulate backend database that doesn't have auth tables."""
            query_str = str(query_text).lower()
            
            result = MagicMock()
            
            # Extract table name from query
            for table_name, exists in backend_tables.items():
                if f"'{table_name}'" in query_str or f'"{table_name}"' in query_str:
                    result.scalar.return_value = 1 if exists else 0
                    return result
            
            # Unknown table
            result.scalar.return_value = 0
            return result
            
        backend_session.execute.side_effect = mock_backend_db_query
        return app

    @pytest.fixture 
    def auth_service_app_mock(self):
        """
        Mock of Auth service app with proper auth tables.
        
        This represents what auth validation SHOULD check against.
        """
        app = MagicMock()
        
        auth_session = AsyncMock()
        auth_session_factory = AsyncMock()
        auth_session_factory.return_value.__aenter__.return_value = auth_session
        
        app.state.db_session_factory = auth_session_factory
        
        # Auth service database schema
        auth_tables = {
            'users': True,
            'user_sessions': True,
            'auth_tokens': True,
            'oauth_credentials': True,
            # Backend tables should NOT be here
            'agent_executions': False,
            'chat_threads': False,
        }
        
        def mock_auth_db_query(query_text):
            query_str = str(query_text).lower()
            result = MagicMock()
            
            for table_name, exists in auth_tables.items():
                if f"'{table_name}'" in query_str:
                    result.scalar.return_value = 1 if exists else 0
                    return result
            
            result.scalar.return_value = 0
            return result
            
        auth_session.execute.side_effect = mock_auth_db_query
        return app

    @pytest.mark.asyncio
    async def test_backend_service_cannot_validate_auth_tables(
        self, validator, backend_service_app_mock
    ):
        """
        DESIGNED TO FAIL: Backend service validation fails when auth tables missing.
        
        This proves the boundary violation:
        - Backend validator tries to find auth tables in backend database
        - Auth tables don't exist in backend database (correct separation)
        - Validation fails, exposing the architectural flaw
        """
        backend_app = backend_service_app_mock
        
        # Find PostgreSQL auth requirement (incorrectly assigned to DATABASE_POSTGRES)
        auth_requirement = None
        for req in GOLDEN_PATH_REQUIREMENTS:
            if req.validation_function == "validate_user_auth_tables":
                auth_requirement = req
                break
        
        assert auth_requirement is not None
        
        # Execute validation that SHOULD fail due to service boundary violation
        result = await validator._validate_requirement(backend_app, auth_requirement)
        
        # CRITICAL: This should fail because backend shouldn't have auth tables
        assert result["success"] is False, (
            "BOUNDARY VIOLATION CONFIRMED: Backend service validation fails because "
            "it's looking for auth tables in backend database. Auth tables belong "
            "to Auth service, not Backend service."
        )
        
        # Verify specific tables that are missing (and should be missing)
        if "details" in result and "missing_tables" in result["details"]:
            missing_tables = result["details"]["missing_tables"]
            expected_missing_auth_tables = ["user_sessions", "users"]  # Should be in Auth service
            
            for table in expected_missing_auth_tables:
                assert table in missing_tables, (
                    f"Table '{table}' should be reported as missing from backend database "
                    f"because it belongs to Auth service"
                )

    @pytest.mark.asyncio
    async def test_auth_validation_should_target_auth_service(
        self, validator, auth_service_app_mock
    ):
        """
        DESIGNED TO SUCCEED: Show that auth tables exist in Auth service.
        
        This test proves that the tables DO exist, but in the correct service.
        When combined with previous test, this proves the boundary violation.
        """
        auth_app = auth_service_app_mock
        
        # Test the same validation logic against Auth service database
        result = await validator._validate_user_auth_tables(auth_app)
        
        # This SHOULD succeed because auth service has the auth tables
        assert result["success"] is True, (
            "AUTH SERVICE VALIDATION WORKS: When checking auth service database, "
            "auth tables are found. This proves the tables exist but in the correct service."
        )
        
        # Document what this proves about the architecture
        if result["success"]:
            details = result.get("details", {})
            tables = details.get("tables", {})
            
            auth_tables_found = ["users", "user_sessions"]
            for table in auth_tables_found:
                if table in tables:
                    assert tables[table] is True, (
                        f"Table '{table}' should exist in auth service database"
                    )

    @pytest.mark.asyncio
    async def test_service_validation_cross_boundary_dependency(
        self, validator, backend_service_app_mock
    ):
        """
        DESIGNED TO FAIL: Demonstrate cross-service dependency problem.
        
        The issue: Backend service validation depends on Auth service database tables.
        This creates incorrect coupling between services.
        """
        backend_app = backend_service_app_mock
        
        # List services that backend validation should validate
        backend_requirements = [
            req for req in GOLDEN_PATH_REQUIREMENTS
            if req.service_type == ServiceType.BACKEND_SERVICE or
            req.service_type == ServiceType.DATABASE_POSTGRES  # Problem: includes auth tables
        ]
        
        # Run golden path validation for backend-related services
        services_to_validate = [ServiceType.DATABASE_POSTGRES, ServiceType.BACKEND_SERVICE]
        result = await validator.validate_golden_path_services(backend_app, services_to_validate)
        
        # This SHOULD fail due to cross-service boundary violations
        assert result.overall_success is False, (
            "CROSS-SERVICE DEPENDENCY EXPOSED: Backend service validation fails because "
            "it tries to validate Auth service concerns (user_sessions table). "
            "Services should validate only their own responsibilities."
        )
        
        # Check that failure is specifically due to auth table validation
        auth_related_failures = [
            failure for failure in result.critical_failures
            if any(keyword in failure.lower() for keyword in ['user', 'auth', 'session'])
        ]
        
        assert len(auth_related_failures) > 0, (
            "Should have auth-related failures when backend tries to validate auth concerns"
        )

    @pytest.mark.asyncio 
    async def test_monolithic_assumption_in_validation_requirements(self, validator):
        """
        DESIGNED TO FAIL: Expose monolithic assumptions in requirement definitions.
        
        The GOLDEN_PATH_REQUIREMENTS incorrectly assign auth validation to 
        DATABASE_POSTGRES service instead of AUTH_SERVICE.
        """
        # Check how requirements are distributed across services
        requirements_by_service = {}
        for req in GOLDEN_PATH_REQUIREMENTS:
            service = req.service_type
            if service not in requirements_by_service:
                requirements_by_service[service] = []
            requirements_by_service[service].append(req)
        
        # Check for boundary violations in requirement assignments
        postgres_requirements = requirements_by_service.get(ServiceType.DATABASE_POSTGRES, [])
        auth_service_requirements = requirements_by_service.get(ServiceType.AUTH_SERVICE, [])
        
        # Find auth-related requirements assigned to database service
        postgres_auth_requirements = [
            req for req in postgres_requirements
            if any(keyword in req.requirement_name.lower() 
                  for keyword in ['user', 'auth', 'session'])
        ]
        
        # BOUNDARY VIOLATION: Auth requirements assigned to database service
        assert len(postgres_auth_requirements) > 0, (
            f"MONOLITHIC ASSUMPTION IN REQUIREMENTS: Found {len(postgres_auth_requirements)} "
            f"auth-related requirements assigned to DATABASE_POSTGRES service: "
            f"{[req.requirement_name for req in postgres_auth_requirements]}. "
            f"These should be assigned to AUTH_SERVICE to respect service boundaries."
        )
        
        # Verify that Auth service has fewer requirements than it should
        assert len(auth_service_requirements) < len(postgres_auth_requirements) + len(auth_service_requirements), (
            "AUTH_SERVICE should have more requirements if boundaries were correct"
        )

    def test_requirement_assignment_violates_service_boundaries(self):
        """
        DESIGNED TO FAIL: Document requirement assignment boundary violations.
        
        This test catalogs all the boundary violations in GOLDEN_PATH_REQUIREMENTS
        to provide clear evidence of the architectural problem.
        """
        boundary_violations = []
        
        for req in GOLDEN_PATH_REQUIREMENTS:
            service = req.service_type
            req_name = req.requirement_name
            validation_func = req.validation_function
            
            # Check for specific boundary violations
            if (service == ServiceType.DATABASE_POSTGRES and 
                any(keyword in req_name.lower() for keyword in ['user', 'auth', 'session'])):
                boundary_violations.append({
                    'requirement': req_name,
                    'assigned_to': service.value,
                    'should_be_assigned_to': ServiceType.AUTH_SERVICE.value,
                    'violation_type': 'auth_logic_in_database_service',
                    'validation_function': validation_func
                })
            
            if (service == ServiceType.BACKEND_SERVICE and 
                'auth' in req_name.lower()):
                boundary_violations.append({
                    'requirement': req_name, 
                    'assigned_to': service.value,
                    'should_be_assigned_to': ServiceType.AUTH_SERVICE.value,
                    'violation_type': 'auth_logic_in_backend_service',
                    'validation_function': validation_func
                })
        
        # This test fails to document the violations
        assert len(boundary_violations) == 0, (
            f"SERVICE BOUNDARY VIOLATIONS FOUND: {boundary_violations}. "
            f"These requirements are assigned to wrong services, creating coupling "
            f"between services and preventing proper microservice isolation."
        )

    @pytest.mark.asyncio
    async def test_integration_reveals_service_coupling_problems(
        self, validator, backend_service_app_mock
    ):
        """
        DESIGNED TO FAIL: Show how current design creates service coupling.
        
        Integration test proving that services cannot be validated independently
        due to incorrect cross-service dependencies in validation logic.
        """
        backend_app = backend_service_app_mock
        
        # Try to validate backend service in isolation
        backend_only_services = [ServiceType.BACKEND_SERVICE]
        
        # This should work for backend-specific validation
        backend_result = await validator.validate_golden_path_services(
            backend_app, backend_only_services
        )
        
        # Now try to validate database requirements that include auth tables
        database_services = [ServiceType.DATABASE_POSTGRES]
        database_result = await validator.validate_golden_path_services(
            backend_app, database_services
        )
        
        # The database validation should fail because it's looking for auth tables
        # in backend database (wrong service boundary)
        assert database_result.overall_success is False, (
            "SERVICE COUPLING EXPOSED: Database validation fails because it's "
            "coupled to auth service tables. This prevents independent service validation."
        )
        
        # Document the coupling problem
        coupling_evidence = {
            'backend_service_independent': backend_result.overall_success,
            'database_service_coupled_to_auth': not database_result.overall_success,
            'coupling_reason': 'database validation checks auth tables'
        }
        
        assert coupling_evidence['database_service_coupled_to_auth'] is False, (
            f"SERVICE COUPLING DETECTED: {coupling_evidence}. "
            f"Services cannot be validated independently due to incorrect dependencies."
        )


class TestCorrectServiceAwareArchitecture:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    Documentation tests showing the CORRECT service-aware approach.
    
    These tests document how the architecture SHOULD work after refactoring.
    """
    
    def test_correct_service_responsibility_mapping(self):
        """Document correct service responsibility mapping."""
        correct_responsibilities = {
            ServiceType.AUTH_SERVICE: [
                "user_authentication_ready",
                "jwt_validation_ready", 
                "session_management_ready",
                "oauth_integration_ready"
            ],
            ServiceType.BACKEND_SERVICE: [
                "agent_execution_ready",
                "tool_system_ready",
                "llm_integration_ready",
                "business_logic_ready"
            ],
            ServiceType.DATABASE_POSTGRES: [
                "database_connectivity_ready",
                "database_performance_ready",
                "connection_pool_ready"
            ],
            ServiceType.WEBSOCKET_SERVICE: [
                "realtime_communication_ready",
                "websocket_events_ready",
                "message_routing_ready"
            ]
        }
        
        # Always "fails" to document the correct approach
        assert False, (
            f"CORRECT SERVICE RESPONSIBILITIES: Each service should validate only "
            f"its own concerns: {correct_responsibilities}"
        )

    def test_correct_validation_approach_documentation(self):
        """Document how service-aware validation should work."""
        correct_approach = {
            "principle": "Services validate through APIs, not direct database access",
            "auth_validation": {
                "method": "HTTP call to auth service health endpoint",
                "validates": ["JWT creation", "User authentication", "Session management"],
                "no_direct_db": "Auth service manages its own database schema"
            },
            "backend_validation": {
                "method": "Check backend components and connections",
                "validates": ["Agent system", "Tool execution", "LLM connectivity"],
                "db_access": "Only for backend-specific tables"
            },
            "cross_service": {
                "method": "Service-to-service health checks",
                "validates": ["Service availability", "API responsiveness"],
                "no_schema_coupling": "No direct database access across services"
            }
        }
        
        # Always "fails" to document the approach
        assert False, (
            f"CORRECT VALIDATION ARCHITECTURE: {correct_approach}"
        )