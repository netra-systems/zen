from shared.isolated_environment import get_env
"""
CORS Validation Utilities for Integration Tests

Business Value Justification (BVJ):
- Segment: ALL (Framework for testing CORS across all services)
- Business Goal: Ensure CORS compliance in all integration tests
- Value Impact: Prevents CORS-related production issues
- Strategic Impact: Systematic testing prevents service integration failures

This module provides utilities to validate CORS headers in integration tests.
"""

from typing import Dict, List, Optional, Any
import os


def validate_cors_headers(
    response_headers: Dict[str, str],
    request_origin: str,
    environment: str = "development"
) -> Dict[str, Any]:
    """
    Validate CORS headers in a response.

    Args:
        response_headers: HTTP response headers
        request_origin: Origin header from the request
        environment: Environment configuration to use

    Returns:
        Dict containing validation results and details
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "headers_found": {},
        "expected_headers": {}
    }

    # Extract CORS headers
    cors_headers = {
        "access-control-allow-origin": response_headers.get("Access-Control-Allow-Origin", ""),
        "access-control-allow-methods": response_headers.get("Access-Control-Allow-Methods", ""),
        "access-control-allow-headers": response_headers.get("Access-Control-Allow-Headers", ""),
        "access-control-allow-credentials": response_headers.get("Access-Control-Allow-Credentials", ""),
        "access-control-max-age": response_headers.get("Access-Control-Max-Age", "")
    }

    validation_results["headers_found"] = cors_headers

    # Validate Access-Control-Allow-Origin
    expected_origin = request_origin
    actual_origin = cors_headers["access-control-allow-origin"]

    if actual_origin != expected_origin and actual_origin != "*":
        validation_results["valid"] = False
        validation_results["errors"].append({
            "type": "origin_mismatch",
            "expected": expected_origin,
            "actual": actual_origin,
            "message": f"Expected origin '{expected_origin}' but got '{actual_origin}'"
        })

    # Validate required methods
    required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_methods = cors_headers["access-control-allow-methods"].upper().split(", ")

    missing_methods = [method for method in required_methods if method not in allowed_methods]
    if missing_methods:
        validation_results["warnings"].append({
            "type": "missing_methods",
            "missing": missing_methods,
            "message": f"Missing required methods: {', '.join(missing_methods)}"
        })

    # Validate common headers
    required_headers = ["Content-Type", "Authorization", "X-Requested-With"]
    allowed_headers_str = cors_headers["access-control-allow-headers"].lower()

    missing_headers = []
    for header in required_headers:
        if header.lower() not in allowed_headers_str:
            missing_headers.append(header)

    if missing_headers:
        validation_results["warnings"].append({
            "type": "missing_headers",
            "missing": missing_headers,
            "message": f"Missing common headers: {', '.join(missing_headers)}"
        })

    # Environment-specific validation
    if environment == "production":
        if actual_origin == "*":
            validation_results["errors"].append({
                "type": "wildcard_origin_production",
                "message": "Wildcard origin (*) should not be used in production"
            })
            validation_results["valid"] = False

    return validation_results


def get_test_origins(environment: str = "development") -> List[str]:
    """
    Get test origins for the specified environment.

    Args:
        environment: Environment to get origins for

    Returns:
        List of test origins for the environment
    """
    origins = {
        "development": [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            "http://[::1]:3000"  # IPv6
        ],
        "staging": [
            "https://app.staging.netrasystems.ai",
            "https://auth.staging.netrasystems.ai",
            "http://localhost:3000"  # Local testing
        ],
        "production": [
            "https://netrasystems.ai",
            "https://app.netrasystems.ai",
            "https://auth.netrasystems.ai"
        ]
    }

    return origins.get(environment, origins["development"])


def create_cors_request_headers(origin: str, method: str = "GET") -> Dict[str, str]:
    """
    Create request headers for testing CORS.

    Args:
        origin: Origin header value
        method: HTTP method for preflight requests

    Returns:
        Dict of request headers for CORS testing
    """
    headers = {
        "Origin": origin,
        "User-Agent": "Mozilla/5.0 (CORS Test Client)"
    }

    # Add preflight headers for non-simple requests
    if method.upper() not in ["GET", "HEAD", "POST"]:
        headers["Access-Control-Request-Method"] = method.upper()
        headers["Access-Control-Request-Headers"] = "Content-Type, Authorization, X-Requested-With"

    return headers


def validate_preflight_response(
    response_headers: Dict[str, str],
    request_method: str,
    request_headers: List[str],
    origin: str
) -> Dict[str, Any]:
    """
    Validate a CORS preflight response.

    Args:
        response_headers: Response headers from OPTIONS request
        request_method: Method that will be used in actual request
        request_headers: Headers that will be sent in actual request
        origin: Origin making the request

    Returns:
        Dict containing validation results
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "preflight_approved": False
    }

    # Check if method is allowed
    allowed_methods = response_headers.get("Access-Control-Allow-Methods", "").upper().split(", ")
    if request_method.upper() not in allowed_methods:
        validation_results["valid"] = False
        validation_results["errors"].append({
            "type": "method_not_allowed",
            "method": request_method,
            "allowed": allowed_methods,
            "message": f"Method {request_method} not allowed. Allowed: {', '.join(allowed_methods)}"
        })

    # Check if headers are allowed
    allowed_headers_str = response_headers.get("Access-Control-Allow-Headers", "").lower()
    allowed_headers = [h.strip() for h in allowed_headers_str.split(",")]

    for header in request_headers:
        if header.lower() not in allowed_headers:
            validation_results["valid"] = False
            validation_results["errors"].append({
                "type": "header_not_allowed",
                "header": header,
                "allowed": allowed_headers,
                "message": f"Header {header} not allowed"
            })

    # Check origin
    allowed_origin = response_headers.get("Access-Control-Allow-Origin", "")
    if allowed_origin != origin and allowed_origin != "*":
        validation_results["valid"] = False
        validation_results["errors"].append({
            "type": "origin_not_allowed",
            "origin": origin,
            "allowed": allowed_origin,
            "message": f"Origin {origin} not allowed"
        })

    if validation_results["valid"]:
        validation_results["preflight_approved"] = True

    return validation_results


