"""Demo handlers for industry templates and metrics."""

from fastapi import HTTPException
from typing import Dict, Any, List
from app.logging_config import central_logger as logger


async def handle_industry_templates(industry: str, demo_service) -> List[Dict[str, Any]]:
    """Handle industry template requests for demo."""
    try:
        logger.info(f"Processing industry templates request for: {industry}")
        
        # Get templates from demo service
        templates = await demo_service.get_industry_templates(industry)
        return templates
    except ValueError as e:
        logger.error(f"Invalid industry: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling industry templates: {e}")
        raise HTTPException(status_code=500, detail="Template processing failed")


async def generate_metrics_from_service(template_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate metrics from template service."""
    try:
        logger.info(f"Generating metrics for template: {template_id}")
        
        # Return mock metrics based on template
        return {
            "metrics": {
                "efficiency": 85.0,
                "cost_reduction": 12.5,
                "performance": 92.0
            },
            "template_id": template_id,
            "status": "generated"
        }
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(status_code=500, detail="Metrics generation failed")


async def handle_synthetic_metrics(scenario: str, duration_hours: int, demo_service):
    """Handle synthetic metrics generation."""
    try:
        logger.info(f"Processing synthetic metrics request - scenario: {scenario}, duration: {duration_hours}h")
        
        # Generate metrics using demo service if available
        metrics = await demo_service.generate_synthetic_metrics(scenario=scenario, duration_hours=duration_hours)
        
        # Return the raw metrics data - the route handler will convert to DemoMetrics
        return metrics
    except AttributeError:
        # Fallback if demo_service doesn't have generate_synthetic_metrics
        logger.info("Using default synthetic metrics")
        from datetime import datetime, UTC
        return {
            "latency_reduction": 60.0 + (duration_hours * 0.5),
            "throughput_increase": 200.0 + (duration_hours * 1.0),
            "cost_reduction": 45.0 + (duration_hours * 0.3),
            "accuracy_improvement": 8.5,
            "timestamps": [datetime.now(UTC)],
            "values": {
                "baseline_latency": [250.0],
                "optimized_latency": [100.0]
            }
        }
    except Exception as e:
        logger.error(f"Error handling synthetic metrics: {e}")
        raise HTTPException(status_code=500, detail="Synthetic metrics failed")


async def build_demo_metrics_response(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build formatted demo metrics response."""
    try:
        logger.info("Building demo metrics response")
        
        # Format and structure the metrics response
        return {
            "data": metrics_data,
            "formatted": True,
            "visualization_ready": True,
            "charts": [
                {"type": "bar", "data": metrics_data.get("metrics", {})},
                {"type": "line", "data": {"trend": "positive"}}
            ],
            "status": "formatted"
        }
    except Exception as e:
        logger.error(f"Error building metrics response: {e}")
        raise HTTPException(status_code=500, detail="Response building failed")