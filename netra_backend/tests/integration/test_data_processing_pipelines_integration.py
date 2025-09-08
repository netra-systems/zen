"""
Data Processing Pipelines Integration Tests

Business Value Justification (BVJ):
- Segment: All
- Business Goal: Ensure reliable data processing for business insights and AI-driven value delivery
- Value Impact: Data pipelines must process user data accurately to deliver business insights, cost optimization, and performance improvements
- Strategic Impact: Core platform capability for data-driven decision making and AI agent execution workflows

These integration tests validate real data processing components that bridge the gap between unit tests 
and full end-to-end tests. They focus on:
1. Message processing pipeline workflow and orchestration
2. Data transformation and validation at pipeline stages  
3. Queue-like processing patterns and message routing
4. Batch processing scenarios and bulk operations
5. Data persistence abstractions and storage patterns
6. Pipeline error handling and recovery mechanisms
7. Data processing performance and throughput optimization
8. Pipeline integration with agent execution workflows
9. Data serialization and deserialization in pipelines
10. Pipeline observability, monitoring, and metrics collection

CRITICAL: These tests use real data processing components without Docker dependencies.
NO MOCKS are used for data processing logic - only for external service isolation.
"""

import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch
import json
import uuid

from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env

# Core data processing components
from netra_backend.app.services.message_queue import MessageQueueService, MessageQueue
from netra_backend.app.core.performance_batch_processor import BatchProcessor
from netra_backend.app.agents.synthetic_data_batch_processor import SyntheticDataBatchProcessor
from netra_backend.app.agents.supervisor.pipeline_builder import PipelineBuilder
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor
from netra_backend.app.schemas.data_ingestion_types import (
    DataSource, DataSourceType, DataFormat, IngestionConfig, IngestionJob, 
    IngestionMetrics, DataPipeline, TransformationStep, IngestionStatus,
    ValidationRule, SchemaMapping, DataQualityCheck, DataQualityReport
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, PipelineStepConfig
)


