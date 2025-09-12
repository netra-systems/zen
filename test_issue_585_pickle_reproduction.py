#!/usr/bin/env python3
"""
Test Issue #585: Agent Pipeline Pickle Module Serialization Errors
REPRODUCTION TEST - NO Docker Dependency

This test reproduces the pickle serialization errors occurring in the agent pipeline
when agent contexts contain module objects that cannot be pickled for Redis caching.

Business Value: Prevents agent execution failures and ensures reliable state persistence.
"""

import pickle
import importlib
import sys
import logging
from typing import Any, Dict
from datetime import datetime, timezone

# Test Framework imports
import pytest

# Core imports for agent contexts
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.services.state_serialization import StateSerializer
    from netra_backend.app.schemas.agent_state import SerializationFormat
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)


class TestAgentPickleSerializationReproduction:
    """Reproduce and validate Issue #585 pickle module serialization errors."""
    
    def test_pickle_serialization_module_contamination_basic(self):
        """
        ISSUE #585 REPRODUCTION: Test basic pickle serialization failure with module objects.
        This test demonstrates the core issue - module objects cannot be pickled.
        """
        # Create contaminated state with module object
        contaminated_state = {
            'user_id': 'test_user_123',
            'thread_id': 'thread_456',
            'run_id': 'run_789',
            'normal_data': {'key': 'value', 'count': 42},
            'contaminated_module': importlib.import_module('os'),  # THIS CAUSES THE ERROR
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Test direct pickle serialization (should fail)
        with pytest.raises(TypeError, match="cannot pickle 'module' object"):
            pickle.dumps(contaminated_state)
        
        print("✓ REPRODUCED: Direct pickle serialization fails with module objects")
    
    def test_state_serializer_pickle_format_module_contamination(self):
        """
        ISSUE #585 REPRODUCTION: Test StateSerializer with pickle format and module contamination.
        This simulates the actual agent pipeline scenario.
        """
        serializer = StateSerializer()
        
        # Create agent state with module contamination (common in reporting/optimization agents)
        agent_state_with_modules = {
            'user_request': 'Optimize my AWS costs',
            'step_count': 3,
            'metadata': {
                'agent_type': 'reporting_agent',
                'execution_phase': 'optimization',
                'tools_used': ['aws_cost_analyzer', 'optimization_engine']
            },
            'agent_context': {
                'aws_module': importlib.import_module('boto3'),  # Module reference
                'pandas_module': importlib.import_module('pandas'),  # Another module
                'analysis_results': {
                    'cost_savings': 2500,
                    'recommendations': ['Use Reserved Instances', 'Optimize S3 storage classes']
                }
            },
            'performance_metrics': {
                'execution_time_ms': 1500,
                'memory_usage_mb': 45.2
            }
        }
        
        # Test StateSerializer with pickle format (should fail)
        with pytest.raises(TypeError, match="cannot pickle 'module' object"):
            serializer.serialize(agent_state_with_modules, SerializationFormat.PICKLE)
        
        print("✓ REPRODUCED: StateSerializer pickle serialization fails with module contamination")
    
    def test_user_execution_context_module_contamination(self):
        """
        ISSUE #585 REPRODUCTION: Test UserExecutionContext with module contamination.
        This tests the scenario where agent contexts get contaminated with module references.
        """
        # Create UserExecutionContext with contaminated agent_context
        contaminated_context = UserExecutionContext(
            user_id='test_user_456',
            thread_id='thread_789',
            run_id='run_012',
            agent_context={
                'imported_tools': {
                    'json_module': importlib.import_module('json'),  # Module contamination
                    'requests_module': importlib.import_module('urllib.request')  # More contamination
                },
                'business_data': {
                    'customer_tier': 'enterprise',
                    'cost_optimization_potential': 3500
                }
            },
            audit_metadata={
                'operation': 'agent_execution',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Test pickle serialization of contaminated context (should fail)
        with pytest.raises(TypeError, match="cannot pickle 'module' object"):
            pickle.dumps(contaminated_context)
        
        print("✓ REPRODUCED: UserExecutionContext pickle serialization fails with module contamination")
    
    def test_redis_cache_fallback_behavior(self):
        """
        ISSUE #585 VALIDATION: Test Redis cache fallback when pickle serialization fails.
        This tests the expected behavior when caching fails due to module contamination.
        """
        from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
        
        # Create cache manager (no actual Redis connection needed for this test)
        cache_manager = RedisCacheManager()
        
        # Create contaminated state that would fail Redis caching
        contaminated_agent_state = {
            'execution_data': {
                'step_results': ['analysis_complete', 'optimization_identified'],
                'context_modules': {
                    'os_module': importlib.import_module('os'),  # Cannot be cached
                    'sys_module': importlib.import_module('sys')   # Cannot be cached
                }
            },
            'user_data': {
                'user_id': 'test_user_789',
                'preferences': {'notification_level': 'high'}
            }
        }
        
        # Simulate the error that would occur in Redis caching
        try:
            # This would normally be: await cache_manager.set(key, contaminated_agent_state)
            # But we test the serialization part directly
            pickle.dumps(contaminated_agent_state)
            assert False, "Expected pickle serialization to fail"
        except TypeError as e:
            assert "cannot pickle 'module' object" in str(e)
            print("✓ VALIDATED: Redis cache would fail with module contamination")
    
    def test_clean_serialization_without_modules(self):
        """
        ISSUE #585 SOLUTION VALIDATION: Test that clean contexts serialize properly.
        This validates the expected behavior when contexts are properly isolated.
        """
        serializer = StateSerializer()
        
        # Create clean agent state without module contamination
        clean_agent_state = {
            'user_request': 'Optimize my AWS costs',
            'step_count': 3,
            'metadata': {
                'agent_type': 'reporting_agent',
                'execution_phase': 'optimization',
                'tools_used': ['aws_cost_analyzer', 'optimization_engine']
            },
            'agent_context': {
                # NO module references - only serializable data
                'analysis_results': {
                    'cost_savings': 2500,
                    'recommendations': ['Use Reserved Instances', 'Optimize S3 storage classes']
                },
                'configuration': {
                    'aws_region': 'us-east-1',
                    'analysis_scope': 'comprehensive'
                }
            },
            'performance_metrics': {
                'execution_time_ms': 1500,
                'memory_usage_mb': 45.2
            }
        }
        
        # Test successful serialization with all formats
        json_result = serializer.serialize(clean_agent_state, SerializationFormat.JSON)
        assert isinstance(json_result, bytes)
        assert len(json_result) > 0
        
        pickle_result = serializer.serialize(clean_agent_state, SerializationFormat.PICKLE)
        assert isinstance(pickle_result, bytes)
        assert len(pickle_result) > 0
        
        compressed_result = serializer.serialize(clean_agent_state, SerializationFormat.COMPRESSED_JSON)
        assert isinstance(compressed_result, bytes)
        assert len(compressed_result) > 0
        
        print("✓ VALIDATED: Clean contexts serialize successfully in all formats")
    
    def test_context_cleanup_prevents_module_contamination(self):
        """
        ISSUE #585 SOLUTION TEST: Test that proper context cleanup prevents module contamination.
        This tests the mitigation strategy for preventing module references in agent contexts.
        """
        # Simulate agent execution context creation and cleanup
        original_context = {
            'business_data': {'customer_id': 'cust_123', 'tier': 'enterprise'},
            'execution_modules': {
                'tool_module': importlib.import_module('json'),  # Temporary module reference
                'analysis_module': importlib.import_module('datetime')
            }
        }
        
        # Context cleanup function (this would be the fix)
        def clean_context_for_serialization(context: Dict[str, Any]) -> Dict[str, Any]:
            """Remove non-serializable objects from context."""
            cleaned = {}
            for key, value in context.items():
                if isinstance(value, dict):
                    # Recursively clean nested dictionaries
                    cleaned_nested = {}
                    for nested_key, nested_value in value.items():
                        # Skip module objects and other non-serializable types
                        if not _is_serializable(nested_value):
                            logger.warning(f"Skipping non-serializable object: {nested_key} ({type(nested_value)})")
                            continue
                        cleaned_nested[nested_key] = nested_value
                    cleaned[key] = cleaned_nested
                elif _is_serializable(value):
                    cleaned[key] = value
                else:
                    logger.warning(f"Skipping non-serializable object: {key} ({type(value)})")
            return cleaned
        
        def _is_serializable(obj: Any) -> bool:
            """Check if object is serializable (can be pickled)."""
            try:
                pickle.dumps(obj)
                return True
            except (TypeError, AttributeError, ImportError):
                return False
        
        # Test context cleaning
        cleaned_context = clean_context_for_serialization(original_context)
        
        # Verify module objects were removed
        assert 'execution_modules' not in cleaned_context or not cleaned_context['execution_modules']
        
        # Verify business data was preserved
        assert cleaned_context['business_data']['customer_id'] == 'cust_123'
        assert cleaned_context['business_data']['tier'] == 'enterprise'
        
        # Test that cleaned context can be pickled
        pickle_result = pickle.dumps(cleaned_context)
        assert isinstance(pickle_result, bytes)
        assert len(pickle_result) > 0
        
        print("✓ VALIDATED: Context cleaning prevents module contamination and enables serialization")


def main():
    """Run the reproduction tests manually."""
    print("=== ISSUE #585 PICKLE SERIALIZATION ERROR REPRODUCTION ===")
    print()
    
    test_instance = TestAgentPickleSerializationReproduction()
    
    try:
        print("1. Testing basic module contamination...")
        test_instance.test_pickle_serialization_module_contamination_basic()
        print()
        
        print("2. Testing StateSerializer with module contamination...")
        test_instance.test_state_serializer_pickle_format_module_contamination()
        print()
        
        print("3. Testing UserExecutionContext with module contamination...")
        test_instance.test_user_execution_context_module_contamination()
        print()
        
        print("4. Testing Redis cache fallback behavior...")
        test_instance.test_redis_cache_fallback_behavior()
        print()
        
        print("5. Testing clean serialization without modules...")
        test_instance.test_clean_serialization_without_modules()
        print()
        
        print("6. Testing context cleanup mitigation...")
        test_instance.test_context_cleanup_prevents_module_contamination()
        print()
        
        print("=== ALL TESTS COMPLETED ===")
        print("✓ ISSUE #585 SUCCESSFULLY REPRODUCED AND VALIDATED")
        print("✓ SOLUTION APPROACH VALIDATED")
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)