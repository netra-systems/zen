#!/usr/bin/env python3
"""
CI/CD Compliance Validation Script

This script runs comprehensive compliance validation in CI/CD environments
and returns appropriate exit codes for automated build/deployment decisions.

Usage:
    python scripts/compliance_validation_ci.py [--threshold 90] [--fail-fast] [--report-path PATH]

Exit Codes:
    0 - Full compliance achieved
    1 - Compliance below threshold but not critical
    2 - Critical compliance failures detected
    3 - Validation script failure

Business Value: Platform/Internal - Automated Quality Assurance
Prevents deployment of non-compliant code, protecting $1M+ ARR from stability issues.

Author: Test Validation and Compliance Specialist
Date: 2025-08-30
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def parse_arguments():
    """Parse command line arguments for CI/CD integration."""
    parser = argparse.ArgumentParser(
        description="CI/CD Compliance Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - Full compliance achieved (safe to deploy)
  1 - Compliance below threshold (review required)
  2 - Critical failures (deployment blocked)
  3 - Validation error (fix validation)

Examples:
  python scripts/compliance_validation_ci.py                    # Default validation
  python scripts/compliance_validation_ci.py --threshold 80     # Lower threshold
  python scripts/compliance_validation_ci.py --fail-fast        # Stop on first critical issue
  python scripts/compliance_validation_ci.py --report-path ./   # Custom report location
        """
    )
    
    parser.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        help="Minimum compliance percentage required (default: 90.0)"
    )
    
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit immediately on first critical issue"
    )
    
    parser.add_argument(
        "--report-path",
        type=str,
        default="./",
        help="Directory to save compliance reports (default: current directory)"
    )
    
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format for parsing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def run_compliance_validation(args) -> Dict[str, Any]:
    """
    Run the comprehensive compliance validation suite.
    
    Returns:
        Dict containing validation results and metrics
    """
    try:
        # Import the comprehensive validator
        from tests.mission_critical.test_comprehensive_compliance_validation import (
            ComprehensiveComplianceValidator
        )
        
        if args.verbose:
            print(" SEARCH:  Starting comprehensive compliance validation...")
        
        validator = ComprehensiveComplianceValidator()
        metrics = validator.run_full_compliance_validation()
        
        return {
            "success": True,
            "metrics": metrics,
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "metrics": None,
            "error": str(e)
        }


def evaluate_compliance(metrics, threshold: float, fail_fast: bool) -> Dict[str, Any]:
    """
    Evaluate compliance results and determine appropriate response.
    
    Returns:
        Dict with evaluation results and recommended exit code
    """
    if metrics is None:
        return {
            "status": "ERROR",
            "exit_code": 3,
            "message": "Validation failed to execute",
            "deployment_safe": False
        }
    
    compliance_percentage = metrics.overall_compliance_percentage
    critical_issues = len(metrics.critical_issues)
    
    # Determine status
    if compliance_percentage >= threshold and critical_issues == 0:
        status = "PASS"
        exit_code = 0
        deployment_safe = True
        message = f" PASS:  Full compliance achieved ({compliance_percentage:.1f}%)"
        
    elif critical_issues > 0:
        status = "CRITICAL_FAILURE"
        exit_code = 2
        deployment_safe = False
        message = f" FAIL:  Critical failures detected ({critical_issues} issues)"
        
    elif compliance_percentage < threshold:
        status = "BELOW_THRESHOLD"
        exit_code = 1
        deployment_safe = False
        message = f" WARNING: [U+FE0F] Compliance below threshold ({compliance_percentage:.1f}% < {threshold}%)"
        
    else:
        status = "UNKNOWN"
        exit_code = 1
        deployment_safe = False
        message = "[U+2753] Unknown compliance state"
    
    # Apply fail-fast logic
    if fail_fast and not deployment_safe:
        exit_code = 2
        message += " (fail-fast enabled)"
    
    return {
        "status": status,
        "exit_code": exit_code,
        "message": message,
        "deployment_safe": deployment_safe,
        "compliance_percentage": compliance_percentage,
        "critical_issues": critical_issues
    }


