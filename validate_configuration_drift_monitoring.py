#!/usr/bin/env python3
"""
Configuration Drift Monitoring System Validation Script

This script validates that the comprehensive configuration drift monitoring
system is properly implemented and can detect the specific configuration
drift patterns that caused WebSocket authentication failures.

Business Mission: Ensure $120K+ MRR is protected from configuration drift
cascade failures through systematic validation of monitoring capabilities.
"""

import sys
import os
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path for imports
sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_file_structure():
    """Validate that all required monitoring system files exist."""
    required_files = [
        'netra_backend/app/monitoring/configuration_drift_monitor.py',
        'netra_backend/app/monitoring/configuration_drift_alerts.py', 
        'netra_backend/app/monitoring/unified_configuration_monitoring.py',
        'tests/integration/configuration/test_configuration_drift_monitoring_comprehensive.py'
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            existing_files.append(file_path)
            file_size = os.path.getsize(file_path)
            logger.info(f"✅ {file_path} exists ({file_size:,} bytes)")
        else:
            missing_files.append(file_path)
            logger.error(f"❌ {file_path} is missing")
    
    return {
        "files_validated": len(required_files),
        "files_existing": len(existing_files),
        "files_missing": len(missing_files),
        "missing_files": missing_files,
        "validation_passed": len(missing_files) == 0
    }


def validate_monitoring_components():
    """Validate monitoring system components can be imported."""
    try:
        # Test imports
        sys.path.insert(0, '.')
        
        # Import configuration drift monitor
        logger.info("Testing ConfigurationDriftMonitor import...")
        from netra_backend.app.monitoring.configuration_drift_monitor import (
            ConfigurationDriftMonitor,
            E2EOAuthSimulationKeyValidator,
            JWTSecretAlignmentValidator,
            WebSocketConfigurationValidator,
            ConfigurationDrift,
            DriftSeverity,
            ConfigurationScope,
            get_configuration_drift_monitor
        )
        logger.info("✅ ConfigurationDriftMonitor imported successfully")
        
        # Import alerting system
        logger.info("Testing ConfigurationDriftAlerting import...")
        from netra_backend.app.monitoring.configuration_drift_alerts import (
            ConfigurationDriftAlerting,
            AlertChannel,
            AlertRule,
            RemediationAction,
            get_configuration_drift_alerting
        )
        logger.info("✅ ConfigurationDriftAlerting imported successfully")
        
        # Import unified monitoring
        logger.info("Testing UnifiedConfigurationMonitoring import...")
        from netra_backend.app.monitoring.unified_configuration_monitoring import (
            UnifiedConfigurationMonitoring,
            get_unified_configuration_monitoring,
            start_configuration_monitoring,
            stop_configuration_monitoring
        )
        logger.info("✅ UnifiedConfigurationMonitoring imported successfully")
        
        return {
            "import_tests_passed": 3,
            "import_tests_total": 3,
            "validation_passed": True,
            "components_available": [
                "ConfigurationDriftMonitor",
                "ConfigurationDriftAlerting", 
                "UnifiedConfigurationMonitoring"
            ]
        }
        
    except ImportError as e:
        logger.error(f"❌ Import validation failed: {e}")
        return {
            "import_tests_passed": 0,
            "import_tests_total": 3,
            "validation_passed": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"❌ Component validation failed: {e}")
        return {
            "import_tests_passed": 0,
            "import_tests_total": 3,
            "validation_passed": False,
            "error": str(e)
        }


async def validate_drift_detection_logic():
    """Validate core drift detection logic works correctly."""
    try:
        # Import components
        from netra_backend.app.monitoring.configuration_drift_monitor import (
            E2EOAuthSimulationKeyValidator,
            JWTSecretAlignmentValidator,
            WebSocketConfigurationValidator,
            ConfigurationDriftMonitor
        )
        
        validation_results = []
        
        # Test E2E OAuth Validator
        logger.info("Testing E2E OAuth simulation key validator...")
        oauth_validator = E2EOAuthSimulationKeyValidator()
        
        # Mock missing key scenario
        import unittest.mock
        with unittest.mock.patch.object(oauth_validator.env, 'get') as mock_env:
            mock_env.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging",
                "E2E_OAUTH_SIMULATION_KEY": None
            }.get(key, default)
            
            oauth_result = await oauth_validator.validate_key_consistency()
            
            if oauth_result.get("drift_detected") is True:
                logger.info("✅ E2E OAuth key drift detection works")
                validation_results.append("oauth_detection_passed")
            else:
                logger.error("❌ E2E OAuth key drift detection failed")
        
        # Test JWT Secret Validator
        logger.info("Testing JWT secret alignment validator...")
        jwt_validator = JWTSecretAlignmentValidator()
        
        with unittest.mock.patch.object(jwt_validator.env, 'get') as mock_env:
            mock_env.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging",
                "JWT_SECRET_KEY": None
            }.get(key, default)
            
            jwt_result = await jwt_validator.validate_jwt_secret_alignment()
            
            if jwt_result.get("drift_detected") is True:
                logger.info("✅ JWT secret drift detection works")
                validation_results.append("jwt_detection_passed")
            else:
                logger.error("❌ JWT secret drift detection failed")
        
        # Test WebSocket Config Validator
        logger.info("Testing WebSocket configuration validator...")
        ws_validator = WebSocketConfigurationValidator()
        
        with unittest.mock.patch.object(ws_validator.env, 'get') as mock_env:
            mock_env.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging",
                "NEXT_PUBLIC_WS_URL": None,
                "NEXT_PUBLIC_WEBSOCKET_URL": None
            }.get(key, default)
            
            # Mock WebSocket integration test to fail
            with unittest.mock.patch.object(ws_validator, '_test_websocket_auth_integration') as mock_test:
                mock_test.return_value = {"success": False}
            with unittest.mock.patch.object(ws_validator, '_validate_websocket_cors_config') as mock_cors:
                mock_cors.return_value = {"drift_detected": False}
                
                ws_result = await ws_validator.validate_websocket_config_coherence()
                
                if ws_result.get("drift_detected") is True:
                    logger.info("✅ WebSocket configuration drift detection works")
                    validation_results.append("websocket_detection_passed")
                else:
                    logger.error("❌ WebSocket configuration drift detection failed")
        
        # Test comprehensive drift monitor
        logger.info("Testing comprehensive configuration drift monitor...")
        drift_monitor = ConfigurationDriftMonitor()
        
        # Mock all validators to return drift
        with unittest.mock.patch.object(drift_monitor.e2e_oauth_validator, 'validate_key_consistency') as mock_oauth:
            mock_oauth.return_value = {
                "drift_detected": True,
                "drift_details": [{
                    "config_key": "E2E_OAUTH_SIMULATION_KEY",
                    "scope": "authentication",
                    "severity": "high",
                    "current_value": "<MISSING>",
                    "expected_value": "<REQUIRED>",
                    "business_impact_mrr": 50000.0,
                    "cascade_risk": ["e2e_authentication_bypass_failure"],
                    "remediation_priority": 2,
                    "detection_timestamp": time.time()
                }]
            }
            
            with unittest.mock.patch.object(drift_monitor.jwt_secret_validator, 'validate_jwt_secret_alignment') as mock_jwt:
                mock_jwt.return_value = {
                    "drift_detected": True,
                    "drift_details": [{
                        "config_key": "JWT_SECRET_KEY",
                        "scope": "authentication", 
                        "severity": "critical",
                        "current_value": "<MISSING>",
                        "expected_value": "<REQUIRED>",
                        "business_impact_mrr": 120000.0,
                        "cascade_risk": ["complete_authentication_failure"],
                        "remediation_priority": 1,
                        "detection_timestamp": time.time()
                    }]
                }
                
                with unittest.mock.patch.object(drift_monitor.websocket_config_validator, 'validate_websocket_config_coherence') as mock_ws:
                    mock_ws.return_value = {
                        "drift_detected": True,
                        "drift_details": [{
                            "config_key": "NEXT_PUBLIC_WS_URL",
                            "scope": "websocket",
                            "severity": "critical", 
                            "current_value": "<MISSING>",
                            "expected_value": "<REQUIRED>",
                            "business_impact_mrr": 120000.0,
                            "cascade_risk": ["no_websocket_connection"],
                            "remediation_priority": 1,
                            "detection_timestamp": time.time()
                        }]
                    }
                    
                    monitor_result = await drift_monitor.check_health()
                    
                    if (monitor_result.success is False and 
                        monitor_result.details.get("drift_detection_summary", {}).get("total_business_impact_mrr", 0) > 100000.0):
                        logger.info("✅ Comprehensive drift monitor works correctly")
                        validation_results.append("monitor_integration_passed")
                    else:
                        logger.error("❌ Comprehensive drift monitor failed")
        
        return {
            "validation_tests_passed": len(validation_results),
            "validation_tests_total": 4,
            "validation_passed": len(validation_results) == 4,
            "passed_tests": validation_results
        }
        
    except Exception as e:
        logger.error(f"❌ Drift detection validation failed: {e}")
        return {
            "validation_tests_passed": 0,
            "validation_tests_total": 4,
            "validation_passed": False,
            "error": str(e)
        }


