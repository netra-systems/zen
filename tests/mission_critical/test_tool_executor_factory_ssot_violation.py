"""
MISSION CRITICAL: ToolExecutorFactory vs UnifiedToolDispatcher SSOT Violation Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Infrastructure
- Business Goal: Protect $500K+ ARR chat functionality reliability
- Value Impact: Prevent unpredictable tool execution routing that breaks golden path
- Strategic Impact: Eliminate WebSocket event loss causing user experience degradation

These tests PROVE the SSOT violation exists and will validate when consolidation is complete.
GitHub Issue: #219
"""

import pytest
import asyncio
import time
import gc
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

# PHASE 2: Import SSOT factory and legacy systems to validate consolidation
try:
    # NEW SSOT FACTORY (Phase 2 consolidation target)
    from netra_backend.app.factories.tool_dispatcher_factory import (
        ToolDispatcherFactory,
        get_tool_dispatcher_factory,
        create_tool_dispatcher
    )
    SSOT_TOOL_DISPATCHER_FACTORY_AVAILABLE = True
except ImportError:
    SSOT_TOOL_DISPATCHER_FACTORY_AVAILABLE = False

try:
    # DEPRECATED: Legacy ToolExecutorFactory (should redirect to SSOT factory)
    from netra_backend.app.agents.tool_executor_factory import (
        ToolExecutorFactory as LegacyToolExecutorFactory, 
        get_tool_executor_factory as get_legacy_tool_executor_factory
    )
    LEGACY_TOOL_EXECUTOR_FACTORY_AVAILABLE = True
except ImportError:
    LEGACY_TOOL_EXECUTOR_FACTORY_AVAILABLE = False

try:
    # DEPRECATED: UnifiedToolDispatcher (should redirect to SSOT factory)
    from netra_backend.app.core.tools.unified_tool_dispatcher import (
        UnifiedToolDispatcher,
        UnifiedToolDispatcherFactory
    )
    UNIFIED_TOOL_DISPATCHER_AVAILABLE = True
except ImportError:
    UNIFIED_TOOL_DISPATCHER_AVAILABLE = False

try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    USER_EXECUTION_CONTEXT_AVAILABLE = True
except ImportError:
    USER_EXECUTION_CONTEXT_AVAILABLE = False


