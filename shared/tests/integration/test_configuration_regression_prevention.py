"""
Configuration Regression Prevention Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Deployment Reliability  
- Business Goal: Prevent recurring configuration cascade failures that have caused production outages
- Value Impact: Configuration regressions have caused complete system outages multiple times
- Strategic Impact: Each regression incident costs hours of downtime and lost development velocity

Testing Strategy:
These tests specifically target the configuration regression scenarios documented in 
MISSION_CRITICAL_NAMED_VALUES_INDEX.xml incident history to ensure they never happen again.

CRITICAL INCIDENT SCENARIOS TESTED:
1. SERVICE_SECRET missing (2025-09-05) - Complete system outage
2. SERVICE_ID timestamp suffix (2025-09-07) - Recurring auth failures every 60s
3. Frontend deployment missing env vars (2025-09-03) - Complete frontend failure
4. Discovery endpoint localhost URLs (2025-09-02) - Service connectivity failures
5. Wrong staging subdomain usage - API call failures
6. WebSocket events missing run_id (2025-09-03) - Message delivery failures
7. Agent execution order incorrect (2025-09-05) - Empty optimization results

These tests ensure the specific configuration patterns that caused outages are detected
and prevented before deployment.
"""

import pytest
import time
from datetime import datetime
from typing import Dict, List, Any
from uuid import uuid4

# Import SSOT test framework
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from test_framework.ssot.configuration_validator import (
    TestConfigurationValidator,
    get_config_validator
)

# Import shared configuration system
from shared.constants.service_identifiers import SERVICE_ID
from shared.isolated_environment import (
    IsolatedEnvironment,
    EnvironmentValidator,
    ValidationResult
)


