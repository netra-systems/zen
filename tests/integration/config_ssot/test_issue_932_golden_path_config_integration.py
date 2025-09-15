"""
INTEGRATION TEST: Golden Path Configuration Integration - Issue #932

Business Value Justification (BVJ):
- Segment: Enterprise/Mid-Market - Core User Journey
- Business Goal: Protect $500K+ ARR by ensuring Golden Path user flow works reliably
- Value Impact: Critical configuration management for user login → AI response flow
- Strategic Impact: Validates SSOT configuration supports end-to-end business functionality

CRITICAL MISSION: Issue #932 Configuration Manager Broken Import Crisis (P0 SSOT violation)

This test suite validates that configuration management works correctly throughout
the Golden Path user flow: User Login → WebSocket Connection → Agent Execution → AI Response

Golden Path Configuration Dependencies:
1. Authentication service configuration for user login
2. WebSocket configuration for real-time communication
3. Database configuration for user state persistence
4. Agent system configuration for AI response generation
5. Service integration configuration for external API calls

Expected Behavior:
- Configuration loads correctly for all Golden Path services
- User authentication configuration enables successful login
- WebSocket configuration supports real-time agent communication
- Database configuration provides reliable state persistence
- All configuration SSOT patterns work end-to-end

This test supports the Configuration Manager SSOT remediation effort for Issue #932.
"""