def get_cors_test_scenarios(environment: str = "development") -> List[Dict[str, Any]]:
    """
    Get common CORS test scenarios for the environment.

    Args:
        environment: Environment to get scenarios for

    Returns:
        List of test scenario configurations
    """
    test_origins = get_test_origins(environment)

    scenarios = []

    # Basic GET requests
    for origin in test_origins:
        scenarios.append({
            "name": f"GET request from {origin}",
            "origin": origin,
            "method": "GET",
            "headers": [],
            "expect_preflight": False
        })

    # POST with JSON
    for origin in test_origins[:2]:  # Limit to first 2 origins
        scenarios.append({
            "name": f"POST JSON from {origin}",
            "origin": origin,
            "method": "POST",
            "headers": ["Content-Type"],
            "content_type": "application/json",
            "expect_preflight": True
        })

    # Authenticated requests
    for origin in test_origins[:1]:  # Limit to first origin
        scenarios.append({
            "name": f"Authenticated request from {origin}",
            "origin": origin,
            "method": "GET",
            "headers": ["Authorization"],
            "expect_preflight": True
        })

    return scenarios


def format_cors_validation_report(validation_results: Dict[str, Any]) -> str:
    """
    Format validation results into a readable report.

    Args:
        validation_results: Results from validate_cors_headers

    Returns:
        Formatted string report
    """
    report_lines = []

    if validation_results["valid"]:
        report_lines.append("CHECK CORS Validation: PASSED")
    else:
        report_lines.append("X CORS Validation: FAILED")

    report_lines.append("")

    # Headers found
    headers = validation_results.get("headers_found", {})
    report_lines.append("Headers Found:")
    for header, value in headers.items():
        if value:
            report_lines.append(f"  {header}: {value}")
        else:
            report_lines.append(f"  {header}: (not set)")

    report_lines.append("")

    # Errors
    errors = validation_results.get("errors", [])
    if errors:
        report_lines.append("Errors:")
        for error in errors:
            report_lines.append(f"  X {error.get('message', str(error))}")
        report_lines.append("")

    # Warnings
    warnings = validation_results.get("warnings", [])
    if warnings:
        report_lines.append("Warnings:")
        for warning in warnings:
            report_lines.append(f"  WARNING️ {warning.get('message', str(warning))}")

    return "\n".join(report_lines)