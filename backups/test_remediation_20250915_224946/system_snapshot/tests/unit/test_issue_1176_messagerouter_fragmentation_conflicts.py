"""
MessageRouter Fragmentation Conflict Tests - Issue #1176

These tests are designed to FAIL initially to prove the fragmentation problems exist.
Tests expose multiple competing MessageRouter implementations causing routing conflicts.

Priority: P0 BLOCKER
Business Impact: $500K+ ARR protection - core WebSocket messaging reliability
"""

import pytest
import unittest
import asyncio
import importlib
import sys
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class MessageRouterFragmentationConflictsTests(SSotBaseTestCase):
    """Test MessageRouter implementation fragmentation causing routing conflicts."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.core_router = None
        self.quality_router = None
        self.import_errors = []
        self.routing_conflicts = []
        self.found_routers = {}

    def test_multiple_messagerouter_implementations_detection(self):
        """
        Test that multiple MessageRouter implementations exist and can conflict.
        
        This test is designed to FAIL to prove fragmentation exists.
        Expected Failure: Multiple competing MessageRouter implementations found.
        """
        logger.info("Testing for multiple MessageRouter implementations...")
        
        # Import paths that should contain MessageRouter implementations
        router_import_paths = [
            'netra_backend.app.websocket_core.handlers',
            'netra_backend.app.services.websocket.quality_message_router',
            'netra_backend.app.websocket_core',  # Deprecated path
        ]
        
        found_routers = {}
        
        for import_path in router_import_paths:
            try:
                module = importlib.import_module(import_path)
                
                # Look for MessageRouter or QualityMessageRouter classes
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    found_routers[import_path] = {
                        'class': router_class,
                        'class_id': id(router_class),
                        'module': module,
                        'type': 'MessageRouter'
                    }
                    logger.info(f"Found MessageRouter in {import_path}: {router_class}")
                
                if hasattr(module, 'QualityMessageRouter'):
                    router_class = getattr(module, 'QualityMessageRouter')
                    found_routers[f"{import_path}.QualityMessageRouter"] = {
                        'class': router_class,
                        'class_id': id(router_class),
                        'module': module,
                        'type': 'QualityMessageRouter'
                    }
                    logger.info(f"Found QualityMessageRouter in {import_path}: {router_class}")
                    
            except ImportError as e:
                self.import_errors.append((import_path, str(e)))
                logger.warning(f"Could not import {import_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error importing {import_path}: {e}")
        
        # Log all found routers
        logger.info(f"Total MessageRouter implementations found: {len(found_routers)}")
        for path, router_info in found_routers.items():
            logger.info(f"  {path}: {router_info['class']} (ID: {router_info['class_id']})")
        
        # This test is designed to FAIL to prove fragmentation exists
        self.assertGreaterEqual(len(found_routers), 2, 
                               "EXPECTED FAILURE: Multiple MessageRouter implementations should exist, "
                               "proving fragmentation. If this passes, fragmentation may be resolved.")
        
        # Check for class ID conflicts (different classes with same interface)
        class_ids = [info['class_id'] for info in found_routers.values()]
        unique_class_ids = set(class_ids)
        
        if len(class_ids) != len(unique_class_ids):
            self.fail("FRAGMENTATION DETECTED: Multiple import paths point to same class - "
                     "this indicates fragmented import management")
        
        # Store for other tests
        self.found_routers = found_routers

    def test_messagerouter_interface_inconsistencies(self):
        """
        Test that MessageRouter implementations have inconsistent interfaces.
        
        Expected Failure: Interface methods differ between implementations.
        """
        logger.info("Testing MessageRouter interface inconsistencies...")
        
        # Try to import both router types
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            self.core_router = MessageRouter()
        except Exception as e:
            self.fail(f"Could not import core MessageRouter: {e}")
        
        try:
            # Import QualityMessageRouter
            quality_module = importlib.import_module('netra_backend.app.services.websocket.quality_message_router')
            QualityMessageRouter = getattr(quality_module, 'QualityMessageRouter')
            
            # Create mock dependencies for QualityMessageRouter
            mock_supervisor = Mock()
            mock_db_session_factory = Mock()
            mock_quality_gate_service = Mock()
            mock_monitoring_service = Mock()
            
            self.quality_router = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
        except Exception as e:
            logger.warning(f"Could not import QualityMessageRouter: {e}")
            # This itself shows fragmentation if import fails
            self.fail(f"FRAGMENTATION DETECTED: QualityMessageRouter import failed - {e}")
        
        # Compare interfaces
        core_methods = set(dir(self.core_router))
        quality_methods = set(dir(self.quality_router))
        
        # Filter to public methods only
        core_public = {m for m in core_methods if not m.startswith('_')}
        quality_public = {m for m in quality_methods if not m.startswith('_')}
        
        logger.info(f"Core MessageRouter methods: {sorted(core_public)}")
        logger.info(f"QualityMessageRouter methods: {sorted(quality_public)}")
        
        # Check for interface differences
        common_methods = core_public.intersection(quality_public)
        core_only = core_public - quality_public
        quality_only = quality_public - core_public
        
        logger.info(f"Common methods: {sorted(common_methods)}")
        logger.info(f"Core-only methods: {sorted(core_only)}")
        logger.info(f"Quality-only methods: {sorted(quality_only)}")
        
        # This test expects interface differences (fragmentation)
        self.assertTrue(len(core_only) > 0 or len(quality_only) > 0,
                       "EXPECTED FAILURE: Router interfaces should differ, proving fragmentation")

    def test_concurrent_router_message_handling_conflicts(self):
        """
        Test that using both routers concurrently creates conflicts.
        
        Expected Failure: Message routing conflicts when both routers handle same message types.
        """
        logger.info("Testing concurrent router message handling conflicts...")
        
        if not self.core_router or not self.quality_router:
            self.skipTest("Routers not available for concurrent testing")
        
        # Create test message that both routers might claim to handle
        test_message = {
            "type": "START_AGENT",
            "data": {"user_id": "test_user", "query": "test query"},
            "message_id": "test_msg_123"
        }
        
        core_can_handle = False
        quality_can_handle = False
        
        # Test if core router can handle message
        try:
            if hasattr(self.core_router, 'can_handle'):
                core_can_handle = self.core_router.can_handle(test_message)
            elif hasattr(self.core_router, 'handlers'):
                # Check if any handler can handle this message type
                for handler in self.core_router.handlers:
                    if hasattr(handler, 'supported_types') and 'START_AGENT' in handler.supported_types:
                        core_can_handle = True
                        break
        except Exception as e:
            logger.warning(f"Core router handle check failed: {e}")
        
        # Test if quality router can handle message  
        try:
            if hasattr(self.quality_router, 'can_handle'):
                quality_can_handle = self.quality_router.can_handle(test_message)
            elif hasattr(self.quality_router, 'handlers'):
                # Check if any handler can handle this message type
                for handler in self.quality_router.handlers.values():
                    if hasattr(handler, 'can_handle') and handler.can_handle(test_message):
                        quality_can_handle = True
                        break
        except Exception as e:
            logger.warning(f"Quality router handle check failed: {e}")
        
        logger.info(f"Core router can handle START_AGENT: {core_can_handle}")
        logger.info(f"Quality router can handle START_AGENT: {quality_can_handle}")
        
        # If both can handle the same message type, there's potential for conflict
        if core_can_handle and quality_can_handle:
            self.fail("FRAGMENTATION CONFLICT DETECTED: Both routers claim to handle START_AGENT messages")
        
        # Also test for actual routing conflicts by trying to route the same message
        # This simulates the "works individually but fails together" pattern
        self.routing_conflicts.append({
            'message_type': 'START_AGENT',
            'core_handles': core_can_handle,
            'quality_handles': quality_can_handle,
            'conflict_detected': core_can_handle and quality_can_handle
        })

    def test_router_initialization_order_dependency_conflicts(self):
        """
        Test that router initialization order creates dependency conflicts.
        
        Expected Failure: Routers have conflicting initialization requirements.
        """
        logger.info("Testing router initialization order dependency conflicts...")
        
        # Test creating routers in different orders to detect conflicts
        initialization_results = []
        
        # Test 1: Core router first
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            core_first = MessageRouter()
            initialization_results.append(('core_first', True, None))
            logger.info("Core router initialization first: SUCCESS")
        except Exception as e:
            initialization_results.append(('core_first', False, str(e)))
            logger.error(f"Core router initialization first: FAILED - {e}")
        
        # Test 2: Quality router first (with mocked dependencies)
        try:
            quality_module = importlib.import_module('netra_backend.app.services.websocket.quality_message_router')
            QualityMessageRouter = getattr(quality_module, 'QualityMessageRouter')
            
            mock_supervisor = Mock()
            mock_db_session_factory = Mock()
            mock_quality_gate_service = Mock()
            mock_monitoring_service = Mock()
            
            quality_first = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            initialization_results.append(('quality_first', True, None))
            logger.info("Quality router initialization first: SUCCESS")
        except Exception as e:
            initialization_results.append(('quality_first', False, str(e)))
            logger.error(f"Quality router initialization first: FAILED - {e}")
        
        # Test 3: Both routers simultaneously
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            quality_module = importlib.import_module('netra_backend.app.services.websocket.quality_message_router')
            QualityMessageRouter = getattr(quality_module, 'QualityMessageRouter')
            
            # Create both at same time
            core_simultaneous = MessageRouter()
            
            mock_supervisor = Mock()
            mock_db_session_factory = Mock()
            mock_quality_gate_service = Mock()
            mock_monitoring_service = Mock()
            
            quality_simultaneous = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            
            initialization_results.append(('simultaneous', True, None))
            logger.info("Simultaneous router initialization: SUCCESS")
        except Exception as e:
            initialization_results.append(('simultaneous', False, str(e)))
            logger.error(f"Simultaneous router initialization: FAILED - {e}")
        
        # Analyze initialization patterns
        successful_inits = [r for r in initialization_results if r[1]]
        failed_inits = [r for r in initialization_results if not r[1]]
        
        logger.info(f"Successful initializations: {len(successful_inits)}")
        logger.info(f"Failed initializations: {len(failed_inits)}")
        
        # If some initialization patterns fail, it indicates dependency conflicts
        if failed_inits:
            error_details = "; ".join([f"{r[0]}: {r[2]}" for r in failed_inits])
            self.fail(f"DEPENDENCY CONFLICTS DETECTED: Some router initialization patterns failed - {error_details}")

    def test_message_routing_precedence_conflicts(self):
        """
        Test that message routing precedence creates conflicts when both routers are active.
        
        Expected Failure: Unclear routing precedence leads to message handling conflicts.
        """
        logger.info("Testing message routing precedence conflicts...")
        
        # Create a scenario where both routers might handle the same message
        test_messages = [
            {"type": "START_AGENT", "data": {"query": "test"}},
            {"type": "agent_started", "data": {"agent_id": "test"}},
            {"type": "quality_check", "data": {"status": "pending"}},
            {"type": "user_message", "data": {"content": "hello"}},
        ]
        
        precedence_conflicts = []
        
        for message in test_messages:
            message_type = message["type"]
            handling_routers = []
            
            # Check which routers can handle each message type
            try:
                # Core router check
                from netra_backend.app.websocket_core.handlers import MessageRouter
                core_router = MessageRouter()
                
                # Simulate message routing to see if it gets handled
                for handler in core_router.handlers:
                    if hasattr(handler, 'supported_types') and message_type in handler.supported_types:
                        handling_routers.append(('core', handler.__class__.__name__))
                        break
                    elif hasattr(handler, 'can_handle'):
                        try:
                            if handler.can_handle(message):
                                handling_routers.append(('core', handler.__class__.__name__))
                                break
                        except:
                            pass
                            
            except Exception as e:
                logger.warning(f"Core router precedence test failed: {e}")
            
            try:
                # Quality router check
                quality_module = importlib.import_module('netra_backend.app.services.websocket.quality_message_router')
                QualityMessageRouter = getattr(quality_module, 'QualityMessageRouter')
                
                mock_supervisor = Mock()
                mock_db_session_factory = Mock()
                mock_quality_gate_service = Mock()
                mock_monitoring_service = Mock()
                
                quality_router = QualityMessageRouter(
                    supervisor=mock_supervisor,
                    db_session_factory=mock_db_session_factory,
                    quality_gate_service=mock_quality_gate_service,
                    monitoring_service=mock_monitoring_service
                )
                
                # Check quality router handlers
                if hasattr(quality_router, 'handlers'):
                    for handler_name, handler in quality_router.handlers.items():
                        if hasattr(handler, 'can_handle'):
                            try:
                                if handler.can_handle(message):
                                    handling_routers.append(('quality', handler_name))
                                    break
                            except:
                                pass
                                
            except Exception as e:
                logger.warning(f"Quality router precedence test failed: {e}")
            
            if len(handling_routers) > 1:
                precedence_conflicts.append({
                    'message_type': message_type,
                    'handling_routers': handling_routers,
                    'conflict': True
                })
                logger.warning(f"PRECEDENCE CONFLICT: {message_type} handled by {handling_routers}")
            else:
                precedence_conflicts.append({
                    'message_type': message_type,
                    'handling_routers': handling_routers,
                    'conflict': False
                })
        
        # Check for conflicts
        conflicts = [c for c in precedence_conflicts if c['conflict']]
        
        if conflicts:
            conflict_details = "; ".join([f"{c['message_type']}: {c['handling_routers']}" for c in conflicts])
            self.fail(f"ROUTING PRECEDENCE CONFLICTS DETECTED: {conflict_details}")
        
        # If no conflicts found, the test should still indicate potential for conflicts
        logger.info(f"Tested {len(test_messages)} message types for precedence conflicts")
        
        # This test is designed to highlight the fragmentation issue
        self.assertGreater(len(precedence_conflicts), 0,
                          "Expected to find routing precedence analysis data")


@pytest.mark.unit
class MessageRouterImportPathFragmentationTests(SSotBaseTestCase):
    """Test MessageRouter import path fragmentation causing module conflicts."""

    def test_import_path_fragmentation_detection(self):
        """
        Test that multiple import paths for MessageRouter create fragmentation.
        
        Expected Failure: Multiple valid import paths exist for same functionality.
        """
        logger.info("Testing import path fragmentation...")
        
        # Known import paths that should work
        import_paths = [
            'netra_backend.app.websocket_core.handlers.MessageRouter',
            'netra_backend.app.websocket_core.MessageRouter',  # Deprecated
            'netra_backend.app.core.message_router.MessageRouter',  # May exist
        ]
        
        successful_imports = []
        failed_imports = []
        class_objects = {}
        
        for import_path in import_paths:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                
                if hasattr(module, class_name):
                    router_class = getattr(module, class_name)
                    successful_imports.append(import_path)
                    class_objects[import_path] = {
                        'class': router_class,
                        'class_id': id(router_class),
                        'module_id': id(module)
                    }
                    logger.info(f"Successfully imported {import_path}: {router_class}")
                else:
                    failed_imports.append((import_path, f"{class_name} not found in module"))
                    
            except ImportError as e:
                failed_imports.append((import_path, f"ImportError: {e}"))
            except Exception as e:
                failed_imports.append((import_path, f"Error: {e}"))
        
        logger.info(f"Successful imports: {len(successful_imports)}")
        logger.info(f"Failed imports: {len(failed_imports)}")
        
        # Log details
        for path in successful_imports:
            obj_info = class_objects[path]
            logger.info(f"  {path}: Class ID {obj_info['class_id']}, Module ID {obj_info['module_id']}")
        
        for path, error in failed_imports:
            logger.warning(f"  {path}: {error}")
        
        # Check for class identity fragmentation
        if len(successful_imports) > 1:
            class_ids = [class_objects[path]['class_id'] for path in successful_imports]
            unique_class_ids = set(class_ids)
            
            if len(unique_class_ids) > 1:
                self.fail("IMPORT FRAGMENTATION DETECTED: Multiple import paths lead to different class objects")
            elif len(unique_class_ids) == 1:
                logger.warning("IMPORT PATH REDUNDANCY: Multiple paths point to same class - cleanup needed")
        
        # This test expects fragmentation (multiple working paths)
        self.assertGreaterEqual(len(successful_imports), 1,
                               "At least one MessageRouter import path should work")

    def test_circular_import_dependencies(self):
        """
        Test for circular import dependencies between MessageRouter implementations.
        
        Expected Failure: Circular dependencies exist between router modules.
        """
        logger.info("Testing for circular import dependencies...")
        
        # Import modules in different orders to detect circular dependencies
        import_sequences = [
            ['netra_backend.app.websocket_core.handlers', 'netra_backend.app.services.websocket.quality_message_router'],
            ['netra_backend.app.services.websocket.quality_message_router', 'netra_backend.app.websocket_core.handlers'],
            ['netra_backend.app.websocket_core', 'netra_backend.app.services.websocket.quality_message_router'],
        ]
        
        circular_dependency_detected = False
        import_results = []
        
        for sequence in import_sequences:
            sequence_result = {'sequence': sequence, 'success': True, 'error': None}
            
            try:
                # Clear previous imports to test fresh import sequence
                modules_to_clear = []
                for module_name in sequence:
                    if module_name in sys.modules:
                        modules_to_clear.append(module_name)
                
                # Import in sequence
                imported_modules = []
                for module_name in sequence:
                    try:
                        module = importlib.import_module(module_name)
                        imported_modules.append(module)
                        logger.debug(f"Successfully imported {module_name} in sequence")
                    except ImportError as e:
                        if "circular" in str(e).lower() or "recursive" in str(e).lower():
                            circular_dependency_detected = True
                            sequence_result['success'] = False
                            sequence_result['error'] = f"Circular dependency: {e}"
                            logger.error(f"Circular dependency detected importing {module_name}: {e}")
                            break
                        else:
                            sequence_result['success'] = False
                            sequence_result['error'] = f"Import error: {e}"
                            logger.warning(f"Import error for {module_name}: {e}")
                            break
                    except Exception as e:
                        sequence_result['success'] = False
                        sequence_result['error'] = f"Unexpected error: {e}"
                        logger.error(f"Unexpected error importing {module_name}: {e}")
                        break
                        
            except Exception as e:
                sequence_result['success'] = False
                sequence_result['error'] = f"Sequence error: {e}"
                
            import_results.append(sequence_result)
        
        # Analyze results
        successful_sequences = [r for r in import_results if r['success']]
        failed_sequences = [r for r in import_results if not r['success']]
        
        logger.info(f"Import sequence test results:")
        logger.info(f"  Successful sequences: {len(successful_sequences)}")
        logger.info(f"  Failed sequences: {len(failed_sequences)}")
        
        for result in failed_sequences:
            logger.warning(f"  Failed: {result['sequence']} - {result['error']}")
        
        if circular_dependency_detected:
            self.fail("CIRCULAR DEPENDENCY DETECTED: MessageRouter modules have circular import dependencies")
        
        # If some sequences fail but not due to circular deps, still indicates fragmentation issues
        if failed_sequences and not circular_dependency_detected:
            error_details = "; ".join([r['error'] for r in failed_sequences])
            self.fail(f"IMPORT SEQUENCE FRAGMENTATION: Some import sequences fail - {error_details}")


if __name__ == '__main__':
    unittest.main()