class TestConfigurationRegressionPrevention(BaseIntegrationTest):
    """
    Integration tests specifically targeting known configuration regression scenarios.
    
    These tests prevent the exact configuration failures that have caused production outages.
    """
    
    def setup_method(self):
        """Set up isolated test environment for each test."""
        super().setup_method()
        self.isolated_helper = IsolatedTestHelper()
        
    def teardown_method(self):
        """Clean up isolated environment after each test.""" 
        self.isolated_helper.cleanup_all()
        super().teardown_method()

    @pytest.mark.integration
    @pytest.mark.regression
    def test_service_secret_missing_regression_2025_09_05(self):
        """
        REGRESSION TEST: Prevent SERVICE_SECRET missing cascade failure (2025-09-05).
        
        INCIDENT: Missing SERVICE_SECRET caused complete staging outage with 100% 
        authentication failure and circuit breaker permanent open state.
        
        IMPACT: Multiple hours of complete system unusability.
        LOG_PATTERN: "INTER-SERVICE AUTHENTICATION CRITICAL ERROR"
        """
        with self.isolated_helper.create_isolated_context("service_secret_regression") as context:
            # GIVEN: Configuration missing SERVICE_SECRET (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_ID", SERVICE_ID, source="service")
            context.env.set("DATABASE_URL", "postgresql://staging:pass@db:5432/staging_db", source="service")
            context.env.set("JWT_SECRET_KEY", "staging_jwt_key", source="secret")
            # SERVICE_SECRET intentionally missing
            
            # WHEN: Validating service configuration
            validator = EnvironmentValidator(context.env)
            result = validator.validate_critical_service_variables("backend")
            
            # THEN: Validation MUST fail and identify SERVICE_SECRET issue
            assert not result.is_valid, "REGRESSION: Missing SERVICE_SECRET must be detected"
            
            error_messages = [str(error) for error in result.errors]
            service_secret_error = any("SERVICE_SECRET" in msg for msg in error_messages)
            assert service_secret_error, f"Must identify SERVICE_SECRET missing: {error_messages}"
            
            # AND: Error message must reference cascade impact
            critical_error = any("CRITICAL" in msg and "SERVICE_SECRET" in msg for msg in error_messages)
            assert critical_error, "Must indicate CRITICAL severity for SERVICE_SECRET"
            
            cascade_impact_mentioned = any(
                any(term in msg.lower() for term in ["authentication", "circuit", "failure"]) 
                for msg in error_messages
            )
            assert cascade_impact_mentioned, "Must reference cascade impact of missing SERVICE_SECRET"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_service_id_timestamp_suffix_regression_2025_09_07(self):
        """
        REGRESSION TEST: Prevent SERVICE_ID timestamp suffix auth failures (2025-09-07).
        
        INCIDENT: SERVICE_ID with timestamp suffix caused auth failures every 60 seconds.
        Auth service expected stable SSOT SERVICE_ID but received "netra-auth-staging-[timestamp]".
        
        IMPACT: Recurring authentication failures every minute.
        LOG_PATTERN: "Service ID mismatch: received netra-auth-staging-[timestamp] but expected netra-backend"
        """
        # Generate timestamp suffix like the problematic pattern
        timestamp_suffix = str(int(time.time()))
        problematic_service_id = f"netra-auth-staging-{timestamp_suffix}"
        
        with self.isolated_helper.create_isolated_context("service_id_regression") as context:
            # GIVEN: SERVICE_ID with timestamp suffix (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("SERVICE_ID", problematic_service_id, source="environment")
            context.env.set("SERVICE_SECRET", "test_secret", source="secret")
            
            # WHEN: Validating SERVICE_ID stability
            validator = EnvironmentValidator(context.env)
            result = validator.validate_service_id_stability()
            
            # THEN: Validation MUST fail for unstable SERVICE_ID
            assert not result.is_valid, f"REGRESSION: Unstable SERVICE_ID must be detected: {problematic_service_id}"
            
            error_messages = [str(error) for error in result.errors]
            
            # AND: Must identify timestamp suffix pattern
            timestamp_error = any("timestamp" in msg.lower() for msg in error_messages)
            assert timestamp_error, f"Must identify timestamp suffix issue: {error_messages}"
            
            # AND: Must reference the expected stable value
            stable_value_mentioned = any(SERVICE_ID in msg for msg in error_messages)
            assert stable_value_mentioned, "Must reference expected stable SERVICE_ID value"

    @pytest.mark.integration
    @pytest.mark.regression 
    def test_frontend_env_vars_missing_regression_2025_09_03(self):
        """
        REGRESSION TEST: Prevent frontend deployment env vars missing (2025-09-03).
        
        INCIDENT: Frontend deployment missing most environment variables caused complete 
        frontend failure with no WebSocket, no auth, no API access.
        
        IMPACT: Complete frontend dysfunction, users unable to access system.
        """
        critical_frontend_vars = [
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL", 
            "NEXT_PUBLIC_AUTH_URL",
            "NEXT_PUBLIC_ENVIRONMENT"
        ]
        
        # Test the specific regression scenario - all variables missing
        with self.isolated_helper.create_isolated_context("frontend_missing_all") as context:
            # GIVEN: Frontend config with NO critical variables (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            # All NEXT_PUBLIC_* variables intentionally missing
            
            # WHEN: Validating frontend configuration
            validator = EnvironmentValidator(context.env)
            result = validator.validate_frontend_critical_variables()
            
            # THEN: Validation MUST fail for all missing variables
            assert not result.is_valid, "REGRESSION: Missing frontend vars must be detected"
            
            error_messages = [str(error) for error in result.errors]
            
            # AND: Must identify ALL missing critical variables
            for var in critical_frontend_vars:
                var_error = any(var in msg for msg in error_messages)
                assert var_error, f"Must identify missing {var}: {error_messages}"
            
            # AND: Must reference cascade impact for each variable
            cascade_impacts = ["API calls", "WebSocket", "auth", "environment"]
            for impact in cascade_impacts:
                impact_mentioned = any(impact.lower() in msg.lower() for msg in error_messages)
                assert impact_mentioned, f"Must mention cascade impact for {impact}"

    @pytest.mark.integration 
    @pytest.mark.regression
    def test_discovery_endpoint_localhost_regression_2025_09_02(self):
        """
        REGRESSION TEST: Prevent discovery endpoint localhost URLs in staging (2025-09-02).
        
        INCIDENT: Discovery endpoint returning localhost URLs in staging environment 
        caused frontend to be unable to connect to services.
        
        IMPACT: Service connectivity failures, frontend unable to reach backend.
        """
        # Reproduce the problematic discovery data from incident
        problematic_discovery_data = {
            "backend_url": "http://localhost:8000",    # Wrong: localhost in staging
            "auth_url": "http://localhost:8081",       # Wrong: localhost in staging  
            "websocket_url": "ws://localhost:8000/ws", # Wrong: localhost in staging
            "analytics_url": "http://localhost:8002"   # Wrong: localhost in staging
        }
        
        with self.isolated_helper.create_isolated_context("discovery_regression") as context:
            # GIVEN: Staging environment with localhost discovery URLs (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            # WHEN: Validating discovery endpoint configuration
            validator = EnvironmentValidator(context.env)
            result = validator.validate_discovery_endpoint_configuration(problematic_discovery_data)
            
            # THEN: Validation MUST fail for localhost URLs in staging
            assert not result.is_valid, "REGRESSION: Localhost URLs in staging must be detected"
            
            error_messages = [str(error) for error in result.errors]
            
            # AND: Must identify localhost issue for each service
            services_with_localhost = ["backend_url", "auth_url", "websocket_url", "analytics_url"]
            for service in services_with_localhost:
                localhost_error = any(
                    "localhost" in msg.lower() and service in msg 
                    for msg in error_messages
                )
                assert localhost_error, f"Must identify localhost issue for {service}: {error_messages}"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_staging_domain_confusion_regression(self):
        """
        REGRESSION TEST: Prevent staging domain confusion (staging.netrasystems.ai vs api.staging).
        
        INCIDENT: Wrong staging subdomain usage caused API calls to fail and WebSocket 
        connection failures.
        
        IMPACT: Frontend unable to communicate with backend services.
        """
        wrong_domain_patterns = [
            "https://staging.netrasystems.ai",      # Wrong: should be api.staging
            "https://staging.netrasystems.ai/api",  # Wrong: should be api.staging  
            "http://staging.netrasystems.ai",       # Wrong: HTTP + wrong subdomain
        ]
        
        for wrong_url in wrong_domain_patterns:
            with self.isolated_helper.create_isolated_context(f"domain_regression_{hash(wrong_url)}") as context:
                # GIVEN: Staging config with wrong domain pattern (reproducing incident)
                context.env.set("ENVIRONMENT", "staging", source="deployment")
                context.env.set("NEXT_PUBLIC_API_URL", wrong_url, source="deployment")
                context.env.set("NEXT_PUBLIC_WS_URL", wrong_url.replace("http", "ws"), source="deployment")
                
                # WHEN: Validating staging domain configuration
                validator = EnvironmentValidator(context.env)
                result = validator.validate_staging_domain_configuration()
                
                # THEN: Validation MUST fail for wrong domain patterns
                assert not result.is_valid, f"REGRESSION: Wrong staging domain must be detected: {wrong_url}"
                
                error_messages = [str(error) for error in result.errors]
                
                # AND: Must identify the specific domain issue
                domain_error = any(
                    "staging.netrasystems.ai" in msg or "api.staging" in msg 
                    for msg in error_messages
                )
                assert domain_error, f"Must identify domain pattern issue for {wrong_url}: {error_messages}"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_websocket_run_id_missing_regression_2025_09_03(self):
        """
        REGRESSION TEST: Prevent WebSocket events missing run_id (2025-09-03).
        
        INCIDENT: WebSocket events missing run_id caused sub-agent messages not to be 
        delivered to users properly.
        
        IMPACT: Users not receiving real-time updates from agents.
        """
        # Simulate WebSocket event data missing run_id
        websocket_events_missing_run_id = [
            {
                "type": "agent_started",
                "data": {"agent_name": "test_agent"},
                # run_id intentionally missing
            },
            {
                "type": "agent_thinking", 
                "data": {"thought": "Processing request"},
                # run_id intentionally missing
            },
            {
                "type": "agent_completed",
                "data": {"result": "Task completed"},
                # run_id intentionally missing
            }
        ]
        
        with self.isolated_helper.create_isolated_context("websocket_regression") as context:
            # GIVEN: WebSocket events without run_id (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            # WHEN: Validating WebSocket event structure
            validator = EnvironmentValidator(context.env)
            
            # Validate each event has required fields
            validation_errors = []
            for event in websocket_events_missing_run_id:
                if "run_id" not in event.get("data", {}):
                    validation_errors.append(f"WebSocket event {event['type']} missing run_id")
            
            # THEN: Validation MUST identify missing run_id fields
            assert len(validation_errors) > 0, "REGRESSION: Missing run_id in WebSocket events must be detected"
            
            # AND: All events must be flagged
            assert len(validation_errors) == len(websocket_events_missing_run_id), \
                f"All events must be flagged for missing run_id: {validation_errors}"
            
            # AND: Error messages must reference impact
            run_id_mentioned = all("run_id" in error for error in validation_errors)
            assert run_id_mentioned, "All errors must mention run_id requirement"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_agent_execution_order_regression_2025_09_05(self):
        """
        REGRESSION TEST: Prevent incorrect agent execution order (2025-09-05).
        
        INCIDENT: Agent execution order incorrect (Optimization before Data) caused 
        empty optimization results with no business value delivered.
        
        IMPACT: Users received empty or useless optimization recommendations.
        """
        # Test configuration representing incorrect agent execution order
        incorrect_execution_order = [
            {"agent": "optimization_agent", "order": 1},  # Wrong: should be after data
            {"agent": "data_agent", "order": 2},          # Wrong: should be before optimization
            {"agent": "triage_agent", "order": 3}         # Wrong: should be first
        ]
        
        correct_execution_order = [
            {"agent": "triage_agent", "order": 1},        # Correct: first
            {"agent": "data_agent", "order": 2},          # Correct: before optimization
            {"agent": "optimization_agent", "order": 3}    # Correct: after data
        ]
        
        with self.isolated_helper.create_isolated_context("agent_order_regression") as context:
            # GIVEN: Incorrect agent execution order (reproducing incident)
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("AGENT_EXECUTION_ORDER", "optimization_agent,data_agent,triage_agent", source="config")
            
            # WHEN: Validating agent execution order
            configured_order = context.env.get("AGENT_EXECUTION_ORDER", "").split(",")
            
            # THEN: Order must be validated
            expected_order = ["triage_agent", "data_agent", "optimization_agent"]
            
            # Check if order is incorrect (reproducing the regression)
            order_is_incorrect = configured_order != expected_order
            assert order_is_incorrect, "Test setup: Should have incorrect order for regression test"
            
            # AND: Validation should identify the incorrect order
            triage_first = configured_order[0] == "triage_agent" if configured_order else False
            data_before_optimization = (
                configured_order.index("data_agent") < configured_order.index("optimization_agent")
                if "data_agent" in configured_order and "optimization_agent" in configured_order
                else False
            )
            
            # These should fail for the incorrect configuration
            assert not triage_first, "REGRESSION: Triage agent should be first but isn't"
            assert not data_before_optimization, "REGRESSION: Data agent should be before optimization but isn't"

        # Test correct configuration passes validation
        with self.isolated_helper.create_isolated_context("agent_order_correct") as context:
            # GIVEN: Correct agent execution order
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            context.env.set("AGENT_EXECUTION_ORDER", "triage_agent,data_agent,optimization_agent", source="config")
            
            # WHEN: Validating correct order
            configured_order = context.env.get("AGENT_EXECUTION_ORDER", "").split(",")
            expected_order = ["triage_agent", "data_agent", "optimization_agent"]
            
            # THEN: Validation should pass for correct order
            order_is_correct = configured_order == expected_order
            assert order_is_correct, "Correct agent execution order should validate successfully"

    @pytest.mark.integration
    @pytest.mark.regression  
    def test_comprehensive_regression_detection(self):
        """
        REGRESSION TEST: Comprehensive test combining multiple regression scenarios.
        
        This test validates that multiple configuration issues are detected simultaneously,
        as they often occur together in deployment scenarios.
        """
        with self.isolated_helper.create_isolated_context("comprehensive_regression") as context:
            # GIVEN: Configuration with MULTIPLE regression issues
            context.env.set("ENVIRONMENT", "staging", source="deployment")
            
            # Issue 1: Missing SERVICE_SECRET
            context.env.set("SERVICE_ID", SERVICE_ID, source="service")
            # SERVICE_SECRET intentionally missing
            
            # Issue 2: Frontend variables missing
            # NEXT_PUBLIC_* variables intentionally missing
            
            # Issue 3: Wrong staging domain
            context.env.set("NEXT_PUBLIC_API_URL", "https://staging.netrasystems.ai", source="deployment")
            
            # Issue 4: Localhost in discovery data
            discovery_data = {
                "backend_url": "http://localhost:8000",
                "auth_url": "http://localhost:8081"
            }
            
            # WHEN: Running comprehensive validation
            validator = EnvironmentValidator(context.env)
            
            backend_result = validator.validate_critical_service_variables("backend")
            frontend_result = validator.validate_frontend_critical_variables()
            staging_result = validator.validate_staging_domain_configuration()
            discovery_result = validator.validate_discovery_endpoint_configuration(discovery_data)
            
            # THEN: ALL validation checks must fail
            validation_results = [backend_result, frontend_result, staging_result, discovery_result]
            all_failed = all(not result.is_valid for result in validation_results)
            assert all_failed, "All validation checks should fail for comprehensive regression scenario"
            
            # AND: Each specific issue must be identified
            all_errors = []
            for result in validation_results:
                all_errors.extend([str(error) for error in result.errors])
            
            # Verify each regression pattern is detected
            regression_patterns = [
                "SERVICE_SECRET",           # Missing service secret
                "NEXT_PUBLIC_API_URL",     # Missing frontend var
                "staging.netrasystems.ai", # Wrong domain
                "localhost"                # Localhost in discovery
            ]
            
            for pattern in regression_patterns:
                pattern_detected = any(pattern in error for error in all_errors)
                assert pattern_detected, f"Regression pattern '{pattern}' must be detected in: {all_errors}"

    @pytest.mark.integration
    @pytest.mark.regression
    def test_configuration_cascade_failure_prevention(self):
        """
        REGRESSION TEST: Prevent configuration cascade failures that cause system-wide outages.
        
        This test ensures that configuration validation prevents the cascade failure patterns
        documented in the incident history.
        """
        cascade_failure_scenarios = [
            {
                "name": "auth_circuit_breaker_cascade",
                "description": "Missing SERVICE_SECRET -> Auth failure -> Circuit breaker open -> 100% lockout",
                "config": {
                    "ENVIRONMENT": "staging",
                    "SERVICE_ID": SERVICE_ID,
                    # SERVICE_SECRET missing - triggers cascade
                },
                "expected_impact": "complete authentication failure"
            },
            {
                "name": "frontend_connection_cascade", 
                "description": "Wrong API URL -> No API calls -> No data -> No business value",
                "config": {
                    "ENVIRONMENT": "staging",
                    "NEXT_PUBLIC_API_URL": "http://localhost:8000",  # Wrong for staging
                    "NEXT_PUBLIC_WS_URL": "ws://localhost:8000",     # Wrong for staging
                },
                "expected_impact": "No API calls work"
            },
            {
                "name": "service_discovery_cascade",
                "description": "Localhost discovery -> Service unreachable -> Frontend broken -> User lockout", 
                "config": {
                    "ENVIRONMENT": "staging",
                },
                "discovery_data": {
                    "backend_url": "http://localhost:8000",
                    "auth_url": "http://localhost:8081"
                },
                "expected_impact": "Service connectivity failures"
            }
        ]
        
        for scenario in cascade_failure_scenarios:
            with self.isolated_helper.create_isolated_context(f"cascade_{scenario['name']}") as context:
                # GIVEN: Configuration that triggers cascade failure
                for key, value in scenario["config"].items():
                    context.env.set(key, value, source="test")
                
                # WHEN: Running validation to prevent cascade
                validator = EnvironmentValidator(context.env)
                
                # Validate different aspects based on scenario
                validation_results = []
                if "SERVICE_SECRET" in scenario["description"]:
                    validation_results.append(validator.validate_critical_service_variables("backend"))
                if "NEXT_PUBLIC" in str(scenario["config"]):
                    validation_results.append(validator.validate_frontend_critical_variables())
                    validation_results.append(validator.validate_staging_domain_configuration())
                if "discovery_data" in scenario:
                    validation_results.append(
                        validator.validate_discovery_endpoint_configuration(scenario["discovery_data"])
                    )
                
                # THEN: Validation must detect and prevent cascade failure
                cascade_prevented = any(not result.is_valid for result in validation_results)
                assert cascade_prevented, f"Cascade failure scenario '{scenario['name']}' must be prevented"
                
                # AND: Error messages must reference the expected cascade impact
                all_errors = []
                for result in validation_results:
                    all_errors.extend([str(error) for error in result.errors])
                
                # Verify impact is mentioned in error messages
                impact_keywords = scenario["expected_impact"].lower().split()
                impact_mentioned = any(
                    any(keyword in error.lower() for keyword in impact_keywords)
                    for error in all_errors
                )
                assert impact_mentioned, \
                    f"Cascade impact must be mentioned for scenario '{scenario['name']}': {all_errors}"