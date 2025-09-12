"""
Test Configuration Regression Prevention Algorithms - Unit Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Regression prevention for critical configuration
- Business Goal: Prevent configuration regressions that cause system outages
- Value Impact: Prevents cascade failures from configuration changes that break production
- Strategic Impact: CRITICAL - Configuration regressions cost $12K MRR per incident

CRITICAL: These tests validate algorithms that prevent configuration regressions,
specifically the patterns identified in MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
that cause cascade failures.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.configuration.central_config_validator import CentralConfigurationValidator


class TestConfigRegressionPreventionAlgorithms(BaseTestCase):
    """Test algorithms that prevent configuration regressions and cascade failures."""
    
    def setup_method(self):
        """Setup test environment with regression prevention validation."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        self.env.enable_isolation()
        
        # Set test environment
        self.env.set("ENVIRONMENT", "test", "test_setup")
        self.env.set("TESTING", "true", "test_setup")
        
        self.validator = CentralConfigurationValidator(env_manager=self.env)
        
    def teardown_method(self):
        """Clean up test environment."""
        self.env.reset_to_original()
        super().teardown_method()

    @pytest.mark.unit
    def test_service_secret_regression_prevention_algorithm(self):
        """Test algorithm preventing SERVICE_SECRET regressions that cause authentication failures."""
        # Baseline: Working SERVICE_SECRET configuration
        baseline_config = {
            "SERVICE_SECRET": "production-service-secret-32-characters-minimum",
            "config_version": "1.0",
            "last_validated": datetime.now().isoformat()
        }
        
        # Test valid configuration change (should pass)
        valid_update = baseline_config.copy()
        valid_update["SERVICE_SECRET"] = "updated-service-secret-32-characters-minimum"
        valid_update["config_version"] = "1.1"
        
        result = self.validator.validate_config_change(baseline_config, valid_update, "SERVICE_SECRET")
        assert result.is_valid, f"Valid SERVICE_SECRET update should pass: {result.errors}"
        
        # Test regression: SERVICE_SECRET becomes too short (causes auth failures)
        short_secret_regression = baseline_config.copy()
        short_secret_regression["SERVICE_SECRET"] = "short"  # Regression!
        
        result = self.validator.validate_config_change(baseline_config, short_secret_regression, "SERVICE_SECRET")
        assert not result.is_valid, "SERVICE_SECRET regression should be prevented"
        
        error_text = " ".join(result.errors)
        assert "regression" in error_text.lower() or "shorter" in error_text.lower(), \
            "Should identify SERVICE_SECRET regression"
            
        # Test regression: SERVICE_SECRET becomes None (causes complete auth failure)
        missing_secret_regression = baseline_config.copy()
        del missing_secret_regression["SERVICE_SECRET"]  # Complete regression!
        
        result = self.validator.validate_config_change(baseline_config, missing_secret_regression, "SERVICE_SECRET")
        assert not result.is_valid, "Missing SERVICE_SECRET should be prevented"
        
        error_text = " ".join(result.errors)
        assert "missing" in error_text.lower() and "SERVICE_SECRET" in error_text, \
            "Should identify missing SERVICE_SECRET as critical regression"
            
    @pytest.mark.unit
    def test_frontend_url_regression_prevention_algorithm(self):
        """Test algorithm preventing frontend URL regressions that break user access."""
        # Baseline: Working staging URLs
        baseline_urls = {
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_WS_URL": "wss://api.staging.netrasystems.ai",
            "NEXT_PUBLIC_AUTH_URL": "https://auth.staging.netrasystems.ai",
            "environment": "staging"
        }
        
        # Test valid URL update (should pass)
        valid_update = baseline_urls.copy()
        valid_update["NEXT_PUBLIC_API_URL"] = "https://api-v2.staging.netrasystems.ai"  # Valid update
        
        result = self.validator.validate_url_regression(baseline_urls, valid_update)
        assert result.is_valid, f"Valid URL update should pass: {result.errors}"
        
        # Test regression: Staging URLs become localhost (breaks staging access)
        localhost_regression = baseline_urls.copy()
        localhost_regression["NEXT_PUBLIC_API_URL"] = "http://localhost:8000"  # Regression!
        
        result = self.validator.validate_url_regression(baseline_urls, localhost_regression)
        assert not result.is_valid, "Localhost regression in staging should be prevented"
        
        error_text = " ".join(result.errors)
        assert "localhost" in error_text and "staging" in error_text.lower(), \
            "Should identify localhost regression in staging environment"
            
        # Test regression: HTTPS becomes HTTP (security downgrade)
        http_downgrade = baseline_urls.copy()
        http_downgrade["NEXT_PUBLIC_API_URL"] = "http://api.staging.netrasystems.ai"  # HTTPS  ->  HTTP regression
        
        result = self.validator.validate_url_regression(baseline_urls, http_downgrade)
        assert not result.is_valid, "HTTPS to HTTP downgrade should be prevented"
        
        error_text = " ".join(result.errors)
        assert "https" in error_text.lower() or "security" in error_text.lower(), \
            "Should identify HTTPS downgrade regression"
            
    @pytest.mark.unit
    def test_oauth_configuration_regression_prevention_algorithm(self):
        """Test algorithm preventing OAuth configuration regressions."""
        # Baseline: Working OAuth configuration
        baseline_oauth = {
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-oauth-client-id-working",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-oauth-client-secret-working",
            "oauth_last_tested": datetime.now().isoformat(),
            "oauth_status": "working"
        }
        
        # Test valid OAuth update
        valid_oauth_update = baseline_oauth.copy()
        valid_oauth_update["GOOGLE_OAUTH_CLIENT_ID_STAGING"] = "updated-staging-oauth-client-id"
        
        result = self.validator.validate_oauth_regression(baseline_oauth, valid_oauth_update)
        assert result.is_valid, f"Valid OAuth update should pass: {result.errors}"
        
        # Test regression: OAuth credentials become empty/None
        empty_oauth_regression = baseline_oauth.copy()
        empty_oauth_regression["GOOGLE_OAUTH_CLIENT_ID_STAGING"] = ""  # Regression!
        
        result = self.validator.validate_oauth_regression(baseline_oauth, empty_oauth_regression)
        assert not result.is_valid, "Empty OAuth credentials should be prevented"
        
        error_text = " ".join(result.errors)
        assert "oauth" in error_text.lower() and "empty" in error_text.lower(), \
            "Should identify empty OAuth regression"
            
        # Test regression: OAuth pattern consistency breaks
        pattern_regression = baseline_oauth.copy()
        pattern_regression["GOOGLE_CLIENT_ID"] = "mixed-pattern-regression"  # Wrong pattern for staging
        
        result = self.validator.validate_oauth_regression(baseline_oauth, pattern_regression)
        assert not result.is_valid, "OAuth pattern regression should be prevented"
        
    @pytest.mark.unit
    def test_database_configuration_regression_prevention_algorithm(self):
        """Test algorithm preventing database configuration regressions."""
        # Baseline: Working SSOT database configuration
        baseline_db = {
            "POSTGRES_HOST": "staging-postgres.gcp",
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging-secure-password-32-chars",
            "POSTGRES_DB": "netra_staging",
            "POSTGRES_PORT": "5432",
            "database_pattern": "ssot_compliant"
        }
        
        # Test valid database update
        valid_db_update = baseline_db.copy()
        valid_db_update["POSTGRES_HOST"] = "new-staging-postgres.gcp"  # Valid host update
        
        result = self.validator.validate_database_regression(baseline_db, valid_db_update)
        assert result.is_valid, f"Valid database update should pass: {result.errors}"
        
        # Test regression: SSOT pattern breaks (introduces direct DATABASE_URL)
        ssot_regression = baseline_db.copy()
        ssot_regression["DATABASE_URL"] = "postgresql://direct:access@host/db"  # Breaks SSOT pattern
        
        result = self.validator.validate_database_regression(baseline_db, ssot_regression)
        assert not result.is_valid, "SSOT pattern regression should be prevented"
        
        error_text = " ".join(result.errors)
        assert "ssot" in error_text.lower() or "pattern" in error_text.lower(), \
            "Should identify SSOT pattern regression"
            
        # Test regression: Required component becomes missing
        missing_component = baseline_db.copy()
        del missing_component["POSTGRES_PASSWORD"]  # Critical component missing
        
        result = self.validator.validate_database_regression(baseline_db, missing_component)
        assert not result.is_valid, "Missing database component should be prevented"
        
        error_text = " ".join(result.errors)
        assert "POSTGRES_PASSWORD" in error_text, "Should identify missing password component"
        
    @pytest.mark.unit
    def test_websocket_event_regression_prevention_algorithm(self):
        """Test algorithm preventing WebSocket event configuration regressions."""
        # Baseline: Complete mission-critical WebSocket events
        baseline_events = {
            "agent_started": {"payload": ["run_id", "agent_name"], "enabled": True},
            "agent_thinking": {"payload": ["run_id", "thought"], "enabled": True}, 
            "tool_executing": {"payload": ["run_id", "tool_name", "args"], "enabled": True},
            "tool_completed": {"payload": ["run_id", "tool_name", "result"], "enabled": True},
            "agent_completed": {"payload": ["run_id", "result"], "enabled": True}
        }
        
        # Test valid event update
        valid_event_update = baseline_events.copy()
        valid_event_update["agent_progress"] = {"payload": ["run_id", "progress"], "enabled": True}  # New event
        
        result = self.validator.validate_websocket_events_regression(baseline_events, valid_event_update)
        assert result.is_valid, f"Valid WebSocket event addition should pass: {result.errors}"
        
        # Test regression: Critical event becomes disabled
        disabled_critical_event = baseline_events.copy()
        disabled_critical_event["agent_started"]["enabled"] = False  # Regression!
        
        result = self.validator.validate_websocket_events_regression(baseline_events, disabled_critical_event)
        assert not result.is_valid, "Disabling critical WebSocket event should be prevented"
        
        error_text = " ".join(result.errors)
        assert "agent_started" in error_text and "critical" in error_text.lower(), \
            "Should identify critical event regression"
            
        # Test regression: run_id removed from payload (causes message routing failures)
        missing_run_id = baseline_events.copy()
        missing_run_id["agent_started"]["payload"] = ["agent_name"]  # Missing run_id!
        
        result = self.validator.validate_websocket_events_regression(baseline_events, missing_run_id)
        assert not result.is_valid, "Missing run_id should be prevented"
        
        error_text = " ".join(result.errors)
        assert "run_id" in error_text, "Should identify missing run_id regression"
        
    @pytest.mark.unit  
    def test_environment_consistency_regression_prevention_algorithm(self):
        """Test algorithm preventing environment consistency regressions."""
        # Baseline: Consistent staging environment configuration
        baseline_env = {
            "ENVIRONMENT": "staging",
            "NEXT_PUBLIC_ENVIRONMENT": "staging",
            "backend_environment": "staging",
            "frontend_environment": "staging",
            "environment_consistency": "validated"
        }
        
        # Test valid environment update
        valid_env_update = baseline_env.copy()
        valid_env_update["environment_version"] = "2.0"  # Valid addition
        
        result = self.validator.validate_environment_consistency_regression(baseline_env, valid_env_update)
        assert result.is_valid, f"Valid environment update should pass: {result.errors}"
        
        # Test regression: Environment consistency breaks
        inconsistent_env = baseline_env.copy()
        inconsistent_env["NEXT_PUBLIC_ENVIRONMENT"] = "production"  # Frontend thinks production!
        
        result = self.validator.validate_environment_consistency_regression(baseline_env, inconsistent_env)
        assert not result.is_valid, "Environment inconsistency should be prevented"
        
        error_text = " ".join(result.errors)
        assert "inconsistent" in error_text.lower() or "mismatch" in error_text.lower(), \
            "Should identify environment inconsistency regression"
            
        # Test regression: Environment becomes undefined
        undefined_env = baseline_env.copy()
        undefined_env["ENVIRONMENT"] = None  # Environment regression
        
        result = self.validator.validate_environment_consistency_regression(baseline_env, undefined_env)
        assert not result.is_valid, "Undefined environment should be prevented"
        
    @pytest.mark.unit
    def test_cascade_failure_pattern_detection_algorithm(self):
        """Test algorithm that detects configuration changes leading to cascade failures."""
        # Known cascade failure patterns from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
        cascade_patterns = {
            "SERVICE_SECRET_missing": {
                "description": "Complete authentication failure and circuit breaker permanent open",
                "impact": "100% user lockout",
                "detection_pattern": {"SERVICE_SECRET": None}
            },
            "localhost_in_staging": {
                "description": "Frontend cannot reach backend",
                "impact": "Complete staging failure", 
                "detection_pattern": {"NEXT_PUBLIC_API_URL": "http://localhost:8000", "ENVIRONMENT": "staging"}
            },
            "websocket_events_missing_run_id": {
                "description": "Events not routed to correct user, messages lost",
                "impact": "Chat appears broken",
                "detection_pattern": {"agent_started": {"payload": []}}
            }
        }
        
        # Test detection of SERVICE_SECRET cascade pattern
        service_secret_config = {
            "SERVICE_SECRET": None,  # Triggers cascade failure
            "ENVIRONMENT": "staging"
        }
        
        detected_patterns = self.validator.detect_cascade_failure_patterns(service_secret_config)
        assert len(detected_patterns) > 0, "Should detect SERVICE_SECRET cascade pattern"
        
        service_secret_pattern = next((p for p in detected_patterns if "SERVICE_SECRET" in p["name"]), None)
        assert service_secret_pattern is not None, "Should specifically detect SERVICE_SECRET cascade pattern"
        assert "authentication failure" in service_secret_pattern["description"], \
            "Should describe authentication cascade impact"
            
        # Test detection of localhost in staging cascade pattern
        localhost_staging_config = {
            "NEXT_PUBLIC_API_URL": "http://localhost:8000",
            "ENVIRONMENT": "staging"
        }
        
        detected_patterns = self.validator.detect_cascade_failure_patterns(localhost_staging_config)
        localhost_pattern = next((p for p in detected_patterns if "localhost" in p["name"]), None)
        assert localhost_pattern is not None, "Should detect localhost in staging cascade pattern"
        
        # Test configuration with no cascade patterns (should be clean)
        clean_config = {
            "SERVICE_SECRET": "valid-service-secret-32-characters-minimum",
            "NEXT_PUBLIC_API_URL": "https://api.staging.netrasystems.ai",
            "ENVIRONMENT": "staging",
            "agent_started": {"payload": ["run_id", "agent_name"]}
        }
        
        detected_patterns = self.validator.detect_cascade_failure_patterns(clean_config)
        assert len(detected_patterns) == 0, f"Clean configuration should not trigger cascade patterns: {detected_patterns}"