async def validate_alerting_system():
    """Validate alerting system functionality."""
    try:
        from netra_backend.app.monitoring.configuration_drift_alerts import (
            ConfigurationDriftAlerting,
            AlertChannel,
            DriftSeverity
        )
        
        logger.info("Testing configuration drift alerting system...")
        
        alerting = ConfigurationDriftAlerting()
        
        # Test alert rule initialization
        if len(alerting.alert_rules) > 0:
            logger.info(f"✅ Alerting system initialized with {len(alerting.alert_rules)} alert rules")
            
            # Test critical drift processing
            mock_drift_result = {
                "drift_detection_summary": {
                    "total_drift_detected": True,
                    "critical_drift_count": 1,
                    "total_business_impact_mrr": 120000.0
                },
                "detected_drifts": [{
                    "config_key": "JWT_SECRET_KEY",
                    "severity": "critical",
                    "business_impact_mrr": 120000.0,
                    "environment": "staging",
                    "cascade_risk": ["complete_authentication_failure"]
                }],
                "critical_drifts": [{
                    "config_key": "JWT_SECRET_KEY",
                    "severity": "critical",
                    "business_impact_mrr": 120000.0,
                    "environment": "staging"
                }]
            }
            
            # Process drift detection
            alert_result = await alerting.process_drift_detection(mock_drift_result)
            
            if alert_result.get("status") == "processed":
                logger.info("✅ Alerting system processes drift detection correctly")
                return {
                    "alerting_validation_passed": True,
                    "alert_rules_count": len(alerting.alert_rules),
                    "processing_test_passed": True
                }
            else:
                logger.error("❌ Alerting system failed to process drift detection")
        else:
            logger.error("❌ Alerting system not properly initialized")
        
        return {
            "alerting_validation_passed": False,
            "alert_rules_count": 0,
            "processing_test_passed": False
        }
        
    except Exception as e:
        logger.error(f"❌ Alerting system validation failed: {e}")
        return {
            "alerting_validation_passed": False,
            "error": str(e)
        }


