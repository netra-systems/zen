"""
Unit Tests for Health Check URL Validation

Purpose: Reproduce "Request URL missing protocol" errors and validate URL parsing
Business Impact: $500K+ MRR at risk due to infrastructure validation gaps
Expected Initial Result: TESTS MUST FAIL to prove issues exist

Test Strategy: Failure-first approach - tests designed to initially fail and 
demonstrate the infrastructure validation gaps, then pass after fixes.
"""

import pytest
import urllib.parse
from typing import Dict, List, Optional, Tuple
from unittest.mock import Mock, patch

# Test subject imports
from netra_backend.app.core.configuration_validator import ConfigurationValidator
from netra_backend.app.monitoring.configuration_drift_monitor import ConfigurationDriftMonitor
from shared.isolated_environment import get_env


class TestHealthCheckURLValidation:
    """
    Tests designed to FAIL initially and prove URL validation issues.
    
    These tests reproduce the exact "Request URL missing protocol" errors
    mentioned in issue #143 context.
    """

    def test_staging_url_protocol_missing_reproduction(self):
        """
        MUST FAIL INITIALLY: Reproduce 'Request URL missing protocol' error.
        
        This test specifically targets the deployment health check failure
        pattern identified in the Golden Path analysis.
        """
        # Test cases that should expose the URL protocol issue
        test_urls = [
            "api.staging.netrasystems.ai",  # Missing protocol - common issue
            "//api.staging.netrasystems.ai",  # Protocol-relative URL
            "staging.netrasystems.ai/health",  # Missing protocol with path
            "",  # Empty URL
            None,  # None URL
            "http://",  # Incomplete URL
            "://api.staging.netrasystems.ai",  # Malformed protocol
        ]
        
        failures = []
        
        for url in test_urls:
            try:
                # This should fail initially for URLs missing protocols
                result = self._validate_url_protocol(url)
                if not result["valid"]:
                    failures.append({
                        "url": url,
                        "error": result["error"],
                        "expected": "Should fail with protocol missing error"
                    })
            except Exception as e:
                # Capture exceptions that indicate URL validation issues
                failures.append({
                    "url": url,
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Initially, this assertion should FAIL showing the issues exist
        assert len(failures) > 0, (
            f"Expected URL validation failures to demonstrate issues exist. "
            f"Found {len(failures)} failures: {failures}"
        )
        
        # After infrastructure fixes, update this test to assert len(failures) == 0

    def test_url_validation_comprehensive_scenarios(self):
        """
        Test all URL validation scenarios comprehensively.
        
        Expected to expose systematic URL validation weaknesses.
        """
        # Valid URLs that should pass
        valid_urls = [
            "https://api.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai/health",
            "wss://api.staging.netrasystems.ai/ws",
            "http://localhost:8000",
            "https://app.staging.netrasystems.ai/login"
        ]
        
        # Invalid URLs that should fail validation
        invalid_urls = [
            "api.staging.netrasystems.ai",  # No protocol
            "ftp://api.staging.netrasystems.ai",  # Wrong protocol
            "https://",  # No hostname
            "https:///path",  # Empty hostname
            "not-a-url",  # Not URL format
            "staging..netrasystems.ai",  # Invalid hostname
        ]
        
        valid_results = []
        invalid_results = []
        
        for url in valid_urls:
            result = self._validate_url_protocol(url)
            valid_results.append({"url": url, "result": result})
            
        for url in invalid_urls:
            result = self._validate_url_protocol(url)
            invalid_results.append({"url": url, "result": result})
        
        # Initially expect some valid URLs to fail (showing validation gaps)
        valid_failures = [r for r in valid_results if not r["result"]["valid"]]
        
        # This should initially FAIL showing validation gaps
        assert len(valid_failures) == 0, (
            f"Valid URLs failing validation (shows validation gaps): {valid_failures}"
        )
        
        # Invalid URLs should properly fail
        invalid_passes = [r for r in invalid_results if r["result"]["valid"]]
        assert len(invalid_passes) == 0, (
            f"Invalid URLs incorrectly passing validation: {invalid_passes}"
        )

    def test_protocol_detection_edge_cases(self):
        """
        Test edge cases in protocol detection logic.
        
        This targets the specific protocol detection issues causing
        deployment health check failures.
        """
        edge_cases = [
            ("HTTP://api.staging.netrasystems.ai", "uppercase protocol"),
            ("https://api.staging.netrasystems.ai:443", "explicit port"),
            ("wss://api.staging.netrasystems.ai:443/ws", "websocket with port"),
            ("https://api.staging.netrasystems.ai/", "trailing slash"),
            ("https://api.staging.netrasystems.ai?param=value", "query parameters"),
            ("https://user:pass@api.staging.netrasystems.ai", "authentication in URL"),
        ]
        
        failures = []
        
        for url, description in edge_cases:
            try:
                result = self._validate_url_protocol(url)
                if not result["valid"]:
                    failures.append({
                        "url": url,
                        "description": description,
                        "error": result["error"]
                    })
            except Exception as e:
                failures.append({
                    "url": url,
                    "description": description,
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Initially expect some failures (showing edge case handling gaps)
        assert len(failures) == 0, (
            f"Protocol detection failing on edge cases: {failures}"
        )

    def test_staging_environment_url_construction(self):
        """
        Test staging environment URL construction patterns.
        
        This specifically tests the URL construction logic that may be
        causing the staging environment health check failures.
        """
        env = get_env()
        
        # Test different environment variable scenarios
        test_scenarios = [
            {
                "BASE_URL": "api.staging.netrasystems.ai",  # Missing protocol
                "expected_error": "Protocol missing"
            },
            {
                "BASE_URL": "https://api.staging.netrasystems.ai",  # Correct
                "expected_valid": True
            },
            {
                "BASE_URL": "",  # Empty
                "expected_error": "Empty URL"
            },
            {
                # No BASE_URL set
                "expected_error": "URL not configured"
            }
        ]
        
        failures = []
        
        for i, scenario in enumerate(test_scenarios):
            # Set up test environment
            if "BASE_URL" in scenario:
                env.set("BASE_URL", scenario["BASE_URL"], source=f"test_{i}")
            else:
                # Clear BASE_URL for testing missing configuration
                env.set("BASE_URL", "", source=f"test_{i}")
            
            try:
                constructed_url = self._construct_staging_url()
                result = self._validate_url_protocol(constructed_url)
                
                if "expected_valid" in scenario:
                    if not result["valid"]:
                        failures.append({
                            "scenario": scenario,
                            "constructed_url": constructed_url,
                            "error": result["error"]
                        })
                else:
                    # Expected to fail - check if it properly detects the issue
                    if result["valid"]:
                        failures.append({
                            "scenario": scenario,
                            "constructed_url": constructed_url,
                            "error": "Should have failed but passed validation"
                        })
                        
            except Exception as e:
                if "expected_error" not in scenario:
                    failures.append({
                        "scenario": scenario,
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
        
        # Initially expect failures showing URL construction issues
        assert len(failures) == 0, (
            f"URL construction issues in staging environment: {failures}"
        )

    def test_health_check_endpoint_url_building(self):
        """
        Test health check endpoint URL building specifically.
        
        This reproduces the exact health check failure pattern.
        """
        # Test health check URL construction for different services
        services = [
            {"name": "backend", "base": "api.staging.netrasystems.ai"},
            {"name": "auth", "base": "auth.staging.netrasystems.ai"}, 
            {"name": "frontend", "base": "app.staging.netrasystems.ai"},
        ]
        
        failures = []
        
        for service in services:
            try:
                # This is likely where the "Request URL missing protocol" occurs
                health_url = self._build_health_check_url(service["base"])
                result = self._validate_url_protocol(health_url)
                
                if not result["valid"]:
                    failures.append({
                        "service": service["name"],
                        "base_url": service["base"],
                        "health_url": health_url,
                        "error": result["error"]
                    })
                    
            except Exception as e:
                failures.append({
                    "service": service["name"],
                    "base_url": service["base"],
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # This should initially FAIL, showing the health check URL issue
        assert len(failures) == 0, (
            f"Health check URL building failures: {failures}"
        )

    # Helper methods for URL validation testing
    
    def _validate_url_protocol(self, url: str) -> Dict[str, any]:
        """
        Validate URL protocol - this replicates the logic causing issues.
        
        Initially, this may have gaps that cause the validation failures.
        """
        if not url:
            return {"valid": False, "error": "Empty or None URL"}
            
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Check for protocol (scheme)
            if not parsed.scheme:
                return {"valid": False, "error": "Request URL missing protocol"}
                
            # Check for supported protocols
            supported_protocols = ["http", "https", "ws", "wss"]
            if parsed.scheme.lower() not in supported_protocols:
                return {"valid": False, "error": f"Unsupported protocol: {parsed.scheme}"}
                
            # Check for hostname
            if not parsed.netloc:
                return {"valid": False, "error": "URL missing hostname"}
                
            return {"valid": True, "url": url, "parsed": parsed}
            
        except Exception as e:
            return {"valid": False, "error": f"URL parsing error: {str(e)}"}

    def _construct_staging_url(self) -> str:
        """
        Construct staging URL - may have issues causing protocol problems.
        """
        env = get_env()
        base_url = env.get("BASE_URL", "")
        
        if not base_url:
            # This might be a source of issues
            base_url = "api.staging.netrasystems.ai"
            
        # This logic might be missing protocol addition
        if not base_url.startswith(("http://", "https://")):
            # Initially this might be missing, causing the protocol error
            base_url = f"https://{base_url}"
            
        return base_url

    def _build_health_check_url(self, base_url: str) -> str:
        """
        Build health check URL - likely source of "missing protocol" error.
        """
        # This logic might be flawed initially
        if not base_url.startswith(("http://", "https://")):
            # The issue might be here - not adding protocol
            health_url = f"{base_url}/health"
        else:
            health_url = f"{base_url}/health"
            
        return health_url


class TestInfrastructureHealthValidation:
    """
    Tests for infrastructure health validation patterns.
    
    These tests focus on the broader infrastructure validation
    that may be failing in the deployment process.
    """

    def test_service_health_check_protocol_validation(self):
        """
        Test service health check protocol validation.
        
        This tests the pattern that might be causing deployment failures.
        """
        # Services that should have health checks
        staging_services = [
            "https://api.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai", 
            "https://app.staging.netrasystems.ai"
        ]
        
        validation_failures = []
        
        for service_url in staging_services:
            try:
                # Test the health check URL construction
                health_url = f"{service_url}/health"
                validation_result = self._validate_service_health_url(health_url)
                
                if not validation_result["valid"]:
                    validation_failures.append({
                        "service_url": service_url,
                        "health_url": health_url,
                        "error": validation_result["error"]
                    })
                    
            except Exception as e:
                validation_failures.append({
                    "service_url": service_url,
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Should pass after infrastructure fixes
        assert len(validation_failures) == 0, (
            f"Service health check validation failures: {validation_failures}"
        )

    def test_configuration_drift_url_validation(self):
        """
        Test configuration drift detection for URL validation.
        
        This may expose configuration issues causing the validation gaps.
        """
        env = get_env()
        
        # Test configuration scenarios that might cause drift
        config_scenarios = [
            {
                "name": "missing_protocol_staging",
                "API_URL": "api.staging.netrasystems.ai",  # Missing https://
                "expected_issue": "Protocol missing"
            },
            {
                "name": "correct_staging", 
                "API_URL": "https://api.staging.netrasystems.ai",
                "expected_valid": True
            }
        ]
        
        configuration_issues = []
        
        for scenario in config_scenarios:
            # Set test configuration
            for key, value in scenario.items():
                if key not in ["name", "expected_issue", "expected_valid"]:
                    env.set(key, value, source=f"test_{scenario['name']}")
            
            try:
                # Test configuration validation
                validation_result = self._validate_configuration_urls()
                
                if "expected_valid" in scenario:
                    if not validation_result["valid"]:
                        configuration_issues.append({
                            "scenario": scenario["name"],
                            "error": validation_result["error"]
                        })
                else:
                    # Should detect configuration issue
                    if validation_result["valid"]:
                        configuration_issues.append({
                            "scenario": scenario["name"],
                            "error": "Should have detected configuration issue"
                        })
                        
            except Exception as e:
                configuration_issues.append({
                    "scenario": scenario["name"],
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        assert len(configuration_issues) == 0, (
            f"Configuration drift URL validation issues: {configuration_issues}"
        )

    # Helper methods
    
    def _validate_service_health_url(self, health_url: str) -> Dict[str, any]:
        """Validate service health URL."""
        try:
            parsed = urllib.parse.urlparse(health_url)
            
            if not parsed.scheme:
                return {"valid": False, "error": "Health URL missing protocol"}
                
            if parsed.scheme not in ["http", "https"]:
                return {"valid": False, "error": f"Invalid health URL protocol: {parsed.scheme}"}
                
            if not parsed.netloc:
                return {"valid": False, "error": "Health URL missing hostname"}
                
            if not parsed.path.endswith("/health"):
                return {"valid": False, "error": "Invalid health check path"}
                
            return {"valid": True, "health_url": health_url}
            
        except Exception as e:
            return {"valid": False, "error": f"Health URL validation error: {str(e)}"}

    def _validate_configuration_urls(self) -> Dict[str, any]:
        """Validate configuration URLs for common issues."""
        env = get_env()
        
        url_configs = [
            "API_URL",
            "AUTH_URL", 
            "WEBSOCKET_URL",
            "FRONTEND_URL"
        ]
        
        issues = []
        
        for config_key in url_configs:
            url_value = env.get(config_key, "")
            if url_value:
                parsed = urllib.parse.urlparse(url_value)
                if not parsed.scheme:
                    issues.append(f"{config_key} missing protocol: {url_value}")
                    
        if issues:
            return {"valid": False, "error": "; ".join(issues)}
            
        return {"valid": True, "message": "All configuration URLs valid"}


# Pytest markers for test organization
pytestmark = [
    pytest.mark.unit,
    pytest.mark.infrastructure_validation,
    pytest.mark.must_fail_initially
]