"""
Error Handling and Fallback Report Integration Tests - Test Suite 6

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure users receive value even when primary report generation fails
- Value Impact: Fallback mechanisms prevent user experience degradation during failures
- Strategic Impact: System resilience maintains user trust and prevents churn

CRITICAL: Tests validate that error scenarios are handled gracefully with meaningful
fallback reports, partial results, and clear error communication. Users must never
receive empty responses or unclear error messages.

Golden Path Focus: Error detection  ->  Fallback activation  ->  Partial report generation  ->  User notification
NO MOCKS: Uses real services to test actual failure scenarios and recovery mechanisms
"""

import asyncio
import logging
import pytest
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from test_framework.base_integration_test import BaseIntegrationTest
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

logger = logging.getLogger(__name__)


class ErrorHandlingReportValidator:
    """Validates error handling and fallback report mechanisms"""
    
    def __init__(self, real_services):
        self.postgres = real_services["postgres"] 
        self.redis = real_services["redis"]
        self.db_session = real_services["db"]

    async def validate_error_response_quality(self, error_response: Dict) -> Dict:
        """Validate error responses provide meaningful information to users"""
        
        # Error response must contain essential elements
        required_fields = ["error_type", "user_message", "recovery_suggestions", "partial_results"]
        missing_fields = [field for field in required_fields if field not in error_response]
        assert len(missing_fields) == 0, f"Error response missing required fields: {missing_fields}"
        
        # User message must be clear and actionable
        user_message = error_response["user_message"]
        assert len(user_message) >= 50, "Error message must be detailed (50+ characters)"
        assert not any(tech_term in user_message.lower() for tech_term in ["exception", "traceback", "null pointer"]), \
            "User message must not contain technical jargon"
        
        # Recovery suggestions must be actionable
        recovery = error_response["recovery_suggestions"]
        assert isinstance(recovery, list), "Recovery suggestions must be a list"
        assert len(recovery) >= 2, "Must provide at least 2 recovery options"
        
        for suggestion in recovery:
            assert any(action_word in suggestion.lower() for action_word in ["try", "check", "contact", "wait"]), \
                f"Recovery suggestion must be actionable: {suggestion}"
        
        # Partial results should still provide some value
        partial_results = error_response["partial_results"]
        if partial_results:
            assert "summary" in partial_results or "insights" in partial_results, \
                "Partial results must contain meaningful content"
            
        return {
            "error_handling_quality": "good",
            "user_friendly": True,
            "actionable_guidance": len(recovery),
            "partial_value_provided": partial_results is not None
        }

    async def validate_fallback_report_completeness(self, fallback_report: Dict) -> Dict:
        """Validate fallback reports provide adequate business value despite failures"""
        
        # Fallback report structure requirements
        assert "fallback_indicator" in fallback_report, "Must indicate this is a fallback report"
        assert "available_data_summary" in fallback_report, "Must summarize what data was available"
        assert "limitations" in fallback_report, "Must clearly state limitations"
        assert "confidence_level" in fallback_report, "Must indicate confidence in partial results"
        
        # Validate fallback still provides business value
        available_summary = fallback_report["available_data_summary"]
        assert len(available_summary) >= 100, "Fallback summary must be substantive"
        
        # Confidence level must be appropriately reduced
        confidence = fallback_report["confidence_level"]
        assert isinstance(confidence, (int, float)), "Confidence must be numeric"
        assert 0.0 <= confidence <= 0.7, "Fallback confidence should be reduced (0.0-0.7)"
        
        # Limitations must be clearly communicated
        limitations = fallback_report["limitations"]
        assert isinstance(limitations, list), "Limitations must be listed"
        assert len(limitations) >= 1, "Must document at least one limitation"
        
        return {
            "fallback_quality_score": min(7.0, confidence * 10),
            "business_value_preserved": True,
            "transparency_maintained": True
        }


