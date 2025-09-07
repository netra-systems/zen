"""
Comprehensive User Execution Context Test Fixtures

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide standardized fixtures for UserExecutionContext testing
- Value Impact: Enables comprehensive multi-user testing scenarios
- Strategic Impact: Ensures proper user isolation and context management testing

This module provides SSOT fixtures for UserExecutionContext integration testing,
including multi-user scenarios, realistic business contexts, and performance testing.

CRITICAL: All fixtures create REAL UserExecutionContext instances with proper
validation, isolation, and business-realistic data patterns.
"""

import pytest
import asyncio
import uuid
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Generator, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

# Import UserExecutionContext components
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError,
    ContextIsolationError,
    clear_shared_object_registry
)

# Import test framework components
from test_framework.isolated_environment_fixtures import isolated_env
from shared.isolated_environment import get_env


@pytest.fixture(scope="function")
def clean_context_registry():
    """Ensure clean shared object registry for each test."""
    clear_shared_object_registry()
    yield
    clear_shared_object_registry()


@pytest.fixture(scope="function")
def realistic_user_context(clean_context_registry, isolated_env) -> UserExecutionContext:
    """Create a realistic UserExecutionContext for testing.
    
    Provides a production-like context with realistic IDs, metadata,
    and business context suitable for most integration tests.
    """
    return UserExecutionContext(
        user_id="user_enterprise_12345678901234567890",
        thread_id="thread_optimization_98765432109876543210",
        run_id=f"run_cost_analysis_{int(time.time())}_a1b2c3d4",
        websocket_client_id="ws_conn_real_12345678901234567890",
        agent_context={
            "agent_name": "cost_optimizer",
            "user_subscription": "enterprise",
            "session_id": "session_enterprise_12345678901234567890",
            "user_preferences": {
                "currency": "USD",
                "timezone": "America/New_York",
                "notification_preferences": ["email", "slack"],
                "optimization_goals": ["cost_reduction", "performance_improvement"]
            },
            "execution_environment": {
                "region": "us-east-1",
                "deployment": "production",
                "feature_flags": ["advanced_analytics", "real_time_updates"]
            }
        },
        audit_metadata={
            "client_ip": "203.0.113.42",
            "user_agent": "NetraUI/2.1.0 (Enterprise Dashboard)",
            "session_start": datetime.now(timezone.utc).isoformat(),
            "request_source": "web_dashboard",
            "compliance_tracking": {
                "gdpr_consent": True,
                "data_retention": "90_days",
                "audit_level": "detailed"
            },
            "business_context": {
                "company_size": "enterprise",
                "monthly_spend": 75000,
                "optimization_tier": "premium"
            }
        }
    )


