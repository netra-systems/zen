"""
Integration Tests: EventValidator Validation Consistency Integration

PURPOSE: Test validation consistency across EventValidator implementations with real services
EXPECTATION: Tests should FAIL initially to demonstrate validation inconsistencies

Business Value Justification (BVJ):
- Segment: Platform/Internal - Integration Testing
- Business Goal: Revenue Protection - Ensure consistent validation with real data
- Value Impact: Protects $500K+ ARR by exposing validation inconsistencies in real scenarios
- Strategic Impact: Validates real-world validation behavior differences

These tests are designed to FAIL initially, demonstrating:
1. Different validation outcomes for the same real event data
2. Inconsistent error handling with real services
3. Different timeout/performance characteristics
4. Inconsistent business value scoring

Test Plan Phase 2: Integration Tests (Real Services, No Docker)
- Test validation consistency with real PostgreSQL data
- Test validation consistency with real Redis caching
- Test real WebSocket event validation differences
- Test real agent execution validation differences

NOTE: Uses real services but no Docker to avoid Docker dependencies
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from unittest.mock import patch, MagicMock

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import real service utilities
from test_framework.database_test_utilities import DatabaseTestUtilities
from shared.isolated_environment import get_env

# CRITICAL: These imports should expose validation inconsistencies in real scenarios
try:
    # Unified implementation (consolidated SSOT)
    from netra_backend.app.websocket_core.event_validator import (
        UnifiedEventValidator,
        ValidationResult as UnifiedValidationResult,
        WebSocketEventMessage as UnifiedWebSocketEventMessage,
        get_websocket_validator as get_unified_validator
    )
    unified_available = True
except ImportError as e:
    unified_available = False
    unified_import_error = str(e)

try:
    # Production implementation (legacy)
    from netra_backend.app.services.websocket_error_validator import (
        WebSocketEventValidator as ProductionEventValidator,
        ValidationResult as ProductionValidationResult,
        get_websocket_validator as get_production_validator
    )
    production_available = True
except ImportError as e:
    production_available = False
    production_import_error = str(e)

try:
    # SSOT Framework implementation (legacy)
    from netra_backend.app.websocket_core.event_validator import (
        AgentEventValidator as SsotFrameworkEventValidator,
        AgentEventValidationResult as SsotFrameworkValidationResult,
        validate_agent_events as ssot_validate_agent_events
    )
    ssot_framework_available = True
except ImportError as e:
    ssot_framework_available = False
    ssot_framework_import_error = str(e)


class TestValidationConsistencyIntegration(SSotAsyncTestCase):
    """
    Integration tests for EventValidator validation consistency with real services.
    
    DESIGNED TO FAIL: These tests expose validation inconsistencies between implementations
    when using real service data and scenarios.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures with real services."""
        await super().asyncSetUp()
        
        # Initialize database utility for real data
        self.db_utility = DatabaseTestUtilities()
        self.env = get_env()
        
        # Track import availability
        self.import_status = {
            "unified": unified_available,
            "production": production_available, 
            "ssot_framework": ssot_framework_available
        }
        
        # Generate real test data
        self.test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"test-thread-{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"test-run-{uuid.uuid4().hex[:8]}"
        self.test_agent_name = "supervisor-agent"
        self.test_tool_name = "data-collector"
        
        # Real event sequence based on actual agent execution
        self.real_event_sequence = self._create_real_event_sequence()
        
    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await super().asyncTearDown()
        
    def _create_real_event_sequence(self) -> List[Dict[str, Any]]:
        """Create realistic event sequence based on actual agent execution patterns."""
        base_time = datetime.now(timezone.utc)
        
        return [
            {
                "type": "agent_started",
                "run_id": self.test_run_id,
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": base_time.isoformat(),
                "payload": {
                    "agent": self.test_agent_name,
                    "status": "started",
                    "workflow": "data_analysis",
                    "context": {"user_request": "Analyze optimization opportunities"}
                }
            },
            {
                "type": "agent_thinking", 
                "run_id": self.test_run_id,
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": (base_time.replace(second=base_time.second + 2)).isoformat(),
                "payload": {
                    "agent": self.test_agent_name,
                    "progress": "analyzing_request",
                    "reasoning": "Evaluating data requirements for optimization analysis"
                }
            },
            {
                "type": "tool_executing",
                "run_id": self.test_run_id,
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": (base_time.replace(second=base_time.second + 5)).isoformat(),
                "payload": {
                    "tool": self.test_tool_name,
                    "status": "executing",
                    "operation": "collect_metrics_data",
                    "parameters": {"time_range": "7d", "metrics": ["cpu", "memory", "latency"]}
                }
            },
            {
                "type": "tool_completed",
                "run_id": self.test_run_id,
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": (base_time.replace(second=base_time.second + 12)).isoformat(),
                "payload": {
                    "tool": self.test_tool_name,
                    "status": "completed",
                    "result": {
                        "data_points": 1440,
                        "avg_cpu": 65.2,
                        "avg_memory": 78.5,
                        "avg_latency": 145.3
                    },
                    "execution_time": 7.2
                }
            },
            {
                "type": "agent_completed",
                "run_id": self.test_run_id,
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": (base_time.replace(second=base_time.second + 15)).isoformat(),
                "payload": {
                    "agent": self.test_agent_name,
                    "status": "completed",
                    "result": {
                        "optimization_opportunities": 3,
                        "potential_savings": "25% latency reduction",
                        "confidence": 0.87
                    },
                    "total_execution_time": 15.2
                }
            }
        ]
    
    async def test_real_event_sequence_validation_consistency(self):
        """
        TEST DESIGNED TO FAIL: Should expose validation differences for real event sequences.
        
        Expected failure: Different implementations may validate the same real event sequence
        differently, demonstrating validation inconsistencies.
        """
        validation_results = {}
        
        # Test unified implementation
        if unified_available:
            try:
                validator = UnifiedEventValidator(strict_mode=True, timeout_seconds=30.0)
                
                # Validate each event individually
                individual_results = []
                for event in self.real_event_sequence:
                    result = validator.validate_event(event, self.test_user_id)
                    individual_results.append({
                        "event_type": event["type"],
                        "is_valid": result.is_valid,
                        "error_message": result.error_message,
                        "criticality": getattr(result, "criticality", None)
                    })
                    
                    # Also record for full validation
                    validator.record_event(event)
                
                # Perform full validation
                full_result = validator.perform_full_validation()
                
                validation_results["unified"] = {
                    "individual_results": individual_results,
                    "full_validation": {
                        "is_valid": full_result.is_valid,
                        "missing_critical_events": list(full_result.missing_critical_events),
                        "business_value_score": full_result.business_value_score,
                        "revenue_impact": full_result.revenue_impact,
                        "error_message": full_result.error_message
                    }
                }
                
            except Exception as e:
                validation_results["unified"] = {"error": str(e)}
        
        # Test production implementation
        if production_available:
            try:
                validator = ProductionEventValidator()
                
                # Validate each event individually
                individual_results = []
                for event in self.real_event_sequence:
                    result = validator.validate_event(event, self.test_user_id)
                    individual_results.append({
                        "event_type": event["type"],
                        "is_valid": result.is_valid,
                        "error_message": result.error_message,
                        "criticality": getattr(result, "criticality", None)
                    })
                
                validation_results["production"] = {
                    "individual_results": individual_results,
                    "full_validation": {
                        "note": "Production validator doesn't support full validation",
                        "stats": validator.get_validation_stats()
                    }
                }
                
            except Exception as e:
                validation_results["production"] = {"error": str(e)}
        
        # Test SSOT framework implementation  
        if ssot_framework_available:
            try:
                # Use convenience function for SSOT framework
                full_result = ssot_validate_agent_events(
                    self.real_event_sequence,
                    strict_mode=True
                )
                
                validation_results["ssot_framework"] = {
                    "individual_results": "Not available in SSOT framework",
                    "full_validation": {
                        "is_valid": full_result.is_valid,
                        "missing_critical_events": list(full_result.missing_critical_events),
                        "business_value_score": full_result.business_value_score,
                        "revenue_impact": full_result.revenue_impact,
                        "error_message": full_result.error_message
                    }
                }
                
            except Exception as e:
                validation_results["ssot_framework"] = {"error": str(e)}
        
        # Check for validation consistency - this should FAIL initially
        successful_validations = [
            impl for impl, result in validation_results.items()
            if "error" not in result
        ]
        
        if len(successful_validations) > 1:
            # Compare individual validation results
            individual_inconsistencies = []
            
            for event_idx, event in enumerate(self.real_event_sequence):
                event_type = event["type"]
                event_results = {}
                
                for impl in successful_validations:
                    result = validation_results[impl]
                    individual = result.get("individual_results")
                    
                    if isinstance(individual, list) and event_idx < len(individual):
                        event_results[impl] = individual[event_idx]["is_valid"]
                
                # Check for inconsistencies
                if len(set(event_results.values())) > 1:
                    individual_inconsistencies.append({
                        "event_type": event_type,
                        "event_index": event_idx,
                        "results": event_results
                    })
            
            if individual_inconsistencies:
                self.fail(
                    f"SSOT VIOLATION: Individual event validation inconsistencies found: "
                    f"{individual_inconsistencies}. "
                    f"Full validation results: {validation_results}. "
                    f"Same real events should produce consistent validation outcomes!"
                )
            
            # Compare full validation results
            full_validation_results = {}
            for impl in successful_validations:
                result = validation_results[impl]
                full_val = result.get("full_validation", {})
                
                if "is_valid" in full_val:
                    full_validation_results[impl] = {
                        "is_valid": full_val["is_valid"],
                        "business_value_score": full_val.get("business_value_score", 0),
                        "revenue_impact": full_val.get("revenue_impact", "UNKNOWN")
                    }
            
            # Check for full validation inconsistencies
            if len(full_validation_results) > 1:
                is_valid_values = [result["is_valid"] for result in full_validation_results.values()]
                business_scores = [result["business_value_score"] for result in full_validation_results.values()]
                revenue_impacts = [result["revenue_impact"] for result in full_validation_results.values()]
                
                if len(set(is_valid_values)) > 1:
                    self.fail(
                        f"SSOT VIOLATION: Full validation is_valid inconsistency: {full_validation_results}. "
                        f"Same real event sequence should produce consistent validation outcomes!"
                    )
                
                if len(set(business_scores)) > 1:
                    score_diff = max(business_scores) - min(business_scores)
                    if score_diff > 5.0:  # Allow small rounding differences
                        self.fail(
                            f"SSOT VIOLATION: Business value score inconsistency: {full_validation_results}. "
                            f"Score difference: {score_diff}%. Same events should produce same business value!"
                        )
    
    async def test_real_database_event_validation_with_persistence(self):
        """
        TEST DESIGNED TO FAIL: Should expose validation differences when using real database data.
        
        Expected failure: Different implementations may handle database-persisted events differently,
        demonstrating data integration inconsistencies.
        """
        # Skip if database not available
        if not await self.db_utility.is_database_available():
            self.skipTest("Database not available for integration testing")
        
        validation_results = {}
        
        # Create test data in database (simulating real persisted events)
        test_events = [
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "agent_started",
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "event_data": self.real_event_sequence[0],
                "created_at": datetime.now(timezone.utc)
            },
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "agent_completed",
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "run_id": self.test_run_id,
                "event_data": self.real_event_sequence[-1],
                "created_at": datetime.now(timezone.utc)
            }
        ]
        
        # Insert test events into database
        try:
            await self.db_utility.insert_test_events(test_events)
            
            # Retrieve events from database
            retrieved_events = await self.db_utility.get_events_for_run(self.test_run_id)
            
            # Test validation with database-retrieved events
            for impl_name in ["unified", "production"]:
                if not self.import_status[impl_name]:
                    continue
                    
                try:
                    if impl_name == "unified":
                        validator = UnifiedEventValidator()
                    elif impl_name == "production":
                        validator = ProductionEventValidator()
                    
                    db_validation_results = []
                    for event_record in retrieved_events:
                        event_data = event_record["event_data"]
                        result = validator.validate_event(event_data, self.test_user_id)
                        
                        db_validation_results.append({
                            "event_id": event_record["event_id"],
                            "event_type": event_data["type"],
                            "is_valid": result.is_valid,
                            "error_message": result.error_message
                        })
                    
                    validation_results[impl_name] = {
                        "db_results": db_validation_results,
                        "total_events": len(retrieved_events)
                    }
                    
                except Exception as e:
                    validation_results[impl_name] = {"error": str(e)}
            
            # Check for database validation consistency - this should FAIL initially
            successful_validations = [
                impl for impl, result in validation_results.items()
                if "error" not in result
            ]
            
            if len(successful_validations) > 1:
                # Compare validation results for same database events
                for event_idx in range(len(retrieved_events)):
                    event_id = retrieved_events[event_idx]["event_id"]
                    event_results = {}
                    
                    for impl in successful_validations:
                        result = validation_results[impl]
                        db_results = result.get("db_results", [])
                        
                        if event_idx < len(db_results):
                            event_results[impl] = db_results[event_idx]["is_valid"]
                    
                    # Check for inconsistencies
                    if len(set(event_results.values())) > 1:
                        self.fail(
                            f"SSOT VIOLATION: Database event validation inconsistency for event {event_id}: "
                            f"{event_results}. "
                            f"Full validation results: {validation_results}. "
                            f"Same database-persisted events should produce consistent validation!"
                        )
            
        finally:
            # Clean up test data
            await self.db_utility.cleanup_test_events(self.test_run_id)
    
    async def test_real_websocket_connection_validation_differences(self):
        """
        TEST DESIGNED TO FAIL: Should expose differences in WebSocket connection validation.
        
        Expected failure: Different implementations may validate WebSocket connections differently,
        demonstrating connection handling inconsistencies.
        """
        validation_results = {}
        
        # Mock WebSocket manager for testing connection validation
        mock_websocket_manager = MagicMock()
        mock_websocket_manager.is_connection_active.return_value = True
        
        test_connection_scenarios = [
            {
                "name": "active_connection",
                "user_id": self.test_user_id,
                "connection_id": f"ws-{uuid.uuid4().hex[:8]}",
                "websocket_manager": mock_websocket_manager,
                "expected_valid": True
            },
            {
                "name": "inactive_connection",
                "user_id": self.test_user_id,
                "connection_id": f"ws-{uuid.uuid4().hex[:8]}",
                "websocket_manager": None,  # No manager = connection issues
                "expected_valid": False
            },
            {
                "name": "invalid_user_id",
                "user_id": "",  # Empty user ID
                "connection_id": f"ws-{uuid.uuid4().hex[:8]}",
                "websocket_manager": mock_websocket_manager,
                "expected_valid": False
            }
        ]
        
        # Test connection validation across implementations
        for impl_name in ["unified", "production"]:
            if not self.import_status[impl_name]:
                continue
                
            try:
                if impl_name == "unified":
                    validator = UnifiedEventValidator()
                elif impl_name == "production":
                    validator = ProductionEventValidator()
                
                # Test connection validation if method exists
                if hasattr(validator, "validate_connection_ready"):
                    connection_results = []
                    
                    for scenario in test_connection_scenarios:
                        result = validator.validate_connection_ready(
                            scenario["user_id"],
                            scenario["connection_id"],
                            scenario["websocket_manager"]
                        )
                        
                        connection_results.append({
                            "scenario": scenario["name"],
                            "is_valid": result.is_valid,
                            "error_message": result.error_message,
                            "expected_valid": scenario["expected_valid"]
                        })
                    
                    validation_results[impl_name] = {
                        "connection_results": connection_results,
                        "has_connection_validation": True
                    }
                else:
                    validation_results[impl_name] = {
                        "connection_results": [],
                        "has_connection_validation": False
                    }
                    
            except Exception as e:
                validation_results[impl_name] = {"error": str(e)}
        
        # Check for connection validation consistency - this should FAIL initially
        successful_validations = [
            impl for impl, result in validation_results.items()
            if "error" not in result
        ]
        
        if len(successful_validations) > 1:
            # Check if all implementations have connection validation
            has_connection_validation = [
                validation_results[impl]["has_connection_validation"]
                for impl in successful_validations
            ]
            
            if not all(has_connection_validation):
                implementations_with_validation = [
                    impl for impl in successful_validations
                    if validation_results[impl]["has_connection_validation"]
                ]
                implementations_without_validation = [
                    impl for impl in successful_validations
                    if not validation_results[impl]["has_connection_validation"]
                ]
                
                self.fail(
                    f"SSOT VIOLATION: Connection validation availability inconsistency. "
                    f"With validation: {implementations_with_validation}. "
                    f"Without validation: {implementations_without_validation}. "
                    f"All implementations should have consistent connection validation capabilities!"
                )
            
            # Compare connection validation results
            implementations_with_validation = [
                impl for impl in successful_validations
                if validation_results[impl]["has_connection_validation"]
            ]
            
            if len(implementations_with_validation) > 1:
                for scenario_idx, scenario in enumerate(test_connection_scenarios):
                    scenario_results = {}
                    
                    for impl in implementations_with_validation:
                        result = validation_results[impl]
                        connection_results = result.get("connection_results", [])
                        
                        if scenario_idx < len(connection_results):
                            scenario_results[impl] = connection_results[scenario_idx]["is_valid"]
                    
                    # Check for scenario inconsistencies
                    if len(set(scenario_results.values())) > 1:
                        self.fail(
                            f"SSOT VIOLATION: Connection validation inconsistency for scenario '{scenario['name']}': "
                            f"{scenario_results}. "
                            f"Full validation results: {validation_results}. "
                            f"Same connection scenarios should produce consistent validation!"
                        )
    
    async def test_real_performance_characteristics_consistency(self):
        """
        TEST DESIGNED TO FAIL: Should expose performance differences between implementations.
        
        Expected failure: Different implementations may have significantly different performance,
        demonstrating optimization inconsistencies.
        """
        performance_results = {}
        
        # Create larger event dataset for performance testing
        large_event_sequence = []
        for i in range(100):  # 100 events per implementation
            event = self.real_event_sequence[i % len(self.real_event_sequence)].copy()
            event["run_id"] = f"{self.test_run_id}-{i}"
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
            large_event_sequence.append(event)
        
        # Test performance across implementations
        for impl_name in ["unified", "production"]:
            if not self.import_status[impl_name]:
                continue
                
            try:
                if impl_name == "unified":
                    validator = UnifiedEventValidator()
                elif impl_name == "production":
                    validator = ProductionEventValidator()
                
                # Measure validation performance
                start_time = time.time()
                validation_count = 0
                validation_errors = 0
                
                for event in large_event_sequence:
                    try:
                        result = validator.validate_event(event, self.test_user_id)
                        validation_count += 1
                        if not result.is_valid:
                            validation_errors += 1
                    except Exception:
                        validation_errors += 1
                
                end_time = time.time()
                total_time = end_time - start_time
                
                performance_results[impl_name] = {
                    "total_time": total_time,
                    "events_processed": validation_count,
                    "validation_errors": validation_errors,
                    "events_per_second": validation_count / total_time if total_time > 0 else 0,
                    "average_time_per_event": total_time / validation_count if validation_count > 0 else 0
                }
                
            except Exception as e:
                performance_results[impl_name] = {"error": str(e)}
        
        # Check for performance consistency - this should FAIL initially
        successful_validations = [
            impl for impl, result in performance_results.items()
            if "error" not in result
        ]
        
        if len(successful_validations) > 1:
            # Compare performance metrics
            events_per_second = [
                performance_results[impl]["events_per_second"]
                for impl in successful_validations
            ]
            
            avg_time_per_event = [
                performance_results[impl]["average_time_per_event"]
                for impl in successful_validations
            ]
            
            # Check for significant performance differences
            if max(events_per_second) > 0 and min(events_per_second) > 0:
                performance_ratio = max(events_per_second) / min(events_per_second)
                
                if performance_ratio > 2.0:  # More than 2x difference
                    self.fail(
                        f"SSOT VIOLATION: Significant performance difference between implementations. "
                        f"Performance results: {performance_results}. "
                        f"Performance ratio: {performance_ratio:.2f}x. "
                        f"Implementations should have similar performance characteristics!"
                    )
            
            # Check for validation error consistency
            validation_error_counts = [
                performance_results[impl]["validation_errors"]
                for impl in successful_validations
            ]
            
            if len(set(validation_error_counts)) > 1:
                self.fail(
                    f"SSOT VIOLATION: Validation error count inconsistency: "
                    f"{dict(zip(successful_validations, validation_error_counts))}. "
                    f"Full performance results: {performance_results}. "
                    f"Same events should produce same number of validation errors!"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])