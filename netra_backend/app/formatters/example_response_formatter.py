"""Example Message Response Formatter

Formats agent processing results into structured, user-friendly responses
optimized for frontend display and business value demonstration.

Business Value: Transforms technical results into compelling value propositions
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ResponseFormat(Enum):
    """Available response formats"""
    DETAILED = "detailed"
    SUMMARY = "summary"
    BUSINESS_FOCUSED = "business_focused"
    TECHNICAL = "technical"


@dataclass
class FormattedMetric:
    """Formatted metric with display properties"""
    label: str
    value: str
    improvement: Optional[str] = None
    unit: Optional[str] = None
    trend: Optional[str] = None  # 'up', 'down', 'stable'
    color: Optional[str] = None  # 'green', 'red', 'blue', 'yellow'


@dataclass
class FormattedRecommendation:
    """Formatted recommendation with priority and impact"""
    title: str
    description: str
    priority: str  # 'high', 'medium', 'low'
    impact: str
    effort: str
    timeline: str
    business_value: Optional[str] = None


@dataclass
class FormattedResult:
    """Complete formatted response"""
    title: str
    summary: str
    metrics: List[FormattedMetric]
    recommendations: List[FormattedRecommendation]
    implementation_steps: List[str]
    business_impact: Dict[str, Any]
    technical_details: Optional[Dict[str, Any]] = None
    charts_data: Optional[Dict[str, Any]] = None
    export_data: Optional[Dict[str, Any]] = None


class ExampleResponseFormatter:
    """Formats example message processing results"""
    
    def __init__(self):
        self.format_strategies = {
            'cost_optimization': self._format_cost_optimization,
            'latency_optimization': self._format_latency_optimization,
            'model_selection': self._format_model_selection,
            'scaling_analysis': self._format_scaling_analysis,
            'advanced_multi_dimensional': self._format_advanced_optimization
        }
        
    def format_response(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat = ResponseFormat.BUSINESS_FOCUSED,
        user_tier: str = 'free'
    ) -> FormattedResult:
        """Main formatting method"""
        
        optimization_type = result.get('optimization_type', 'general')
        
        try:
            # Get appropriate formatter
            formatter = self.format_strategies.get(
                optimization_type,
                self._format_general_response
            )
            
            # Format the response
            formatted = formatter(result, response_format, user_tier)
            
            # Add processing metadata
            formatted.technical_details = {
                'processing_time_ms': result.get('processing_time_ms'),
                'message_id': result.get('message_id'),
                'optimization_type': optimization_type,
                'formatter_version': '1.0'
            }
            
            # Generate export data for business users
            formatted.export_data = self._generate_export_data(result, formatted)
            
            logger.debug(f"Formatted {optimization_type} response", {
                'format': response_format.value,
                'user_tier': user_tier,
                'metrics_count': len(formatted.metrics),
                'recommendations_count': len(formatted.recommendations)
            })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return self._format_error_response(str(e))
            
    def _format_cost_optimization(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format cost optimization results"""
        
        analysis = result.get('analysis', {})
        current_spending = analysis.get('current_spending', {})
        opportunities = analysis.get('optimization_opportunities', [])
        outcomes = result.get('expected_outcomes', {})
        
        # Create formatted metrics
        metrics = [
            FormattedMetric(
                label="Current Monthly Cost",
                value=current_spending.get('monthly_total', '$0'),
                color="blue"
            ),
            FormattedMetric(
                label="Potential Savings",
                value=outcomes.get('monthly_savings', '$0'),
                improvement=f"{outcomes.get('savings_percentage', '0')}% reduction",
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="Payback Period",
                value=outcomes.get('payback_period', 'N/A'),
                color="blue"
            ),
            FormattedMetric(
                label="Quality Maintenance",
                value=outcomes.get('quality_maintenance', 'N/A'),
                trend="stable",
                color="green"
            )
        ]
        
        # Create recommendations
        recommendations = []
        for i, opp in enumerate(opportunities[:3]):  # Limit to top 3
            priority = ['high', 'medium', 'low'][i] if i < 3 else 'low'
            recommendations.append(FormattedRecommendation(
                title=opp.get('strategy', ''),
                description=opp.get('description', ''),
                priority=priority,
                impact=opp.get('potential_savings', ''),
                effort=opp.get('implementation_effort', ''),
                timeline="2-4 weeks",
                business_value=f"Cost reduction: {opp.get('potential_savings', '')}"
            ))
            
        # Implementation steps
        roadmap = result.get('implementation_roadmap', {})
        steps = []
        for week, tasks in roadmap.items():
            if isinstance(tasks, list):
                steps.extend([f"{week.replace('_', ' ').title()}: {task}" for task in tasks])
                
        return FormattedResult(
            title="[U+1F4B0] Cost Optimization Analysis",
            summary=f"Identified {len(opportunities)} optimization opportunities with potential savings of {outcomes.get('monthly_savings', '$0')} per month ({outcomes.get('savings_percentage', '0')}% reduction).",
            metrics=metrics,
            recommendations=recommendations,
            implementation_steps=steps,
            business_impact={
                'monthly_savings': outcomes.get('monthly_savings', '$0'),
                'annual_impact': f"${int(outcomes.get('monthly_savings', '$0').replace('$', '').replace(',', '')) * 12:,}" if outcomes.get('monthly_savings') else '$0',
                'roi_category': 'high_impact',
                'complexity': 'medium'
            },
            charts_data=self._generate_cost_charts(result)
        )
        
    def _format_latency_optimization(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format latency optimization results"""
        
        current = result.get('current_performance', {})
        strategies = result.get('optimization_strategies', [])
        projected = result.get('projected_results', {})
        
        metrics = [
            FormattedMetric(
                label="Current Average Latency",
                value=current.get('average_latency', 'N/A'),
                color="red"
            ),
            FormattedMetric(
                label="Optimized Latency",
                value=projected.get('new_average_latency', 'N/A'),
                improvement=projected.get('improvement_factor', ''),
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="P95 Improvement",
                value=projected.get('new_p95_latency', 'N/A'),
                improvement=f"From {current.get('p95_latency', 'N/A')}",
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="User Satisfaction",
                value=projected.get('user_satisfaction_increase', 'N/A'),
                trend="up",
                color="blue"
            )
        ]
        
        recommendations = []
        for i, strategy in enumerate(strategies[:4]):
            priority = ['high', 'high', 'medium', 'low'][i] if i < 4 else 'low'
            recommendations.append(FormattedRecommendation(
                title=strategy.get('strategy', ''),
                description=strategy.get('description', ''),
                priority=priority,
                impact=strategy.get('latency_improvement', ''),
                effort="Medium",
                timeline="1-2 weeks",
                business_value=f"Latency: {strategy.get('latency_improvement', '')}"
            ))
            
        return FormattedResult(
            title=" LIGHTNING:  Latency Optimization Analysis",
            summary=f"Achieve {projected.get('improvement_factor', 'significant')} latency improvement with {len(strategies)} optimization strategies.",
            metrics=metrics,
            recommendations=recommendations,
            implementation_steps=[
                "Implement response streaming for immediate perceived improvements",
                "Deploy model optimization for different query types",
                "Set up parallel processing for multi-step operations",
                "Configure edge caching for common responses"
            ],
            business_impact={
                'latency_improvement': projected.get('improvement_factor', ''),
                'user_experience': 'Significantly improved',
                'competitive_advantage': 'High',
                'revenue_impact': 'Positive (reduced churn)'
            },
            charts_data=self._generate_latency_charts(result)
        )
        
    def _format_model_selection(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format model selection analysis results"""
        
        comparison = result.get('model_comparison', {})
        recommendations = result.get('recommendations', {})
        
        metrics = []
        for model_name, model_data in comparison.items():
            metrics.extend([
                FormattedMetric(
                    label=f"{model_name.upper()} Score",
                    value=f"{model_data.get('overall_score', 0)}/100",
                    color="blue"
                ),
                FormattedMetric(
                    label=f"{model_name.upper()} Speed",
                    value=model_data.get('performance_metrics', {}).get('speed', 'N/A'),
                    color="green"
                )
            ])
            
        # Overall impact metrics
        expected = recommendations.get('expected_impact', {})
        metrics.extend([
            FormattedMetric(
                label="Cost Reduction",
                value=expected.get('cost_reduction', '0%'),
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="Quality Improvement",
                value=expected.get('quality_improvement', '0%'),
                trend="up",
                color="green"
            )
        ])
        
        # Create model recommendations
        model_recs = []
        for model_name, model_data in comparison.items():
            model_recs.append(FormattedRecommendation(
                title=f"Use {model_name.upper()}",
                description=f"Best for: {', '.join(model_data.get('best_use_cases', []))}",
                priority="high" if model_data.get('overall_score', 0) > 90 else "medium",
                impact=f"Score: {model_data.get('overall_score', 0)}/100",
                effort="Low",
                timeline="1 week",
                business_value=f"Optimized for specific use cases"
            ))
            
        return FormattedResult(
            title="[U+1F916] Model Selection Analysis",
            summary=f"Analyzed {len(comparison)} models with recommendation for hybrid approach achieving {expected.get('cost_reduction', '0%')} cost reduction and {expected.get('quality_improvement', '0%')} quality improvement.",
            metrics=metrics,
            recommendations=model_recs,
            implementation_steps=[
                "Implement request classification system",
                "Configure model routing rules",
                "Set up performance monitoring",
                "Gradually migrate traffic to optimal models"
            ],
            business_impact={
                'cost_optimization': expected.get('cost_reduction', '0%'),
                'quality_enhancement': expected.get('quality_improvement', '0%'),
                'operational_efficiency': 'Improved',
                'scalability': 'Enhanced'
            },
            charts_data=self._generate_model_charts(result)
        )
        
    def _format_scaling_analysis(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format scaling analysis results"""
        
        current = result.get('current_metrics', {})
        projections = result.get('scaling_projections', {}).get('with_50_percent_growth', {})
        strategies = result.get('optimization_strategies', [])
        outcomes = result.get('projected_outcomes', {})
        
        metrics = [
            FormattedMetric(
                label="Current Monthly Requests",
                value=current.get('monthly_requests', '0'),
                color="blue"
            ),
            FormattedMetric(
                label="Projected Requests",
                value=projections.get('monthly_requests', '0'),
                improvement="+50% growth",
                trend="up",
                color="blue"
            ),
            FormattedMetric(
                label="Optimized Cost",
                value=projections.get('projected_cost_optimized', '$0'),
                improvement=f"vs ${projections.get('projected_cost_linear', '$0')} linear",
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="Performance Maintained",
                value=outcomes.get('performance_maintained', 'N/A'),
                color="green"
            )
        ]
        
        recommendations = []
        for i, strategy in enumerate(strategies):
            recommendations.append(FormattedRecommendation(
                title=strategy.get('strategy', ''),
                description=strategy.get('description', ''),
                priority=['high', 'medium', 'medium'][i] if i < 3 else 'low',
                impact=strategy.get('cost_savings', strategy.get('performance_improvement', '')),
                effort=strategy.get('complexity', 'Medium'),
                timeline="2-4 weeks",
                business_value=f"Scaling efficiency improvement"
            ))
            
        return FormattedResult(
            title="[U+1F4C8] Scaling Analysis",
            summary=f"Prepared for {projections.get('monthly_requests', '0')} monthly requests with {outcomes.get('cost_efficiency', 'optimized')} cost efficiency.",
            metrics=metrics,
            recommendations=recommendations,
            implementation_steps=[
                "Implement request batching system",
                "Deploy intelligent load balancing",
                "Enhance caching infrastructure",
                "Set up predictive scaling alerts"
            ],
            business_impact={
                'scalability': 'High',
                'cost_efficiency': outcomes.get('cost_efficiency', ''),
                'performance_reliability': outcomes.get('performance_maintained', ''),
                'growth_readiness': 'Excellent'
            },
            charts_data=self._generate_scaling_charts(result)
        )
        
    def _format_advanced_optimization(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format advanced multi-dimensional optimization results"""
        
        constraints = result.get('constraints_analysis', {})
        solution = result.get('optimization_solution', {})
        components = result.get('solution_components', [])
        business = result.get('business_impact', {})
        
        metrics = [
            FormattedMetric(
                label="Cost Reduction Achieved",
                value=solution.get('achieved_cost_reduction', '0%'),
                improvement=f"Target: {constraints.get('cost_reduction_target', '0%')}",
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="Latency Improvement",
                value=solution.get('achieved_latency_improvement', '1x'),
                improvement=f"Target: {constraints.get('latency_improvement_target', '1x')}",
                trend="down",
                color="green"
            ),
            FormattedMetric(
                label="Scaling Capacity",
                value=solution.get('achieved_scaling_capacity', '0%'),
                improvement=f"Target: {constraints.get('scaling_target', '0%')}",
                trend="up",
                color="green"
            ),
            FormattedMetric(
                label="Monthly Savings",
                value=business.get('monthly_savings', '$0'),
                trend="up",
                color="green"
            )
        ]
        
        recommendations = []
        for i, component in enumerate(components[:4]):
            recommendations.append(FormattedRecommendation(
                title=component.get('component', ''),
                description=f"Multi-impact optimization component",
                priority=['high', 'high', 'medium', 'medium'][i] if i < 4 else 'low',
                impact=f"Cost: {component.get('impact', {}).get('cost', 'N/A')}",
                effort="High",
                timeline="1-3 weeks",
                business_value=f"Comprehensive optimization"
            ))
            
        timeline = result.get('implementation_timeline', {})
        steps = []
        for phase, details in timeline.items():
            tasks = details.get('tasks', []) if isinstance(details, dict) else []
            improvement = details.get('expected_improvement', '') if isinstance(details, dict) else ''
            steps.extend([f"{phase.replace('_', ' ').title()}: {task} ({improvement})" for task in tasks])
            
        return FormattedResult(
            title="[U+1F680] Advanced Multi-Dimensional Optimization",
            summary=f"Achieved {solution.get('achieved_cost_reduction', '0%')} cost reduction, {solution.get('achieved_latency_improvement', '1x')} latency improvement, and {solution.get('achieved_scaling_capacity', '0%')} scaling capacity through integrated optimization approach.",
            metrics=metrics,
            recommendations=recommendations,
            implementation_steps=steps,
            business_impact={
                'cost_savings': business.get('monthly_savings', '$0'),
                'productivity_gain': business.get('productivity_increase', '0%'),
                'user_satisfaction': business.get('user_satisfaction_score', '0%'),
                'competitive_position': business.get('competitive_advantage', 'Enhanced')
            },
            charts_data=self._generate_advanced_charts(result)
        )
        
    def _format_general_response(
        self,
        result: Dict[str, Any],
        response_format: ResponseFormat,
        user_tier: str
    ) -> FormattedResult:
        """Format general/fallback responses"""
        
        return FormattedResult(
            title=" CHART:  Optimization Analysis",
            summary="Analysis completed. This demonstrates the type of detailed insights available in the full Netra platform.",
            metrics=[
                FormattedMetric(
                    label="Analysis Completed",
                    value="[U+2713]",
                    color="green"
                )
            ],
            recommendations=[
                FormattedRecommendation(
                    title="Explore Full Platform",
                    description="Access comprehensive AI optimization tools",
                    priority="high",
                    impact="High",
                    effort="Low",
                    timeline="Immediate"
                )
            ],
            implementation_steps=[
                "Sign up for detailed analysis",
                "Connect your AI infrastructure",
                "Receive personalized recommendations",
                "Implement optimizations with guidance"
            ],
            business_impact={
                'demonstration': 'Successful',
                'next_step': 'Full platform access',
                'value_preview': 'High'
            }
        )
        
    def _format_error_response(self, error_message: str) -> FormattedResult:
        """Format error responses"""
        
        return FormattedResult(
            title=" WARNING: [U+FE0F] Analysis Error",
            summary=f"An error occurred during analysis: {error_message}",
            metrics=[
                FormattedMetric(
                    label="Status",
                    value="Error",
                    color="red"
                )
            ],
            recommendations=[
                FormattedRecommendation(
                    title="Retry Analysis",
                    description="Please try again with a different example",
                    priority="high",
                    impact="Resolution",
                    effort="Low",
                    timeline="Immediate"
                )
            ],
            implementation_steps=[
                "Select a different example message",
                "Check your connection",
                "Contact support if issue persists"
            ],
            business_impact={
                'status': 'error',
                'resolution': 'retry_recommended'
            }
        )
        
    def _generate_cost_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for cost optimization"""
        
        analysis = result.get('analysis', {})
        opportunities = analysis.get('optimization_opportunities', [])
        
        return {
            'savings_breakdown': {
                'type': 'pie',
                'data': [
                    {'name': opp.get('strategy', ''), 'value': opp.get('potential_savings', '').replace('$', '').replace('/month', '').replace(',', '')}
                    for opp in opportunities
                ]
            },
            'cost_timeline': {
                'type': 'line',
                'data': {
                    'before': analysis.get('current_spending', {}).get('monthly_total', '0'),
                    'after': result.get('expected_outcomes', {}).get('monthly_savings', '0')
                }
            }
        }
        
    def _generate_latency_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for latency optimization"""
        
        current = result.get('current_performance', {})
        projected = result.get('projected_results', {})
        
        return {
            'latency_comparison': {
                'type': 'bar',
                'data': {
                    'current_avg': current.get('average_latency', '0ms').replace('ms', ''),
                    'optimized_avg': projected.get('new_average_latency', '0ms').replace('ms', ''),
                    'current_p95': current.get('p95_latency', '0ms').replace('ms', ''),
                    'optimized_p95': projected.get('new_p95_latency', '0ms').replace('ms', '')
                }
            }
        }
        
    def _generate_model_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for model selection"""
        
        comparison = result.get('model_comparison', {})
        
        return {
            'model_scores': {
                'type': 'radar',
                'data': {
                    model: {
                        'overall': data.get('overall_score', 0),
                        'accuracy': data.get('performance_metrics', {}).get('accuracy', '0%').replace('%', ''),
                        'consistency': data.get('performance_metrics', {}).get('consistency', '0%').replace('%', ''),
                        'speed': 100 - int(data.get('performance_metrics', {}).get('speed', '1000ms').replace('ms', '')) / 10
                    }
                    for model, data in comparison.items()
                }
            }
        }
        
    def _generate_scaling_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for scaling analysis"""
        
        current = result.get('current_metrics', {})
        projections = result.get('scaling_projections', {}).get('with_50_percent_growth', {})
        
        return {
            'scaling_projection': {
                'type': 'line',
                'data': {
                    'current_requests': current.get('monthly_requests', '0').replace(',', ''),
                    'projected_requests': projections.get('monthly_requests', '0').replace(',', ''),
                    'current_cost': current.get('monthly_cost', '$0').replace('$', '').replace(',', ''),
                    'optimized_cost': projections.get('projected_cost_optimized', '$0').replace('$', '').replace(',', '')
                }
            }
        }
        
    def _generate_advanced_charts(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate chart data for advanced optimization"""
        
        constraints = result.get('constraints_analysis', {})
        solution = result.get('optimization_solution', {})
        
        return {
            'optimization_results': {
                'type': 'gauge',
                'data': {
                    'cost_target': constraints.get('cost_reduction_target', '0%').replace('%', ''),
                    'cost_achieved': solution.get('achieved_cost_reduction', '0%').replace('%', ''),
                    'latency_target': constraints.get('latency_improvement_target', '1x').replace('x', ''),
                    'latency_achieved': solution.get('achieved_latency_improvement', '1x').replace('x', ''),
                    'scaling_target': constraints.get('scaling_target', '0%').replace('% usage increase', '').replace('%', ''),
                    'scaling_achieved': solution.get('achieved_scaling_capacity', '0%').replace('% growth support', '').replace('%', '')
                }
            }
        }
        
    def _generate_export_data(self, result: Dict[str, Any], formatted: FormattedResult) -> Dict[str, Any]:
        """Generate data optimized for export/sharing"""
        
        return {
            'executive_summary': {
                'title': formatted.title,
                'key_findings': formatted.summary,
                'business_impact': formatted.business_impact,
                'next_steps': formatted.implementation_steps[:3]
            },
            'metrics_summary': [
                {
                    'metric': m.label,
                    'value': m.value,
                    'improvement': m.improvement,
                    'trend': m.trend
                }
                for m in formatted.metrics
            ],
            'recommendations': [
                {
                    'title': r.title,
                    'priority': r.priority,
                    'impact': r.impact,
                    'business_value': r.business_value
                }
                for r in formatted.recommendations
            ],
            'export_metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'optimization_type': result.get('optimization_type', ''),
                'processing_time': result.get('processing_time_ms', 0)
            }
        }


# Global formatter instance
response_formatter = ExampleResponseFormatter()


def format_example_response(
    result: Dict[str, Any],
    response_format: ResponseFormat = ResponseFormat.BUSINESS_FOCUSED,
    user_tier: str = 'free'
) -> FormattedResult:
    """Public interface for formatting example responses"""
    return response_formatter.format_response(result, response_format, user_tier)


def get_response_formatter() -> ExampleResponseFormatter:
    """Get the global response formatter instance"""
    return response_formatter