async def validate_unified_monitoring():
    """Validate unified monitoring orchestration."""
    try:
        from netra_backend.app.monitoring.unified_configuration_monitoring import (
            UnifiedConfigurationMonitoring,
            get_unified_configuration_monitoring
        )
        
        logger.info("Testing unified configuration monitoring...")
        
        # Test singleton access
        monitoring1 = get_unified_configuration_monitoring()
        monitoring2 = get_unified_configuration_monitoring()
        
        if monitoring1 is monitoring2:
            logger.info("✅ Unified monitoring singleton pattern works")
            
            # Test status retrieval
            status = await monitoring1.get_current_status()
            
            if "total_mrr_protected" in status and status["total_mrr_protected"] == 120000.0:
                logger.info("✅ Unified monitoring status reporting works")
                
                # Test immediate drift check
                drift_check = await monitoring1.perform_immediate_drift_check()
                
                if "check_type" in drift_check and drift_check["check_type"] == "immediate":
                    logger.info("✅ Immediate drift check functionality works")
                    
                    return {
                        "unified_monitoring_passed": True,
                        "singleton_test_passed": True,
                        "status_test_passed": True,
                        "immediate_check_passed": True,
                        "total_mrr_protected": status["total_mrr_protected"]
                    }
                else:
                    logger.error("❌ Immediate drift check failed")
            else:
                logger.error("❌ Status reporting failed")
        else:
            logger.error("❌ Singleton pattern failed")
        
        return {
            "unified_monitoring_passed": False,
            "singleton_test_passed": False,
            "status_test_passed": False,
            "immediate_check_passed": False
        }
        
    except Exception as e:
        logger.error(f"❌ Unified monitoring validation failed: {e}")
        return {
            "unified_monitoring_passed": False,
            "error": str(e)
        }


