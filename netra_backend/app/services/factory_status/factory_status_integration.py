"""AI Factory Status Integration with SPEC Compliance Scoring."""

from pathlib import Path

from netra_backend.app.services.factory_status.compliance_api_handler import (
    ComplianceAPIHandler,
)
from netra_backend.app.services.factory_status.factory_status_reporter import (
    FactoryStatusReporter,
)


# Factory function for creating reporter instance
def create_factory_status_reporter() -> FactoryStatusReporter:
    """Create factory status reporter instance."""
    project_root = Path(__file__).parent.parent.parent.parent
    return FactoryStatusReporter(project_root)


# Async initialization for API endpoints
async def init_compliance_api() -> ComplianceAPIHandler:
    """Initialize compliance API handler."""
    reporter = create_factory_status_reporter()
    return ComplianceAPIHandler(reporter)