class TestToolExecutorFactorySSotViolation(SSotBaseTestCase):
    """
    MISSION CRITICAL: Tests that SHOULD FAIL until SSOT consolidation is complete.
    
    These tests prove the existence of duplicate tool execution systems that create
    unpredictable routing and golden path failures.
    """
    
    def setup_method(self, method=None):
        """Setup for SSOT violation detection."""
        super().setup_method(method)
        self.record_metric("test_category", "tool_executor_factory_ssot_violation")
        
        # Track systems and violations
        self._execution_systems = []
        self._websocket_adapters = []
        self._tool_registries = []
        self._violations_detected = []
        
        # Test user context for isolation testing
        if USER_EXECUTION_CONTEXT_AVAILABLE:
            self._test_user_context = UserExecutionContext(
                user_id="ssot_violation_test_user",
                thread_id="ssot_violation_test_thread", 
                run_id="ssot_violation_test_run"
            )
    
    @pytest.mark.mission_critical
    def test_duplicate_tool_execution_systems_exist(self):
        """
        SHOULD FAIL: Prove both ToolExecutorFactory and UnifiedToolDispatcher exist.
        
        This test SHOULD FAIL until SSOT consolidation removes the duplication.
        When fixed, only one tool execution system should exist.
        """
        # Skip if modules not available
        if not TOOL_EXECUTOR_FACTORY_AVAILABLE or not UNIFIED_TOOL_DISPATCHER_AVAILABLE:
            pytest.skip("Tool execution modules not available")
        
        # Detect competing tool execution systems
        competing_systems = []
        
        # System 1: ToolExecutorFactory
        try:
            factory = ToolExecutorFactory()
            competing_systems.append({
                "name": "ToolExecutorFactory",
                "class": ToolExecutorFactory,
                "instance": factory,
                "module": "netra_backend.app.agents.tool_executor_factory"
            })
            self._execution_systems.append(factory)
        except Exception as e:
            competing_systems.append({
                "name": "ToolExecutorFactory", 
                "class": ToolExecutorFactory,
                "error": str(e),
                "module": "netra_backend.app.agents.tool_executor_factory"
            })
        
        # System 2: UnifiedToolDispatcher - check forbidden direct instantiation
        try:
            # This should raise RuntimeError due to factory enforcement
            unified_dispatcher = UnifiedToolDispatcher()
            competing_systems.append({
                "name": "UnifiedToolDispatcher",
                "class": UnifiedToolDispatcher,
                "instance": unified_dispatcher,
                "module": "netra_backend.app.core.tools.unified_tool_dispatcher",
                "error": "Direct instantiation should be forbidden"
            })
        except RuntimeError as e:
            # Expected - direct instantiation is forbidden
            competing_systems.append({
                "name": "UnifiedToolDispatcher",
                "class": UnifiedToolDispatcher,
                "factory_enforced": True,
                "error": str(e),
                "module": "netra_backend.app.core.tools.unified_tool_dispatcher"
            })
        
        # VIOLATION DETECTION: Multiple tool execution systems exist
        active_systems = [s for s in competing_systems if "instance" in s]
        factory_enforced_systems = [s for s in competing_systems if s.get("factory_enforced")]
        
        # Record violations
        if len(active_systems) > 0:
            self._violations_detected.append({
                "type": "DUPLICATE_TOOL_EXECUTION_SYSTEMS",
                "severity": "CRITICAL",
                "description": f"Found {len(active_systems)} active tool execution systems",
                "systems": [s["name"] for s in active_systems],
                "business_impact": "Unpredictable tool execution routing"
            })
        
        if len(factory_enforced_systems) > 0:
            self._violations_detected.append({
                "type": "FACTORY_PATTERN_INCONSISTENCY", 
                "severity": "HIGH",
                "description": f"Found {len(factory_enforced_systems)} factory-enforced systems",
                "systems": [s["name"] for s in factory_enforced_systems],
                "business_impact": "Inconsistent instantiation patterns"
            })
        
        # Log detailed findings
        for system in competing_systems:
            print(f"\nTool Execution System Detected:")
            print(f"  Name: {system['name']}")
            print(f"  Module: {system['module']}")
            print(f"  Status: {'ACTIVE' if 'instance' in system else 'FACTORY_ENFORCED' if system.get('factory_enforced') else 'ERROR'}")
            if "error" in system:
                print(f"  Error: {system['error']}")
        
        # ASSERT VIOLATION: This test SHOULD FAIL until consolidation complete
        # When fixed, there should be only ONE tool execution system
        total_systems = len(active_systems) + len(factory_enforced_systems)
        
        if total_systems > 1:
            violation_summary = f"""
SSOT VIOLATION DETECTED: Multiple Tool Execution Systems
- Active Systems: {len(active_systems)}
- Factory-Enforced Systems: {len(factory_enforced_systems)}
- Total Systems: {total_systems}
- Expected: 1 (after SSOT consolidation)

This test SHOULD FAIL until GitHub Issue #219 is resolved.
Systems Found: {[s['name'] for s in competing_systems]}
"""
            # This assertion should FAIL until the violation is fixed
            assert False, violation_summary
        
        # When the violation is fixed, this should pass
        assert total_systems == 1, "SSOT consolidation complete - only one tool execution system should exist"
    
    @pytest.mark.mission_critical
    def test_websocket_adapter_proliferation(self):
        """
        SHOULD FAIL: Prove 3 different WebSocket adapter implementations exist.
        
        This test detects WebSocket adapter proliferation that causes event delivery inconsistency.
        """
        # Skip if modules not available
        if not TOOL_EXECUTOR_FACTORY_AVAILABLE or not UNIFIED_TOOL_DISPATCHER_AVAILABLE:
            pytest.skip("Tool execution modules not available") 
        
        # Detect WebSocket adapter implementations
        websocket_adapters = []
        
        # Adapter 1: From ToolExecutorFactory
        try:
            if hasattr(ToolExecutorFactory, '__init__'):
                factory = ToolExecutorFactory()
                if hasattr(factory, '_create_websocket_bridge') or hasattr(factory, 'websocket_manager'):
                    websocket_adapters.append({
                        "name": "ToolExecutorFactory WebSocket Bridge",
                        "source": "ToolExecutorFactory",
                        "module": "netra_backend.app.agents.tool_executor_factory",
                        "type": "Factory-based adapter"
                    })
        except Exception as e:
            pass
        
        # Adapter 2: From UnifiedToolDispatcher
        try:
            # Check for WebSocket adapter methods
            if hasattr(UnifiedToolDispatcher, '_create_websocket_bridge_adapter'):
                websocket_adapters.append({
                    "name": "UnifiedToolDispatcher WebSocket Adapter",
                    "source": "UnifiedToolDispatcher", 
                    "module": "netra_backend.app.core.tools.unified_tool_dispatcher",
                    "type": "Dispatcher-based adapter"
                })
        except Exception as e:
            pass
        
        # Adapter 3: Look for other WebSocket bridge implementations
        try:
            # Search for WebSocket bridge classes
            adapter_classes = [
                "WebSocketBridgeAdapter",
                "AgentWebSocketBridgeAdapter", 
                "WebSocketEventEmitter",
                "UnifiedWebSocketEmitter"
            ]
            
            for adapter_class in adapter_classes:
                try:
                    # Try to find in various modules
                    modules_to_check = [
                        "netra_backend.app.websocket_core",
                        "netra_backend.app.agents",
                        "netra_backend.app.core.tools"
                    ]
                    
                    for module_name in modules_to_check:
                        try:
                            import importlib
                            module = importlib.import_module(module_name)
                            if hasattr(module, adapter_class):
                                websocket_adapters.append({
                                    "name": adapter_class,
                                    "source": module_name,
                                    "module": module_name,
                                    "type": "Standalone adapter class"
                                })
                                break
                        except ImportError:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        
        self._websocket_adapters = websocket_adapters
        
        # VIOLATION DETECTION: Multiple WebSocket adapter implementations
        if len(websocket_adapters) >= 3:
            self._violations_detected.append({
                "type": "WEBSOCKET_ADAPTER_PROLIFERATION",
                "severity": "CRITICAL", 
                "description": f"Found {len(websocket_adapters)} WebSocket adapter implementations",
                "adapters": [a["name"] for a in websocket_adapters],
                "business_impact": "Inconsistent WebSocket event delivery breaking chat UX"
            })
        
        # Log findings
        print(f"\nWebSocket Adapter Detection Results:")
        print(f"Total adapters found: {len(websocket_adapters)}")
        for adapter in websocket_adapters:
            print(f"  - {adapter['name']} ({adapter['type']}) from {adapter['source']}")
        
        # ASSERT VIOLATION: This test SHOULD FAIL until adapter consolidation
        if len(websocket_adapters) >= 3:
            violation_summary = f"""
WEBSOCKET ADAPTER PROLIFERATION DETECTED: {len(websocket_adapters)} adapters found
Expected: 1 unified WebSocket adapter

This causes inconsistent event delivery breaking the golden path user experience.
Adapters Found: {[a['name'] for a in websocket_adapters]}

This test SHOULD FAIL until GitHub Issue #219 WebSocket adapter consolidation is complete.
"""
            # This assertion should FAIL until the violation is fixed
            assert False, violation_summary
        
        # When fixed, should have only one adapter
        assert len(websocket_adapters) <= 1, "WebSocket adapter consolidation complete"
    
    @pytest.mark.mission_critical
    def test_tool_registry_duplication(self):
        """
        SHOULD FAIL: Prove multiple ToolRegistry instances created causing memory waste.
        
        This test detects tool registry duplication that leads to inconsistent tool state.
        """
        # Skip if modules not available
        if not TOOL_EXECUTOR_FACTORY_AVAILABLE or not UNIFIED_TOOL_DISPATCHER_AVAILABLE:
            pytest.skip("Tool execution modules not available")
        
        # Track tool registry instances
        tool_registries = []
        
        # Registry 1: From ToolExecutorFactory
        try:
            factory = ToolExecutorFactory()
            # Look for registry creation in factory methods
            if hasattr(factory, 'create_tool_executor'):
                # Check for registry creation patterns
                tool_registries.append({
                    "name": "ToolExecutorFactory Registry",
                    "source": "ToolExecutorFactory", 
                    "instance_id": id(factory),
                    "type": "Factory-created registry"
                })
        except Exception as e:
            pass
        
        # Registry 2: From UnifiedToolDispatcher factory
        try:
            if USER_EXECUTION_CONTEXT_AVAILABLE:
                # Use factory method to create dispatcher (should create registry)
                dispatcher_factory = UnifiedToolDispatcherFactory()
                if hasattr(dispatcher_factory, 'create_for_request'):
                    tool_registries.append({
                        "name": "UnifiedToolDispatcher Registry",
                        "source": "UnifiedToolDispatcherFactory",
                        "instance_id": id(dispatcher_factory),
                        "type": "Dispatcher-created registry"
                    })
        except Exception as e:
            pass
        
        # Registry 3: Look for direct registry imports
        try:
            from netra_backend.app.core.registry.universal_registry import ToolRegistry, UniversalRegistry
            
            # Create test registries to simulate duplication
            registry1 = ToolRegistry() if hasattr(ToolRegistry, '__call__') else None
            registry2 = UniversalRegistry() if hasattr(UniversalRegistry, '__call__') else None
            
            if registry1:
                tool_registries.append({
                    "name": "Direct ToolRegistry",
                    "source": "Direct import",
                    "instance_id": id(registry1),
                    "type": "Direct registry instance"
                })
            
            if registry2:
                tool_registries.append({
                    "name": "Direct UniversalRegistry", 
                    "source": "Direct import",
                    "instance_id": id(registry2),
                    "type": "Universal registry instance"
                })
        except ImportError:
            pass
        except Exception:
            pass
        
        self._tool_registries = tool_registries
        
        # VIOLATION DETECTION: Multiple registry instances
        unique_registries = len(set(r["instance_id"] for r in tool_registries))
        
        if unique_registries > 1:
            self._violations_detected.append({
                "type": "TOOL_REGISTRY_DUPLICATION",
                "severity": "HIGH",
                "description": f"Found {unique_registries} unique tool registry instances",
                "registries": [r["name"] for r in tool_registries],
                "business_impact": "Memory waste and tool state inconsistency"
            })
        
        # Log findings
        print(f"\nTool Registry Duplication Detection:")
        print(f"Total registries found: {len(tool_registries)}")
        print(f"Unique instances: {unique_registries}")
        for registry in tool_registries:
            print(f"  - {registry['name']} ({registry['type']}) ID: {registry['instance_id']}")
        
        # ASSERT VIOLATION: This test SHOULD FAIL until registry consolidation  
        if unique_registries > 1:
            violation_summary = f"""
TOOL REGISTRY DUPLICATION DETECTED: {unique_registries} unique registries
Expected: 1 shared registry or proper per-request isolation

This causes memory waste and tool state inconsistency.
Registries Found: {[r['name'] for r in tool_registries]}

This test SHOULD FAIL until GitHub Issue #219 registry consolidation is complete.
"""
            # This assertion should FAIL until the violation is fixed
            assert False, violation_summary
        
        # When fixed, should have proper registry management
        assert unique_registries <= 1, "Tool registry consolidation complete"
    
    @pytest.mark.mission_critical 
    async def test_inconsistent_tool_execution_routing(self):
        """
        SHOULD FAIL: Prove tool calls hit different execution systems unpredictably.
        
        This test demonstrates golden path failures due to routing conflicts.
        """
        # Skip if modules not available
        if not (TOOL_EXECUTOR_FACTORY_AVAILABLE and UNIFIED_TOOL_DISPATCHER_AVAILABLE and USER_EXECUTION_CONTEXT_AVAILABLE):
            pytest.skip("Required modules not available")
        
        execution_routes = []
        
        # Route 1: Through ToolExecutorFactory
        try:
            factory = ToolExecutorFactory()
            if hasattr(factory, 'create_tool_executor'):
                execution_routes.append({
                    "name": "ToolExecutorFactory Route",
                    "system": "ToolExecutorFactory",
                    "method": "create_tool_executor",
                    "available": True
                })
        except Exception as e:
            execution_routes.append({
                "name": "ToolExecutorFactory Route",
                "system": "ToolExecutorFactory", 
                "error": str(e),
                "available": False
            })
        
        # Route 2: Through UnifiedToolDispatcher factory
        try:
            # Use factory method instead of direct instantiation
            if hasattr(UnifiedToolDispatcherFactory, 'create_for_request'):
                execution_routes.append({
                    "name": "UnifiedToolDispatcher Route",
                    "system": "UnifiedToolDispatcher",
                    "method": "create_for_request",
                    "available": True
                })
        except Exception as e:
            execution_routes.append({
                "name": "UnifiedToolDispatcher Route",
                "system": "UnifiedToolDispatcher",
                "error": str(e),
                "available": False
            })
        
        # Route 3: Direct UnifiedToolDispatcher (should be forbidden)
        try:
            dispatcher = UnifiedToolDispatcher()
            execution_routes.append({
                "name": "Direct UnifiedToolDispatcher Route",
                "system": "UnifiedToolDispatcher",
                "method": "direct_instantiation",
                "available": True,
                "violation": "Direct instantiation should be forbidden"
            })
        except RuntimeError as e:
            execution_routes.append({
                "name": "Direct UnifiedToolDispatcher Route", 
                "system": "UnifiedToolDispatcher",
                "method": "direct_instantiation",
                "available": False,
                "factory_enforced": True,
                "error": str(e)
            })
        
        # Count available routes
        available_routes = [r for r in execution_routes if r.get("available")]
        factory_enforced_routes = [r for r in execution_routes if r.get("factory_enforced")]
        
        # VIOLATION DETECTION: Multiple available execution routes
        if len(available_routes) > 1:
            self._violations_detected.append({
                "type": "INCONSISTENT_TOOL_EXECUTION_ROUTING",
                "severity": "CRITICAL",
                "description": f"Found {len(available_routes)} different tool execution routes",
                "routes": [r["name"] for r in available_routes],
                "business_impact": "Unpredictable routing causing golden path failures"
            })
        
        # Log findings
        print(f"\nTool Execution Routing Analysis:")
        print(f"Available routes: {len(available_routes)}")
        print(f"Factory-enforced routes: {len(factory_enforced_routes)}")
        for route in execution_routes:
            status = "AVAILABLE" if route.get("available") else "BLOCKED" if route.get("factory_enforced") else "ERROR"
            print(f"  - {route['name']}: {status}")
            if "error" in route:
                print(f"    Error: {route['error']}")
            if "violation" in route:
                print(f"    Violation: {route['violation']}")
        
        # ASSERT VIOLATION: This test SHOULD FAIL until routing is unified
        if len(available_routes) > 1:
            violation_summary = f"""
INCONSISTENT TOOL EXECUTION ROUTING DETECTED: {len(available_routes)} routes available
Expected: 1 unified tool execution route

This causes unpredictable behavior where tool calls may hit different systems,
leading to inconsistent WebSocket events and golden path failures.

Routes Found: {[r['name'] for r in available_routes]}

This test SHOULD FAIL until GitHub Issue #219 routing consolidation is complete.
"""
            # This assertion should FAIL until the violation is fixed
            assert False, violation_summary
        
        # When fixed, should have only one execution route
        assert len(available_routes) <= 1, "Tool execution routing consolidation complete"
    
    def teardown_method(self, method=None):
        """Cleanup and report violations detected."""
        # Report all violations detected
        if self._violations_detected:
            print(f"\n{'='*80}")
            print("SSOT VIOLATIONS DETECTED - BLOCKING GOLDEN PATH")
            print(f"{'='*80}")
            
            for violation in self._violations_detected:
                print(f"\nVIOLATION: {violation['type']}")
                print(f"Severity: {violation['severity']}")
                print(f"Description: {violation['description']}")
                print(f"Business Impact: {violation['business_impact']}")
                if "systems" in violation:
                    print(f"Systems: {violation['systems']}")
                if "adapters" in violation:
                    print(f"Adapters: {violation['adapters']}")
                if "registries" in violation:
                    print(f"Registries: {violation['registries']}")
                if "routes" in violation:
                    print(f"Routes: {violation['routes']}")
            
            print(f"\nTotal violations: {len(self._violations_detected)}")
            print("These violations MUST be resolved to complete GitHub Issue #219")
            print(f"{'='*80}")
        
        # Cleanup test resources
        for system in self._execution_systems:
            try:
                if hasattr(system, 'cleanup'):
                    asyncio.create_task(system.cleanup())
            except Exception:
                pass
        
        # Force garbage collection to clean up instances
        gc.collect()
        
        super().teardown_method(method)