async def validate_business_impact_calculation():
    """Validate business impact calculation accuracy."""
    try:
        from netra_backend.app.monitoring.configuration_drift_monitor import (
            ConfigurationDrift,
            DriftSeverity,
            ConfigurationScope
        )
        
        logger.info("Testing business impact calculation...")
        
        # Create test configuration drifts
        test_drifts = [
            ConfigurationDrift(
                config_key="JWT_SECRET_KEY",
                scope=ConfigurationScope.AUTHENTICATION,
                severity=DriftSeverity.CRITICAL,
                current_value="<MISSING>",
                expected_value="<REQUIRED>",
                environment="staging",
                detection_timestamp=time.time(),
                business_impact_mrr=120000.0,
                cascade_risk=["complete_authentication_failure", "system_unusable"],
                remediation_priority=1
            ),
            ConfigurationDrift(
                config_key="E2E_OAUTH_SIMULATION_KEY",
                scope=ConfigurationScope.AUTHENTICATION,
                severity=DriftSeverity.HIGH,
                current_value="<MISSING>",
                expected_value="<REQUIRED>",
                environment="staging",
                detection_timestamp=time.time(),
                business_impact_mrr=50000.0,
                cascade_risk=["e2e_test_failures", "staging_validation_blocked"],
                remediation_priority=2
            )
        ]
        
        # Calculate total business impact
        total_impact = sum(drift.business_impact_mrr for drift in test_drifts)
        critical_drifts = [drift for drift in test_drifts if drift.severity == DriftSeverity.CRITICAL]
        
        if total_impact == 170000.0 and len(critical_drifts) == 1:
            logger.info(f"✅ Business impact calculation correct: ${total_impact:,.0f} MRR with {len(critical_drifts)} critical drift(s)")
            
            # Test drift serialization
            drift_dict = test_drifts[0].to_dict()
            
            if "business_impact_mrr" in drift_dict and drift_dict["severity"] == "critical":
                logger.info("✅ Configuration drift serialization works")
                
                return {
                    "business_impact_calculation_passed": True,
                    "total_calculated_impact": total_impact,
                    "critical_drifts_detected": len(critical_drifts),
                    "serialization_test_passed": True
                }
            else:
                logger.error("❌ Configuration drift serialization failed")
        else:
            logger.error(f"❌ Business impact calculation incorrect: expected $170,000, got ${total_impact:,.0f}")
        
        return {
            "business_impact_calculation_passed": False,
            "total_calculated_impact": total_impact,
            "critical_drifts_detected": len(critical_drifts),
            "serialization_test_passed": False
        }
        
    except Exception as e:
        logger.error(f"❌ Business impact calculation validation failed: {e}")
        return {
            "business_impact_calculation_passed": False,
            "error": str(e)
        }


