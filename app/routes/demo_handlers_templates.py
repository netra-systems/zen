"""Demo handlers for industry templates and metrics."""

from fastapi import HTTPException
from typing import Dict, Any, List
from app.logging_config import central_logger as logger


async def handle_industry_templates(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle industry template requests for demo."""
    try:
        logger.info("Processing industry templates request for demo")
        
        # Return basic template structure
        return {
            "templates": [
                {"id": "tech", "name": "Technology", "description": "Tech industry template"},
                {"id": "finance", "name": "Finance", "description": "Financial services template"},
                {"id": "healthcare", "name": "Healthcare", "description": "Healthcare industry template"}
            ],
            "status": "success"
        }
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


async def handle_synthetic_metrics(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle synthetic metrics generation."""
    try:
        logger.info("Processing synthetic metrics request")
        
        # Return synthetic metrics
        return {
            "synthetic_metrics": {
                "ai_efficiency": 78.5,
                "cost_savings": 15.2,
                "performance_boost": 88.0,
                "error_reduction": 67.3
            },
            "generated_at": "2025-08-18T16:45:00Z",
            "status": "success"
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