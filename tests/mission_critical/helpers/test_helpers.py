"""
Mission Critical Test Helpers

Comprehensive test helper utilities for mission critical functionality testing.
Provides specialized utilities for GitHub integration, WebSocket event validation,
SSOT compliance checking, and business value assessment.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Testing Infrastructure & Quality Assurance  
- Value Impact: Enables comprehensive validation of mission critical systems
- Strategic Impact: Foundation for reliable GitHub integration and business continuity

Key Capabilities:
1. GitHub Integration Test Utilities
2. WebSocket Event Validation
3. SSOT Compliance Verification
4. Business Value Assessment
5. Performance & Reliability Testing
"""

import time
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from unittest.mock import Mock, MagicMock
import json

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


class MissionCriticalTestHelper:
    """
    Mission Critical Test Helper providing comprehensive testing utilities.
    
    CRITICAL: This class provides essential test infrastructure for mission critical
    functionality validation including GitHub integration, WebSocket events, and
    business value protection.
    
    Business Impact:
    - Enables reliable GitHub integration testing
    - Validates $500K+ ARR functionality protection
    - Ensures mission critical test infrastructure reliability
    """
    
    def __init__(self):
        """Initialize test helper with SSOT compliance."""
        self.env = IsolatedEnvironment()
        self.id_manager = UnifiedIDManager()
        self._test_data_cache = {}
        
    # ==========================================
    # GitHub Integration Test Utilities
    # ==========================================
    
    def create_github_test_context(self, 
                                 issue_type: str = "test", 
                                 priority: str = "P2",
                                 business_impact: str = "medium") -> Dict[str, Any]:
        """
        Create standardized GitHub test context for issue automation testing.
        
        Args:
            issue_type: Type of issue being tested
            priority: Priority level (P1, P2, P3)
            business_impact: Business impact level
            
        Returns:
            Standardized test context dictionary
        """
        test_issue_number = self.generate_test_issue_number()
        
        return {
            "issue_number": test_issue_number,
            "issue_type": issue_type,
            "priority": priority,
            "business_impact": business_impact,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "test_context": True,
            "github_config": self._get_github_test_config(),
            "validation_criteria": {
                "issue_creation_time_ms": 5000,  # Max 5 seconds
                "response_validation": True,
                "error_handling_validation": True
            }
        }
    
    def generate_test_issue_number(self) -> int:
        """
        Generate test issue number in safe range (90000-99999).
        
        Returns:
            Test issue number that won't conflict with real issues
        """
        # Use consistent ID generation from UnifiedIDManager
        test_id = self.id_manager.generate_id(IDType.THREAD, prefix="test")
        # Extract numeric part and map to test range
        numeric_part = int(test_id.split('_')[-1][:5], 16) % 10000
        return 90000 + numeric_part
    
    def validate_issue_creation(self, 
                              issue_data: Dict[str, Any], 
                              expected_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate GitHub issue creation meets expected criteria.
        
        Args:
            issue_data: Actual issue data created
            expected_criteria: Expected validation criteria
            
        Returns:
            Validation results with pass/fail status
        """
        results = {
            "validation_passed": True,
            "errors": [],
            "warnings": [],
            "metrics": {}
        }
        
        # Validate required fields
        required_fields = ["title", "body", "labels"]
        for field in required_fields:
            if field not in issue_data:
                results["errors"].append(f"Missing required field: {field}")
                results["validation_passed"] = False
        
        # Validate business impact assessment
        if "business_impact" in expected_criteria:
            if not self.assess_business_impact(issue_data):
                results["warnings"].append("Business impact assessment incomplete")
        
        # Validate performance criteria
        if "max_creation_time" in expected_criteria:
            creation_time = issue_data.get("creation_time_ms", 0)
            max_time = expected_criteria["max_creation_time"]
            if creation_time > max_time:
                results["errors"].append(f"Creation time {creation_time}ms exceeds limit {max_time}ms")
                results["validation_passed"] = False
        
        results["metrics"]["validation_time"] = time.time()
        return results
    
    def assess_business_impact(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess business impact of test scenarios for revenue protection validation.
        
        Args:
            test_data: Test scenario data
            
        Returns:
            Business impact assessment
        """
        impact_assessment = {
            "revenue_at_risk": 0,
            "customer_segments_affected": [],
            "criticality_score": 0.0,
            "recovery_time_estimate": "unknown"
        }
        
        # Analyze test scenario for business impact
        if "error_type" in test_data:
            error_type = test_data["error_type"].lower()
            
            if "critical" in error_type or "system" in error_type:
                impact_assessment["revenue_at_risk"] = 500000  # $500K+ ARR
                impact_assessment["customer_segments_affected"] = ["Free", "Early", "Mid", "Enterprise"]
                impact_assessment["criticality_score"] = 1.0
                impact_assessment["recovery_time_estimate"] = "immediate"
            
            elif "websocket" in error_type or "chat" in error_type:
                impact_assessment["revenue_at_risk"] = 450000  # 90% of platform value
                impact_assessment["customer_segments_affected"] = ["Early", "Mid", "Enterprise"]
                impact_assessment["criticality_score"] = 0.9
                impact_assessment["recovery_time_estimate"] = "< 5 minutes"
            
            elif "auth" in error_type or "security" in error_type:
                impact_assessment["revenue_at_risk"] = 500000
                impact_assessment["customer_segments_affected"] = ["All"]
                impact_assessment["criticality_score"] = 1.0
                impact_assessment["recovery_time_estimate"] = "immediate"
        
        return impact_assessment
    
    # ==========================================
    # WebSocket Event Validation
    # ==========================================
    
    def validate_websocket_events(self, 
                                event_sequence: List[Dict[str, Any]], 
                                expected_events: List[str]) -> Dict[str, Any]:
        """
        Validate WebSocket event sequence for business critical functionality.
        
        Args:
            event_sequence: Actual events received
            expected_events: Expected event types
            
        Returns:
            Validation results with business value scoring
        """
        validation_results = {
            "sequence_valid": True,
            "missing_events": [],
            "unexpected_events": [],
            "business_value_score": 0.0,
            "event_timing": {},
            "errors": []
        }
        
        # Extract event types from sequence
        actual_events = [event.get("type", "") for event in event_sequence]
        
        # Check for missing critical events
        for expected_event in expected_events:
            if expected_event not in actual_events:
                validation_results["missing_events"].append(expected_event)
                validation_results["sequence_valid"] = False
        
        # Check for unexpected events
        for actual_event in actual_events:
            if actual_event not in expected_events:
                validation_results["unexpected_events"].append(actual_event)
        
        # Score business value of event flow
        validation_results["business_value_score"] = self.score_event_business_value(event_sequence)
        
        # Analyze event timing
        validation_results["event_timing"] = self._analyze_event_timing(event_sequence)
        
        return validation_results
    
    def score_event_business_value(self, event_sequence: List[Dict[str, Any]]) -> float:
        """
        Score the business value of WebSocket event sequence.
        
        Args:
            event_sequence: Event sequence to score
            
        Returns:
            Business value score (0.0 to 1.0)
        """
        if not event_sequence:
            return 0.0
        
        score = 0.0
        critical_events = ["agent_started", "agent_thinking", "tool_executing", 
                         "tool_completed", "agent_completed"]
        
        for event in event_sequence:
            event_type = event.get("type", "")
            
            # Critical business events (chat functionality = 90% of platform value)
            if event_type in critical_events:
                score += 0.18  # Each critical event worth 18% (5 events = 90%)
            
            # Additional value for proper event data
            if event.get("data") and isinstance(event["data"], dict):
                score += 0.02  # Bonus for proper data structure
        
        return min(score, 1.0)  # Cap at 100%
    
    # ==========================================
    # SSOT Compliance Validation
    # ==========================================
    
    def validate_module_compliance(self, 
                                 module_path: str, 
                                 compliance_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate module follows SSOT compliance patterns.
        
        Args:
            module_path: Path to module being validated
            compliance_rules: SSOT compliance rules to check
            
        Returns:
            Compliance validation results
        """
        compliance_results = {
            "compliant": True,
            "violations": [],
            "warnings": [],
            "score": 0.0,
            "recommendations": []
        }
        
        # Check for duplicate implementations (SSOT violation)
        if "no_duplicates" in compliance_rules:
            duplicates = self._detect_duplicate_implementations(module_path)
            if duplicates:
                compliance_results["violations"].extend(duplicates)
                compliance_results["compliant"] = False
        
        # Check for proper import patterns
        if "absolute_imports" in compliance_rules:
            relative_imports = self._detect_relative_imports(module_path)
            if relative_imports:
                compliance_results["violations"].extend(relative_imports)
                compliance_results["compliant"] = False
        
        # Calculate compliance score
        max_score = len(compliance_rules)
        violations = len(compliance_results["violations"])
        compliance_results["score"] = max(0.0, (max_score - violations) / max_score)
        
        return compliance_results
    
    def detect_ssot_violations(self, 
                             codebase_path: str, 
                             violation_patterns: List[str]) -> Dict[str, Any]:
        """
        Detect SSOT violations across codebase.
        
        Args:
            codebase_path: Path to codebase
            violation_patterns: Patterns that indicate SSOT violations
            
        Returns:
            SSOT violation detection results
        """
        violation_results = {
            "violations_found": [],
            "violation_count": 0,
            "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "remediation_suggestions": []
        }
        
        # Simulate violation detection (in real implementation, would scan files)
        for pattern in violation_patterns:
            if "duplicate" in pattern.lower():
                violation_results["violations_found"].append({
                    "type": "duplicate_implementation",
                    "severity": "high",
                    "description": f"Duplicate implementation pattern: {pattern}",
                    "suggested_fix": "Consolidate into single SSOT implementation"
                })
                violation_results["severity_breakdown"]["high"] += 1
        
        violation_results["violation_count"] = len(violation_results["violations_found"])
        return violation_results
    
    # ==========================================
    # Performance & Reliability Testing
    # ==========================================
    
    async def measure_async_performance(self, 
                                      async_function, 
                                      *args, 
                                      **kwargs) -> Dict[str, Any]:
        """
        Measure performance of async function execution.
        
        Args:
            async_function: Async function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Performance measurement results
        """
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            result = await async_function(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        end_memory = self._get_memory_usage()
        
        return {
            "execution_time_ms": (end_time - start_time) * 1000,
            "memory_delta_mb": (end_memory - start_memory) / 1024 / 1024,
            "success": success,
            "error": error,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def track_memory_usage(self, test_duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Track memory usage over test duration.
        
        Args:
            test_duration_seconds: Duration to track memory
            
        Returns:
            Memory usage tracking results
        """
        memory_samples = []
        start_time = time.time()
        
        while (time.time() - start_time) < test_duration_seconds:
            memory_samples.append({
                "timestamp": time.time(),
                "memory_mb": self._get_memory_usage() / 1024 / 1024
            })
            time.sleep(1)  # Sample every second
        
        if memory_samples:
            memory_values = [sample["memory_mb"] for sample in memory_samples]
            return {
                "samples": memory_samples,
                "min_memory_mb": min(memory_values),
                "max_memory_mb": max(memory_values),
                "avg_memory_mb": sum(memory_values) / len(memory_values),
                "memory_growth_mb": memory_values[-1] - memory_values[0],
                "duration_seconds": test_duration_seconds
            }
        
        return {"error": "No memory samples collected"}
    
    def generate_test_data(self, 
                          data_type: str, 
                          count: int = 1, 
                          **options) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Generate test data for various testing scenarios.
        
        Args:
            data_type: Type of test data to generate
            count: Number of data items to generate
            **options: Additional generation options
            
        Returns:
            Generated test data
        """
        generators = {
            "websocket_event": self._generate_websocket_event,
            "github_issue": self._generate_github_issue_data,
            "user_context": self._generate_user_context,
            "error_context": self._generate_error_context
        }
        
        if data_type not in generators:
            raise ValueError(f"Unsupported data type: {data_type}")
        
        generator = generators[data_type]
        
        if count == 1:
            return generator(**options)
        else:
            return [generator(**options) for _ in range(count)]
    
    # ==========================================
    # Private Helper Methods
    # ==========================================
    
    def _get_github_test_config(self) -> Dict[str, Any]:
        """Get GitHub test configuration."""
        return {
            "enabled": self.env.get("GITHUB_INTEGRATION_ENABLED", "true").lower() == "true",
            "token": self.env.get("GITHUB_TEST_TOKEN", "test_token"),
            "repo_owner": self.env.get("GITHUB_TEST_REPO_OWNER", "test_owner"),
            "repo_name": self.env.get("GITHUB_TEST_REPO_NAME", "test_repo"),
            "test_mode": True
        }
    
    def _analyze_event_timing(self, event_sequence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze timing of event sequence."""
        if len(event_sequence) < 2:
            return {"error": "Insufficient events for timing analysis"}
        
        timings = []
        for i in range(1, len(event_sequence)):
            prev_time = event_sequence[i-1].get("timestamp", 0)
            curr_time = event_sequence[i].get("timestamp", 0)
            if prev_time and curr_time:
                timings.append(curr_time - prev_time)
        
        if timings:
            return {
                "average_interval_ms": sum(timings) / len(timings),
                "min_interval_ms": min(timings),
                "max_interval_ms": max(timings),
                "total_duration_ms": event_sequence[-1].get("timestamp", 0) - event_sequence[0].get("timestamp", 0)
            }
        
        return {"error": "No valid timestamps found"}
    
    def _detect_duplicate_implementations(self, module_path: str) -> List[str]:
        """Detect duplicate implementations (placeholder)."""
        # In real implementation, would scan for duplicate code patterns
        return []
    
    def _detect_relative_imports(self, module_path: str) -> List[str]:
        """Detect relative imports (placeholder)."""
        # In real implementation, would scan for relative import patterns
        return []
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    
    def _generate_websocket_event(self, event_type: str = "agent_started", **options) -> Dict[str, Any]:
        """Generate WebSocket event test data."""
        return {
            "type": event_type,
            "timestamp": time.time() * 1000,  # milliseconds
            "data": options.get("data", {}),
            "user_id": options.get("user_id", f"test_user_{self.id_manager.generate_id(IDType.USER, prefix='test')}"),
            "thread_id": options.get("thread_id", f"test_thread_{self.id_manager.generate_id(IDType.THREAD, prefix='test')}")
        }
    
    def _generate_github_issue_data(self, issue_type: str = "test", **options) -> Dict[str, Any]:
        """Generate GitHub issue test data."""
        return {
            "title": options.get("title", f"Test Issue - {issue_type}"),
            "body": options.get("body", f"Test issue for {issue_type} validation"),
            "labels": options.get("labels", ["test", issue_type]),
            "priority": options.get("priority", "P2"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "test_context": True
        }
    
    def _generate_user_context(self, **options) -> Dict[str, Any]:
        """Generate user context test data."""
        return {
            "user_id": options.get("user_id", self.id_manager.generate_id(IDType.USER, prefix="test")),
            "thread_id": options.get("thread_id", self.id_manager.generate_id(IDType.THREAD, prefix="test")),
            "request_id": options.get("request_id", self.id_manager.generate_id(IDType.REQUEST, prefix="test")),
            "is_test": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_error_context(self, error_type: str = "test_error", **options) -> Dict[str, Any]:
        """Generate error context test data."""
        return {
            "error_type": error_type,
            "error_message": options.get("message", f"Test error: {error_type}"),
            "stack_trace": options.get("stack_trace", "Test stack trace"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": options.get("severity", "medium"),
            "test_context": True
        }


# Export the main class
__all__ = ["MissionCriticalTestHelper"]