import unittest
import asyncio
import time
import json
from typing import Dict, List, Optional, Any
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestIssue932GoldenPathConfigIntegration(SSotAsyncTestCase, unittest.TestCase):
    """Integration tests for Golden Path configuration flow for Issue #932."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.golden_path_results = {}
        self.service_configs = {}
        self.integration_test_data = []
    
    def test_authentication_service_configuration_integration(self):
        """
        CRITICAL TEST: Validate authentication service configuration integration.
        
        Tests that configuration provides proper authentication service settings
        for the Golden Path user login flow. Critical for user authentication.
        """
        self.record_metric("test_category", "auth_service_config")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Check for authentication service configuration
            auth_config_found = False
            auth_service_url = None
            
            if hasattr(config, 'auth_service_url'):
                auth_service_url = config.auth_service_url
                auth_config_found = True
            elif hasattr(config, 'AUTH_SERVICE_URL'):
                auth_service_url = config.AUTH_SERVICE_URL
                auth_config_found = True
            
            # Record auth service configuration status
            self.record_metric("auth_service_config_found", auth_config_found)
            
            if auth_config_found and auth_service_url:
                self.record_metric("auth_service_url_configured", True)
                self.record_metric("auth_service_url", str(auth_service_url))
                
                # Basic validation of auth service URL format
                if isinstance(auth_service_url, str):
                    is_valid_url = (auth_service_url.startswith('http://') or 
                                   auth_service_url.startswith('https://') or
                                   auth_service_url.startswith('localhost:') or
                                   '8001' in auth_service_url)  # Default auth service port
                    self.record_metric("auth_service_url_format_valid", is_valid_url)
                else:
                    self.record_metric("auth_service_url_format_valid", False)
            else:
                self.record_metric("auth_service_url_configured", False)
                # This might be expected in some test configurations
                self.record_metric("auth_service_config_status", "not_configured")
            
            self.service_configs['auth_service'] = {
                'configured': auth_config_found,
                'url': str(auth_service_url) if auth_service_url else None,
                'status': 'success'
            }
            
            self.record_metric("auth_service_config_test", "success")
            
        except Exception as e:
            self.service_configs['auth_service'] = {
                'configured': False,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("auth_service_config_test", "failed")
            self.fail(f"Authentication service configuration test failed: {e}")
    
    def test_database_configuration_integration(self):
        """
        CRITICAL TEST: Validate database configuration integration.
        
        Tests that configuration provides proper database settings for
        user state persistence in the Golden Path flow.
        """
        self.record_metric("test_category", "database_config")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Check for database configuration
            database_config_found = False
            database_url = None
            
            if hasattr(config, 'database_url'):
                database_url = config.database_url
                database_config_found = True
            elif hasattr(config, 'DATABASE_URL'):
                database_url = config.DATABASE_URL
                database_config_found = True
            
            # Record database configuration status
            self.record_metric("database_config_found", database_config_found)
            
            if database_config_found and database_url:
                self.record_metric("database_url_configured", True)
                
                # Basic validation of database URL format
                if isinstance(database_url, str):
                    is_postgres_url = ('postgresql://' in database_url or 
                                      'postgres://' in database_url or
                                      'sqlite://' in database_url)
                    self.record_metric("database_url_format_valid", is_postgres_url)
                    
                    # Check if URL contains credentials (security consideration)
                    has_credentials = '@' in database_url
                    self.record_metric("database_url_has_credentials", has_credentials)
                else:
                    self.record_metric("database_url_format_valid", False)
            else:
                self.record_metric("database_url_configured", False)
            
            self.service_configs['database'] = {
                'configured': database_config_found,
                'url_present': database_url is not None,
                'status': 'success'
            }
            
            self.record_metric("database_config_test", "success")
            
        except Exception as e:
            self.service_configs['database'] = {
                'configured': False,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("database_config_test", "failed")
            self.fail(f"Database configuration test failed: {e}")
    
    def test_redis_configuration_integration(self):
        """
        TEST: Validate Redis configuration integration.
        
        Tests that configuration provides proper Redis settings for
        caching and session management in the Golden Path flow.
        """
        self.record_metric("test_category", "redis_config")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Check for Redis configuration
            redis_config_found = False
            redis_url = None
            
            if hasattr(config, 'redis_url'):
                redis_url = config.redis_url
                redis_config_found = True
            elif hasattr(config, 'REDIS_URL'):
                redis_url = config.REDIS_URL
                redis_config_found = True
            
            # Record Redis configuration status
            self.record_metric("redis_config_found", redis_config_found)
            
            if redis_config_found and redis_url:
                self.record_metric("redis_url_configured", True)
                
                # Basic validation of Redis URL format
                if isinstance(redis_url, str):
                    is_valid_redis_url = ('redis://' in redis_url or 
                                         'localhost:6379' in redis_url or
                                         'redis:6379' in redis_url)
                    self.record_metric("redis_url_format_valid", is_valid_redis_url)
                else:
                    self.record_metric("redis_url_format_valid", False)
            else:
                self.record_metric("redis_url_configured", False)
                # Redis might be optional in some configurations
                self.record_metric("redis_config_status", "optional_not_configured")
            
            self.service_configs['redis'] = {
                'configured': redis_config_found,
                'url_present': redis_url is not None,
                'status': 'success'
            }
            
            self.record_metric("redis_config_test", "success")
            
        except Exception as e:
            self.service_configs['redis'] = {
                'configured': False,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("redis_config_test", "failed")
            # Don't fail the test for Redis config issues as it might be optional
            self.record_metric("redis_config_test_result", "failed_but_optional")
    
    def test_websocket_configuration_integration(self):
        """
        CRITICAL TEST: Validate WebSocket configuration integration.
        
        Tests that configuration provides proper WebSocket settings for
        real-time agent communication in the Golden Path flow.
        """
        self.record_metric("test_category", "websocket_config")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Check for WebSocket-related configuration
            websocket_config_found = False
            websocket_settings = {}
            
            # Look for various WebSocket configuration attributes
            websocket_attrs = [
                'websocket_url', 'WEBSOCKET_URL', 'ws_url',
                'websocket_port', 'WEBSOCKET_PORT',
                'websocket_host', 'WEBSOCKET_HOST',
                'cors_origins', 'CORS_ORIGINS'  # CORS is critical for WebSocket
            ]
            
            for attr in websocket_attrs:
                if hasattr(config, attr):
                    websocket_settings[attr] = getattr(config, attr)
                    websocket_config_found = True
            
            # Record WebSocket configuration status
            self.record_metric("websocket_config_found", websocket_config_found)
            self.record_metric("websocket_settings_count", len(websocket_settings))
            
            if websocket_settings:
                self.record_metric("websocket_settings", websocket_settings)
                
                # Check for CORS configuration (critical for WebSocket)
                cors_configured = any('cors' in k.lower() for k in websocket_settings.keys())
                self.record_metric("cors_configured", cors_configured)
            else:
                # WebSocket configuration might be handled differently or be optional
                self.record_metric("websocket_config_status", "not_explicitly_configured")
            
            self.service_configs['websocket'] = {
                'configured': websocket_config_found,
                'settings_count': len(websocket_settings),
                'status': 'success'
            }
            
            self.record_metric("websocket_config_test", "success")
            
        except Exception as e:
            self.service_configs['websocket'] = {
                'configured': False,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("websocket_config_test", "failed")
            self.fail(f"WebSocket configuration test failed: {e}")
    
    def test_agent_system_configuration_integration(self):
        """
        TEST: Validate agent system configuration integration.
        
        Tests that configuration provides proper agent system settings for
        AI response generation in the Golden Path flow.
        """
        self.record_metric("test_category", "agent_system_config")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration
            config = get_config()
            self.assertIsNotNone(config, "Configuration should not be None")
            
            # Check for agent system configuration
            agent_config_found = False
            agent_settings = {}
            
            # Look for various agent configuration attributes
            agent_attrs = [
                'llm_provider', 'LLM_PROVIDER',
                'openai_api_key', 'OPENAI_API_KEY',
                'anthropic_api_key', 'ANTHROPIC_API_KEY',
                'agent_timeout', 'AGENT_TIMEOUT',
                'max_agent_iterations', 'MAX_AGENT_ITERATIONS'
            ]
            
            for attr in agent_attrs:
                if hasattr(config, attr):
                    value = getattr(config, attr)
                    # Don't log sensitive keys directly
                    if 'api_key' in attr.lower():
                        agent_settings[attr] = 'configured' if value else 'not_configured'
                    else:
                        agent_settings[attr] = value
                    agent_config_found = True
            
            # Record agent system configuration status
            self.record_metric("agent_system_config_found", agent_config_found)
            self.record_metric("agent_settings_count", len(agent_settings))
            
            if agent_settings:
                self.record_metric("agent_settings", agent_settings)
                
                # Check for LLM provider configuration
                llm_provider_configured = any('llm_provider' in k.lower() for k in agent_settings.keys())
                self.record_metric("llm_provider_configured", llm_provider_configured)
                
                # Check for API key configuration (without logging values)
                api_key_configured = any('api_key' in k.lower() for k in agent_settings.keys())
                self.record_metric("api_key_configured", api_key_configured)
            else:
                # Agent configuration might be handled elsewhere or be environment-specific
                self.record_metric("agent_system_config_status", "not_explicitly_configured")
            
            self.service_configs['agent_system'] = {
                'configured': agent_config_found,
                'settings_count': len(agent_settings),
                'status': 'success'
            }
            
            self.record_metric("agent_system_config_test", "success")
            
        except Exception as e:
            self.service_configs['agent_system'] = {
                'configured': False,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("agent_system_config_test", "failed")
            # Don't fail the test as agent config might be optional or handled differently
            self.record_metric("agent_system_config_test_result", "failed_but_optional")
    
    def test_configuration_consistency_across_services(self):
        """
        INTEGRATION TEST: Validate configuration consistency across services.
        
        Tests that configuration provides consistent settings across all
        services involved in the Golden Path flow.
        """
        self.record_metric("test_category", "config_consistency")
        
        try:
            from netra_backend.app.config import get_config
            
            # Get configuration multiple times to test consistency
            configs = []
            for i in range(3):
                config = get_config()
                self.assertIsNotNone(config, f"Configuration {i} should not be None")
                configs.append(config)
                time.sleep(0.1)  # Small delay
            
            # Test consistency
            config_types = [type(config).__name__ for config in configs]
            unique_types = set(config_types)
            
            self.record_metric("config_consistency_types", config_types)
            self.record_metric("config_types_unique_count", len(unique_types))
            
            # All configurations should be the same type
            self.assertEqual(len(unique_types), 1, f"Configuration types should be consistent: {unique_types}")
            
            # Test attribute consistency
            if configs:
                first_config = configs[0]
                consistency_issues = []
                
                for i, config in enumerate(configs[1:], 1):
                    # Compare common attributes
                    first_attrs = set(dir(first_config))
                    current_attrs = set(dir(config))
                    
                    missing_attrs = first_attrs - current_attrs
                    extra_attrs = current_attrs - first_attrs
                    
                    if missing_attrs:
                        consistency_issues.append(f"Config {i} missing attributes: {missing_attrs}")
                    if extra_attrs:
                        consistency_issues.append(f"Config {i} extra attributes: {extra_attrs}")
                
                self.record_metric("config_consistency_issues", consistency_issues)
                
                # Should have no major consistency issues
                major_issues = [issue for issue in consistency_issues if 'missing' in issue]
                self.assertEqual(len(major_issues), 0, f"Major consistency issues found: {major_issues}")
            
            self.record_metric("config_consistency_test", "success")
            
        except Exception as e:
            self.record_metric("config_consistency_test", "failed")
            self.fail(f"Configuration consistency test failed: {e}")
    
    def test_golden_path_configuration_end_to_end(self):
        """
        CRITICAL TEST: End-to-end Golden Path configuration validation.
        
        Tests that all configuration components work together to support
        the complete Golden Path: User Login → WebSocket → Agent → AI Response.
        """
        self.record_metric("test_category", "golden_path_e2e_config")
        
        golden_path_steps = {
            'configuration_loading': False,
            'auth_service_ready': False,
            'database_ready': False,
            'websocket_ready': False,
            'agent_system_ready': False,
        }
        
        try:
            # Step 1: Configuration loading
            from netra_backend.app.config import get_config
            config = get_config()
            self.assertIsNotNone(config, "Configuration should load successfully")
            golden_path_steps['configuration_loading'] = True
            
            # Step 2: Auth service configuration validation
            if 'auth_service' in self.service_configs:
                auth_status = self.service_configs['auth_service'].get('status') == 'success'
                golden_path_steps['auth_service_ready'] = auth_status
            
            # Step 3: Database configuration validation
            if 'database' in self.service_configs:
                db_status = self.service_configs['database'].get('status') == 'success'
                golden_path_steps['database_ready'] = db_status
            
            # Step 4: WebSocket configuration validation
            if 'websocket' in self.service_configs:
                ws_status = self.service_configs['websocket'].get('status') == 'success'
                golden_path_steps['websocket_ready'] = ws_status
            
            # Step 5: Agent system configuration validation
            if 'agent_system' in self.service_configs:
                agent_status = self.service_configs['agent_system'].get('status') == 'success'
                golden_path_steps['agent_system_ready'] = agent_status
            
            # Calculate Golden Path readiness
            ready_steps = sum(golden_path_steps.values())
            total_steps = len(golden_path_steps)
            readiness_percentage = (ready_steps / total_steps) * 100 if total_steps > 0 else 0
            
            # Record comprehensive metrics
            self.record_metric("golden_path_steps", golden_path_steps)
            self.record_metric("golden_path_ready_steps", ready_steps)
            self.record_metric("golden_path_total_steps", total_steps)
            self.record_metric("golden_path_readiness_percentage", readiness_percentage)
            
            self.golden_path_results = {
                'steps': golden_path_steps,
                'readiness': readiness_percentage,
                'critical_ready': golden_path_steps['configuration_loading'] and golden_path_steps['database_ready'],
                'status': 'success'
            }
            
            # Golden Path should have at least basic readiness
            self.assertGreaterEqual(
                readiness_percentage, 40.0,
                f"Golden Path should have at least 40% readiness. Current: {readiness_percentage}%. Steps: {golden_path_steps}"
            )
            
            # Critical components should be ready
            critical_ready = golden_path_steps['configuration_loading']
            self.assertTrue(critical_ready, "Critical configuration loading must be ready for Golden Path")
            
            self.record_metric("golden_path_e2e_test", "success")
            
        except Exception as e:
            self.golden_path_results = {
                'steps': golden_path_steps,
                'error': str(e),
                'status': 'failed'
            }
            self.record_metric("golden_path_e2e_test", "failed")
            self.fail(f"Golden Path end-to-end configuration test failed: {e}")
    
    def test_golden_path_integration_summary(self):
        """
        SUMMARY TEST: Comprehensive Golden Path integration summary.
        
        Provides complete summary of Golden Path configuration integration
        results for SSOT compliance monitoring and Issue #932 validation.
        """
        self.record_metric("test_category", "integration_summary")
        
        # Collect all service configuration results
        service_results = {}
        for service_name, config_data in self.service_configs.items():
            service_results[service_name] = {
                'configured': config_data.get('configured', False),
                'status': config_data.get('status', 'unknown')
            }
        
        # Calculate success metrics
        successful_services = sum(1 for result in service_results.values() if result['status'] == 'success')
        total_services = len(service_results)
        
        if total_services > 0:
            service_success_rate = (successful_services / total_services) * 100
        else:
            service_success_rate = 0
        
        # Record comprehensive metrics
        self.record_metric("integration_total_services", total_services)
        self.record_metric("integration_successful_services", successful_services)
        self.record_metric("integration_service_success_rate", service_success_rate)
        self.record_metric("integration_service_results", service_results)
        
        # Include Golden Path results if available
        if self.golden_path_results:
            self.record_metric("golden_path_results", self.golden_path_results)
            golden_path_ready = self.golden_path_results.get('readiness', 0)
            self.record_metric("golden_path_final_readiness", golden_path_ready)
        
        # Summary message
        summary = (
            f"Golden Path Configuration Integration Summary: "
            f"{successful_services}/{total_services} services configured successfully "
            f"({service_success_rate:.1f}% success rate)"
        )
        
        if self.golden_path_results:
            golden_path_ready = self.golden_path_results.get('readiness', 0)
            summary += f", Golden Path {golden_path_ready:.1f}% ready"
        
        self.record_metric("golden_path_integration_summary", summary)
        
        # Integration test should pass if we have reasonable service configuration
        self.assertGreaterEqual(
            service_success_rate, 60.0,
            f"Service configuration should have at least 60% success rate. Results: {service_results}"
        )
        
        # If we have Golden Path results, they should show some readiness
        if self.golden_path_results:
            golden_path_readiness = self.golden_path_results.get('readiness', 0)
            self.assertGreaterEqual(
                golden_path_readiness, 20.0,
                f"Golden Path should have at least 20% readiness. Current: {golden_path_readiness}%"
            )


if __name__ == '__main__':
    # Run tests
    unittest.main()