@pytest.fixture(scope="function")
def multi_user_contexts(clean_context_registry, isolated_env) -> List[UserExecutionContext]:
    """Create multiple realistic user contexts for multi-user testing.
    
    Provides 5 different user contexts representing different user types:
    - Free tier user
    - Early adopter 
    - Mid-tier business user
    - Enterprise user
    - Internal/admin user
    """
    contexts = []
    
    # Free tier user
    free_user = UserExecutionContext(
        user_id="user_free_09876543210987654321",
        thread_id="thread_free_basic_12345678901234567890",
        run_id=f"run_free_basic_{int(time.time())}_f1r2e3e4",
        websocket_client_id="ws_free_09876543210987654321",
        agent_context={
            "agent_name": "triage_agent",
            "user_subscription": "free",
            "session_id": "session_free_09876543210987654321",
            "user_preferences": {
                "currency": "USD",
                "timezone": "America/Los_Angeles"
            },
            "rate_limits": {
                "requests_per_hour": 50,
                "agents_per_day": 10,
                "analysis_depth": "basic"
            }
        },
        audit_metadata={
            "client_ip": "198.51.100.10",
            "user_agent": "NetraUI/2.1.0 (Free Tier)",
            "request_source": "web_app",
            "business_context": {
                "company_size": "individual",
                "monthly_spend": 500,
                "optimization_tier": "basic"
            }
        }
    )
    contexts.append(free_user)
    
    # Early adopter user
    early_user = UserExecutionContext(
        user_id="user_early_11223344556677889900",
        thread_id="thread_early_startup_99887766554433221100",
        run_id=f"run_early_startup_{int(time.time())}_e1a2r3l4",
        websocket_client_id="ws_early_11223344556677889900",
        agent_context={
            "agent_name": "optimization_agent",
            "user_subscription": "early",
            "session_id": "session_early_11223344556677889900",
            "user_preferences": {
                "currency": "USD",
                "timezone": "America/New_York",
                "notification_preferences": ["email"],
                "optimization_goals": ["cost_reduction"]
            },
            "execution_environment": {
                "region": "us-west-2",
                "deployment": "staging",
                "feature_flags": ["beta_features"]
            }
        },
        audit_metadata={
            "client_ip": "203.0.113.25",
            "user_agent": "NetraUI/2.1.0 (Early Access)",
            "request_source": "mobile_app",
            "business_context": {
                "company_size": "startup",
                "monthly_spend": 5000,
                "optimization_tier": "growth"
            }
        }
    )
    contexts.append(early_user)
    
    # Mid-tier business user
    mid_user = UserExecutionContext(
        user_id="user_business_55443322110099887766",
        thread_id="thread_business_ops_44332211009988776655",
        run_id=f"run_business_ops_{int(time.time())}_m1i2d3b4",
        websocket_client_id="ws_business_55443322110099887766",
        agent_context={
            "agent_name": "business_optimizer",
            "user_subscription": "business",
            "session_id": "session_business_55443322110099887766",
            "user_preferences": {
                "currency": "EUR",
                "timezone": "Europe/London",
                "notification_preferences": ["email", "teams"],
                "optimization_goals": ["cost_reduction", "compliance"]
            },
            "execution_environment": {
                "region": "eu-west-1",
                "deployment": "production",
                "feature_flags": ["advanced_analytics", "compliance_reporting"]
            }
        },
        audit_metadata={
            "client_ip": "203.0.113.67",
            "user_agent": "NetraUI/2.1.0 (Business Dashboard)",
            "request_source": "web_dashboard",
            "compliance_tracking": {
                "gdpr_consent": True,
                "data_retention": "30_days",
                "audit_level": "standard"
            },
            "business_context": {
                "company_size": "mid_market",
                "monthly_spend": 25000,
                "optimization_tier": "professional"
            }
        }
    )
    contexts.append(mid_user)
    
    # Enterprise user
    enterprise_user = UserExecutionContext(
        user_id="user_enterprise_77889900112233445566",
        thread_id="thread_enterprise_ops_66778899001122334455",
        run_id=f"run_enterprise_ops_{int(time.time())}_e1n2t3e4",
        websocket_client_id="ws_enterprise_77889900112233445566",
        agent_context={
            "agent_name": "enterprise_optimizer",
            "user_subscription": "enterprise",
            "session_id": "session_enterprise_77889900112233445566",
            "user_preferences": {
                "currency": "USD",
                "timezone": "America/Chicago",
                "notification_preferences": ["email", "slack", "pagerduty"],
                "optimization_goals": ["cost_reduction", "performance_improvement", "compliance", "governance"]
            },
            "execution_environment": {
                "region": "us-central-1",
                "deployment": "production",
                "feature_flags": ["all_features", "enterprise_analytics", "custom_integrations"]
            },
            "enterprise_features": {
                "sso_enabled": True,
                "custom_policies": True,
                "dedicated_support": True,
                "advanced_security": True
            }
        },
        audit_metadata={
            "client_ip": "203.0.113.100",
            "user_agent": "NetraUI/2.1.0 (Enterprise Suite)",
            "request_source": "enterprise_dashboard",
            "compliance_tracking": {
                "gdpr_consent": True,
                "ccpa_consent": True,
                "sox_compliance": True,
                "data_retention": "7_years",
                "audit_level": "comprehensive"
            },
            "business_context": {
                "company_size": "enterprise",
                "monthly_spend": 150000,
                "optimization_tier": "enterprise",
                "contract_tier": "platinum"
            }
        }
    )
    contexts.append(enterprise_user)
    
    # Internal/admin user
    internal_user = UserExecutionContext(
        user_id="user_internal_99001122334455667788",
        thread_id="thread_internal_admin_88990011223344556677",
        run_id=f"run_internal_admin_{int(time.time())}_i1n2t3r4",
        websocket_client_id="ws_internal_99001122334455667788",
        agent_context={
            "agent_name": "admin_agent",
            "user_subscription": "internal",
            "session_id": "session_internal_99001122334455667788",
            "user_preferences": {
                "currency": "USD",
                "timezone": "UTC",
                "notification_preferences": ["email", "slack"],
                "admin_capabilities": ["user_management", "system_monitoring", "data_analysis"]
            },
            "execution_environment": {
                "region": "admin",
                "deployment": "internal",
                "feature_flags": ["all_features", "admin_tools", "debug_mode"]
            },
            "admin_features": {
                "full_access": True,
                "system_commands": True,
                "user_impersonation": True,
                "advanced_debugging": True
            }
        },
        audit_metadata={
            "client_ip": "10.0.0.100",
            "user_agent": "NetraAdmin/1.0.0 (Internal Tools)",
            "request_source": "admin_dashboard",
            "admin_context": {
                "staff_member": True,
                "access_level": "administrator",
                "department": "engineering",
                "clearance": "full_system"
            }
        }
    )
    contexts.append(internal_user)
    
    return contexts


