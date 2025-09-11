"""
Integration Tests: Production EventValidator Detection and Analysis

PURPOSE: Detect and analyze production EventValidator usage patterns and inconsistencies
EXPECTATION: Tests should FAIL initially to demonstrate production usage conflicts

Business Value Justification (BVJ):
- Segment: Platform/Internal - Production Analysis
- Business Goal: Revenue Protection - Detect production validation inconsistencies
- Value Impact: Protects $500K+ ARR by identifying production validation issues
- Strategic Impact: Validates production impact of SSOT consolidation

These tests are designed to FAIL initially, demonstrating:
1. Multiple production EventValidator instances in use
2. Inconsistent production validation patterns
3. Production performance issues with multiple validators
4. Production error patterns from validator conflicts

Test Plan Phase 2b: Production Validator Detection (Real Services, No Docker)
- Test production validator instance detection
- Test production validation pattern analysis
- Test production error pattern detection
- Test production performance impact analysis

NOTE: Uses real services to detect actual production patterns
"""

import pytest
import asyncio
import time
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from unittest.mock import patch, MagicMock
from collections import defaultdict

# Import test framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import real service utilities
from test_framework.database_test_utilities import DatabaseTestUtilities
from shared.isolated_environment import get_env

# CRITICAL: These imports should expose production validator conflicts
try:
    # Production EventValidator (legacy - should be replaced)
    from netra_backend.app.services.websocket_error_validator import (
        get_websocket_validator as get_production_validator,
        reset_websocket_validator as reset_production_validator
    )
    production_validator_available = True
except ImportError as e:
    production_validator_available = False
    production_import_error = str(e)

try:
    # Unified EventValidator (consolidated SSOT - should be primary)
    from netra_backend.app.websocket_core.event_validator import (
        get_websocket_validator as get_unified_validator,
        reset_websocket_validator as reset_unified_validator
    )
    unified_validator_available = True
except ImportError as e:
    unified_validator_available = False
    unified_import_error = str(e)

try:
    # WebSocket Manager (may use either validator)
    from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager
    websocket_manager_available = True
except ImportError as e:
    websocket_manager_available = False
    websocket_manager_import_error = str(e)


