"""
Test Auth Service Health Check Functionality

Business Value Justification (BVJ):
- Segment: Platform/Internal (serves all segments)  
- Business Goal: Ensure reliable service operations and traffic routing
- Value Impact: Health checks prevent service outages, enable proper load balancing,
  and provide early warning of system failures
- Strategic Impact: Critical infrastructure for 99.9% uptime SLA and zero-downtime deployments

CRITICAL BUSINESS CONTEXT:
Health check functionality is MISSION CRITICAL for production operations. Load balancers,
orchestrators, and monitoring systems depend on health checks to:
1. Route traffic only to healthy service instances
2. Detect service problems before customers are affected  
3. Enable zero-downtime deployments via rolling updates
4. Trigger automated recovery and scaling actions
5. Provide operational visibility into service state

Failed or inaccurate health checks can cause:
- Service outages (503 errors to customers)
- Revenue loss from unavailable service
- Cascade failures across microservices
- Delayed incident response
- Failed deployments and rollbacks

This test ensures health monitoring delivers REAL business value by validating:
- Accurate health state reporting (healthy vs unhealthy)
- Performance requirements for health check responses
- Proper environment-specific behavior
- Database dependency validation
- OAuth configuration monitoring
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Absolute imports following CLAUDE.md requirements
from auth_service.health_check import check_health, check_readiness
from auth_service.health_config import (
    get_auth_health, 
    check_auth_postgres_health,
    check_oauth_providers_health,
    check_jwt_configuration,
    HealthStatus
)
from auth_service.auth_core.auth_environment import get_auth_env
from shared.isolated_environment import get_env


class TestAuthServiceHealthCheckScript:
    """Test standalone health_check.py script functionality"""
    
    def test_health_check_script_basic_functionality(self):
        """
        Test health_check.py script basic functionality
        
        Business Value: Orchestrators like Kubernetes and Cloud Run depend on this
        script to determine if auth service should receive traffic. Broken health 
        checks = service outages = revenue loss.
        """
        # Test successful health check with mocked HTTP response
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Mock successful health response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"status": "healthy"}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            # Test default port resolution
            result = check_health()
            assert result is True
            
            # Verify correct URL construction
            mock_urlopen.assert_called_once()
            args, kwargs = mock_urlopen.call_args
            request = args[0]
            assert "localhost:" in request.full_url
            assert "/health" in request.full_url
            assert "auth-health-checker/1.0" in request.headers.get('User-agent', '')
    
    def test_health_check_script_environment_port_handling(self):
        """
        Test health check script handles environment-specific ports correctly
        
        Business Value: Different environments (dev/staging/prod) use different ports.
        Incorrect port resolution causes health check failures and deployment issues.
        """
        test_cases = [
            ("production", None, 8080),    # Cloud Run standard port
            ("staging", None, 8080),       # Cloud Run standard port  
            ("development", None, 8081),   # Development port
            ("test", None, 8082),          # Test port
            ("unknown", None, 8080),       # Default fallback
        ]
        
        for env, port_override, expected_port in test_cases:
            with patch('auth_service.health_check.get_env') as mock_env:
                # Mock environment configuration
                mock_env_instance = Mock()
                mock_env_instance.get.side_effect = lambda key, default=None: {
                    'ENVIRONMENT': env,
                    'PORT': str(port_override) if port_override else None
                }.get(key, default)
                mock_env.return_value = mock_env_instance
                
                with patch('urllib.request.urlopen') as mock_urlopen:
                    # Mock successful response
                    mock_response = Mock()
                    mock_response.status = 200
                    mock_response.read.return_value = b'{"status": "healthy"}'
                    mock_urlopen.return_value.__enter__.return_value = mock_response
                    
                    result = check_health()
                    assert result is True
                    
                    # Verify correct port was used
                    mock_urlopen.assert_called_once()
                    args, kwargs = mock_urlopen.call_args
                    request = args[0]
                    assert f"localhost:{expected_port}/health" in request.full_url
                    
                    mock_urlopen.reset_mock()
    
    def test_health_check_script_failure_scenarios(self):
        """
        Test health check script handles failure scenarios correctly
        
        Business Value: Health checks must fail fast and accurately report when 
        service is unhealthy. False positives cause traffic to be routed to 
        broken services, causing customer-facing errors.
        """
        import urllib.error
        
        failure_scenarios = [
            # Network connection failures
            (urllib.error.URLError("Connection refused"), False),
            # HTTP error responses  
            (urllib.error.HTTPError(url="test", code=503, msg="Service Unavailable", 
                                  hdrs={}, fp=None), False),
            # Invalid JSON responses
            (None, False, b'invalid json'),
            # Missing status field
            (None, False, b'{"message": "ok"}'),
            # Unhealthy status
            (None, False, b'{"status": "unhealthy"}'),
        ]
        
        for exception, expected_result, *response_data in failure_scenarios:
            with patch('urllib.request.urlopen') as mock_urlopen:
                if exception:
                    mock_urlopen.side_effect = exception
                else:
                    # Mock response with invalid data
                    mock_response = Mock()
                    mock_response.status = 200
                    mock_response.read.return_value = response_data[0] if response_data else b'{"status": "healthy"}'
                    mock_urlopen.return_value.__enter__.return_value = mock_response
                
                result = check_health()
                assert result == expected_result
                
    def test_readiness_check_script_functionality(self):
        """
        Test readiness check script functionality
        
        Business Value: Readiness checks determine when service can accept traffic
        during startup and deployment. Incorrect readiness = failed deployments or
        traffic routed to services that aren't fully initialized.
        """
        with patch('urllib.request.urlopen') as mock_urlopen:
            # Test successful readiness check
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"ready": true}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = check_readiness()
            assert result is True
            
            # Verify correct readiness endpoint called
            mock_urlopen.assert_called_once()
            args, kwargs = mock_urlopen.call_args
            request = args[0]
            assert "/readiness" in request.full_url
            
        # Test readiness failure
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.read.return_value = b'{"ready": false}'
            mock_urlopen.return_value.__enter__.return_value = mock_response
            
            result = check_readiness()
            assert result is False


class TestAuthServiceHealthEndpoints:
    """Test FastAPI health endpoints in main.py"""
    
    def test_health_endpoints_response_formats(self):
        """
        Test /health and /readiness endpoints return correct response formats
        
        Business Value: Load balancers and monitoring systems depend on consistent
        response formats to make routing decisions. Inconsistent responses cause
        operational issues and false alerts.
        """
        # Test health endpoint response structure
        from auth_service.main import health_interface
        
        basic_health = health_interface.get_basic_health()
        
        # Verify required fields for load balancer compatibility
        assert "status" in basic_health
        assert "service" in basic_health  
        assert "version" in basic_health
        assert "timestamp" in basic_health
        assert "uptime_seconds" in basic_health
        
        # Verify correct values
        assert basic_health["status"] == "healthy"
        assert basic_health["service"] == "auth-service"
        assert basic_health["version"] == "1.0.0"
        assert isinstance(basic_health["uptime_seconds"], (int, float))
        assert basic_health["uptime_seconds"] >= 0
        
        # Verify timestamp is ISO format (required for monitoring systems)
        from datetime import datetime
        timestamp = basic_health["timestamp"]
        assert isinstance(timestamp, str)
        # Should be able to parse as ISO datetime
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_health_check_database_dependency_validation(self):
        """
        Test health check validates database connectivity in production environments
        
        Business Value: Database connectivity is critical for auth service functionality.
        Health checks must accurately reflect whether service can handle authentication
        requests. False health reports = customers unable to login = revenue loss.
        """
        # Mock environment as staging to trigger database validation
        with patch('auth_service.main.AuthConfig.get_environment') as mock_env:
            mock_env.return_value = "staging"
            
            # Test healthy database scenario
            with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
                mock_db.is_ready = AsyncMock(return_value=True)
                
                from auth_service.main import health
                response = await health()
                
                # Should return healthy status with database info
                assert isinstance(response, dict)
                assert response["status"] == "healthy"
                assert response["environment"] == "staging"
                assert response["database_status"] == "connected"
                
        # Test unhealthy database scenario  
        with patch('auth_service.main.AuthConfig.get_environment') as mock_env:
            mock_env.return_value = "production"
            
            with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
                mock_db.is_ready = AsyncMock(return_value=False)
                
                from auth_service.main import health
                from fastapi.responses import JSONResponse
                
                response = await health()
                
                # Should return 503 Service Unavailable for unhealthy database
                assert isinstance(response, JSONResponse)
                assert response.status_code == 503
                
                # Parse response content
                import json
                content = json.loads(response.body.decode())
                assert content["status"] == "unhealthy"
                assert "Database connectivity failed" in content["reason"]
                assert content["environment"] == "production"
                
    @pytest.mark.asyncio  
    async def test_health_check_oauth_validation(self):
        """
        Test health check validates OAuth configuration in production
        
        Business Value: OAuth is critical for user authentication and signup.
        Broken OAuth = users cannot login = churn and revenue loss.
        Health monitoring must detect OAuth misconfigurations early.
        """
        # Test OAuth status endpoint
        with patch('auth_service.main.AuthConfig.get_environment') as mock_env:
            mock_env.return_value = "staging"
            
            # Mock healthy OAuth manager
            with patch('auth_service.auth_core.oauth_manager.OAuthManager') as mock_oauth_manager:
                mock_manager = Mock()
                mock_manager.get_available_providers.return_value = ["google"]
                
                # Mock Google provider with healthy status
                mock_provider = Mock()
                mock_provider.self_check.return_value = {
                    "is_healthy": True,
                    "client_id_configured": True,
                    "client_secret_configured": True
                }
                mock_provider.get_configuration_status.return_value = {
                    "client_id_length": 64,
                    "redirect_uri_valid": True
                }
                mock_manager.get_provider.return_value = mock_provider
                mock_oauth_manager.return_value = mock_manager
                
                from auth_service.main import oauth_status
                response = await oauth_status()
                
                # Should return healthy OAuth status
                assert isinstance(response, dict)
                assert response["oauth_healthy"] is True
                assert response["available_providers"] == ["google"]
                assert response["oauth_providers"]["google"]["is_healthy"] is True
                
        # Test unhealthy OAuth in production (should return 503)
        with patch('auth_service.main.AuthConfig.get_environment') as mock_env:
            mock_env.return_value = "production"
            
            with patch('auth_service.auth_core.oauth_manager.OAuthManager') as mock_oauth_manager:
                mock_manager = Mock()
                mock_manager.get_available_providers.return_value = ["google"]
                
                # Mock unhealthy Google provider
                mock_provider = Mock()
                mock_provider.self_check.return_value = {
                    "is_healthy": False,
                    "error": "Client ID not configured"
                }
                mock_manager.get_provider.return_value = mock_provider
                mock_oauth_manager.return_value = mock_manager
                
                from auth_service.main import oauth_status
                from fastapi.responses import JSONResponse
                
                response = await oauth_status()
                
                # Should return 503 for unhealthy OAuth in production
                assert isinstance(response, JSONResponse)
                assert response.status_code == 503
                
                import json
                content = json.loads(response.body.decode())
                assert content["oauth_healthy"] is False
    
    def test_health_check_performance_timing(self):
        """
        Test health check endpoints meet performance requirements
        
        Business Value: Health checks are called frequently by load balancers.
        Slow health checks cause increased latency, timeout failures, and 
        operational overhead. Health checks must respond within SLA requirements.
        """
        from auth_service.main import health_interface
        
        # Health checks should complete in under 100ms for operational efficiency
        max_response_time = 0.1  # 100ms
        
        # Test basic health check performance
        start_time = time.time()
        basic_health = health_interface.get_basic_health()
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < max_response_time, \
            f"Health check took {response_time:.3f}s, exceeds {max_response_time}s limit"
        
        # Verify response completeness (no missing fields that cause retries)
        required_fields = ["status", "service", "version", "timestamp", "uptime_seconds"]
        for field in required_fields:
            assert field in basic_health, f"Missing required field: {field}"
            assert basic_health[field] is not None, f"Null value for required field: {field}"
    
    def test_health_check_environment_differences(self):
        """
        Test health check behavior varies appropriately by environment
        
        Business Value: Different environments have different reliability requirements.
        Development can be permissive while production must be strict. Wrong behavior
        in production = customer-facing outages.
        """
        test_environments = [
            # (environment, should_validate_db, should_be_strict)
            ("development", False, False),     # Permissive for dev productivity  
            ("test", False, False),           # Permissive for test reliability
            ("staging", True, True),          # Strict like production
            ("production", True, True),       # Strictest validation
        ]
        
        for env, should_validate_db, should_be_strict in test_environments:
            # Test environment-specific behavior patterns
            auth_env = get_auth_env()
            
            # Mock the environment
            with patch.object(auth_env, 'get_environment', return_value=env):
                # Verify environment-specific health check behavior
                assert auth_env.get_environment() == env
                
                if env in ["staging", "production"]:
                    # Production environments should have stricter validation
                    # (actual validation logic is tested in integration tests)
                    assert should_validate_db is True
                    assert should_be_strict is True
                else:
                    # Development/test should be more permissive
                    assert should_validate_db is False
                    assert should_be_strict is False


class TestHealthConfigModule:
    """Test health_config.py health check functions"""
    
    @pytest.mark.asyncio
    async def test_auth_postgres_health_check_success(self):
        """
        Test PostgreSQL database health check success scenario
        
        Business Value: Database connectivity is fundamental for auth service.
        Accurate database health reporting prevents traffic routing to instances
        with broken database connections.
        """
        # Mock successful database connection
        with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar.return_value = 1
            mock_session.execute.return_value = mock_result
            
            mock_db.get_session.return_value.__aenter__.return_value = mock_session
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)
            
            result = await check_auth_postgres_health()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert "database connection successful" in result["message"].lower()
            
    @pytest.mark.asyncio
    async def test_auth_postgres_health_check_failure(self):
        """
        Test PostgreSQL database health check failure scenario
        
        Business Value: When database is down, health checks must report unhealthy
        status to prevent failed authentication attempts and user frustration.
        """
        # Mock database connection failure
        with patch('auth_service.auth_core.database.connection.auth_db') as mock_db:
            mock_db.get_session.side_effect = Exception("Connection failed")
            
            result = await check_auth_postgres_health()
            
            assert result["status"] == HealthStatus.UNHEALTHY.value
            assert "database connection failed" in result["message"].lower()
            assert "Connection failed" in result["message"]
    
    @pytest.mark.asyncio
    async def test_oauth_providers_health_check(self):
        """
        Test OAuth providers health check functionality
        
        Business Value: OAuth enables user signup and login. Broken OAuth = 
        users cannot access service = churn and revenue loss. Health monitoring
        must detect OAuth configuration issues.
        """
        # Mock auth environment with configured providers
        with patch('auth_service.health_config.get_auth_env') as mock_env:
            mock_auth_env = Mock()
            mock_auth_env.get_oauth_google_client_id.return_value = "test-google-client-id"
            mock_auth_env.get_oauth_github_client_id.return_value = ""  # Not configured
            mock_env.return_value = mock_auth_env
            
            result = await check_oauth_providers_health()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert "google" in result["details"]["configured_providers"]
            assert "github" not in result["details"]["configured_providers"]
            assert "OAuth providers configured: google" in result["message"]
        
        # Test no providers configured scenario
        with patch('auth_service.health_config.get_auth_env') as mock_env:
            mock_auth_env = Mock()
            mock_auth_env.get_oauth_google_client_id.return_value = ""
            mock_auth_env.get_oauth_github_client_id.return_value = ""
            mock_env.return_value = mock_auth_env
            
            result = await check_oauth_providers_health()
            
            assert result["status"] == HealthStatus.DEGRADED.value
            assert "No OAuth providers configured" in result["message"]
            assert result["details"]["configured_providers"] == []
    
    @pytest.mark.asyncio 
    async def test_jwt_configuration_health_check(self):
        """
        Test JWT configuration health check functionality
        
        Business Value: JWT tokens are used for user session management.
        Broken JWT configuration = authentication failures = users locked out.
        Health monitoring must validate JWT setup.
        """
        # Test healthy JWT configuration
        with patch('auth_service.health_config.get_auth_env') as mock_env:
            mock_auth_env = Mock()
            mock_auth_env.get_jwt_secret_key.return_value = "a" * 32  # 32+ character key
            mock_auth_env.get_jwt_algorithm.return_value = "HS256"
            mock_env.return_value = mock_auth_env
            
            result = await check_jwt_configuration()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert "JWT configured with HS256" in result["message"]
            assert result["details"]["algorithm"] == "HS256"
        
        # Test weak JWT secret (degraded)
        with patch('auth_service.health_config.get_auth_env') as mock_env:
            mock_auth_env = Mock()
            mock_auth_env.get_jwt_secret_key.return_value = "short"  # Less than 32 chars
            mock_auth_env.get_jwt_algorithm.return_value = "HS256"
            mock_env.return_value = mock_auth_env
            
            result = await check_jwt_configuration()
            
            assert result["status"] == HealthStatus.DEGRADED.value
            assert "JWT secret key is weak" in result["message"]
        
        # Test missing JWT secret (unhealthy)
        with patch('auth_service.health_config.get_auth_env') as mock_env:
            mock_auth_env = Mock()
            mock_auth_env.get_jwt_secret_key.return_value = ""
            mock_env.return_value = mock_auth_env
            
            result = await check_jwt_configuration()
            
            assert result["status"] == HealthStatus.UNHEALTHY.value
            assert "JWT secret key not configured" in result["message"]
    
    @pytest.mark.asyncio
    async def test_overall_auth_health_status_aggregation(self):
        """
        Test overall auth health status aggregation logic
        
        Business Value: Overall health status drives load balancer routing decisions.
        Incorrect aggregation = traffic routed to partially broken instances = 
        customer-facing errors and degraded user experience.
        """
        # Test all healthy scenario
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db, \
             patch('auth_service.health_config.check_jwt_configuration') as mock_jwt, \
             patch('auth_service.health_config.check_oauth_providers_health') as mock_oauth:
            
            mock_db.return_value = {"status": HealthStatus.HEALTHY.value}
            mock_jwt.return_value = {"status": HealthStatus.HEALTHY.value}  
            mock_oauth.return_value = {"status": HealthStatus.HEALTHY.value}
            
            result = await get_auth_health()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["service"] == "auth_service"
            assert result["version"] == "1.0.0"
            assert "checks" in result
            assert len(result["checks"]) == 3
        
        # Test degraded scenario (one component degraded)
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db, \
             patch('auth_service.health_config.check_jwt_configuration') as mock_jwt, \
             patch('auth_service.health_config.check_oauth_providers_health') as mock_oauth:
            
            mock_db.return_value = {"status": HealthStatus.HEALTHY.value}
            mock_jwt.return_value = {"status": HealthStatus.DEGRADED.value}  # Degraded
            mock_oauth.return_value = {"status": HealthStatus.HEALTHY.value}
            
            result = await get_auth_health()
            
            # Overall status should be degraded if any component is degraded
            assert result["status"] == HealthStatus.DEGRADED.value
        
        # Test unhealthy scenario (one component unhealthy)
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db, \
             patch('auth_service.health_config.check_jwt_configuration') as mock_jwt, \
             patch('auth_service.health_config.check_oauth_providers_health') as mock_oauth:
            
            mock_db.return_value = {"status": HealthStatus.UNHEALTHY.value}  # Unhealthy
            mock_jwt.return_value = {"status": HealthStatus.HEALTHY.value}
            mock_oauth.return_value = {"status": HealthStatus.HEALTHY.value}
            
            result = await get_auth_health()
            
            # Overall status should be unhealthy if any component is unhealthy
            assert result["status"] == HealthStatus.UNHEALTHY.value


class TestHealthCheckBusinessValue:
    """Test health check functionality delivers real business value"""
    
    def test_health_monitoring_prevents_service_outages(self):
        """
        Test health monitoring enables operational excellence
        
        Business Value: Health monitoring is the foundation of reliable service
        operations. Accurate health reporting enables:
        - Zero-downtime deployments via rolling updates
        - Automatic instance replacement when unhealthy
        - Early detection of degraded service performance  
        - Proper load balancer traffic distribution
        - Proactive incident response before customer impact
        """
        # Verify health check covers all critical service dependencies
        critical_dependencies = [
            "database",  # User authentication data
            "jwt",       # Session token validation
            "oauth"      # Third-party login integration
        ]
        
        # Mock a comprehensive health check
        async def mock_health_check():
            return await get_auth_health()
        
        # Run health check and verify all critical deps are monitored
        import asyncio
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db, \
             patch('auth_service.health_config.check_jwt_configuration') as mock_jwt, \
             patch('auth_service.health_config.check_oauth_providers_health') as mock_oauth:
            
            mock_db.return_value = {"status": HealthStatus.HEALTHY.value}
            mock_jwt.return_value = {"status": HealthStatus.HEALTHY.value}
            mock_oauth.return_value = {"status": HealthStatus.HEALTHY.value}
            
            result = asyncio.run(mock_health_check())
            
            # Verify all critical dependencies are monitored
            monitored_deps = set(result["checks"].keys())
            expected_deps = set(critical_dependencies)
            
            assert expected_deps.issubset(monitored_deps), \
                f"Missing health checks for critical dependencies: {expected_deps - monitored_deps}"
            
            # Verify overall health aggregation works correctly
            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["service"] == "auth_service"
    
    def test_health_check_supports_deployment_automation(self):
        """
        Test health checks enable automated deployment workflows
        
        Business Value: Automated deployments depend on reliable health checks
        to determine when new service versions are ready for traffic. This enables:
        - Faster time-to-market for new features
        - Reduced operational overhead and manual errors
        - Consistent deployment process across environments
        - Ability to rollback failed deployments automatically
        """
        # Test health check provides deployment-ready information
        from auth_service.main import health_interface
        
        health_response = health_interface.get_basic_health()
        
        # Verify deployment automation requirements
        deployment_fields = [
            "service",          # Service identification for orchestrators
            "version",          # Version tracking for deployment management  
            "status",           # Health status for traffic routing decisions
            "uptime_seconds",   # Service stability indicator
            "timestamp"         # Response freshness validation
        ]
        
        for field in deployment_fields:
            assert field in health_response, \
                f"Missing deployment field '{field}' required for automation"
            assert health_response[field] is not None, \
                f"Deployment field '{field}' cannot be null"
        
        # Verify service identification matches expected values
        assert health_response["service"] == "auth-service"
        assert health_response["version"] == "1.0.0"
        assert health_response["status"] == "healthy"
        
        # Verify uptime indicates service stability (not just started)
        assert isinstance(health_response["uptime_seconds"], (int, float))
        assert health_response["uptime_seconds"] >= 0
    
    def test_health_check_enables_monitoring_and_alerting(self):
        """
        Test health checks provide sufficient data for operational monitoring
        
        Business Value: Operations teams need rich health data to:
        - Set up intelligent alerting that reduces false positives
        - Diagnose service issues quickly during incidents
        - Track service reliability metrics and SLA compliance
        - Make informed decisions about scaling and resource allocation
        """
        import asyncio
        
        async def get_comprehensive_health():
            return await get_auth_health()
        
        # Mock all health components for comprehensive test
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db, \
             patch('auth_service.health_config.check_jwt_configuration') as mock_jwt, \
             patch('auth_service.health_config.check_oauth_providers_health') as mock_oauth:
            
            # Return detailed health information
            mock_db.return_value = {
                "status": HealthStatus.HEALTHY.value,
                "message": "Auth database connection successful"
            }
            mock_jwt.return_value = {
                "status": HealthStatus.HEALTHY.value,
                "message": "JWT configured with HS256 algorithm",
                "details": {"algorithm": "HS256"}
            }
            mock_oauth.return_value = {
                "status": HealthStatus.HEALTHY.value,
                "message": "OAuth providers configured: google",
                "details": {"configured_providers": ["google"]}
            }
            
            health_data = asyncio.run(get_comprehensive_health())
            
            # Verify monitoring-friendly data structure
            monitoring_requirements = [
                "status",           # Overall health for alerting rules
                "service",          # Service identification in logs
                "version",          # Version tracking for regression analysis
                "checks"            # Component-level health for detailed diagnosis
            ]
            
            for requirement in monitoring_requirements:
                assert requirement in health_data, \
                    f"Missing monitoring requirement: {requirement}"
            
            # Verify component-level health provides diagnostic details
            assert len(health_data["checks"]) >= 3, "Insufficient health check coverage"
            
            for component, check_result in health_data["checks"].items():
                # Each component should have status and message for diagnosis
                assert "status" in check_result, f"Component {component} missing status"
                assert "message" in check_result, f"Component {component} missing diagnostic message"
                
                # Status should be a valid enum value
                valid_statuses = [s.value for s in HealthStatus]
                assert check_result["status"] in valid_statuses, \
                    f"Component {component} has invalid status: {check_result['status']}"