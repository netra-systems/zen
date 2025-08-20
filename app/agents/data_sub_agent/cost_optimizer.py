"""Cost Optimizer - AI Workload Cost Analysis and Optimization

Core component for identifying cost optimization opportunities.
Critical for capturing performance fees through 15-30% cost savings.

Business Value: Direct revenue impact through performance fee model.
"""

from typing import Dict, Any, List, Optional, Tuple
import statistics
from datetime import datetime, timedelta

from app.logging_config import central_logger


class CostOptimizer:
    """Analyzes and optimizes AI workload costs."""
    
    def __init__(self, clickhouse_client):
        self.logger = central_logger.get_logger("CostOptimizer")
        self.clickhouse_client = clickhouse_client
        
        # Cost optimization thresholds
        self.thresholds = {
            "high_cost_per_request_cents": 5.0,
            "cost_efficiency_threshold": 0.8,
            "min_savings_percentage": 10.0,
            "target_savings_percentage": 25.0
        }
    
    async def analyze_costs(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main cost analysis and optimization workflow."""
        timeframe = request.get("timeframe", "24h")
        user_id = request.get("user_id")
        
        try:
            # Get cost breakdown data
            cost_data = await self.clickhouse_client.get_cost_breakdown(timeframe, user_id)
            
            if not cost_data:
                return self._create_no_data_result()
            
            # Perform comprehensive cost analysis
            analysis_results = {
                "summary": f"Cost analysis for {len(cost_data)} workload types over {timeframe}",
                "data_points": sum(row.get("request_count", 0) for row in cost_data),
                "findings": [],
                "recommendations": [],
                "cost_breakdown": cost_data,
                "optimization_opportunities": [],
                "savings_potential": {}
            }
            
            # Analyze cost efficiency by workload type
            efficiency_analysis = self._analyze_cost_efficiency(cost_data)
            analysis_results["cost_efficiency"] = efficiency_analysis
            analysis_results["findings"].extend(efficiency_analysis.get("findings", []))
            
            # Identify optimization opportunities
            optimizations = self._identify_optimization_opportunities(cost_data)
            analysis_results["optimization_opportunities"] = optimizations
            analysis_results["findings"].extend(optimizations.get("findings", []))
            
            # Calculate potential savings
            savings = self._calculate_savings_potential(cost_data, optimizations)
            analysis_results["savings_potential"] = savings
            
            # Generate actionable recommendations
            analysis_results["recommendations"] = self._generate_cost_recommendations(analysis_results)
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Cost analysis failed: {e}")
            return {"error": str(e), "data_points": 0}
    
    def _analyze_cost_efficiency(self, cost_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost efficiency across workload types."""
        if not cost_data:
            return {"error": "No cost data for efficiency analysis"}
        
        efficiency_metrics = []
        findings = []
        
        for workload in cost_data:
            workload_type = workload.get("workload_type", "unknown")
            avg_cost = workload.get("avg_cost_cents", 0)
            request_count = workload.get("request_count", 0)
            total_cost = workload.get("total_cost_cents", 0)
            
            # Calculate efficiency score (lower cost per request = higher efficiency)
            efficiency_score = 1.0 / (avg_cost + 0.1) if avg_cost > 0 else 0
            
            efficiency_data = {
                "workload_type": workload_type,
                "avg_cost_cents": avg_cost,
                "total_cost_cents": total_cost,
                "request_count": request_count,
                "efficiency_score": efficiency_score,
                "cost_per_thousand_requests": (avg_cost * 1000) if avg_cost > 0 else 0
            }
            
            efficiency_metrics.append(efficiency_data)
            
            # Generate findings for high-cost workloads
            if avg_cost > self.thresholds["high_cost_per_request_cents"]:
                findings.append(
                    f"High-cost workload: {workload_type} averages {avg_cost:.2f} cents per request"
                )
        
        # Sort by efficiency (lowest cost per request first)
        efficiency_metrics.sort(key=lambda x: x["avg_cost_cents"])
        
        return {
            "efficiency_metrics": efficiency_metrics,
            "findings": findings,
            "most_efficient": efficiency_metrics[0] if efficiency_metrics else None,
            "least_efficient": efficiency_metrics[-1] if efficiency_metrics else None
        }
    
    def _identify_optimization_opportunities(self, cost_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify specific cost optimization opportunities."""
        opportunities = []
        findings = []
        
        if not cost_data:
            return {"opportunities": [], "findings": []}
        
        # Calculate overall statistics for comparison
        all_avg_costs = [row["avg_cost_cents"] for row in cost_data if row.get("avg_cost_cents", 0) > 0]
        
        if not all_avg_costs:
            return {"opportunities": [], "findings": []}
        
        median_cost = statistics.median(all_avg_costs)
        mean_cost = statistics.mean(all_avg_costs)
        
        for workload in cost_data:
            workload_type = workload.get("workload_type", "unknown")
            avg_cost = workload.get("avg_cost_cents", 0)
            total_cost = workload.get("total_cost_cents", 0)
            request_count = workload.get("request_count", 0)
            
            # Identify high-cost workloads relative to median
            if avg_cost > median_cost * 1.5:
                potential_savings_per_request = avg_cost - median_cost
                total_potential_savings = potential_savings_per_request * request_count
                
                opportunity = {
                    "type": "high_cost_workload",
                    "workload_type": workload_type,
                    "current_avg_cost_cents": avg_cost,
                    "target_avg_cost_cents": median_cost,
                    "potential_savings_per_request_cents": potential_savings_per_request,
                    "total_potential_savings_cents": total_potential_savings,
                    "request_count": request_count,
                    "optimization_strategies": self._get_optimization_strategies(workload_type, avg_cost)
                }
                
                opportunities.append(opportunity)
                
                savings_pct = (potential_savings_per_request / avg_cost) * 100
                findings.append(
                    f"Optimization opportunity: {workload_type} could save {savings_pct:.1f}% ({potential_savings_per_request:.2f} cents per request)"
                )
        
        return {
            "opportunities": opportunities,
            "findings": findings,
            "baseline_costs": {
                "median_cost_cents": median_cost,
                "mean_cost_cents": mean_cost
            }
        }
    
    def _get_optimization_strategies(self, workload_type: str, avg_cost: float) -> List[str]:
        """Get specific optimization strategies for workload type."""
        strategies = []
        
        # General strategies based on cost level
        if avg_cost > 10.0:
            strategies.extend([
                "Consider switching to smaller/cheaper model",
                "Implement request batching",
                "Add response caching for repeated queries"
            ])
        elif avg_cost > 5.0:
            strategies.extend([
                "Optimize prompt length and complexity",
                "Implement intelligent caching"
            ])
        
        # Workload-specific strategies
        workload_lower = workload_type.lower()
        if "chat" in workload_lower:
            strategies.append("Use conversation context management to reduce token usage")
        elif "embedding" in workload_lower:
            strategies.append("Batch embedding requests to reduce API overhead")
        elif "completion" in workload_lower:
            strategies.append("Optimize max_tokens parameter based on actual usage")
        
        return strategies
    
    def _calculate_savings_potential(self, cost_data: List[Dict[str, Any]], 
                                   optimizations: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate total savings potential across all optimizations."""
        if not optimizations.get("opportunities"):
            return {"total_savings_cents": 0, "savings_percentage": 0}
        
        total_current_cost = sum(row.get("total_cost_cents", 0) for row in cost_data)
        total_potential_savings = sum(
            opp.get("total_potential_savings_cents", 0) 
            for opp in optimizations["opportunities"]
        )
        
        savings_percentage = (
            (total_potential_savings / total_current_cost) * 100 
            if total_current_cost > 0 else 0
        )
        
        # Cap savings at realistic maximum
        savings_percentage = min(savings_percentage, self.thresholds["target_savings_percentage"])
        total_potential_savings = (savings_percentage / 100) * total_current_cost
        
        return {
            "total_current_cost_cents": total_current_cost,
            "total_potential_savings_cents": total_potential_savings,
            "savings_percentage": savings_percentage,
            "monthly_projection_cents": total_potential_savings * 30,
            "annual_projection_cents": total_potential_savings * 365,
            "meets_minimum_threshold": savings_percentage >= self.thresholds["min_savings_percentage"]
        }
    
    def _generate_cost_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate prioritized cost optimization recommendations."""
        recommendations = []
        savings_potential = analysis.get("savings_potential", {})
        
        if savings_potential.get("savings_percentage", 0) >= self.thresholds["min_savings_percentage"]:
            recommendations.append(
                f"Immediate action recommended: {savings_potential['savings_percentage']:.1f}% cost reduction possible "
                f"(${savings_potential['total_potential_savings_cents'] / 100:.2f} potential monthly savings)"
            )
        
        # Top optimization opportunities
        opportunities = analysis.get("optimization_opportunities", {}).get("opportunities", [])
        if opportunities:
            # Sort by potential savings
            top_opportunities = sorted(
                opportunities, 
                key=lambda x: x.get("total_potential_savings_cents", 0), 
                reverse=True
            )[:3]
            
            for i, opp in enumerate(top_opportunities, 1):
                strategies = opp.get("optimization_strategies", [])
                if strategies:
                    recommendations.append(
                        f"Priority {i}: {opp['workload_type']} - {strategies[0]}"
                    )
        
        # General recommendations if no specific opportunities
        if not recommendations:
            recommendations.extend([
                "Monitor workload costs regularly for optimization opportunities",
                "Consider implementing cost alerting for high-spend workloads",
                "Review model selection for cost-performance optimization"
            ])
        
        return recommendations
    
    def _create_no_data_result(self) -> Dict[str, Any]:
        """Create result for when no cost data is available."""
        return {
            "summary": "No cost data available for optimization analysis",
            "data_points": 0,
            "findings": ["Insufficient cost data for analysis"],
            "recommendations": ["Ensure cost metrics are being tracked in workload events"],
            "savings_potential": {"total_savings_cents": 0, "savings_percentage": 0}
        }
