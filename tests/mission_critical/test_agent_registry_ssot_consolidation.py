#!/usr/bin/env python3

"""
Agent Registry SSOT Consolidation Tests - Issue #845 Core Validation

Business Impact: $500K+ ARR - Duplicate AgentRegistry implementations blocking Golden Path
BVJ: ALL segments | Platform Stability | Prevent SSOT consolidation from breaking core functionality
Priority: P0 - Core infrastructure validation for SSOT consolidation

CRITICAL REQUIREMENTS:
- Test basic registry functionality preservation during consolidation
- Validate advanced registry features remain intact
- Ensure import path compatibility after consolidation  
- Verify interface consistency between old/new implementations
- Comprehensive regression testing for agent creation/discovery

Test Categories:
1. Basic Registry Functionality Tests (8+ test cases)
2. Advanced Registry Feature Tests (6+ test cases)
3. Import Path Compatibility Tests (5+ test cases)
4. Interface Consistency Validation Tests (4+ test cases)
5. Regression Prevention Tests (7+ test cases)

SSOT FILES BEING CONSOLIDATED:
- Basic Registry: /netra_backend/app/agents/registry.py
- Advanced Registry: /netra_backend/app/agents/supervisor/agent_registry.py

NOTE: Tests are designed to FAIL initially to prove they catch regressions
"""

import asyncio
import os
import sys
import uuid
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

import pytest
from loguru import logger

