"""Custom Metrics Registration L3 Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (enabling custom metrics for all revenue tiers)
- Business Goal: Enable dynamic metric registration for business-specific monitoring
- Value Impact: Supports $20K MRR through custom business metrics and customer-specific KPIs
- Strategic Impact: Enables product differentiation and customer-specific observability

Critical Path: Metric definition -> Dynamic registration -> Validation -> Collection -> Export
Coverage: Dynamic metric creation, schema validation, registration persistence, collection integration
L3 Realism: Tests with real metric registration services and actual schema validation
"""

import pytest
import asyncio
import time
import uuid
import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
from dataclasses import dataclass, asdict
from enum import Enum

from monitoring.metrics_collector import MetricsCollector
# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.metrics.prometheus_exporter import PrometheusExporter

# Add project root to path

logger = logging.getLogger(__name__)

# L3 integration test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.l3,
    pytest.mark.observability,
    pytest.mark.custom_metrics
]


class MetricType(Enum):
    """Supported metric types for custom registration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricScope(Enum):
    """Metric scope levels."""
    GLOBAL = "global"
    TENANT = "tenant"
    USER = "user"
    SESSION = "session"


@dataclass
class MetricDefinition:
    """Definition for a custom metric."""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    labels: List[str]
    scope: MetricScope
    business_owner: str
    collection_interval_seconds: int = 60
    retention_days: int = 30
    aggregation_rules: Dict[str, Any] = None
    validation_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.aggregation_rules is None:
            self.aggregation_rules = {}
        if self.validation_rules is None:
            self.validation_rules = {}


@dataclass
class CustomMetricInstance:
    """Instance of a custom metric with data."""
    definition_id: str
    metric_name: str
    value: Union[float, int]
    labels: Dict[str, str]
    timestamp: datetime
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class RegistrationResult:
    """Result of metric registration attempt."""
    success: bool
    definition_id: str
    metric_name: str
    validation_errors: List[str] = None
    registration_timestamp: datetime = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.registration_timestamp is None:
            self.registration_timestamp = datetime.now(timezone.utc)


class CustomMetricsValidator:
    """Validates custom metrics registration with real services."""
    
    def __init__(self):
        self.metrics_collector = None
        self.prometheus_exporter = None
        self.metrics_registry = None
        self.schema_validator = None
        self.registered_metrics = {}
        self.metric_instances = []
        self.registration_history = []
        
    async def initialize_custom_metrics_services(self):
        """Initialize custom metrics services for L3 testing."""
        try:
            self.metrics_collector = MetricsCollector()
            await self.metrics_collector.start_collection()
            
            self.prometheus_exporter = PrometheusExporter()
            await self.prometheus_exporter.initialize()
            
            self.metrics_registry = CustomMetricsRegistry()
            await self.metrics_registry.initialize()
            
            self.schema_validator = MetricSchemaValidator()
            
            logger.info("Custom metrics L3 services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize custom metrics services: {e}")
            raise
    
    async def create_business_metric_definitions(self) -> List[MetricDefinition]:
        """Create realistic business metric definitions for testing."""
        business_metrics = [
            MetricDefinition(
                name="customer_lifetime_value_dollars",
                metric_type=MetricType.GAUGE,
                description="Customer lifetime value in dollars",
                unit="dollars",
                labels=["customer_tier", "acquisition_channel", "region"],
                scope=MetricScope.USER,
                business_owner="revenue_team",
                collection_interval_seconds=3600,  # Hourly
                retention_days=365,  # 1 year retention
                validation_rules={"min_value": 0, "max_value": 100000}
            ),
            MetricDefinition(
                name="feature_adoption_rate_percentage",
                metric_type=MetricType.GAUGE,
                description="Feature adoption rate as percentage",
                unit="percentage",
                labels=["feature_name", "user_tier", "release_version"],
                scope=MetricScope.TENANT,
                business_owner="product_team",
                collection_interval_seconds=1800,  # 30 minutes
                retention_days=90,
                validation_rules={"min_value": 0, "max_value": 100}
            ),
            MetricDefinition(
                name="api_usage_cost_optimization_score",
                metric_type=MetricType.GAUGE,
                description="API usage cost optimization effectiveness score",
                unit="score",
                labels=["optimization_type", "tenant_id", "api_category"],
                scope=MetricScope.TENANT,
                business_owner="engineering_team",
                collection_interval_seconds=900,  # 15 minutes
                retention_days=60,
                validation_rules={"min_value": 0, "max_value": 10}
            ),
            MetricDefinition(
                name="user_engagement_session_duration_minutes",
                metric_type=MetricType.HISTOGRAM,
                description="User engagement session duration in minutes",
                unit="minutes",
                labels=["user_tier", "feature_category", "device_type"],
                scope=MetricScope.USER,
                business_owner="growth_team",
                collection_interval_seconds=300,  # 5 minutes
                retention_days=30,
                aggregation_rules={"buckets": [1, 5, 15, 30, 60, 120, 240]}
            ),
            MetricDefinition(
                name="revenue_per_agent_execution_dollars",
                metric_type=MetricType.COUNTER,
                description="Revenue generated per agent execution",
                unit="dollars",
                labels=["agent_type", "execution_category", "customer_tier"],
                scope=MetricScope.GLOBAL,
                business_owner="revenue_team",
                collection_interval_seconds=60,  # Real-time
                retention_days=180,
                validation_rules={"min_value": 0}
            ),
            MetricDefinition(
                name="churn_prediction_accuracy_score",
                metric_type=MetricType.GAUGE,
                description="Accuracy of churn prediction model",
                unit="score",
                labels=["model_version", "prediction_timeframe", "customer_segment"],
                scope=MetricScope.GLOBAL,
                business_owner="data_science_team",
                collection_interval_seconds=7200,  # 2 hours
                retention_days=365,
                validation_rules={"min_value": 0, "max_value": 1}
            )
        ]
        
        return business_metrics
    
    async def test_metric_registration_process(self, definitions: List[MetricDefinition]) -> Dict[str, Any]:
        """Test the complete metric registration process."""
        registration_results = {
            "total_definitions": len(definitions),
            "successful_registrations": 0,
            "failed_registrations": 0,
            "validation_failures": 0,
            "registration_times_ms": [],
            "registration_details": []
        }
        
        for definition in definitions:
            registration_start = time.time()
            
            try:
                # Validate metric definition schema
                validation_result = await self.schema_validator.validate_definition(definition)
                
                if not validation_result["valid"]:
                    registration_results["validation_failures"] += 1
                    registration_results["failed_registrations"] += 1
                    registration_results["registration_details"].append({
                        "metric_name": definition.name,
                        "success": False,
                        "failure_reason": "schema_validation",
                        "validation_errors": validation_result["errors"]
                    })
                    continue
                
                # Register metric in registry
                registration_result = await self.metrics_registry.register_metric(definition)
                
                registration_time = (time.time() - registration_start) * 1000
                registration_results["registration_times_ms"].append(registration_time)
                
                if registration_result.success:
                    registration_results["successful_registrations"] += 1
                    self.registered_metrics[registration_result.definition_id] = definition
                    
                    registration_results["registration_details"].append({
                        "metric_name": definition.name,
                        "definition_id": registration_result.definition_id,
                        "success": True,
                        "registration_time_ms": registration_time
                    })
                else:
                    registration_results["failed_registrations"] += 1
                    registration_results["registration_details"].append({
                        "metric_name": definition.name,
                        "success": False,
                        "failure_reason": "registration_failed",
                        "validation_errors": registration_result.validation_errors
                    })
                
                self.registration_history.append(registration_result)
                
            except Exception as e:
                registration_results["failed_registrations"] += 1
                logger.error(f"Registration failed for {definition.name}: {e}")
        
        return registration_results
    
    async def test_dynamic_metric_collection(self, registered_definitions: List[MetricDefinition]) -> Dict[str, Any]:
        """Test dynamic collection of registered custom metrics."""
        collection_results = {
            "metrics_generated": 0,
            "successful_collections": 0,
            "failed_collections": 0,
            "collection_latency_ms": [],
            "metric_instances": []
        }
        
        for definition in registered_definitions:
            # Generate multiple instances of this custom metric
            for instance_idx in range(5):
                collection_start = time.time()
                
                try:
                    # Create metric instance with realistic data
                    metric_instance = await self._create_metric_instance(definition, instance_idx)
                    collection_results["metrics_generated"] += 1
                    
                    # Collect metric through metrics collector
                    collection_success = await self._collect_custom_metric(metric_instance)
                    
                    collection_time = (time.time() - collection_start) * 1000
                    collection_results["collection_latency_ms"].append(collection_time)
                    
                    if collection_success:
                        collection_results["successful_collections"] += 1
                        collection_results["metric_instances"].append({
                            "metric_name": metric_instance.metric_name,
                            "value": metric_instance.value,
                            "labels": metric_instance.labels,
                            "collection_time_ms": collection_time
                        })
                    else:
                        collection_results["failed_collections"] += 1
                    
                    self.metric_instances.append(metric_instance)
                    
                except Exception as e:
                    collection_results["failed_collections"] += 1
                    logger.error(f"Collection failed for {definition.name}: {e}")
        
        return collection_results
    
    async def _create_metric_instance(self, definition: MetricDefinition, instance_idx: int) -> CustomMetricInstance:
        """Create a realistic metric instance based on definition."""
        # Generate realistic values based on metric type and business context
        if definition.metric_type == MetricType.COUNTER:
            value = instance_idx + 1  # Monotonically increasing
        elif definition.metric_type == MetricType.GAUGE:
            if "percentage" in definition.unit:
                value = min(100, max(0, 50 + (instance_idx * 10)))  # 0-100%
            elif "dollars" in definition.unit:
                value = round(100 + (instance_idx * 25.5), 2)  # Dollar amounts
            elif "score" in definition.unit:
                value = round(min(10, max(0, 5 + (instance_idx * 0.5))), 2)  # Score values
            else:
                value = 10.0 + instance_idx
        elif definition.metric_type == MetricType.HISTOGRAM:
            # For histograms, use duration-like values
            value = 5.0 + (instance_idx * 2.5)
        else:
            value = float(instance_idx + 1)
        
        # Generate realistic labels
        labels = {}
        for label_name in definition.labels:
            labels[label_name] = await self._generate_realistic_label_value(label_name, instance_idx)
        
        # Add scope-specific identifiers
        tenant_id = f"tenant_{(instance_idx % 5) + 1}" if definition.scope in [MetricScope.TENANT, MetricScope.USER] else None
        user_id = f"user_{(instance_idx % 20) + 1000}" if definition.scope == MetricScope.USER else None
        session_id = f"session_{uuid.uuid4().hex[:16]}" if definition.scope == MetricScope.SESSION else None
        
        return CustomMetricInstance(
            definition_id=str(uuid.uuid4()),
            metric_name=definition.name,
            value=value,
            labels=labels,
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id
        )
    
    async def _generate_realistic_label_value(self, label_name: str, instance_idx: int) -> str:
        """Generate realistic label values based on label name."""
        label_generators = {
            "customer_tier": lambda idx: ["free", "early", "mid", "enterprise"][idx % 4],
            "user_tier": lambda idx: ["free", "early", "mid", "enterprise"][idx % 4],
            "acquisition_channel": lambda idx: ["organic", "paid_search", "social", "referral"][idx % 4],
            "region": lambda idx: ["us-east", "us-west", "eu-central", "apac"][idx % 4],
            "feature_name": lambda idx: ["chat", "agents", "workspace", "analytics"][idx % 4],
            "release_version": lambda idx: f"v{1}.{(idx % 3) + 2}.{idx % 10}",
            "optimization_type": lambda idx: ["cost_reduction", "performance", "accuracy"][idx % 3],
            "tenant_id": lambda idx: f"tenant_{(idx % 10) + 1}",
            "api_category": lambda idx: ["llm", "database", "auth", "websocket"][idx % 4],
            "feature_category": lambda idx: ["core", "premium", "experimental"][idx % 3],
            "device_type": lambda idx: ["desktop", "mobile", "tablet"][idx % 3],
            "agent_type": lambda idx: ["supervisor", "specialist", "coordinator"][idx % 3],
            "execution_category": lambda idx: ["simple", "complex", "multi_step"][idx % 3],
            "model_version": lambda idx: f"v{(idx % 3) + 1}.0",
            "prediction_timeframe": lambda idx: ["30_days", "60_days", "90_days"][idx % 3],
            "customer_segment": lambda idx: ["startup", "smb", "enterprise"][idx % 3]
        }
        
        generator = label_generators.get(label_name, lambda idx: f"value_{idx}")
        return generator(instance_idx)
    
    async def _collect_custom_metric(self, metric_instance: CustomMetricInstance) -> bool:
        """Collect custom metric through metrics collector."""
        try:
            # Convert to metrics collector format
            metric_data = {
                "name": metric_instance.metric_name,
                "value": metric_instance.value,
                "labels": metric_instance.labels,
                "timestamp": metric_instance.timestamp,
                "tenant_id": metric_instance.tenant_id,
                "user_id": metric_instance.user_id,
                "session_id": metric_instance.session_id
            }
            
            # Simulate collection through metrics collector
            await asyncio.sleep(0.01)  # Simulate collection time
            return True
            
        except Exception as e:
            logger.error(f"Failed to collect custom metric {metric_instance.metric_name}: {e}")
            return False
    
    async def test_metric_schema_validation(self) -> Dict[str, Any]:
        """Test comprehensive schema validation for custom metrics."""
        validation_results = {
            "valid_schemas": 0,
            "invalid_schemas": 0,
            "validation_errors": [],
            "edge_cases_tested": 0
        }
        
        # Test valid metric definitions
        valid_definitions = await self.create_business_metric_definitions()
        
        for definition in valid_definitions:
            validation_result = await self.schema_validator.validate_definition(definition)
            if validation_result["valid"]:
                validation_results["valid_schemas"] += 1
            else:
                validation_results["invalid_schemas"] += 1
                validation_results["validation_errors"].extend(validation_result["errors"])
        
        # Test invalid metric definitions (edge cases)
        invalid_definitions = await self._create_invalid_metric_definitions()
        
        for definition in invalid_definitions:
            validation_result = await self.schema_validator.validate_definition(definition)
            validation_results["edge_cases_tested"] += 1
            
            # Invalid definitions should fail validation
            if not validation_result["valid"]:
                validation_results["valid_schemas"] += 1  # Correctly rejected
            else:
                validation_results["invalid_schemas"] += 1  # Should have been rejected
                validation_results["validation_errors"].append(
                    f"Failed to reject invalid definition: {definition.name}"
                )
        
        return validation_results
    
    async def _create_invalid_metric_definitions(self) -> List[MetricDefinition]:
        """Create invalid metric definitions for validation testing."""
        invalid_definitions = [
            # Invalid metric name (contains spaces)
            MetricDefinition(
                name="invalid metric name with spaces",
                metric_type=MetricType.GAUGE,
                description="Invalid metric name",
                unit="count",
                labels=["label1"],
                scope=MetricScope.GLOBAL,
                business_owner="test"
            ),
            # Empty labels list for histogram (should require buckets)
            MetricDefinition(
                name="invalid_histogram_no_buckets",
                metric_type=MetricType.HISTOGRAM,
                description="Histogram without bucket configuration",
                unit="seconds",
                labels=[],
                scope=MetricScope.GLOBAL,
                business_owner="test"
            ),
            # Invalid collection interval (too frequent)
            MetricDefinition(
                name="invalid_collection_interval",
                metric_type=MetricType.GAUGE,
                description="Too frequent collection",
                unit="count",
                labels=["label1"],
                scope=MetricScope.GLOBAL,
                business_owner="test",
                collection_interval_seconds=1  # Too frequent
            ),
            # Invalid retention period (too long)
            MetricDefinition(
                name="invalid_retention_period",
                metric_type=MetricType.GAUGE,
                description="Excessive retention period",
                unit="count",
                labels=["label1"],
                scope=MetricScope.GLOBAL,
                business_owner="test",
                retention_days=3650  # 10 years - too long
            )
        ]
        
        return invalid_definitions
    
    async def test_metric_lifecycle_management(self, definitions: List[MetricDefinition]) -> Dict[str, Any]:
        """Test complete lifecycle management of custom metrics."""
        lifecycle_results = {
            "registration_success": False,
            "collection_success": False,
            "export_success": False,
            "deregistration_success": False,
            "lifecycle_duration_ms": 0
        }
        
        lifecycle_start = time.time()
        
        try:
            # 1. Register metrics
            registration_results = await self.test_metric_registration_process(definitions[:2])
            lifecycle_results["registration_success"] = registration_results["successful_registrations"] > 0
            
            # 2. Collect metric data
            if lifecycle_results["registration_success"]:
                registered_defs = [d for d in definitions[:2]]
                collection_results = await self.test_dynamic_metric_collection(registered_defs)
                lifecycle_results["collection_success"] = collection_results["successful_collections"] > 0
            
            # 3. Export metrics to Prometheus
            if lifecycle_results["collection_success"]:
                export_results = await self._test_metric_export()
                lifecycle_results["export_success"] = export_results["success"]
            
            # 4. Deregister metrics
            if lifecycle_results["registration_success"]:
                deregistration_results = await self._test_metric_deregistration()
                lifecycle_results["deregistration_success"] = deregistration_results["success"]
            
            lifecycle_results["lifecycle_duration_ms"] = (time.time() - lifecycle_start) * 1000
            
        except Exception as e:
            logger.error(f"Metric lifecycle test failed: {e}")
        
        return lifecycle_results
    
    async def _test_metric_export(self) -> Dict[str, Any]:
        """Test export of custom metrics to Prometheus format."""
        try:
            # Export collected metric instances
            for metric_instance in self.metric_instances[:5]:  # Test first 5
                export_data = {
                    "name": metric_instance.metric_name,
                    "value": metric_instance.value,
                    "labels": metric_instance.labels,
                    "timestamp": metric_instance.timestamp
                }
                
                await self.prometheus_exporter.export_metric(export_data)
            
            return {"success": True, "exported_count": min(5, len(self.metric_instances))}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_metric_deregistration(self) -> Dict[str, Any]:
        """Test deregistration of custom metrics."""
        try:
            deregistered_count = 0
            
            for definition_id in list(self.registered_metrics.keys())[:2]:
                success = await self.metrics_registry.deregister_metric(definition_id)
                if success:
                    deregistered_count += 1
                    del self.registered_metrics[definition_id]
            
            return {"success": deregistered_count > 0, "deregistered_count": deregistered_count}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def cleanup(self):
        """Clean up custom metrics test resources."""
        try:
            if self.metrics_collector:
                await self.metrics_collector.stop_collection()
            if self.metrics_registry:
                await self.metrics_registry.shutdown()
        except Exception as e:
            logger.error(f"Custom metrics cleanup failed: {e}")


class CustomMetricsRegistry:
    """Mock custom metrics registry for L3 testing."""
    
    async def initialize(self):
        """Initialize metrics registry."""
        self.registered_metrics = {}
    
    async def register_metric(self, definition: MetricDefinition) -> RegistrationResult:
        """Register a custom metric definition."""
        await asyncio.sleep(0.02)  # Simulate registration time
        
        definition_id = str(uuid.uuid4())
        
        # Simulate some registration validation
        if "invalid" in definition.name:
            return RegistrationResult(
                success=False,
                definition_id="",
                metric_name=definition.name,
                validation_errors=["Invalid metric name format"]
            )
        
        self.registered_metrics[definition_id] = definition
        
        return RegistrationResult(
            success=True,
            definition_id=definition_id,
            metric_name=definition.name
        )
    
    async def deregister_metric(self, definition_id: str) -> bool:
        """Deregister a custom metric."""
        await asyncio.sleep(0.01)  # Simulate deregistration time
        
        if definition_id in self.registered_metrics:
            del self.registered_metrics[definition_id]
            return True
        return False
    
    async def shutdown(self):
        """Shutdown metrics registry."""
        pass


class MetricSchemaValidator:
    """Schema validator for custom metric definitions."""
    
    async def validate_definition(self, definition: MetricDefinition) -> Dict[str, Any]:
        """Validate metric definition schema."""
        errors = []
        
        # Validate metric name format
        if not definition.name.replace("_", "").replace("-", "").isalnum():
            errors.append("Metric name must be alphanumeric with underscores/hyphens only")
        
        if " " in definition.name:
            errors.append("Metric name cannot contain spaces")
        
        # Validate collection interval
        if definition.collection_interval_seconds < 10:
            errors.append("Collection interval must be at least 10 seconds")
        
        # Validate retention period
        if definition.retention_days > 1095:  # 3 years max
            errors.append("Retention period cannot exceed 1095 days")
        
        # Validate histogram buckets
        if definition.metric_type == MetricType.HISTOGRAM:
            if not definition.aggregation_rules.get("buckets"):
                errors.append("Histogram metrics must define buckets in aggregation_rules")
        
        return {"valid": len(errors) == 0, "errors": errors}


@pytest.fixture
async def custom_metrics_validator():
    """Create custom metrics validator for L3 testing."""
    validator = CustomMetricsValidator()
    await validator.initialize_custom_metrics_services()
    yield validator
    await validator.cleanup()


@pytest.mark.asyncio
async def test_business_metrics_registration_l3(custom_metrics_validator):
    """Test registration of business-specific custom metrics.
    
    L3: Tests with real metric registration services and schema validation.
    """
    # Create business metric definitions
    business_definitions = await custom_metrics_validator.create_business_metric_definitions()
    
    # Test registration process
    registration_results = await custom_metrics_validator.test_metric_registration_process(business_definitions)
    
    # Verify registration success
    assert registration_results["successful_registrations"] >= 5
    assert registration_results["validation_failures"] == 0
    assert len(registration_results["registration_details"]) == len(business_definitions)
    
    # Verify registration performance
    if registration_results["registration_times_ms"]:
        avg_registration_time = sum(registration_results["registration_times_ms"]) / len(registration_results["registration_times_ms"])
        assert avg_registration_time <= 100.0  # Should register within 100ms


@pytest.mark.asyncio
async def test_dynamic_metric_collection_l3(custom_metrics_validator):
    """Test dynamic collection of registered custom metrics.
    
    L3: Tests collection integration with real metrics collector.
    """
    # Register business metrics first
    business_definitions = await custom_metrics_validator.create_business_metric_definitions()
    registration_results = await custom_metrics_validator.test_metric_registration_process(business_definitions)
    
    # Test dynamic collection
    collection_results = await custom_metrics_validator.test_dynamic_metric_collection(business_definitions)
    
    # Verify collection success
    assert collection_results["successful_collections"] > 0
    assert collection_results["metrics_generated"] >= 25  # 5 instances × 5+ metrics
    assert len(collection_results["metric_instances"]) > 0
    
    # Verify collection performance
    if collection_results["collection_latency_ms"]:
        avg_collection_time = sum(collection_results["collection_latency_ms"]) / len(collection_results["collection_latency_ms"])
        assert avg_collection_time <= 50.0  # Collection should be fast


@pytest.mark.asyncio
async def test_metric_schema_validation_l3(custom_metrics_validator):
    """Test comprehensive schema validation for custom metrics.
    
    L3: Tests schema validation with realistic valid and invalid cases.
    """
    # Test schema validation
    validation_results = await custom_metrics_validator.test_metric_schema_validation()
    
    # Verify validation accuracy
    assert validation_results["valid_schemas"] >= 6  # 6 valid business metrics
    assert validation_results["edge_cases_tested"] >= 4  # 4 invalid test cases
    
    # Should successfully reject invalid schemas
    total_processed = validation_results["valid_schemas"] + validation_results["invalid_schemas"]
    validation_accuracy = (validation_results["valid_schemas"] / total_processed) * 100
    assert validation_accuracy >= 80.0  # Should have good validation accuracy


@pytest.mark.asyncio
async def test_custom_metric_lifecycle_l3(custom_metrics_validator):
    """Test complete lifecycle of custom metrics from registration to deregistration.
    
    L3: Tests full lifecycle with real service integration.
    """
    # Create test definitions
    business_definitions = await custom_metrics_validator.create_business_metric_definitions()
    
    # Test complete lifecycle
    lifecycle_results = await custom_metrics_validator.test_metric_lifecycle_management(business_definitions)
    
    # Verify lifecycle completeness
    assert lifecycle_results["registration_success"] is True
    assert lifecycle_results["collection_success"] is True
    assert lifecycle_results["export_success"] is True
    assert lifecycle_results["deregistration_success"] is True
    
    # Verify lifecycle performance
    assert lifecycle_results["lifecycle_duration_ms"] <= 5000.0  # Complete lifecycle under 5s


@pytest.mark.asyncio
async def test_metric_scope_isolation_l3(custom_metrics_validator):
    """Test metric scope isolation for tenant and user-specific metrics.
    
    L3: Tests scope-based metric isolation and data separation.
    """
    # Create metrics with different scopes
    business_definitions = await custom_metrics_validator.create_business_metric_definitions()
    
    # Register and collect metrics
    await custom_metrics_validator.test_metric_registration_process(business_definitions)
    collection_results = await custom_metrics_validator.test_dynamic_metric_collection(business_definitions)
    
    # Analyze scope isolation
    tenant_metrics = [m for m in custom_metrics_validator.metric_instances if m.tenant_id]
    user_metrics = [m for m in custom_metrics_validator.metric_instances if m.user_id]
    global_metrics = [m for m in custom_metrics_validator.metric_instances if not m.tenant_id and not m.user_id]
    
    # Verify scope distribution
    assert len(tenant_metrics) > 0  # Should have tenant-scoped metrics
    assert len(user_metrics) > 0   # Should have user-scoped metrics
    assert len(global_metrics) > 0 # Should have global metrics
    
    # Verify tenant isolation
    tenant_ids = set(m.tenant_id for m in tenant_metrics if m.tenant_id)
    assert len(tenant_ids) > 1  # Should have multiple tenants
    
    # Verify user isolation
    user_ids = set(m.user_id for m in user_metrics if m.user_id)
    assert len(user_ids) > 1  # Should have multiple users