def generate_ci_report(metrics, evaluation, args) -> str:
    """
    Generate CI/CD-friendly compliance report.
    
    Returns:
        Path to the generated report file
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"compliance_ci_report_{timestamp}.json"
    report_path = Path(args.report_path) / report_filename
    
    # Create comprehensive CI report
    ci_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "validation_type": "ci_cd_compliance_check",
        "status": evaluation["status"],
        "deployment_safe": evaluation["deployment_safe"],
        "compliance_percentage": evaluation["compliance_percentage"],
        "threshold": args.threshold,
        "exit_code": evaluation["exit_code"],
        "message": evaluation["message"],
        
        # Detailed metrics
        "metrics": {
            "mock_violations": metrics.mock_violations if metrics else 0,
            "environment_violations": metrics.isolated_environment_violations if metrics else 0,
            "architecture_violations": metrics.architecture_violations if metrics else 0,
            "websocket_events_status": metrics.websocket_events_status if metrics else "UNKNOWN",
            "real_service_connection_status": metrics.real_service_connection_status if metrics else "UNKNOWN",
            "test_quality_score": metrics.test_quality_score if metrics else 0.0
        },
        
        # CI/CD metadata
        "configuration": {
            "threshold": args.threshold,
            "fail_fast": args.fail_fast,
            "verbose": args.verbose
        },
        
        # Action items
        "critical_issues": metrics.critical_issues if metrics else [],
        "recommendations": metrics.recommendations if metrics else [],
        
        # Compliance breakdown
        "compliance_breakdown": {
            "mock_policy": "PASS" if metrics and metrics.mock_violations == 0 else "FAIL",
            "environment_isolation": "PASS" if metrics and metrics.isolated_environment_violations == 0 else "FAIL",
            "architecture_standards": "PASS" if evaluation["compliance_percentage"] >= 90 else "FAIL",
            "websocket_events": metrics.websocket_events_status if metrics else "UNKNOWN",
            "real_services": metrics.real_service_connection_status if metrics else "UNKNOWN"
        }
    }
    
    # Save report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(ci_report, f, indent=2)
    
    return str(report_path)


def print_compliance_summary(evaluation, metrics, verbose=False):
    """Print human-readable compliance summary."""
    print("\n" + "=" * 60)
    print("[U+1F3D7][U+FE0F] CI/CD COMPLIANCE VALIDATION RESULTS")
    print("=" * 60)
    
    print(f"Status: {evaluation['status']}")
    print(f"Message: {evaluation['message']}")
    print(f"Deployment Safe: {' PASS:  YES' if evaluation['deployment_safe'] else ' FAIL:  NO'}")
    print(f"Exit Code: {evaluation['exit_code']}")
    
    if metrics:
        print(f"\n CHART:  Key Metrics:")
        print(f"  Overall Compliance: {evaluation['compliance_percentage']:.1f}%")
        print(f"  Mock Violations: {metrics.mock_violations}")
        print(f"  Environment Issues: {metrics.isolated_environment_violations}")
        print(f"  Architecture Issues: {metrics.architecture_violations}")
        print(f"  WebSocket Status: {metrics.websocket_events_status}")
        print(f"  Real Services: {metrics.real_service_connection_status}")
        
        if verbose and metrics.critical_issues:
            print(f"\n FAIL:  Critical Issues:")
            for issue in metrics.critical_issues:
                print(f"  [U+2022] {issue}")
        
        if verbose and metrics.recommendations:
            print(f"\n[U+1F527] Recommendations:")
            for rec in metrics.recommendations:
                print(f"  [U+2022] {rec}")
    
    print("=" * 60)


def main():
    """Main CI/CD compliance validation entry point."""
    args = parse_arguments()
    
    if args.verbose:
        print("[U+1F680] CI/CD Compliance Validation Starting...")
        print(f"   Threshold: {args.threshold}%")
        print(f"   Fail Fast: {args.fail_fast}")
        print(f"   Report Path: {args.report_path}")
    
    # Run validation
    validation_result = run_compliance_validation(args)
    
    if not validation_result["success"]:
        print(f" FAIL:  Validation execution failed: {validation_result['error']}")
        if args.json_output:
            print(json.dumps({
                "status": "ERROR",
                "exit_code": 3,
                "error": validation_result["error"]
            }))
        sys.exit(3)
    
    # Evaluate results
    evaluation = evaluate_compliance(
        validation_result["metrics"], 
        args.threshold, 
        args.fail_fast
    )
    
    # Generate CI report
    report_path = generate_ci_report(
        validation_result["metrics"], 
        evaluation, 
        args
    )
    
    # Output results
    if args.json_output:
        # JSON output for parsing by CI systems
        output = {
            "status": evaluation["status"],
            "deployment_safe": evaluation["deployment_safe"],
            "compliance_percentage": evaluation["compliance_percentage"],
            "exit_code": evaluation["exit_code"],
            "message": evaluation["message"],
            "report_path": report_path,
            "critical_issues_count": evaluation["critical_issues"]
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print_compliance_summary(evaluation, validation_result["metrics"], args.verbose)
        print(f"\n[U+1F4CB] Detailed report saved: {report_path}")
    
    # Set appropriate exit code for CI/CD
    if args.verbose:
        print(f"\n[U+1F3C1] Exiting with code: {evaluation['exit_code']}")
    
    sys.exit(evaluation["exit_code"])


if __name__ == "__main__":
    main()