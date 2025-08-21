"""Template management for demo service."""

from typing import Dict, Any, List

from netra_backend.app.services.demo.industry_config import INDUSTRY_FACTORS
from netra_backend.app.services.demo.response_generator import (generate_prompt_template, 
                                generate_optimization_scenarios)
from netra_backend.app.services.demo.metrics_generator import (generate_baseline_metrics,
                               generate_optimized_metrics)

async def get_industry_templates(industry: str) -> List[Dict[str, Any]]:
    """Get industry-specific templates and scenarios."""
    industry_lower = industry.lower()
    if industry_lower not in INDUSTRY_FACTORS:
        raise ValueError(f"Unknown industry: {industry}")
    industry_data = INDUSTRY_FACTORS[industry_lower]
    templates = []
    for scenario in industry_data["typical_scenarios"]:
        template = {
            "industry": industry,
            "name": scenario.replace("_", " ").title(),
            "description": f"Optimization template for {scenario.replace('_', ' ')} in {industry}",
            "prompt_template": generate_prompt_template(industry, scenario),
            "optimization_scenarios": generate_optimization_scenarios(industry, scenario),
            "typical_metrics": {
                "baseline": generate_baseline_metrics(industry),
                "optimized": generate_optimized_metrics(industry)
            }
        }
        templates.append(template)
    return templates