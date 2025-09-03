"""Test endpoints for GCP error reporting.

CRITICAL: These endpoints are for testing GCP error reporting integration.
They deliberately raise exceptions to verify error reporting works in GCP Cloud Run.
"""

from fastapi import APIRouter, HTTPException
from netra_backend.app.core.exceptions_base import NetraException, ValidationError, ServiceUnavailableException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.services.monitoring.gcp_error_reporter import gcp_reportable, report_exception, report_error
from netra_backend.app.core.unified_logging import get_logger
from shared.isolated_environment import get_env

logger = get_logger(__name__)
router = APIRouter(prefix="/test/gcp-errors", tags=["Testing"])

# Only enable in non-production environments
env = get_env()
ENVIRONMENT = env.get("ENVIRONMENT", "development").lower()
TESTING_ENABLED = ENVIRONMENT in ["development", "staging", "testing"]


@router.get("/deliberate-unhandled")
async def deliberate_unhandled_error():
    """Deliberately raise an unhandled exception to test GCP error reporting."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: About to raise deliberate unhandled exception")
    
    # This should appear in GCP Error Reporting
    raise RuntimeError("TEST: Deliberate unhandled exception for GCP error reporting test")


@router.get("/deliberate-netra-exception")
async def deliberate_netra_exception():
    """Raise a NetraException with HIGH severity (auto-reports to GCP)."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: About to raise NetraException with HIGH severity")
    
    # High severity exceptions auto-report to GCP
    raise ServiceUnavailableException(
        message="TEST: Deliberate service unavailable exception",
        details={"test": True, "purpose": "GCP error reporting validation"},
        user_message="This is a test error - please ignore"
    )


@router.get("/deliberate-handled-reported")
async def deliberate_handled_but_reported():
    """Handle an exception but still report it to GCP."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: Handling exception but reporting to GCP")
    
    try:
        # Simulate some operation that fails
        result = 1 / 0
    except ZeroDivisionError as e:
        # Report to GCP even though we're handling it
        report_exception(e, extra_context={
            "test": True,
            "endpoint": "deliberate-handled-reported",
            "message": "This error was handled but still reported"
        })
        
        return {
            "status": "error_handled",
            "message": "Division by zero was caught and reported to GCP",
            "reported": True
        }


@router.get("/deliberate-decorated")
@gcp_reportable(reraise=True)
async def deliberate_decorated_function():
    """Test the @gcp_reportable decorator."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: About to raise exception in decorated function")
    
    # This will be reported via the decorator
    raise ValueError("TEST: Exception from decorated function")


@router.get("/deliberate-decorated-no-reraise")
@gcp_reportable(reraise=False)
async def deliberate_decorated_no_reraise():
    """Test the @gcp_reportable decorator without re-raising."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: Raising exception that won't be re-raised")
    
    # This will be reported but not re-raised
    raise ValueError("TEST: Silently reported exception")
    
    # This line won't execute, but the endpoint will return None
    # instead of raising the exception


@router.get("/deliberate-message")
async def deliberate_error_message():
    """Report an error message (not exception) to GCP."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: Reporting error message to GCP")
    
    # Report a message without an actual exception
    report_error(
        "TEST: Critical system issue detected (simulated)",
        severity=ErrorSeverity.CRITICAL,
        extra_context={
            "test": True,
            "simulation": True,
            "metric": 42,
            "threshold": 100
        }
    )
    
    return {
        "status": "message_reported",
        "message": "Error message reported to GCP without exception"
    }


@router.get("/test-cascade")
async def test_error_cascade():
    """Test a cascade of errors to see how they appear in GCP."""
    if not TESTING_ENABLED:
        raise HTTPException(status_code=403, detail="Test endpoints disabled in production")
    
    logger.warning("TEST: Starting error cascade test")
    
    # Report multiple related errors
    try:
        # First error
        raise ConnectionError("Database connection failed")
    except ConnectionError as e:
        report_exception(e, extra_context={"cascade_step": 1})
        
        try:
            # Second error as consequence
            raise ServiceUnavailableException(
                "Service unavailable due to database connection",
                details={"original_error": str(e)}
            )
        except ServiceUnavailableException as e2:
            # This will auto-report due to HIGH severity
            
            # Final error
            raise NetraException(
                "System failure cascade",
                code=ErrorCode.INTERNAL_ERROR,
                severity=ErrorSeverity.CRITICAL,
                details={
                    "cascade_complete": True,
                    "errors_in_cascade": 3
                }
            )


@router.get("/verify-setup")
async def verify_gcp_error_setup():
    """Verify GCP error reporting is configured correctly."""
    from netra_backend.app.services.monitoring.gcp_error_reporter import get_error_reporter
    
    reporter = get_error_reporter()
    
    return {
        "gcp_error_reporting_enabled": reporter.enabled,
        "gcp_client_initialized": reporter.client is not None,
        "environment": ENVIRONMENT,
        "testing_endpoints_enabled": TESTING_ENABLED,
        "gcp_available": reporter.client is not None,
        "instructions": {
            "test_unhandled": f"GET /test/gcp-errors/deliberate-unhandled",
            "test_netra_exception": f"GET /test/gcp-errors/deliberate-netra-exception",
            "test_handled": f"GET /test/gcp-errors/deliberate-handled-reported",
            "test_decorator": f"GET /test/gcp-errors/deliberate-decorated",
            "test_message": f"GET /test/gcp-errors/deliberate-message",
            "test_cascade": f"GET /test/gcp-errors/test-cascade"
        }
    }