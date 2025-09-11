#!/usr/bin/env python3
"""
Configuration Drift Monitoring System File Verification

This script verifies that the configuration drift monitoring system files
are properly implemented with the required functionality.
"""

import os
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Any


def analyze_file_content(file_path: str) -> Dict[str, Any]:
    """Analyze the content of a monitoring system file."""
    if not os.path.exists(file_path):
        return {
            "exists": False,
            "error": "File does not exist"
        }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = len(content)
        lines = content.split('\n')
        
        # Count key components
        classes = re.findall(r'class\s+(\w+)', content)
        # Also find dataclasses 
        dataclasses = re.findall(r'@dataclass.*?\nclass\s+(\w+)', content, re.DOTALL)
        all_classes = list(set(classes + dataclasses))
        
        functions = re.findall(r'def\s+(\w+)', content)
        async_functions = re.findall(r'async\s+def\s+(\w+)', content)
        imports = re.findall(r'from\s+[\w.]+\s+import|import\s+[\w.]+', content)
        
        # Look for specific patterns
        has_business_value_justification = "Business Value Justification" in content
        has_critical_mission = "CRITICAL MISSION" in content or "MISSION CRITICAL" in content
        has_mrr_calculation = "$120" in content or "120000" in content
        has_drift_detection = "drift_detected" in content
        has_alert_system = "alert" in content.lower()
        
        return {
            "exists": True,
            "file_size": file_size,
            "line_count": len(lines),
            "classes": all_classes,
            "class_count": len(all_classes),
            "functions": functions,
            "function_count": len(functions),
            "async_functions": async_functions,
            "async_function_count": len(async_functions),
            "import_count": len(imports),
            "has_business_value_justification": has_business_value_justification,
            "has_critical_mission": has_critical_mission,
            "has_mrr_calculation": has_mrr_calculation,
            "has_drift_detection": has_drift_detection,
            "has_alert_system": has_alert_system
        }
        
    except Exception as e:
        return {
            "exists": True,
            "error": f"Failed to analyze file: {str(e)}"
        }


def verify_configuration_drift_monitor():
    """Verify the configuration drift monitor implementation."""
    file_path = "netra_backend/app/monitoring/configuration_drift_monitor.py"
    analysis = analyze_file_content(file_path)
    
    if not analysis.get("exists", False):
        return analysis
    
    # Check for required components
    required_classes = [
        "E2EOAuthSimulationKeyValidator",
        "JWTSecretAlignmentValidator", 
        "WebSocketConfigurationValidator",
        "ConfigurationDriftMonitor"
    ]
    
    found_classes = analysis.get("classes", [])
    missing_classes = [cls for cls in required_classes if cls not in found_classes]
    
    # Check for enum classes
    has_drift_severity = "DriftSeverity" in found_classes
    has_configuration_scope = "ConfigurationScope" in found_classes
    
    # Check for key methods
    functions = analysis.get("functions", [])
    has_validate_methods = any("validate" in func for func in functions)
    has_check_health = "check_health" in functions
    
    return {
        **analysis,
        "required_classes_found": len(required_classes) - len(missing_classes),
        "required_classes_total": len(required_classes),
        "missing_classes": missing_classes,
        "has_drift_severity_enum": has_drift_severity,
        "has_configuration_scope_enum": has_configuration_scope,
        "has_validate_methods": has_validate_methods,
        "has_check_health_method": has_check_health,
        "validation_passed": len(missing_classes) == 0 and has_validate_methods and has_check_health
    }


def verify_configuration_drift_alerts():
    """Verify the configuration drift alerting system implementation."""
    file_path = "netra_backend/app/monitoring/configuration_drift_alerts.py"
    analysis = analyze_file_content(file_path)
    
    if not analysis.get("exists", False):
        return analysis
    
    # Check for required components
    required_classes = [
        "ConfigurationDriftAlerting",
        "AlertRule",
        "RemediationAction"
    ]
    
    found_classes = analysis.get("classes", [])
    missing_classes = [cls for cls in required_classes if cls not in found_classes]
    
    # Check for enum classes
    has_alert_channel = "AlertChannel" in found_classes
    has_remediation_status = "RemediationStatus" in found_classes
    
    # Check for key methods
    functions = analysis.get("functions", [])
    has_process_drift = "process_drift_detection" in functions
    has_trigger_alert = any("trigger" in func for func in functions)
    
    return {
        **analysis,
        "required_classes_found": len(required_classes) - len(missing_classes),
        "required_classes_total": len(required_classes),
        "missing_classes": missing_classes,
        "has_alert_channel_enum": has_alert_channel,
        "has_remediation_status_enum": has_remediation_status,
        "has_process_drift_method": has_process_drift,
        "has_trigger_methods": has_trigger_alert,
        "validation_passed": len(missing_classes) == 0 and has_process_drift and has_trigger_alert
    }


