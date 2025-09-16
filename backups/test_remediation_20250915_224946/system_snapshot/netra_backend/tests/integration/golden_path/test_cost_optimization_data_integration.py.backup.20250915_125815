"""
Test Cost Optimization Data Integration

Business Value Justification (BVJ):
- Segment: Mid, Enterprise (primary cost optimization users)
- Business Goal: Ensure cost optimization analysis works with real data sources
- Value Impact: Cost optimization is core value prop - delivers quantifiable ROI to users
- Strategic Impact: MISSION CRITICAL for $500K+ ARR - cost savings = primary customer value

CRITICAL REQUIREMENTS:
1. Test cost analysis with real database queries
2. Test optimization result persistence
3. Test historical cost tracking
4. Test business value calculations with real data
5. NO MOCKS for PostgreSQL/Redis - real cost data analysis
6. Use E2E authentication for all cost operations
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class CostOptimizationResult:
    """Result of cost optimization analysis."""
    analysis_id: str
    success: bool
    total_cost: float
    potential_savings: float
    recommendations_count: int
    data_sources: List[str]
    execution_time: float
    data_persisted: bool
    error_message: Optional[str] = None


class TestCostOptimizationDataIntegration(BaseIntegrationTest):
    """Test cost optimization with real PostgreSQL data persistence."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cost_analysis_with_database_queries(self, real_services_fixture):
        """Test cost analysis with real database queries."""
        user_context = await create_authenticated_user_context(
            user_email=f"cost_analysis_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Set up cost data in database
        cost_data_setup = await self._setup_cost_data(
            db_session, str(user_context.user_id)
        )
        assert cost_data_setup["success"], "Cost data setup should succeed"
        
        # Perform cost analysis
        analysis_result = await self._perform_cost_analysis(
            db_session, str(user_context.user_id)
        )
        
        assert analysis_result.success, f"Cost analysis failed: {analysis_result.error_message}"
        assert analysis_result.total_cost > 0, "Should calculate total costs"
        assert analysis_result.potential_savings > 0, "Should identify savings opportunities"
        assert analysis_result.data_persisted, "Analysis should be persisted"
        
        # Verify business value delivered
        self.assert_business_value_delivered(
            {
                "cost_analysis_completed": True,
                "potential_savings": analysis_result.potential_savings,
                "recommendations": analysis_result.recommendations_count
            },
            "cost_savings"
        )
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_optimization_result_persistence(self, real_services_fixture):
        """Test optimization result persistence to database."""
        user_context = await create_authenticated_user_context(
            user_email=f"optimization_persist_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Create optimization results
        optimization_data = {
            "total_monthly_cost": 5000.00,
            "optimization_categories": [
                {"category": "compute", "current_cost": 2000, "optimized_cost": 1500, "savings": 500},
                {"category": "storage", "current_cost": 1500, "optimized_cost": 1200, "savings": 300},
                {"category": "network", "current_cost": 1500, "optimized_cost": 1400, "savings": 100}
            ],
            "total_potential_savings": 900,
            "implementation_priority": ["high", "medium", "low"],
            "confidence_score": 0.87
        }
        
        # Persist optimization results
        persistence_result = await self._persist_optimization_results(
            db_session, str(user_context.user_id), optimization_data
        )
        
        assert persistence_result["success"], f"Persistence failed: {persistence_result['error']}"
        assert persistence_result["optimization_id"] is not None
        
        # Retrieve and verify persisted data
        optimization_id = persistence_result["optimization_id"]
        retrieved_data = await self._retrieve_optimization_results(
            db_session, optimization_id
        )
        
        assert retrieved_data["found"], "Should retrieve persisted optimization"
        assert retrieved_data["data"]["total_potential_savings"] == 900
        assert len(retrieved_data["data"]["optimization_categories"]) == 3
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_historical_cost_tracking(self, real_services_fixture):
        """Test historical cost tracking with real data."""
        user_context = await create_authenticated_user_context(
            user_email=f"cost_tracking_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Create historical cost data
        historical_data = await self._create_historical_cost_data(
            db_session, str(user_context.user_id)
        )
        assert historical_data["success"], "Historical data creation should succeed"
        
        # Analyze cost trends
        trend_analysis = await self._analyze_cost_trends(
            db_session, str(user_context.user_id)
        )
        
        assert trend_analysis["success"], f"Trend analysis failed: {trend_analysis['error']}"
        assert trend_analysis["data_points"] >= 6, "Should have sufficient historical data"
        assert "monthly_growth_rate" in trend_analysis, "Should calculate growth rate"
        assert "cost_pattern" in trend_analysis, "Should identify cost patterns"
        
        # Test cost forecasting
        forecast_result = await self._forecast_future_costs(
            db_session, str(user_context.user_id), months_ahead=3
        )
        
        assert forecast_result["success"], "Cost forecasting should succeed"
        assert len(forecast_result["forecasts"]) == 3, "Should forecast 3 months"
        
    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_business_value_calculations(self, real_services_fixture):
        """Test business value calculations with real data."""
        user_context = await create_authenticated_user_context(
            user_email=f"business_value_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Set up comprehensive cost scenario
        scenario_data = {
            "current_monthly_spend": 8000.00,
            "infrastructure_details": {
                "compute_instances": 45,
                "storage_gb": 15000,
                "network_gb_transfer": 5000,
                "managed_services": 8
            },
            "usage_patterns": {
                "peak_utilization": 0.75,
                "off_peak_utilization": 0.30,
                "weekend_utilization": 0.20
            }
        }
        
        # Calculate business value impact
        value_calculation = await self._calculate_business_value_impact(
            db_session, str(user_context.user_id), scenario_data
        )
        
        assert value_calculation["success"], f"Value calculation failed: {value_calculation['error']}"
        
        business_impact = value_calculation["business_impact"]
        assert business_impact["roi_percentage"] > 0, "Should show positive ROI"
        assert business_impact["payback_months"] <= 12, "Should have reasonable payback period"
        assert business_impact["annual_savings"] > 0, "Should calculate annual savings"
        
        # Verify business value metrics
        metrics = business_impact["metrics"]
        assert "cost_reduction_percentage" in metrics
        assert "efficiency_improvement" in metrics
        assert "resource_optimization_score" in metrics
        
        # Test different customer segments
        segment_tests = ["mid", "enterprise"]
        
        for segment in segment_tests:
            segment_value = await self._calculate_segment_specific_value(
                db_session, str(user_context.user_id), scenario_data, segment
            )
            
            assert segment_value["success"], f"Segment {segment} calculation failed"
            assert segment_value["segment_benefits"] is not None
            
            if segment == "enterprise":
                # Enterprise should get additional benefits
                assert "compliance_value" in segment_value["segment_benefits"]
                assert "scale_efficiency" in segment_value["segment_benefits"]
    
    # Helper methods for cost optimization testing
    
    async def _create_user_in_database(self, db_session, user_context):
        """Create user in database for cost optimization testing."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"Cost Optimization User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _setup_cost_data(self, db_session, user_id: str) -> Dict[str, Any]:
        """Set up cost data for analysis."""
        try:
            # Create sample cost data
            cost_entries = [
                {"service": "ec2", "cost": 2500.00, "month": "2024-01"},
                {"service": "s3", "cost": 800.00, "month": "2024-01"},
                {"service": "rds", "cost": 1200.00, "month": "2024-01"},
                {"service": "ec2", "cost": 2800.00, "month": "2024-02"},
                {"service": "s3", "cost": 850.00, "month": "2024-02"},
                {"service": "rds", "cost": 1250.00, "month": "2024-02"},
            ]
            
            cost_insert = """
                INSERT INTO user_cost_data (
                    user_id, service_name, monthly_cost, billing_month, created_at
                ) VALUES (
                    %(user_id)s, %(service)s, %(cost)s, %(month)s, %(created_at)s
                )
            """
            
            for entry in cost_entries:
                await db_session.execute(cost_insert, {
                    "user_id": user_id,
                    "service": entry["service"],
                    "cost": entry["cost"],
                    "month": entry["month"],
                    "created_at": datetime.now(timezone.utc)
                })
            
            await db_session.commit()
            
            return {"success": True, "entries_created": len(cost_entries)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _perform_cost_analysis(self, db_session, user_id: str) -> CostOptimizationResult:
        """Perform cost analysis with database queries."""
        start_time = time.time()
        analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
        
        try:
            # Query user cost data
            cost_query = """
                SELECT service_name, SUM(monthly_cost) as total_cost, COUNT(*) as months
                FROM user_cost_data
                WHERE user_id = %(user_id)s
                GROUP BY service_name
                ORDER BY total_cost DESC
            """
            
            result = await db_session.execute(cost_query, {"user_id": user_id})
            cost_data = result.fetchall()
            
            if not cost_data:
                return CostOptimizationResult(
                    analysis_id=analysis_id,
                    success=False,
                    total_cost=0,
                    potential_savings=0,
                    recommendations_count=0,
                    data_sources=[],
                    execution_time=time.time() - start_time,
                    data_persisted=False,
                    error_message="No cost data found"
                )
            
            # Calculate optimization opportunities
            total_cost = sum(row.total_cost for row in cost_data)
            
            # Simulated optimization analysis
            optimization_recommendations = []
            total_savings = 0
            
            for row in cost_data:
                service = row.service_name
                service_cost = row.total_cost
                
                # Service-specific optimization calculations
                if service == "ec2":
                    savings = service_cost * 0.25  # 25% savings through right-sizing
                    optimization_recommendations.append({
                        "service": service,
                        "recommendation": "Right-size instances based on utilization",
                        "potential_savings": savings
                    })
                elif service == "s3":
                    savings = service_cost * 0.15  # 15% savings through storage optimization
                    optimization_recommendations.append({
                        "service": service,
                        "recommendation": "Optimize storage classes and lifecycle policies",
                        "potential_savings": savings
                    })
                elif service == "rds":
                    savings = service_cost * 0.20  # 20% savings through reserved instances
                    optimization_recommendations.append({
                        "service": service,
                        "recommendation": "Use Reserved Instances for stable workloads",
                        "potential_savings": savings
                    })
                
                total_savings += savings
            
            # Persist analysis results
            analysis_insert = """
                INSERT INTO cost_optimization_analyses (
                    id, user_id, total_cost, potential_savings, 
                    recommendations_data, created_at
                ) VALUES (
                    %(analysis_id)s, %(user_id)s, %(total_cost)s, %(savings)s,
                    %(recommendations)s, %(created_at)s
                )
            """
            
            await db_session.execute(analysis_insert, {
                "analysis_id": analysis_id,
                "user_id": user_id,
                "total_cost": total_cost,
                "savings": total_savings,
                "recommendations": json.dumps(optimization_recommendations),
                "created_at": datetime.now(timezone.utc)
            })
            await db_session.commit()
            
            return CostOptimizationResult(
                analysis_id=analysis_id,
                success=True,
                total_cost=total_cost,
                potential_savings=total_savings,
                recommendations_count=len(optimization_recommendations),
                data_sources=["user_cost_data"],
                execution_time=time.time() - start_time,
                data_persisted=True
            )
            
        except Exception as e:
            return CostOptimizationResult(
                analysis_id=analysis_id,
                success=False,
                total_cost=0,
                potential_savings=0,
                recommendations_count=0,
                data_sources=[],
                execution_time=time.time() - start_time,
                data_persisted=False,
                error_message=str(e)
            )
    
    async def _persist_optimization_results(
        self, db_session, user_id: str, optimization_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist optimization results to database."""
        try:
            optimization_id = f"opt_{uuid.uuid4().hex[:8]}"
            
            optimization_insert = """
                INSERT INTO optimization_results (
                    id, user_id, optimization_data, created_at
                ) VALUES (
                    %(opt_id)s, %(user_id)s, %(data)s, %(created_at)s
                )
            """
            
            await db_session.execute(optimization_insert, {
                "opt_id": optimization_id,
                "user_id": user_id,
                "data": json.dumps(optimization_data),
                "created_at": datetime.now(timezone.utc)
            })
            await db_session.commit()
            
            return {
                "success": True,
                "optimization_id": optimization_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _retrieve_optimization_results(
        self, db_session, optimization_id: str
    ) -> Dict[str, Any]:
        """Retrieve optimization results from database."""
        try:
            retrieve_query = """
                SELECT optimization_data, created_at
                FROM optimization_results
                WHERE id = %(opt_id)s
            """
            
            result = await db_session.execute(retrieve_query, {"opt_id": optimization_id})
            row = result.fetchone()
            
            if row:
                return {
                    "found": True,
                    "data": json.loads(row.optimization_data),
                    "created_at": row.created_at
                }
            else:
                return {"found": False}
                
        except Exception as e:
            return {
                "found": False,
                "error": str(e)
            }
    
    async def _create_historical_cost_data(self, db_session, user_id: str) -> Dict[str, Any]:
        """Create historical cost data for trend analysis."""
        try:
            # Generate 6 months of historical data
            historical_entries = []
            base_cost = 4000.00
            
            for i in range(6):
                month_date = (datetime.now() - timedelta(days=30 * i)).replace(day=1)
                # Simulate cost growth over time
                month_cost = base_cost + (i * 200) + (i * i * 50)  # Accelerating growth
                
                historical_entries.append({
                    "user_id": user_id,
                    "month": month_date.strftime("%Y-%m"),
                    "total_cost": month_cost,
                    "compute_cost": month_cost * 0.5,
                    "storage_cost": month_cost * 0.3,
                    "network_cost": month_cost * 0.2
                })
            
            history_insert = """
                INSERT INTO historical_costs (
                    user_id, billing_month, total_cost, compute_cost, 
                    storage_cost, network_cost, created_at
                ) VALUES (
                    %(user_id)s, %(month)s, %(total_cost)s, %(compute_cost)s,
                    %(storage_cost)s, %(network_cost)s, %(created_at)s
                )
            """
            
            for entry in historical_entries:
                await db_session.execute(history_insert, {
                    **entry,
                    "created_at": datetime.now(timezone.utc)
                })
            
            await db_session.commit()
            
            return {
                "success": True,
                "months_created": len(historical_entries)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_cost_trends(self, db_session, user_id: str) -> Dict[str, Any]:
        """Analyze cost trends from historical data."""
        try:
            trend_query = """
                SELECT billing_month, total_cost, compute_cost, storage_cost, network_cost
                FROM historical_costs
                WHERE user_id = %(user_id)s
                ORDER BY billing_month ASC
            """
            
            result = await db_session.execute(trend_query, {"user_id": user_id})
            historical_data = result.fetchall()
            
            if len(historical_data) < 2:
                return {
                    "success": False,
                    "error": "Insufficient historical data for trend analysis"
                }
            
            # Calculate growth rate
            first_month = historical_data[0].total_cost
            last_month = historical_data[-1].total_cost
            months_span = len(historical_data) - 1
            
            monthly_growth_rate = ((last_month / first_month) ** (1 / months_span) - 1) * 100
            
            # Identify cost pattern
            costs = [row.total_cost for row in historical_data]
            if all(costs[i] <= costs[i + 1] for i in range(len(costs) - 1)):
                cost_pattern = "consistently_increasing"
            elif all(costs[i] >= costs[i + 1] for i in range(len(costs) - 1)):
                cost_pattern = "consistently_decreasing"
            else:
                cost_pattern = "variable"
            
            return {
                "success": True,
                "data_points": len(historical_data),
                "monthly_growth_rate": round(monthly_growth_rate, 2),
                "cost_pattern": cost_pattern,
                "first_month_cost": first_month,
                "latest_month_cost": last_month
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _forecast_future_costs(
        self, db_session, user_id: str, months_ahead: int
    ) -> Dict[str, Any]:
        """Forecast future costs based on historical trends."""
        try:
            # Get trend data first
            trend_analysis = await self._analyze_cost_trends(db_session, user_id)
            
            if not trend_analysis["success"]:
                return trend_analysis
            
            # Simple linear forecasting
            growth_rate = trend_analysis["monthly_growth_rate"] / 100
            latest_cost = trend_analysis["latest_month_cost"]
            
            forecasts = []
            for month in range(1, months_ahead + 1):
                forecasted_cost = latest_cost * ((1 + growth_rate) ** month)
                future_date = (datetime.now() + timedelta(days=30 * month)).strftime("%Y-%m")
                
                forecasts.append({
                    "month": future_date,
                    "forecasted_cost": round(forecasted_cost, 2)
                })
            
            return {
                "success": True,
                "forecasts": forecasts,
                "growth_rate_used": growth_rate * 100
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _calculate_business_value_impact(
        self, db_session, user_id: str, scenario_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate business value impact of cost optimization."""
        try:
            current_monthly_spend = scenario_data["current_monthly_spend"]
            
            # Calculate optimization potential based on infrastructure details
            infrastructure = scenario_data["infrastructure_details"]
            usage_patterns = scenario_data["usage_patterns"]
            
            # Compute optimization opportunities
            compute_optimization = current_monthly_spend * 0.3 * (1 - usage_patterns["peak_utilization"])
            storage_optimization = current_monthly_spend * 0.2 * 0.15  # 15% storage savings
            network_optimization = current_monthly_spend * 0.15 * 0.10  # 10% network savings
            
            total_monthly_savings = compute_optimization + storage_optimization + network_optimization
            annual_savings = total_monthly_savings * 12
            
            # Calculate ROI and payback
            implementation_cost = 5000  # Estimated implementation cost
            roi_percentage = (annual_savings / implementation_cost) * 100
            payback_months = implementation_cost / total_monthly_savings
            
            # Calculate efficiency metrics
            cost_reduction_percentage = (total_monthly_savings / current_monthly_spend) * 100
            resource_optimization_score = min(100, cost_reduction_percentage * 2)  # Weighted score
            
            business_impact = {
                "monthly_savings": round(total_monthly_savings, 2),
                "annual_savings": round(annual_savings, 2),
                "roi_percentage": round(roi_percentage, 2),
                "payback_months": round(payback_months, 1),
                "metrics": {
                    "cost_reduction_percentage": round(cost_reduction_percentage, 2),
                    "efficiency_improvement": round(resource_optimization_score, 2),
                    "resource_optimization_score": round(resource_optimization_score, 2)
                }
            }
            
            # Persist business value calculation
            value_insert = """
                INSERT INTO business_value_calculations (
                    user_id, calculation_data, created_at
                ) VALUES (
                    %(user_id)s, %(data)s, %(created_at)s
                )
            """
            
            await db_session.execute(value_insert, {
                "user_id": user_id,
                "data": json.dumps({
                    "scenario": scenario_data,
                    "business_impact": business_impact
                }),
                "created_at": datetime.now(timezone.utc)
            })
            await db_session.commit()
            
            return {
                "success": True,
                "business_impact": business_impact
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _calculate_segment_specific_value(
        self, db_session, user_id: str, scenario_data: Dict[str, Any], segment: str
    ) -> Dict[str, Any]:
        """Calculate segment-specific business value."""
        try:
            base_calculation = await self._calculate_business_value_impact(
                db_session, user_id, scenario_data
            )
            
            if not base_calculation["success"]:
                return base_calculation
            
            base_impact = base_calculation["business_impact"]
            segment_benefits = {}
            
            if segment == "enterprise":
                # Enterprise gets additional benefits
                segment_benefits = {
                    "compliance_value": base_impact["annual_savings"] * 0.1,  # 10% compliance benefit
                    "scale_efficiency": base_impact["annual_savings"] * 0.05,  # 5% scale benefit
                    "priority_support": True,
                    "dedicated_success_manager": True
                }
            elif segment == "mid":
                # Mid-tier gets moderate additional benefits
                segment_benefits = {
                    "implementation_support": True,
                    "monthly_optimization_reviews": True
                }
            
            return {
                "success": True,
                "base_impact": base_impact,
                "segment_benefits": segment_benefits,
                "segment": segment
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }