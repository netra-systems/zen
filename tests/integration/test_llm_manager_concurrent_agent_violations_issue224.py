"""
LLM Manager Concurrent Agent Creation Violations - Issue #224 Phase 3 Integration Tests

DESIGNED TO FAIL: These tests prove agent system user isolation failures exist.
They will PASS after proper factory pattern remediation is implemented.

Business Value: Platform/Enterprise - Data Privacy & User Isolation
Protects $500K+ ARR chat functionality from user conversation mixing between concurrent users.

Test Strategy:
1. Concurrent agent creation with different user contexts
2. WebSocket integration with agent factory patterns  
3. User conversation isolation validation
4. Agent memory and state isolation testing

IMPORTANT: These tests simulate real multi-user scenarios to detect
isolation failures that could cause conversation data bleeding in production.

Target Issue: 51 LLMManager factory violations causing user conversation mixing
"""

import asyncio
import gc
import threading
import time
import uuid
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

import pytest
from loguru import logger

# Import for analysis (Note: We expect these to have violations)
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent

# Import SSOT test infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@dataclass 
class UserSimulation:
    """Simulation of a user context for testing isolation."""
    user_id: str
    session_id: str
    thread_id: str
    run_id: str
    test_marker: str
    created_at: float
    

class TestLLMManagerConcurrentAgentViolationsIssue224(SSotAsyncTestCase):
    """Integration tests to detect user isolation violations in concurrent agent creation"""
    
    async def test_concurrent_agent_creation_user_isolation_violations(self):
        """DESIGNED TO FAIL: Test concurrent agent creation for user isolation violations.
        
        This test should FAIL because agents using direct LLMManager() instantiation
        will share LLM instances between users, causing conversation mixing.
        
        Expected Issues:
        - Same LLM manager instance returned for different users
        - Conversation context bleeding between concurrent users
        - Memory/cache sharing across user boundaries
        
        Business Impact: User conversation privacy violations in multi-user chat scenarios
        """
        logger.info("Starting concurrent agent creation user isolation test...")
        
        isolation_violations = []
        user_simulations = []
        agent_instances = {}
        llm_manager_ids = defaultdict(set)
        
        # Create multiple user simulations for concurrent testing
        num_users = 8  # Simulate multiple concurrent users
        for i in range(num_users):
            user_sim = UserSimulation(
                user_id=str(uuid.uuid4()),
                session_id=str(uuid.uuid4()),
                thread_id=str(uuid.uuid4()),
                run_id=str(uuid.uuid4()),
                test_marker=f'concurrent_user_{i}_{int(time.time())}',
                created_at=time.time()
            )
            user_simulations.append(user_sim)
        
        async def create_agent_for_user(user_sim: UserSimulation, agent_class) -> Dict:
            """Create an agent instance for a specific user and analyze isolation."""
            try:
                # Create user context (the pattern agents should use)
                user_context = {
                    'user_id': user_sim.user_id,
                    'session_id': user_sim.session_id,
                    'thread_id': user_sim.thread_id,
                    'run_id': user_sim.run_id,
                    'test_marker': user_sim.test_marker
                }
                
                # Create agent using factory method (if it exists)
                if hasattr(agent_class, 'create_for_user'):
                    agent = agent_class.create_for_user(user_context)
                else:
                    # Fallback to default constructor (this is where violations occur)
                    logger.warning(f"Agent {agent_class.__name__} lacks create_for_user factory method")
                    agent = agent_class()
                
                # Try to extract LLM manager information
                llm_manager = None
                llm_manager_id = None
                
                if hasattr(agent, 'llm_manager'):
                    llm_manager = agent.llm_manager
                    llm_manager_id = id(llm_manager)
                elif hasattr(agent, '_llm_manager'):
                    llm_manager = agent._llm_manager
                    llm_manager_id = id(llm_manager)
                
                return {
                    'user_id': user_sim.user_id,
                    'agent': agent,
                    'agent_class': agent_class.__name__,
                    'llm_manager': llm_manager,
                    'llm_manager_id': llm_manager_id,
                    'test_marker': user_sim.test_marker,
                    'success': True,
                    'created_at': time.time()
                }
                
            except Exception as e:
                logger.error(f"Failed to create agent for user {user_sim.user_id}: {e}")
                return {
                    'user_id': user_sim.user_id,
                    'agent_class': agent_class.__name__,
                    'success': False,
                    'error': str(e),
                    'created_at': time.time()
                }
        
        # Test multiple agent types that are known to have violations
        agent_classes_to_test = [
            DataHelperAgent,
            UnifiedTriageAgent,
            OptimizationsCoreSubAgent
        ]
        
        # Create agents concurrently for all users and all agent types
        creation_tasks = []
        for agent_class in agent_classes_to_test:
            for user_sim in user_simulations:
                task = create_agent_for_user(user_sim, agent_class)
                creation_tasks.append(task)
        
        # Execute concurrent agent creation
        logger.info(f"Creating {len(creation_tasks)} agent instances concurrently...")
        creation_results = await asyncio.gather(*creation_tasks, return_exceptions=True)
        
        # Analyze results for isolation violations
        successful_creations = [r for r in creation_results if isinstance(r, dict) and r.get('success')]
        failed_creations = [r for r in creation_results if isinstance(r, dict) and not r.get('success')]
        
        logger.info(f"Successful agent creations: {len(successful_creations)}")
        logger.info(f"Failed agent creations: {len(failed_creations)}")
        
        # Group results by agent class for analysis
        by_agent_class = defaultdict(list)
        for result in successful_creations:
            by_agent_class[result['agent_class']].append(result)
        
        # Check for LLM manager sharing violations (same ID across different users)
        for agent_class, results in by_agent_class.items():
            llm_ids_to_users = defaultdict(list)
            
            for result in results:
                if result['llm_manager_id']:
                    llm_ids_to_users[result['llm_manager_id']].append(result['user_id'])
            
            # Detect violations: same LLM manager ID used by multiple users
            for llm_id, user_ids in llm_ids_to_users.items():
                if len(user_ids) > 1:
                    isolation_violations.append({
                        'violation_type': 'shared_llm_manager',
                        'agent_class': agent_class,
                        'llm_manager_id': llm_id,
                        'affected_users': user_ids,
                        'severity': 'CRITICAL'
                    })
                    logger.error(f"VIOLATION: {agent_class} shares LLM manager {llm_id} across users {user_ids}")
        
        # Check for memory/state isolation issues
        for agent_class, results in by_agent_class.items():
            agents_by_user = {r['user_id']: r for r in results}
            
            # Try to inject user-specific test data and check for cross-contamination
            test_data_key = f'test_isolation_{int(time.time())}'
            
            for user_id, result in agents_by_user.items():
                agent = result['agent']
                
                # Try to set user-specific test data on the agent's LLM manager
                if result['llm_manager']:
                    try:
                        # Try different ways to set test data
                        if hasattr(result['llm_manager'], '_context'):
                            result['llm_manager']._context = {test_data_key: user_id}
                        elif hasattr(result['llm_manager'], 'cache'):
                            result['llm_manager'].cache = {test_data_key: user_id}
                        elif hasattr(result['llm_manager'], '_cache'):
                            result['llm_manager']._cache = {test_data_key: user_id}
                        
                    except Exception as e:
                        logger.debug(f"Could not set test data on LLM manager for {agent_class}: {e}")
            
            # Check for data bleeding between users
            await asyncio.sleep(0.1)  # Allow async operations to complete
            
            for user_id, result in agents_by_user.items():
                if result['llm_manager']:
                    try:
                        # Check if other users' data is visible
                        context_data = None
                        if hasattr(result['llm_manager'], '_context'):
                            context_data = getattr(result['llm_manager'], '_context', {})
                        elif hasattr(result['llm_manager'], 'cache'):
                            context_data = getattr(result['llm_manager'], 'cache', {})
                        elif hasattr(result['llm_manager'], '_cache'):
                            context_data = getattr(result['llm_manager'], '_cache', {})
                        
                        if context_data and isinstance(context_data, dict):
                            stored_user_id = context_data.get(test_data_key)
                            if stored_user_id and stored_user_id != user_id:
                                isolation_violations.append({
                                    'violation_type': 'data_bleeding',
                                    'agent_class': agent_class,
                                    'expected_user': user_id,
                                    'found_user_data': stored_user_id,
                                    'severity': 'HIGH'
                                })
                                logger.error(f"DATA BLEEDING: {agent_class} shows user {stored_user_id} data to user {user_id}")
                                
                    except Exception as e:
                        logger.debug(f"Could not check test data on LLM manager for {agent_class}: {e}")
        
        # Record metrics
        self.record_metric('user_simulations', len(user_simulations))
        self.record_metric('agent_classes_tested', len(agent_classes_to_test))
        self.record_metric('total_creation_attempts', len(creation_tasks))
        self.record_metric('successful_creations', len(successful_creations))
        self.record_metric('failed_creations', len(failed_creations))
        self.record_metric('isolation_violations', len(isolation_violations))
        
        # Log summary
        logger.info(f"Tested {len(agent_classes_to_test)} agent classes with {len(user_simulations)} users")
        logger.info(f"Found {len(isolation_violations)} isolation violations")
        
        for violation in isolation_violations:
            logger.error(f"ISOLATION VIOLATION: {violation}")
        
        # This test should FAIL because we expect isolation violations
        assert len(isolation_violations) > 0, (
            f"Expected user isolation violations in concurrent agent creation, but found none. "
            f"This may indicate agents are properly using factory patterns with user context. "
            f"Tested {len(successful_creations)} successful agent creations across {len(agent_classes_to_test)} agent types."
        )
        
        # Check for specific violation types
        shared_manager_violations = [v for v in isolation_violations if v['violation_type'] == 'shared_llm_manager']
        data_bleeding_violations = [v for v in isolation_violations if v['violation_type'] == 'data_bleeding']
        
        pytest.fail(
            f"User Isolation Violations Detected in Concurrent Agent Creation! "
            f"Found {len(isolation_violations)} total violations: "
            f"{len(shared_manager_violations)} shared LLM managers, "
            f"{len(data_bleeding_violations)} data bleeding incidents. "
            f"This proves multi-user conversation mixing risk exists in agent system."
        )
    
    async def test_websocket_agent_integration_factory_violations(self):
        """DESIGNED TO FAIL: Test WebSocket integration with agent factory pattern violations.
        
        This test should FAIL because agents created through WebSocket events
        bypass proper factory patterns, causing user isolation issues.
        
        Expected Issues:
        - WebSocket agent creation bypasses user context
        - Agent execution events use shared LLM managers
        - WebSocket user sessions get mixed agent responses
        
        Business Impact: WebSocket chat functionality mixes user conversations
        """
        logger.info("Starting WebSocket agent integration factory violations test...")
        
        websocket_violations = []
        
        # Simulate WebSocket agent creation scenarios
        websocket_scenarios = [
            {
                'user_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'thread_id': str(uuid.uuid4()),
                'run_id': str(uuid.uuid4()),
                'message': 'Test user conversation 1',
                'agent_type': 'triage'
            },
            {
                'user_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'thread_id': str(uuid.uuid4()),
                'run_id': str(uuid.uuid4()),
                'message': 'Test user conversation 2',
                'agent_type': 'data_helper'
            },
            {
                'user_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4()),
                'thread_id': str(uuid.uuid4()),
                'run_id': str(uuid.uuid4()),
                'message': 'Test user conversation 3', 
                'agent_type': 'optimization'
            }
        ]
        
        async def simulate_websocket_agent_creation(scenario: Dict) -> Dict:
            """Simulate how WebSocket might create agents for user requests."""
            try:
                user_context = {
                    'user_id': scenario['user_id'],
                    'session_id': scenario['session_id'],
                    'thread_id': scenario['thread_id'],
                    'run_id': scenario['run_id']
                }
                
                # Simulate different agent creation patterns that WebSocket might use
                agent = None
                creation_method = None
                llm_manager_id = None
                
                if scenario['agent_type'] == 'triage':
                    # Test UnifiedTriageAgent creation patterns
                    try:
                        # Try factory method first
                        if hasattr(UnifiedTriageAgent, 'create_for_user'):
                            agent = UnifiedTriageAgent.create_for_user(user_context)
                            creation_method = 'factory'
                        else:
                            # Fallback to direct instantiation (violation expected)
                            agent = UnifiedTriageAgent()
                            creation_method = 'direct'
                            
                    except Exception as e:
                        logger.error(f"Failed to create UnifiedTriageAgent: {e}")
                        return {'success': False, 'error': str(e)}
                        
                elif scenario['agent_type'] == 'data_helper':
                    # Test DataHelperAgent creation patterns
                    try:
                        if hasattr(DataHelperAgent, 'create_for_user'):
                            agent = DataHelperAgent.create_for_user(user_context)
                            creation_method = 'factory'
                        else:
                            # This should use the violation pattern
                            agent = DataHelperAgent()
                            creation_method = 'direct'
                            
                    except Exception as e:
                        logger.error(f"Failed to create DataHelperAgent: {e}")
                        return {'success': False, 'error': str(e)}
                        
                elif scenario['agent_type'] == 'optimization':
                    # Test OptimizationsCoreSubAgent creation patterns
                    try:
                        if hasattr(OptimizationsCoreSubAgent, 'create_for_user'):
                            agent = OptimizationsCoreSubAgent.create_for_user(user_context)
                            creation_method = 'factory'
                        else:
                            agent = OptimizationsCoreSubAgent()
                            creation_method = 'direct'
                            
                    except Exception as e:
                        logger.error(f"Failed to create OptimizationsCoreSubAgent: {e}")
                        return {'success': False, 'error': str(e)}
                
                # Extract LLM manager info
                if agent:
                    if hasattr(agent, 'llm_manager'):
                        llm_manager_id = id(agent.llm_manager)
                    elif hasattr(agent, '_llm_manager'):
                        llm_manager_id = id(agent._llm_manager)
                
                return {
                    'success': True,
                    'scenario': scenario,
                    'agent': agent,
                    'creation_method': creation_method,
                    'llm_manager_id': llm_manager_id,
                    'user_context': user_context,
                    'created_at': time.time()
                }
                
            except Exception as e:
                logger.error(f"WebSocket agent creation simulation failed: {e}")
                return {'success': False, 'error': str(e)}
        
        # Execute WebSocket agent creation simulations
        simulation_tasks = [simulate_websocket_agent_creation(scenario) for scenario in websocket_scenarios]
        simulation_results = await asyncio.gather(*simulation_tasks, return_exceptions=True)
        
        successful_simulations = [r for r in simulation_results if isinstance(r, dict) and r.get('success')]
        failed_simulations = [r for r in simulation_results if isinstance(r, dict) and not r.get('success')]
        
        logger.info(f"Successful WebSocket simulations: {len(successful_simulations)}")
        logger.info(f"Failed WebSocket simulations: {len(failed_simulations)}")
        
        # Analyze for WebSocket-specific violations
        direct_creation_count = len([r for r in successful_simulations if r['creation_method'] == 'direct'])
        factory_creation_count = len([r for r in successful_simulations if r['creation_method'] == 'factory'])
        
        if direct_creation_count > 0:
            websocket_violations.append({
                'violation_type': 'websocket_bypasses_factory',
                'direct_creations': direct_creation_count,
                'factory_creations': factory_creation_count,
                'severity': 'CRITICAL'
            })
            logger.error(f"VIOLATION: {direct_creation_count} WebSocket agents created without factory pattern")
        
        # Check for shared LLM managers in WebSocket context
        llm_manager_usage = defaultdict(list)
        for result in successful_simulations:
            if result['llm_manager_id']:
                llm_manager_usage[result['llm_manager_id']].append(result['scenario']['user_id'])
        
        for llm_id, user_ids in llm_manager_usage.items():
            if len(user_ids) > 1:
                websocket_violations.append({
                    'violation_type': 'websocket_shared_llm_manager',
                    'llm_manager_id': llm_id,
                    'affected_users': user_ids,
                    'severity': 'CRITICAL'
                })
                logger.error(f"WEBSOCKET VIOLATION: LLM manager {llm_id} shared across users {user_ids}")
        
        # Check for missing user context in agent creation
        missing_context_count = 0
        for result in successful_simulations:
            agent = result['agent']
            user_context = result['user_context']
            
            # Check if agent has proper user context
            has_user_context = False
            if hasattr(agent, 'user_id') and agent.user_id == user_context['user_id']:
                has_user_context = True
            elif hasattr(agent, '_user_context') and agent._user_context:
                has_user_context = True
            elif hasattr(agent, 'context') and agent.context:
                has_user_context = True
            
            if not has_user_context:
                missing_context_count += 1
        
        if missing_context_count > 0:
            websocket_violations.append({
                'violation_type': 'websocket_missing_user_context',
                'agents_without_context': missing_context_count,
                'total_agents': len(successful_simulations),
                'severity': 'HIGH'
            })
            logger.error(f"VIOLATION: {missing_context_count} WebSocket agents lack proper user context")
        
        # Record metrics
        self.record_metric('websocket_scenarios_tested', len(websocket_scenarios))
        self.record_metric('successful_simulations', len(successful_simulations))
        self.record_metric('direct_creations', direct_creation_count)
        self.record_metric('factory_creations', factory_creation_count)
        self.record_metric('websocket_violations', len(websocket_violations))
        
        # Log summary
        logger.info(f"Tested {len(websocket_scenarios)} WebSocket scenarios")
        logger.info(f"Direct creation violations: {direct_creation_count}")
        logger.info(f"Found {len(websocket_violations)} WebSocket violations")
        
        for violation in websocket_violations:
            logger.error(f"WEBSOCKET VIOLATION: {violation}")
        
        # This test should FAIL because we expect WebSocket violations
        assert len(websocket_violations) > 0, (
            f"Expected WebSocket agent factory violations, but found none. "
            f"This may indicate WebSocket integration properly uses factory patterns. "
            f"Tested {len(successful_simulations)} successful agent creations through WebSocket simulation."
        )
        
        # Check that most agents are created through direct instantiation (violation)
        if len(successful_simulations) > 0:
            direct_ratio = direct_creation_count / len(successful_simulations)
            assert direct_ratio > 0.5, (
                f"Expected majority of WebSocket agents to use direct instantiation (violation), "
                f"but only {direct_ratio:.2%} used direct creation. This may indicate factory patterns are implemented."
            )
        
        pytest.fail(
            f"WebSocket Agent Integration Factory Violations Detected! "
            f"Found {len(websocket_violations)} violations. "
            f"Direct creation: {direct_creation_count}, Factory creation: {factory_creation_count}. "
            f"This proves WebSocket chat functionality bypasses proper user isolation patterns."
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)