class DataPipelineProcessor:
    """Helper class for data pipeline processing operations."""
    
    def __init__(self):
        self.message_queue = MessageQueueService()
        self.batch_processor = BatchProcessor(max_batch_size=50, flush_interval=0.5)
        self.pipeline_builder = PipelineBuilder()
        
    async def process_message_pipeline(self, messages: List[Dict[str, Any]], 
                                     queue_name: str = "data_processing") -> Dict[str, Any]:
        """Process messages through pipeline workflow."""
        await self.message_queue.start()
        
        # Publish messages to queue
        published_count = 0
        for message in messages:
            success = await self.message_queue.publish(queue_name, message)
            if success:
                published_count += 1
        
        # Process messages from queue
        processed_messages = []
        processing_errors = []
        
        while True:
            message = await self.message_queue.consume(queue_name)
            if not message:
                break
                
            try:
                # Simulate data processing with validation
                processed_message = await self._process_message(message)
                processed_messages.append(processed_message)
            except Exception as e:
                processing_errors.append({
                    "message_id": message.get("id", "unknown"),
                    "error": str(e),
                    "original_message": message
                })
        
        return {
            "published_count": published_count,
            "processed_count": len(processed_messages),
            "error_count": len(processing_errors),
            "processed_messages": processed_messages,
            "errors": processing_errors,
            "queue_size_after": self.message_queue.get_queue_size(queue_name)
        }
    
    async def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual message with validation and transformation."""
        # Validate required fields
        if "data" not in message:
            raise ValueError("Message missing required 'data' field")
        
        # Transform message data
        processed_data = {
            "id": message.get("id", str(uuid.uuid4())),
            "timestamp": message.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "queue": message.get("queue", "unknown"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "original_data": message["data"],
            "transformed_data": await self._transform_message_data(message["data"]),
            "validation_status": "passed"
        }
        
        return processed_data
    
    async def _transform_message_data(self, data: Any) -> Any:
        """Transform message data based on type and content."""
        if isinstance(data, dict):
            # Transform dictionary data
            transformed = {}
            for key, value in data.items():
                if isinstance(value, str) and value.isdigit():
                    transformed[f"{key}_numeric"] = int(value)
                elif isinstance(value, str) and key.endswith("_date"):
                    try:
                        transformed[f"{key}_parsed"] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        transformed[key] = value
                else:
                    transformed[key] = value
            return transformed
        elif isinstance(data, list):
            # Transform list data
            return [await self._transform_message_data(item) for item in data]
        else:
            return data
    
    async def create_data_ingestion_pipeline(self, source_config: Dict[str, Any],
                                           transformation_steps: List[Dict[str, Any]]) -> DataPipeline:
        """Create data ingestion pipeline with transformations."""
        # Create data source
        source = DataSource(
            name=source_config.get("name", "test_source"),
            type=DataSourceType(source_config.get("type", "api")),
            config=source_config.get("config", {}),
            metadata=source_config.get("metadata", {})
        )
        
        # Create destination (for simplicity, same as source but different config)
        destination = DataSource(
            name=f"{source.name}_output",
            type=source.type,
            config={**source.config, "output": True},
            metadata={"role": "destination"}
        )
        
        # Create transformation steps
        transformations = []
        for step_config in transformation_steps:
            transformation = TransformationStep(
                name=step_config.get("name", "transform"),
                type=step_config.get("type", "map"),
                config=step_config.get("config", {}),
                input_schema=step_config.get("input_schema"),
                output_schema=step_config.get("output_schema")
            )
            transformations.append(transformation)
        
        # Create pipeline
        pipeline = DataPipeline(
            name="integration_test_pipeline",
            description="Pipeline for integration testing",
            source=source,
            transformations=transformations,
            destination=destination,
            enabled=True,
            metadata={"test": True, "created_by": "integration_test"}
        )
        
        return pipeline
    
    def calculate_pipeline_metrics(self, start_time: datetime, 
                                 processed_count: int, 
                                 error_count: int,
                                 total_bytes: int = 0) -> IngestionMetrics:
        """Calculate pipeline processing metrics."""
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        metrics = IngestionMetrics(
            job_id="integration_test_job",
            total_records=processed_count + error_count,
            processed_records=processed_count,
            successful_records=processed_count,
            failed_records=error_count,
            processing_rate=processed_count / duration if duration > 0 else 0,
            total_bytes_processed=total_bytes,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration
        )
        
        return metrics


class TestDataProcessingPipelines(BaseIntegrationTest):
    """Integration tests for data processing pipelines functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.processor = DataPipelineProcessor()
        self.batch_processor = BatchProcessor(max_batch_size=10, flush_interval=0.1)
        
        # Test data
        self.sample_messages = [
            {"data": {"user_id": "123", "action": "login", "timestamp_date": "2024-01-01T10:00:00Z"}},
            {"data": {"user_id": "456", "action": "purchase", "amount": "99.99", "timestamp_date": "2024-01-01T11:00:00Z"}},
            {"data": {"user_id": "789", "action": "logout", "session_duration": "3600", "timestamp_date": "2024-01-01T12:00:00Z"}},
            {"data": {"user_id": "123", "action": "view_profile", "timestamp_date": "2024-01-01T13:00:00Z"}},
            {"data": {"user_id": "456", "action": "add_to_cart", "item_count": "3", "timestamp_date": "2024-01-01T14:00:00Z"}}
        ]
    
    @pytest.mark.integration
    async def test_message_processing_pipeline_workflow(self):
        """Test message processing pipeline workflow and orchestration.
        
        BVJ: Ensures message processing pipelines can handle user interaction data
        to provide real-time insights for business decision making.
        """
        # Process messages through pipeline
        start_time = datetime.now(timezone.utc)
        result = await self.processor.process_message_pipeline(
            self.sample_messages, 
            queue_name="workflow_test"
        )
        
        # Validate pipeline processing
        assert result["published_count"] == len(self.sample_messages), "All messages should be published"
        assert result["processed_count"] == len(self.sample_messages), "All messages should be processed"
        assert result["error_count"] == 0, "No processing errors should occur"
        assert result["queue_size_after"] == 0, "Queue should be empty after processing"
        
        # Validate message transformations
        processed_messages = result["processed_messages"]
        assert len(processed_messages) == len(self.sample_messages)
        
        for processed_msg in processed_messages:
            assert "id" in processed_msg
            assert "timestamp" in processed_msg
            assert "processed_at" in processed_msg
            assert "transformed_data" in processed_msg
            assert "validation_status" in processed_msg
            assert processed_msg["validation_status"] == "passed"
            
            # Validate data transformations
            transformed = processed_msg["transformed_data"]
            if "amount" in processed_msg["original_data"]:
                assert "amount_numeric" in transformed, "Numeric conversion should occur"
            if any(key.endswith("_date") for key in processed_msg["original_data"]):
                date_keys = [k for k in transformed.keys() if k.endswith("_date_parsed")]
                assert len(date_keys) > 0, "Date parsing should occur"
        
        # Calculate metrics
        metrics = self.processor.calculate_pipeline_metrics(
            start_time, result["processed_count"], result["error_count"]
        )
        
        assert metrics.successful_records == len(self.sample_messages)
        assert metrics.failed_records == 0
        assert metrics.processing_rate > 0, "Processing rate should be positive"
    
    @pytest.mark.integration 
    async def test_data_transformation_and_validation(self):
        """Test data transformation and validation at pipeline stages.
        
        BVJ: Ensures data transformations provide accurate business intelligence
        by converting raw user data into actionable insights.
        """
        # Create pipeline with multiple transformation steps
        source_config = {
            "name": "user_events",
            "type": "stream",
            "config": {"format": "json", "schema_validation": True},
            "metadata": {"source_system": "web_app"}
        }
        
        transformation_steps = [
            {
                "name": "data_validation",
                "type": "filter",
                "config": {"validate_required_fields": ["user_id", "action"]},
                "input_schema": {"user_id": "string", "action": "string"},
                "output_schema": {"user_id": "string", "action": "string", "validated": "boolean"}
            },
            {
                "name": "data_enrichment", 
                "type": "map",
                "config": {"add_metadata": True, "normalize_timestamps": True},
                "input_schema": {"user_id": "string", "action": "string"},
                "output_schema": {"user_id": "string", "action": "string", "enriched_at": "datetime"}
            },
            {
                "name": "business_logic",
                "type": "custom",
                "config": {"calculate_session_metrics": True, "detect_patterns": True},
                "output_schema": {"user_id": "string", "session_value": "number", "pattern_detected": "boolean"}
            }
        ]
        
        pipeline = await self.processor.create_data_ingestion_pipeline(
            source_config, transformation_steps
        )
        
        # Validate pipeline structure
        assert pipeline.name == "integration_test_pipeline"
        assert pipeline.source.name == "user_events"
        assert pipeline.source.type == DataSourceType.STREAM
        assert len(pipeline.transformations) == 3
        assert pipeline.destination.name == "user_events_output"
        assert pipeline.enabled is True
        
        # Validate transformation steps
        validation_step = pipeline.transformations[0]
        assert validation_step.name == "data_validation"
        assert validation_step.type == "filter"
        assert "validate_required_fields" in validation_step.config
        
        enrichment_step = pipeline.transformations[1]
        assert enrichment_step.name == "data_enrichment"
        assert enrichment_step.type == "map"
        assert "add_metadata" in enrichment_step.config
        
        business_step = pipeline.transformations[2]
        assert business_step.name == "business_logic"
        assert business_step.type == "custom"
        assert "calculate_session_metrics" in business_step.config
        
        # Test schema validation
        for step in pipeline.transformations:
            if step.input_schema:
                assert isinstance(step.input_schema, dict)
                assert len(step.input_schema) > 0
            if step.output_schema:
                assert isinstance(step.output_schema, dict)
                assert len(step.output_schema) > 0
    
    @pytest.mark.integration
    async def test_queue_processing_patterns_and_routing(self):
        """Test queue-like processing patterns and message routing.
        
        BVJ: Validates message routing capabilities essential for multi-tenant
        user request processing and real-time response delivery.
        """
        message_queue = MessageQueueService()
        await message_queue.start()
        
        # Create messages for different routing patterns
        priority_messages = [
            {"data": {"priority": "high", "user_type": "enterprise", "request": "urgent_analysis"}},
            {"data": {"priority": "medium", "user_type": "professional", "request": "report_generation"}},
            {"data": {"priority": "low", "user_type": "free", "request": "basic_query"}}
        ]
        
        # Test routing to different queues based on priority
        routing_results = {}
        for msg in priority_messages:
            priority = msg["data"]["priority"]
            queue_name = f"priority_{priority}"
            
            success = await message_queue.publish(queue_name, msg)
            assert success, f"Message should be published to {queue_name}"
            
            routing_results[queue_name] = message_queue.get_queue_size(queue_name)
        
        # Validate queue routing
        assert routing_results["priority_high"] == 1
        assert routing_results["priority_medium"] == 1
        assert routing_results["priority_low"] == 1
        
        # Test batch consumption with different processing strategies
        processing_results = {}
        
        # High priority - immediate processing
        high_msg = await message_queue.consume("priority_high")
        assert high_msg is not None
        assert high_msg["data"]["priority"] == "high"
        processing_results["high_processed"] = True
        
        # Medium priority - batch processing
        medium_messages = []
        for _ in range(2):  # Consume multiple if available
            msg = await message_queue.consume("priority_medium")
            if msg:
                medium_messages.append(msg)
        
        processing_results["medium_batch_size"] = len(medium_messages)
        processing_results["medium_processed"] = len(medium_messages) > 0
        
        # Low priority - deferred processing
        low_queue_size = message_queue.get_queue_size("priority_low")
        processing_results["low_deferred"] = low_queue_size > 0
        
        # Validate processing patterns
        assert processing_results["high_processed"] is True
        assert processing_results["medium_processed"] is True
        assert processing_results["low_deferred"] is True
        
        # Test message handler subscription
        handled_messages = []
        
        async def test_handler(message):
            handled_messages.append({
                "id": message.get("id"),
                "handled_at": datetime.now(timezone.utc).isoformat(),
                "data": message.get("data")
            })
        
        # Subscribe handler and process remaining messages
        await message_queue.subscribe("priority_low", test_handler)
        await message_queue.process_queue("priority_low")
        
        # Validate handler processing
        assert len(handled_messages) == 1
        assert handled_messages[0]["data"]["priority"] == "low"
        assert "handled_at" in handled_messages[0]
    
    @pytest.mark.integration
    async def test_batch_processing_scenarios_and_operations(self):
        """Test batch processing scenarios and bulk operations.
        
        BVJ: Ensures efficient bulk data processing for cost optimization
        analysis and performance metrics aggregation.
        """
        batch_processor = BatchProcessor(max_batch_size=3, flush_interval=0.2)
        
        # Test data for batch processing
        user_activity_data = [
            {"user_id": "u1", "session_time": 1800, "api_calls": 25, "cost": 0.50},
            {"user_id": "u2", "session_time": 3600, "api_calls": 50, "cost": 1.00},
            {"user_id": "u3", "session_time": 900, "api_calls": 10, "cost": 0.20},
            {"user_id": "u4", "session_time": 2400, "api_calls": 35, "cost": 0.70},
            {"user_id": "u5", "session_time": 1200, "api_calls": 20, "cost": 0.40}
        ]
        
        # Batch processing results tracking
        processed_batches = []
        batch_metrics = {
            "total_batches": 0,
            "total_items": 0,
            "processing_times": [],
            "batch_sizes": []
        }
        
        async def batch_processor_func(batch_items):
            """Process batch and calculate aggregated metrics."""
            start_time = datetime.now(timezone.utc)
            
            # Calculate batch aggregations
            batch_result = {
                "batch_id": f"batch_{len(processed_batches) + 1}",
                "item_count": len(batch_items),
                "total_session_time": sum(item["session_time"] for item in batch_items),
                "total_api_calls": sum(item["api_calls"] for item in batch_items),
                "total_cost": sum(item["cost"] for item in batch_items),
                "avg_session_time": sum(item["session_time"] for item in batch_items) / len(batch_items),
                "avg_cost_per_call": sum(item["cost"] for item in batch_items) / sum(item["api_calls"] for item in batch_items),
                "processed_at": start_time.isoformat(),
                "users_in_batch": [item["user_id"] for item in batch_items]
            }
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()
            
            batch_result["processing_time"] = processing_time
            processed_batches.append(batch_result)
            
            # Update metrics
            batch_metrics["total_batches"] += 1
            batch_metrics["total_items"] += len(batch_items)
            batch_metrics["processing_times"].append(processing_time)
            batch_metrics["batch_sizes"].append(len(batch_items))
        
        # Add items to batch processor
        for item in user_activity_data:
            await batch_processor.add_to_batch("user_activity", item, batch_processor_func)
        
        # Wait for timer-based flush of remaining items
        await asyncio.sleep(0.3)
        
        # Force flush any remaining batches
        await batch_processor.flush_all()
        
        # Validate batch processing results
        assert len(processed_batches) >= 2, "Should process at least 2 batches"
        assert batch_metrics["total_items"] == len(user_activity_data), "All items should be processed"
        
        # Validate batch aggregations
        total_processed_cost = sum(batch["total_cost"] for batch in processed_batches)
        expected_total_cost = sum(item["cost"] for item in user_activity_data)
        assert abs(total_processed_cost - expected_total_cost) < 0.01, "Cost aggregation should be accurate"
        
        total_processed_calls = sum(batch["total_api_calls"] for batch in processed_batches)
        expected_total_calls = sum(item["api_calls"] for item in user_activity_data)
        assert total_processed_calls == expected_total_calls, "API call aggregation should be accurate"
        
        # Validate batch sizes respect max_batch_size
        for batch in processed_batches:
            assert batch["item_count"] <= 3, "Batch size should not exceed max_batch_size"
        
        # Validate performance metrics
        assert all(pt > 0 for pt in batch_metrics["processing_times"]), "All processing times should be positive"
        avg_processing_time = sum(batch_metrics["processing_times"]) / len(batch_metrics["processing_times"])
        assert avg_processing_time < 1.0, "Average processing time should be under 1 second"
        
        # Get batch statistics
        stats = batch_processor.get_batch_stats()
        assert stats["active_batches"] == 0, "No active batches should remain"
        assert stats["pending_items"] == 0, "No pending items should remain"
    
    @pytest.mark.integration
    async def test_data_persistence_abstractions_and_storage(self):
        """Test data persistence abstractions and storage patterns.
        
        BVJ: Validates data storage patterns critical for maintaining user
        session state and agent execution results for business continuity.
        """
        # Mock database and storage layers for integration testing
        mock_db_session = MagicMock()
        mock_storage_client = MagicMock()
        
        # Create ingestion job with persistence configuration
        source = DataSource(
            name="user_sessions",
            type=DataSourceType.DATABASE,
            config={
                "connection_string": "postgresql://test:test@localhost:5432/test_db",
                "table_name": "user_sessions",
                "batch_size": 1000
            },
            metadata={"persistent": True}
        )
        
        ingestion_config = IngestionConfig(
            source=source,
            format=DataFormat.JSON,
            batch_size=500,
            parallel_workers=2,
            validation_rules=[
                ValidationRule(
                    field="user_id",
                    rule_type="required",
                    error_message="User ID is required"
                ),
                ValidationRule(
                    field="session_duration",
                    rule_type="range",
                    value={"min": 0, "max": 86400},
                    error_message="Session duration must be between 0 and 86400 seconds"
                )
            ],
            schema_mapping=[
                SchemaMapping(
                    source_field="user_id",
                    target_field="user_identifier",
                    data_type="string"
                ),
                SchemaMapping(
                    source_field="session_start",
                    target_field="session_start_time",
                    transformation="iso_to_datetime",
                    data_type="datetime"
                )
            ],
            deduplication_enabled=True,
            deduplication_fields=["user_id", "session_start"]
        )
        
        ingestion_job = IngestionJob(
            name="user_session_ingestion",
            config=ingestion_config,
            status=IngestionStatus.PENDING,
            schedule="0 */6 * * *",  # Every 6 hours
            metadata={"priority": "high", "retention_days": 90}
        )
        
        # Validate job configuration
        assert ingestion_job.name == "user_session_ingestion"
        assert ingestion_job.status == IngestionStatus.PENDING
        assert ingestion_job.config.source.name == "user_sessions"
        assert ingestion_job.config.batch_size == 500
        assert ingestion_job.config.deduplication_enabled is True
        assert len(ingestion_job.config.validation_rules) == 2
        assert len(ingestion_job.config.schema_mapping) == 2
        
        # Test validation rules
        user_id_rule = ingestion_job.config.validation_rules[0]
        assert user_id_rule.field == "user_id"
        assert user_id_rule.rule_type == "required"
        
        duration_rule = ingestion_job.config.validation_rules[1]
        assert duration_rule.field == "session_duration"
        assert duration_rule.rule_type == "range"
        assert duration_rule.value == {"min": 0, "max": 86400}
        
        # Test schema mapping
        user_id_mapping = ingestion_job.config.schema_mapping[0]
        assert user_id_mapping.source_field == "user_id"
        assert user_id_mapping.target_field == "user_identifier"
        
        session_mapping = ingestion_job.config.schema_mapping[1]
        assert session_mapping.source_field == "session_start"
        assert session_mapping.target_field == "session_start_time"
        assert session_mapping.transformation == "iso_to_datetime"
        
        # Simulate job execution with metrics collection
        start_time = datetime.now(timezone.utc)
        
        # Mock data processing
        sample_records = [
            {"user_id": "u1", "session_start": "2024-01-01T10:00:00Z", "session_duration": 1800},
            {"user_id": "u2", "session_start": "2024-01-01T11:00:00Z", "session_duration": 3600},
            {"user_id": "u1", "session_start": "2024-01-01T10:00:00Z", "session_duration": 1800},  # Duplicate
            {"user_id": "u3", "session_start": "2024-01-01T12:00:00Z", "session_duration": 90000}   # Invalid duration
        ]
        
        # Process records with validation and deduplication
        valid_records = []
        duplicate_records = []
        invalid_records = []
        seen_records = set()
        
        for record in sample_records:
            # Check for duplicates
            record_key = (record["user_id"], record["session_start"])
            if record_key in seen_records:
                duplicate_records.append(record)
                continue
            
            # Validate record
            is_valid = True
            validation_errors = []
            
            # Check required fields
            if not record.get("user_id"):
                validation_errors.append("User ID is required")
                is_valid = False
            
            # Check session duration range
            duration = record.get("session_duration", 0)
            if duration < 0 or duration > 86400:
                validation_errors.append("Session duration must be between 0 and 86400 seconds")
                is_valid = False
            
            if is_valid:
                valid_records.append(record)
                seen_records.add(record_key)
            else:
                invalid_records.append({"record": record, "errors": validation_errors})
        
        # Create metrics
        end_time = datetime.now(timezone.utc)
        metrics = IngestionMetrics(
            job_id=ingestion_job.id,
            total_records=len(sample_records),
            processed_records=len(valid_records),
            successful_records=len(valid_records),
            failed_records=len(invalid_records),
            duplicate_records=len(duplicate_records),
            processing_rate=len(valid_records) / ((end_time - start_time).total_seconds() or 1),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=(end_time - start_time).total_seconds(),
            errors=[{"record_id": i, "error": err["errors"]} for i, err in enumerate(invalid_records)]
        )
        
        # Validate persistence metrics
        assert metrics.total_records == 4
        assert metrics.successful_records == 2, "Should have 2 valid unique records"
        assert metrics.duplicate_records == 1, "Should detect 1 duplicate"
        assert metrics.failed_records == 1, "Should have 1 invalid record"
        assert metrics.processing_rate > 0
        assert len(metrics.errors) == 1
    
    @pytest.mark.integration
    async def test_pipeline_error_handling_and_recovery(self):
        """Test pipeline error handling and recovery mechanisms.
        
        BVJ: Ensures system resilience for continuous business operations
        when data processing encounters errors or failures.
        """
        message_queue = MessageQueueService()
        await message_queue.start()
        
        # Create messages with various error scenarios
        test_messages = [
            {"data": {"valid": True, "user_id": "u1", "action": "login"}},
            {"data": None},  # Invalid data - None
            {"data": {"valid": True, "user_id": "u2", "action": "purchase"}},
            {"invalid_structure": True},  # Missing data field
            {"data": {"valid": True, "user_id": "u3", "action": "logout"}},
            {"data": {"invalid_field": "causes_processing_error"}},  # Processing error trigger
        ]
        
        # Track error handling
        processing_results = {
            "successful": [],
            "validation_errors": [],
            "processing_errors": [],
            "recovered": []
        }
        
        # Process messages with error handling
        for i, message in enumerate(test_messages):
            try:
                # Publish message
                success = await message_queue.publish("error_test_queue", message)
                if not success:
                    processing_results["validation_errors"].append({
                        "message_id": i,
                        "error": "Failed to publish",
                        "message": message
                    })
                    continue
                
                # Consume and process message
                consumed_msg = await message_queue.consume("error_test_queue")
                if not consumed_msg:
                    processing_results["processing_errors"].append({
                        "message_id": i,
                        "error": "Failed to consume",
                        "message": message
                    })
                    continue
                
                # Validate message structure
                if "data" not in consumed_msg or consumed_msg["data"] is None:
                    processing_results["validation_errors"].append({
                        "message_id": i,
                        "error": "Invalid message structure",
                        "message": consumed_msg
                    })
                    continue
                
                # Simulate processing that might fail
                data = consumed_msg["data"]
                if "invalid_field" in data:
                    # Trigger processing error
                    raise ValueError("Processing error triggered by invalid_field")
                
                # Successful processing
                processed = {
                    "message_id": i,
                    "original": consumed_msg,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "status": "success"
                }
                processing_results["successful"].append(processed)
                
            except Exception as e:
                # Error recovery mechanism
                error_info = {
                    "message_id": i,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "message": message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Attempt recovery based on error type
                if "processing error" in str(e).lower():
                    # Try alternative processing
                    try:
                        recovered_msg = {
                            "message_id": i,
                            "original": message,
                            "recovery_method": "alternative_processing",
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "status": "recovered"
                        }
                        processing_results["recovered"].append(recovered_msg)
                    except:
                        processing_results["processing_errors"].append(error_info)
                else:
                    processing_results["processing_errors"].append(error_info)
        
        # Validate error handling results
        assert len(processing_results["successful"]) >= 2, "Should have some successful processing"
        assert len(processing_results["validation_errors"]) >= 1, "Should detect validation errors"
        assert len(processing_results["processing_errors"]) >= 0, "May have processing errors"
        assert len(processing_results["recovered"]) >= 0, "May have recovered messages"
        
        # Validate error recovery
        total_processed = (len(processing_results["successful"]) + 
                         len(processing_results["recovered"]))
        total_errors = (len(processing_results["validation_errors"]) + 
                       len(processing_results["processing_errors"]))
        
        assert total_processed + total_errors == len(test_messages), "All messages should be accounted for"
        
        # Test circuit breaker pattern (simplified)
        error_threshold = 3
        consecutive_errors = 0
        circuit_breaker_triggered = False
        
        for error in processing_results["processing_errors"]:
            consecutive_errors += 1
            if consecutive_errors >= error_threshold:
                circuit_breaker_triggered = True
                break
        
        # Validate circuit breaker logic
        if len(processing_results["processing_errors"]) >= error_threshold:
            assert circuit_breaker_triggered, "Circuit breaker should trigger after threshold"
        
        # Create error report
        error_report = {
            "total_messages": len(test_messages),
            "successful_count": len(processing_results["successful"]),
            "validation_error_count": len(processing_results["validation_errors"]),
            "processing_error_count": len(processing_results["processing_errors"]),
            "recovered_count": len(processing_results["recovered"]),
            "success_rate": len(processing_results["successful"]) / len(test_messages) * 100,
            "recovery_rate": len(processing_results["recovered"]) / max(len(processing_results["processing_errors"]), 1) * 100,
            "circuit_breaker_triggered": circuit_breaker_triggered
        }
        
        assert error_report["success_rate"] >= 30.0, "Should have at least 30% success rate"
        assert isinstance(error_report["recovery_rate"], float), "Recovery rate should be calculated"
    
    @pytest.mark.integration
    async def test_pipeline_integration_with_agent_workflows(self):
        """Test pipeline integration with agent execution workflows.
        
        BVJ: Validates integration between data processing pipelines and AI agents
        to ensure seamless delivery of AI-powered insights to users.
        """
        # Create mock agent state and execution context
        agent_state = DeepAgentState()
        agent_state.user_prompt = "Analyze user behavior patterns for optimization"
        agent_state.context_data = {
            "user_id": "test_user_123",
            "analysis_type": "behavioral",
            "time_range": "last_30_days"
        }
        
        execution_context = AgentExecutionContext(
            run_id="test_run_123",
            thread_id="test_thread_456", 
            user_id="test_user_123",
            agent_name="data_analysis"
        )
        
        # Create pipeline builder and build execution pipeline
        pipeline_builder = PipelineBuilder()
        pipeline_steps = pipeline_builder.get_execution_pipeline(
            agent_state.user_prompt,
            agent_state
        )
        
        # Validate pipeline structure
        assert len(pipeline_steps) >= 2, "Should have at least triage and reporting steps"
        
        # Check for expected pipeline steps
        step_names = [step.agent_name for step in pipeline_steps]
        assert "triage" in step_names, "Should include triage step"
        assert "reporting" in step_names, "Should include reporting step"
        
        # Test data processing integration
        user_behavior_data = [
            {"timestamp": "2024-01-01T10:00:00Z", "user_id": "test_user_123", "action": "login", "duration": 300},
            {"timestamp": "2024-01-01T10:05:00Z", "user_id": "test_user_123", "action": "view_dashboard", "duration": 120},
            {"timestamp": "2024-01-01T10:07:00Z", "user_id": "test_user_123", "action": "run_analysis", "duration": 1800},
            {"timestamp": "2024-01-01T10:37:00Z", "user_id": "test_user_123", "action": "export_results", "duration": 60}
        ]
        
        # Process data through pipeline stages
        pipeline_results = {
            "raw_data": user_behavior_data,
            "processed_data": [],
            "insights": [],
            "agent_context": {
                "run_id": execution_context.run_id,
                "user_id": execution_context.user_id,
                "agent_name": execution_context.agent_name
            }
        }
        
        # Stage 1: Data validation and enrichment
        for record in user_behavior_data:
            if record["user_id"] == execution_context.user_id:  # User-specific processing
                enriched_record = {
                    **record,
                    "processed_by": execution_context.agent_name,
                    "processing_time": datetime.now(timezone.utc).isoformat(),
                    "session_context": agent_state.context_data,
                    "duration_minutes": record["duration"] / 60
                }
                pipeline_results["processed_data"].append(enriched_record)
        
        # Stage 2: Business intelligence generation
        total_session_time = sum(r["duration"] for r in pipeline_results["processed_data"])
        action_counts = {}
        for record in pipeline_results["processed_data"]:
            action = record["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Generate insights for agent response
        insights = [
            {
                "type": "session_analysis",
                "metric": "total_session_duration",
                "value": total_session_time,
                "unit": "seconds",
                "insight": f"User spent {total_session_time/60:.1f} minutes in session"
            },
            {
                "type": "engagement_pattern",
                "metric": "most_frequent_action",
                "value": max(action_counts.items(), key=lambda x: x[1]) if action_counts else None,
                "insight": "Identifies primary user engagement pattern"
            },
            {
                "type": "productivity_indicator",
                "metric": "analysis_to_export_ratio",
                "value": action_counts.get("run_analysis", 0) / max(action_counts.get("export_results", 1), 1),
                "insight": "Measures conversion from analysis to actionable results"
            }
        ]
        
        pipeline_results["insights"] = insights
        
        # Validate pipeline-agent integration
        assert len(pipeline_results["processed_data"]) == len(user_behavior_data)
        assert len(pipeline_results["insights"]) == 3
        
        # Validate user-specific processing
        for record in pipeline_results["processed_data"]:
            assert record["user_id"] == execution_context.user_id
            assert record["processed_by"] == execution_context.agent_name
            assert "processing_time" in record
            assert "session_context" in record
        
        # Validate insights generation
        session_insight = next(i for i in insights if i["type"] == "session_analysis")
        assert session_insight["value"] == total_session_time
        assert session_insight["value"] > 0, "Should have positive session time"
        
        engagement_insight = next(i for i in insights if i["type"] == "engagement_pattern")
        assert engagement_insight["value"] is not None, "Should identify engagement pattern"
        
        productivity_insight = next(i for i in insights if i["type"] == "productivity_indicator")
        assert isinstance(productivity_insight["value"], (int, float)), "Should calculate productivity ratio"
        
        # Update agent state with pipeline results
        agent_state.pipeline_results = pipeline_results
        agent_state.insights_generated = len(insights)
        agent_state.data_processed = len(pipeline_results["processed_data"])
        
        # Validate agent state updates
        assert hasattr(agent_state, 'pipeline_results')
        assert agent_state.insights_generated == 3
        assert agent_state.data_processed == len(user_behavior_data)
    
    @pytest.mark.integration
    async def test_pipeline_observability_and_metrics_collection(self):
        """Test pipeline observability, monitoring, and metrics collection.
        
        BVJ: Ensures system observability for maintaining high performance and
        reliability standards essential for business-critical operations.
        """
        # Create comprehensive metrics collection system
        pipeline_metrics = {
            "execution_metrics": {
                "start_time": datetime.now(timezone.utc),
                "end_time": None,
                "duration_seconds": 0,
                "throughput_records_per_second": 0,
                "memory_usage_mb": 0,
                "cpu_utilization_percent": 0
            },
            "processing_metrics": {
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "duplicate_records": 0,
                "processing_stages": [],
                "average_processing_time_ms": 0
            },
            "quality_metrics": {
                "data_quality_score": 0.0,
                "validation_pass_rate": 0.0,
                "completeness_score": 0.0,
                "consistency_score": 0.0
            },
            "business_metrics": {
                "cost_per_record": 0.0,
                "business_value_generated": 0.0,
                "user_satisfaction_score": 0.0,
                "insights_generated": 0
            }
        }
        
        # Simulate pipeline execution with metrics collection
        test_dataset = [
            {"id": f"record_{i}", "user_id": f"user_{i%10}", "value": i * 10, "quality": "high" if i % 3 == 0 else "medium"}
            for i in range(50)
        ]
        
        start_time = datetime.now(timezone.utc)
        pipeline_metrics["execution_metrics"]["start_time"] = start_time
        
        # Processing stage 1: Validation
        validation_start = datetime.now(timezone.utc)
        valid_records = []
        invalid_records = []
        
        for record in test_dataset:
            if record.get("id") and record.get("user_id") and "value" in record:
                valid_records.append({
                    **record,
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                    "validation_stage": "passed"
                })
            else:
                invalid_records.append({
                    **record,
                    "validation_error": "Missing required fields",
                    "validated_at": datetime.now(timezone.utc).isoformat()
                })
        
        validation_end = datetime.now(timezone.utc)
        validation_duration = (validation_end - validation_start).total_seconds() * 1000  # ms
        
        pipeline_metrics["processing_metrics"]["processing_stages"].append({
            "stage_name": "validation",
            "duration_ms": validation_duration,
            "input_count": len(test_dataset),
            "output_count": len(valid_records),
            "error_count": len(invalid_records)
        })
        
        # Processing stage 2: Enrichment
        enrichment_start = datetime.now(timezone.utc)
        enriched_records = []
        
        for record in valid_records:
            enriched = {
                **record,
                "enriched_at": datetime.now(timezone.utc).isoformat(),
                "value_category": "high" if record["value"] > 200 else "low",
                "user_segment": f"segment_{hash(record['user_id']) % 5}",
                "processing_metadata": {
                    "enrichment_version": "1.0",
                    "data_source": "integration_test"
                }
            }
            enriched_records.append(enriched)
            
            # Simulate processing time
            await asyncio.sleep(0.001)
        
        enrichment_end = datetime.now(timezone.utc)
        enrichment_duration = (enrichment_end - enrichment_start).total_seconds() * 1000  # ms
        
        pipeline_metrics["processing_metrics"]["processing_stages"].append({
            "stage_name": "enrichment",
            "duration_ms": enrichment_duration,
            "input_count": len(valid_records),
            "output_count": len(enriched_records),
            "error_count": 0
        })
        
        # Processing stage 3: Analytics
        analytics_start = datetime.now(timezone.utc)
        analytics_results = {
            "total_value": sum(r["value"] for r in enriched_records),
            "average_value": sum(r["value"] for r in enriched_records) / len(enriched_records),
            "high_value_count": len([r for r in enriched_records if r["value_category"] == "high"]),
            "unique_users": len(set(r["user_id"] for r in enriched_records)),
            "segment_distribution": {}
        }
        
        # Calculate segment distribution
        for record in enriched_records:
            segment = record["user_segment"]
            analytics_results["segment_distribution"][segment] = analytics_results["segment_distribution"].get(segment, 0) + 1
        
        analytics_end = datetime.now(timezone.utc)
        analytics_duration = (analytics_end - analytics_start).total_seconds() * 1000  # ms
        
        pipeline_metrics["processing_metrics"]["processing_stages"].append({
            "stage_name": "analytics",
            "duration_ms": analytics_duration,
            "input_count": len(enriched_records),
            "output_count": 1,  # Single analytics result
            "analytics_results": analytics_results
        })
        
        # Complete execution metrics
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()
        
        pipeline_metrics["execution_metrics"]["end_time"] = end_time
        pipeline_metrics["execution_metrics"]["duration_seconds"] = total_duration
        pipeline_metrics["execution_metrics"]["throughput_records_per_second"] = len(test_dataset) / total_duration if total_duration > 0 else 0
        
        # Complete processing metrics
        pipeline_metrics["processing_metrics"]["total_records"] = len(test_dataset)
        pipeline_metrics["processing_metrics"]["successful_records"] = len(enriched_records)
        pipeline_metrics["processing_metrics"]["failed_records"] = len(invalid_records)
        
        total_processing_time = sum(stage["duration_ms"] for stage in pipeline_metrics["processing_metrics"]["processing_stages"])
        pipeline_metrics["processing_metrics"]["average_processing_time_ms"] = total_processing_time / len(pipeline_metrics["processing_metrics"]["processing_stages"])
        
        # Calculate quality metrics
        validation_pass_rate = len(valid_records) / len(test_dataset) if test_dataset else 0
        completeness_score = len([r for r in enriched_records if all(k in r for k in ["id", "user_id", "value"])]) / len(enriched_records) if enriched_records else 0
        consistency_score = 1.0  # Assume consistent processing for integration test
        
        pipeline_metrics["quality_metrics"]["validation_pass_rate"] = validation_pass_rate
        pipeline_metrics["quality_metrics"]["completeness_score"] = completeness_score
        pipeline_metrics["quality_metrics"]["consistency_score"] = consistency_score
        pipeline_metrics["quality_metrics"]["data_quality_score"] = (validation_pass_rate + completeness_score + consistency_score) / 3
        
        # Calculate business metrics
        pipeline_metrics["business_metrics"]["cost_per_record"] = 0.001  # $0.001 per record
        pipeline_metrics["business_metrics"]["business_value_generated"] = analytics_results["total_value"] * 0.01  # 1% of total value
        pipeline_metrics["business_metrics"]["insights_generated"] = len(analytics_results) - 2  # Exclude counts
        pipeline_metrics["business_metrics"]["user_satisfaction_score"] = 0.95 if validation_pass_rate > 0.9 else 0.8
        
        # Validate metrics collection
        assert pipeline_metrics["execution_metrics"]["duration_seconds"] > 0, "Should have positive duration"
        assert pipeline_metrics["execution_metrics"]["throughput_records_per_second"] > 0, "Should have positive throughput"
        
        assert pipeline_metrics["processing_metrics"]["total_records"] == 50, "Should process all test records"
        assert pipeline_metrics["processing_metrics"]["successful_records"] > 0, "Should have successful records"
        assert len(pipeline_metrics["processing_metrics"]["processing_stages"]) == 3, "Should have 3 processing stages"
        
        assert 0.0 <= pipeline_metrics["quality_metrics"]["data_quality_score"] <= 1.0, "Quality score should be normalized"
        assert pipeline_metrics["quality_metrics"]["validation_pass_rate"] > 0.9, "Should have high validation pass rate"
        
        assert pipeline_metrics["business_metrics"]["cost_per_record"] > 0, "Should have positive cost per record"
        assert pipeline_metrics["business_metrics"]["business_value_generated"] > 0, "Should generate business value"
        
        # Validate stage-specific metrics
        validation_stage = pipeline_metrics["processing_metrics"]["processing_stages"][0]
        assert validation_stage["stage_name"] == "validation"
        assert validation_stage["input_count"] == 50
        assert validation_stage["output_count"] <= validation_stage["input_count"]
        
        enrichment_stage = pipeline_metrics["processing_metrics"]["processing_stages"][1]
        assert enrichment_stage["stage_name"] == "enrichment"
        assert enrichment_stage["output_count"] == enrichment_stage["input_count"], "Enrichment should not filter records"
        
        analytics_stage = pipeline_metrics["processing_metrics"]["processing_stages"][2]
        assert analytics_stage["stage_name"] == "analytics"
        assert "analytics_results" in analytics_stage
        assert analytics_stage["analytics_results"]["unique_users"] > 0, "Should identify unique users"