@pytest.fixture(scope="function")
def websocket_context_scenarios(clean_context_registry, isolated_env) -> Dict[str, UserExecutionContext]:
    """Create WebSocket-specific context scenarios for real-time testing.
    
    Provides different WebSocket connection scenarios:
    - New connection
    - Reconnection
    - Mobile connection
    - High-frequency updates
    """
    scenarios = {}
    
    # New WebSocket connection
    scenarios["new_connection"] = UserExecutionContext(
        user_id="user_ws_new_12345678901234567890",
        thread_id="thread_ws_new_98765432109876543210",
        run_id=f"run_ws_new_{int(time.time())}_n1e2w3c4",
        websocket_client_id="ws_new_12345678901234567890",
        agent_context={
            "agent_name": "triage_agent",
            "websocket_state": "connecting",
            "connection_type": "new",
            "real_time_updates": True,
            "event_subscriptions": ["agent_started", "agent_thinking", "agent_completed"]
        },
        audit_metadata={
            "connection_start": datetime.now(timezone.utc).isoformat(),
            "connection_type": "websocket",
            "client_capabilities": ["real_time", "binary_support"],
            "connection_quality": "high"
        }
    )
    
    # WebSocket reconnection
    scenarios["reconnection"] = UserExecutionContext(
        user_id="user_ws_reconnect_11223344556677889900",
        thread_id="thread_ws_reconnect_99887766554433221100",
        run_id=f"run_ws_reconnect_{int(time.time())}_r1e2c3o4",
        websocket_client_id="ws_reconnect_11223344556677889900",
        agent_context={
            "agent_name": "cost_optimizer",
            "websocket_state": "reconnecting",
            "connection_type": "reconnection",
            "previous_session": "ws_old_99887766554433221100",
            "real_time_updates": True,
            "event_subscriptions": ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        },
        audit_metadata={
            "connection_start": datetime.now(timezone.utc).isoformat(),
            "reconnection_attempt": 2,
            "previous_disconnect_reason": "network_timeout",
            "connection_quality": "degraded"
        }
    )
    
    # Mobile WebSocket connection
    scenarios["mobile_connection"] = UserExecutionContext(
        user_id="user_ws_mobile_55443322110099887766",
        thread_id="thread_ws_mobile_44332211009988776655",
        run_id=f"run_ws_mobile_{int(time.time())}_m1o2b3i4",
        websocket_client_id="ws_mobile_55443322110099887766",
        agent_context={
            "agent_name": "mobile_agent",
            "websocket_state": "connected",
            "connection_type": "mobile",
            "device_type": "mobile",
            "real_time_updates": True,
            "battery_optimization": True,
            "event_subscriptions": ["agent_started", "agent_completed"]  # Reduced for battery
        },
        audit_metadata={
            "connection_start": datetime.now(timezone.utc).isoformat(),
            "device_info": {
                "platform": "iOS",
                "version": "16.5",
                "app_version": "2.1.0"
            },
            "connection_quality": "variable",
            "network_type": "cellular"
        }
    )
    
    # High-frequency updates connection
    scenarios["high_frequency"] = UserExecutionContext(
        user_id="user_ws_hf_77889900112233445566",
        thread_id="thread_ws_hf_66778899001122334455",
        run_id=f"run_ws_hf_{int(time.time())}_h1f2u3p4",
        websocket_client_id="ws_hf_77889900112233445566",
        agent_context={
            "agent_name": "real_time_analyzer",
            "websocket_state": "connected",
            "connection_type": "high_frequency",
            "real_time_updates": True,
            "update_frequency": "high",
            "event_subscriptions": [
                "agent_started", "agent_thinking", "tool_executing", 
                "tool_completed", "agent_completed", "progress_update",
                "status_change", "data_received"
            ]
        },
        audit_metadata={
            "connection_start": datetime.now(timezone.utc).isoformat(),
            "expected_event_rate": "10_per_second",
            "connection_quality": "premium",
            "buffer_size": "large"
        }
    )
    
    return scenarios


