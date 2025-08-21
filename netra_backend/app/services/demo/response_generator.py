"""Response generation for demo service."""

from typing import Dict, Any, List

from netra_backend.app.industry_config import get_industry_factors

def generate_demo_response(message: str, industry: str, 
                          metrics: Dict[str, Any]) -> str:
    """Generate a contextual demo response."""
    industry_context = get_industry_factors(industry)
    response = f"""Based on my analysis of your {industry} AI workloads, I've identified several optimization opportunities:

**Cost Optimization:**
- Reduce infrastructure costs by {metrics['cost_reduction_percentage']:.1f}% through intelligent model routing
- Estimated annual savings: ${metrics['estimated_annual_savings']:,.0f}

**Performance Improvements:**
- Decrease latency by {metrics['latency_improvement_ms']:.0f}ms (average)
- Increase throughput by {metrics['throughput_increase_factor']:.1f}x
- Improve model accuracy by {metrics['accuracy_improvement_percentage']:.1f}%

**Implementation Timeline:**
- Full optimization achievable in {metrics['implementation_time_weeks']} weeks
- ROI typically realized within 2-3 months

**Key Areas for {industry.title()} Optimization:**
"""
    for scenario in industry_context["typical_scenarios"][:3]:
        response += f"- {scenario.replace('_', ' ').title()}\n"
    response += f"\nConfidence Score: {metrics['confidence_score']:.2%}"
    return response

def generate_prompt_template(industry: str, scenario: str) -> str:
    """Generate a prompt template for a specific scenario."""
    return f"""Analyze and optimize {scenario.replace('_', ' ')} workloads for {industry} industry.
Consider:
- Current infrastructure and model usage
- Latency requirements and SLAs
- Cost constraints and budget
- Compliance and regulatory requirements
- Scale and growth projections

Provide specific optimization recommendations."""

def generate_optimization_scenarios(industry: str, 
                                   scenario: str) -> List[Dict[str, Any]]:
    """Generate optimization scenarios for demonstration."""
    return [
        {
            "name": "Model Selection Optimization",
            "description": "Intelligently route requests to optimal models",
            "impact": "30-40% cost reduction",
            "implementation": "2-3 weeks"
        },
        {
            "name": "Caching Strategy",
            "description": "Implement intelligent caching for common queries",
            "impact": "50-70% latency reduction",
            "implementation": "1-2 weeks"
        },
        {
            "name": "Batch Processing Optimization",
            "description": "Optimize batch sizes and processing windows",
            "impact": "2-3x throughput increase",
            "implementation": "3-4 weeks"
        }
    ]