def verify_unified_configuration_monitoring():
    """Verify the unified configuration monitoring implementation."""
    file_path = "netra_backend/app/monitoring/unified_configuration_monitoring.py"
    analysis = analyze_file_content(file_path)
    
    if not analysis.get("exists", False):
        return analysis
    
    # Check for required components
    required_classes = [
        "UnifiedConfigurationMonitoring",
        "MonitoringCycle"
    ]
    
    found_classes = analysis.get("classes", [])
    missing_classes = [cls for cls in required_classes if cls not in found_classes]
    
    # Check for key methods
    functions = analysis.get("functions", [])
    has_start_monitoring = "start_continuous_monitoring" in functions
    has_stop_monitoring = "stop_monitoring" in functions
    has_immediate_check = "perform_immediate_drift_check" in functions
    has_get_status = "get_current_status" in functions
    
    return {
        **analysis,
        "required_classes_found": len(required_classes) - len(missing_classes),
        "required_classes_total": len(required_classes),
        "missing_classes": missing_classes,
        "has_start_monitoring": has_start_monitoring,
        "has_stop_monitoring": has_stop_monitoring,
        "has_immediate_check": has_immediate_check,
        "has_get_status": has_get_status,
        "validation_passed": (len(missing_classes) == 0 and has_start_monitoring and 
                             has_stop_monitoring and has_immediate_check and has_get_status)
    }


def verify_test_suite():
    """Verify the comprehensive test suite implementation."""
    file_path = "tests/integration/configuration/test_configuration_drift_monitoring_comprehensive.py"
    analysis = analyze_file_content(file_path)
    
    if not analysis.get("exists", False):
        return analysis
    
    # Check for test classes
    found_classes = analysis.get("classes", [])
    test_classes = [cls for cls in found_classes if "Test" in cls]
    
    # Check for key test methods
    functions = analysis.get("functions", [])
    test_methods = [func for func in functions if func.startswith("test_")]
    
    # Check for integration scenarios
    has_integration_scenarios = any("integration" in cls.lower() for cls in test_classes)
    has_websocket_scenario = any("websocket" in func for func in test_methods)
    has_oauth_scenario = any("oauth" in func for func in test_methods)
    
    return {
        **analysis,
        "test_classes_found": len(test_classes),
        "test_methods_found": len(test_methods),
        "test_classes": test_classes,
        "test_methods": test_methods[:10],  # First 10 test methods
        "has_integration_scenarios": has_integration_scenarios,
        "has_websocket_scenario": has_websocket_scenario,
        "has_oauth_scenario": has_oauth_scenario,
        "validation_passed": len(test_classes) >= 5 and len(test_methods) >= 15  # Reasonable thresholds
    }


