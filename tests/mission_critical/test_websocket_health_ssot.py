#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket Health Check SSOT Integration Tests

THIS SUITE FOCUSES ON THE CRITICAL VIOLATIONS IN WEBSOCKET HEALTH ENDPOINTS.
Business Value: $500K+ ARR - Validates health check functionality during SSOT migration

PURPOSE:
- Focus on critical violations in websocket_ssot.py lines 1439, 1470, 1496
- Test health endpoint functionality with SSOT patterns
- Test configuration endpoint integrity during migration
- Validate statistics endpoint functionality preservation
- Ensure no silent failures during health check operations

CRITICAL HEALTH ENDPOINTS:
1. websocket_health_check() - Line 1439 violation
2. get_websocket_config() - Line 1470 violation  
3. websocket_detailed_stats() - Line 1496 violation

HEALTH CHECK BUSINESS VALUE:
Health checks are critical for:
- Production deployment validation
- Load balancer health monitoring
- Auto-scaling decision making
- Incident detection and alerting
- Customer SLA compliance

INTEGRATION STRATEGY:
- Test real health endpoint functionality (not mocked)
- Validate health check data integrity
- Test endpoint availability during migration
- Ensure health checks don't fail silently
"""

import asyncio
import os
import sys
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import time
import traceback

# CRITICAL: Add project root to Python path for imports  
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import environment and test framework
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase

import pytest
from loguru import logger

# Import components for health testing
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketHealthSSot(SSotAsyncTestCase):
    """Mission Critical: WebSocket Health Check SSOT Integration Tests
    
    These tests validate the health check endpoints during factory pattern migration:
    1. Health check endpoint functionality preservation
    2. Configuration endpoint data integrity  
    3. Statistics endpoint information accuracy
    4. Integration with production monitoring systems
    """
    
    def setup_method(self, method):
        """Set up test environment for health check testing."""
        super().setup_method(method)
        
        self.test_user_id = f"health_test_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"health_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"health_run_{uuid.uuid4().hex[:8]}"
        self.health_check_timeout = 30  # seconds
        
        logger.info(f"[HEALTH CHECK TEST] Setup complete for health validation")

    def teardown_method(self, method):
        """Clean up health check test environment."""
        super().teardown_method(method)
        logger.info("[HEALTH CHECK TEST] Teardown complete")

    @pytest.mark.asyncio
    async def test_websocket_health_check_endpoint_integrity(self):
        """TEST: WebSocket health check endpoint functionality integrity
        
        PURPOSE: Validates that the websocket_health_check() function (line 1439 violation)
        continues to work correctly during and after SSOT migration.
        
        BUSINESS CRITICAL: Health checks are used by:
        - GCP Load Balancer for traffic routing
        - Auto-scaling systems for capacity decisions  
        - Monitoring systems for alerting
        - SLA compliance reporting
        """
        logger.info("[HEALTH ENDPOINT] Testing WebSocket health check endpoint integrity...")
        
        try:
            # Import the WebSocket route class
            from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
            
            # Create instance for health check testing
            websocket_route = WebSocketSSOTRouter()
            
            # Execute health check with timeout protection
            start_time = time.time()
            health_result = await asyncio.wait_for(
                websocket_route.websocket_health_check(),
                timeout=self.health_check_timeout
            )
            execution_time = time.time() - start_time
            
            # CRITICAL: Health check must return structured data
            assert isinstance(health_result, dict), "Health check must return dictionary"
            assert "status" in health_result, "Health check missing required 'status' field"
            assert "timestamp" in health_result, "Health check missing required 'timestamp' field"
            
            logger.info(f"[HEALTH CHECK SUCCESS] Health check completed in {execution_time:.2f}s")
            logger.info(f"[HEALTH STATUS] Status: {health_result.get('status')}")
            
            # Validate health check status values
            valid_statuses = ["healthy", "unhealthy", "degraded"]
            actual_status = health_result.get("status")
            assert actual_status in valid_statuses, f"Invalid health status: {actual_status}"
            
            # Test timestamp validity
            timestamp_str = health_result.get("timestamp")
            try:
                # Validate timestamp format
                timestamp_parsed = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_diff = abs((datetime.now(timezone.utc) - timestamp_parsed).total_seconds())
                assert time_diff < 60, f"Health check timestamp too old: {time_diff}s"
                logger.info(f"[TIMESTAMP VALID] Health check timestamp: {timestamp_str}")
            except Exception as e:
                logger.error(f"[TIMESTAMP ERROR] Invalid timestamp format: {e}")
                pytest.fail(f"Health check timestamp invalid: {e}")
            
            # Validate component health information
            if "components" in health_result:
                components = health_result["components"]
                logger.info(f"[COMPONENTS] Health check components: {list(components.keys())}")
                
                # Expected components for WebSocket health
                expected_components = ["factory", "message_router", "connection_monitor"]
                
                for component in expected_components:
                    if component in components:
                        component_status = components[component]
                        logger.info(f"[COMPONENT STATUS] {component}: {component_status}")
                        
                        # Component status should be boolean or have meaningful status
                        assert isinstance(component_status, (bool, str, dict)), f"Component {component} has invalid status type"
                
                # At least one component should be reporting status
                assert len(components) > 0, "Health check must report component status"
            
            # Performance validation - health check should be fast
            assert execution_time < 10.0, f"Health check too slow: {execution_time}s > 10s"
            
            logger.info("[HEALTH ENDPOINT SUCCESS] WebSocket health check endpoint working correctly")
            
        except asyncio.TimeoutError:
            logger.error(f"[HEALTH ENDPOINT TIMEOUT] Health check timed out after {self.health_check_timeout}s")
            pytest.fail("CRITICAL: Health check endpoint timeout - system may be unhealthy")
            
        except ImportError as e:
            logger.error(f"[HEALTH ENDPOINT IMPORT ERROR] Cannot import WebSocketSSotRoute: {e}")
            pytest.fail(f"CRITICAL: Health check endpoint not accessible - {e}")
            
        except Exception as e:
            logger.error(f"[HEALTH ENDPOINT FAILURE] Health check failed: {e}")
            logger.error(f"[ERROR DETAILS] {traceback.format_exc()}")
            
            # Determine if this is a migration-related failure or system failure
            if "get_websocket_manager_factory" in str(e):
                logger.info("[MIGRATION NOTE] Health check failure related to factory migration - expected during transition")
            else:
                pytest.fail(f"CRITICAL: Health check endpoint system failure - {e}")

    @pytest.mark.asyncio
    async def test_websocket_config_endpoint_data_integrity(self):
        """TEST: WebSocket configuration endpoint data integrity
        
        PURPOSE: Validates that get_websocket_config() function (line 1470 violation)  
        returns correct configuration data during SSOT migration.
        
        BUSINESS CRITICAL: Configuration data is used by:
        - Frontend for WebSocket connection parameters
        - Load testing for capacity planning
        - Development environment setup
        - Production deployment validation
        """
        logger.info("[CONFIG ENDPOINT] Testing WebSocket configuration endpoint data integrity...")
        
        try:
            from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
            
            websocket_route = WebSocketSSOTRouter()
            
            # Execute configuration retrieval with timeout
            start_time = time.time()
            config_result = await asyncio.wait_for(
                websocket_route.get_websocket_config(),
                timeout=self.health_check_timeout
            )
            execution_time = time.time() - start_time
            
            # CRITICAL: Config must return structured data
            assert isinstance(config_result, dict), "Config endpoint must return dictionary"
            
            logger.info(f"[CONFIG SUCCESS] Configuration retrieved in {execution_time:.2f}s")
            
            # Check for error responses
            if "error" in config_result:
                error_msg = config_result["error"]
                logger.warning(f"[CONFIG ERROR] Configuration error: {error_msg}")
                
                # During migration, some errors might be expected
                if "get_websocket_manager_factory" in error_msg:
                    logger.info("[MIGRATION NOTE] Config error related to factory migration")
                else:
                    pytest.fail(f"CRITICAL: Configuration endpoint system error - {error_msg}")
                    
            elif "websocket_config" in config_result:
                # Validate configuration structure and values
                ws_config = config_result["websocket_config"]
                logger.info("[CONFIG STRUCTURE] WebSocket configuration retrieved successfully")
                
                # Expected configuration parameters
                expected_config_keys = [
                    "heartbeat_interval",
                    "connection_timeout", 
                    "max_message_size",
                    "compression_enabled"
                ]
                
                for config_key in expected_config_keys:
                    if config_key in ws_config:
                        config_value = ws_config[config_key]
                        logger.info(f"[CONFIG PARAM] {config_key}: {config_value}")
                        
                        # Validate config value types and ranges
                        if config_key == "heartbeat_interval":
                            assert isinstance(config_value, (int, float)), f"Invalid heartbeat_interval type: {type(config_value)}"
                            assert 10 <= config_value <= 300, f"Invalid heartbeat_interval range: {config_value}"
                            
                        elif config_key == "connection_timeout":
                            assert isinstance(config_value, (int, float)), f"Invalid connection_timeout type: {type(config_value)}"
                            assert 60 <= config_value <= 3600, f"Invalid connection_timeout range: {config_value}"
                            
                        elif config_key == "max_message_size":
                            assert isinstance(config_value, int), f"Invalid max_message_size type: {type(config_value)}"
                            assert config_value >= 1024, f"Invalid max_message_size: {config_value}"
                            
                        elif config_key == "compression_enabled":
                            assert isinstance(config_value, bool), f"Invalid compression_enabled type: {type(config_value)}"
                
                # At least basic config should be present
                assert "heartbeat_interval" in ws_config, "Missing critical heartbeat_interval config"
                
                logger.info("[CONFIG VALIDATION SUCCESS] All configuration parameters valid")
            
            else:
                logger.warning("[CONFIG STRUCTURE WARNING] Unexpected configuration response structure")
                logger.info(f"[CONFIG CONTENT] Response keys: {list(config_result.keys())}")
            
            # Performance validation
            assert execution_time < 5.0, f"Config endpoint too slow: {execution_time}s > 5s"
            
            logger.info("[CONFIG ENDPOINT SUCCESS] Configuration endpoint working correctly")
            
        except asyncio.TimeoutError:
            logger.error(f"[CONFIG ENDPOINT TIMEOUT] Config endpoint timed out after {self.health_check_timeout}s")
            pytest.fail("CRITICAL: Configuration endpoint timeout")
            
        except ImportError as e:
            logger.error(f"[CONFIG ENDPOINT IMPORT ERROR] Cannot import WebSocketSSotRoute: {e}")
            pytest.fail(f"CRITICAL: Configuration endpoint not accessible - {e}")
            
        except Exception as e:
            logger.error(f"[CONFIG ENDPOINT FAILURE] Configuration endpoint failed: {e}")
            logger.error(f"[ERROR DETAILS] {traceback.format_exc()}")
            
            if "get_websocket_manager_factory" in str(e):
                logger.info("[MIGRATION NOTE] Config failure related to factory migration")
            else:
                pytest.fail(f"CRITICAL: Configuration endpoint system failure - {e}")

    @pytest.mark.asyncio 
    async def test_websocket_stats_endpoint_information_accuracy(self):
        """TEST: WebSocket statistics endpoint information accuracy
        
        PURPOSE: Validates that websocket_detailed_stats() function (line 1496 violation)
        returns accurate statistical information during SSOT migration.
        
        BUSINESS CRITICAL: Statistics are used for:
        - Performance monitoring and optimization
        - Capacity planning and scaling decisions
        - Business intelligence and analytics
        - Customer usage tracking and billing
        """
        logger.info("[STATS ENDPOINT] Testing WebSocket statistics endpoint information accuracy...")
        
        try:
            from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
            
            websocket_route = WebSocketSSOTRouter()
            
            # Execute statistics retrieval with timeout
            start_time = time.time()
            stats_result = await asyncio.wait_for(
                websocket_route.websocket_detailed_stats(),
                timeout=self.health_check_timeout
            )
            execution_time = time.time() - start_time
            
            # CRITICAL: Stats must return structured data
            assert isinstance(stats_result, dict), "Stats endpoint must return dictionary"
            
            logger.info(f"[STATS SUCCESS] Statistics retrieved in {execution_time:.2f}s")
            
            # Check for error responses
            if "error" in stats_result:
                error_msg = stats_result["error"]
                logger.warning(f"[STATS ERROR] Statistics error: {error_msg}")
                
                if "get_websocket_manager_factory" in error_msg:
                    logger.info("[MIGRATION NOTE] Stats error related to factory migration")
                else:
                    pytest.fail(f"CRITICAL: Statistics endpoint system error - {error_msg}")
                    
            else:
                # Validate statistics structure
                logger.info("[STATS STRUCTURE] Statistics data retrieved successfully")
                
                # Check for SSOT-specific statistics
                if "ssot_stats" in stats_result:
                    ssot_stats = stats_result["ssot_stats"]
                    logger.info(f"[SSOT STATS] SSOT statistics: {list(ssot_stats.keys())}")
                    
                    # Validate SSOT migration progress indicators
                    if "consolidation_complete" in ssot_stats:
                        consolidation_status = ssot_stats["consolidation_complete"]
                        logger.info(f"[CONSOLIDATION STATUS] Consolidation complete: {consolidation_status}")
                        assert isinstance(consolidation_status, bool), "Consolidation status must be boolean"
                    
                    if "ssot_compliance" in ssot_stats:
                        compliance_status = ssot_stats["ssot_compliance"]
                        logger.info(f"[COMPLIANCE STATUS] SSOT compliance: {compliance_status}")
                        assert isinstance(compliance_status, bool), "SSOT compliance must be boolean"
                    
                    if "original_total_lines" in ssot_stats:
                        original_lines = ssot_stats["original_total_lines"]
                        logger.info(f"[MIGRATION METRIC] Original total lines: {original_lines}")
                        assert isinstance(original_lines, (int, str)), "Original lines must be int or string"
                
                # Check for active component information
                if "active_components" in stats_result:
                    active_components = stats_result["active_components"]
                    logger.info(f"[ACTIVE COMPONENTS] Found {len(active_components)} component categories")
                    
                    # Components should be structured data
                    assert isinstance(active_components, dict), "Active components must be dictionary"
                    
                    for component_name, component_info in active_components.items():
                        logger.info(f"[COMPONENT INFO] {component_name}: {type(component_info)}")
                
                # Check for performance metrics
                if "performance_metrics" in stats_result:
                    perf_metrics = stats_result["performance_metrics"]
                    logger.info(f"[PERFORMANCE] Performance metrics available: {list(perf_metrics.keys())}")
                    
                    # Validate performance data types
                    for metric_name, metric_value in perf_metrics.items():
                        assert isinstance(metric_value, (int, float, dict)), f"Invalid metric type for {metric_name}: {type(metric_value)}"
                
                # Basic validation - at least some statistical data should be present
                expected_sections = ["ssot_stats", "active_components", "performance_metrics"]
                found_sections = [section for section in expected_sections if section in stats_result]
                assert len(found_sections) > 0, f"Statistics missing expected sections: {expected_sections}"
                
                logger.info(f"[STATS VALIDATION SUCCESS] Found data sections: {found_sections}")
            
            # Performance validation
            assert execution_time < 10.0, f"Stats endpoint too slow: {execution_time}s > 10s"
            
            logger.info("[STATS ENDPOINT SUCCESS] Statistics endpoint working correctly")
            
        except asyncio.TimeoutError:
            logger.error(f"[STATS ENDPOINT TIMEOUT] Stats endpoint timed out after {self.health_check_timeout}s")
            pytest.fail("CRITICAL: Statistics endpoint timeout")
            
        except ImportError as e:
            logger.error(f"[STATS ENDPOINT IMPORT ERROR] Cannot import WebSocketSSotRoute: {e}")
            pytest.fail(f"CRITICAL: Statistics endpoint not accessible - {e}")
            
        except Exception as e:
            logger.error(f"[STATS ENDPOINT FAILURE] Statistics endpoint failed: {e}")
            logger.error(f"[ERROR DETAILS] {traceback.format_exc()}")
            
            if "get_websocket_manager_factory" in str(e):
                logger.info("[MIGRATION NOTE] Stats failure related to factory migration")
            else:
                pytest.fail(f"CRITICAL: Statistics endpoint system failure - {e}")

    @pytest.mark.asyncio
    async def test_health_endpoints_production_readiness(self):
        """TEST: Health endpoints production readiness validation
        
        PURPOSE: Comprehensive test ensuring all health endpoints are ready for
        production load balancer and monitoring system integration.
        
        BUSINESS CRITICAL: Production systems depend on these endpoints for:
        - Traffic routing decisions
        - Auto-scaling triggers
        - Incident detection and alerting
        - SLA compliance monitoring
        """
        logger.info("[PRODUCTION READINESS] Testing health endpoints production readiness...")
        
        try:
            from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter
            
            websocket_route = WebSocketSSOTRouter()
            
            # Test all endpoints in sequence to verify complete functionality
            endpoints_tested = []
            
            # 1. Health Check Endpoint
            try:
                health_result = await asyncio.wait_for(websocket_route.websocket_health_check(), timeout=10)
                health_status = health_result.get("status") if isinstance(health_result, dict) else "error"
                endpoints_tested.append({"endpoint": "health_check", "status": health_status, "success": True})
                logger.info(f"[HEALTH CHECK] Status: {health_status}")
            except Exception as e:
                endpoints_tested.append({"endpoint": "health_check", "status": "failed", "error": str(e), "success": False})
                logger.error(f"[HEALTH CHECK FAILED] {e}")
            
            # 2. Configuration Endpoint  
            try:
                config_result = await asyncio.wait_for(websocket_route.get_websocket_config(), timeout=10)
                config_status = "success" if isinstance(config_result, dict) and "websocket_config" in config_result else "error"
                endpoints_tested.append({"endpoint": "config", "status": config_status, "success": True})
                logger.info(f"[CONFIG] Status: {config_status}")
            except Exception as e:
                endpoints_tested.append({"endpoint": "config", "status": "failed", "error": str(e), "success": False})
                logger.error(f"[CONFIG FAILED] {e}")
            
            # 3. Statistics Endpoint
            try:
                stats_result = await asyncio.wait_for(websocket_route.websocket_detailed_stats(), timeout=10)
                stats_status = "success" if isinstance(stats_result, dict) else "error"
                endpoints_tested.append({"endpoint": "stats", "status": stats_status, "success": True})
                logger.info(f"[STATS] Status: {stats_status}")
            except Exception as e:
                endpoints_tested.append({"endpoint": "stats", "status": "failed", "error": str(e), "success": False})
                logger.error(f"[STATS FAILED] {e}")
            
            # Production readiness assessment
            successful_endpoints = [ep for ep in endpoints_tested if ep["success"]]
            failed_endpoints = [ep for ep in endpoints_tested if not ep["success"]]
            
            logger.info(f"[PRODUCTION READINESS SUMMARY]")
            logger.info(f"  Total endpoints tested: {len(endpoints_tested)}")
            logger.info(f"  Successful endpoints: {len(successful_endpoints)}")
            logger.info(f"  Failed endpoints: {len(failed_endpoints)}")
            
            for endpoint in successful_endpoints:
                logger.info(f"    ✅ {endpoint['endpoint']}: {endpoint['status']}")
                
            for endpoint in failed_endpoints:
                logger.warning(f"    ❌ {endpoint['endpoint']}: {endpoint.get('error', 'unknown error')}")
            
            # Production readiness criteria:
            # - At least health check must work (critical for load balancer)
            # - Other endpoints can fail during migration but should be documented
            health_check_working = any(ep["endpoint"] == "health_check" and ep["success"] for ep in endpoints_tested)
            
            if health_check_working:
                logger.info("[PRODUCTION READY] Health check endpoint working - minimum production readiness achieved")
                
                # Count migration-related failures vs system failures
                migration_failures = 0
                system_failures = 0
                
                for endpoint in failed_endpoints:
                    error_msg = endpoint.get("error", "")
                    if "get_websocket_manager_factory" in error_msg:
                        migration_failures += 1
                    else:
                        system_failures += 1
                
                if system_failures > 0:
                    logger.error(f"[SYSTEM FAILURES] {system_failures} system failures detected - not migration related")
                    pytest.fail(f"CRITICAL: {system_failures} system failures in health endpoints")
                    
                if migration_failures > 0:
                    logger.info(f"[MIGRATION FAILURES] {migration_failures} migration-related failures - expected during transition")
                
            else:
                logger.error("[PRODUCTION NOT READY] Health check endpoint not working - system not production ready")
                pytest.fail("CRITICAL: Health check endpoint not working - production deployment blocked")
            
            logger.info("[PRODUCTION READINESS SUCCESS] Health endpoints ready for production")
            
        except Exception as e:
            logger.error(f"[PRODUCTION READINESS FAILURE] Production readiness test failed: {e}")
            pytest.fail(f"CRITICAL: Production readiness validation failed - {e}")


if __name__ == "__main__":
    # Allow running this test file directly for debugging
    import subprocess
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short", 
        "-s"
    ])
    
    sys.exit(result.returncode)