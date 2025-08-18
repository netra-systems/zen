"""Factory Compliance API Routes for SPEC Compliance Scoring.

Provides endpoints for SPEC compliance analysis and scoring.
Module follows 300-line limit with 8-line function limit.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

from app.services.factory_status.factory_status_integration import (
    init_compliance_api,
    ComplianceAPIHandler
)
from app.core.exceptions_base import ValidationError as ValidationException
from app.auth_integration.auth import get_current_user


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


@router.get("/score")
async def get_compliance_scores(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current SPEC compliance scores."""
    handler = await get_compliance_handler()
    scores = await handler.get_compliance_score()
    return {"status": "success", "scores": scores}


@router.post("/analyze")
async def analyze_module_compliance(
    modules: List[str],
    use_claude_cli: bool = Query(False),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger compliance analysis for specific modules."""
    if use_claude_cli and not _is_dev_environment():
        raise HTTPException(403, "Claude CLI only in dev")
    
    handler = await get_compliance_handler()
    try:
        results = await handler.analyze_modules(modules, use_claude_cli)
        return {"status": "success", "analysis": results, "claude_cli": use_claude_cli}
    except ValidationException as e:
        raise HTTPException(400, str(e))


@router.get("/violations")
async def get_compliance_violations(
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    category: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get list of current spec violations."""
    handler = await get_compliance_handler()
    violations = await handler.get_violations(severity, category)
    
    return {
        "status": "success",
        "violations": violations,
        "total_count": len(violations),
        "filters": {"severity": severity, "category": category}
    }


@router.get("/remediation/{module_name}")
async def get_remediation_steps(
    module_name: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get remediation steps for a specific module."""
    handler = await get_compliance_handler()
    module_path = Path(__file__).parent.parent / module_name
    
    if not module_path.exists():
        raise HTTPException(404, f"Module {module_name} not found")
    
    score = await handler.reporter.scorer.score_module(module_path)
    steps = _format_remediation_steps(score)
    
    return {
        "status": "success",
        "module": module_name,
        "current_score": score.overall_score,
        "remediation_steps": steps
    }


@router.get("/trends")
async def get_compliance_trends(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get compliance trend analysis."""
    handler = await get_compliance_handler()
    report = await handler.reporter.generate_compliance_report()
    
    return {
        "status": "success",
        "trends": report.get("trend_analysis", {}),
        "current_score": report.get("overall_compliance_score"),
        "timestamp": report.get("timestamp")
    }


@router.get("/orchestration-alignment")
async def check_orchestration_alignment(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check alignment with master orchestration spec."""
    handler = await get_compliance_handler()
    report = await handler.reporter.generate_compliance_report()
    
    return {
        "status": "success",
        "alignment": report.get("orchestration_alignment", {}),
        "timestamp": report.get("timestamp")
    }


@router.post("/claude-review")
async def trigger_claude_review(
    modules: List[str],
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Trigger Claude CLI review for modules (dev only)."""
    if not _is_dev_environment():
        raise HTTPException(403, "Claude CLI only available in development")
    
    handler = await get_compliance_handler()
    
    try:
        results = await handler.reporter.trigger_claude_review(modules)
        return {"status": "success", "reviews": results}
    except ValidationException as e:
        raise HTTPException(400, str(e))


@router.get("/report")
async def get_full_compliance_report(
    refresh: bool = Query(False),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get full compliance report with all metrics."""
    handler = await get_compliance_handler()
    
    if refresh:
        report = await handler.reporter.generate_compliance_report()
    else:
        report = await handler.reporter.get_cached_report()
        if not report:
            report = await handler.reporter.generate_compliance_report()
    
    return {"status": "success", "report": report}


@router.get("/module/{module_name}/details")
async def get_module_compliance_details(
    module_name: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed compliance info for a module."""
    handler = await get_compliance_handler()
    module_path = Path(__file__).parent.parent / module_name
    
    if not module_path.exists():
        raise HTTPException(404, f"Module {module_name} not found")
    
    score = await handler.reporter.scorer.score_module(module_path)
    
    return {
        "status": "success",
        "module": module_name,
        "scores": {
            "overall": score.overall_score,
            "architecture": score.architecture_score,
            "type_safety": score.type_safety_score,
            "spec_alignment": score.spec_alignment_score,
            "test_coverage": score.test_coverage_score,
            "documentation": score.documentation_score
        },
        "violations": score.violations,
        "timestamp": score.timestamp.isoformat()
    }


@router.get("/dashboard")
async def get_compliance_dashboard(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get compliance dashboard data."""
    handler = await get_compliance_handler()
    report = await handler.reporter.get_cached_report()
    
    if not report:
        report = await handler.reporter.generate_compliance_report()
    
    return {
        "status": "success",
        "dashboard": {
            "overall_score": report["overall_compliance_score"],
            "top_modules": report["top_compliant_modules"],
            "bottom_modules": report["modules_needing_attention"],
            "critical_count": len(report["critical_violations"]),
            "violations_summary": report["violations_summary"],
            "orchestration_aligned": report["orchestration_alignment"]["aligned"],
            "last_updated": report["timestamp"]
        }
    }


def _is_dev_environment() -> bool:
    """Check if running in development environment."""
    env = os.getenv("ENVIRONMENT", "staging")  # Default to staging for safety
    return env in ["development", "dev", "local"]


def _create_violation_step(v: Dict) -> Dict:
    """Create single violation step."""
    return {
        "violation": v.get("description"),
        "severity": v.get("severity"),
        "remediation": v.get("remediation"),
        "file": v.get("file_path"),
        "line": v.get("line_number")
    }


def _format_remediation_steps(score) -> List[Dict]:
    """Format remediation steps from score violations."""
    return [_create_violation_step(v) for v in score.violations[:10]]