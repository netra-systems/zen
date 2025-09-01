"""
Agent Heartbeat System for Lifecycle Monitoring
================================================
Provides heartbeat mechanism for agents to signal they're alive during execution.
"""

import asyncio
import time
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from netra_backend.app.core.execution_tracker import get_execution_tracker
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentHeartbeat:
    """
    Heartbeat context manager for agent executions.
    
    Usage:
        async with AgentHeartbeat(exec_id, agent_name) as heartbeat:
            # Do work...
            await heartbeat.pulse()  # Send manual heartbeat
            # More work...
    """
    
    def __init__(
        self,
        exec_id: UUID,
        agent_name: str,
        interval: float = 5.0,
        websocket_callback: Optional[Callable] = None
    ):
        self.exec_id = exec_id
        self.agent_name = agent_name
        self.interval = interval
        self.websocket_callback = websocket_callback
        self.tracker = get_execution_tracker()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        self._pulse_count = 0
        
    async def __aenter__(self):
        """Start heartbeat on context entry."""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop heartbeat on context exit."""
        await self.stop()
        
    async def start(self):
        """Start the heartbeat loop."""
        if self._running:
            return
            
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug(f"Started heartbeat for {self.agent_name} (exec_id={self.exec_id})")
        
    async def stop(self):
        """Stop the heartbeat loop."""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            
        logger.debug(f"Stopped heartbeat for {self.agent_name} (exec_id={self.exec_id}), pulses={self._pulse_count}")
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._running:
            try:
                await self.pulse()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                
    async def pulse(self, data: Optional[Dict[str, Any]] = None):
        """Send a single heartbeat pulse."""
        try:
            # Update execution tracker
            success = await self.tracker.heartbeat(self.exec_id)
            
            if success:
                self._pulse_count += 1
                
                # Send WebSocket update if callback provided
                if self.websocket_callback:
                    try:
                        await self.websocket_callback({
                            "type": "agent_heartbeat",
                            "data": {
                                "agent": self.agent_name,
                                "exec_id": str(self.exec_id),
                                "pulse": self._pulse_count,
                                "timestamp": time.time(),
                                **(data or {})
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error sending WebSocket heartbeat: {e}")
                        
            return success
            
        except Exception as e:
            logger.error(f"Error sending heartbeat pulse: {e}")
            return False


class HeartbeatManager:
    """
    Manages heartbeats for multiple agent executions.
    """
    
    def __init__(self):
        self.heartbeats: Dict[UUID, AgentHeartbeat] = {}
        
    async def create_heartbeat(
        self,
        exec_id: UUID,
        agent_name: str,
        interval: float = 5.0,
        websocket_callback: Optional[Callable] = None
    ) -> AgentHeartbeat:
        """Create and start a new heartbeat."""
        if exec_id in self.heartbeats:
            logger.warning(f"Heartbeat already exists for exec_id={exec_id}")
            return self.heartbeats[exec_id]
            
        heartbeat = AgentHeartbeat(exec_id, agent_name, interval, websocket_callback)
        self.heartbeats[exec_id] = heartbeat
        await heartbeat.start()
        
        return heartbeat
        
    async def stop_heartbeat(self, exec_id: UUID):
        """Stop and remove a heartbeat."""
        if exec_id in self.heartbeats:
            await self.heartbeats[exec_id].stop()
            del self.heartbeats[exec_id]
            
    async def stop_all(self):
        """Stop all heartbeats."""
        for heartbeat in list(self.heartbeats.values()):
            await heartbeat.stop()
        self.heartbeats.clear()
        
    def get_heartbeat(self, exec_id: UUID) -> Optional[AgentHeartbeat]:
        """Get heartbeat by execution ID."""
        return self.heartbeats.get(exec_id)


# Global heartbeat manager
_heartbeat_manager: Optional[HeartbeatManager] = None


def get_heartbeat_manager() -> HeartbeatManager:
    """Get or create the global heartbeat manager."""
    global _heartbeat_manager
    if _heartbeat_manager is None:
        _heartbeat_manager = HeartbeatManager()
    return _heartbeat_manager