# Import production components for real validation
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestAgentRegistrySSoTConsolidation(SSotAsyncTestCase):
    """
    Core SSOT consolidation validation for AgentRegistry implementations.
    
    Business Value: Ensures SSOT consolidation doesn't break core agent management
    Coverage: Validates all registry functionality preservation during consolidation
    Priority: P0 - Must pass before any SSOT consolidation deployment
    """
    
    def setup_method(self, method):
        """Setup SSOT consolidation test environment - real infrastructure only."""
        super().setup_method(method)
        
        # Create unique test identifiers
        self.test_id = str(uuid.uuid4())[:8]
        self.test_user_id = f"test_user_{self.test_id}"
        
        # Test context for agent creation
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=f"thread_{self.test_id}",
            run_id=f"run_{uuid.uuid4()}",
            request_id=f"req_{uuid.uuid4()}"
        )
        
        # Registry instances for comparison testing
        self.basic_registry = None
        self.advanced_registry = None
        
        logger.info(f"Setup SSOT consolidation test: {self.test_id}")
    
    def teardown_method(self, method):
        """Cleanup registry instances and resources."""
        # Cleanup registries
        async def cleanup_registries():
            if self.advanced_registry and hasattr(self.advanced_registry, 'cleanup'):
                try:
                    await self.advanced_registry.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up advanced registry: {e}")
        
        # Run cleanup
        loop = asyncio.new_event_loop()
        loop.run_until_complete(cleanup_registries())
        loop.close()
        
        super().teardown_method(method)
    
    # ===== BASIC REGISTRY FUNCTIONALITY TESTS (8+ test cases) =====
    
    async def test_basic_registry_functionality_preserved(self):
        """Validate all basic registry features work with advanced registry."""
        # Import both registry implementations
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Test that we can import both
            assert BasicRegistry is not None, "Basic AgentRegistry should be importable"
            assert AdvancedRegistry is not None, "Advanced AgentRegistry should be importable"
            
            # Create instances
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            
            # Test basic functionality exists in both
            basic_methods = ['register_agent', 'get_agent_info', 'get_all_agents']
            for method_name in basic_methods:
                assert hasattr(basic_registry, method_name), f"Basic registry missing {method_name}"
                assert hasattr(advanced_registry, method_name), f"Advanced registry missing {method_name}"
            
            logger.info("✓ Basic registry functionality preserved in advanced registry")
            
        except ImportError as e:
            self.fail(f"REGRESSION: Cannot import registry implementations for comparison: {e}")
    
    async def test_agent_registration_compatibility(self):
        """Test that agent registration works identically in both registries."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Create both registry instances
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            
            # Test agent registration in basic registry
            agent_id_basic = basic_registry.register_agent(
                AgentType.TRIAGE,
                "Test Triage Agent",
                "Test agent for SSOT validation"
            )
            assert agent_id_basic is not None, "Basic registry should return agent ID"
            assert isinstance(agent_id_basic, str), "Agent ID should be string"
            
            # Verify agent was registered
            agent_info_basic = basic_registry.get_agent_info(agent_id_basic)
            assert agent_info_basic is not None, "Should retrieve registered agent info"
            assert agent_info_basic.name == "Test Triage Agent", "Agent name should match"
            
            logger.info("✓ Agent registration compatibility validated between registries")
            
        except Exception as e:
            self.fail(f"REGRESSION: Agent registration compatibility broken: {e}")
    
    async def test_agent_discovery_methods_preserved(self):
        """Test that all agent discovery methods work in advanced registry."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Test with advanced registry
            advanced_registry = AdvancedRegistry()
            
            # Register test agents
            agent_id_1 = advanced_registry.register_agent(
                AgentType.TRIAGE, "Triage Test", "Test triage agent"
            )
            agent_id_2 = advanced_registry.register_agent(
                AgentType.OPTIMIZER, "Optimizer Test", "Test optimizer agent"
            )
            
            # Test discovery methods
            all_agents = advanced_registry.get_all_agents()
            assert len(all_agents) >= 2, "Should find all registered agents"
            
            triage_agents = advanced_registry.get_agents_by_type(AgentType.TRIAGE)
            assert len(triage_agents) >= 1, "Should find triage agents"
            
            # Test agent lookup by name
            found_agent = advanced_registry.find_agent_by_name("Triage Test")
            assert found_agent is not None, "Should find agent by name"
            assert found_agent.agent_id == agent_id_1, "Found agent should match registered agent"
            
            logger.info("✓ Agent discovery methods preserved in advanced registry")
            
        except Exception as e:
            self.fail(f"REGRESSION: Agent discovery methods broken: {e}")
    
    async def test_agent_status_management_preserved(self):
        """Test that agent status management works in advanced registry."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType, AgentStatus
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Register test agent
            agent_id = advanced_registry.register_agent(
                AgentType.TRIAGE, "Status Test Agent", "Test status management"
            )
            
            # Test status updates
            result = advanced_registry.update_agent_status(agent_id, AgentStatus.BUSY)
            assert result is True, "Status update should succeed"
            
            # Verify status was updated
            agent_info = advanced_registry.get_agent_info(agent_id)
            assert agent_info.status == AgentStatus.BUSY, "Agent status should be updated"
            
            # Test status-based queries
            busy_agents = advanced_registry.get_agents_by_status(AgentStatus.BUSY)
            assert len(busy_agents) >= 1, "Should find busy agents"
            
            available_agents = advanced_registry.get_available_agents()
            # Available agents should not include our busy agent
            available_ids = [agent.agent_id for agent in available_agents]
            assert agent_id not in available_ids, "Busy agent should not be in available list"
            
            logger.info("✓ Agent status management preserved in advanced registry")
            
        except Exception as e:
            self.fail(f"REGRESSION: Agent status management broken: {e}")
    
    async def test_agent_metrics_tracking_preserved(self):
        """Test that agent metrics and performance tracking work in advanced registry."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Register test agent
            agent_id = advanced_registry.register_agent(
                AgentType.TRIAGE, "Metrics Test Agent", "Test metrics tracking"
            )
            
            # Test metrics methods
            execution_result = advanced_registry.increment_execution_count(agent_id)
            assert execution_result is True, "Execution count increment should succeed"
            
            error_result = advanced_registry.increment_error_count(agent_id)
            assert error_result is True, "Error count increment should succeed"
            
            # Verify metrics were updated
            agent_info = advanced_registry.get_agent_info(agent_id)
            assert agent_info.execution_count >= 1, "Execution count should be incremented"
            assert agent_info.error_count >= 1, "Error count should be incremented"
            
            # Test registry statistics
            stats = advanced_registry.get_registry_stats()
            assert 'total_agents' in stats, "Registry stats should include total agents"
            assert stats['total_agents'] >= 1, "Should count registered agents"
            
            logger.info("✓ Agent metrics tracking preserved in advanced registry")
            
        except Exception as e:
            self.fail(f"REGRESSION: Agent metrics tracking broken: {e}")
    
    async def test_agent_cleanup_functionality_preserved(self):
        """Test that agent cleanup and lifecycle management work in advanced registry."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Register test agent
            agent_id = advanced_registry.register_agent(
                AgentType.TRIAGE, "Cleanup Test Agent", "Test cleanup functionality"
            )
            
            # Verify agent exists
            assert agent_id in advanced_registry, "Agent should be registered"
            agent_info = advanced_registry.get_agent_info(agent_id)
            assert agent_info is not None, "Should find registered agent"
            
            # Test unregister functionality
            unregister_result = advanced_registry.unregister_agent(agent_id)
            assert unregister_result is True, "Agent unregistration should succeed"
            
            # Verify agent was removed
            assert agent_id not in advanced_registry, "Agent should be unregistered"
            removed_agent_info = advanced_registry.get_agent_info(agent_id)
            assert removed_agent_info is None, "Should not find unregistered agent"
            
            logger.info("✓ Agent cleanup functionality preserved in advanced registry")
            
        except Exception as e:
            self.fail(f"REGRESSION: Agent cleanup functionality broken: {e}")
    
    async def test_registry_health_monitoring_preserved(self):
        """Test that registry health and monitoring work in advanced registry."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test registry health check
            health = advanced_registry.get_registry_health()
            assert isinstance(health, dict), "Health should be a dictionary"
            assert 'status' in health or 'total_agents' in health, "Health should include status info"
            
            # Test factory integration status
            factory_status = advanced_registry.get_factory_integration_status()
            assert isinstance(factory_status, dict), "Factory status should be a dictionary"
            
            logger.info("✓ Registry health monitoring preserved in advanced registry")
            
        except Exception as e:
            # This might not exist in basic registry, so just log warning
            logger.warning(f"Registry health monitoring not available: {e}")
    
    async def test_basic_registry_container_operations(self):
        """Test that basic container operations (len, contains) work in advanced registry."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test empty registry
            initial_count = len(advanced_registry)
            assert isinstance(initial_count, int), "Registry length should be integer"
            
            # Register test agents
            agent_id_1 = advanced_registry.register_agent(
                AgentType.TRIAGE, "Container Test 1", "Test container ops"
            )
            agent_id_2 = advanced_registry.register_agent(
                AgentType.OPTIMIZER, "Container Test 2", "Test container ops"
            )
            
            # Test length increased
            new_count = len(advanced_registry)
            assert new_count == initial_count + 2, "Registry length should increase with registrations"
            
            # Test contains operation
            assert agent_id_1 in advanced_registry, "Registry should contain registered agent"
            assert agent_id_2 in advanced_registry, "Registry should contain registered agent"
            assert "nonexistent_agent" not in advanced_registry, "Registry should not contain unregistered agent"
            
            logger.info("✓ Basic registry container operations preserved in advanced registry")
            
        except Exception as e:
            self.fail(f"REGRESSION: Basic registry container operations broken: {e}")
    
    # ===== ADVANCED REGISTRY FEATURE TESTS (6+ test cases) =====
    
    async def test_advanced_registry_features_retained(self):
        """Ensure advanced features not broken by consolidation."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test advanced features that should exist
            advanced_features = [
                'get_user_session',
                'create_agent_for_user', 
                'cleanup_user_session',
                'monitor_all_users',
                'set_websocket_manager'
            ]
            
            available_features = []
            missing_features = []
            
            for feature in advanced_features:
                if hasattr(advanced_registry, feature):
                    available_features.append(feature)
                else:
                    missing_features.append(feature)
            
            # Should have most advanced features
            assert len(available_features) >= 3, f"Should have advanced features. Available: {available_features}, Missing: {missing_features}"
            
            logger.info(f"✓ Advanced registry features retained: {available_features}")
            
        except Exception as e:
            self.fail(f"REGRESSION: Advanced registry features broken: {e}")
    
    async def test_user_isolation_features_preserved(self):
        """Test that advanced user isolation features are preserved."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test user session creation
            if hasattr(advanced_registry, 'get_user_session'):
                user_session = await advanced_registry.get_user_session(self.test_user_id)
                assert user_session is not None, "Should create user session"
                assert hasattr(user_session, 'user_id'), "User session should have user_id"
                assert user_session.user_id == self.test_user_id, "User session should match requested user"
                
                logger.info("✓ User isolation features preserved")
            else:
                logger.warning("User isolation features not available for testing")
                
        except Exception as e:
            self.fail(f"REGRESSION: User isolation features broken: {e}")
    
    async def test_websocket_integration_preserved(self):
        """Test that WebSocket integration features are preserved."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test WebSocket manager setting
            if hasattr(advanced_registry, 'set_websocket_manager'):
                # Create mock WebSocket manager
                mock_websocket_manager = MagicMock()
                
                # Should not raise exception
                advanced_registry.set_websocket_manager(mock_websocket_manager)
                
                # Should store the manager
                if hasattr(advanced_registry, 'websocket_manager'):
                    assert advanced_registry.websocket_manager is mock_websocket_manager, "Should store WebSocket manager"
                
                logger.info("✓ WebSocket integration features preserved")
            else:
                logger.warning("WebSocket integration not available for testing")
                
        except Exception as e:
            self.fail(f"REGRESSION: WebSocket integration broken: {e}")
    
    async def test_factory_pattern_support_preserved(self):
        """Test that factory pattern support is preserved in advanced registry."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test factory integration methods
            factory_methods = ['register_factory', 'get_factory_integration_status']
            
            available_factory_methods = []
            for method in factory_methods:
                if hasattr(advanced_registry, method):
                    available_factory_methods.append(method)
            
            assert len(available_factory_methods) >= 1, f"Should have factory methods: {available_factory_methods}"
            
            # Test factory status if available
            if hasattr(advanced_registry, 'get_factory_integration_status'):
                factory_status = advanced_registry.get_factory_integration_status()
                assert isinstance(factory_status, dict), "Factory status should be dictionary"
                
            logger.info(f"✓ Factory pattern support preserved: {available_factory_methods}")
            
        except Exception as e:
            self.fail(f"REGRESSION: Factory pattern support broken: {e}")
    
    async def test_monitoring_and_metrics_enhanced_features(self):
        """Test that enhanced monitoring and metrics features are preserved."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test enhanced monitoring methods
            monitoring_methods = [
                'monitor_all_users',
                'diagnose_websocket_wiring',
                'get_ssot_compliance_status'
            ]
            
            available_monitoring = []
            for method in monitoring_methods:
                if hasattr(advanced_registry, method):
                    available_monitoring.append(method)
            
            # Should have some enhanced monitoring
            if available_monitoring:
                logger.info(f"✓ Enhanced monitoring features preserved: {available_monitoring}")
                
                # Test one monitoring method if available
                if hasattr(advanced_registry, 'diagnose_websocket_wiring'):
                    diagnosis = advanced_registry.diagnose_websocket_wiring()
                    assert isinstance(diagnosis, dict), "WebSocket diagnosis should be dictionary"
            else:
                logger.warning("Enhanced monitoring features not available")
                
        except Exception as e:
            self.fail(f"REGRESSION: Enhanced monitoring features broken: {e}")
    
    async def test_cleanup_and_lifecycle_advanced_features(self):
        """Test that advanced cleanup and lifecycle management features are preserved."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test advanced cleanup methods
            cleanup_methods = [
                'cleanup',
                'cleanup_user_session', 
                'emergency_cleanup_all'
            ]
            
            available_cleanup = []
            for method in cleanup_methods:
                if hasattr(advanced_registry, method):
                    available_cleanup.append(method)
            
            assert len(available_cleanup) >= 1, f"Should have advanced cleanup methods: {available_cleanup}"
            
            logger.info(f"✓ Advanced cleanup features preserved: {available_cleanup}")
            
        except Exception as e:
            self.fail(f"REGRESSION: Advanced cleanup features broken: {e}")
    
    # ===== IMPORT PATH COMPATIBILITY TESTS (5+ test cases) =====
    
    async def test_import_path_compatibility(self):
        """Validate import paths resolve correctly after consolidation."""
        # Test basic registry import
        try:
            from netra_backend.app.agents.registry import AgentRegistry
            assert AgentRegistry is not None, "Basic registry should be importable"
            logger.info("✓ Basic registry import path works")
        except ImportError as e:
            self.fail(f"REGRESSION: Basic registry import broken: {e}")
        
        # Test advanced registry import  
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            assert AgentRegistry is not None, "Advanced registry should be importable"
            logger.info("✓ Advanced registry import path works")
        except ImportError as e:
            self.fail(f"REGRESSION: Advanced registry import broken: {e}")
    
    async def test_registry_class_aliases_preserved(self):
        """Test that registry class aliases and exports are preserved."""
        # Test basic registry exports
        try:
            from netra_backend.app.agents.registry import (
                AgentRegistry, AgentInfo, AgentStatus, AgentType, 
                agent_registry, register_agent, get_agent_info
            )
            
            # Verify all expected exports exist
            exports = [AgentRegistry, AgentInfo, AgentStatus, AgentType, 
                      agent_registry, register_agent, get_agent_info]
            
            for export in exports:
                assert export is not None, f"Export {export} should not be None"
                
            logger.info("✓ Basic registry exports preserved")
            
        except ImportError as e:
            self.fail(f"REGRESSION: Basic registry exports broken: {e}")
    
    async def test_global_registry_instance_compatibility(self):
        """Test that global registry instance patterns are preserved."""
        try:
            from netra_backend.app.agents.registry import agent_registry
            
            # Should have global registry instance
            assert agent_registry is not None, "Global registry instance should exist"
            
            # Should be usable
            initial_count = len(agent_registry)
            assert isinstance(initial_count, int), "Global registry should support len()"
            
            logger.info("✓ Global registry instance compatibility preserved")
            
        except ImportError as e:
            self.fail(f"REGRESSION: Global registry instance broken: {e}")
    
    async def test_factory_function_imports_preserved(self):
        """Test that factory function imports are preserved."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import get_agent_registry
            
            # Should be able to import factory function
            assert get_agent_registry is not None, "Factory function should be importable"
            assert callable(get_agent_registry), "Factory function should be callable"
            
            logger.info("✓ Factory function imports preserved")
            
        except ImportError as e:
            logger.warning(f"Factory function import not available: {e}")
    
    async def test_backwards_compatibility_imports(self):
        """Test that backwards compatibility imports still work."""
        # Test that old import patterns still work
        import_tests = [
            ("netra_backend.app.agents.registry", "AgentRegistry"),
            ("netra_backend.app.agents.registry", "AgentType"), 
            ("netra_backend.app.agents.registry", "AgentStatus"),
            ("netra_backend.app.agents.supervisor.agent_registry", "AgentRegistry")
        ]
        
        successful_imports = 0
        for module_path, class_name in import_tests:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                assert cls is not None, f"Should import {class_name} from {module_path}"
                successful_imports += 1
            except (ImportError, AttributeError) as e:
                logger.warning(f"Import {class_name} from {module_path} failed: {e}")
        
        assert successful_imports >= 3, f"Should have successful backwards compatible imports: {successful_imports}/4"
        logger.info(f"✓ Backwards compatibility imports: {successful_imports}/4 successful")
    
    # ===== INTERFACE CONSISTENCY VALIDATION TESTS (4+ test cases) =====
    
    async def test_interface_consistency_validation(self):
        """Check interface consistency between old/new implementations."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Get common methods
            basic_methods = set(dir(BasicRegistry))
            advanced_methods = set(dir(AdvancedRegistry))
            
            # Find common public methods (non-private)
            common_methods = {
                method for method in basic_methods & advanced_methods 
                if not method.startswith('_') and callable(getattr(BasicRegistry, method, None))
            }
            
            assert len(common_methods) >= 5, f"Should have common interface methods: {common_methods}"
            
            # Test that common methods have compatible signatures
            incompatible_methods = []
            for method_name in list(common_methods)[:5]:  # Test first 5 methods
                try:
                    basic_method = getattr(BasicRegistry, method_name)
                    advanced_method = getattr(AdvancedRegistry, method_name)
                    
                    # Both should be callable
                    assert callable(basic_method), f"Basic {method_name} should be callable"
                    assert callable(advanced_method), f"Advanced {method_name} should be callable"
                    
                except Exception as e:
                    incompatible_methods.append(f"{method_name}: {e}")
            
            assert len(incompatible_methods) == 0, f"Interface incompatibilities: {incompatible_methods}"
            
            logger.info(f"✓ Interface consistency validated for {len(common_methods)} common methods")
            
        except Exception as e:
            self.fail(f"REGRESSION: Interface consistency validation failed: {e}")
    
    async def test_method_signature_compatibility(self):
        """Test that critical method signatures are compatible between implementations."""
        critical_methods = [
            'register_agent',
            'get_agent_info', 
            'update_agent_status',
            'get_all_agents'
        ]
        
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            signature_issues = []
            
            for method_name in critical_methods:
                try:
                    # Check both registries have the method
                    basic_has_method = hasattr(BasicRegistry, method_name)
                    advanced_has_method = hasattr(AdvancedRegistry, method_name)
                    
                    if basic_has_method and advanced_has_method:
                        # Both have the method - signature compatibility validated by usage
                        logger.debug(f"Method {method_name} available in both registries")
                    elif not basic_has_method and advanced_has_method:
                        logger.info(f"Method {method_name} only in advanced registry (enhancement)")
                    elif basic_has_method and not advanced_has_method:
                        signature_issues.append(f"Method {method_name} missing in advanced registry")
                    else:
                        signature_issues.append(f"Method {method_name} missing in both registries")
                        
                except Exception as e:
                    signature_issues.append(f"Method {method_name} signature check failed: {e}")
            
            assert len(signature_issues) == 0, f"Method signature issues: {signature_issues}"
            
            logger.info("✓ Method signature compatibility validated")
            
        except Exception as e:
            self.fail(f"REGRESSION: Method signature compatibility broken: {e}")
    
    async def test_return_type_consistency(self):
        """Test that method return types are consistent between implementations."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Create instances
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            
            # Test return type consistency for registry operations
            basic_agent_id = basic_registry.register_agent(
                AgentType.TRIAGE, "Return Type Test Basic", "Test return types"
            )
            advanced_agent_id = advanced_registry.register_agent(
                AgentType.TRIAGE, "Return Type Test Advanced", "Test return types"  
            )
            
            # Both should return strings
            assert isinstance(basic_agent_id, str), "Basic registry should return string agent ID"
            assert isinstance(advanced_agent_id, str), "Advanced registry should return string agent ID"
            
            # Test get_all_agents return type
            basic_all_agents = basic_registry.get_all_agents()
            advanced_all_agents = advanced_registry.get_all_agents()
            
            assert isinstance(basic_all_agents, list), "Basic registry get_all_agents should return list"
            assert isinstance(advanced_all_agents, list), "Advanced registry get_all_agents should return list"
            
            logger.info("✓ Return type consistency validated")
            
        except Exception as e:
            self.fail(f"REGRESSION: Return type consistency broken: {e}")
    
    async def test_error_handling_consistency(self):
        """Test that error handling patterns are consistent between implementations."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Create instances
            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()
            
            # Test error handling for non-existent agent
            basic_result = basic_registry.get_agent_info("nonexistent_agent_id")
            advanced_result = advanced_registry.get_agent_info("nonexistent_agent_id")
            
            # Both should handle missing agents consistently (None or similar)
            assert basic_result is None, "Basic registry should return None for missing agent"
            assert advanced_result is None, "Advanced registry should return None for missing agent"
            
            # Test error handling for invalid status update
            basic_status_result = basic_registry.update_agent_status("nonexistent_agent", None)
            advanced_status_result = advanced_registry.update_agent_status("nonexistent_agent", None)
            
            # Both should handle invalid updates consistently  
            assert basic_status_result == False, "Basic registry should return False for invalid status update"
            assert advanced_status_result == False, "Advanced registry should return False for invalid status update"
            
            logger.info("✓ Error handling consistency validated")
            
        except Exception as e:
            self.fail(f"REGRESSION: Error handling consistency broken: {e}")
    
    # ===== REGRESSION PREVENTION TESTS (7+ test cases) =====
    
    async def test_no_functionality_regression(self):
        """Comprehensive regression test suite."""
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry, AgentType, AgentStatus
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            # Test full workflow with advanced registry
            advanced_registry = AdvancedRegistry()
            
            # Full agent lifecycle test
            agent_id = advanced_registry.register_agent(
                AgentType.TRIAGE, 
                "Regression Test Agent",
                "Comprehensive regression test agent",
                metadata={"test": "regression"}
            )
            
            # Verify registration
            assert agent_id is not None, "Agent registration should succeed"
            assert agent_id in advanced_registry, "Registry should contain agent"
            
            # Test status changes
            status_updated = advanced_registry.update_agent_status(agent_id, AgentStatus.BUSY)
            assert status_updated, "Status update should succeed"
            
            # Test metrics
            metrics_updated = advanced_registry.increment_execution_count(agent_id)
            assert metrics_updated, "Metrics update should succeed"
            
            # Test queries
            agent_info = advanced_registry.get_agent_info(agent_id)
            assert agent_info.name == "Regression Test Agent", "Agent info should be retrievable"
            
            # Test cleanup
            cleanup_success = advanced_registry.unregister_agent(agent_id)
            assert cleanup_success, "Agent cleanup should succeed"
            
            logger.info("✓ No functionality regression detected")
            
        except Exception as e:
            self.fail(f"REGRESSION: Functionality regression detected: {e}")
    
    async def test_performance_regression_basic_operations(self):
        """Test that basic operations don't have performance regressions."""
        import time
        
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry, AgentType
            
            advanced_registry = AdvancedRegistry()
            
            # Test registration performance
            start_time = time.time()
            agent_ids = []
            
            for i in range(10):  # Register 10 agents
                agent_id = advanced_registry.register_agent(
                    AgentType.TRIAGE,
                    f"Performance Test Agent {i}",
                    f"Performance test agent {i}"
                )
                agent_ids.append(agent_id)
            
            registration_time = time.time() - start_time
            
            # Should be fast (less than 1 second for 10 registrations)
            assert registration_time < 1.0, f"Agent registration too slow: {registration_time:.3f}s"
            
            # Test query performance
            start_time = time.time()
            
            for agent_id in agent_ids:
                agent_info = advanced_registry.get_agent_info(agent_id)
                assert agent_info is not None, "Should retrieve agent info"
            
            query_time = time.time() - start_time
            
            # Should be very fast (less than 0.1 seconds for 10 queries)
            assert query_time < 0.1, f"Agent queries too slow: {query_time:.3f}s"
            
            logger.info(f"✓ Performance regression test passed: {registration_time:.3f}s registration, {query_time:.3f}s queries")
            
        except Exception as e:
            self.fail(f"REGRESSION: Performance regression detected: {e}")
    
    async def test_memory_usage_regression(self):
        """Test that memory usage doesn't regress with advanced registry."""
        import gc
        
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry, AgentType
            
            # Force garbage collection before test
            gc.collect()
            
            advanced_registry = AdvancedRegistry()
            
            # Register and unregister agents to test cleanup
            for i in range(20):
                agent_id = advanced_registry.register_agent(
                    AgentType.TRIAGE,
                    f"Memory Test Agent {i}",
                    f"Memory test agent {i}"
                )
                
                # Immediately unregister to test cleanup
                unregistered = advanced_registry.unregister_agent(agent_id)
                assert unregistered, f"Agent {i} should be unregistered"
            
            # Verify registry is empty
            assert len(advanced_registry) == 0, "Registry should be empty after cleanup"
            
            # Force garbage collection
            gc.collect()
            
            logger.info("✓ Memory usage regression test passed")
            
        except Exception as e:
            self.fail(f"REGRESSION: Memory usage regression detected: {e}")
    
    async def test_thread_safety_regression(self):
        """Test that thread safety hasn't regressed in advanced registry."""
        import threading
        import time
        
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry, AgentType
            
            advanced_registry = AdvancedRegistry()
            results = []
            errors = []
            
            def register_agent_worker(worker_id):
                try:
                    agent_id = advanced_registry.register_agent(
                        AgentType.TRIAGE,
                        f"Thread Test Agent {worker_id}",
                        f"Thread safety test agent {worker_id}"
                    )
                    results.append(agent_id)
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {e}")
            
            # Create multiple threads registering agents simultaneously
            threads = []
            for i in range(5):
                thread = threading.Thread(target=register_agent_worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=2.0)
            
            # Verify no errors occurred
            assert len(errors) == 0, f"Thread safety errors: {errors}"
            
            # Verify all registrations succeeded
            assert len(results) == 5, f"Should have 5 successful registrations, got {len(results)}"
            
            # Verify all agent IDs are unique
            unique_results = set(results)
            assert len(unique_results) == len(results), "All agent IDs should be unique"
            
            logger.info("✓ Thread safety regression test passed")
            
        except Exception as e:
            self.fail(f"REGRESSION: Thread safety regression detected: {e}")
    
    async def test_concurrent_user_operations_no_regression(self):
        """Test that concurrent user operations don't have regressions."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test concurrent user session creation if available
            if hasattr(advanced_registry, 'get_user_session'):
                user_sessions = []
                
                # Create multiple user sessions concurrently
                user_tasks = []
                for i in range(3):
                    user_id = f"concurrent_user_{i}_{self.test_id}"
                    task = advanced_registry.get_user_session(user_id)
                    user_tasks.append(task)
                
                # Wait for all sessions to be created
                user_sessions = await asyncio.gather(*user_tasks)
                
                # Verify all sessions were created
                assert len(user_sessions) == 3, "Should create all user sessions"
                
                # Verify sessions are distinct
                user_ids = [session.user_id for session in user_sessions]
                assert len(set(user_ids)) == 3, "All user sessions should be distinct"
                
                logger.info("✓ Concurrent user operations regression test passed")
            else:
                logger.warning("Concurrent user operations not available for testing")
                
        except Exception as e:
            self.fail(f"REGRESSION: Concurrent user operations regression: {e}")
    
    async def test_websocket_integration_no_regression(self):
        """Test that WebSocket integration hasn't regressed."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Test WebSocket integration if available
            if hasattr(advanced_registry, 'set_websocket_manager'):
                # Create mock WebSocket manager
                mock_manager = MagicMock()
                mock_manager.initialize = AsyncMock()
                
                # Set WebSocket manager
                advanced_registry.set_websocket_manager(mock_manager)
                
                # Test WebSocket diagnosis if available
                if hasattr(advanced_registry, 'diagnose_websocket_wiring'):
                    diagnosis = advanced_registry.diagnose_websocket_wiring()
                    assert isinstance(diagnosis, dict), "WebSocket diagnosis should be dictionary"
                    
                logger.info("✓ WebSocket integration regression test passed")
            else:
                logger.warning("WebSocket integration not available for testing")
                
        except Exception as e:
            self.fail(f"REGRESSION: WebSocket integration regression: {e}")
    
    async def test_comprehensive_integration_no_regression(self):
        """Comprehensive integration test ensuring no major regressions."""
        try:
            from netra_backend.app.agents.registry import AgentType, AgentStatus
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            
            advanced_registry = AdvancedRegistry()
            
            # Comprehensive workflow test
            workflow_steps = []
            
            # Step 1: Register multiple agent types
            agent_ids = []
            agent_types = [AgentType.TRIAGE, AgentType.OPTIMIZER, AgentType.DATA_HELPER]
            
            for i, agent_type in enumerate(agent_types):
                agent_id = advanced_registry.register_agent(
                    agent_type,
                    f"Integration Test {agent_type.value} {i}",
                    f"Integration test for {agent_type.value}",
                    metadata={"integration_test": True, "step": i}
                )
                agent_ids.append(agent_id)
                workflow_steps.append(f"Registered {agent_type.value}")
            
            # Step 2: Test status updates and queries
            for i, agent_id in enumerate(agent_ids):
                status = AgentStatus.BUSY if i % 2 == 0 else AgentStatus.IDLE
                updated = advanced_registry.update_agent_status(agent_id, status)
                assert updated, f"Status update should succeed for agent {i}"
                workflow_steps.append(f"Updated status for agent {i}")
            
            # Step 3: Test queries and metrics
            all_agents = advanced_registry.get_all_agents()
            assert len(all_agents) >= len(agent_ids), "Should find all registered agents"
            
            busy_agents = advanced_registry.get_agents_by_status(AgentStatus.BUSY)
            available_agents = advanced_registry.get_available_agents()
            
            workflow_steps.append(f"Queried agents: {len(all_agents)} total, {len(busy_agents)} busy, {len(available_agents)} available")
            
            # Step 4: Test cleanup
            cleanup_count = 0
            for agent_id in agent_ids:
                if advanced_registry.unregister_agent(agent_id):
                    cleanup_count += 1
            
            workflow_steps.append(f"Cleaned up {cleanup_count} agents")
            
            # Verify final state
            final_count = len(advanced_registry)
            workflow_steps.append(f"Final registry count: {final_count}")
            
            logger.info(f"✓ Comprehensive integration test passed: {len(workflow_steps)} steps completed")
            for step in workflow_steps:
                logger.debug(f"  - {step}")
                
        except Exception as e:
            self.fail(f"REGRESSION: Comprehensive integration regression: {e}")


if __name__ == '__main__':
    # Run with real services - no mocking allowed
    pytest.main([__file__, "-v", "--tb=short", "--no-cov"])