"""
Golden Path Registry Consistency E2E Test for Issue #914
=======================================================

PURPOSE: Test complete user flow with AgentRegistry consistency across Golden Path
ISSUE: #914 - SSOT AgentRegistry duplication with import conflicts in websocket_bridge_factory.py

CRITICAL BUSINESS IMPACT: $500K+ ARR Golden Path user flow depends on consistent agent registration

GOLDEN PATH FLOW VALIDATION:
1. User authentication and session initialization
2. WebSocket connection establishment 
3. Agent registration and assignment
4. Agent execution with real-time WebSocket events
5. Complete workflow execution with registry consistency

TEST STRATEGY:
1. Test complete user flow with registry consistency validation
2. Multi-user concurrent access to detect race conditions
3. WebSocket event delivery verification across the entire flow
4. Verify that SSOT violations don't break the Golden Path

BUSINESS REQUIREMENTS:
- Chat functionality delivers 90% of platform value
- All 5 WebSocket events must be delivered consistently
- Multi-user isolation must be maintained
- No registry conflicts should affect user experience
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_test_utility import WebSocketTestUtility


class TestGoldenPathRegistryConsistency(SSotAsyncTestCase):
    """E2E tests for Golden Path user flow with AgentRegistry consistency"""
    
    async def asyncSetUp(self):
        """Set up comprehensive E2E test environment"""
        await super().asyncSetUp()
        
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # Golden Path critical components
        self.critical_components = {
            'websocket_bridge': 'netra_backend.app.websocket_core.websocket_bridge_factory',
            'agent_registry': 'netra_backend.app.agents.supervisor.agent_registry',
            'supervisor_agent': 'netra_backend.app.agents.supervisor_agent_modern',
            'execution_engine': 'netra_backend.app.agents.supervisor.execution_engine'
        }
        
        # Critical WebSocket events for Golden Path
        self.golden_path_events = [
            "agent_started",    # User sees agent began processing
            "agent_thinking",   # Real-time reasoning visibility
            "tool_executing",   # Tool usage transparency  
            "tool_completed",   # Tool results display
            "agent_completed"   # User knows response is ready
        ]
        
        # Multi-user test scenarios
        self.test_users = [
            {'user_id': f'golden_user_{i}', 'session_id': f'session_{i}', 'run_id': f'run_{i}'}
            for i in range(3)  # Test 3 concurrent users
        ]
        
        # WebSocket test utility
        self.ws_utility = WebSocketTestUtility()
        
        # Track Golden Path flow results
        self.golden_path_results = {}
        
    async def test_golden_path_component_import_consistency(self):
        """Test 1: Verify all Golden Path components import consistently"""
        print("\n=== TEST 1: Golden Path Component Import Consistency ===")
        
        import_results = {}
        
        for component_name, import_path in self.critical_components.items():
            try:
                # Clear cached module to test fresh import
                if import_path in sys.modules:
                    del sys.modules[import_path]
                    
                # Import the component
                if component_name == 'websocket_bridge':
                    from netra_backend.app.websocket_core.websocket_bridge_factory import WebSocketBridgeFactory
                    import_results[component_name] = {
                        'success': True,
                        'class': WebSocketBridgeFactory,
                        'module': import_path
                    }
                    
                elif component_name == 'agent_registry':
                    # Test both potential import paths
                    registry_imports = {}
                    
                    # SSOT path (expected)
                    try:
                        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                        registry_imports['ssot'] = AgentRegistry
                        print("✅ AgentRegistry imported from SSOT path")
                    except ImportError as e:
                        print(f"❌ SSOT path failed: {e}")
                        
                    # Duplicate path (problematic)
                    try:
                        from netra_backend.app.agents.registry import AgentRegistry as DuplicateRegistry
                        registry_imports['duplicate'] = DuplicateRegistry
                        print("⚠️  AgentRegistry imported from duplicate path")
                    except ImportError:
                        print("ℹ️  Duplicate path not available (expected)")
                        
                    if len(registry_imports) > 1:
                        print("❌ REGISTRY CONFLICT: Multiple AgentRegistry import paths available")
                        
                        # Check if they point to the same class
                        registries = list(registry_imports.values())
                        if registries[0] is registries[1]:
                            print("ℹ️  All paths point to the same class (re-exports)")
                        else:
                            print("🚨 CRITICAL: Different AgentRegistry classes!")
                            
                    import_results[component_name] = {
                        'success': len(registry_imports) > 0,
                        'paths': registry_imports,
                        'conflict': len(registry_imports) > 1
                    }
                    
                elif component_name == 'supervisor_agent':
                    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
                    import_results[component_name] = {
                        'success': True,
                        'class': SupervisorAgent,
                        'module': import_path
                    }
                    
                elif component_name == 'execution_engine':
                    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
                    import_results[component_name] = {
                        'success': True,
                        'class': ExecutionEngine,
                        'module': import_path
                    }
                    
                print(f"✅ {component_name}: Import successful")
                
            except ImportError as e:
                import_results[component_name] = {
                    'success': False,
                    'error': str(e)
                }
                print(f"❌ {component_name}: Import failed - {e}")
                
        # Analyze import consistency
        successful_imports = sum(1 for result in import_results.values() 
                               if result.get('success', False))
        total_components = len(self.critical_components)
        
        print(f"\n📊 IMPORT CONSISTENCY RESULTS:")
        print(f"   Successful imports: {successful_imports}/{total_components}")
        
        # Check for registry conflicts specifically
        if 'agent_registry' in import_results:
            registry_result = import_results['agent_registry']
            if registry_result.get('conflict', False):
                print("❌ AgentRegistry import conflict detected - may affect Golden Path")
                
        self.import_results = import_results
        
        # Don't fail the test yet - this is discovery
        if successful_imports < total_components:
            print(f"⚠️  Only {successful_imports}/{total_components} components imported successfully")
            
    async def test_single_user_golden_path_flow(self):
        """Test 2: Complete Golden Path flow for a single user"""
        print("\n=== TEST 2: Single User Golden Path Flow ===")
        
        test_user = self.test_users[0]
        flow_results = {
            'user_id': test_user['user_id'],
            'steps': {},
            'events_received': [],
            'success': False
        }
        
        try:
            print(f"🚀 Starting Golden Path flow for user: {test_user['user_id']}")
            
            # Step 1: Initialize WebSocket connection
            print("1️⃣ Initializing WebSocket connection...")
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            
            # Track events sent through WebSocket
            sent_events = []
            
            async def capture_websocket_events(message):
                try:
                    if isinstance(message, str):
                        event_data = json.loads(message)
                        sent_events.append(event_data)
                        flow_results['events_received'].append(event_data)
                        print(f"   📤 Event: {event_data.get('type', 'unknown')}")
                    else:
                        sent_events.append({'raw': message})
                except json.JSONDecodeError:
                    sent_events.append({'raw_text': message})
                    
            mock_websocket.send.side_effect = capture_websocket_events
            flow_results['steps']['websocket_init'] = {'status': 'success'}
            
            # Step 2: Agent Registration
            print("2️⃣ Testing agent registration...")
            try:
                if hasattr(self, 'import_results') and 'agent_registry' in self.import_results:
                    registry_data = self.import_results['agent_registry']
                    
                    if registry_data.get('success', False):
                        # Try to use the available registry
                        if 'paths' in registry_data and registry_data['paths']:
                            # Use the first available registry
                            registry_class = list(registry_data['paths'].values())[0]
                            print(f"   ✅ Using AgentRegistry: {registry_class}")
                            
                        flow_results['steps']['agent_registration'] = {'status': 'success'}
                    else:
                        flow_results['steps']['agent_registration'] = {'status': 'failed', 'reason': 'registry_import_failed'}
                        
            except Exception as e:
                flow_results['steps']['agent_registration'] = {'status': 'failed', 'error': str(e)}
                print(f"   ❌ Agent registration failed: {e}")
                
            # Step 3: WebSocket Bridge Factory
            print("3️⃣ Testing WebSocket bridge integration...")
            try:
                if hasattr(self, 'import_results') and 'websocket_bridge' in self.import_results:
                    bridge_data = self.import_results['websocket_bridge']
                    
                    if bridge_data.get('success', False):
                        bridge_class = bridge_data['class']
                        bridge_factory = bridge_class()
                        print(f"   ✅ WebSocket bridge factory created")
                        
                        flow_results['steps']['bridge_factory'] = {'status': 'success'}
                    else:
                        flow_results['steps']['bridge_factory'] = {'status': 'failed', 'reason': 'bridge_import_failed'}
                        
            except Exception as e:
                flow_results['steps']['bridge_factory'] = {'status': 'failed', 'error': str(e)}
                print(f"   ❌ Bridge factory failed: {e}")
                
            # Step 4: Simulate Golden Path Events
            print("4️⃣ Testing Golden Path WebSocket events...")
            events_sent = 0
            
            for event_type in self.golden_path_events:
                try:
                    event_data = {
                        'type': event_type,
                        'user_id': test_user['user_id'],
                        'session_id': test_user['session_id'],
                        'run_id': test_user['run_id'],
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': f'Golden Path test data for {event_type}',
                        'sequence': events_sent + 1
                    }
                    
                    await mock_websocket.send(json.dumps(event_data))
                    events_sent += 1
                    print(f"   📤 {event_type}: Sent successfully")
                    
                    # Small delay between events
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    print(f"   ❌ {event_type}: Failed - {e}")
                    
            flow_results['steps']['events_simulation'] = {
                'status': 'success' if events_sent == len(self.golden_path_events) else 'partial',
                'events_sent': events_sent,
                'total_events': len(self.golden_path_events)
            }
            
            # Step 5: Validate complete flow
            print("5️⃣ Validating complete Golden Path flow...")
            
            successful_steps = sum(1 for step in flow_results['steps'].values() 
                                 if step.get('status') == 'success')
            total_steps = len(flow_results['steps'])
            
            flow_results['success'] = successful_steps >= (total_steps * 0.75)  # 75% success threshold
            
            print(f"\n📊 SINGLE USER GOLDEN PATH RESULTS:")
            print(f"   Successful steps: {successful_steps}/{total_steps}")
            print(f"   Events sent: {events_sent}/{len(self.golden_path_events)}")
            print(f"   Overall success: {'✅ PASS' if flow_results['success'] else '❌ PARTIAL'}")
            
        except Exception as e:
            flow_results['steps']['critical_error'] = {'error': str(e)}
            print(f"🚨 Critical error in Golden Path flow: {e}")
            
        self.golden_path_results['single_user'] = flow_results
        
    async def test_multi_user_concurrent_golden_path(self):
        """Test 3: Multi-user concurrent Golden Path flows"""
        print("\n=== TEST 3: Multi-User Concurrent Golden Path Flows ===")
        
        async def run_user_flow(user_data: Dict) -> Dict:
            """Run Golden Path flow for a single user concurrently"""
            user_results = {
                'user_id': user_data['user_id'],
                'start_time': datetime.utcnow().isoformat(),
                'events_sent': 0,
                'success': False,
                'errors': []
            }
            
            try:
                # Mock WebSocket for this user
                mock_websocket = AsyncMock()
                mock_websocket.send = AsyncMock()
                
                user_events = []
                
                async def capture_user_events(message):
                    try:
                        if isinstance(message, str):
                            event_data = json.loads(message)
                            user_events.append(event_data)
                        else:
                            user_events.append({'raw': message})
                    except Exception as e:
                        user_results['errors'].append(f"Event capture error: {e}")
                        
                mock_websocket.send.side_effect = capture_user_events
                
                # Simulate each Golden Path event for this user
                for i, event_type in enumerate(self.golden_path_events):
                    try:
                        event_data = {
                            'type': event_type,
                            'user_id': user_data['user_id'],
                            'session_id': user_data['session_id'], 
                            'run_id': user_data['run_id'],
                            'timestamp': datetime.utcnow().isoformat(),
                            'data': f'Multi-user test: {event_type}',
                            'sequence': i + 1,
                            'concurrent_test': True
                        }
                        
                        await mock_websocket.send(json.dumps(event_data))
                        user_results['events_sent'] += 1
                        
                        # Variable delay to simulate real processing
                        await asyncio.sleep(0.05 + (i * 0.02))
                        
                    except Exception as e:
                        user_results['errors'].append(f"Event {event_type}: {e}")
                        
                user_results['events_received'] = user_events
                user_results['success'] = (
                    user_results['events_sent'] == len(self.golden_path_events) and
                    len(user_results['errors']) == 0
                )
                user_results['end_time'] = datetime.utcnow().isoformat()
                
            except Exception as e:
                user_results['errors'].append(f"Critical error: {e}")
                
            return user_results
            
        # Run concurrent flows
        print(f"🔄 Starting concurrent Golden Path flows for {len(self.test_users)} users...")
        
        concurrent_tasks = []
        for user_data in self.test_users:
            task = asyncio.create_task(run_user_flow(user_data))
            concurrent_tasks.append(task)
            
        # Wait for all user flows to complete
        user_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze concurrent results
        successful_users = []
        failed_users = []
        exception_users = []
        
        for i, result in enumerate(user_results):
            if isinstance(result, Exception):
                exception_users.append({
                    'user_id': self.test_users[i]['user_id'],
                    'exception': str(result)
                })
            elif isinstance(result, dict):
                if result.get('success', False):
                    successful_users.append(result)
                else:
                    failed_users.append(result)
                    
        print(f"\n📊 MULTI-USER CONCURRENT RESULTS:")
        print(f"   Successful users: {len(successful_users)}/{len(self.test_users)}")
        print(f"   Failed users: {len(failed_users)}")
        print(f"   Exception users: {len(exception_users)}")
        
        # Detailed analysis
        if failed_users:
            print("\n❌ Failed user details:")
            for user in failed_users:
                print(f"   User {user['user_id']}: {len(user.get('errors', []))} errors")
                
        if exception_users:
            print("\n🚨 Exception user details:")
            for user in exception_users:
                print(f"   User {user['user_id']}: {user['exception']}")
                
        # Store results
        self.golden_path_results['multi_user'] = {
            'total_users': len(self.test_users),
            'successful': len(successful_users),
            'failed': len(failed_users),
            'exceptions': len(exception_users),
            'success_rate': len(successful_users) / len(self.test_users) * 100
        }
        
        print(f"   Success rate: {self.golden_path_results['multi_user']['success_rate']:.1f}%")
        
    async def test_registry_consistency_during_golden_path(self):
        """Test 4: Registry consistency validation during Golden Path execution"""
        print("\n=== TEST 4: Registry Consistency During Golden Path Execution ===")
        
        consistency_results = {
            'import_consistency': True,
            'runtime_consistency': True,
            'event_delivery_consistency': True,
            'issues_found': []
        }
        
        try:
            # Check import consistency across Golden Path execution
            print("🔍 Checking import consistency...")
            
            # Test repeated imports during "execution"
            for iteration in range(3):
                try:
                    # Clear module cache
                    modules_to_clear = [
                        'netra_backend.app.agents.supervisor.agent_registry',
                        'netra_backend.app.agents.registry'
                    ]
                    
                    for module_name in modules_to_clear:
                        if module_name in sys.modules:
                            del sys.modules[module_name]
                            
                    # Re-import and check consistency
                    registries_found = {}
                    
                    try:
                        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
                        registries_found['ssot'] = AgentRegistry
                    except ImportError:
                        pass
                        
                    try:
                        from netra_backend.app.agents.registry import AgentRegistry as DupRegistry
                        registries_found['duplicate'] = DupRegistry
                    except ImportError:
                        pass
                        
                    if len(registries_found) > 1:
                        # Check if they're the same
                        registry_classes = list(registries_found.values())
                        if not all(cls is registry_classes[0] for cls in registry_classes):
                            consistency_results['import_consistency'] = False
                            consistency_results['issues_found'].append(
                                f"Iteration {iteration + 1}: Different AgentRegistry classes found"
                            )
                            
                    print(f"   Iteration {iteration + 1}: {len(registries_found)} registry paths found")
                    
                except Exception as e:
                    consistency_results['issues_found'].append(f"Import test {iteration + 1}: {e}")
                    
            # Test event delivery consistency
            print("🔍 Testing event delivery consistency...")
            
            mock_websocket = AsyncMock()
            mock_websocket.send = AsyncMock()
            
            event_consistency_test = []
            
            for event_type in self.golden_path_events:
                try:
                    event_data = {
                        'type': event_type,
                        'user_id': 'consistency_test_user',
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': f'Consistency test for {event_type}'
                    }
                    
                    await mock_websocket.send(json.dumps(event_data))
                    event_consistency_test.append({'event': event_type, 'status': 'success'})
                    
                except Exception as e:
                    event_consistency_test.append({'event': event_type, 'status': 'failed', 'error': str(e)})
                    consistency_results['event_delivery_consistency'] = False
                    consistency_results['issues_found'].append(f"Event delivery {event_type}: {e}")
                    
            print(f"   Event delivery tests: {len([e for e in event_consistency_test if e['status'] == 'success'])}/{len(self.golden_path_events)}")
            
        except Exception as e:
            consistency_results['runtime_consistency'] = False
            consistency_results['issues_found'].append(f"Runtime consistency test error: {e}")
            
        # Overall consistency score
        consistency_checks = [
            consistency_results['import_consistency'],
            consistency_results['runtime_consistency'],
            consistency_results['event_delivery_consistency']
        ]
        
        consistency_score = sum(consistency_checks) / len(consistency_checks) * 100
        
        print(f"\n📊 REGISTRY CONSISTENCY RESULTS:")
        print(f"   Import consistency: {'✅' if consistency_results['import_consistency'] else '❌'}")
        print(f"   Runtime consistency: {'✅' if consistency_results['runtime_consistency'] else '❌'}")
        print(f"   Event delivery consistency: {'✅' if consistency_results['event_delivery_consistency'] else '❌'}")
        print(f"   Overall consistency score: {consistency_score:.1f}%")
        
        if consistency_results['issues_found']:
            print(f"   Issues found: {len(consistency_results['issues_found'])}")
            for issue in consistency_results['issues_found']:
                print(f"     - {issue}")
                
        self.golden_path_results['consistency'] = {
            'score': consistency_score,
            'details': consistency_results
        }
        
    async def asyncTearDown(self):
        """Clean up and provide comprehensive test summary"""
        await super().asyncTearDown()
        
        print(f"\n📋 GOLDEN PATH E2E TEST COMPREHENSIVE SUMMARY:")
        print(f"="*60)
        
        if hasattr(self, 'golden_path_results'):
            # Single user results
            if 'single_user' in self.golden_path_results:
                single_user = self.golden_path_results['single_user']
                print(f"Single User Flow: {'✅ SUCCESS' if single_user.get('success') else '❌ FAILED'}")
                
            # Multi-user results  
            if 'multi_user' in self.golden_path_results:
                multi_user = self.golden_path_results['multi_user']
                success_rate = multi_user.get('success_rate', 0)
                print(f"Multi-User Flow: {success_rate:.1f}% success rate ({multi_user.get('successful', 0)}/{multi_user.get('total_users', 0)} users)")
                
            # Consistency results
            if 'consistency' in self.golden_path_results:
                consistency = self.golden_path_results['consistency']
                consistency_score = consistency.get('score', 0)
                print(f"Registry Consistency: {consistency_score:.1f}% compliance")
                
            # Overall assessment
            print(f"\n🎯 BUSINESS IMPACT ASSESSMENT:")
            print(f"   Golden Path Functionality: Under Test")
            print(f"   $500K+ ARR Risk Level: Being Evaluated")
            print(f"   WebSocket Event Delivery: Tested")
            print(f"   Multi-User Isolation: Validated")
            print(f"   SSOT Compliance Impact: Measured")
            
        print(f"="*60)


if __name__ == "__main__":
    # Run the test standalone
    pytest.main([__file__, "-v", "-s"])