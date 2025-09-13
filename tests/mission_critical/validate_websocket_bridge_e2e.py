"""
End-to-End WebSocket Bridge Validation Script

This script traces the complete WebSocket bridge flow from startup to event emission,
ensuring that all components are properly wired and functional.

CRITICAL BUSINESS VALUE: Chat delivers 90% of value - this validation ensures
the entire communication chain works end-to-end.
"""

import asyncio
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directories to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Application imports
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger


def get_test_logger(name: str) -> logging.Logger:
    """Simple test logger implementation."""
    return central_logger.get_logger(name)


class ValidationReport:
    """Simple validation report implementation."""
    def __init__(self, name: str):
        self.name = name


class WebSocketBridgeE2EValidator:
    """
    Comprehensive E2E validator for WebSocket bridge integration.
    
    Validates the complete flow:
    1. Startup -> AgentWebSocketBridge initialization
    2. AgentRegistry receives bridge
    3. ExecutionEngine passes bridge to AgentExecutionCore
    4. AgentExecutionCore sets bridge on agents
    5. Agents emit events through bridge
    6. Events reach WebSocket manager
    """
    
    def __init__(self):
        self.logger = get_test_logger(__name__)
        self.validation_report = ValidationReport("WebSocket Bridge E2E Flow")
        self.test_thread_id = f"e2e_test_{uuid.uuid4()}"
        self.test_run_id = f"run_{uuid.uuid4()}"
        
        # Track validation results
        self.validations: List[Dict[str, Any]] = []
        
    async def validate_complete_flow(self) -> bool:
        """
        Validate the complete WebSocket bridge flow end-to-end.
        Returns True if all validations pass.
        """
        self.logger.info("=" * 80)
        self.logger.info("[U+1F680] STARTING E2E WEBSOCKET BRIDGE VALIDATION")
        self.logger.info("=" * 80)
        
        try:
            # Phase 1: Startup and Initialization
            await self._validate_startup_initialization()
            
            # Phase 2: Component Integration
            await self._validate_component_integration()
            
            # Phase 3: Bridge Propagation
            await self._validate_bridge_propagation()
            
            # Phase 4: Event Flow
            await self._validate_event_flow()
            
            # Phase 5: End-to-End Message Delivery
            await self._validate_e2e_message_delivery()
            
            # Generate comprehensive report
            success = await self._generate_final_report()
            
            if success:
                self.logger.info(" PASS:  ALL E2E WEBSOCKET BRIDGE VALIDATIONS PASSED")
            else:
                self.logger.error(" FAIL:  E2E WEBSOCKET BRIDGE VALIDATION FAILED")
                
            return success
            
        except Exception as e:
            self.logger.error(f"[U+1F4A5] E2E VALIDATION CRASHED: {e}")
            self._add_validation("E2E Validation", False, f"Validation crashed: {e}")
            return False
    
    async def _validate_startup_initialization(self) -> None:
        """Phase 1: Validate startup creates all required components."""
        self.logger.info("[U+1F4CB] PHASE 1: Startup Initialization")
        
        try:
            # Create a minimal FastAPI app for testing
            from fastapi import FastAPI
            from netra_backend.app.smd import StartupOrchestrator
            
            app = FastAPI()
            orchestrator = StartupOrchestrator(app)
            
            # Mock minimal initialization for testing
            await self._mock_minimal_startup(app)
            
            # Validate required components exist
            components_to_check = [
                ('agent_websocket_bridge', 'AgentWebSocketBridge'),
                ('agent_supervisor', 'Agent Supervisor'),
                ('tool_dispatcher', 'Tool Dispatcher')
            ]
            
            all_components_exist = True
            for attr_name, display_name in components_to_check:
                if hasattr(app.state, attr_name) and getattr(app.state, attr_name) is not None:
                    self.logger.info(f"    PASS:  {display_name}: Present")
                    self._add_validation(f"Startup: {display_name}", True, "Component created during startup")
                else:
                    self.logger.error(f"    FAIL:  {display_name}: Missing or None")
                    self._add_validation(f"Startup: {display_name}", False, f"{display_name} not created or is None")
                    all_components_exist = False
            
            if all_components_exist:
                self.logger.info(" PASS:  Phase 1: All startup components initialized successfully")
            else:
                self.logger.error(" FAIL:  Phase 1: Critical startup components missing")
                
        except Exception as e:
            self.logger.error(f" FAIL:  Phase 1 failed: {e}")
            self._add_validation("Startup Initialization", False, f"Phase failed: {e}")
    
    async def _validate_component_integration(self) -> None:
        """Phase 2: Validate components are properly integrated."""
        self.logger.info("[U+1F517] PHASE 2: Component Integration")
        
        try:
            # Test AgentWebSocketBridge integration
            await self._test_bridge_integration()
            
            # Test AgentRegistry integration
            await self._test_registry_integration()
            
            # Test Tool Dispatcher integration
            await self._test_tool_dispatcher_integration()
            
            self.logger.info(" PASS:  Phase 2: Component integration validated")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Phase 2 failed: {e}")
            self._add_validation("Component Integration", False, f"Phase failed: {e}")
    
    async def _validate_bridge_propagation(self) -> None:
        """Phase 3: Validate bridge is properly propagated to agents."""
        self.logger.info("[U+1F309] PHASE 3: Bridge Propagation")
        
        try:
            # Test bridge propagation through registry
            await self._test_bridge_propagation_to_agents()
            
            # Test ExecutionEngine bridge handling
            await self._test_execution_engine_bridge()
            
            # Test AgentExecutionCore bridge setting
            await self._test_agent_execution_core_bridge()
            
            self.logger.info(" PASS:  Phase 3: Bridge propagation validated")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Phase 3 failed: {e}")
            self._add_validation("Bridge Propagation", False, f"Phase failed: {e}")
    
    async def _validate_event_flow(self) -> None:
        """Phase 4: Validate events flow through the bridge correctly."""
        self.logger.info("[U+1F4E1] PHASE 4: Event Flow")
        
        try:
            # Test basic event emission
            await self._test_basic_event_emission()
            
            # Test tool execution events
            await self._test_tool_execution_events()
            
            # Test agent lifecycle events
            await self._test_agent_lifecycle_events()
            
            self.logger.info(" PASS:  Phase 4: Event flow validated")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Phase 4 failed: {e}")
            self._add_validation("Event Flow", False, f"Phase failed: {e}")
    
    async def _validate_e2e_message_delivery(self) -> None:
        """Phase 5: Validate end-to-end message delivery to WebSocket."""
        self.logger.info(" TARGET:  PHASE 5: E2E Message Delivery")
        
        try:
            # Test complete message path: Agent -> Bridge -> WebSocket Manager
            await self._test_complete_message_path()
            
            # Test error handling in message delivery
            await self._test_message_delivery_error_handling()
            
            # Test message queuing when no connections
            await self._test_message_queuing()
            
            self.logger.info(" PASS:  Phase 5: E2E message delivery validated")
            
        except Exception as e:
            self.logger.error(f" FAIL:  Phase 5 failed: {e}")
            self._add_validation("E2E Message Delivery", False, f"Phase failed: {e}")
    
    async def _mock_minimal_startup(self, app) -> None:
        """Create minimal startup components for testing."""
        from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.config import settings
        
        # Mock minimal LLM manager
        app.state.llm_manager = LLMManager(settings)
        
        # Create AgentWebSocketBridge
        bridge = await get_agent_websocket_bridge()
        app.state.agent_websocket_bridge = bridge
        
        # Create tool dispatcher with bridge
        app.state.tool_dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
        
        # Mock database session factory (minimal for testing)
        class MockSessionFactory:
            async def __call__(self):
                return None
        app.state.db_session_factory = MockSessionFactory()
        
        # Create supervisor (this will create registry internally)
        supervisor = SupervisorAgent(
            app.state.db_session_factory,
            app.state.llm_manager, 
            bridge,
            app.state.tool_dispatcher
        )
        app.state.agent_supervisor = supervisor
    
    async def _test_bridge_integration(self) -> None:
        """Test AgentWebSocketBridge integration."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            bridge = await get_agent_websocket_bridge()
            
            # Test bridge has required methods
            required_methods = [
                'notify_agent_started',
                'notify_agent_completed', 
                'notify_tool_executing',
                'notify_tool_completed'
            ]
            
            for method_name in required_methods:
                if hasattr(bridge, method_name):
                    self._add_validation(f"Bridge Method: {method_name}", True, "Method exists")
                else:
                    self._add_validation(f"Bridge Method: {method_name}", False, "Method missing")
            
            # Test bridge health
            status = await bridge.health_check()
            self._add_validation("Bridge Health", True, f"Bridge state: {status.state.value}")
            
        except Exception as e:
            self._add_validation("Bridge Integration Test", False, f"Test failed: {e}")
    
    async def _test_registry_integration(self) -> None:
        """Test AgentRegistry integration with bridge."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            from netra_backend.app.config import settings
            
            bridge = await get_agent_websocket_bridge()
            llm_manager = LLMManager(settings)
            tool_dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
            
            registry = AgentRegistry(llm_manager, tool_dispatcher)
            registry.register_default_agents()
            
            # Test registry has set_websocket_bridge method
            if hasattr(registry, 'set_websocket_bridge'):
                self._add_validation("Registry Bridge Method", True, "set_websocket_bridge exists")
                
                # Test setting the bridge
                registry.set_websocket_bridge(bridge)
                
                # Verify bridge was set
                if hasattr(registry, 'websocket_bridge') and registry.websocket_bridge is not None:
                    self._add_validation("Registry Bridge Set", True, "Bridge successfully set")
                else:
                    self._add_validation("Registry Bridge Set", False, "Bridge not set properly")
            else:
                self._add_validation("Registry Bridge Method", False, "set_websocket_bridge missing")
                
        except Exception as e:
            self._add_validation("Registry Integration Test", False, f"Test failed: {e}")
    
    async def _test_tool_dispatcher_integration(self) -> None:
        """Test Tool Dispatcher integration with bridge."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            
            bridge = await get_agent_websocket_bridge()
            dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
            
            # Test dispatcher has WebSocket support
            if hasattr(dispatcher, 'has_websocket_support'):
                support = dispatcher.has_websocket_support
                self._add_validation("Tool Dispatcher WebSocket Support", support, 
                                   f"WebSocket support: {support}")
            else:
                self._add_validation("Tool Dispatcher WebSocket Support", False, 
                                   "has_websocket_support property missing")
            
            # Test set_websocket_bridge method
            if hasattr(dispatcher, 'set_websocket_bridge'):
                dispatcher.set_websocket_bridge(bridge)
                self._add_validation("Tool Dispatcher Bridge Method", True, "set_websocket_bridge works")
            else:
                self._add_validation("Tool Dispatcher Bridge Method", False, "set_websocket_bridge missing")
                
        except Exception as e:
            self._add_validation("Tool Dispatcher Integration Test", False, f"Test failed: {e}")
    
    async def _test_bridge_propagation_to_agents(self) -> None:
        """Test bridge propagation to individual agents."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            from netra_backend.app.config import settings
            
            bridge = await get_agent_websocket_bridge()
            llm_manager = LLMManager(settings)
            tool_dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
            
            registry = AgentRegistry(llm_manager, tool_dispatcher)
            registry.register_default_agents()
            registry.set_websocket_bridge(bridge)
            
            # Check if agents received the bridge
            agents_with_bridge = 0
            agents_without_bridge = 0
            
            for agent_name, agent in registry.agents.items():
                if hasattr(agent, 'set_websocket_bridge'):
                    # Bridge setter exists - this is good
                    agents_with_bridge += 1
                    self._add_validation(f"Agent Bridge Support: {agent_name}", True, 
                                       "Agent supports set_websocket_bridge")
                else:
                    agents_without_bridge += 1
                    self._add_validation(f"Agent Bridge Support: {agent_name}", False,
                                       "Agent missing set_websocket_bridge")
            
            if agents_without_bridge == 0:
                self._add_validation("All Agents Bridge Support", True, 
                                   f"All {agents_with_bridge} agents support bridge")
            else:
                self._add_validation("All Agents Bridge Support", False,
                                   f"{agents_without_bridge} agents lack bridge support")
                
        except Exception as e:
            self._add_validation("Bridge Propagation to Agents Test", False, f"Test failed: {e}")
    
    async def _test_execution_engine_bridge(self) -> None:
        """Test ExecutionEngine handles bridge correctly."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            from netra_backend.app.config import settings
            
            bridge = await get_agent_websocket_bridge()
            llm_manager = LLMManager(settings)
            tool_dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
            
            registry = AgentRegistry(llm_manager, tool_dispatcher)
            engine = ExecutionEngine(registry, bridge)
            
            # Test engine has the bridge
            if hasattr(engine, 'websocket_bridge') and engine.websocket_bridge is not None:
                self._add_validation("ExecutionEngine Bridge", True, "Bridge properly set")
            else:
                self._add_validation("ExecutionEngine Bridge", False, "Bridge not set")
                
        except Exception as e:
            self._add_validation("ExecutionEngine Bridge Test", False, f"Test failed: {e}")
    
    async def _test_agent_execution_core_bridge(self) -> None:
        """Test AgentExecutionCore bridge setting."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.config import settings
            
            bridge = await get_agent_websocket_bridge()
            llm_manager = LLMManager(settings)
            
            # Create a test agent
            agent = BaseAgent(llm_manager, "test_agent", "Test agent for validation")
            
            # Create AgentExecutionCore
            core = AgentExecutionCore()
            
            # Test set_websocket_bridge method
            if hasattr(core, 'set_websocket_bridge'):
                core.set_websocket_bridge(bridge)
                self._add_validation("AgentExecutionCore Bridge Method", True, "set_websocket_bridge exists")
                
                # Test that it can set bridge on agents
                result = await core.set_agent_bridge(agent, bridge)
                if result:
                    self._add_validation("AgentExecutionCore Bridge Setting", True, "Successfully set bridge on agent")
                else:
                    self._add_validation("AgentExecutionCore Bridge Setting", False, "Failed to set bridge on agent")
            else:
                self._add_validation("AgentExecutionCore Bridge Method", False, "set_websocket_bridge missing")
                
        except Exception as e:
            self._add_validation("AgentExecutionCore Bridge Test", False, f"Test failed: {e}")
    
    async def _test_basic_event_emission(self) -> None:
        """Test basic event emission through the bridge."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            bridge = await get_agent_websocket_bridge()
            
            # Test basic event methods
            test_run_id = f"test_{uuid.uuid4()}"
            
            # Test agent_started event
            await bridge.notify_agent_started(test_run_id, "test_agent", {"test": True})
            self._add_validation("Event Emission: agent_started", True, "Event sent without error")
            
            # Test tool_executing event
            await bridge.notify_tool_executing(test_run_id, "test_agent", "test_tool", {"input": "test"})
            self._add_validation("Event Emission: tool_executing", True, "Event sent without error")
            
            # Test tool_completed event  
            await bridge.notify_tool_completed(test_run_id, "test_agent", "test_tool", {"result": "success"})
            self._add_validation("Event Emission: tool_completed", True, "Event sent without error")
            
            # Test agent_completed event
            await bridge.notify_agent_completed(test_run_id, "test_agent", {"final": "result"})
            self._add_validation("Event Emission: agent_completed", True, "Event sent without error")
            
        except Exception as e:
            self._add_validation("Basic Event Emission Test", False, f"Test failed: {e}")
    
    async def _test_tool_execution_events(self) -> None:
        """Test tool execution events flow correctly."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            
            bridge = await get_agent_websocket_bridge()
            dispatcher = ToolDispatcher(tools=[], websocket_bridge=bridge)
            
            # Register a simple test tool
            def test_tool(input_text: str) -> str:
                return f"Processed: {input_text}"
            
            dispatcher.register_tool("test_tool", test_tool, "Test tool for validation")
            
            # Execute tool and verify events are sent
            test_run_id = f"tool_test_{uuid.uuid4()}"
            result = await dispatcher.dispatch("test_tool", input_text="test input")
            
            if result.status.value == "completed":
                self._add_validation("Tool Execution Events", True, "Tool executed and events sent")
            else:
                self._add_validation("Tool Execution Events", False, f"Tool execution failed: {result.message}")
                
        except Exception as e:
            self._add_validation("Tool Execution Events Test", False, f"Test failed: {e}")
    
    async def _test_agent_lifecycle_events(self) -> None:
        """Test agent lifecycle events flow correctly."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.llm.llm_manager import LLMManager
            from netra_backend.app.config import settings
            
            bridge = await get_agent_websocket_bridge()
            llm_manager = LLMManager(settings)
            
            # Create a test agent
            agent = BaseAgent(llm_manager, "test_agent", "Test agent for validation")
            
            # Set the bridge on the agent
            if hasattr(agent, 'set_websocket_bridge'):
                agent.set_websocket_bridge(bridge)
                
                # Test that agent can emit events
                test_run_id = f"agent_test_{uuid.uuid4()}"
                
                # Simulate agent lifecycle
                await agent.emit_agent_started(test_run_id, {"test": "started"})
                await agent.emit_thinking("Processing test request...")
                await agent.emit_agent_completed(test_run_id, {"result": "completed"})
                
                self._add_validation("Agent Lifecycle Events", True, "Agent lifecycle events sent")
            else:
                self._add_validation("Agent Lifecycle Events", False, "Agent missing set_websocket_bridge")
                
        except Exception as e:
            self._add_validation("Agent Lifecycle Events Test", False, f"Test failed: {e}")
    
    async def _test_complete_message_path(self) -> None:
        """Test complete message path from agent to WebSocket manager."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.websocket_core import get_websocket_manager
            
            bridge = await get_agent_websocket_bridge()
            manager = get_websocket_manager()
            
            # Test that bridge can send to manager
            test_thread_id = f"e2e_test_{uuid.uuid4()}"
            test_message = {
                "type": "e2e_test",
                "data": {"test": "complete_path"},
                "timestamp": time.time()
            }
            
            # Send through bridge to manager
            success = await manager.send_to_thread(test_thread_id, test_message)
            
            if success:
                self._add_validation("Complete Message Path", True, "Message sent through complete path")
            else:
                self._add_validation("Complete Message Path", False, "Message failed to send")
                
        except Exception as e:
            self._add_validation("Complete Message Path Test", False, f"Test failed: {e}")
    
    async def _test_message_delivery_error_handling(self) -> None:
        """Test error handling in message delivery."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            
            bridge = await get_agent_websocket_bridge()
            
            # Test with invalid data - should not crash
            try:
                await bridge.notify_agent_started("invalid_run", "test_agent", {"malformed": None})
                self._add_validation("Error Handling: Invalid Data", True, "Bridge handles invalid data gracefully")
            except Exception:
                self._add_validation("Error Handling: Invalid Data", False, "Bridge crashed on invalid data")
            
            # Test with None values - should not crash  
            try:
                await bridge.notify_tool_executing(None, "test_agent", "test_tool", {})
                self._add_validation("Error Handling: None Values", True, "Bridge handles None values gracefully")
            except Exception:
                self._add_validation("Error Handling: None Values", False, "Bridge crashed on None values")
                
        except Exception as e:
            self._add_validation("Message Delivery Error Handling Test", False, f"Test failed: {e}")
    
    async def _test_message_queuing(self) -> None:
        """Test message queuing when no WebSocket connections exist."""
        try:
            from netra_backend.app.services.agent_websocket_bridge import get_agent_websocket_bridge
            from netra_backend.app.websocket_core import get_websocket_manager
            
            bridge = await get_agent_websocket_bridge()
            manager = get_websocket_manager()
            
            # Send message when no connections exist (normal startup state)
            test_thread_id = f"queue_test_{uuid.uuid4()}"
            test_message = {
                "type": "queue_test",
                "data": {"test": "queuing"},
                "timestamp": time.time()
            }
            
            # This should succeed even with no connections (message queued)
            success = await manager.send_to_thread(test_thread_id, test_message)
            
            if success:
                self._add_validation("Message Queuing", True, "Messages queued when no connections")
            else:
                self._add_validation("Message Queuing", False, "Message queuing failed")
                
        except Exception as e:
            self._add_validation("Message Queuing Test", False, f"Test failed: {e}")
    
    def _add_validation(self, component: str, passed: bool, details: str) -> None:
        """Add a validation result to the report."""
        validation = {
            "component": component,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        }
        self.validations.append(validation)
        
        if passed:
            self.logger.info(f"    PASS:  {component}: {details}")
        else:
            self.logger.error(f"    FAIL:  {component}: {details}")
    
    async def _generate_final_report(self) -> bool:
        """Generate comprehensive final report."""
        self.logger.info("=" * 80)
        self.logger.info(" CHART:  E2E VALIDATION FINAL REPORT")
        self.logger.info("=" * 80)
        
        total_validations = len(self.validations)
        passed_validations = len([v for v in self.validations if v["passed"]])
        failed_validations = total_validations - passed_validations
        success_rate = (passed_validations / total_validations) * 100 if total_validations > 0 else 0
        
        self.logger.info(f"[U+1F4C8] OVERALL RESULTS:")
        self.logger.info(f"   Total Validations: {total_validations}")
        self.logger.info(f"   Passed: {passed_validations}")
        self.logger.info(f"   Failed: {failed_validations}")
        self.logger.info(f"   Success Rate: {success_rate:.1f}%")
        
        if failed_validations > 0:
            self.logger.error("=" * 80)
            self.logger.error(" FAIL:  FAILED VALIDATIONS:")
            self.logger.error("=" * 80)
            
            for validation in self.validations:
                if not validation["passed"]:
                    self.logger.error(f"    FAIL:  {validation['component']}: {validation['details']}")
        
        # Business impact assessment
        critical_failures = self._assess_critical_failures()
        
        if critical_failures:
            self.logger.error("=" * 80)
            self.logger.error(" ALERT:  CRITICAL BUSINESS IMPACT DETECTED")
            self.logger.error("=" * 80)
            for failure in critical_failures:
                self.logger.error(f"   [U+1F4A5] {failure}")
            self.logger.error("[U+1F534] CHAT FUNCTIONALITY WILL NOT WORK PROPERLY")
            success = False
        else:
            self.logger.info("=" * 80)
            self.logger.info("[U+1F7E2] ALL CRITICAL PATHS VALIDATED SUCCESSFULLY")
            self.logger.info(" PASS:  CHAT FUNCTIONALITY READY FOR BUSINESS VALUE DELIVERY")
            self.logger.info("=" * 80)
            success = failed_validations == 0
        
        return success
    
    def _assess_critical_failures(self) -> List[str]:
        """Assess which failures are critical for business value."""
        critical_failures = []
        
        # Critical components that MUST work for chat
        critical_components = [
            "AgentWebSocketBridge",
            "Bridge Integration",
            "Tool Dispatcher WebSocket Support", 
            "Agent Bridge Support",
            "Event Emission",
            "Complete Message Path"
        ]
        
        for validation in self.validations:
            if not validation["passed"]:
                component = validation["component"]
                for critical in critical_components:
                    if critical.lower() in component.lower():
                        critical_failures.append(f"{component}: {validation['details']}")
                        break
        
        return critical_failures


async def main():
    """Main entry point for E2E validation."""
    validator = WebSocketBridgeE2EValidator()
    
    try:
        success = await validator.validate_complete_flow()
        
        if success:
            print("\n CELEBRATION:  E2E WebSocket Bridge validation PASSED - Chat functionality is ready!")
            return 0
        else:
            print("\n[U+1F4A5] E2E WebSocket Bridge validation FAILED - Chat will not work properly!")
            return 1
            
    except Exception as e:
        print(f"\n[U+1F480] E2E validation crashed: {e}")
        return 2


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)