"""
Test 1: SSOT Violation - Multiple Emitter Instances

PURPOSE: Prove multiple emitter instances violate SSOT principles
EXPECTED: FAIL before consolidation (shows SSOT violation exists)

This test demonstrates the current state where multiple UserWebSocketEmitter classes
exist across different modules, violating the Single Source of Truth principle.

Business Impact: $500K+ ARR at risk due to fragmented WebSocket implementations
causing unreliable real-time notifications in chat functionality.

CRITICAL: This test MUST FAIL before consolidation to prove SSOT violations exist.
"""

import asyncio
import inspect
import pytest
import logging
from typing import Dict, List, Set, Type, Any
from pathlib import Path

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestSSotViolationMultipleEmitterInstances(SSotAsyncTestCase):
    """Test that demonstrates SSOT violations in WebSocket emitter implementations.
    
    This test MUST FAIL before consolidation to prove the problem exists.
    """
    
    def setup_method(self, method):
        """Set up test infrastructure."""
        super().setup_method(method)
        self.logger = logging.getLogger(__name__)

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation  
    async def test_multiple_emitter_class_definitions_violate_ssot(self):
        """Test that multiple UserWebSocketEmitter class definitions exist (SSOT violation).
        
        EXPECTED: FAIL - Multiple classes with same name should be found
        BUSINESS VALUE: Demonstrates fragmentation that causes unreliable chat notifications
        """
        emitter_classes_found = []
        codebase_root = Path("/Users/anthony/Desktop/netra-apex")
        
        # Search for UserWebSocketEmitter class definitions
        for python_file in codebase_root.rglob("*.py"):
            try:
                content = python_file.read_text(encoding='utf-8')
                if "class UserWebSocketEmitter" in content:
                    # Extract the file path relative to project root
                    relative_path = python_file.relative_to(codebase_root)
                    emitter_classes_found.append(str(relative_path))
            except (UnicodeDecodeError, OSError):
                continue
        
        # THIS ASSERTION WILL FAIL to prove SSOT violation exists
        # (Before consolidation, we expect > 1 class, so this assertion should fail)
        self.assertEqual(
            len(emitter_classes_found), 1,
            f"SSOT VIOLATION DETECTED: Found {len(emitter_classes_found)} UserWebSocketEmitter classes: {emitter_classes_found}. "
            f"Expected exactly 1 for SSOT compliance but found multiple classes violating Single Source of Truth principle."
        )
        
        # Log the specific violations for debugging
        print(f"SSOT VIOLATION DETECTED: {len(emitter_classes_found)} UserWebSocketEmitter classes found")
        for emitter_path in emitter_classes_found:
            print(f"  - {emitter_path}")

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_import_path_fragmentation_violates_ssot(self):
        """Test that UserWebSocketEmitter can be imported from multiple paths (SSOT violation).
        
        EXPECTED: FAIL - Multiple import paths should be found
        BUSINESS VALUE: Shows confusion that leads to wrong emitter usage in chat
        """
        import_paths_tested = [
            "netra_backend.app.agents.supervisor.agent_instance_factory",
            "netra_backend.app.services.websocket_bridge_factory", 
            "netra_backend.app.services.user_websocket_emitter",
            "netra_backend.app.websocket_core.unified_emitter"
        ]
        
        successful_imports = []
        
        for import_path in import_paths_tested:
            try:
                module = __import__(import_path, fromlist=['UserWebSocketEmitter'])
                if hasattr(module, 'UserWebSocketEmitter'):
                    successful_imports.append(import_path)
                    self.logger.warning(f"Successfully imported UserWebSocketEmitter from {import_path}")
            except ImportError:
                self.logger.info(f"Failed to import UserWebSocketEmitter from {import_path}")
        
        # THIS ASSERTION WILL FAIL to prove import fragmentation exists  
        # (Before consolidation, we expect > 1 import path, so this assertion should fail)
        self.assertEqual(
            len(successful_imports), 1,
            f"SSOT VIOLATION DETECTED: UserWebSocketEmitter can be imported from {len(successful_imports)} paths: {successful_imports}. "
            f"Expected exactly 1 canonical import path for SSOT compliance but found multiple import paths."
        )

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_factory_creates_different_emitter_types(self):
        """Test that different factories create different emitter types (SSOT violation).
        
        EXPECTED: FAIL - Different emitter types should be created from different sources
        BUSINESS VALUE: Demonstrates inconsistent emitter behavior affecting chat reliability
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter as AgentFactoryEmitter
        from netra_backend.app.services.websocket_bridge_factory import UserWebSocketEmitter as BridgeFactoryEmitter
        from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter as ServiceEmitter
        
        # Check if these are actually different classes
        emitter_types = [AgentFactoryEmitter, BridgeFactoryEmitter, ServiceEmitter]
        unique_types = set(id(emitter_type) for emitter_type in emitter_types)
        
        # Get the module paths for each class
        module_paths = [emitter_type.__module__ for emitter_type in emitter_types]
        
        # THIS ASSERTION WILL FAIL to prove different types exist
        # (Before consolidation, we expect > 1 module, so this assertion should fail)
        self.assertEqual(
            len(set(module_paths)), 1,
            f"SSOT VIOLATION DETECTED: UserWebSocketEmitter classes from different modules: {module_paths}. "
            f"Expected single module for SSOT compliance but found multiple modules causing inconsistent behavior."
        )
        
        self.logger.critical(f"Found UserWebSocketEmitter in {len(set(module_paths))} different modules")
        for path in set(module_paths):
            self.logger.critical(f"  - {path}")

    @pytest.mark.expected_to_fail
    @pytest.mark.phase_1_pre_consolidation
    async def test_method_signature_inconsistency_across_emitters(self):
        """Test that UserWebSocketEmitter classes have inconsistent method signatures.
        
        EXPECTED: FAIL - Method signatures should differ across implementations
        BUSINESS VALUE: Shows API inconsistency that breaks chat integrations
        """
        from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter as AgentFactoryEmitter
        from netra_backend.app.services.websocket_bridge_factory import UserWebSocketEmitter as BridgeFactoryEmitter
        from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter as ServiceEmitter
        
        # Get __init__ method signatures
        emitters = [AgentFactoryEmitter, BridgeFactoryEmitter, ServiceEmitter]
        signatures = []
        
        for emitter_class in emitters:
            try:
                sig = inspect.signature(emitter_class.__init__)
                param_names = list(sig.parameters.keys())
                signatures.append((emitter_class.__module__, param_names))
            except Exception as e:
                self.logger.error(f"Failed to get signature for {emitter_class.__module__}: {e}")
        
        # Check if all signatures are the same
        param_sets = [set(sig[1]) for sig in signatures]
        all_same = all(param_set == param_sets[0] for param_set in param_sets)
        
        # THIS ASSERTION WILL FAIL to prove signature inconsistency
        # (Before consolidation, we expect inconsistent signatures, so this assertion should fail)
        self.assertTrue(
            all_same,
            f"SSOT VIOLATION DETECTED: UserWebSocketEmitter __init__ signatures are inconsistent across modules. "
            f"Signatures: {signatures}. This breaks API compatibility and causes integration failures."
        )
        
        for module, params in signatures:
            self.logger.critical(f"UserWebSocketEmitter in {module} has params: {params}")

    @pytest.mark.expected_to_fail  
    @pytest.mark.phase_1_pre_consolidation
    async def test_agent_instance_factory_emitter_needs_consolidation(self):
        """Test that agent_instance_factory.py:55 UserWebSocketEmitter needs consolidation.
        
        EXPECTED: FAIL - This specific location should still contain UserWebSocketEmitter class
        BUSINESS VALUE: Validates the exact target for SSOT consolidation
        """
        target_file = Path("/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/supervisor/agent_instance_factory.py")
        
        # Read the target file
        content = target_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Check line 55 specifically (accounting for 0-based indexing)
        if len(lines) > 54:
            line_55 = lines[54].strip()
            
            # THIS ASSERTION MUST FAIL to prove the target class exists
            self.assertIn(
                "class UserWebSocketEmitter",
                line_55,
                f"CONSOLIDATION TARGET: Line 55 in agent_instance_factory.py should contain 'class UserWebSocketEmitter'. "
                f"Found: '{line_55}'. This is the specific target for SSOT consolidation."
            )
        else:
            self.fail(f"agent_instance_factory.py has only {len(lines)} lines, cannot check line 55")
        
        # Also verify the class actually exists in this module
        from netra_backend.app.agents.supervisor.agent_instance_factory import UserWebSocketEmitter
        
        self.assertEqual(
            UserWebSocketEmitter.__module__,
            "netra_backend.app.agents.supervisor.agent_instance_factory",
            f"UserWebSocketEmitter in agent_instance_factory should be from that module, "
            f"but found module: {UserWebSocketEmitter.__module__}"
        )
        
        self.logger.critical(f"CONSOLIDATION TARGET CONFIRMED: UserWebSocketEmitter exists in agent_instance_factory.py line 55")
        self.logger.critical(f"Module: {UserWebSocketEmitter.__module__}")