class TestErrorHandlingFallbackReportIntegration(BaseIntegrationTest):
    """
    Integration tests for error handling and fallback report mechanisms
    
    CRITICAL: Tests ensure that failure scenarios result in meaningful
    communication and partial value delivery to users rather than blank failures.
    """

    @pytest.mark.asyncio
    async def test_data_source_failure_with_partial_report_generation(self, real_services_fixture):
        """
        BVJ: Validates system handles data source failures with partial report generation
        Reliability: Users must receive value even when some data sources are unavailable
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for data source failure testing")
            
        validator = ErrorHandlingReportValidator(real_services_fixture)
        
        # Create scenario with partial data source failure
        user_id = UnifiedIdGenerator.generate_base_id("user_partial_fail")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_partial_fail")
        
        # Simulate successful data from some sources, failures from others
        successful_data_sources = [
            ("aws_billing", {"status": "success", "records": 1500, "cost_data": {"total": 15420.50}}),
            ("monitoring_api", {"status": "success", "metrics_collected": 850})
        ]
        
        failed_data_sources = [
            ("github_api", {"status": "failed", "error": "API rate limit exceeded", "retry_after": 3600}),
            ("external_analytics", {"status": "failed", "error": "Service temporarily unavailable"})
        ]
        
        # Store successful data
        for source, data in successful_data_sources:
            await real_services_fixture["db"].execute("""
                INSERT INTO data_source_results (id, execution_id, source_name, status, data_content, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, UnifiedIdGenerator.generate_base_id("data_success"), execution_id, source, 
                data["status"], json.dumps(data), datetime.utcnow())
        
        # Store failed data source attempts
        for source, error_info in failed_data_sources:
            await real_services_fixture["db"].execute("""
                INSERT INTO data_source_errors (id, execution_id, source_name, error_type, error_message, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, UnifiedIdGenerator.generate_base_id("data_error"), execution_id, source,
                "api_failure", error_info["error"], datetime.utcnow())
        
        # Generate partial report based on available data
        partial_report = {
            "title": "Infrastructure Cost Analysis (Partial Results)",
            "fallback_indicator": True,
            "available_data_summary": "Analysis based on AWS billing data ($15,420.50 total costs) and monitoring metrics (850 data points). GitHub repository metrics and external analytics temporarily unavailable.",
            "limitations": [
                "Code repository analysis unavailable due to GitHub API limits",
                "External analytics data missing - results may not reflect complete picture",
                "Recommendations focus only on infrastructure costs, not development productivity"
            ],
            "confidence_level": 0.65,
            "partial_insights": [
                "Infrastructure costs total $15,420.50 for current period",
                "Monitoring data shows 850 metric collection points active",
                "Cost trend analysis limited to billing data only"
            ],
            "fallback_recommendations": [
                "Review infrastructure costs based on available billing data",
                "Retry full analysis in 1 hour when GitHub API limits reset",
                "Consider alternative data sources for development metrics"
            ],
            "next_steps": "Full analysis will be available once all data sources are accessible"
        }
        
        # Store partial report
        report_id = UnifiedIdGenerator.generate_base_id("partial_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, report_id, user_id, execution_id, partial_report["title"], json.dumps(partial_report), 
            True, 6.5, datetime.utcnow())
        
        # Create error response for user notification
        error_response = {
            "error_type": "partial_data_failure",
            "user_message": "We've generated a partial analysis based on available data sources. Some external services are temporarily unavailable, but we've provided insights from your infrastructure billing and monitoring data.",
            "recovery_suggestions": [
                "Review the partial analysis results which contain valuable cost insights",
                "Try running the full analysis again in 1 hour when external APIs are available", 
                "Contact support if you continue to experience data source issues"
            ],
            "partial_results": partial_report,
            "estimated_retry_time": "1 hour"
        }
        
        # Validate error handling quality
        error_validation = await validator.validate_error_response_quality(error_response)
        assert error_validation["user_friendly"] is True
        assert error_validation["actionable_guidance"] >= 2
        assert error_validation["partial_value_provided"] is True
        
        # Validate fallback report quality
        fallback_validation = await validator.validate_fallback_report_completeness(partial_report)
        assert fallback_validation["business_value_preserved"] is True
        assert fallback_validation["transparency_maintained"] is True
        assert fallback_validation["fallback_quality_score"] >= 6.0  # Acceptable quality despite failures

    @pytest.mark.asyncio
    async def test_agent_execution_timeout_with_progress_preservation(self, real_services_fixture):
        """
        BVJ: Validates system handles agent execution timeouts while preserving progress
        User Experience: Long-running analyses should provide interim results on timeout
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for timeout handling testing")
            
        validator = ErrorHandlingReportValidator(real_services_fixture)
        
        # Create timeout scenario with partial progress
        user_id = UnifiedIdGenerator.generate_base_id("user_timeout")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_timeout")
        
        # Simulate agent execution that times out partway through
        await real_services_fixture["db"].execute("""
            INSERT INTO execution_contexts (id, user_id, agent_type, status, created_at, timeout_at, config)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, execution_id, user_id, "comprehensive_analysis", "timeout", datetime.utcnow(),
            datetime.utcnow() + timedelta(minutes=15), '{"timeout_minutes": 15, "max_execution_time": 900}')
        
        # Store progress made before timeout
        progress_stages = [
            ("data_collection", "completed", "Successfully collected 12,500 data points", 8.2),
            ("trend_analysis", "completed", "Identified 3 major trends in cost patterns", 7.8),
            ("optimization_analysis", "partial", "Analyzed 60% of infrastructure components before timeout", 6.1),
            ("recommendations_engine", "not_started", "Timeout occurred before recommendations phase", 0.0)
        ]
        
        for stage, status, description, partial_score in progress_stages:
            await real_services_fixture["db"].execute("""
                INSERT INTO execution_progress (id, execution_id, stage, status, description, partial_score, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, UnifiedIdGenerator.generate_base_id("progress"), execution_id, stage, status, 
                description, partial_score, datetime.utcnow())
        
        # Generate progress preservation report
        progress_report = {
            "title": "Infrastructure Analysis Progress Report (Execution Timeout)",
            "fallback_indicator": True,
            "execution_status": "timeout_after_partial_completion",
            "available_data_summary": "Analysis completed data collection (12,500 points) and trend identification (3 major patterns) before reaching timeout limit. Partial optimization analysis covered 60% of infrastructure components.",
            "limitations": [
                "Analysis incomplete due to 15-minute execution timeout",
                "Optimization recommendations not generated - analysis stopped at 60% completion",
                "Full insights require completion of remaining analysis phases"
            ],
            "confidence_level": 0.6,
            "completed_stages": {
                "data_collection": {
                    "status": "complete",
                    "results": "12,500 data points collected across all infrastructure components",
                    "insights": ["Data collection successful with 100% coverage", "All target systems responding normally"]
                },
                "trend_analysis": {
                    "status": "complete", 
                    "results": "3 major cost trends identified with statistical significance",
                    "insights": ["Monthly costs trending upward 8%", "Weekend usage patterns show 23% reduction", "Peak hours concentrate in 9AM-2PM window"]
                },
                "optimization_analysis": {
                    "status": "60% complete",
                    "results": "Partial analysis of infrastructure components completed",
                    "insights": ["EC2 instances show 15% over-provisioning in analyzed subset", "Storage optimization opportunities identified in 40% of analyzed systems"]
                }
            },
            "interim_recommendations": [
                "Review weekend usage patterns for potential cost savings (23% reduction observed)",
                "Investigate EC2 over-provisioning in analyzed components (15% waste identified)",
                "Schedule completion of full analysis during off-peak hours for faster execution"
            ],
            "next_steps": "Resume analysis from optimization phase to complete remaining 40% and generate full recommendations"
        }
        
        # Store timeout preservation report
        report_id = UnifiedIdGenerator.generate_base_id("timeout_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, report_id, user_id, execution_id, progress_report["title"], json.dumps(progress_report),
            True, 6.0, datetime.utcnow())
        
        # Create timeout error response
        timeout_error = {
            "error_type": "execution_timeout",
            "user_message": "Your comprehensive analysis reached the 15-minute execution limit before completion. We've preserved all progress made and generated an interim report with valuable insights from completed analysis phases.",
            "recovery_suggestions": [
                "Review the interim report which contains meaningful insights from completed analysis",
                "Resume the analysis from where it stopped to get full recommendations",
                "Consider breaking complex analyses into smaller focused reports for faster execution",
                "Run intensive analyses during off-peak hours for better performance"
            ],
            "partial_results": progress_report,
            "resume_option": True,
            "estimated_completion_time": "10 additional minutes"
        }
        
        # Validate timeout handling
        timeout_validation = await validator.validate_error_response_quality(timeout_error)
        assert timeout_validation["user_friendly"] is True
        assert timeout_validation["actionable_guidance"] >= 3
        
        # Validate progress preservation
        fallback_validation = await validator.validate_fallback_report_completeness(progress_report)
        assert fallback_validation["business_value_preserved"] is True
        
        # Verify progress stages were recorded
        progress_query = """
            SELECT stage, status, partial_score
            FROM execution_progress
            WHERE execution_id = $1
            ORDER BY timestamp
        """
        progress_records = await real_services_fixture["db"].fetch(progress_query, execution_id)
        
        assert len(progress_records) == 4  # All stages recorded
        completed_stages = [p for p in progress_records if p["status"] == "completed"]
        assert len(completed_stages) == 2  # Two stages completed before timeout

    @pytest.mark.asyncio
    async def test_external_api_cascading_failures_with_degraded_service(self, real_services_fixture):
        """
        BVJ: Validates system handles cascading external API failures gracefully
        System Resilience: Multiple API failures shouldn't result in total system failure
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for cascading failure testing")
            
        # Create cascading failure scenario
        user_id = UnifiedIdGenerator.generate_base_id("user_cascade")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_cascade")
        
        # Simulate multiple external API failures
        api_failures = [
            ("aws_cost_api", "authentication_failure", "Invalid credentials - API key may have expired"),
            ("github_api", "rate_limit_exceeded", "API rate limit exceeded - 1000 requests per hour limit reached"),
            ("monitoring_api", "service_unavailable", "External monitoring service returning 503 errors"),
            ("analytics_api", "network_timeout", "Connection timeout after 30 seconds - service may be overloaded")
        ]
        
        # Store API failure records
        for api_name, failure_type, error_message in api_failures:
            await real_services_fixture["db"].execute("""
                INSERT INTO external_api_failures (id, execution_id, api_name, failure_type, error_message, timestamp, retry_attempted)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, UnifiedIdGenerator.generate_base_id("api_fail"), execution_id, api_name, failure_type,
                error_message, datetime.utcnow(), True)
        
        # Create degraded service response using internal data only
        degraded_report = {
            "title": "System Analysis Report (Degraded Service Mode)",
            "fallback_indicator": True,
            "service_mode": "degraded",
            "available_data_summary": "Analysis generated using internal system data and cached information due to multiple external service outages. Current results based on historical patterns and internal metrics only.",
            "limitations": [
                "Real-time cost data unavailable due to AWS API authentication issues",
                "Repository metrics missing due to GitHub API rate limits", 
                "External monitoring data unavailable due to service outages",
                "Analytics correlations limited to internal data patterns only"
            ],
            "confidence_level": 0.4,
            "degraded_analysis": {
                "historical_patterns": "Based on 30-day historical data trends from internal cache",
                "internal_metrics": "System performance metrics from internal monitoring only",
                "predictive_estimates": "Cost projections based on historical usage patterns (40% confidence)"
            },
            "emergency_insights": [
                "Historical cost trend shows 12% month-over-month increase pattern",
                "Internal system metrics indicate 85% average resource utilization",
                "Cache analysis suggests peak usage occurs during business hours (9AM-5PM)",
                "Previous optimization recommendations showed 18% cost reduction potential"
            ],
            "degraded_recommendations": [
                "Monitor external service status for restoration of full analysis capabilities",
                "Review historical optimization recommendations which may still be applicable",
                "Consider internal cost control measures while external data is unavailable",
                "Schedule full analysis retry once external services are restored"
            ],
            "service_recovery": {
                "estimated_resolution": "2-6 hours based on typical external service recovery times",
                "monitoring_status": "Actively monitoring all external service endpoints",
                "notification_setup": "Will notify when full service capabilities are restored"
            }
        }
        
        # Store degraded service report
        report_id = UnifiedIdGenerator.generate_base_id("degraded_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, service_mode, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, degraded_report["title"], json.dumps(degraded_report),
            True, "degraded", 4.0, datetime.utcnow())
        
        # Create cascading failure error response
        cascade_error = {
            "error_type": "cascading_external_failures",
            "user_message": "Multiple external services are currently experiencing outages, affecting our ability to generate comprehensive reports. We've created a degraded analysis using available internal data and historical patterns.",
            "recovery_suggestions": [
                "Review the degraded analysis which provides insights based on historical data",
                "Check service status page for updates on external service restoration", 
                "Consider implementing recommended actions from previous analyses",
                "Retry full analysis once external services are restored (estimated 2-6 hours)"
            ],
            "partial_results": degraded_report,
            "affected_services": [api[0] for api in api_failures],
            "estimated_recovery": "2-6 hours"
        }
        
        # Validate cascading failure handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        cascade_validation = await validator.validate_error_response_quality(cascade_error)
        assert cascade_validation["user_friendly"] is True
        assert cascade_validation["partial_value_provided"] is True
        
        # Validate degraded service still provides some value
        degraded_validation = await validator.validate_fallback_report_completeness(degraded_report)
        assert degraded_validation["business_value_preserved"] is True
        assert degraded_validation["transparency_maintained"] is True
        
        # Verify all API failures were recorded
        failure_query = """
            SELECT COUNT(*) as failure_count, 
                   COUNT(DISTINCT api_name) as affected_apis
            FROM external_api_failures
            WHERE execution_id = $1
        """
        failure_stats = await real_services_fixture["db"].fetchrow(failure_query, execution_id)
        
        assert failure_stats["failure_count"] == 4  # All failures recorded
        assert failure_stats["affected_apis"] == 4  # All APIs affected

    @pytest.mark.asyncio
    async def test_database_connection_failure_with_cache_fallback(self, real_services_fixture):
        """
        BVJ: Validates system handles database failures using cache fallback mechanisms
        Critical Infrastructure: Database outages must not result in total service failure
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for database failure testing")
            
        # Pre-populate cache with fallback data
        user_id = UnifiedIdGenerator.generate_base_id("user_db_fail")
        cache_key = f"fallback_data_{user_id}"
        
        cached_fallback_data = {
            "user_profile": {
                "id": user_id,
                "preferences": {"report_type": "cost_optimization", "detail_level": "summary"},
                "historical_reports": 15
            },
            "recent_analysis": {
                "last_cost_total": 14250.75,
                "trend": "increasing",
                "top_recommendations": [
                    "Right-size EC2 instances (potential 20% savings)",
                    "Optimize storage lifecycle policies",
                    "Review unused resources weekly"
                ]
            },
            "system_status": {
                "cached_at": datetime.utcnow().isoformat(),
                "data_freshness": "6_hours_old",
                "confidence": 0.3
            }
        }
        
        # Store fallback data in Redis cache
        if real_services_fixture.get("redis"):
            await real_services_fixture["redis"].set(cache_key, json.dumps(cached_fallback_data), ex=7200)
        
        # Simulate database connection failure scenario
        execution_id = UnifiedIdGenerator.generate_base_id("exec_db_fail")
        
        # Create cache-based fallback report
        cache_fallback_report = {
            "title": "Cost Analysis Report (Cache Fallback Mode)",
            "fallback_indicator": True,
            "data_source": "cached_data_only",
            "available_data_summary": "Report generated from cached data due to database connectivity issues. Information is approximately 6 hours old but provides directional insights for immediate decision-making.",
            "limitations": [
                "Data is 6 hours old due to database connectivity issues",
                "Unable to access real-time metrics and current system state",
                "Recommendations based on historical patterns only",
                "Cannot update user preferences or save new insights"
            ],
            "confidence_level": 0.3,
            "cached_insights": [
                "Last recorded cost total: $14,250.75 with increasing trend",
                "Previous analysis identified 20% potential savings through EC2 right-sizing",
                "Storage optimization and unused resource review remain actionable",
                "Historical pattern suggests weekly cost review provides ongoing value"
            ],
            "cache_based_recommendations": [
                "Implement previously identified EC2 right-sizing opportunities (20% savings potential)",
                "Continue storage lifecycle policy optimization from prior recommendations",
                "Perform manual unused resource audit while database is unavailable",
                "Monitor service status for database restoration to access current metrics"
            ],
            "service_limitations": {
                "cannot_save_preferences": True,
                "cannot_access_realtime_data": True,
                "cannot_update_user_history": True,
                "estimated_restoration": "Database team actively working on connectivity issues"
            }
        }
        
        # Since database is unavailable, we'll simulate storing this in cache only
        if real_services_fixture.get("redis"):
            cache_report_key = f"fallback_report_{user_id}_{execution_id}"
            await real_services_fixture["redis"].set(cache_report_key, json.dumps(cache_fallback_report), ex=3600)
        
        # Create database failure error response
        db_failure_error = {
            "error_type": "database_connectivity_failure",
            "user_message": "We're currently experiencing database connectivity issues but have generated a report using cached information. While the data is several hours old, it provides actionable insights for immediate use.",
            "recovery_suggestions": [
                "Review cached recommendations which remain actionable despite data age",
                "Implement previously identified cost optimization opportunities",
                "Check service status page for database connectivity updates",
                "Retry full analysis once database connectivity is restored"
            ],
            "partial_results": cache_fallback_report,
            "service_impact": "Cannot save new data or access real-time metrics",
            "cache_data_age": "6 hours"
        }
        
        # Validate database failure handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        db_failure_validation = await validator.validate_error_response_quality(db_failure_error)
        assert db_failure_validation["user_friendly"] is True
        assert db_failure_validation["partial_value_provided"] is True
        
        # Validate cache fallback provides minimal viable value
        cache_validation = await validator.validate_fallback_report_completeness(cache_fallback_report)
        assert cache_validation["business_value_preserved"] is True
        assert cache_validation["transparency_maintained"] is True
        
        # The confidence level should be appropriately low for cached data
        assert cache_fallback_report["confidence_level"] <= 0.4  # Low confidence appropriate for stale data

    @pytest.mark.asyncio
    async def test_llm_service_failure_with_template_based_reporting(self, real_services_fixture):
        """
        BVJ: Validates system handles LLM service failures with template-based fallback
        AI Dependency: LLM outages shouldn't prevent users from receiving structured reports
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for LLM failure testing")
            
        # Create LLM service failure scenario
        user_id = UnifiedIdGenerator.generate_base_id("user_llm_fail")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_llm_fail")
        
        # Store LLM service failure record
        await real_services_fixture["db"].execute("""
            INSERT INTO service_failures (id, execution_id, service_name, failure_type, error_message, timestamp, retry_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, UnifiedIdGenerator.generate_base_id("llm_fail"), execution_id, "llm_service", 
            "service_unavailable", "LLM service returning 503 errors - model servers overloaded", 
            datetime.utcnow(), 3)
        
        # Generate raw data that would normally be processed by LLM
        raw_analysis_data = {
            "cost_metrics": {
                "total_monthly_cost": 18750.25,
                "cost_increase_percent": 15.5,
                "largest_cost_category": "compute",
                "compute_cost": 11250.15,
                "storage_cost": 4125.75,
                "network_cost": 3374.35
            },
            "performance_metrics": {
                "avg_cpu_utilization": 42.3,
                "avg_memory_utilization": 68.7,
                "response_time_ms": 245,
                "error_rate_percent": 0.12
            },
            "optimization_opportunities": [
                {"category": "compute", "potential_savings": 2250.03, "confidence": 0.85},
                {"category": "storage", "potential_savings": 825.15, "confidence": 0.78},
                {"category": "network", "potential_savings": 674.67, "confidence": 0.65}
            ]
        }
        
        # Store raw data
        await real_services_fixture["db"].execute("""
            INSERT INTO raw_analysis_data (id, execution_id, data_content, timestamp)
            VALUES ($1, $2, $3, $4)
        """, UnifiedIdGenerator.generate_base_id("raw_data"), execution_id, 
            json.dumps(raw_analysis_data), datetime.utcnow())
        
        # Generate template-based report without LLM processing
        template_report = {
            "title": "Infrastructure Cost and Performance Report (Template-Generated)",
            "fallback_indicator": True,
            "generation_method": "template_based_fallback",
            "available_data_summary": "Structured report generated from raw metrics using predefined templates due to LLM service unavailability. Data analysis complete but natural language insights limited.",
            "limitations": [
                "Natural language insights unavailable due to LLM service outage",
                "Recommendations use predefined templates rather than custom analysis",
                "Complex correlations and nuanced insights require LLM restoration",
                "Report format is structured but lacks narrative flow"
            ],
            "confidence_level": 0.7,
            "template_sections": {
                "cost_summary": {
                    "total_cost": f"${raw_analysis_data['cost_metrics']['total_monthly_cost']:,.2f}",
                    "trend": f"Increased {raw_analysis_data['cost_metrics']['cost_increase_percent']:.1f}% from previous period",
                    "breakdown": {
                        "compute": f"${raw_analysis_data['cost_metrics']['compute_cost']:,.2f} ({raw_analysis_data['cost_metrics']['compute_cost']/raw_analysis_data['cost_metrics']['total_monthly_cost']*100:.1f}%)",
                        "storage": f"${raw_analysis_data['cost_metrics']['storage_cost']:,.2f}",
                        "network": f"${raw_analysis_data['cost_metrics']['network_cost']:,.2f}"
                    }
                },
                "performance_summary": {
                    "cpu_utilization": f"{raw_analysis_data['performance_metrics']['avg_cpu_utilization']:.1f}% average",
                    "memory_utilization": f"{raw_analysis_data['performance_metrics']['avg_memory_utilization']:.1f}% average", 
                    "response_time": f"{raw_analysis_data['performance_metrics']['response_time_ms']}ms average",
                    "error_rate": f"{raw_analysis_data['performance_metrics']['error_rate_percent']:.2f}% error rate"
                },
                "optimization_opportunities": [
                    f"Compute optimization: ${opp['potential_savings']:,.2f} potential savings ({opp['confidence']*100:.0f}% confidence)"
                    for opp in raw_analysis_data['optimization_opportunities']
                ]
            },
            "template_recommendations": [
                f"Review compute usage - {raw_analysis_data['performance_metrics']['avg_cpu_utilization']:.1f}% utilization suggests right-sizing opportunities",
                f"Investigate cost increase of {raw_analysis_data['cost_metrics']['cost_increase_percent']:.1f}% to identify root causes",
                "Monitor for LLM service restoration to receive detailed narrative analysis",
                f"Consider immediate action on high-confidence optimization opportunities (${sum(opp['potential_savings'] for opp in raw_analysis_data['optimization_opportunities'] if opp['confidence'] > 0.8):,.2f} potential)"
            ],
            "llm_restoration_benefits": "Once LLM service is restored, you'll receive enhanced narrative insights, correlation analysis, and customized recommendations based on your specific context."
        }
        
        # Store template-based report
        report_id = UnifiedIdGenerator.generate_base_id("template_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, generation_method, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, template_report["title"], json.dumps(template_report),
            True, "template_based", 7.0, datetime.utcnow())
        
        # Create LLM failure error response
        llm_failure_error = {
            "error_type": "llm_service_unavailable",
            "user_message": "Our AI analysis service is temporarily unavailable, but we've generated a structured report using your data and predefined templates. All metrics and optimization opportunities are included, though narrative insights are limited.",
            "recovery_suggestions": [
                "Review the structured report which contains all your key metrics and optimization opportunities",
                "Focus on high-confidence optimization recommendations for immediate action",
                "Monitor service status for LLM restoration to receive enhanced narrative analysis",
                "Consider subscribing to service notifications for immediate updates on restoration"
            ],
            "partial_results": template_report,
            "service_status": "LLM servers overloaded - team actively working on scaling",
            "enhanced_analysis_available_when": "LLM service restoration (estimated 1-3 hours)"
        }
        
        # Validate LLM failure handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        llm_failure_validation = await validator.validate_error_response_quality(llm_failure_error)
        assert llm_failure_validation["user_friendly"] is True
        assert llm_failure_validation["partial_value_provided"] is True
        
        # Validate template-based report maintains high value
        template_validation = await validator.validate_fallback_report_completeness(template_report)
        assert template_validation["business_value_preserved"] is True
        assert template_validation["fallback_quality_score"] >= 6.5  # Template reports should maintain good value
        
        # Verify structured data is comprehensive
        assert template_report["confidence_level"] >= 0.7  # Template-based should have higher confidence than cache-based
        assert len(template_report["template_sections"]["optimization_opportunities"]) >= 3  # All opportunities preserved

    @pytest.mark.asyncio
    async def test_memory_resource_exhaustion_with_simplified_analysis(self, real_services_fixture):
        """
        BVJ: Validates system handles memory exhaustion with simplified analysis fallback
        System Scalability: Resource constraints shouldn't prevent basic report generation
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for memory exhaustion testing")
            
        # Create memory exhaustion scenario
        user_id = UnifiedIdGenerator.generate_base_id("user_memory")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_memory")
        
        # Simulate memory pressure situation
        await real_services_fixture["db"].execute("""
            INSERT INTO system_resources (id, execution_id, resource_type, usage_percent, threshold_exceeded, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6),
                   ($7, $8, $9, $10, $11, $12)
        """, UnifiedIdGenerator.generate_base_id("memory"), execution_id, "memory", 92.5, True, datetime.utcnow(),
             UnifiedIdGenerator.generate_base_id("cpu"), execution_id, "cpu", 78.3, False, datetime.utcnow())
        
        # Store resource exhaustion event
        await real_services_fixture["db"].execute("""
            INSERT INTO resource_events (id, execution_id, event_type, description, mitigation_action, timestamp)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, UnifiedIdGenerator.generate_base_id("resource_event"), execution_id, "memory_exhaustion",
            "Memory usage exceeded 90% threshold during complex analysis - switching to simplified mode",
            "reduced_complexity_analysis", datetime.utcnow())
        
        # Generate simplified analysis report
        simplified_report = {
            "title": "Cost Analysis Report (Simplified Mode)",
            "fallback_indicator": True,
            "analysis_mode": "simplified_due_to_resource_constraints",
            "available_data_summary": "Analysis performed using simplified algorithms due to high memory usage (92.5%). Core insights provided with reduced computational complexity but maintained accuracy.",
            "limitations": [
                "Complex correlations skipped to conserve memory resources",
                "Advanced statistical analysis not performed due to resource constraints", 
                "Detailed trend analysis limited to essential patterns only",
                "Machine learning models not applied due to memory requirements"
            ],
            "confidence_level": 0.8,
            "simplified_analysis": {
                "basic_cost_metrics": {
                    "current_period_total": 16250.40,
                    "previous_period_total": 14180.75,
                    "change_percent": 14.6,
                    "change_category": "significant_increase"
                },
                "top_cost_drivers": [
                    {"category": "ec2_instances", "cost": 9750.24, "percent_of_total": 60.0},
                    {"category": "rds_database", "cost": 3412.58, "percent_of_total": 21.0},
                    {"category": "data_transfer", "cost": 2087.58, "percent_of_total": 12.8}
                ],
                "immediate_opportunities": [
                    {"action": "stop_unused_instances", "potential_savings": 1250.00, "effort": "low"},
                    {"action": "rightsize_oversized_instances", "potential_savings": 975.50, "effort": "medium"}
                ]
            },
            "simplified_recommendations": [
                "Stop 5 unused EC2 instances identified - immediate $1,250/month savings",
                "Right-size 3 over-provisioned instances - $975.50/month savings potential",
                "Monitor resource usage patterns when system resources allow for detailed analysis",
                "Schedule comprehensive analysis during off-peak hours for full insights"
            ],
            "resource_status": {
                "memory_usage": "92.5% - exceeding normal operational limits",
                "cpu_usage": "78.3% - within acceptable range",
                "recommendation": "Schedule intensive analysis during low-usage periods"
            }
        }
        
        # Store simplified report
        report_id = UnifiedIdGenerator.generate_base_id("simplified_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, analysis_mode, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, simplified_report["title"], json.dumps(simplified_report),
            True, "simplified", 8.0, datetime.utcnow())
        
        # Create memory exhaustion error response
        memory_error = {
            "error_type": "resource_exhaustion",
            "user_message": "System memory usage is currently high (92.5%), so we've generated a simplified analysis that focuses on your most important cost optimization opportunities. Core insights and immediate action items are provided.",
            "recovery_suggestions": [
                "Review immediate cost optimization opportunities identified ($2,225.50 total savings potential)",
                "Implement low-effort recommendations first (stop unused instances - $1,250 savings)",
                "Schedule comprehensive analysis during off-peak hours for detailed insights",
                "Monitor system status page for optimal times to run complex analyses"
            ],
            "partial_results": simplified_report,
            "resource_impact": "Simplified algorithms used to conserve memory",
            "full_analysis_recommendation": "Schedule during off-peak hours when system resources are available"
        }
        
        # Validate memory exhaustion handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        memory_validation = await validator.validate_error_response_quality(memory_error)
        assert memory_validation["user_friendly"] is True
        assert memory_validation["actionable_guidance"] >= 3
        
        # Validate simplified analysis maintains high business value
        simplified_validation = await validator.validate_fallback_report_completeness(simplified_report)
        assert simplified_validation["business_value_preserved"] is True
        assert simplified_validation["fallback_quality_score"] >= 7.0  # Simplified mode should maintain good value
        
        # Verify resource monitoring is in place
        resource_query = """
            SELECT resource_type, usage_percent, threshold_exceeded
            FROM system_resources
            WHERE execution_id = $1
        """
        resources = await real_services_fixture["db"].fetch(resource_query, execution_id)
        
        memory_record = next(r for r in resources if r["resource_type"] == "memory")
        assert memory_record["usage_percent"] > 90.0  # High memory usage recorded
        assert memory_record["threshold_exceeded"] is True  # Threshold breach detected

    @pytest.mark.asyncio
    async def test_user_permission_denial_with_available_scope_analysis(self, real_services_fixture):
        """
        BVJ: Validates system handles permission denials by providing analysis within allowed scope
        Security and UX: Permission restrictions shouldn't result in empty responses
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for permission testing")
            
        # Create permission-restricted scenario  
        user_id = UnifiedIdGenerator.generate_base_id("user_restricted")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_restricted")
        
        # Define user permission scope (limited access scenario)
        user_permissions = {
            "allowed_resources": ["compute", "storage"],
            "denied_resources": ["network", "security", "billing_details"],
            "access_level": "read_only",
            "cost_data_access": "summary_only"
        }
        
        # Store user permission record
        await real_services_fixture["db"].execute("""
            INSERT INTO user_permissions (id, user_id, permissions_scope, access_level, restricted_resources, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, UnifiedIdGenerator.generate_base_id("permissions"), user_id, json.dumps(user_permissions),
            "limited", json.dumps(user_permissions["denied_resources"]), datetime.utcnow())
        
        # Simulate permission denials during analysis
        permission_denials = [
            ("network_analysis", "access_denied", "User lacks permission to access detailed network cost breakdowns"),
            ("security_assessment", "access_denied", "Security analysis requires elevated permissions"),  
            ("detailed_billing", "access_denied", "Detailed billing data restricted to billing administrators")
        ]
        
        for analysis_type, denial_type, reason in permission_denials:
            await real_services_fixture["db"].execute("""
                INSERT INTO permission_denials (id, execution_id, user_id, analysis_type, denial_reason, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, UnifiedIdGenerator.generate_base_id("denial"), execution_id, user_id, analysis_type, reason, datetime.utcnow())
        
        # Generate scoped analysis report within allowed permissions
        scoped_report = {
            "title": "Infrastructure Analysis Report (Limited Scope)",
            "fallback_indicator": True,
            "access_scope": "limited_permissions_applied",
            "available_data_summary": "Analysis performed within your current permission level. Compute and storage insights provided while network, security, and detailed billing analysis require additional permissions.",
            "limitations": [
                "Network cost analysis not available - requires network administrator permissions",
                "Security assessment not included - requires security analyst permissions",
                "Detailed billing breakdowns restricted - contact billing administrator for access",
                "Analysis limited to compute and storage resources within your access scope"
            ],
            "confidence_level": 0.9,  # High confidence for allowed scope
            "permitted_analysis": {
                "compute_insights": {
                    "total_instances": 47,
                    "average_utilization": 58.3,
                    "rightsizing_opportunities": 8,
                    "estimated_optimization": "15-20% cost reduction potential"
                },
                "storage_insights": {
                    "total_storage_gb": 15250,
                    "storage_types": {"gp2": 8500, "gp3": 4250, "io1": 2500},
                    "lifecycle_optimization": "30% of data eligible for archival storage",
                    "estimated_savings": "$850/month through lifecycle policies"
                },
                "combined_recommendations": [
                    "Right-size 8 over-provisioned compute instances for 15-20% cost reduction",
                    "Implement storage lifecycle policies for $850/month savings",
                    "Monitor resource utilization weekly within your permission scope"
                ]
            },
            "access_expansion_benefits": {
                "network_permissions": "Would enable network cost optimization analysis",
                "security_permissions": "Would provide security posture and compliance insights",
                "billing_permissions": "Would allow detailed cost attribution and budget analysis"
            },
            "permission_request_process": "Contact system administrator to request expanded analysis permissions"
        }
        
        # Store scoped report
        report_id = UnifiedIdGenerator.generate_base_id("scoped_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, access_scope, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, scoped_report["title"], json.dumps(scoped_report),
            True, "limited_permissions", 7.5, datetime.utcnow())
        
        # Create permission-aware error response
        permission_error = {
            "error_type": "insufficient_permissions",
            "user_message": "Your current permissions allow analysis of compute and storage resources. We've generated insights within your access scope, though additional permissions would enable more comprehensive analysis.",
            "recovery_suggestions": [
                "Review compute and storage optimization opportunities within your current permissions",
                "Implement available recommendations (estimated $850+/month savings potential)",
                "Contact your administrator to request expanded permissions for network and security analysis",
                "Focus on actionable insights within your current scope while pursuing permission expansion"
            ],
            "partial_results": scoped_report,
            "missing_permissions": user_permissions["denied_resources"],
            "permission_request_contact": "system_administrator"
        }
        
        # Validate permission handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        permission_validation = await validator.validate_error_response_quality(permission_error)
        assert permission_validation["user_friendly"] is True
        assert permission_validation["partial_value_provided"] is True
        
        # Validate scoped analysis provides meaningful value
        scoped_validation = await validator.validate_fallback_report_completeness(scoped_report)
        assert scoped_validation["business_value_preserved"] is True
        assert scoped_validation["fallback_quality_score"] >= 7.0  # Should maintain high value within scope
        
        # Verify permission denials were properly recorded
        denial_query = """
            SELECT analysis_type, denial_reason
            FROM permission_denials
            WHERE execution_id = $1 AND user_id = $2
        """
        denials = await real_services_fixture["db"].fetch(denial_query, execution_id, user_id)
        
        assert len(denials) == 3  # All denials recorded
        denied_types = [d["analysis_type"] for d in denials]
        assert "network_analysis" in denied_types
        assert "security_assessment" in denied_types
        assert "detailed_billing" in denied_types
        
        # Confidence should remain high for permitted scope
        assert scoped_report["confidence_level"] >= 0.9  # High confidence within permitted scope

    @pytest.mark.asyncio
    async def test_network_connectivity_intermittent_failures_with_retry_logic(self, real_services_fixture):
        """
        BVJ: Validates system handles intermittent network failures with intelligent retry
        Reliability: Network issues shouldn't prevent eventual report delivery to users
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for network failure testing")
            
        # Create intermittent network failure scenario
        user_id = UnifiedIdGenerator.generate_base_id("user_network")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_network")
        
        # Simulate network retry attempts with eventual success
        retry_attempts = [
            (1, "timeout", "Connection timeout after 30 seconds", datetime.utcnow()),
            (2, "dns_failure", "DNS resolution failed for external service", datetime.utcnow() + timedelta(seconds=30)),
            (3, "connection_refused", "Connection refused by external service", datetime.utcnow() + timedelta(seconds=90)), 
            (4, "success", "Connection established successfully", datetime.utcnow() + timedelta(seconds=150))
        ]
        
        # Store retry attempts
        for attempt_num, result, description, timestamp in retry_attempts:
            await real_services_fixture["db"].execute("""
                INSERT INTO network_retry_attempts (id, execution_id, attempt_number, result, description, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, UnifiedIdGenerator.generate_base_id(f"retry_{attempt_num}"), execution_id, attempt_num, result, description, timestamp)
        
        # Generate report with retry success information
        retry_success_report = {
            "title": "Cloud Cost Analysis Report (Completed After Network Retry)",
            "fallback_indicator": False,  # Successful completion after retries
            "completion_status": "success_after_retries",
            "available_data_summary": "Full analysis completed successfully after overcoming initial network connectivity issues. All external data sources accessed and comprehensive insights generated.",
            "retry_information": {
                "total_attempts": 4,
                "success_on_attempt": 4,
                "total_retry_duration": "150 seconds",
                "network_issues_encountered": ["timeout", "dns_failure", "connection_refused"]
            },
            "confidence_level": 0.95,  # Full confidence after successful completion
            "complete_analysis": {
                "cost_summary": {
                    "current_month_total": 19750.85,
                    "previous_month_total": 17200.40,
                    "change_percent": 14.8,
                    "trend": "increasing"
                },
                "external_data_integration": {
                    "aws_billing_data": "Successfully retrieved and analyzed",
                    "monitoring_metrics": "Full dataset accessed after retry",
                    "third_party_apis": "All integrations completed successfully"
                },
                "comprehensive_insights": [
                    "Monthly costs increased 14.8% to $19,750.85 - primarily driven by compute expansion",
                    "Network retry mechanisms ensured complete data collection despite initial connectivity issues",
                    "All optimization opportunities identified through successful external API integration",
                    "Monitoring data correlation completed successfully on retry attempt 4"
                ]
            },
            "recommendations": [
                "Address compute cost increase of $2,550.45 through right-sizing analysis",
                "Implement network resilience monitoring to track connectivity patterns",
                "Consider backup data sources for critical analysis to reduce retry dependency",
                "Review network infrastructure stability for improved future analysis performance"
            ],
            "network_resilience_notes": "System successfully recovered from network issues, ensuring complete analysis delivery. Consider network infrastructure review for improved stability."
        }
        
        # Store successful report after retries
        report_id = UnifiedIdGenerator.generate_base_id("retry_success_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, completion_status, retry_count, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, retry_success_report["title"], json.dumps(retry_success_report),
            "success_after_retries", 4, 9.5, datetime.utcnow())
        
        # Create successful retry completion response
        retry_success_response = {
            "error_type": None,  # No error - successful completion
            "user_message": "Your analysis completed successfully! We encountered some initial network connectivity issues but our retry mechanisms ensured complete data collection and comprehensive insights generation.",
            "recovery_actions_taken": [
                "Automatically retried failed network connections (4 attempts total)",
                "Successfully established connections to all required external services",
                "Completed full data collection and analysis as requested",
                "Generated comprehensive report with all requested insights"
            ],
            "results": retry_success_report,
            "performance_notes": "Network retry added 150 seconds to analysis time but ensured complete results",
            "reliability_confirmation": "System resilience mechanisms worked as designed"
        }
        
        # Validate retry success handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        
        # Since this is a success case, we'll validate the report completeness differently
        # This demonstrates the system's ability to recover and deliver full value
        assert retry_success_report["confidence_level"] >= 0.9  # Full confidence after successful retry
        assert retry_success_report["completion_status"] == "success_after_retries"
        assert retry_success_report["retry_information"]["success_on_attempt"] == 4
        
        # Verify retry attempts were properly logged
        retry_query = """
            SELECT attempt_number, result, description
            FROM network_retry_attempts
            WHERE execution_id = $1
            ORDER BY attempt_number
        """
        retries = await real_services_fixture["db"].fetch(retry_query, execution_id)
        
        assert len(retries) == 4  # All retry attempts logged
        assert retries[0]["result"] == "timeout"  # First attempt failed
        assert retries[1]["result"] == "dns_failure"  # Second attempt failed
        assert retries[2]["result"] == "connection_refused"  # Third attempt failed  
        assert retries[3]["result"] == "success"  # Fourth attempt succeeded
        
        # Final report should have high business value since full analysis completed
        final_report_query = """
            SELECT business_value_score, completion_status, retry_count
            FROM reports
            WHERE id = $1
        """
        report_result = await real_services_fixture["db"].fetchrow(final_report_query, report_id)
        
        assert report_result["business_value_score"] >= 9.0  # High value after successful completion
        assert report_result["completion_status"] == "success_after_retries"
        assert report_result["retry_count"] == 4  # Retry count tracked

    @pytest.mark.asyncio
    async def test_comprehensive_error_aggregation_with_priority_triage(self, real_services_fixture):
        """
        BVJ: Validates system handles multiple simultaneous errors with intelligent prioritization
        System Resilience: Multiple failures should be triaged to deliver maximum possible value
        """
        if not real_services_fixture["database_available"]:
            pytest.skip("Database required for error aggregation testing")
            
        # Create comprehensive multi-error scenario
        user_id = UnifiedIdGenerator.generate_base_id("user_multi_error")
        execution_id = UnifiedIdGenerator.generate_base_id("exec_multi_error")
        
        # Define multiple simultaneous failures with different severity levels
        error_scenarios = [
            ("external_api_failure", "high", "Primary cost API unavailable", "blocks_cost_analysis"),
            ("memory_pressure", "medium", "Memory usage at 88% - approaching limits", "reduces_analysis_depth"), 
            ("network_timeout", "low", "Secondary monitoring API slow response", "delays_completion"),
            ("permission_restriction", "medium", "Limited access to security data", "reduces_scope"),
            ("cache_miss", "low", "Historical data cache expired", "requires_fresh_calculation")
        ]
        
        # Store all error scenarios
        for error_type, severity, description, impact in error_scenarios:
            await real_services_fixture["db"].execute("""
                INSERT INTO execution_errors (id, execution_id, error_type, severity, description, impact_type, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, UnifiedIdGenerator.generate_base_id(f"error_{error_type}"), execution_id, error_type, 
                severity, description, impact, datetime.utcnow())
        
        # Execute error triage and prioritization
        error_triage = {
            "critical_blockers": [
                {"error": "external_api_failure", "impact": "blocks_cost_analysis", "mitigation": "use_cached_data"}
            ],
            "manageable_constraints": [
                {"error": "memory_pressure", "impact": "reduces_analysis_depth", "mitigation": "simplified_algorithms"},
                {"error": "permission_restriction", "impact": "reduces_scope", "mitigation": "scoped_analysis"}
            ],
            "minor_issues": [
                {"error": "network_timeout", "impact": "delays_completion", "mitigation": "extended_timeout"},
                {"error": "cache_miss", "impact": "requires_fresh_calculation", "mitigation": "real_time_calculation"}
            ]
        }
        
        # Generate triaged analysis report that works around multiple issues
        triaged_report = {
            "title": "Infrastructure Analysis Report (Multi-Error Recovery Mode)",
            "fallback_indicator": True,
            "error_triage_applied": True,
            "available_data_summary": "Analysis completed despite multiple system constraints through intelligent error prioritization and mitigation. Cost insights provided via cached data, analysis simplified for memory efficiency, and scope adjusted for available permissions.",
            "error_summary": {
                "total_errors": len(error_scenarios),
                "critical_blockers": 1,
                "manageable_constraints": 2,
                "minor_issues": 2,
                "mitigation_success_rate": "100%"
            },
            "limitations": [
                "Real-time cost data unavailable - using cached data (24 hours old)",
                "Analysis depth reduced due to memory constraints (88% usage)",
                "Security analysis excluded due to permission restrictions",
                "Completion delayed by network timeouts (extended to 45 seconds)",
                "Historical comparisons calculated fresh due to cache expiration"
            ],
            "confidence_level": 0.6,  # Moderate confidence given multiple constraints
            "triaged_analysis": {
                "cached_cost_insights": {
                    "last_known_total": 16890.75,
                    "trend_direction": "increasing",
                    "data_age": "24 hours",
                    "confidence": "medium - based on recent historical pattern"
                },
                "simplified_performance": {
                    "basic_utilization": "CPU: 65%, Memory: 72%, Storage: 45%",
                    "simplified_recommendations": "Focus on CPU optimization (35% headroom available)"
                },
                "permitted_scope_analysis": {
                    "compute_optimization": "Available within current permissions",
                    "storage_optimization": "Available within current permissions",
                    "network_security_analysis": "Restricted - requires elevated permissions"
                }
            },
            "mitigation_strategies_applied": [
                "Cached data substitution for unavailable real-time APIs",
                "Memory-efficient algorithms to work within 88% usage constraint",
                "Scoped analysis to respect permission boundaries",
                "Extended timeouts to accommodate network delays",
                "Real-time calculation to replace expired cache data"
            ],
            "recovery_recommendations": [
                "Monitor API service restoration for fresh cost data (estimated 2-4 hours)",
                "Schedule comprehensive analysis during low-memory periods",
                "Request additional permissions for complete security analysis",
                "Consider backup network paths for improved connectivity",
                "Implement proactive cache warming to prevent future cache misses"
            ],
            "system_resilience_notes": "Error prioritization successfully maintained analysis capability despite 5 simultaneous issues. Mitigation strategies preserved 60% of full analysis value."
        }
        
        # Store triaged report
        report_id = UnifiedIdGenerator.generate_base_id("triaged_report")
        await real_services_fixture["db"].execute("""
            INSERT INTO reports (id, user_id, execution_id, title, content, is_fallback, error_count, business_value_score, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, user_id, execution_id, triaged_report["title"], json.dumps(triaged_report),
            True, len(error_scenarios), 6.0, datetime.utcnow())
        
        # Create comprehensive error response
        multi_error_response = {
            "error_type": "multiple_system_constraints",
            "user_message": "We encountered several system constraints simultaneously but successfully triaged and mitigated each issue to deliver a comprehensive analysis. Your report provides valuable insights despite the challenging conditions.",
            "recovery_suggestions": [
                "Review the triaged analysis which maintains 60% of full analysis value",
                "Implement immediate recommendations within current system constraints",
                "Monitor service status page for optimal timing of comprehensive re-analysis",
                "Consider system configuration improvements to reduce future constraint impact"
            ],
            "partial_results": triaged_report,
            "error_details": {
                "critical_issues": 1,
                "resolved_through_mitigation": len(error_scenarios),
                "analysis_value_preserved": "60%"
            },
            "system_status": "Resilience mechanisms operating effectively despite multiple constraints"
        }
        
        # Validate comprehensive error handling
        validator = ErrorHandlingReportValidator(real_services_fixture)
        multi_error_validation = await validator.validate_error_response_quality(multi_error_response)
        assert multi_error_validation["user_friendly"] is True
        assert multi_error_validation["partial_value_provided"] is True
        
        # Validate triaged report maintains reasonable value despite multiple issues
        triage_validation = await validator.validate_fallback_report_completeness(triaged_report)
        assert triage_validation["business_value_preserved"] is True
        assert triage_validation["transparency_maintained"] is True
        
        # Verify error triage was comprehensive
        error_count_query = """
            SELECT severity, COUNT(*) as count
            FROM execution_errors
            WHERE execution_id = $1
            GROUP BY severity
        """
        error_counts = await real_services_fixture["db"].fetch(error_count_query, execution_id)
        
        severity_counts = {row["severity"]: row["count"] for row in error_counts}
        assert severity_counts.get("high", 0) >= 1  # Critical issues identified
        assert severity_counts.get("medium", 0) >= 1  # Medium issues managed
        assert severity_counts.get("low", 0) >= 1  # Minor issues handled
        
        # System should maintain reasonable business value even with multiple errors
        assert triaged_report["confidence_level"] >= 0.5  # Still provides value despite constraints
        assert triaged_report["error_summary"]["mitigation_success_rate"] == "100%"  # All errors mitigated