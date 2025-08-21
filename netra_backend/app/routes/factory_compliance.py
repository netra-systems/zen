"""Factory Compliance API Routes for SPEC Compliance Scoring.

Provides endpoints for SPEC compliance analysis and scoring.
Module follows 450-line limit with 25-line function limit.
"""

from fastapi import APIRouter, Query, Depends
from typing import Dict, Any, List, Optional

from app.services.factory_status.factory_status_integration import (
    init_compliance_api,
    ComplianceAPIHandler
)
from app.auth_integration.auth import get_current_user
from app.routes.factory_compliance_handlers import (
    handle_compliance_scores, handle_module_compliance_analysis,
    handle_compliance_violations, handle_remediation_steps,
    handle_compliance_trends, handle_orchestration_alignment,
    handle_claude_review
)
from app.routes.factory_compliance_validators import (
    validate_claude_cli_access, validate_dev_environment
)
from app.routes.factory_compliance_reports import (
    handle_full_compliance_report, handle_module_compliance_details,
    handle_compliance_dashboard
)

router = APIRouter(
    prefix="/api/factory-status/compliance",
    tags=["factory-compliance"]
)

# Compliance handler singleton
_compliance_handler: Optional[ComplianceAPIHandler] = None


async def get_compliance_handler() -> ComplianceAPIHandler:
    """Get or initialize compliance handler."""
    global _compliance_handler
    if not _compliance_handler:
        _compliance_handler = await init_compliance_api()
    return _compliance_handler


async def _handle_module_analysis(modules: List[str], use_claude_cli: bool) -> Dict[str, Any]:
    """Handle module analysis with compliance handler."""
    handler = await get_compliance_handler()
    return await handle_module_compliance_analysis(handler, modules, use_claude_cli)


@router.get("/score")
async def get_compliance_scores(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current SPEC compliance scores."""
    handler = await get_compliance_handler()
    return await handle_compliance_scores(handler)


@router.post("/analyze")
async def analyze_module_compliance(
    modules: List[str], use_claude_cli: bool = Query(False),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger compliance analysis for specific modules."""
    validate_claude_cli_access(use_claude_cli)
    return await _handle_module_analysis(modules, use_claude_cli)


@router.get("/violations")
async def get_compliance_violations(
    severity: Optional[str] = Query(None, pattern="^(critical|high|medium|low)$"),
    category: Optional[str] = Query(None), current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get list of current spec violations."""
    handler = await get_compliance_handler()
    return await handle_compliance_violations(handler, severity, category)


@router.get("/remediation/{module_name}")
async def get_remediation_steps(
    module_name: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get remediation steps for a specific module."""
    handler = await get_compliance_handler()
    return await handle_remediation_steps(handler, module_name)


@router.get("/trends")
async def get_compliance_trends(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get compliance trend analysis."""
    handler = await get_compliance_handler()
    return await handle_compliance_trends(handler)


@router.get("/orchestration-alignment")
async def check_orchestration_alignment(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check alignment with master orchestration spec."""
    handler = await get_compliance_handler()
    return await handle_orchestration_alignment(handler)


@router.post("/claude-review")
async def trigger_claude_review(
    modules: List[str],
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger Claude CLI review for modules (dev only)."""
    validate_dev_environment()
    handler = await get_compliance_handler()
    return await handle_claude_review(handler, modules)


@router.get("/report")
async def get_full_compliance_report(
    refresh: bool = Query(False),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get full compliance report with all metrics."""
    handler = await get_compliance_handler()
    return await handle_full_compliance_report(handler, refresh)


@router.get("/module/{module_name}/details")
async def get_module_compliance_details(
    module_name: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed compliance info for a module."""
    handler = await get_compliance_handler()
    return await handle_module_compliance_details(handler, module_name)


@router.get("/dashboard")
async def get_compliance_dashboard(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get compliance dashboard data."""
    handler = await get_compliance_handler()
    return await handle_compliance_dashboard(handler)