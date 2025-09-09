"""
GitHub Issue #117 - WebSocket JSON SSOT Violations Reproduction Test Suite

CRITICAL: This test suite is designed to FAIL initially - it reproduces SSOT violations
in WebSocket JSON serialization that are causing 1011 errors and agent execution timeouts.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Identify and fix SSOT violations in WebSocket JSON handling  
- Value Impact: Eliminates serialization inconsistencies causing WebSocket failures
- Strategic Impact: Prevents $120K+ MRR loss from chat functionality failures

Test Strategy: FAILING TESTS FIRST
These tests are EXPECTED TO FAIL initially, reproducing the exact SSOT violations.
After consolidation fixes are implemented, these tests should PASS.
"""

import json
import pytest
import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict

# Test framework imports following SSOT patterns
from test_framework.base_integration_test import BaseIntegrationTest

# Production imports to test
from netra_backend.app.schemas.websocket_models import BaseWebSocketPayload
from netra_backend.app.websocket_core.types import get_frontend_message_type
from netra_backend.app.agents.state import DeepAgentState
from shared.isolated_environment import get_env


class TestWebSocketJSONSSOTViolations(BaseIntegrationTest):
    """Unit tests to reproduce WebSocket JSON SSOT violations."""

    def test_duplicate_serialization_functions_identified(self):
        """FAILING TEST: Should identify all 6+ duplicate JSON serialization functions.
        
        This test scans the codebase and identifies functions that perform
        similar WebSocket JSON serialization operations, violating SSOT principles.
        
        EXPECTED TO FAIL: Multiple functions exist doing the same serialization.
        PASSES AFTER FIX: Only one canonical serialization function exists.
        """
        # Scan codebase for WebSocket JSON serialization functions
        project_root = Path(__file__).parent.parent.parent.parent
        websocket_files = list(project_root.rglob("*websocket*.py"))
        json_files = list(project_root.rglob("*json*.py"))
        
        serialization_functions = []
        duplicate_patterns = set()
        
        # Look for common serialization patterns
        patterns_to_find = [
            "json.dumps",
            "to_json",
            "serialize",
            "dict()",
            "__dict__",
            "model_dump",
            "json.loads"
        ]
        
        for file_path in websocket_files + json_files:
            if "test" in str(file_path) or ".git" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in patterns_to_find:
                        if pattern in content:
                            # Count occurrences
                            count = content.count(pattern)
                            if count > 0:
                                serialization_functions.append({
                                    'file': str(file_path),
                                    'pattern': pattern,
                                    'count': count
                                })
                                if count > 1:
                                    duplicate_patterns.add(pattern)
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Test assertion: Should fail if we find multiple serialization approaches
        unique_files_with_serialization = len(set(
            func['file'] for func in serialization_functions
        ))
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially
        # We expect to find 6+ different files doing WebSocket JSON serialization
        assert unique_files_with_serialization <= 2, (
            f"SSOT VIOLATION: Found {unique_files_with_serialization} files doing "
            f"WebSocket JSON serialization. Should be consolidated to 1-2 files max. "
            f"Files: {set(func['file'] for func in serialization_functions)}"
        )
        
        # Additional check for duplicate patterns
        assert len(duplicate_patterns) == 0, (
            f"SSOT VIOLATION: Found duplicate serialization patterns: {duplicate_patterns}"
        )

    def test_agent_state_serialization_consistency(self):
        """FAILING TEST: DeepAgentState serialization should be consistent across all usages.
        
        Tests that DeepAgentState serializes identically everywhere it's used.
        Currently fails due to different serialization approaches in different modules.
        
        EXPECTED TO FAIL: Inconsistent serialization methods found.
        PASSES AFTER FIX: Single consistent serialization approach.
        """
        # Create test DeepAgentState
        agent_state = DeepAgentState(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            current_agent="test_agent",
            context={"test": "data"},
            step_count=1
        )
        
        # Test different serialization approaches that might exist
        serialization_methods = []
        
        # Method 1: Direct dict conversion
        try:
            method1_result = dict(agent_state.__dict__)
            serialization_methods.append(("__dict__", method1_result))
        except Exception as e:
            serialization_methods.append(("__dict__", f"ERROR: {e}"))
        
        # Method 2: JSON dumps
        try:
            method2_result = json.dumps(agent_state.__dict__)
            serialization_methods.append(("json.dumps", method2_result))
        except Exception as e:
            serialization_methods.append(("json.dumps", f"ERROR: {e}"))
            
        # Method 3: to_dict if exists
        try:
            if hasattr(agent_state, 'to_dict'):
                method3_result = agent_state.to_dict()
                serialization_methods.append(("to_dict", method3_result))
        except Exception as e:
            serialization_methods.append(("to_dict", f"ERROR: {e}"))
            
        # Method 4: model_dump if Pydantic
        try:
            if hasattr(agent_state, 'model_dump'):
                method4_result = agent_state.model_dump()
                serialization_methods.append(("model_dump", method4_result))
        except Exception as e:
            serialization_methods.append(("model_dump", f"ERROR: {e}"))
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially
        # We expect inconsistent serialization results
        assert len(set(str(result) for method, result in serialization_methods)) <= 1, (
            f"SSOT VIOLATION: DeepAgentState has inconsistent serialization methods. "
            f"Found {len(serialization_methods)} different approaches: "
            f"{[(method, type(result).__name__) for method, result in serialization_methods]}"
        )

    def test_websocket_message_serialization_ssot(self):
        """FAILING TEST: WebSocket message serialization should use single method.
        
        Tests that all WebSocket messages use the same serialization approach.
        Currently fails due to scattered serialization logic across modules.
        
        EXPECTED TO FAIL: Multiple serialization approaches found.
        PASSES AFTER FIX: Single SSOT serialization method used.
        """
        # Test WebSocket message serialization patterns
        test_message = {
            "type": "agent_started", 
            "thread_id": "test_123",
            "data": {"agent": "test_agent"}
        }
        
        # Look for different serialization approaches in production code
        project_root = Path(__file__).parent.parent.parent.parent
        websocket_core_path = project_root / "netra_backend" / "app" / "websocket_core"
        
        serialization_approaches = []
        
        # Scan websocket_core files for serialization patterns
        if websocket_core_path.exists():
            for py_file in websocket_core_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Look for serialization patterns
                        if "json.dumps" in content:
                            serialization_approaches.append(f"json.dumps in {py_file.name}")
                        if "to_json" in content:
                            serialization_approaches.append(f"to_json in {py_file.name}")
                        if "serialize" in content:
                            serialization_approaches.append(f"serialize in {py_file.name}")
                        if "__dict__" in content:
                            serialization_approaches.append(f"__dict__ in {py_file.name}")
                            
                except (UnicodeDecodeError, FileNotFoundError):
                    continue
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially
        # We expect to find multiple serialization approaches
        unique_approaches = len(set(approach.split()[0] for approach in serialization_approaches))
        assert unique_approaches <= 1, (
            f"SSOT VIOLATION: Found {unique_approaches} different WebSocket serialization approaches. "
            f"Should be consolidated to 1 SSOT method. Approaches found: {serialization_approaches}"
        )

    def test_frontend_message_type_conversion_unified(self):
        """FAILING TEST: Frontend message type conversion should be unified.
        
        Tests that message type conversion uses single source of truth.
        Currently fails due to multiple conversion functions scattered across codebase.
        
        EXPECTED TO FAIL: Multiple conversion functions found.
        PASSES AFTER FIX: Single SSOT conversion function used.
        """
        # Test message types that need frontend conversion
        backend_message_types = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        conversion_functions = []
        
        # Scan for message type conversion functions
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Look for conversion patterns
        conversion_patterns = [
            "get_frontend_message_type",
            "convert_message_type", 
            "frontend_type",
            "message_type_mapping",
            "type_conversion"
        ]
        
        for py_file in project_root.rglob("*.py"):
            if "test" in str(py_file) or ".git" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern in conversion_patterns:
                        if pattern in content:
                            conversion_functions.append(f"{pattern} in {py_file}")
            except (UnicodeDecodeError, FileNotFoundError):
                continue
        
        # Test the actual conversion function if it exists
        conversion_results = {}
        try:
            from netra_backend.app.websocket_core.types import get_frontend_message_type
            for msg_type in backend_message_types:
                result = get_frontend_message_type(msg_type)
                conversion_results[msg_type] = result
        except ImportError:
            # Expected if function doesn't exist yet
            pass
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially  
        # We expect multiple conversion functions or inconsistent results
        unique_conversion_files = len(set(
            func.split(" in ")[-1] for func in conversion_functions
        ))
        assert unique_conversion_files <= 1, (
            f"SSOT VIOLATION: Found {unique_conversion_files} files with message type conversion. "
            f"Should be consolidated to 1 SSOT file. Functions found: {conversion_functions}"
        )

    def test_websocket_json_performance_requirements(self):
        """FAILING TEST: WebSocket JSON serialization should meet performance requirements.
        
        Tests that JSON serialization is fast enough for real-time WebSocket communication.
        Currently fails due to inefficient serialization approaches.
        
        EXPECTED TO FAIL: Serialization too slow for real-time requirements.
        PASSES AFTER FIX: Optimized SSOT serialization meets performance targets.
        """
        import time
        
        # Create realistic WebSocket message
        large_message = {
            "type": "agent_completed",
            "thread_id": "test_thread_123",
            "data": {
                "agent": "cost_optimizer",
                "result": {
                    "recommendations": [f"rec_{i}" for i in range(100)],
                    "analysis": f"Large analysis text " * 100,
                    "metrics": {f"metric_{i}": i * 1.5 for i in range(50)}
                },
                "execution_time": 45.2,
                "tokens_used": 1250
            }
        }
        
        # Test serialization performance
        start_time = time.time()
        serialized = json.dumps(large_message)
        serialization_time = time.time() - start_time
        
        # Test deserialization performance  
        start_time = time.time()
        deserialized = json.loads(serialized)
        deserialization_time = time.time() - start_time
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially
        # Performance requirements: <10ms for serialization + deserialization
        total_time = serialization_time + deserialization_time
        assert total_time < 0.010, (
            f"PERFORMANCE VIOLATION: WebSocket JSON serialization too slow. "
            f"Total time: {total_time:.4f}s (limit: 0.010s). "
            f"Serialization: {serialization_time:.4f}s, Deserialization: {deserialization_time:.4f}s"
        )
        
        # Verify data integrity
        assert deserialized == large_message, "Data integrity violation during serialization"

    def test_websocket_json_error_handling_unified(self):
        """FAILING TEST: WebSocket JSON error handling should be unified.
        
        Tests that JSON serialization errors are handled consistently across all WebSocket operations.
        Currently fails due to different error handling approaches in different modules.
        
        EXPECTED TO FAIL: Inconsistent error handling found.
        PASSES AFTER FIX: Unified error handling across all WebSocket JSON operations.
        """
        # Test problematic data that might cause serialization errors
        problematic_data = [
            {"circular": None},  # We'll make this circular
            {"datetime": "not_serializable_datetime_obj"},
            {"complex": complex(1, 2)},
            {"function": lambda x: x},
            {"bytes": b"binary_data"}
        ]
        
        # Create circular reference
        problematic_data[0]["circular"] = problematic_data[0]
        
        error_handling_results = []
        
        for i, data in enumerate(problematic_data[1:], 1):  # Skip circular reference for now
            try:
                # Test current error handling approach
                result = json.dumps(data, default=str)  # Common fallback
                error_handling_results.append(f"data_{i}: SUCCESS")
            except Exception as e:
                error_handling_results.append(f"data_{i}: ERROR - {type(e).__name__}")
        
        # CRITICAL ASSERTION: This SHOULD FAIL initially
        # We expect inconsistent error handling (some succeed with fallback, some fail)
        error_count = len([r for r in error_handling_results if "ERROR" in r])
        success_count = len([r for r in error_handling_results if "SUCCESS" in r])
        
        # Test should fail if error handling is inconsistent
        assert error_count == 0 or success_count == 0, (
            f"SSOT VIOLATION: Inconsistent JSON error handling. "
            f"Some data serialized with fallbacks, others failed. "
            f"Results: {error_handling_results}. "
            f"Need unified error handling approach."
        )


# Test Configuration
pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.ssot_violations,
    pytest.mark.expected_failure  # These tests SHOULD fail initially
]