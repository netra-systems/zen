"""
Startup Validation Fix - Ensure proper agent WebSocket initialization.

This module provides fixes for common startup validation failures,
particularly around agent WebSocket bridge initialization issues.
"""

import logging
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class StartupValidationFixer:
    """Helper class to fix common startup validation issues."""
    
    @staticmethod
    def fix_agent_websocket_initialization(app_state) -> Dict[str, Any]:
        """Fix agent WebSocket initialization issues.
        
        Args:
            app_state: The FastAPI app.state object
            
        Returns:
            Dictionary with fix results
        """
        results = {
            'agents_fixed': [],
            'agents_skipped': [],
            'errors': [],
            'success': True
        }
        
        try:
            # Check if agent supervisor exists
            if not hasattr(app_state, 'agent_supervisor') or not app_state.agent_supervisor:
                results['errors'].append("Agent supervisor not found")
                results['success'] = False
                return results
            
            # Check if supervisor has registry
            supervisor = app_state.agent_supervisor
            if not hasattr(supervisor, 'registry') or not supervisor.registry:
                results['errors'].append("Agent registry not found in supervisor")
                results['success'] = False
                return results
            
            registry = supervisor.registry
            
            # Check if WebSocket bridge is available
            websocket_bridge = getattr(app_state, 'agent_websocket_bridge', None)
            if not websocket_bridge:
                results['errors'].append("AgentWebSocketBridge not found")
                results['success'] = False
                return results
            
            # Fix agents that don't have proper WebSocket initialization
            for agent_name, agent in registry.agents.items():
                try:
                    # Check if agent needs WebSocket initialization
                    needs_fix = False
                    
                    # Check for missing set_websocket_bridge method
                    if not hasattr(agent, 'set_websocket_bridge'):
                        # Check if this is a BaseAgent that should have the method
                        if hasattr(agent, '__class__'):
                            from netra_backend.app.agents.base_agent import BaseAgent
                            if BaseAgent in agent.__class__.__mro__:
                                # This should have WebSocket methods but doesn't
                                needs_fix = True
                                logger.warning(f"Agent {agent_name} inherits from BaseAgent but missing WebSocket methods")
                    
                    # Check for missing WebSocket adapter
                    if hasattr(agent, '_websocket_adapter') and agent._websocket_adapter is None:
                        needs_fix = True
                        logger.warning(f"Agent {agent_name} has None WebSocket adapter")
                    
                    if needs_fix:
                        # Try to fix the agent
                        if StartupValidationFixer._fix_individual_agent(agent, agent_name, websocket_bridge):
                            results['agents_fixed'].append(agent_name)
                        else:
                            results['agents_skipped'].append(agent_name)
                    else:
                        results['agents_skipped'].append(agent_name)
                        
                except Exception as e:
                    error_msg = f"Failed to fix agent {agent_name}: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
            
            logger.info(f"Agent WebSocket fix results: {len(results['agents_fixed'])} fixed, "
                       f"{len(results['agents_skipped'])} skipped, {len(results['errors'])} errors")
            
        except Exception as e:
            results['errors'].append(f"Critical error in agent WebSocket fix: {e}")
            results['success'] = False
            logger.error(f"Critical error in agent WebSocket fix: {e}")
        
        return results
    
    @staticmethod
    def _fix_individual_agent(agent, agent_name: str, websocket_bridge) -> bool:
        """Fix an individual agent's WebSocket initialization.
        
        Args:
            agent: The agent instance
            agent_name: Name of the agent
            websocket_bridge: WebSocket bridge to set
            
        Returns:
            True if agent was fixed, False otherwise
        """
        try:
            # Try to initialize WebSocket adapter if missing
            if hasattr(agent, '_websocket_adapter') and agent._websocket_adapter is None:
                try:
                    from netra_backend.app.agents.base.websocket_adapter import WebSocketEventAdapter
                    agent._websocket_adapter = WebSocketEventAdapter()
                    logger.info(f"Initialized WebSocket adapter for agent {agent_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize WebSocket adapter for {agent_name}: {e}")
                    return False
            
            # Try to set WebSocket bridge
            if hasattr(agent, 'set_websocket_bridge'):
                try:
                    agent.set_websocket_bridge(websocket_bridge, None)
                    logger.info(f"Set WebSocket bridge for agent {agent_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to set WebSocket bridge for {agent_name}: {e}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to fix agent {agent_name}: {e}")
            return False


def apply_startup_validation_fixes(app) -> Dict[str, Any]:
    """Apply startup validation fixes to the app.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Dictionary with fix results
    """
    logger.info("Applying startup validation fixes...")
    
    all_results = {
        'websocket_fix': None,
        'overall_success': True,
        'total_fixes_applied': 0
    }
    
    try:
        # Fix agent WebSocket initialization
        websocket_results = StartupValidationFixer.fix_agent_websocket_initialization(app.state)
        all_results['websocket_fix'] = websocket_results
        
        if not websocket_results['success']:
            all_results['overall_success'] = False
        else:
            all_results['total_fixes_applied'] += len(websocket_results['agents_fixed'])
        
        if all_results['overall_success']:
            logger.info(f"✅ Startup validation fixes applied successfully - {all_results['total_fixes_applied']} fixes")
        else:
            logger.warning("⚠️ Some startup validation fixes failed - check detailed results")
    
    except Exception as e:
        logger.error(f"Critical error applying startup validation fixes: {e}")
        all_results['overall_success'] = False
        all_results['critical_error'] = str(e)
    
    return all_results