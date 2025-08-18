"""Factory compliance handlers."""
from fastapi import HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.services.factory_status.factory_status_integration import ComplianceAPIHandler
from app.core.exceptions_base import ValidationError as ValidationException
from app.auth_integration.auth import get_current_user


async def handle_compliance_scores(handler: ComplianceAPIHandler) -> Dict[str, Any]:
    """Handle compliance scores request."""
    scores = await handler.get_compliance_score()
    return {"status": "success", "scores": scores}


async def _perform_analysis(handler: ComplianceAPIHandler, modules: List[str], use_claude_cli: bool):
    """Perform compliance analysis."""
    return await handler.analyze_modules(modules, use_claude_cli)

async def handle_module_compliance_analysis(
    handler: ComplianceAPIHandler, modules: List[str], use_claude_cli: bool
) -> Dict[str, Any]:
    """Handle module compliance analysis."""
    try:
        results = await _perform_analysis(handler, modules, use_claude_cli)
        return build_analyze_response(results, use_claude_cli)
    except ValidationException as e:
        raise HTTPException(400, str(e))


async def handle_compliance_violations(
    handler: ComplianceAPIHandler, severity: Optional[str], category: Optional[str]
) -> Dict[str, Any]:
    """Handle compliance violations request."""
    violations = await handler.get_violations(severity, category)
    return build_violations_response(violations, severity, category)


async def _score_module_for_remediation(handler: ComplianceAPIHandler, module_path: Path):
    """Score module for remediation."""
    return await handler.reporter.scorer.score_module(module_path)

async def handle_remediation_steps(
    handler: ComplianceAPIHandler, module_name: str
) -> Dict[str, Any]:
    """Handle remediation steps request."""
    module_path = Path(__file__).parent.parent / module_name
    validate_module_path(module_name, module_path)
    score = await _score_module_for_remediation(handler, module_path)
    steps = format_remediation_steps(score)
    return build_remediation_response(module_name, score, steps)


async def handle_compliance_trends(handler: ComplianceAPIHandler) -> Dict[str, Any]:
    """Handle compliance trends request."""
    report = await handler.reporter.generate_compliance_report()
    return build_trends_response(report)


async def handle_orchestration_alignment(handler: ComplianceAPIHandler) -> Dict[str, Any]:
    """Handle orchestration alignment request."""
    report = await handler.reporter.generate_compliance_report()
    return build_alignment_response(report)


async def _trigger_review(handler: ComplianceAPIHandler, modules: List[str]):
    """Trigger Claude review."""
    return await handler.reporter.trigger_claude_review(modules)

async def handle_claude_review(
    handler: ComplianceAPIHandler, modules: List[str]
) -> Dict[str, Any]:
    """Handle Claude review request."""
    try:
        results = await _trigger_review(handler, modules)
        return build_review_response(results)
    except ValidationException as e:
        raise HTTPException(400, str(e))


# Response builders
def build_analyze_response(results, use_claude_cli: bool) -> Dict[str, Any]:
    """Build analysis response."""
    return {"status": "success", "analysis": results, "claude_cli": use_claude_cli}


def build_violations_response(violations, severity, category) -> Dict[str, Any]:
    """Build violations response."""
    return {
        "status": "success",
        "violations": violations,
        "total_count": len(violations),
        "filters": {"severity": severity, "category": category}
    }


def build_remediation_response(module_name: str, score, steps) -> Dict[str, Any]:
    """Build remediation response."""
    return {
        "status": "success",
        "module": module_name,
        "current_score": score.overall_score,
        "remediation_steps": steps
    }


def build_trends_response(report) -> Dict[str, Any]:
    """Build trends response."""
    return {
        "status": "success",
        "trends": report.get("trend_analysis", {}),
        "current_score": report.get("overall_compliance_score"),
        "timestamp": report.get("timestamp")
    }


def build_alignment_response(report) -> Dict[str, Any]:
    """Build alignment response."""
    return {
        "status": "success",
        "alignment": report.get("orchestration_alignment", {}),
        "timestamp": report.get("timestamp")
    }


def build_review_response(results) -> Dict[str, Any]:
    """Build Claude review response."""
    return {"status": "success", "reviews": results}


# Validators
def validate_module_path(module_name: str, module_path: Path) -> None:
    """Validate module path exists."""
    if not module_path.exists():
        raise HTTPException(404, f"Module {module_name} not found")


# Formatters
def extract_violation_fields(v: Dict) -> tuple:
    """Extract violation fields."""
    return (v.get("description"), v.get("severity"), v.get("remediation"))


def create_violation_step(v: Dict) -> Dict:
    """Create single violation step."""
    description, severity, remediation = extract_violation_fields(v)
    return {
        "violation": description, "severity": severity,
        "remediation": remediation, "file": v.get("file_path"), "line": v.get("line_number")
    }


def format_remediation_steps(score) -> List[Dict]:
    """Format remediation steps from score violations."""
    return [create_violation_step(v) for v in score.violations[:10]]