class TestProductionValidatorDetection(SSotAsyncTestCase):
    """
    Integration tests for production EventValidator detection and analysis.
    
    DESIGNED TO FAIL: These tests expose production validator conflicts and usage patterns
    that indicate incomplete SSOT consolidation in production environments.
    """
    
    async def asyncSetUp(self):
        """Set up test fixtures for production analysis."""
        await super().asyncSetUp()
        
        # Initialize database utility for production-like data
        self.db_utility = DatabaseTestUtilities()
        self.env = get_env()
        
        # Track validator availability
        self.validator_availability = {
            "production": production_validator_available,
            "unified": unified_validator_available,
            "websocket_manager": websocket_manager_available
        }
        
        # Generate production-like test data
        self.production_user_id = f"prod-user-{uuid.uuid4().hex[:8]}"
        self.production_thread_id = f"prod-thread-{uuid.uuid4().hex[:8]}"
        self.production_connection_id = f"ws-conn-{uuid.uuid4().hex[:8]}"
        
        # Production-like event patterns
        self.production_event_patterns = self._create_production_event_patterns()
        
        # Reset any existing validator instances for clean testing
        if production_validator_available:
            try:
                reset_production_validator()
            except Exception:
                pass
        
        if unified_validator_available:
            try:
                reset_unified_validator()
            except Exception:
                pass
    
    async def asyncTearDown(self):
        """Clean up test fixtures."""
        await super().asyncTearDown()
        
    def _create_production_event_patterns(self) -> List[Dict[str, Any]]:
        """Create production-like event patterns based on real usage."""
        base_time = datetime.now(timezone.utc)
        
        return [
            # High-frequency agent execution pattern
            {
                "pattern_name": "high_frequency_execution",
                "events": [
                    {
                        "type": "agent_started",
                        "run_id": f"hf-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "triage-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": base_time.isoformat(),
                        "payload": {"priority": "high", "workflow": "triage"}
                    },
                    {
                        "type": "agent_completed",
                        "run_id": f"hf-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "triage-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": (base_time + timedelta(seconds=1)).isoformat(),
                        "payload": {"result": "fast_triage_complete"}
                    }
                ]
            },
            # Complex multi-agent workflow pattern
            {
                "pattern_name": "multi_agent_workflow",
                "events": [
                    {
                        "type": "agent_started",
                        "run_id": f"ma-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "supervisor-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": base_time.isoformat(),
                        "payload": {"workflow": "comprehensive_analysis"}
                    },
                    {
                        "type": "tool_executing",
                        "run_id": f"ma-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "data-helper-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": (base_time + timedelta(seconds=5)).isoformat(),
                        "payload": {"tool": "data_collector", "operation": "gather_metrics"}
                    },
                    {
                        "type": "tool_completed",
                        "run_id": f"ma-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "data-helper-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": (base_time + timedelta(seconds=15)).isoformat(),
                        "payload": {"tool": "data_collector", "result": "metrics_collected"}
                    },
                    {
                        "type": "agent_completed",
                        "run_id": f"ma-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "apex-optimizer-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": (base_time + timedelta(seconds=25)).isoformat(),
                        "payload": {"result": "optimization_recommendations"}
                    }
                ]
            },
            # Error-prone event pattern
            {
                "pattern_name": "error_prone_events",
                "events": [
                    {
                        "type": "agent_started",
                        "run_id": "",  # Invalid run_id
                        "agent_name": "test-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": base_time.isoformat(),
                        "payload": {}
                    },
                    {
                        "type": "invalid_event_type",  # Invalid event type
                        "run_id": f"err-run-{uuid.uuid4().hex[:8]}",
                        "agent_name": "test-agent",
                        "user_id": self.production_user_id,
                        "thread_id": self.production_thread_id,
                        "timestamp": base_time.isoformat(),
                        "payload": {"error": "test_error"}
                    }
                ]
            }
        ]
    
    async def test_production_validator_instance_conflicts(self):
        """
        TEST DESIGNED TO FAIL: Should expose multiple validator instances in production use.
        
        Expected failure: Both production and unified validators may be accessible,
        creating potential conflicts in production environments.
        """
        validator_instances = {}
        
        # Test production validator availability
        if production_validator_available:
            try:
                prod_validator = get_production_validator()
                validator_instances["production"] = {
                    "instance": prod_validator,
                    "type": type(prod_validator).__name__,
                    "module": type(prod_validator).__module__,
                    "instance_id": id(prod_validator),
                    "has_validate_event": hasattr(prod_validator, "validate_event"),
                    "has_validation_stats": hasattr(prod_validator, "get_validation_stats")
                }
            except Exception as e:
                validator_instances["production"] = {"error": str(e)}
        
        # Test unified validator availability
        if unified_validator_available:
            try:
                unified_validator = get_unified_validator()
                validator_instances["unified"] = {
                    "instance": unified_validator,
                    "type": type(unified_validator).__name__,
                    "module": type(unified_validator).__module__,
                    "instance_id": id(unified_validator),
                    "has_validate_event": hasattr(unified_validator, "validate_event"),
                    "has_validation_stats": hasattr(unified_validator, "get_validation_stats")
                }
            except Exception as e:
                validator_instances["unified"] = {"error": str(e)}
        
        # Check for instance conflicts - this should FAIL initially
        successful_instances = [
            name for name, info in validator_instances.items()
            if "error" not in info
        ]
        
        if len(successful_instances) > 1:
            # Multiple validators accessible - potential production conflict
            instance_details = {
                name: {
                    "type": info["type"],
                    "module": info["module"],
                    "instance_id": info["instance_id"]
                }
                for name, info in validator_instances.items()
                if "error" not in info
            }
            
            self.fail(
                f"PRODUCTION CONFLICT: Multiple EventValidator instances accessible: {instance_details}. "
                f"This creates potential conflicts in production environments where different code paths "
                f"may use different validators, leading to inconsistent validation behavior!"
            )
    
    async def test_production_validation_pattern_inconsistencies(self):
        """
        TEST DESIGNED TO FAIL: Should expose inconsistent validation patterns in production scenarios.
        
        Expected failure: Different production event patterns may be validated differently
        by different validator implementations.
        """
        validation_pattern_results = {}
        
        for pattern in self.production_event_patterns:
            pattern_name = pattern["pattern_name"]
            events = pattern["events"]
            
            pattern_results = {}
            
            # Test with production validator
            if production_validator_available:
                try:
                    prod_validator = get_production_validator()
                    prod_results = []
                    
                    for event in events:
                        result = prod_validator.validate_event(event, self.production_user_id)
                        prod_results.append({
                            "event_type": event["type"],
                            "is_valid": result.is_valid,
                            "error_message": result.error_message
                        })
                    
                    pattern_results["production"] = {
                        "results": prod_results,
                        "total_events": len(events),
                        "valid_events": sum(1 for r in prod_results if r["is_valid"]),
                        "validation_stats": prod_validator.get_validation_stats()
                    }
                    
                except Exception as e:
                    pattern_results["production"] = {"error": str(e)}
            
            # Test with unified validator
            if unified_validator_available:
                try:
                    unified_validator = get_unified_validator()
                    unified_results = []
                    
                    for event in events:
                        result = unified_validator.validate_event(event, self.production_user_id)
                        unified_results.append({
                            "event_type": event["type"],
                            "is_valid": result.is_valid,
                            "error_message": result.error_message
                        })
                    
                    pattern_results["unified"] = {
                        "results": unified_results,
                        "total_events": len(events),
                        "valid_events": sum(1 for r in unified_results if r["is_valid"]),
                        "validation_stats": unified_validator.get_validation_stats()
                    }
                    
                except Exception as e:
                    pattern_results["unified"] = {"error": str(e)}
            
            validation_pattern_results[pattern_name] = pattern_results
        
        # Check for validation pattern inconsistencies - this should FAIL initially
        inconsistency_found = False
        inconsistency_details = []
        
        for pattern_name, pattern_results in validation_pattern_results.items():
            successful_validators = [
                name for name, result in pattern_results.items()
                if "error" not in result
            ]
            
            if len(successful_validators) > 1:
                # Compare validation outcomes
                valid_event_counts = [
                    pattern_results[validator]["valid_events"]
                    for validator in successful_validators
                ]
                
                if len(set(valid_event_counts)) > 1:
                    inconsistency_found = True
                    inconsistency_details.append({
                        "pattern": pattern_name,
                        "validator_results": {
                            validator: pattern_results[validator]["valid_events"]
                            for validator in successful_validators
                        }
                    })
        
        if inconsistency_found:
            self.fail(
                f"PRODUCTION VALIDATION INCONSISTENCY: Different validators produce different outcomes "
                f"for same production patterns: {inconsistency_details}. "
                f"Full results: {validation_pattern_results}. "
                f"Production environments must have consistent validation behavior!"
            )
    
    async def test_production_websocket_manager_validator_usage(self):
        """
        TEST DESIGNED TO FAIL: Should expose which validator WebSocket manager uses in production.
        
        Expected failure: WebSocket manager may use inconsistent validators or may not be
        using the unified validator consistently.
        """
        if not websocket_manager_available:
            self.skipTest("WebSocket manager not available for testing")
        
        websocket_manager_analysis = {}
        
        try:
            # Create WebSocket manager instance
            manager = UnifiedWebSocketManager()
            
            # Analyze which validator the manager uses
            manager_info = {
                "type": type(manager).__name__,
                "module": type(manager).__module__,
                "has_event_validator": hasattr(manager, "event_validator"),
                "has_validate_event": hasattr(manager, "validate_event"),
                "has_emit_event": hasattr(manager, "emit_event")
            }
            
            # Try to detect which validator is being used
            if hasattr(manager, "event_validator"):
                validator = getattr(manager, "event_validator", None)
                if validator:
                    manager_info["validator_type"] = type(validator).__name__
                    manager_info["validator_module"] = type(validator).__module__
                    manager_info["validator_instance_id"] = id(validator)
            
            # Test event validation through manager if possible
            if hasattr(manager, "validate_event") or hasattr(manager, "emit_event"):
                test_event = {
                    "type": "agent_started",
                    "run_id": f"ws-test-{uuid.uuid4().hex[:8]}",
                    "agent_name": "test-agent",
                    "user_id": self.production_user_id,
                    "thread_id": self.production_thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {"test": "websocket_validation"}
                }
                
                if hasattr(manager, "validate_event"):
                    try:
                        validation_result = manager.validate_event(test_event, self.production_user_id)
                        manager_info["validation_test"] = {
                            "success": True,
                            "is_valid": validation_result.is_valid,
                            "error_message": validation_result.error_message
                        }
                    except Exception as e:
                        manager_info["validation_test"] = {
                            "success": False,
                            "error": str(e)
                        }
            
            websocket_manager_analysis["manager_info"] = manager_info
            
        except Exception as e:
            websocket_manager_analysis["manager_error"] = str(e)
        
        # Compare manager's validator with available validators
        if "manager_info" in websocket_manager_analysis:
            manager_info = websocket_manager_analysis["manager_info"]
            validator_type = manager_info.get("validator_type")
            validator_module = manager_info.get("validator_module")
            
            # Check which validator the manager is using
            if validator_type and validator_module:
                # Determine if manager is using production or unified validator
                if "websocket_error_validator" in validator_module:
                    using_validator = "production"
                elif "websocket_core.event_validator" in validator_module:
                    using_validator = "unified"
                else:
                    using_validator = "unknown"
                
                websocket_manager_analysis["manager_uses"] = using_validator
                
                # This should FAIL if manager is not using unified validator
                if using_validator != "unified":
                    self.fail(
                        f"PRODUCTION VALIDATOR INCONSISTENCY: WebSocket manager using '{using_validator}' validator "
                        f"instead of unified validator. "
                        f"Manager info: {manager_info}. "
                        f"Production systems should use the unified EventValidator for consistency!"
                    )
            else:
                self.fail(
                    f"PRODUCTION VALIDATOR DETECTION FAILED: Cannot determine which validator "
                    f"WebSocket manager is using. "
                    f"Manager info: {manager_info}. "
                    f"Production systems must have clear validator usage patterns!"
                )
    
    async def test_production_error_pattern_analysis(self):
        """
        TEST DESIGNED TO FAIL: Should expose different error patterns from validator conflicts.
        
        Expected failure: Different validators may produce different error patterns for
        the same problematic events, indicating validation inconsistencies.
        """
        error_pattern_analysis = {}
        
        # Test error-prone events with both validators
        error_events = self.production_event_patterns[2]["events"]  # error_prone_events pattern
        
        for validator_name in ["production", "unified"]:
            if not self.validator_availability.get(validator_name):
                continue
                
            try:
                if validator_name == "production":
                    validator = get_production_validator()
                elif validator_name == "unified":
                    validator = get_unified_validator()
                
                error_results = []
                
                for event in error_events:
                    try:
                        result = validator.validate_event(event, self.production_user_id)
                        error_results.append({
                            "event_type": event.get("type", "unknown"),
                            "is_valid": result.is_valid,
                            "error_message": result.error_message,
                            "has_business_impact": hasattr(result, "business_impact") and result.business_impact,
                            "criticality": getattr(result, "criticality", None)
                        })
                    except Exception as validation_error:
                        error_results.append({
                            "event_type": event.get("type", "unknown"),
                            "validation_exception": str(validation_error),
                            "exception_type": type(validation_error).__name__
                        })
                
                error_pattern_analysis[validator_name] = {
                    "error_results": error_results,
                    "total_errors": len([r for r in error_results if not r.get("is_valid", True)]),
                    "exceptions": len([r for r in error_results if "validation_exception" in r]),
                    "validation_stats": validator.get_validation_stats() if hasattr(validator, "get_validation_stats") else None
                }
                
            except Exception as e:
                error_pattern_analysis[validator_name] = {"error": str(e)}
        
        # Check for error pattern inconsistencies - this should FAIL initially
        successful_validators = [
            name for name, result in error_pattern_analysis.items()
            if "error" not in result
        ]
        
        if len(successful_validators) > 1:
            # Compare error patterns
            error_inconsistencies = []
            
            for event_idx, event in enumerate(error_events):
                event_type = event.get("type", "unknown")
                event_error_results = {}
                
                for validator_name in successful_validators:
                    results = error_pattern_analysis[validator_name]["error_results"]
                    if event_idx < len(results):
                        result = results[event_idx]
                        event_error_results[validator_name] = {
                            "is_valid": result.get("is_valid"),
                            "has_error_message": bool(result.get("error_message")),
                            "has_exception": "validation_exception" in result
                        }
                
                # Check for inconsistencies in error handling
                is_valid_values = [r.get("is_valid") for r in event_error_results.values()]
                exception_values = [r.get("has_exception") for r in event_error_results.values()]
                
                if len(set(is_valid_values)) > 1 or len(set(exception_values)) > 1:
                    error_inconsistencies.append({
                        "event_type": event_type,
                        "event_index": event_idx,
                        "validator_results": event_error_results
                    })
            
            if error_inconsistencies:
                self.fail(
                    f"PRODUCTION ERROR PATTERN INCONSISTENCY: Different validators handle errors differently: "
                    f"{error_inconsistencies}. "
                    f"Full error analysis: {error_pattern_analysis}. "
                    f"Production systems must have consistent error handling!"
                )
    
    async def test_production_validator_performance_impact(self):
        """
        TEST DESIGNED TO FAIL: Should expose performance impact of validator conflicts.
        
        Expected failure: Using multiple validators or wrong validator may cause
        performance degradation in production scenarios.
        """
        performance_analysis = {}
        
        # Create production-scale event load
        production_event_load = []
        for i in range(500):  # 500 events to simulate production load
            pattern = self.production_event_patterns[i % len(self.production_event_patterns)]
            event = pattern["events"][i % len(pattern["events"])].copy()
            event["run_id"] = f"perf-test-{i}-{uuid.uuid4().hex[:8]}"
            event["timestamp"] = datetime.now(timezone.utc).isoformat()
            production_event_load.append(event)
        
        # Test performance with each validator
        for validator_name in ["production", "unified"]:
            if not self.validator_availability.get(validator_name):
                continue
                
            try:
                if validator_name == "production":
                    validator = get_production_validator()
                elif validator_name == "unified":
                    validator = get_unified_validator()
                
                # Reset validator stats
                if hasattr(validator, "reset_stats"):
                    validator.reset_stats()
                
                # Measure performance
                start_time = time.time()
                start_memory = self._get_memory_usage()
                
                validation_results = []
                for event in production_event_load:
                    try:
                        result = validator.validate_event(event, self.production_user_id)
                        validation_results.append(result.is_valid)
                    except Exception:
                        validation_results.append(False)
                
                end_time = time.time()
                end_memory = self._get_memory_usage()
                
                total_time = end_time - start_time
                memory_delta = end_memory - start_memory if end_memory and start_memory else 0
                
                performance_analysis[validator_name] = {
                    "total_time": total_time,
                    "events_processed": len(production_event_load),
                    "valid_events": sum(validation_results),
                    "events_per_second": len(production_event_load) / total_time if total_time > 0 else 0,
                    "memory_delta_mb": memory_delta / (1024 * 1024) if memory_delta else 0,
                    "validation_stats": validator.get_validation_stats() if hasattr(validator, "get_validation_stats") else None
                }
                
            except Exception as e:
                performance_analysis[validator_name] = {"error": str(e)}
        
        # Check for performance impact - this should FAIL initially
        successful_validators = [
            name for name, result in performance_analysis.items()
            if "error" not in result
        ]
        
        if len(successful_validators) > 1:
            # Compare performance metrics
            performance_metrics = {}
            for validator_name in successful_validators:
                metrics = performance_analysis[validator_name]
                performance_metrics[validator_name] = {
                    "events_per_second": metrics["events_per_second"],
                    "memory_delta_mb": metrics["memory_delta_mb"]
                }
            
            # Check for significant performance differences
            events_per_second_values = [m["events_per_second"] for m in performance_metrics.values()]
            memory_delta_values = [m["memory_delta_mb"] for m in performance_metrics.values()]
            
            if max(events_per_second_values) > 0 and min(events_per_second_values) > 0:
                performance_ratio = max(events_per_second_values) / min(events_per_second_values)
                
                if performance_ratio > 1.5:  # More than 50% difference
                    self.fail(
                        f"PRODUCTION PERFORMANCE IMPACT: Significant performance difference between validators. "
                        f"Performance metrics: {performance_metrics}. "
                        f"Performance ratio: {performance_ratio:.2f}x. "
                        f"Full analysis: {performance_analysis}. "
                        f"Production systems should have optimal validator performance!"
                    )
            
            # Check for memory usage differences
            if memory_delta_values and max(memory_delta_values) > 10:  # More than 10MB difference
                memory_difference = max(memory_delta_values) - min(memory_delta_values)
                
                if memory_difference > 5:  # More than 5MB difference
                    self.fail(
                        f"PRODUCTION MEMORY IMPACT: Significant memory usage difference between validators. "
                        f"Memory metrics: {dict(zip(successful_validators, memory_delta_values))}. "
                        f"Memory difference: {memory_difference:.2f}MB. "
                        f"Production systems should have consistent memory usage!"
                    )
    
    def _get_memory_usage(self) -> Optional[int]:
        """Helper to get current memory usage in bytes."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])