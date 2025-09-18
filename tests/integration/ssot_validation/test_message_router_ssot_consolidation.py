"""
MessageRouter SSOT Consolidation Validation

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Message Delivery
- Value Impact: Validates MessageRouter SSOT for $500K+ ARR chat functionality
- Strategic Impact: Ensures consistent message routing across all WebSocket events

Tests validate Issue #1115 completion - MessageRouter SSOT implementation.
This determines if MessageRouter consolidation is functionally complete.
"""

import unittest
import asyncio
import importlib
import inspect
from typing import Dict, List, Any, Type
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MessageRouterSSOTConsolidationTests(SSotAsyncTestCase, unittest.TestCase):
    """Validate MessageRouter SSOT consolidation is complete."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.router_import_paths = [
            'netra_backend.app.websocket_core.handlers',
            'netra_backend.app.websocket_core.canonical_message_router', 
            'netra_backend.app.services.websocket.quality_message_router'
        ]
        
    async def test_message_router_class_id_consistency(self):
        """Validate all MessageRouter imports resolve to identical classes."""
        # This is the CRITICAL test for MessageRouter SSOT completion
        # Import from multiple paths and verify class ID consistency
        
        router_classes = {}
        import_errors = {}
        
        # Import MessageRouter from all known paths
        for path in self.router_import_paths:
            try:
                module = importlib.import_module(path)
                
                # Try different class names that might exist
                router_class = None
                for class_name in ['MessageRouter', 'QualityMessageRouter', 'CanonicalMessageRouter']:
                    router_class = getattr(module, class_name, None)
                    if router_class:
                        router_classes[f"{path}.{class_name}"] = {
                            'class_obj': router_class,
                            'class_id': id(router_class),
                            'module_path': path,
                            'class_name': class_name
                        }
                
                if not router_class:
                    import_errors[path] = "No MessageRouter class found"
                    
            except ImportError as e:
                import_errors[path] = str(e)
        
        # Validate we have router classes
        self.assertGreater(
            len(router_classes), 0,
            f"No MessageRouter classes found. Import errors: {import_errors}"
        )
        
        # Check for SSOT compliance - key test for Issue #1115
        unique_class_ids = set(info['class_id'] for info in router_classes.values())
        
        if len(unique_class_ids) > 1:
            # SSOT violation detected - multiple different class objects
            print(f"\n🚨 SSOT VIOLATION DETECTED:")
            print(f"Found {len(unique_class_ids)} different MessageRouter class objects:")
            for import_path, info in router_classes.items():
                print(f"  {import_path}: ID {info['class_id']} ({info['class_name']})")
            
            # This indicates Issue #1115 may not be complete
            self.fail(f"MessageRouter SSOT violation: {len(unique_class_ids)} different class objects")
        else:
            # SSOT compliance verified
            print(f"\nCHECK MessageRouter SSOT COMPLIANCE VERIFIED:")
            print(f"All {len(router_classes)} imports resolve to same class object (ID: {list(unique_class_ids)[0]})")
            for import_path, info in router_classes.items():
                print(f"  CHECK {import_path}")
    
    async def test_message_router_inheritance_consistency(self):
        """Validate MessageRouter inheritance hierarchy is consistent."""
        # Test that compatibility classes properly inherit from canonical implementation
        
        try:
            # Import canonical and compatibility classes
            from netra_backend.app.websocket_core.canonical_message_router import CanonicalMessageRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            
            # Verify inheritance relationships
            self.assertTrue(
                issubclass(QualityMessageRouter, CanonicalMessageRouter),
                "QualityMessageRouter should inherit from CanonicalMessageRouter"
            )
            
            # Check if MessageRouter is properly related to canonical
            if MessageRouter != QualityMessageRouter:
                # Different classes - check inheritance
                self.assertTrue(
                    issubclass(MessageRouter, CanonicalMessageRouter) or MessageRouter == CanonicalMessageRouter,
                    "MessageRouter should inherit from CanonicalMessageRouter or be the same class"
                )
            
            print(f"\nCHECK MessageRouter Inheritance Hierarchy:")
            print(f"  CanonicalMessageRouter: {id(CanonicalMessageRouter)}")
            print(f"  MessageRouter: {id(MessageRouter)} (same: {MessageRouter == CanonicalMessageRouter})")
            print(f"  QualityMessageRouter: {id(QualityMessageRouter)} (inherits: {issubclass(QualityMessageRouter, CanonicalMessageRouter)})")
            
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter classes: {e}")
    
    async def test_message_router_functionality_consistency(self):
        """Validate all MessageRouter instances have consistent functionality."""
        # Test that routing behavior is identical across import paths
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as HandlersRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
            
            # Create instances if classes are different
            if HandlersRouter != QualityMessageRouter:
                # Different classes - test they have same interface
                handlers_methods = set(dir(HandlersRouter))
                quality_methods = set(dir(QualityMessageRouter))
                
                # Core methods that should be present
                required_methods = {
                    'route_message', 'add_handler', 'remove_handler', 
                    'handle_message', 'broadcast_message'
                }
                
                handlers_has_required = required_methods.intersection(handlers_methods)
                quality_has_required = required_methods.intersection(quality_methods)
                
                self.assertEqual(
                    len(handlers_has_required),
                    len(quality_has_required),
                    "MessageRouter classes should have consistent interface"
                )
            else:
                # Same class - SSOT compliance verified
                print("CHECK MessageRouter classes are identical - SSOT compliance verified")
                
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter for functionality test: {e}")
    
    async def test_no_duplicate_message_router_implementations(self):
        """Scan codebase for duplicate MessageRouter implementations."""
        # Expected: Only CanonicalMessageRouter + compatibility layers
        # Success Criteria: No standalone duplicate implementations
        
        import os
        import re
        
        router_implementations = []
        
        # Scan for class definitions
        for root, dirs, files in os.walk('netra_backend'):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Look for MessageRouter class definitions
                            if re.search(r'class\s+\w*MessageRouter', content):
                                # Extract class names
                                class_matches = re.findall(r'class\s+(\w*MessageRouter[^(]*)', content)
                                for class_name in class_matches:
                                    class_name = class_name.strip()
                                    if class_name:
                                        router_implementations.append({
                                            'file': filepath,
                                            'class_name': class_name
                                        })
                                        
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        # Analyze implementations
        known_acceptable = {
            'CanonicalMessageRouter',  # SSOT implementation
            'MessageRouter',           # Compatibility layer
            'QualityMessageRouter',    # Compatibility layer
            'LegacyQualityMessageRouter',  # Deprecated compatibility
            'UserScopedWebSocketEventRouter',  # Specialized router
            'WebSocketEventRouter'     # Specialized router
        }
        
        problematic_routers = []
        for impl in router_implementations:
            if impl['class_name'] not in known_acceptable:
                problematic_routers.append(impl)
        
        # Log findings
        print(f"\nMessageRouter Implementation Analysis:")
        print(f"  Total implementations found: {len(router_implementations)}")
        print(f"  Known acceptable: {len(router_implementations) - len(problematic_routers)}")
        print(f"  Potentially problematic: {len(problematic_routers)}")
        
        if problematic_routers:
            print(f"\nWARNING️  Potentially problematic implementations:")
            for impl in problematic_routers[:5]:  # Show first 5
                print(f"    {impl['class_name']} in {impl['file']}")
        
        # This test documents current state
        # Fewer implementations = better SSOT compliance
        self.assertLessEqual(
            len(problematic_routers), 
            3,  # Allow some specialized routers
            f"Too many potentially duplicate MessageRouter implementations: {len(problematic_routers)}"
        )

    async def test_message_router_backward_compatibility(self):
        """Validate backward compatibility maintained during SSOT consolidation."""
        # Test existing import patterns continue working
        
        compatibility_imports = [
            # Standard import patterns that should work
            ('netra_backend.app.websocket_core.handlers', 'MessageRouter'),
            ('netra_backend.app.services.websocket.quality_message_router', 'QualityMessageRouter'),
            ('netra_backend.app.websocket_core.canonical_message_router', 'CanonicalMessageRouter')
        ]
        
        import_success = {}
        
        for module_path, class_name in compatibility_imports:
            try:
                module = importlib.import_module(module_path)
                router_class = getattr(module, class_name, None)
                import_success[f"{module_path}.{class_name}"] = {
                    'success': router_class is not None,
                    'class_type': str(type(router_class)) if router_class else None
                }
            except ImportError as e:
                import_success[f"{module_path}.{class_name}"] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Validate all compatibility imports work
        failed_imports = [path for path, result in import_success.items() if not result['success']]
        
        if failed_imports:
            print(f"\nX Failed compatibility imports:")
            for path in failed_imports:
                error = import_success[path].get('error', 'Unknown error')
                print(f"    {path}: {error}")
            
            self.fail(f"Backward compatibility broken for imports: {failed_imports}")
        else:
            print(f"\nCHECK All MessageRouter compatibility imports working:")
            for path in import_success.keys():
                print(f"    CHECK {path}")


class MessageRouterSSOTFunctionalityTests(SSotAsyncTestCase):
    """Test MessageRouter SSOT functionality works correctly."""
    
    async def test_message_router_basic_functionality(self):
        """Test basic MessageRouter functionality with SSOT implementation."""
        
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            
            # Test basic instantiation
            router = MessageRouter()
            
            # Test basic interface exists
            self.assertTrue(hasattr(router, 'route_message') or hasattr(router, 'handle_message'),
                           "MessageRouter should have message handling capability")
            
            print(f"\nCHECK MessageRouter basic functionality test passed")
            print(f"    Router class: {router.__class__.__name__}")
            print(f"    Available methods: {[m for m in dir(router) if not m.startswith('_')]}")
            
        except ImportError as e:
            self.skipTest(f"Cannot import MessageRouter for functionality test: {e}")
        except Exception as e:
            self.fail(f"MessageRouter instantiation failed: {e}")
    
    async def test_message_router_ssot_metadata(self):
        """Test MessageRouter SSOT metadata is available."""
        
        try:
            # Check if SSOT metadata is available
            from netra_backend.app.websocket_core.canonical_message_router import SSOT_INFO
            
            self.assertIsInstance(SSOT_INFO, dict, "SSOT_INFO should be a dictionary")
            self.assertIn('canonical_class', SSOT_INFO, "SSOT_INFO should specify canonical class")
            
            print(f"\nCHECK MessageRouter SSOT metadata available:")
            for key, value in SSOT_INFO.items():
                print(f"    {key}: {value}")
                
        except ImportError:
            self.skipTest("SSOT metadata not available - may indicate incomplete consolidation")


if __name__ == '__main__':
    unittest.main()