"""Quality Dashboard API Routes

This module provides API endpoints for quality monitoring, reporting, and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, UTC
from pydantic import BaseModel, Field
from enum import Enum

from app.logging_config import central_logger
from app.auth.auth_dependencies import get_current_user
from app.services.quality_gate_service import QualityGateService, ContentType
from app.services.quality_monitoring_service import QualityMonitoringService, AlertSeverity
from app.services.fallback_response_service import FallbackResponseService
from app.redis_manager import get_redis_manager, RedisManager
from app.dependencies import DbDep
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.quality_types import (
    User, QualityValidationRequest, QualityValidationResponse,
    QualityAlert, AlertAcknowledgement, AlertAcknowledgementResponse,
    QualityDashboardData, QualityReport, QualityReportType,
    QualityStatistics, QualityServiceHealth, QualityThresholdCheck
)

logger = central_logger.get_logger(__name__)

router = APIRouter(prefix="/api/quality", tags=["quality"])

# Initialize services
quality_gate_service = QualityGateService()
monitoring_service = QualityMonitoringService()
fallback_service = FallbackResponseService()


# Remove local definitions - using typed versions from schemas


@router.get("/dashboard")
async def get_quality_dashboard(
    current_user: User = Depends(get_current_user),
    period_hours: int = Query(24, description="Period in hours for data")
) -> QualityDashboardData:
    """
    Get comprehensive quality dashboard data
    
    Returns metrics, alerts, and agent profiles for the dashboard view.
    """
    try:
        dashboard_data = await monitoring_service.get_dashboard_data()
        
        # Convert to typed response
        return QualityDashboardData(
            summary=dashboard_data.get("summary", {}),
            recent_alerts=[QualityAlert(**alert) for alert in dashboard_data.get("recent_alerts", [])],
            agent_profiles=dashboard_data.get("agent_profiles", {}),
            quality_trends=dashboard_data.get("quality_trends", {}),
            top_issues=dashboard_data.get("top_issues", []),
            system_health=dashboard_data.get("system_health", {}),
            period_hours=period_hours,
            user_id=current_user.id,
            generated_at=datetime.now(UTC)
        )
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")


@router.post("/validate")
async def validate_content(
    request: QualityValidationRequest,
    current_user: User = Depends(get_current_user)
) -> QualityValidationResponse:
    """
    Validate content quality on-demand
    
    Useful for testing prompts and validating outputs before deployment.
    """
    try:
        # Map string to ContentType
        content_type_map = {
            "optimization": ContentType.OPTIMIZATION,
            "data_analysis": ContentType.DATA_ANALYSIS,
            "action_plan": ContentType.ACTION_PLAN,
            "report": ContentType.REPORT,
            "triage": ContentType.TRIAGE,
            "error": ContentType.ERROR_MESSAGE,
            "general": ContentType.GENERAL
        }
        content_type = content_type_map.get(request.content_type, ContentType.GENERAL)
        
        # Add user context
        context = request.context or {}
        context["user_id"] = current_user.id
        
        # Validate content
        result = await quality_gate_service.validate_content(
            content=request.content,
            content_type=content_type,
            context=context,
            strict_mode=request.strict_mode
        )
        
        return QualityValidationResponse(
            passed=result.passed,
            metrics={
                "overall_score": result.metrics.overall_score,
                "quality_level": result.metrics.quality_level.value,
                "specificity_score": result.metrics.specificity_score,
                "actionability_score": result.metrics.actionability_score,
                "quantification_score": result.metrics.quantification_score,
                "relevance_score": result.metrics.relevance_score,
                "completeness_score": result.metrics.completeness_score,
                "novelty_score": result.metrics.novelty_score,
                "clarity_score": result.metrics.clarity_score,
                "word_count": result.metrics.word_count,
                "generic_phrase_count": result.metrics.generic_phrase_count,
                "circular_reasoning_detected": result.metrics.circular_reasoning_detected,
                "hallucination_risk": result.metrics.hallucination_risk,
                "redundancy_ratio": result.metrics.redundancy_ratio,
                "issues": result.metrics.issues,
                "suggestions": result.metrics.suggestions
            },
            retry_suggested=result.retry_suggested,
            retry_adjustments=result.retry_prompt_adjustments,
            validation_id=f"val_{int(datetime.now(UTC).timestamp())}",
            timestamp=datetime.now(UTC)
        )
        
    except Exception as e:
        logger.error(f"Error validating content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/agents/{agent_name}/report")
async def get_agent_quality_report(
    agent_name: str,
    current_user: User = Depends(get_current_user),
    period_hours: int = Query(24, description="Period in hours")
) -> Dict[str, Any]:
    """
    Get detailed quality report for a specific agent
    
    Provides comprehensive analysis of an agent's performance and quality metrics.
    """
    try:
        report = await monitoring_service.get_agent_report(agent_name, period_hours)
        
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate agent report")


@router.get("/alerts")
async def get_quality_alerts(
    current_user: User = Depends(get_current_user),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    limit: int = Query(50, description="Maximum alerts to return")
) -> List[QualityAlert]:
    """
    Get quality alerts
    
    Returns active and recent quality alerts with filtering options.
    """
    try:
        all_alerts = list(monitoring_service.alert_history)[-limit:]
        
        # Apply filters
        if severity:
            all_alerts = [a for a in all_alerts if a.severity.value == severity]
        
        if acknowledged is not None:
            all_alerts = [a for a in all_alerts if a.acknowledged == acknowledged]
        
        # Convert to typed format
        return [
            QualityAlert(
                id=alert.id,
                timestamp=alert.timestamp,
                severity=alert.severity,
                metric_type=alert.metric_type,
                agent=alert.agent,
                message=alert.message,
                current_value=alert.current_value,
                threshold=alert.threshold,
                details=alert.details,
                acknowledged=alert.acknowledged,
                resolved=alert.resolved
            )
            for alert in all_alerts
        ]
        
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


@router.post("/alerts/acknowledge")
async def acknowledge_alert(
    request: AlertAcknowledgement,
    current_user: User = Depends(get_current_user)
) -> AlertAcknowledgementResponse:
    """
    Acknowledge or resolve a quality alert
    
    Allows users to acknowledge they've seen an alert or mark it as resolved.
    """
    try:
        if request.action == "acknowledge":
            success = await monitoring_service.acknowledge_alert(request.alert_id)
        elif request.action == "resolve":
            success = await monitoring_service.resolve_alert(request.alert_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertAcknowledgementResponse(
            success=True,
            alert_id=request.alert_id,
            action=request.action,
            user_id=current_user.id,
            timestamp=datetime.now(UTC)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/reports/generate")
async def generate_quality_report(
    report_type: QualityReportType = Query(QualityReportType.SUMMARY),
    period_days: int = Query(7, description="Period in days"),
    current_user: User = Depends(get_current_user)
) -> QualityReport:
    """
    Generate a comprehensive quality report
    
    Creates detailed quality analysis reports for different time periods and scopes.
    """
    try:
        period_hours = period_days * 24
        
        if report_type == QualityReportType.SUMMARY:
            data = await monitoring_service.get_dashboard_data()
            
        elif report_type == QualityReportType.DETAILED:
            # Get data for all agents
            agent_reports = {}
            for agent_name in ["TriageSubAgent", "DataSubAgent", "OptimizationsCoreSubAgent",
                             "ActionsToMeetGoalsSubAgent", "ReportingSubAgent"]:
                agent_reports[agent_name] = await monitoring_service.get_agent_report(
                    agent_name, period_hours
                )
            
            data = {
                "summary": await monitoring_service.get_dashboard_data(),
                "agents": agent_reports,
                "period_days": period_days
            }
            
        elif report_type == QualityReportType.TREND_ANALYSIS:
            # Analyze trends over time
            trends = []
            for i in range(period_days):
                day_start = datetime.now(UTC) - timedelta(days=i+1)
                day_end = datetime.now(UTC) - timedelta(days=i)
                # Would need to implement time-based filtering in monitoring service
                # For now, return current data
                trends.append({
                    "date": day_start.date().isoformat(),
                    "data": await monitoring_service.get_dashboard_data()
                })
            
            data = {
                "trends": trends,
                "period_days": period_days
            }
        
        else:
            data = {"error": "Unknown report type"}
        
        return QualityReport(
            report_type=report_type,
            generated_at=datetime.now(UTC),
            generated_by=current_user.id,
            period_days=period_days,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/statistics")
async def get_quality_statistics(
    current_user: User = Depends(get_current_user),
    content_type: Optional[str] = Query(None, description="Filter by content type")
) -> QualityStatistics:
    """
    Get quality statistics
    
    Returns statistical analysis of quality metrics across different dimensions.
    """
    try:
        # Map string to ContentType if provided
        ct = None
        if content_type:
            content_type_map = {
                "optimization": ContentType.OPTIMIZATION,
                "data_analysis": ContentType.DATA_ANALYSIS,
                "action_plan": ContentType.ACTION_PLAN,
                "report": ContentType.REPORT,
                "triage": ContentType.TRIAGE,
                "error": ContentType.ERROR_MESSAGE,
                "general": ContentType.GENERAL
            }
            ct = content_type_map.get(content_type)
        
        stats = await quality_gate_service.get_quality_stats(ct)
        
        # Convert stats to typed response
        return QualityStatistics(
            total_validations=stats.get("total_validations", 0),
            average_score=stats.get("average_score", 0.0),
            median_score=stats.get("median_score", 0.0),
            score_distribution=stats.get("score_distribution", {}),
            pass_rate=stats.get("pass_rate", 0.0),
            top_issues=stats.get("top_issues", []),
            improvement_areas=stats.get("improvement_areas", []),
            content_type_breakdown=stats.get("content_type_breakdown", {}),
            agent_performance=stats.get("agent_performance", {}),
            timestamp=datetime.now(UTC),
            content_type_filter=content_type
        )
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.post("/monitoring/start")
async def start_quality_monitoring(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    interval_seconds: int = Query(60, description="Monitoring interval in seconds")
) -> Dict[str, Any]:
    """
    Start quality monitoring
    
    Begins continuous quality monitoring with specified interval.
    Admin only endpoint.
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        background_tasks.add_task(
            monitoring_service.start_monitoring,
            interval_seconds=interval_seconds
        )
        
        return {
            "status": "started",
            "interval_seconds": interval_seconds,
            "started_by": current_user.id,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start monitoring")


@router.post("/monitoring/stop")
async def stop_quality_monitoring(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Stop quality monitoring
    
    Stops continuous quality monitoring.
    Admin only endpoint.
    """
    try:
        # Check if user is admin
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        await monitoring_service.stop_monitoring()
        
        return {
            "status": "stopped",
            "stopped_by": current_user.id,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping monitoring: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stop monitoring")


@router.get("/health")
async def quality_service_health() -> QualityServiceHealth:
    """
    Check quality service health
    
    Returns the health status of all quality services.
    """
    try:
        return QualityServiceHealth(
            status="healthy",
            services={
                "quality_gate": "active" if quality_gate_service else "inactive",
                "monitoring": "active" if monitoring_service.monitoring_active else "inactive",
                "fallback": "active" if fallback_service else "inactive"
            },
            statistics={
                "total_validations": len(quality_gate_service.validation_cache) if quality_gate_service else 0,
                "active_alerts": len(monitoring_service.active_alerts) if monitoring_service else 0,
                "monitored_agents": len(monitoring_service.agent_profiles) if monitoring_service else 0
            },
            timestamp=datetime.now(UTC)
        )
        
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}")
        return QualityServiceHealth(
            status="unhealthy",
            services={},
            statistics={},
            timestamp=datetime.now(UTC),
            error=str(e)
        )

async def check_quality_thresholds(metric: str, value: float) -> Dict[str, Any]:
    """Check quality thresholds for testing."""
    threshold = 0.9
    return {
        "metric": metric,
        "value": value,
        "threshold": threshold,
        "alert": value < threshold
    }

async def check_quality_alerts() -> List[Dict[str, Any]]:
    """Check quality alerts for testing."""
    from app.services import quality_service
    alerts = quality_service.check_thresholds()
    return alerts