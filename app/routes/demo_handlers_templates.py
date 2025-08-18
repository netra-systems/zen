"""Demo templates and metrics handlers."""
from fastapi import HTTPException
from typing import List, Dict, Any

from app.services.demo_service import DemoService
from app.schemas.demo_schemas import IndustryTemplate, DemoMetrics


async def handle_industry_templates(
    industry: str, demo_service: DemoService
) -> List[IndustryTemplate]:
    """Get industry-specific demo templates."""
    return await execute_templates_with_error_handling(industry, demo_service)


async def execute_templates_with_error_handling(
    industry: str, demo_service: DemoService
) -> List[IndustryTemplate]:
    """Execute template retrieval with error handling."""
    return await handle_template_retrieval(industry, demo_service)


async def handle_template_retrieval(
    industry: str, demo_service: DemoService
) -> List[IndustryTemplate]:
    """Handle template retrieval with error handling."""
    try:
        return await demo_service.get_industry_templates(industry)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        handle_templates_error(e)


async def generate_metrics_from_service(
    scenario: str, duration_hours: int, demo_service: DemoService
) -> Dict[str, Any]:
    """Generate metrics through demo service."""
    return await demo_service.generate_synthetic_metrics(
        scenario=scenario, duration_hours=duration_hours
    )


async def handle_synthetic_metrics(
    scenario: str, duration_hours: int, demo_service: DemoService
) -> DemoMetrics:
    """Generate synthetic metrics."""
    return await execute_metrics_with_error_handling(scenario, duration_hours, demo_service)


async def execute_metrics_with_error_handling(
    scenario: str, duration_hours: int, demo_service: DemoService
) -> DemoMetrics:
    """Execute metrics generation with error handling."""
    return await handle_metrics_generation(scenario, duration_hours, demo_service)


async def handle_metrics_generation(
    scenario: str, duration_hours: int, demo_service: DemoService
) -> DemoMetrics:
    """Handle metrics generation with error handling."""
    try:
        metrics = await generate_metrics_from_service(scenario, duration_hours, demo_service)
        return build_demo_metrics_response(metrics)
    except Exception as e:
        handle_metrics_error(e)


def handle_templates_error(e: Exception) -> None:
    """Handle templates retrieval error."""
    from app.routes.demo_handlers_utils import log_and_raise_error
    log_and_raise_error("Failed to retrieve templates", e)


def handle_metrics_error(e: Exception) -> None:
    """Handle metrics generation error."""
    from app.routes.demo_handlers_utils import log_and_raise_error
    log_and_raise_error("Failed to generate metrics", e)


def build_demo_metrics_response(metrics: Dict[str, Any]) -> DemoMetrics:
    """Build DemoMetrics response from service data."""
    return DemoMetrics(**metrics)