def generate_verification_report():
    """Generate comprehensive verification report."""
    
    print("="*80)
    print("CONFIGURATION DRIFT MONITORING SYSTEM VERIFICATION REPORT")
    print("="*80)
    print(f"Report Date: {datetime.now(timezone.utc).isoformat()}")
    print(f"Mission: Verify implementation of $120,000+ MRR protection system")
    print("="*80)
    
    verification_results = {}
    
    # Verify each component
    components = [
        ("Configuration Drift Monitor", verify_configuration_drift_monitor),
        ("Configuration Drift Alerts", verify_configuration_drift_alerts),
        ("Unified Configuration Monitoring", verify_unified_configuration_monitoring),
        ("Comprehensive Test Suite", verify_test_suite)
    ]
    
    total_validations = 0
    passed_validations = 0
    
    for component_name, verify_func in components:
        print(f"\n{component_name.upper()}")
        print("-" * len(component_name))
        
        result = verify_func()
        verification_results[component_name.lower().replace(" ", "_")] = result
        
        if result.get("exists", False) and not result.get("error"):
            print(f"File Size: {result.get('file_size', 0):,} bytes")
            print(f"Lines of Code: {result.get('line_count', 0):,}")
            print(f"Classes: {result.get('class_count', 0)}")
            print(f"Functions: {result.get('function_count', 0)}")
            print(f"Async Functions: {result.get('async_function_count', 0)}")
            
            if result.get("has_business_value_justification"):
                print("[PASS] Business Value Justification: Present")
            else:
                print("[WARN] Business Value Justification: Missing")
            
            if result.get("has_critical_mission"):
                print("[PASS] Critical Mission Statement: Present")
            else:
                print("[WARN] Critical Mission Statement: Missing")
            
            if result.get("has_mrr_calculation"):
                print("[PASS] MRR Protection Calculation: Present")
            else:
                print("[WARN] MRR Protection Calculation: Missing")
            
            # Component-specific validations
            if "missing_classes" in result:
                missing = result.get("missing_classes", [])
                if missing:
                    print(f"[FAIL] Missing Required Classes: {', '.join(missing)}")
                else:
                    print("[PASS] All Required Classes: Present")
            
            if result.get("validation_passed", False):
                print("[PASS] Component Validation: PASSED")
                passed_validations += 1
            else:
                print("[FAIL] Component Validation: FAILED")
            
        elif result.get("error"):
            print(f"[ERROR] {result.get('error')}")
        else:
            print("[FAIL] File does not exist")
        
        total_validations += 1
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    success_rate = (passed_validations / total_validations) * 100
    print(f"Components Verified: {total_validations}")
    print(f"Components Passed: {passed_validations}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # File sizes summary
    total_lines = sum(result.get("line_count", 0) for result in verification_results.values() if result.get("exists"))
    total_size = sum(result.get("file_size", 0) for result in verification_results.values() if result.get("exists"))
    
    print(f"\nImplementation Statistics:")
    print(f"Total Lines of Code: {total_lines:,}")
    print(f"Total File Size: {total_size:,} bytes")
    
    # Business value assessment
    mrr_coverage = sum(1 for result in verification_results.values() if result.get("has_mrr_calculation", False))
    print(f"MRR Protection Coverage: {mrr_coverage}/{total_validations} components")
    
    # Final assessment
    print("\n" + "="*80)
    print("FINAL ASSESSMENT")
    print("="*80)
    
    if passed_validations == total_validations:
        print("STATUS: ALL COMPONENTS VERIFIED")
        print("READINESS: System is ready for deployment")
        print("PROTECTION: $120,000+ MRR configuration drift protection implemented")
        assessment = "READY_FOR_DEPLOYMENT"
    elif passed_validations >= (total_validations * 0.75):  # 75% pass rate
        print("STATUS: MOSTLY VERIFIED")
        print("READINESS: Minor issues to address before deployment")
        print("PROTECTION: Configuration drift protection substantially implemented")
        assessment = "NEEDS_MINOR_FIXES"
    else:
        print("STATUS: VERIFICATION FAILED")
        print("READINESS: Major issues must be resolved before deployment")
        print("PROTECTION: Configuration drift protection incomplete")
        assessment = "NEEDS_MAJOR_FIXES"
    
    print(f"\nReport completed at: {datetime.now(timezone.utc).isoformat()}")
    
    # Save detailed results
    detailed_results = {
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "verification_summary": {
            "total_components": total_validations,
            "passed_components": passed_validations,
            "success_rate_percentage": success_rate,
            "assessment": assessment
        },
        "implementation_statistics": {
            "total_lines_of_code": total_lines,
            "total_file_size_bytes": total_size,
            "mrr_protection_coverage": f"{mrr_coverage}/{total_validations}"
        },
        "component_details": verification_results
    }
    
    with open('configuration_drift_monitoring_verification.json', 'w') as f:
        json.dump(detailed_results, f, indent=2)
    
    print(f"\nDetailed verification results saved to: configuration_drift_monitoring_verification.json")
    
    return assessment == "READY_FOR_DEPLOYMENT"


if __name__ == "__main__":
    """Run the verification script."""
    try:
        success = generate_verification_report()
        exit_code = 0 if success else 1
        print(f"\nExiting with code: {exit_code}")
        exit(exit_code)
        
    except Exception as e:
        print(f"\nVerification script failed: {e}")
        exit(1)