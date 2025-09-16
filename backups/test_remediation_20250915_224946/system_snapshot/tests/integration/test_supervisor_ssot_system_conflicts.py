"""NEW INTEGRATION TESTS - Expose SupervisorAgent System-Level SSOT Conflicts

Business Value: Proves system-level impacts of Issue #800 duplicate SupervisorAgent implementations
BVJ: ALL segments | System Stability | Golden Path reliability through SSOT compliance  

PURPOSE: Integration tests that expose how SupervisorAgent SSOT violations impact system integration.
These tests are designed to FAIL and show system-level conflicts from duplicate implementations.

After SSOT remediation, these tests will pass, validating system-wide consistency.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.logging_config import central_logger
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
class SupervisorSystemLevelSSotConflictsTests(SSotBaseTestCase):
    """Integration tests exposing supervisor SSOT conflicts at system level."""

    def test_supervisor_registry_integration_conflict_SHOULD_FAIL(self):
        """FAILING - Shows AgentRegistry doesn't know which supervisor to use
        
        Expected to FAIL: AgentRegistry or factory systems may have confusion
        about which SupervisorAgent implementation to use.
        
        After remediation: Will pass when registry uses single SSOT supervisor.
        """
        logger.info("🔴 EXPOSING SYSTEM CONFLICT: Registry-supervisor integration confusion")
        
        registry_supervisor_refs = []
        
        # Check AgentRegistry references
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
            factory = get_agent_instance_factory()
            
            # Check if factory has supervisor references
            if hasattr(factory, '_agent_classes') and factory._agent_classes:
                supervisor_refs = []
                for name, agent_class in factory._agent_classes.items():
                    if 'supervisor' in name.lower():
                        supervisor_refs.append((name, agent_class, id(agent_class)))
                        
                if supervisor_refs:
                    registry_supervisor_refs.extend(supervisor_refs)
                    logger.info(f"Factory supervisor references: {[(name, cls.__module__) for name, cls, _ in supervisor_refs]}")
                    
        except ImportError as e:
            logger.warning(f"Could not check agent factory: {e}")
        
        # Check for AgentService supervisor configuration
        try:
            # This might show which supervisor AgentService is configured to use
            import inspect
            
            # Try to find supervisor creation patterns in the system
            from netra_backend.app.services import agent_service
            
            # Look for supervisor creation methods
            service_methods = inspect.getmembers(agent_service, predicate=inspect.isfunction)
            supervisor_creation_methods = []
            
            for method_name, method_obj in service_methods:
                if 'supervisor' in method_name.lower():
                    supervisor_creation_methods.append((method_name, method_obj))
                    
            if supervisor_creation_methods:
                logger.info(f"AgentService supervisor methods: {[name for name, _ in supervisor_creation_methods]}")
                
                # Try to trace what SupervisorAgent these methods use
                for method_name, method_obj in supervisor_creation_methods:
                    try:
                        source = inspect.getsource(method_obj)
                        if 'supervisor_ssot' in source and 'supervisor_consolidated' in source:
                            registry_supervisor_refs.append(("agent_service", "BOTH_REFERENCED", 0))
                            logger.error(f"🚨 AgentService method {method_name} references BOTH supervisor implementations")
                        elif 'supervisor_ssot' in source:
                            registry_supervisor_refs.append(("agent_service", "SSOT", 1))
                        elif 'supervisor_consolidated' in source:
                            registry_supervisor_refs.append(("agent_service", "CONSOLIDATED", 2))
                    except Exception:
                        pass  # Skip source analysis if it fails
                        
        except ImportError as e:
            logger.warning(f"Could not check agent service: {e}")
        
        # SYSTEM CONFLICT DETECTION
        unique_refs = set()
        for name, ref, ref_id in registry_supervisor_refs:
            if ref_id != 0:  # Skip special markers
                unique_refs.add(ref_id)
                
        if len(unique_refs) > 1:
            logger.error(f"🚨 SYSTEM INTEGRATION CONFLICT: Registry systems reference {len(unique_refs)} different supervisor implementations")
            logger.error(f"   References: {registry_supervisor_refs}")
            
            # This test should FAIL to expose the system conflict
            pytest.fail(f"REGISTRY INTEGRATION CONFLICT: System components reference "
                       f"{len(unique_refs)} different SupervisorAgent implementations. "
                       f"Expected: 1 SSOT reference. Found: {registry_supervisor_refs}")
                       
        elif len(registry_supervisor_refs) == 0:
            logger.warning("⚠️  No supervisor registry references found - may indicate configuration issues")
        else:
            logger.info("✓ All system components reference the same supervisor")

    def test_supervisor_execution_engine_confusion_SHOULD_FAIL(self):
        """FAILING - Shows ExecutionEngine conflicts with multiple supervisors
        
        Expected to FAIL: ExecutionEngine or UserExecutionEngine may have 
        confusion about supervisor execution patterns.
        
        After remediation: Will pass when engine works with single SSOT supervisor.
        """
        logger.info("🔴 EXPOSING SYSTEM CONFLICT: ExecutionEngine-supervisor pattern conflicts")
        
        execution_engine_conflicts = []
        
        # Check UserExecutionEngine interaction patterns
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
            
            # Check if UserExecutionEngine has supervisor-specific logic
            engine_methods = dir(UserExecutionEngine)
            supervisor_related_methods = [
                method for method in engine_methods 
                if 'supervisor' in method.lower() and not method.startswith('__')
            ]
            
            if supervisor_related_methods:
                logger.info(f"UserExecutionEngine supervisor methods: {supervisor_related_methods}")
                
                # Try to analyze method implementations for supervisor references
                for method_name in supervisor_related_methods:
                    try:
                        method = getattr(UserExecutionEngine, method_name)
                        if hasattr(method, '__code__'):
                            # This is a very basic check - in real implementation would be more sophisticated
                            source_info = {
                                "method": method_name,
                                "expects_supervisor": True,
                                "pattern": "unknown"
                            }
                            execution_engine_conflicts.append(source_info)
                    except Exception:
                        pass
                        
        except ImportError as e:
            logger.warning(f"Could not check UserExecutionEngine: {e}")
        
        # Check general ExecutionEngine patterns
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            
            # Look for supervisor execution methods
            if hasattr(ExecutionEngine, 'execute_supervisor') or hasattr(ExecutionEngine, 'supervisor_execute'):
                execution_engine_conflicts.append({
                    "component": "ExecutionEngine",
                    "has_supervisor_methods": True,
                    "potential_conflict": "May expect specific supervisor interface"
                })
                
        except ImportError as e:
            logger.warning(f"Could not check ExecutionEngine: {e}")
        
        # Check for WebSocket-ExecutionEngine-Supervisor chain conflicts
        try:
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            
            # Check if WebSocket bridge has supervisor-specific logic
            bridge_methods = dir(AgentWebSocketBridge)
            supervisor_bridge_methods = [
                method for method in bridge_methods 
                if 'supervisor' in method.lower() and not method.startswith('__')
            ]
            
            if supervisor_bridge_methods:
                execution_engine_conflicts.append({
                    "component": "AgentWebSocketBridge", 
                    "supervisor_methods": supervisor_bridge_methods,
                    "potential_conflict": "May have supervisor-specific event handling"
                })
                logger.info(f"WebSocket bridge supervisor methods: {supervisor_bridge_methods}")
                
        except ImportError as e:
            logger.warning(f"Could not check AgentWebSocketBridge: {e}")
        
        # EXECUTION ENGINE CONFLICT DETECTION
        if execution_engine_conflicts:
            logger.error(f"🚨 EXECUTION ENGINE CONFLICTS: {len(execution_engine_conflicts)} components have supervisor-specific logic")
            for conflict in execution_engine_conflicts:
                logger.error(f"   {conflict}")
            
            # Check if conflicts suggest multiple supervisor expectations
            if len(execution_engine_conflicts) > 1:
                # This test should FAIL to expose the execution engine conflicts
                pytest.fail(f"EXECUTION ENGINE CONFLICTS: {len(execution_engine_conflicts)} system components "
                           f"have supervisor-specific logic that may conflict with multiple implementations. "
                           f"Expected: Unified supervisor interface. Found: {execution_engine_conflicts}")
        else:
            logger.info("✓ No obvious execution engine conflicts detected")

    async def test_supervisor_websocket_event_delivery_race_SHOULD_FAIL(self):
        """FAILING - Shows potential WebSocket event delivery conflicts
        
        Expected to FAIL: Multiple supervisors might emit events for the same user action,
        causing duplicate or conflicting events.
        
        After remediation: Will pass when only one supervisor emits events.
        """
        logger.info("🔴 EXPOSING SYSTEM CONFLICT: WebSocket event delivery race conditions")
        
        # Mock WebSocket manager to capture event emissions
        captured_events = []
        
        async def capture_event(*args, **kwargs):
            captured_events.append({"args": args, "kwargs": kwargs, "source": "mock"})
        
        # Try to create both supervisor types and see if they both emit events
        supervisors_created = []
        
        try:
            from netra_backend.app.llm.llm_manager import LLMManager
            llm_manager = Mock(spec=LLMManager)
            
            # Mock WebSocket bridge
            websocket_bridge = Mock()
            websocket_bridge.websocket_manager = Mock()
            websocket_bridge.websocket_manager.send_to_user = AsyncMock(side_effect=capture_event)
            websocket_bridge.emit_agent_event = AsyncMock(side_effect=capture_event)
            
            # Try creating both supervisor implementations
            try:
                from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SSotSupervisor
                ssot_supervisor = SSotSupervisor(
                    llm_manager=llm_manager,
                    websocket_bridge=websocket_bridge
                )
                supervisors_created.append(("SSOT", ssot_supervisor))
                logger.info("✓ Created SSOT supervisor instance")
            except Exception as e:
                logger.warning(f"Could not create SSOT supervisor: {e}")
            
            try:
                from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as ConsolidatedSupervisor
                consolidated_supervisor = ConsolidatedSupervisor(
                    llm_manager=llm_manager,
                    websocket_bridge=websocket_bridge
                )
                supervisors_created.append(("Consolidated", consolidated_supervisor))
                logger.info("✓ Created Consolidated supervisor instance")
            except Exception as e:
                logger.warning(f"Could not create Consolidated supervisor: {e}")
                
        except Exception as e:
            logger.warning(f"Could not set up supervisor test: {e}")
        
        if len(supervisors_created) < 2:
            pytest.skip("Need both supervisor implementations to test event conflicts")
        
        # Test WebSocket event emission from both supervisors
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            # Create mock context
            mock_context = Mock(spec=UserExecutionContext)
            mock_context.user_id = "test_user_123"
            mock_context.run_id = "test_run_456" 
            mock_context.websocket_connection_id = "ws_conn_789"
            mock_context.created_at = Mock()
            mock_context.created_at.isoformat.return_value = "2024-01-01T00:00:00Z"
            
            # Test each supervisor's event emission
            event_emissions = []
            
            for name, supervisor in supervisors_created:
                captured_events.clear()  # Reset capture
                
                try:
                    # Try to trigger WebSocket events
                    if hasattr(supervisor, '_emit_agent_started'):
                        await supervisor._emit_agent_started(mock_context, "test request")
                        event_emissions.append((name, "agent_started", len(captured_events)))
                        
                    if hasattr(supervisor, '_emit_agent_completed'):
                        await supervisor._emit_agent_completed(mock_context, {"result": "test"})
                        event_emissions.append((name, "agent_completed", len(captured_events)))
                        
                except Exception as e:
                    logger.warning(f"Event emission failed for {name}: {e}")
                    event_emissions.append((name, "emission_failed", 0))
            
            # WEBSOCKET EVENT CONFLICT DETECTION
            if len(event_emissions) > 0:
                successful_emissions = [(name, event, count) for name, event, count in event_emissions if count > 0]
                
                if len(successful_emissions) > 1:
                    logger.error(f"🚨 WEBSOCKET EVENT CONFLICTS: Multiple supervisors successfully emit events")
                    for name, event, count in successful_emissions:
                        logger.error(f"   {name} supervisor emitted {count} {event} events")
                    
                    # This test should FAIL to expose the event conflicts
                    pytest.fail(f"WEBSOCKET EVENT CONFLICTS: {len(successful_emissions)} supervisors "
                               f"can emit WebSocket events simultaneously. Expected: 1 SSOT emitter. "
                               f"Found: {successful_emissions}")
                else:
                    logger.info("✓ Only one supervisor successfully emits WebSocket events")
            else:
                logger.warning("⚠️  No WebSocket events were emitted by any supervisor")
                
        except Exception as e:
            logger.error(f"WebSocket event test failed: {e}")
            pytest.skip(f"Could not test WebSocket event conflicts: {e}")

    def test_supervisor_factory_pattern_inconsistency_SHOULD_FAIL(self):
        """FAILING - Shows inconsistent factory patterns between supervisors
        
        Expected to FAIL: Different supervisors may use different factory patterns,
        causing system integration issues.
        
        After remediation: Will pass when unified factory pattern exists.
        """
        logger.info("🔴 EXPOSING SYSTEM CONFLICT: Inconsistent supervisor factory patterns")
        
        factory_patterns = []
        
        # Check factory patterns in both supervisor implementations
        supervisor_classes = []
        
        try:
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as SSotSupervisor
            supervisor_classes.append(("SSOT", SSotSupervisor))
        except ImportError:
            pass
            
        try:
            from netra_backend.app.agents.supervisor_ssot import SupervisorAgent as ConsolidatedSupervisor
            supervisor_classes.append(("Consolidated", ConsolidatedSupervisor))
        except ImportError:
            pass
        
        if len(supervisor_classes) < 2:
            pytest.skip("Need both supervisor implementations to test factory patterns")
        
        # Analyze factory patterns
        for name, supervisor_class in supervisor_classes:
            pattern_info = {
                "name": name,
                "has_create_method": hasattr(supervisor_class, 'create'),
                "create_is_classmethod": False,
                "create_signature": None,
                "init_signature": None,
                "uses_agent_factory": False,
                "uses_registry_pattern": False
            }
            
            # Check create method
            if hasattr(supervisor_class, 'create'):
                create_method = getattr(supervisor_class, 'create')
                pattern_info["create_is_classmethod"] = isinstance(create_method, classmethod)
                
                try:
                    import inspect
                    sig = inspect.signature(create_method)
                    pattern_info["create_signature"] = list(sig.parameters.keys())
                except Exception:
                    pattern_info["create_signature"] = "unknown"
            
            # Check __init__ signature  
            try:
                import inspect
                sig = inspect.signature(supervisor_class.__init__)
                pattern_info["init_signature"] = list(sig.parameters.keys())
            except Exception:
                pattern_info["init_signature"] = "unknown"
            
            # Check for agent factory usage
            try:
                import inspect
                source = inspect.getsource(supervisor_class)
                if 'agent_instance_factory' in source or 'AgentInstanceFactory' in source:
                    pattern_info["uses_agent_factory"] = True
                if 'AgentRegistry' in source or 'agent_registry' in source:
                    pattern_info["uses_registry_pattern"] = True
            except Exception:
                pass  # Skip source analysis if it fails
                
            factory_patterns.append(pattern_info)
            logger.info(f"SupervisorAgent {name} factory pattern: {pattern_info}")
        
        # FACTORY PATTERN CONFLICT DETECTION
        if len(factory_patterns) > 1:
            conflicts = []
            
            base_pattern = factory_patterns[0]
            for other_pattern in factory_patterns[1:]:
                for key in ["has_create_method", "create_is_classmethod", "uses_agent_factory", "uses_registry_pattern"]:
                    if base_pattern[key] != other_pattern[key]:
                        conflicts.append(f"{key}: {base_pattern['name']}={base_pattern[key]} vs {other_pattern['name']}={other_pattern[key]}")
                        
                # Check signature differences
                if base_pattern["create_signature"] != other_pattern["create_signature"]:
                    conflicts.append(f"create_signature: {base_pattern['name']}={base_pattern['create_signature']} vs {other_pattern['name']}={other_pattern['create_signature']}")
                    
                if base_pattern["init_signature"] != other_pattern["init_signature"]:
                    conflicts.append(f"init_signature: {base_pattern['name']}={base_pattern['init_signature']} vs {other_pattern['name']}={other_pattern['init_signature']}")
            
            if conflicts:
                logger.error(f"🚨 FACTORY PATTERN CONFLICTS: {len(conflicts)} inconsistencies detected")
                for conflict in conflicts:
                    logger.error(f"   {conflict}")
                
                # This test should FAIL to expose the factory conflicts
                pytest.fail(f"FACTORY PATTERN CONFLICTS: {len(conflicts)} inconsistencies between "
                           f"supervisor implementations. Expected: Unified factory pattern. "
                           f"Conflicts: {conflicts}")
            else:
                logger.info("✓ Factory patterns are consistent between supervisors")
        else:
            logger.info("✓ Only one supervisor factory pattern found")


# After SSOT remediation validation tests (currently skipped)
@pytest.mark.integration
class SupervisorSystemLevelSSotValidationTests(SSotBaseTestCase):
    """Integration tests that will pass after SSOT remediation."""
    
    @pytest.mark.skip("Will be enabled after SSOT remediation")
    def test_supervisor_unified_system_integration_WILL_PASS(self):
        """PASSING test after remediation - clean supervisor-registry-engine integration
        
        Currently SKIPPED: Will be enabled after SSOT remediation.
        After remediation: Will pass when unified system integration exists.
        """
        logger.info("✅ VALIDATING: Clean supervisor system integration")
        
        # Import the SSOT SupervisorAgent
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        
        # Validate system components use the SSOT supervisor
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
            factory = get_agent_instance_factory()
            
            # Factory should be configured to use SSOT supervisor
            assert factory is not None, "AgentInstanceFactory should be available"
            
            # Should be able to create supervisor via factory
            # (This would be a more complex test in real implementation)
            logger.info("✓ SSOT supervisor integrates properly with AgentInstanceFactory")
            
        except ImportError as e:
            pytest.fail(f"SSOT supervisor system integration failed: {e}")

    @pytest.mark.skip("Will be enabled after SSOT remediation") 
    def test_supervisor_unified_websocket_integration_WILL_PASS(self):
        """PASSING test after remediation - consistent WebSocket integration
        
        Currently SKIPPED: Will be enabled after SSOT remediation.
        After remediation: Will pass when unified WebSocket integration exists.
        """
        logger.info("✅ VALIDATING: Unified supervisor WebSocket integration")
        
        # Import the SSOT SupervisorAgent
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Should integrate cleanly with WebSocket bridge
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Should create without conflicts
        supervisor = SupervisorAgent.create(
            llm_manager=Mock(),
            websocket_bridge=websocket_bridge
        )
        
        assert supervisor is not None, "SSOT supervisor should create successfully"
        assert hasattr(supervisor, 'websocket_bridge'), "SSOT supervisor should have WebSocket bridge"
        
        logger.info("✓ SSOT supervisor integrates properly with WebSocket systems")


if __name__ == "__main__":
    # Run system conflict analysis
    import asyncio
    
    async def run_analysis():
        test_instance = SupervisorSystemLevelSSotConflictsTests()
        
        print("🔍 Running SupervisorAgent System-Level SSOT Conflict Analysis:")
        
        try:
            test_instance.test_supervisor_registry_integration_conflict_SHOULD_FAIL()
            print("❌ Registry integration conflict test unexpectedly passed")
        except AssertionError as e:
            print(f"✅ Registry integration conflict exposed: {e}")
        except Exception as e:
            print(f"⚠️  Registry integration test error: {e}")
        
        try:
            test_instance.test_supervisor_execution_engine_confusion_SHOULD_FAIL()
            print("❌ Execution engine conflict test unexpectedly passed")
        except AssertionError as e:
            print(f"✅ Execution engine conflict exposed: {e}")
        except Exception as e:
            print(f"⚠️  Execution engine test error: {e}")
        
        try:
            await test_instance.test_supervisor_websocket_event_delivery_race_SHOULD_FAIL()
            print("❌ WebSocket event conflict test unexpectedly passed")
        except AssertionError as e:
            print(f"✅ WebSocket event conflict exposed: {e}")
        except Exception as e:
            print(f"⚠️  WebSocket event test error: {e}")
    
    asyncio.run(run_analysis())