@pytest.fixture(scope="function")
def performance_test_contexts(clean_context_registry, isolated_env) -> List[UserExecutionContext]:
    """Create contexts specifically for performance and load testing.
    
    Provides contexts with varying data sizes and complexity for performance testing.
    """
    contexts = []
    
    # Small context (minimal data)
    small_context = UserExecutionContext(
        user_id="user_perf_small_12345678901234567890",
        thread_id="thread_perf_small_98765432109876543210",
        run_id=f"run_perf_small_{int(time.time())}_s1m2a3l4",
        agent_context={"agent_name": "simple_agent"},
        audit_metadata={"test_type": "small"}
    )
    contexts.append(small_context)
    
    # Medium context (moderate data)
    medium_context = UserExecutionContext(
        user_id="user_perf_medium_11223344556677889900",
        thread_id="thread_perf_medium_99887766554433221100",
        run_id=f"run_perf_medium_{int(time.time())}_m1e2d3i4",
        agent_context={
            "agent_name": "medium_agent",
            "data": list(range(100)),
            "config": {f"key_{i}": f"value_{i}" for i in range(50)}
        },
        audit_metadata={
            "test_type": "medium",
            "data_size": "moderate",
            "metadata": {f"audit_{i}": f"value_{i}" for i in range(25)}
        }
    )
    contexts.append(medium_context)
    
    # Large context (substantial data)
    large_data = {
        "large_array": list(range(1000)),
        "nested_data": {
            f"section_{i}": {
                f"subsection_{j}": list(range(10))
                for j in range(10)
            }
            for i in range(20)
        },
        "text_data": ["sample_text_" + "x" * 100] * 50
    }
    
    large_context = UserExecutionContext(
        user_id="user_perf_large_55443322110099887766",
        thread_id="thread_perf_large_44332211009988776655",
        run_id=f"run_perf_large_{int(time.time())}_l1a2r3g4",
        agent_context={
            "agent_name": "large_agent",
            "large_data": large_data,
            "performance_test": True
        },
        audit_metadata={
            "test_type": "large",
            "data_size": "substantial",
            "performance_metrics": {
                "expected_creation_time": "< 100ms",
                "expected_serialization_time": "< 50ms"
            }
        }
    )
    contexts.append(large_context)
    
    return contexts


@pytest.fixture(scope="function")
def concurrent_context_factory(clean_context_registry, isolated_env):
    """Factory for creating concurrent contexts with proper isolation.
    
    Returns a function that can create multiple contexts concurrently
    while ensuring proper isolation and unique identifiers.
    """
    def create_concurrent_contexts(count: int, base_name: str = "concurrent") -> List[UserExecutionContext]:
        """Create multiple contexts concurrently with unique identifiers."""
        contexts = []
        
        for i in range(count):
            context = UserExecutionContext(
                user_id=f"user_{base_name}_{i:06d}_{'x' * 20}",
                thread_id=f"thread_{base_name}_{i:06d}_{'y' * 15}",
                run_id=f"run_{base_name}_{i:06d}_{int(time.time() * 1000000)}",
                agent_context={
                    "concurrent_test": True,
                    "context_index": i,
                    "base_name": base_name,
                    "creation_time": time.perf_counter()
                },
                audit_metadata={
                    "concurrency_test": True,
                    "batch_name": base_name,
                    "context_number": i,
                    "total_contexts": count
                }
            )
            contexts.append(context)
        
        return contexts
    
    return create_concurrent_contexts


