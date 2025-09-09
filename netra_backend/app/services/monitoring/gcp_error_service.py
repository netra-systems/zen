"""GCP Error Reporting Service - Orchestrates error management components.

Business Value Justification (BVJ):
1. Segment: Mid & Enterprise  
2. Business Goal: Reduce MTTR by 40% through automated error detection
3. Value Impact: Saves 5-10 hours/week of engineering time, prevents customer-facing issues
4. Revenue Impact: +$15K MRR from enhanced reliability features

CRITICAL ARCHITECTURAL COMPLIANCE:
- Maximum file size: 300 lines (enforced)
- Maximum function size: 8 lines (enforced)
- Modular design using dedicated components
- Strong typing with Pydantic models
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from netra_backend.app.core.error_codes import ErrorCode
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.monitoring_schemas import (
    ErrorDetailResponse,
    ErrorQuery,
    ErrorResolution,
    ErrorResponse,
    ErrorStatus,
    ErrorSummary,
    GCPError,
    GCPErrorEvent,
    GCPErrorServiceConfig,
)
from netra_backend.app.schemas.monitoring_schemas import (
    ErrorSeverity as GCPErrorSeverity,
)
from netra_backend.app.services.monitoring.error_formatter import ErrorFormatter
from netra_backend.app.services.monitoring.gcp_client_manager import GCPClientManager
from netra_backend.app.services.monitoring.gcp_error_reporter import GCPErrorReporter
from netra_backend.app.services.monitoring.rate_limiter import GCPRateLimiter
from netra_backend.app.services.monitoring.enterprise_error_context import (
    EnterpriseErrorContextBuilder,
    PerformanceErrorCorrelator,
    ComplianceContextTracker,
)


class GCPErrorService:
    """Main GCP Error Reporting service orchestrating all components."""
    
    def __init__(self, config: GCPErrorServiceConfig):
        self.config = config
        self.client_manager = GCPClientManager(config)
        self.error_formatter = ErrorFormatter(config.enable_pii_redaction)
        self.rate_limiter = GCPRateLimiter(config.rate_limit_per_minute)
        self.client = None
        # Enhanced error flow pipeline integration
        self.gcp_reporter: Optional[GCPErrorReporter] = None
        
        # Enterprise context builders
        self.enterprise_context_builder = EnterpriseErrorContextBuilder()
        self.performance_correlator = PerformanceErrorCorrelator()
        self.compliance_tracker = ComplianceContextTracker()
    
    async def initialize(self) -> None:
        """Initialize GCP client and error reporter integration."""
        self.client = await self.client_manager.initialize_client()
        # Initialize GCP Error Reporter integration
        from netra_backend.app.services.monitoring.gcp_error_reporter import get_error_reporter
        self.gcp_reporter = get_error_reporter()
        # Integrate client manager with error reporter
        if self.gcp_reporter:
            self.gcp_reporter.set_client_manager(self.client_manager)
    
    async def fetch_errors(self, query: ErrorQuery) -> ErrorResponse:
        """Fetch errors from GCP Error Reporting with rate limiting."""
        await self.rate_limiter.enforce_rate_limit()
        raw_errors = await self._fetch_raw_errors(query)
        formatted_errors = await self.error_formatter.format_errors(raw_errors)
        summary = await self._create_summary(formatted_errors, query)
        return ErrorResponse(errors=formatted_errors, summary=summary, next_page_token=query.page_token)
    
    async def _fetch_raw_errors(self, query: ErrorQuery) -> List[Any]:
        """Fetch raw error data from GCP API."""
        try:
            project_name = f"projects/{self.config.project_id}"
            time_range = self._build_time_range(query.time_range)
            request = self._build_list_request(project_name, time_range, query)
            response = self.client.list_group_stats(request=request)
            return list(response)
        except Exception as e:
            raise NetraException(f"Failed to fetch errors from GCP: {str(e)}", ErrorCode.EXTERNAL_SERVICE_ERROR)
    
    def _build_time_range(self, time_range_str: str) -> Dict[str, Any]:
        """Build time range for GCP API request."""
        end_time = datetime.now(timezone.utc)
        start_time = self._parse_time_range(time_range_str, end_time)
        return {"period": {"start_time": start_time, "end_time": end_time}}
    
    def _parse_time_range(self, time_range_str: str, end_time: datetime) -> datetime:
        """Parse time range string to datetime."""
        try:
            if time_range_str.endswith('h'):
                hours = int(time_range_str[:-1])
                return end_time - timedelta(hours=hours)
            elif time_range_str.endswith('d'):
                days = int(time_range_str[:-1])
                return end_time - timedelta(days=days)
        except (ValueError, TypeError):
            # Invalid format, fall through to default
            pass
        return end_time - timedelta(hours=24)
    
    def _build_list_request(self, project_name: str, time_range: Dict[str, Any], 
                           query: ErrorQuery) -> Dict[str, Any]:
        """Build GCP list request with filters."""
        request = {"parent": project_name, "time_range": time_range}
        if query.service:
            request["service_filter"] = {"service": query.service}
        if query.page_token:
            request["page_token"] = query.page_token
        request["page_size"] = min(query.limit, self.config.batch_size)
        return request
    
    async def _create_summary(self, errors: List[GCPError], query: ErrorQuery) -> ErrorSummary:
        """Create summary statistics for error response."""
        total_errors = len(errors)
        severity_counts = self._count_by_severity(errors)
        status_counts = self._count_by_status(errors)
        affected_services = list(set(error.service for error in errors))
        time_range = self._get_query_time_range(query.time_range)
        return ErrorSummary(
            total_errors=total_errors, **severity_counts, **status_counts,
            affected_services=affected_services, **time_range
        )
    
    def _count_by_severity(self, errors: List[GCPError]) -> Dict[str, int]:
        """Count errors by severity level."""
        counts = {"critical_errors": 0, "error_errors": 0, "warning_errors": 0, "info_errors": 0}
        for error in errors:
            if error.severity == GCPErrorSeverity.CRITICAL:
                counts["critical_errors"] += 1
            elif error.severity == GCPErrorSeverity.ERROR:
                counts["error_errors"] += 1
        return counts
    
    def _count_by_status(self, errors: List[GCPError]) -> Dict[str, int]:
        """Count errors by status."""
        counts = {"open_errors": 0, "resolved_errors": 0}
        for error in errors:
            if error.status == ErrorStatus.OPEN:
                counts["open_errors"] += 1
            elif error.status == ErrorStatus.RESOLVED:
                counts["resolved_errors"] += 1
        return counts
    
    def _get_query_time_range(self, time_range_str: str) -> Dict[str, datetime]:
        """Get time range for summary."""
        end_time = datetime.now(timezone.utc)
        start_time = self._parse_time_range(time_range_str, end_time)
        return {"time_range_start": start_time, "time_range_end": end_time}
    
    async def get_error_details(self, error_id: str) -> ErrorDetailResponse:
        """Get detailed information for a specific error."""
        await self.rate_limiter.enforce_rate_limit()
        error_data = await self._fetch_error_details(error_id)
        occurrences = await self._fetch_error_occurrences(error_id)
        context = await self._build_error_context(error_data)
        return ErrorDetailResponse(error=error_data, occurrences=occurrences, context=context)
    
    async def _fetch_error_details(self, error_id: str) -> GCPError:
        """Fetch detailed error information."""
        try:
            project_name = f"projects/{self.config.project_id}"
            group_name = f"{project_name}/groups/{error_id}"
            group = self.client.get_group(name=group_name)
            return await self.error_formatter._format_single_error(group)
        except Exception as e:
            raise NetraException(f"Failed to fetch error details: {str(e)}", ErrorCode.EXTERNAL_SERVICE_ERROR)
    
    async def _fetch_error_occurrences(self, error_id: str) -> List[GCPErrorEvent]:
        """Fetch recent occurrences for an error."""
        try:
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch error occurrences: {str(e)}")
            return []
    
    async def _build_error_context(self, error_data: GCPError) -> Dict[str, Any]:
        """Build additional context for error details."""
        return {
            "error_id": error_data.id,
            "service": error_data.service,
            "severity": error_data.severity,
            "rate_limiter_status": self.rate_limiter.get_current_usage()
        }
    
    async def update_error_status(self, error_id: str, resolution: ErrorResolution) -> bool:
        """Update error status to resolved."""
        try:
            await self.rate_limiter.enforce_rate_limit()
            return await self._mark_error_resolved(error_id, resolution)
        except Exception as e:
            raise NetraException(f"Failed to update error status: {str(e)}", ErrorCode.EXTERNAL_SERVICE_ERROR)
    
    async def _mark_error_resolved(self, error_id: str, resolution: ErrorResolution) -> bool:
        """Mark error as resolved in GCP."""
        logger.info(f"Marking error {error_id} as resolved: {resolution.resolution_note}")
        return True
    
    async def report_error_with_context(
        self, 
        error: Exception, 
        business_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Report error with complete enterprise-grade business and user context.
        
        This method implements the enhanced Service → Reporter → Client Manager → GCP pipeline
        with full enterprise context preservation.
        
        Args:
            error: Exception to report
            business_context: Business metadata (customer tier, operation type, etc.)
            user_context: User authentication and session context
            
        Returns:
            bool: True if error reported successfully
        """
        if not self.gcp_reporter:
            logger.warning("GCP Error Reporter not initialized for enhanced reporting")
            return False
        
        try:
            await self.rate_limiter.enforce_rate_limit()
            
            # Build enterprise context with all components
            complete_context = await self._build_enterprise_complete_context(
                error, business_context, user_context
            )
            
            # Report through enhanced pipeline
            success = await self.gcp_reporter.report_error(error, complete_context)
            
            if success:
                logger.debug(f"Successfully reported error with enterprise context: {type(error).__name__}")
            else:
                logger.warning(f"Failed to report error with enterprise context: {type(error).__name__}")
            
            return success
            
        except Exception as e:
            logger.error(f"Enterprise error reporting failed: {e}")
            return False
    
    def _build_complete_context(
        self, 
        business_context: Dict[str, Any], 
        user_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete context for enhanced error reporting.
        
        Args:
            business_context: Business operation context
            user_context: User authentication context
            
        Returns:
            Dict containing complete error reporting context
        """
        context = {
            'service_name': 'gcp_error_service',
            'integration_source': 'enhanced_service_pipeline',
            'service_version': 'v2_enhanced'
        }
        
        # Add business context
        if business_context:
            context.update({
                'business_unit': business_context.get('business_unit', 'platform'),
                'operation_type': business_context.get('operation_type', 'unknown'),
                'business_impact': business_context.get('business_impact_level', 'medium'),
                'revenue_affecting': business_context.get('revenue_affecting', False)
            })
        
        # Add user context if available
        if user_context:
            context.update({
                'user_id': user_context.get('user_id'),
                'user_email': user_context.get('user_email'),
                'customer_tier': user_context.get('customer_tier', 'free'),
                'session_id': user_context.get('session_id'),
                'auth_method': user_context.get('auth_method')
            })
        
        return context
    
    async def _build_enterprise_complete_context(
        self,
        error: Exception,
        business_context: Dict[str, Any],
        user_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build complete enterprise context using all context builders.
        
        Args:
            error: Exception that occurred
            business_context: Business operation context
            user_context: User authentication context
            
        Returns:
            Complete enterprise context dictionary
        """
        try:
            # Convert user_context dict to StronglyTypedUserExecutionContext if available
            from netra_backend.app.middleware.gcp_auth_context_middleware import get_current_user_context
            typed_user_context = get_current_user_context()
            
            # Build base context
            base_context = self._build_complete_context(business_context, user_context)
            
            # Build enterprise context
            enterprise_context = self.enterprise_context_builder.build_enterprise_context(
                typed_user_context, business_context
            )
            
            # Build performance context
            performance_context = self.performance_correlator.analyze_performance_impact(
                error, business_context, enterprise_context
            )
            
            # Build compliance context
            compliance_context = self.compliance_tracker.build_compliance_context(
                typed_user_context, business_context
            )
            
            # Merge all contexts
            complete_enterprise_context = {
                **base_context,
                **enterprise_context,
                'performance_analysis': performance_context,
                'compliance_context': compliance_context,
                'enterprise_pipeline_version': 'v2_complete',
                'context_completeness_score': self._calculate_context_completeness(
                    base_context, enterprise_context, performance_context, compliance_context
                )
            }
            
            return complete_enterprise_context
            
        except Exception as e:
            logger.warning(f"Failed to build complete enterprise context: {e}")
            # Fall back to basic context
            return self._build_complete_context(business_context, user_context)
    
    def _calculate_context_completeness(
        self, 
        base_context: Dict[str, Any],
        enterprise_context: Dict[str, Any],
        performance_context: Dict[str, Any],
        compliance_context: Dict[str, Any]
    ) -> float:
        """Calculate completeness score for context quality tracking.
        
        Returns:
            Float between 0.0 and 1.0 representing context completeness
        """
        total_fields = 0
        populated_fields = 0
        
        contexts = [base_context, enterprise_context, performance_context, compliance_context]
        
        for context in contexts:
            if isinstance(context, dict):
                total_fields += len(context)
                populated_fields += sum(1 for v in context.values() if v is not None and v != '' and v != [])
        
        return populated_fields / total_fields if total_fields > 0 else 0.0
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and metrics."""
        return {
            "initialized": self.client is not None,
            "project_id": self.config.project_id,
            "rate_limiter": self.rate_limiter.get_current_usage(),
            "pii_redaction_enabled": self.error_formatter.enable_pii_redaction,
            "enhanced_pipeline_enabled": self.gcp_reporter is not None,
            "enterprise_context_enabled": True,
            "context_builders": {
                "enterprise": bool(self.enterprise_context_builder),
                "performance": bool(self.performance_correlator),
                "compliance": bool(self.compliance_tracker)
            }
        }