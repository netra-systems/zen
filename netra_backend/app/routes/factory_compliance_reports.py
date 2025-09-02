"""Factory compliance reporting utilities."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from netra_backend.app.services.factory_status.factory_status_integration import (
    ComplianceAPIHandler,
)


async def handle_full_compliance_report(
    handler: ComplianceAPIHandler, refresh: bool
) -> Dict[str, Any]:
    """Handle full compliance report request."""
    report = await get_compliance_report(handler, refresh)
    return {"status": "success", "report": report}


async def _validate_and_score_module(handler: ComplianceAPIHandler, module_name: str, module_path: Path):
    """Validate and score module."""
    from netra_backend.app.routes.factory_compliance_validators import (
        validate_module_path,
    )
    validate_module_path(module_name, module_path)
    return await handler.reporter.scorer.score_module(module_path)

async def handle_module_compliance_details(
    handler: ComplianceAPIHandler, module_name: str
) -> Dict[str, Any]:
    """Handle module compliance details request."""
    module_path = Path(__file__).parent.parent / module_name
    score = await _validate_and_score_module(handler, module_name, module_path)
    return build_module_details_response(module_name, score)


async def handle_compliance_dashboard(handler: ComplianceAPIHandler) -> Dict[str, Any]:
    """Handle compliance dashboard request."""
    report = await get_dashboard_report(handler)
    return {"status": "success", "dashboard": build_dashboard_data(report)}


async def get_compliance_report(handler: ComplianceAPIHandler, refresh: bool):
    """Get compliance report based on refresh flag."""
    if refresh:
        return await handler.reporter.generate_compliance_report()
    report = await handler.reporter.get_cached_report()
    if not report:
        report = await handler.reporter.generate_compliance_report()
    return report


async def get_dashboard_report(handler: ComplianceAPIHandler):
    """Get dashboard report with fallback."""
    report = await handler.reporter.get_cached_report()
    if not report:
        report = await handler.reporter.generate_compliance_report()
    return report


def _extract_score_values(score) -> Dict[str, Any]:
    """Extract score values."""
    return {
        "overall": score.overall_score, "architecture": score.architecture_score,
        "type_safety": score.type_safety_score, "spec_alignment": score.spec_alignment_score,
        "test_coverage": score.test_coverage_score, "documentation": score.documentation_score
    }

def build_score_details(score) -> Dict[str, Any]:
    """Build detailed score breakdown."""
    return _extract_score_values(score)


def _build_response_data(module_name: str, score) -> Dict[str, Any]:
    """Build response data."""
    return {
        "status": "success", "module": module_name,
        "scores": build_score_details(score), "violations": score.violations,
        "timestamp": score.timestamp.isoformat()
    }

def build_module_details_response(module_name: str, score) -> Dict[str, Any]:
    """Build module details response."""
    return _build_response_data(module_name, score)


def extract_dashboard_core_data(report) -> Dict[str, Any]:
    """Extract core dashboard data."""
    return {
        "overall_score": report["overall_compliance_score"],
        "top_modules": report["top_compliant_modules"],
        "bottom_modules": report["modules_needing_attention"],
        "critical_count": len(report["critical_violations"])
    }


def extract_dashboard_status_data(report) -> Dict[str, Any]:
    """Extract dashboard status data."""
    return {
        "violations_summary": report["violations_summary"],
        "orchestration_aligned": report["orchestration_alignment"]["aligned"],
        "last_updated": report["timestamp"]
    }


def build_dashboard_data(report) -> Dict[str, Any]:
    """Build dashboard data structure."""
    core_data = extract_dashboard_core_data(report)
    status_data = extract_dashboard_status_data(report)
    return {**core_data, **status_data}