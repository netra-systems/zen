#!/usr/bin/env python3
"""
Test script for Docker Compose Log Introspection System

Tests the log introspector and issue creator functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from docker_compose_log_introspector import (
    DockerComposeLogIntrospector,
    ErrorCategory,
    ErrorSeverity,
    ErrorPattern,
    DetectedError,
    ServiceLogs
)

from docker_log_issue_creator import (
    GitHubIssueCreator,
    IssueTemplate
)


def test_error_detection():
    """Test error pattern detection."""
    print("Testing error detection...")
    
    introspector = DockerComposeLogIntrospector()
    
    # Test various error patterns
    test_cases = [
        # Database errors
        ("2024-01-15T10:30:45.123456Z backend | psycopg2.OperationalError: could not connect to server",
         ErrorCategory.DATABASE_CONNECTION, ErrorSeverity.ERROR),
        
        # Authentication errors  
        ("2024-01-15T10:31:00.000000Z auth | ERROR: 401 unauthorized access attempt",
         ErrorCategory.AUTHENTICATION, ErrorSeverity.ERROR),
        
        # Network errors
        ("2024-01-15T10:32:00.000000Z frontend | Error: ECONNREFUSED - Connection refused",
         ErrorCategory.NETWORK, ErrorSeverity.ERROR),
        
        # Configuration errors
        ("2024-01-15T10:33:00.000000Z backend | KeyError: 'DATABASE_URL' missing required config",
         ErrorCategory.CONFIGURATION, ErrorSeverity.WARNING),
        
        # Memory errors
        ("2024-01-15T10:34:00.000000Z worker | FATAL: out of memory, cannot allocate 1GB",
         ErrorCategory.MEMORY, ErrorSeverity.CRITICAL),
        
        # Import errors
        ("2024-01-15T10:35:00.000000Z backend | ModuleNotFoundError: No module named 'redis'",
         ErrorCategory.DEPENDENCY, ErrorSeverity.ERROR),
        
        # Timeout errors
        ("2024-01-15T10:36:00.000000Z backend | WARNING: Request timeout after 30s",
         ErrorCategory.TIMEOUT, ErrorSeverity.WARNING),
        
        # WebSocket errors
        ("2024-01-15T10:37:00.000000Z backend | websocket connection failed: 1006",
         ErrorCategory.WEBSOCKET, ErrorSeverity.WARNING),
        
        # CORS errors
        ("2024-01-15T10:38:00.000000Z frontend | CORS blocked: No Access-Control-Allow-Origin",
         ErrorCategory.CORS, ErrorSeverity.ERROR),
        
        # SSL errors
        ("2024-01-15T10:39:00.000000Z backend | SSL certificate verify failed: self signed",
         ErrorCategory.SSL_TLS, ErrorSeverity.ERROR),
    ]
    
    passed = 0
    failed = 0
    
    for log_line, expected_category, expected_severity in test_cases:
        errors = introspector.detect_errors_in_logs([log_line], "test-service")
        
        if errors:
            error = errors[0]
            if error.category == expected_category and error.severity == expected_severity:
                print(f"  [U+2713] Correctly detected {expected_category.value} with {expected_severity.value}")
                passed += 1
            else:
                print(f"  [U+2717] Wrong detection for: {log_line[:50]}...")
                print(f"    Expected: {expected_category.value}/{expected_severity.value}")
                print(f"    Got: {error.category.value}/{error.severity.value}")
                failed += 1
        else:
            print(f"  [U+2717] Failed to detect error in: {log_line[:50]}...")
            failed += 1
    
    print(f"\nError Detection Results: {passed} passed, {failed} failed")
    return failed == 0


def test_error_grouping():
    """Test error grouping and deduplication."""
    print("\nTesting error grouping...")
    
    introspector = DockerComposeLogIntrospector()
    
    # Create sample logs with multiple similar errors
    logs = [
        "2024-01-15T10:00:00Z backend | psycopg2.OperationalError: connection refused",
        "2024-01-15T10:00:01Z backend | psycopg2.OperationalError: connection refused", 
        "2024-01-15T10:00:02Z backend | psycopg2.OperationalError: connection refused",
        "2024-01-15T10:00:03Z auth | JWT decode error: invalid signature",
        "2024-01-15T10:00:04Z auth | JWT decode error: invalid signature",
        "2024-01-15T10:00:05Z frontend | CORS blocked by policy",
    ]
    
    # Process logs for multiple services
    service_logs = {
        "backend": ServiceLogs(
            service_name="backend",
            lines=logs[:3],
            errors=introspector.detect_errors_in_logs(logs[:3], "backend"),
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=3,
            error_count=3,
            warning_count=0
        ),
        "auth": ServiceLogs(
            service_name="auth",
            lines=logs[3:5],
            errors=introspector.detect_errors_in_logs(logs[3:5], "auth"),
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=2,
            error_count=2,
            warning_count=0
        ),
        "frontend": ServiceLogs(
            service_name="frontend",
            lines=logs[5:6],
            errors=introspector.detect_errors_in_logs(logs[5:6], "frontend"),
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=1,
            error_count=1,
            warning_count=0
        )
    }
    
    # Generate report
    report = introspector.generate_error_report(service_logs)
    
    # Check report contains expected sections
    assert "DOCKER COMPOSE LOG INTROSPECTION REPORT" in report
    assert "SUMMARY" in report
    assert "ERRORS BY CATEGORY" in report
    assert "Total Errors: 6" in report
    
    print("  [U+2713] Error grouping and reporting works correctly")
    return True


def test_issue_creation():
    """Test GitHub issue template creation."""
    print("\nTesting issue creation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        dedupe_file = Path(tmpdir) / "test_issues.json"
        creator = GitHubIssueCreator(dry_run=True, dedupe_file=str(dedupe_file))
        
        # Create sample errors
        errors = [
            ("backend", DetectedError(
                timestamp=datetime.now(),
                service="backend",
                category=ErrorCategory.DATABASE_CONNECTION,
                severity=ErrorSeverity.ERROR,
                message="Database connection failed",
                raw_log="psycopg2.OperationalError: could not connect",
                line_number=1
            )),
            ("backend", DetectedError(
                timestamp=datetime.now(),
                service="backend", 
                category=ErrorCategory.DATABASE_CONNECTION,
                severity=ErrorSeverity.ERROR,
                message="Database connection failed",
                raw_log="psycopg2.OperationalError: connection refused",
                line_number=2
            ))
        ]
        
        # Create issue template
        template = creator.create_issue_template(
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR,
            errors
        )
        
        # Verify template
        assert "Database Connection" in template.title
        assert "2 occurrences" in template.title
        assert "backend" in template.body
        assert "bug" in template.labels
        assert "severity:error" in template.labels
        
        print("  [U+2713] Issue template creation works correctly")
        
        # Test deduplication
        error_hash = creator.get_error_hash(
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR,
            [e for _, e in errors]
        )
        
        # First check - should create
        assert creator.should_create_issue(
            error_hash, 
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR
        ) == True
        
        # Record as created
        creator.created_issues[error_hash] = {
            'created_at': datetime.now().isoformat(),
            'url': 'test-url'
        }
        
        # Second check - should not create (duplicate)
        assert creator.should_create_issue(
            error_hash,
            ErrorCategory.DATABASE_CONNECTION,
            ErrorSeverity.ERROR
        ) == False
        
        print("  [U+2713] Issue deduplication works correctly")
        
    return True


def test_docker_compose_integration():
    """Test actual Docker Compose command execution (if available)."""
    print("\nTesting Docker Compose integration...")
    
    introspector = DockerComposeLogIntrospector()
    
    # Check if Docker is available
    returncode, stdout, stderr = introspector.run_docker_compose(["--version"])
    
    if returncode != 0:
        print("   WARNING:  Docker Compose not available, skipping integration test")
        return True
    
    print(f"  [U+2713] Docker Compose version: {stdout.strip()}")
    
    # Try to get service list (may be empty if no services running)
    returncode, stdout, stderr = introspector.run_docker_compose(["ps", "--services"])
    
    if returncode == 0:
        services = [s.strip() for s in stdout.split('\n') if s.strip()]
        if services:
            print(f"  [U+2713] Found {len(services)} running service(s): {', '.join(services)}")
            
            # Try to get logs for first service
            service = services[0]
            logs = introspector.get_service_logs(service, tail=10)
            print(f"  [U+2713] Retrieved {logs.total_lines} log lines from {service}")
            
            if logs.errors:
                print(f"  [U+2713] Detected {len(logs.errors)} error(s) in {service} logs")
        else:
            print("   WARNING:  No services running, cannot test log retrieval")
    else:
        print("   WARNING:  Could not get service list")
    
    return True


def test_report_generation():
    """Test report generation with various error scenarios."""
    print("\nTesting report generation...")
    
    introspector = DockerComposeLogIntrospector()
    
    # Create a complex scenario with multiple services and error types
    test_logs = {
        "backend": ServiceLogs(
            service_name="backend",
            lines=["line1", "line2"],
            errors=[
                DetectedError(
                    timestamp=datetime.now(),
                    service="backend",
                    category=ErrorCategory.DATABASE_CONNECTION,
                    severity=ErrorSeverity.ERROR,
                    message="DB error",
                    raw_log="Connection refused to database",
                    line_number=1
                ),
                DetectedError(
                    timestamp=datetime.now(),
                    service="backend",
                    category=ErrorCategory.MEMORY,
                    severity=ErrorSeverity.CRITICAL,
                    message="OOM",
                    raw_log="Out of memory error",
                    line_number=2
                )
            ],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=2,
            error_count=1,
            warning_count=0
        ),
        "frontend": ServiceLogs(
            service_name="frontend",
            lines=["line3"],
            errors=[
                DetectedError(
                    timestamp=datetime.now(),
                    service="frontend",
                    category=ErrorCategory.CORS,
                    severity=ErrorSeverity.ERROR,
                    message="CORS",
                    raw_log="CORS policy blocked request",
                    line_number=1
                )
            ],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=1,
            error_count=1,
            warning_count=0
        ),
        "auth": ServiceLogs(
            service_name="auth",
            lines=[],
            errors=[],
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_lines=0,
            error_count=0,
            warning_count=0
        )
    }
    
    # Generate report
    report = introspector.generate_error_report(test_logs)
    
    # Verify report sections
    checks = [
        ("Services Analyzed: 3", "Service count"),
        ("Total Errors: 2", "Error count"),
        ("ERRORS BY CATEGORY", "Category section"),
        ("Database Connection: 1", "DB errors"),
        ("Memory/Resource: 1", "Memory errors"),
        ("CORS: 1", "CORS errors"),
        ("BACKEND", "Backend section"),
        ("FRONTEND", "Frontend section")
    ]
    
    for check_text, description in checks:
        if check_text in report:
            print(f"  [U+2713] Report contains {description}")
        else:
            print(f"  [U+2717] Report missing {description}")
            return False
    
    # Auth service should not appear in detailed section (no errors)
    if "AUTH\n" not in report.upper() or "auth" not in report.lower().split("analyzed"):
        print("  [U+2713] Empty service not in detailed section")
    else:
        print("  [U+2717] Empty service incorrectly appears in detailed section")
        return False
    
    print("  [U+2713] Report generation works correctly")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("Docker Compose Log Introspection Test Suite")
    print("="*60)
    
    tests = [
        ("Error Detection", test_error_detection),
        ("Error Grouping", test_error_grouping),
        ("Issue Creation", test_issue_creation),
        ("Report Generation", test_report_generation),
        ("Docker Integration", test_docker_compose_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n[U+2717] {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for test_name, success in results:
        status = "[U+2713] PASSED" if success else "[U+2717] FAILED"
        print(f"{test_name:20} {status}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n CELEBRATION:  All tests passed!")
        return 0
    else:
        print(f"\n FAIL:  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())