@pytest.fixture(scope="function")
async def async_context_manager():
    """Async context manager for testing context lifecycle management."""
    
    class AsyncContextManager:
        def __init__(self):
            self.managed_contexts = []
            self.cleanup_callbacks = []
        
        async def create_managed_context(
            self, 
            user_id: str, 
            thread_id: str, 
            run_id: str,
            **kwargs
        ) -> UserExecutionContext:
            """Create and manage a context with automatic cleanup."""
            context = UserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                **kwargs
            )
            self.managed_contexts.append(context)
            return context
        
        def add_cleanup_callback(self, callback):
            """Add a cleanup callback to be called during teardown."""
            self.cleanup_callbacks.append(callback)
        
        async def cleanup_all(self):
            """Clean up all managed contexts and run callbacks."""
            for callback in self.cleanup_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    print(f"Cleanup callback error: {e}")
            
            self.managed_contexts.clear()
            self.cleanup_callbacks.clear()
    
    manager = AsyncContextManager()
    yield manager
    await manager.cleanup_all()


@pytest.fixture(scope="function")
def context_hierarchy_builder(clean_context_registry, isolated_env):
    """Builder for creating complex context hierarchies.
    
    Provides utilities for building parent-child context relationships
    with proper depth tracking and hierarchy management.
    """
    
    class ContextHierarchyBuilder:
        def __init__(self):
            self.root_contexts = []
            self.all_contexts = []
        
        def create_root_context(self, name: str) -> UserExecutionContext:
            """Create a root context for hierarchy building."""
            root_context = UserExecutionContext(
                user_id=f"user_hierarchy_{name}_12345678901234567890",
                thread_id=f"thread_hierarchy_{name}_98765432109876543210",
                run_id=f"run_hierarchy_{name}_{int(time.time())}_root",
                agent_context={
                    "hierarchy_name": name,
                    "context_type": "root",
                    "hierarchy_test": True
                },
                audit_metadata={
                    "hierarchy_role": "root",
                    "hierarchy_name": name
                }
            )
            
            self.root_contexts.append(root_context)
            self.all_contexts.append(root_context)
            return root_context
        
        def build_hierarchy(self, root_context: UserExecutionContext, depth: int) -> List[UserExecutionContext]:
            """Build a hierarchy of specified depth from a root context."""
            hierarchy = [root_context]
            current_parent = root_context
            
            for level in range(1, depth + 1):
                child_context = current_parent.create_child_context(
                    f"level_{level}_operation",
                    additional_agent_context={
                        "hierarchy_level": level,
                        "level_name": f"level_{level}"
                    },
                    additional_audit_metadata={
                        "hierarchy_level": level,
                        "parent_level": level - 1
                    }
                )
                hierarchy.append(child_context)
                self.all_contexts.append(child_context)
                current_parent = child_context
            
            return hierarchy
        
        def create_sibling_contexts(self, parent_context: UserExecutionContext, count: int) -> List[UserExecutionContext]:
            """Create multiple sibling contexts from the same parent."""
            siblings = []
            
            for i in range(count):
                sibling = parent_context.create_child_context(
                    f"sibling_{i}_operation",
                    additional_agent_context={
                        "sibling_index": i,
                        "sibling_count": count
                    },
                    additional_audit_metadata={
                        "sibling_info": f"sibling_{i}_of_{count}"
                    }
                )
                siblings.append(sibling)
                self.all_contexts.append(sibling)
            
            return siblings
        
        def get_all_contexts(self) -> List[UserExecutionContext]:
            """Get all contexts created by this builder."""
            return self.all_contexts.copy()
        
        def get_contexts_by_depth(self, depth: int) -> List[UserExecutionContext]:
            """Get all contexts at a specific depth level."""
            return [ctx for ctx in self.all_contexts if ctx.operation_depth == depth]
    
    return ContextHierarchyBuilder()


# Export all fixtures for easy import
__all__ = [
    "clean_context_registry",
    "realistic_user_context", 
    "multi_user_contexts",
    "websocket_context_scenarios",
    "performance_test_contexts",
    "concurrent_context_factory",
    "async_context_manager",
    "context_hierarchy_builder"
]