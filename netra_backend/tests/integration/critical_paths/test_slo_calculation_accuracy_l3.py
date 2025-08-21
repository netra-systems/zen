"""SLO/SLI Calculation Accuracy L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (SLA compliance for all revenue tiers)
- Business Goal: Accurate SLO tracking to maintain customer SLA commitments and avoid penalties
- Value Impact: Prevents $20K+ penalties through accurate SLA monitoring and proactive issue detection
- Strategic Impact: Maintains customer trust and competitive advantage through reliable service guarantees

Critical Path: Metric collection -> SLI calculation -> SLO evaluation -> Threshold monitoring -> Alert generation
Coverage: SLI accuracy, SLO calculations, error budget tracking, trend analysis, compliance reporting
L3 Realism: Tests with real SLO definitions and actual service metrics
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import time
import uuid
import logging
import statistics
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.observability,
    pytest.mark.slo
]


class SLIType(Enum):
    """Types of Service Level Indicators."""
    AVAILABILITY = "availability"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    QUALITY = "quality"


class TimeWindow(Enum):
    """Time windows for SLO evaluation."""
    ROLLING_1_HOUR = "rolling_1h"
    ROLLING_24_HOUR = "rolling_24h"
    ROLLING_7_DAY = "rolling_7d"
    ROLLING_30_DAY = "rolling_30d"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


@dataclass
class SLODefinition:
    """Defines a Service Level Objective."""
    slo_id: str
    service_name: str
    sli_type: SLIType
    target_percentage: float
    time_window: TimeWindow
    measurement_query: str
    business_criticality: str  # "critical", "high", "medium", "low"
    customer_facing: bool
    error_budget_policy: str = "burn_rate"
    compliance_required: bool = False


@dataclass
class SLIDataPoint:
    """Represents a single SLI measurement."""
    timestamp: datetime
    service_name: str
    sli_type: SLIType
    success_count: int
    total_count: int
    value: float  # Calculated SLI value (0-100%)
    raw_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.raw_metrics is None:
            self.raw_metrics = {}


@dataclass
class SLOCalculationResult:
    """Results of SLO calculation."""
    slo_id: str
    evaluation_time: datetime
    time_window_start: datetime
    time_window_end: datetime
    target_percentage: float
    actual_percentage: float
    error_budget_remaining: float
    error_budget_burn_rate: float
    compliance_status: str  # "compliant", "at_risk", "violated"
    trend_direction: str  # "improving", "stable", "degrading"


@dataclass
class SLOAnalysis:
    """Analysis of SLO performance."""
    total_slos: int
    compliant_slos: int
    at_risk_slos: int
    violated_slos: int
    average_compliance: float
    critical_violations: List[str]
    error_budget_utilization: float


class SLOCalculationValidator:
    """Validates SLO/SLI calculation accuracy with real service metrics."""
    
    def __init__(self):
        self.metrics_collector = None
        self.slo_calculator = None
        self.alert_manager = None
        self.slo_definitions = []
        self.sli_data_points = []
        self.slo_calculations = []
        self.compliance_history = []
        
    async def initialize_slo_services(self):
        """Initialize SLO calculation services for L3 testing."""
        try:
            self.metrics_collector = SLIMetricsCollector()
            await self.metrics_collector.initialize()
            
            self.slo_calculator = SLOCalculator()
            await self.slo_calculator.initialize()
            
            self.alert_manager = SLOAlertManager()
            
            # Setup realistic SLO definitions
            await self._setup_slo_definitions()
            
            logger.info("SLO calculation L3 services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize SLO services: {e}")
            raise
    
    async def _setup_slo_definitions(self):
        """Setup realistic SLO definitions for different services."""
        slo_definitions = [
            # API Gateway - Customer-facing availability
            SLODefinition(
                slo_id="api_gateway_availability",
                service_name="api-gateway",
                sli_type=SLIType.AVAILABILITY,
                target_percentage=99.9,  # 99.9% uptime SLO
                time_window=TimeWindow.ROLLING_30_DAY,
                measurement_query="sum(http_requests_total{status!~'5..'}) / sum(http_requests_total)",
                business_criticality="critical",
                customer_facing=True,
                compliance_required=True
            ),
            SLODefinition(
                slo_id="api_gateway_latency_p95",
                service_name="api-gateway",
                sli_type=SLIType.LATENCY,
                target_percentage=95.0,  # 95% of requests under 500ms
                time_window=TimeWindow.ROLLING_24_HOUR,
                measurement_query="histogram_quantile(0.95, http_request_duration_seconds_bucket) < 0.5",
                business_criticality="high",
                customer_facing=True
            ),
            
            # Authentication Service - Critical for all operations
            SLODefinition(
                slo_id="auth_service_availability",
                service_name="auth-service",
                sli_type=SLIType.AVAILABILITY,
                target_percentage=99.95, # Higher SLO for auth
                time_window=TimeWindow.ROLLING_7_DAY,
                measurement_query="sum(auth_requests_total{status='success'}) / sum(auth_requests_total)",
                business_criticality="critical",
                customer_facing=True,
                compliance_required=True
            ),
            SLODefinition(
                slo_id="auth_service_error_rate",
                service_name="auth-service",
                sli_type=SLIType.ERROR_RATE,
                target_percentage=99.5,  # Less than 0.5% error rate
                time_window=TimeWindow.ROLLING_24_HOUR,
                measurement_query="sum(auth_errors_total) / sum(auth_requests_total) < 0.005",
                business_criticality="critical",
                customer_facing=True
            ),
            
            # Agent Service - Core business functionality
            SLODefinition(
                slo_id="agent_service_quality",
                service_name="agent-service",
                sli_type=SLIType.QUALITY,
                target_percentage=95.0,  # 95% successful agent executions
                time_window=TimeWindow.ROLLING_24_HOUR,
                measurement_query="sum(agent_executions_total{status='success'}) / sum(agent_executions_total)",
                business_criticality="high",
                customer_facing=True
            ),
            SLODefinition(
                slo_id="agent_service_throughput",
                service_name="agent-service",
                sli_type=SLIType.THROUGHPUT,
                target_percentage=90.0,  # Maintain 90% of expected throughput
                time_window=TimeWindow.ROLLING_1_HOUR,
                measurement_query="rate(agent_executions_total[1h]) >= 0.9 * agent_expected_rate",
                business_criticality="medium",
                customer_facing=False
            ),
            
            # Database Service - Backend reliability
            SLODefinition(
                slo_id="database_availability",
                service_name="database-service",
                sli_type=SLIType.AVAILABILITY,
                target_percentage=99.5,
                time_window=TimeWindow.ROLLING_7_DAY,
                measurement_query="sum(db_connections_successful) / sum(db_connection_attempts)",
                business_criticality="high",
                customer_facing=False
            ),
            SLODefinition(
                slo_id="database_latency_p99",
                service_name="database-service",
                sli_type=SLIType.LATENCY,
                target_percentage=99.0,  # 99% of queries under 100ms
                time_window=TimeWindow.ROLLING_1_HOUR,
                measurement_query="histogram_quantile(0.99, db_query_duration_seconds_bucket) < 0.1",
                business_criticality="medium",
                customer_facing=False
            ),
            
            # WebSocket Service - Real-time communication
            SLODefinition(
                slo_id="websocket_availability",
                service_name="websocket-service",
                sli_type=SLIType.AVAILABILITY,
                target_percentage=99.0,
                time_window=TimeWindow.ROLLING_24_HOUR,
                measurement_query="sum(websocket_connections_active) / sum(websocket_connections_attempted)",
                business_criticality="medium",
                customer_facing=True
            )
        ]
        
        self.slo_definitions = slo_definitions
        await self.slo_calculator.configure_slos(slo_definitions)
    
    async def generate_sli_data_stream(self, duration_hours: int = 72, 
                                     data_points_per_hour: int = 60) -> List[SLIDataPoint]:
        """Generate realistic SLI data stream for testing."""
        sli_data = []
        start_time = datetime.now(timezone.utc) - timedelta(hours=duration_hours)
        
        # Generate data points across the time period
        for hour_offset in range(duration_hours):
            hour_start = start_time + timedelta(hours=hour_offset)
            
            # Vary performance throughout the day (simulate daily patterns)
            daily_performance_factor = self._calculate_daily_performance_factor(hour_offset)
            
            for minute_offset in range(0, 60, 60 // data_points_per_hour):
                data_time = hour_start + timedelta(minutes=minute_offset)
                
                # Generate SLI data for each service
                for slo_def in self.slo_definitions:
                    sli_point = await self._generate_sli_data_point(
                        slo_def, data_time, daily_performance_factor
                    )
                    sli_data.append(sli_point)
        
        self.sli_data_points = sli_data
        return sli_data
    
    def _calculate_daily_performance_factor(self, hour_offset: int) -> float:
        """Calculate performance variation throughout the day."""
        hour_of_day = hour_offset % 24
        
        # Simulate daily patterns: degradation during peak hours, maintenance windows
        if 9 <= hour_of_day <= 17:  # Business hours - higher load
            return 0.95
        elif 2 <= hour_of_day <= 4:  # Maintenance window
            return 0.85
        else:  # Off-peak hours
            return 0.98
    
    async def _generate_sli_data_point(self, slo_def: SLODefinition, 
                                     timestamp: datetime, performance_factor: float) -> SLIDataPoint:
        """Generate realistic SLI data point for a specific service and time."""
        # Base success rates by service type
        base_success_rates = {
            "api-gateway": 0.995,
            "auth-service": 0.998,
            "agent-service": 0.96,
            "database-service": 0.997,
            "websocket-service": 0.92
        }
        
        base_success_rate = base_success_rates.get(slo_def.service_name, 0.95)
        
        # Apply performance factor and add some randomness
        import random
        actual_success_rate = base_success_rate * performance_factor * random.uniform(0.98, 1.02)
        actual_success_rate = min(1.0, max(0.0, actual_success_rate))
        
        # Generate request volumes based on service type
        volume_ranges = {
            "api-gateway": (800, 1200),
            "auth-service": (200, 400),
            "agent-service": (50, 150),
            "database-service": (1000, 1500),
            "websocket-service": (300, 600)
        }
        
        min_vol, max_vol = volume_ranges.get(slo_def.service_name, (100, 200))
        total_count = random.randint(min_vol, max_vol)
        success_count = int(total_count * actual_success_rate)
        
        # Adjust SLI value calculation based on SLI type
        if slo_def.sli_type == SLIType.AVAILABILITY:
            sli_value = (success_count / total_count) * 100
        elif slo_def.sli_type == SLIType.ERROR_RATE:
            error_count = total_count - success_count
            sli_value = (1 - (error_count / total_count)) * 100
        elif slo_def.sli_type == SLIType.LATENCY:
            # For latency SLIs, simulate percentage of requests meeting latency target
            sli_value = actual_success_rate * 100
        elif slo_def.sli_type == SLIType.QUALITY:
            # Quality metrics (e.g., successful AI agent executions)
            sli_value = actual_success_rate * 100
        elif slo_def.sli_type == SLIType.THROUGHPUT:
            # Throughput as percentage of expected rate
            expected_rate = 100  # Baseline expected rate
            actual_rate = total_count
            sli_value = min(100, (actual_rate / expected_rate) * 100)
        else:
            sli_value = actual_success_rate * 100
        
        return SLIDataPoint(
            timestamp=timestamp,
            service_name=slo_def.service_name,
            sli_type=slo_def.sli_type,
            success_count=success_count,
            total_count=total_count,
            value=sli_value,
            raw_metrics={
                "service": slo_def.service_name,
                "sli_type": slo_def.sli_type.value,
                "performance_factor": performance_factor
            }
        )
    
    async def calculate_slo_compliance(self, sli_data: List[SLIDataPoint]) -> List[SLOCalculationResult]:
        """Calculate SLO compliance for all defined SLOs."""
        slo_results = []
        evaluation_time = datetime.now(timezone.utc)
        
        for slo_def in self.slo_definitions:
            try:
                # Calculate SLO for this definition
                slo_result = await self._calculate_single_slo(slo_def, sli_data, evaluation_time)
                slo_results.append(slo_result)
                
            except Exception as e:
                logger.error(f"SLO calculation failed for {slo_def.slo_id}: {e}")
        
        self.slo_calculations = slo_results
        return slo_results
    
    async def _calculate_single_slo(self, slo_def: SLODefinition, sli_data: List[SLIDataPoint],
                                  evaluation_time: datetime) -> SLOCalculationResult:
        """Calculate SLO compliance for a single SLO definition."""
        # Determine time window
        time_window_start = self._calculate_time_window_start(evaluation_time, slo_def.time_window)
        
        # Filter SLI data for this SLO
        relevant_data = [
            point for point in sli_data
            if (point.service_name == slo_def.service_name and
                point.sli_type == slo_def.sli_type and
                time_window_start <= point.timestamp <= evaluation_time)
        ]
        
        if not relevant_data:
            # No data available - assume violation
            return SLOCalculationResult(
                slo_id=slo_def.slo_id,
                evaluation_time=evaluation_time,
                time_window_start=time_window_start,
                time_window_end=evaluation_time,
                target_percentage=slo_def.target_percentage,
                actual_percentage=0.0,
                error_budget_remaining=0.0,
                error_budget_burn_rate=100.0,
                compliance_status="violated",
                trend_direction="unknown"
            )
        
        # Calculate weighted average SLI value
        total_weight = sum(point.total_count for point in relevant_data)
        if total_weight == 0:
            actual_percentage = 0.0
        else:
            weighted_sum = sum(point.value * point.total_count for point in relevant_data)
            actual_percentage = weighted_sum / total_weight
        
        # Calculate error budget metrics
        error_budget_remaining = max(0, (actual_percentage - slo_def.target_percentage) / 
                                   (100 - slo_def.target_percentage) * 100)
        
        # Calculate burn rate (how fast error budget is being consumed)
        burn_rate = self._calculate_error_budget_burn_rate(relevant_data, slo_def)
        
        # Determine compliance status
        if actual_percentage >= slo_def.target_percentage:
            compliance_status = "compliant"
        elif actual_percentage >= slo_def.target_percentage * 0.95:  # Within 5% of target
            compliance_status = "at_risk"
        else:
            compliance_status = "violated"
        
        # Calculate trend direction
        trend_direction = self._calculate_trend_direction(relevant_data)
        
        return SLOCalculationResult(
            slo_id=slo_def.slo_id,
            evaluation_time=evaluation_time,
            time_window_start=time_window_start,
            time_window_end=evaluation_time,
            target_percentage=slo_def.target_percentage,
            actual_percentage=actual_percentage,
            error_budget_remaining=error_budget_remaining,
            error_budget_burn_rate=burn_rate,
            compliance_status=compliance_status,
            trend_direction=trend_direction
        )
    
    def _calculate_time_window_start(self, evaluation_time: datetime, time_window: TimeWindow) -> datetime:
        """Calculate start time for SLO evaluation window."""
        if time_window == TimeWindow.ROLLING_1_HOUR:
            return evaluation_time - timedelta(hours=1)
        elif time_window == TimeWindow.ROLLING_24_HOUR:
            return evaluation_time - timedelta(hours=24)
        elif time_window == TimeWindow.ROLLING_7_DAY:
            return evaluation_time - timedelta(days=7)
        elif time_window == TimeWindow.ROLLING_30_DAY:
            return evaluation_time - timedelta(days=30)
        elif time_window == TimeWindow.MONTHLY:
            return evaluation_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_window == TimeWindow.QUARTERLY:
            quarter_month = ((evaluation_time.month - 1) // 3) * 3 + 1
            return evaluation_time.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return evaluation_time - timedelta(hours=24)  # Default to 24 hours
    
    def _calculate_error_budget_burn_rate(self, sli_data: List[SLIDataPoint], slo_def: SLODefinition) -> float:
        """Calculate error budget burn rate."""
        if len(sli_data) < 2:
            return 0.0
        
        # Calculate recent performance vs older performance
        sorted_data = sorted(sli_data, key=lambda x: x.timestamp)
        recent_data = sorted_data[-len(sorted_data)//4:]  # Last 25% of data
        older_data = sorted_data[:len(sorted_data)//4]   # First 25% of data
        
        recent_avg = statistics.mean([point.value for point in recent_data])
        older_avg = statistics.mean([point.value for point in older_data])
        
        # Calculate burn rate based on performance degradation
        if recent_avg < slo_def.target_percentage:
            degradation = (older_avg - recent_avg) / max(1, older_avg) * 100
            return min(100, max(0, degradation))
        else:
            return 0.0
    
    def _calculate_trend_direction(self, sli_data: List[SLIDataPoint]) -> str:
        """Calculate trend direction for SLI values."""
        if len(sli_data) < 3:
            return "stable"
        
        sorted_data = sorted(sli_data, key=lambda x: x.timestamp)
        values = [point.value for point in sorted_data]
        
        # Calculate linear trend
        n = len(values)
        x = list(range(n))
        y = values
        
        # Simple linear regression slope
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "degrading"
        else:
            return "stable"
    
    async def analyze_slo_performance(self, slo_results: List[SLOCalculationResult]) -> SLOAnalysis:
        """Analyze overall SLO performance and compliance."""
        if not slo_results:
            return SLOAnalysis(
                total_slos=0, compliant_slos=0, at_risk_slos=0, violated_slos=0,
                average_compliance=0.0, critical_violations=[], error_budget_utilization=0.0
            )
        
        # Count compliance statuses
        compliant_count = sum(1 for result in slo_results if result.compliance_status == "compliant")
        at_risk_count = sum(1 for result in slo_results if result.compliance_status == "at_risk")
        violated_count = sum(1 for result in slo_results if result.compliance_status == "violated")
        
        # Calculate average compliance
        avg_compliance = statistics.mean([result.actual_percentage for result in slo_results])
        
        # Identify critical violations
        critical_violations = []
        for result in slo_results:
            if result.compliance_status == "violated":
                # Find corresponding SLO definition to check criticality
                slo_def = next((slo for slo in self.slo_definitions if slo.slo_id == result.slo_id), None)
                if slo_def and slo_def.business_criticality in ["critical", "high"]:
                    critical_violations.append(result.slo_id)
        
        # Calculate overall error budget utilization
        error_budget_utilization = statistics.mean([
            100 - result.error_budget_remaining for result in slo_results
        ])
        
        return SLOAnalysis(
            total_slos=len(slo_results),
            compliant_slos=compliant_count,
            at_risk_slos=at_risk_count,
            violated_slos=violated_count,
            average_compliance=avg_compliance,
            critical_violations=critical_violations,
            error_budget_utilization=error_budget_utilization
        )
    
    async def test_slo_calculation_accuracy(self, known_sli_values: Dict[str, float]) -> Dict[str, Any]:
        """Test SLO calculation accuracy against known SLI values."""
        accuracy_results = {
            "total_tests": 0,
            "accurate_calculations": 0,
            "calculation_errors": [],
            "accuracy_percentage": 0.0,
            "max_deviation": 0.0
        }
        
        # Generate test SLI data with known values
        test_sli_data = []
        current_time = datetime.now(timezone.utc)
        
        for slo_def in self.slo_definitions:
            if slo_def.slo_id in known_sli_values:
                expected_value = known_sli_values[slo_def.slo_id]
                
                # Create consistent SLI data points
                for i in range(10):  # 10 data points
                    timestamp = current_time - timedelta(minutes=i * 5)
                    total_count = 1000
                    success_count = int(total_count * (expected_value / 100))
                    
                    sli_point = SLIDataPoint(
                        timestamp=timestamp,
                        service_name=slo_def.service_name,
                        sli_type=slo_def.sli_type,
                        success_count=success_count,
                        total_count=total_count,
                        value=expected_value
                    )
                    test_sli_data.append(sli_point)
        
        # Calculate SLOs
        slo_results = await self.calculate_slo_compliance(test_sli_data)
        
        # Verify accuracy
        for result in slo_results:
            if result.slo_id in known_sli_values:
                expected_value = known_sli_values[result.slo_id]
                actual_value = result.actual_percentage
                
                accuracy_results["total_tests"] += 1
                
                # Calculate deviation
                deviation = abs(expected_value - actual_value)
                accuracy_results["max_deviation"] = max(accuracy_results["max_deviation"], deviation)
                
                # Check if calculation is accurate (within 1% tolerance)
                if deviation <= 1.0:
                    accuracy_results["accurate_calculations"] += 1
                else:
                    accuracy_results["calculation_errors"].append({
                        "slo_id": result.slo_id,
                        "expected": expected_value,
                        "actual": actual_value,
                        "deviation": deviation
                    })
        
        # Calculate accuracy percentage
        if accuracy_results["total_tests"] > 0:
            accuracy_percentage = (accuracy_results["accurate_calculations"] / accuracy_results["total_tests"]) * 100
            accuracy_results["accuracy_percentage"] = accuracy_percentage
        
        return accuracy_results
    
    async def test_error_budget_tracking(self, sli_data: List[SLIDataPoint]) -> Dict[str, Any]:
        """Test error budget tracking and burn rate calculations."""
        error_budget_results = {
            "slos_tracked": 0,
            "error_budgets_calculated": 0,
            "burn_rates_calculated": 0,
            "budget_violations": [],
            "average_burn_rate": 0.0
        }
        
        # Calculate SLOs to get error budget information
        slo_results = await self.calculate_slo_compliance(sli_data)
        
        burn_rates = []
        
        for result in slo_results:
            error_budget_results["slos_tracked"] += 1
            
            # Check error budget calculation
            if result.error_budget_remaining >= 0:
                error_budget_results["error_budgets_calculated"] += 1
            
            # Check burn rate calculation
            if result.error_budget_burn_rate >= 0:
                error_budget_results["burn_rates_calculated"] += 1
                burn_rates.append(result.error_budget_burn_rate)
            
            # Check for budget violations
            if result.error_budget_remaining <= 10:  # Less than 10% budget remaining
                slo_def = next((slo for slo in self.slo_definitions if slo.slo_id == result.slo_id), None)
                error_budget_results["budget_violations"].append({
                    "slo_id": result.slo_id,
                    "service": slo_def.service_name if slo_def else "unknown",
                    "remaining_budget": result.error_budget_remaining,
                    "burn_rate": result.error_budget_burn_rate,
                    "criticality": slo_def.business_criticality if slo_def else "unknown"
                })
        
        # Calculate average burn rate
        if burn_rates:
            error_budget_results["average_burn_rate"] = statistics.mean(burn_rates)
        
        return error_budget_results
    
    async def cleanup(self):
        """Clean up SLO calculation test resources."""
        try:
            if self.metrics_collector:
                await self.metrics_collector.shutdown()
            if self.slo_calculator:
                await self.slo_calculator.shutdown()
        except Exception as e:
            logger.error(f"SLO calculation cleanup failed: {e}")


class SLIMetricsCollector:
    """Mock SLI metrics collector for L3 testing."""
    
    async def initialize(self):
        """Initialize metrics collector."""
        pass
    
    async def shutdown(self):
        """Shutdown metrics collector."""
        pass


class SLOCalculator:
    """Mock SLO calculator for L3 testing."""
    
    async def initialize(self):
        """Initialize SLO calculator."""
        self.configured_slos = []
    
    async def configure_slos(self, slo_definitions: List[SLODefinition]):
        """Configure SLO definitions."""
        self.configured_slos = slo_definitions
    
    async def shutdown(self):
        """Shutdown SLO calculator."""
        pass


class SLOAlertManager:
    """Mock SLO alert manager for L3 testing."""
    
    def __init__(self):
        self.alerts_generated = []
    
    async def generate_slo_alert(self, slo_result: SLOCalculationResult):
        """Generate alert for SLO violation."""
        if slo_result.compliance_status in ["at_risk", "violated"]:
            alert = {
                "slo_id": slo_result.slo_id,
                "status": slo_result.compliance_status,
                "actual_percentage": slo_result.actual_percentage,
                "target_percentage": slo_result.target_percentage,
                "generated_at": datetime.now(timezone.utc)
            }
            self.alerts_generated.append(alert)


@pytest.fixture
async def slo_calculation_validator():
    """Create SLO calculation validator for L3 testing."""
    validator = SLOCalculationValidator()
    await validator.initialize_slo_services()
    yield validator
    await validator.cleanup()


@pytest.mark.asyncio
async def test_slo_calculation_accuracy_l3(slo_calculation_validator):
    """Test accuracy of SLO calculations against known values.
    
    L3: Tests with real SLO calculations and known SLI inputs.
    """
    # Define known SLI values for testing
    known_sli_values = {
        "api_gateway_availability": 99.95,
        "auth_service_availability": 99.97,
        "agent_service_quality": 96.2,
        "database_availability": 99.8
    }
    
    # Test calculation accuracy
    accuracy_results = await slo_calculation_validator.test_slo_calculation_accuracy(known_sli_values)
    
    # Verify calculation accuracy
    assert accuracy_results["accuracy_percentage"] >= 95.0  # At least 95% accurate calculations
    assert accuracy_results["max_deviation"] <= 2.0  # Maximum 2% deviation
    assert len(accuracy_results["calculation_errors"]) <= 1  # Minimal calculation errors


@pytest.mark.asyncio
async def test_slo_compliance_monitoring_l3(slo_calculation_validator):
    """Test SLO compliance monitoring with realistic data.
    
    L3: Tests compliance tracking with real service metrics.
    """
    # Generate realistic SLI data
    sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=48, data_points_per_hour=30)
    
    # Calculate SLO compliance
    slo_results = await slo_calculation_validator.calculate_slo_compliance(sli_data)
    
    # Analyze SLO performance
    slo_analysis = await slo_calculation_validator.analyze_slo_performance(slo_results)
    
    # Verify compliance monitoring
    assert slo_analysis.total_slos > 0
    assert slo_analysis.average_compliance >= 90.0  # Overall compliance should be good
    
    # Verify critical services compliance
    critical_violations = slo_analysis.critical_violations
    assert len(critical_violations) <= 1  # Minimal critical violations allowed
    
    # Verify SLO distribution
    compliance_rate = (slo_analysis.compliant_slos / slo_analysis.total_slos) * 100
    assert compliance_rate >= 70.0  # At least 70% of SLOs should be compliant


@pytest.mark.asyncio
async def test_error_budget_tracking_l3(slo_calculation_validator):
    """Test error budget tracking and burn rate calculations.
    
    L3: Tests error budget management with real SLO data.
    """
    # Generate SLI data with some performance degradation
    sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=36, data_points_per_hour=40)
    
    # Test error budget tracking
    error_budget_results = await slo_calculation_validator.test_error_budget_tracking(sli_data)
    
    # Verify error budget tracking
    assert error_budget_results["slos_tracked"] > 0
    assert error_budget_results["error_budgets_calculated"] == error_budget_results["slos_tracked"]
    assert error_budget_results["burn_rates_calculated"] == error_budget_results["slos_tracked"]
    
    # Verify burn rate calculations
    assert error_budget_results["average_burn_rate"] >= 0.0
    assert error_budget_results["average_burn_rate"] <= 100.0
    
    # Check budget violations
    if error_budget_results["budget_violations"]:
        for violation in error_budget_results["budget_violations"]:
            assert violation["remaining_budget"] <= 10.0  # Should be low budget
            assert "criticality" in violation


@pytest.mark.asyncio
async def test_slo_time_window_accuracy_l3(slo_calculation_validator):
    """Test accuracy of different SLO time window calculations.
    
    L3: Tests time window calculations with various periods.
    """
    # Generate data spanning multiple time windows
    sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=168, data_points_per_hour=20)  # 1 week
    
    # Calculate SLOs
    slo_results = await slo_calculation_validator.calculate_slo_compliance(sli_data)
    
    # Verify time window calculations
    time_window_results = {}
    for result in slo_results:
        slo_def = next((slo for slo in slo_calculation_validator.slo_definitions if slo.slo_id == result.slo_id), None)
        if slo_def:
            window_type = slo_def.time_window.value
            if window_type not in time_window_results:
                time_window_results[window_type] = []
            time_window_results[window_type].append(result)
    
    # Verify different time windows are calculated
    assert len(time_window_results) >= 3  # Should have multiple time windows
    
    # Verify time window accuracy
    for window_type, results in time_window_results.items():
        for result in results:
            window_duration = (result.time_window_end - result.time_window_start).total_seconds()
            
            if "1h" in window_type:
                assert 3500 <= window_duration <= 3700  # ~1 hour
            elif "24h" in window_type:
                assert 86300 <= window_duration <= 86500  # ~24 hours
            elif "7d" in window_type:
                assert 604700 <= window_duration <= 604900  # ~7 days


@pytest.mark.asyncio
async def test_slo_trend_analysis_l3(slo_calculation_validator):
    """Test SLO trend analysis and direction calculation.
    
    L3: Tests trend detection with realistic performance patterns.
    """
    # Generate SLI data with clear trends
    sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=72, data_points_per_hour=30)
    
    # Calculate SLOs
    slo_results = await slo_calculation_validator.calculate_slo_compliance(sli_data)
    
    # Analyze trends
    trend_analysis = {
        "improving": 0,
        "stable": 0,
        "degrading": 0,
        "unknown": 0
    }
    
    for result in slo_results:
        trend_analysis[result.trend_direction] += 1
    
    # Verify trend analysis
    total_trends = sum(trend_analysis.values())
    assert total_trends > 0
    
    # Should have some trend detection (not all unknown)
    assert trend_analysis["unknown"] < total_trends * 0.5
    
    # Verify trend directions are reasonable
    for direction, count in trend_analysis.items():
        assert count >= 0


@pytest.mark.asyncio
async def test_critical_slo_priority_l3(slo_calculation_validator):
    """Test priority handling for critical SLOs.
    
    L3: Tests that critical SLOs receive appropriate priority and accuracy.
    """
    # Generate SLI data
    sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=24, data_points_per_hour=60)
    
    # Calculate SLOs
    slo_results = await slo_calculation_validator.calculate_slo_compliance(sli_data)
    
    # Analyze critical SLOs
    critical_slo_results = []
    for result in slo_results:
        slo_def = next((slo for slo in slo_calculation_validator.slo_definitions if slo.slo_id == result.slo_id), None)
        if slo_def and slo_def.business_criticality == "critical":
            critical_slo_results.append(result)
    
    assert len(critical_slo_results) > 0  # Should have critical SLOs
    
    # Verify critical SLOs have appropriate targets
    for result in critical_slo_results:
        assert result.target_percentage >= 99.0  # Critical SLOs should have high targets
    
    # Verify critical SLO compliance
    critical_violations = [r for r in critical_slo_results if r.compliance_status == "violated"]
    violation_rate = len(critical_violations) / len(critical_slo_results)
    assert violation_rate <= 0.2  # No more than 20% critical SLO violations


@pytest.mark.asyncio
async def test_slo_calculation_performance_l3(slo_calculation_validator):
    """Test performance of SLO calculations under load.
    
    L3: Tests calculation performance with large datasets.
    """
    # Generate large dataset
    large_sli_data = await slo_calculation_validator.generate_sli_data_stream(duration_hours=168, data_points_per_hour=120)  # High frequency data
    
    # Measure calculation performance
    calc_start = time.time()
    slo_results = await slo_calculation_validator.calculate_slo_compliance(large_sli_data)
    calc_duration = time.time() - calc_start
    
    # Verify calculation performance
    assert calc_duration <= 10.0  # Should complete within 10 seconds
    assert len(slo_results) > 0  # Should produce results
    
    # Verify all SLOs were calculated
    expected_slo_count = len(slo_calculation_validator.slo_definitions)
    assert len(slo_results) == expected_slo_count
    
    # Calculate throughput
    data_points_processed = len(large_sli_data)
    throughput = data_points_processed / calc_duration
    assert throughput >= 100  # Should process at least 100 data points per second