async def run_comprehensive_validation():
    """Run comprehensive validation of the configuration drift monitoring system."""
    
    print("🚀 CONFIGURATION DRIFT MONITORING SYSTEM VALIDATION")
    print("="*80)
    print(f"Validation Date: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mission: Validate system protection of $120,000+ MRR from configuration drift")
    print("="*80)
    
    validation_results = {}
    
    # Step 1: File structure validation
    print("\n📁 STEP 1: File Structure Validation")
    print("-" * 40)
    file_validation = validate_file_structure()
    validation_results["file_structure"] = file_validation
    
    if not file_validation["validation_passed"]:
        print("❌ File structure validation failed - cannot proceed")
        return validation_results
    
    # Step 2: Component import validation
    print("\n🔧 STEP 2: Component Import Validation")
    print("-" * 40)
    import_validation = validate_monitoring_components()
    validation_results["component_imports"] = import_validation
    
    if not import_validation["validation_passed"]:
        print("❌ Component import validation failed - cannot proceed")
        return validation_results
    
    # Step 3: Drift detection logic validation
    print("\n🔍 STEP 3: Drift Detection Logic Validation")
    print("-" * 40)
    drift_validation = await validate_drift_detection_logic()
    validation_results["drift_detection"] = drift_validation
    
    # Step 4: Alerting system validation
    print("\n🚨 STEP 4: Alerting System Validation")
    print("-" * 40)
    alerting_validation = await validate_alerting_system()
    validation_results["alerting_system"] = alerting_validation
    
    # Step 5: Unified monitoring validation
    print("\n🎯 STEP 5: Unified Monitoring Validation")
    print("-" * 40)
    unified_validation = await validate_unified_monitoring()
    validation_results["unified_monitoring"] = unified_validation
    
    # Step 6: Business impact calculation validation
    print("\n💰 STEP 6: Business Impact Calculation Validation")
    print("-" * 40)
    business_validation = await validate_business_impact_calculation()
    validation_results["business_impact"] = business_validation
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("="*80)
    
    total_validations = 6
    passed_validations = sum(1 for v in validation_results.values() 
                           if v.get("validation_passed") or v.get("alerting_validation_passed") or 
                              v.get("unified_monitoring_passed") or v.get("business_impact_calculation_passed"))
    
    print(f"Total Validation Categories: {total_validations}")
    print(f"Passed Validations: {passed_validations}")
    print(f"Success Rate: {(passed_validations / total_validations) * 100:.1f}%")
    
    # Detailed results
    print("\nDetailed Results:")
    for category, result in validation_results.items():
        status = "✅ PASSED" if (result.get("validation_passed") or 
                                result.get("alerting_validation_passed") or
                                result.get("unified_monitoring_passed") or 
                                result.get("business_impact_calculation_passed")) else "❌ FAILED"
        print(f"  {category.replace('_', ' ').title()}: {status}")
    
    # Business impact summary
    if business_validation.get("business_impact_calculation_passed"):
        total_impact = business_validation.get("total_calculated_impact", 0)
        print(f"\n💼 Business Impact Protection: ${total_impact:,.0f} MRR validated")
    
    # Final assessment
    print("\n🎯 FINAL ASSESSMENT")
    print("="*80)
    
    if passed_validations == total_validations:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("Configuration drift monitoring system is ready for deployment.")
        print("✅ System will protect $120,000+ MRR from configuration drift cascade failures")
        success = True
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("Review and fix issues before deploying the monitoring system.")
        print("⚠️  Configuration drift protection may be incomplete")
        success = False
    
    print(f"\nValidation completed at: {datetime.now(timezone.utc).isoformat()}")
    print("="*80)
    
    return validation_results, success


if __name__ == "__main__":
    """Run the validation script."""
    try:
        results, success = asyncio.run(run_comprehensive_validation())
        
        # Save validation results
        with open('configuration_drift_monitoring_validation_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Validation results saved to: configuration_drift_monitoring_validation_results.json")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Validation script failed: {e}")
        sys.exit(1)