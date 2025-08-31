"""Periodic Update Manager for Long-Running Operations

This module provides automatic periodic updates for operations that take longer than 5 seconds,
ensuring users never experience silent periods during agent execution.

Business Value: Prevents user abandonment during long operations, improving retention.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Dict, Optional, Set

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
    from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PeriodicUpdateManager:
    """Manages periodic updates for long-running agent operations.
    
    Automatically sends contextual updates for operations that exceed 5 seconds,
    providing users with meaningful progress information and preventing the
    perception of system unresponsiveness.
    """
    
    def __init__(self, websocket_notifier: 'WebSocketNotifier'):
        self.websocket_notifier = websocket_notifier
        self.active_operations: Dict[str, Dict] = {}
        self.update_tasks: Dict[str, asyncio.Task] = {}
        self._shutdown = False
    
    @asynccontextmanager
    async def track_operation(self, context: 'AgentExecutionContext', 
                             operation_name: str, operation_type: str = None,
                             expected_duration_ms: int = None,
                             operation_description: str = None):
        """Context manager for tracking long-running operations with automatic updates.
        
        Args:
            context: Execution context for WebSocket routing
            operation_name: Name of the operation (e.g., "data_analysis", "report_generation")
            operation_type: Type category (e.g., "database_query", "llm_generation")
            expected_duration_ms: Expected duration in milliseconds
            operation_description: User-friendly description
        """
        operation_id = f"{context.run_id}_{operation_name}"
        start_time = time.time()
        
        # Send initial thinking event instead of operation_started (which isn't valid)
        await self.websocket_notifier.send_agent_thinking(
            context, 
            f"Starting {operation_description or operation_name}...",
            step_number=0
        )
        
        # Store operation metadata
        self.active_operations[operation_id] = {
            "context": context,
            "operation_name": operation_name,
            "operation_type": operation_type,
            "start_time": start_time,
            "expected_duration_ms": expected_duration_ms,
            "operation_description": operation_description,
            "last_update_time": start_time,
            "update_count": 0
        }
        
        # Start periodic updates if expected to be long-running
        if not expected_duration_ms or expected_duration_ms > 5000:
            self.update_tasks[operation_id] = asyncio.create_task(
                self._periodic_update_loop(operation_id)
            )
        
        try:
            yield
        finally:
            # Cleanup and send completion
            await self._complete_operation(operation_id)
    
    async def _periodic_update_loop(self, operation_id: str):
        """Send periodic updates for a long-running operation."""
        try:
            while operation_id in self.active_operations and not self._shutdown:
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
                if operation_id not in self.active_operations:
                    break
                
                await self._send_periodic_update(operation_id)
                
        except asyncio.CancelledError:
            logger.debug(f"Periodic updates cancelled for operation {operation_id}")
        except Exception as e:
            logger.error(f"Error in periodic update loop for {operation_id}: {e}")
    
    async def _send_periodic_update(self, operation_id: str):
        """Send a single periodic update for an operation."""
        if operation_id not in self.active_operations:
            return
            
        op_data = self.active_operations[operation_id]
        current_time = time.time()
        elapsed_ms = (current_time - op_data["start_time"]) * 1000
        
        # Calculate progress if we have expected duration
        progress_percentage = None
        estimated_remaining_ms = None
        
        if op_data.get("expected_duration_ms"):
            progress_percentage = min(95, (elapsed_ms / op_data["expected_duration_ms"]) * 100)
            estimated_remaining_ms = max(1000, op_data["expected_duration_ms"] - elapsed_ms)
        
        # Generate contextual status message based on operation type and elapsed time
        status_message = self._generate_status_message(
            op_data["operation_name"], 
            op_data.get("operation_type"),
            elapsed_ms,
            op_data["update_count"]
        )
        
        # Send periodic update as agent_thinking event
        await self.websocket_notifier.send_agent_thinking(
            op_data["context"],
            status_message,
            step_number=op_data['update_count'] + 1,
            progress_percentage=progress_percentage
        )
        
        # Update tracking
        op_data["last_update_time"] = current_time
        op_data["update_count"] += 1
    
    def _generate_status_message(self, operation_name: str, operation_type: str,
                               elapsed_ms: float, update_count: int) -> str:
        """Generate contextual status message based on operation details."""
        elapsed_seconds = int(elapsed_ms / 1000)
        
        # Base messages for different operation types
        type_messages = {
            "database_query": [
                f"Querying database... ({elapsed_seconds}s)",
                f"Processing large dataset... ({elapsed_seconds}s)",
                f"Optimizing query performance... ({elapsed_seconds}s)"
            ],
            "llm_generation": [
                f"Generating AI response... ({elapsed_seconds}s)",
                f"Processing complex reasoning... ({elapsed_seconds}s)",
                f"Finalizing response quality... ({elapsed_seconds}s)"
            ],
            "data_processing": [
                f"Analyzing data patterns... ({elapsed_seconds}s)",
                f"Processing {operation_name} calculations... ({elapsed_seconds}s)",
                f"Generating insights... ({elapsed_seconds}s)"
            ],
            "file_operation": [
                f"Processing file operation... ({elapsed_seconds}s)",
                f"Handling large file... ({elapsed_seconds}s)",
                f"Finalizing file processing... ({elapsed_seconds}s)"
            ]
        }
        
        # Get appropriate message set
        messages = type_messages.get(operation_type, [
            f"Processing {operation_name}... ({elapsed_seconds}s)",
            f"Working on complex operation... ({elapsed_seconds}s)",
            f"Finalizing results... ({elapsed_seconds}s)"
        ])
        
        # Cycle through messages to show progress
        message_index = update_count % len(messages)
        return messages[message_index]
    
    async def _complete_operation(self, operation_id: str):
        """Complete an operation and send final event."""
        if operation_id not in self.active_operations:
            return
            
        op_data = self.active_operations[operation_id]
        end_time = time.time()
        duration_ms = (end_time - op_data["start_time"]) * 1000
        
        # Cancel periodic updates
        if operation_id in self.update_tasks:
            self.update_tasks[operation_id].cancel()
            try:
                await self.update_tasks[operation_id]
            except asyncio.CancelledError:
                pass
            del self.update_tasks[operation_id]
        
        # Generate result summary
        result_summary = self._generate_completion_summary(
            op_data["operation_name"], duration_ms, op_data["update_count"]
        )
        
        # Send completion as final report event
        await self.websocket_notifier.send_final_report(
            op_data["context"],
            {
                "operation_name": op_data["operation_name"],
                "result_summary": result_summary,
                "total_updates_sent": op_data["update_count"],
                "duration_category": self._get_duration_category(duration_ms)
            },
            duration_ms
        )
        
        # Cleanup
        del self.active_operations[operation_id]
    
    def _generate_completion_summary(self, operation_name: str, 
                                   duration_ms: float, update_count: int) -> str:
        """Generate a completion summary for the operation."""
        duration_seconds = int(duration_ms / 1000)
        
        if duration_seconds < 10:
            return f"Completed {operation_name} quickly"
        elif duration_seconds < 30:
            return f"Completed {operation_name} in {duration_seconds} seconds"
        elif duration_seconds < 60:
            return f"Completed complex {operation_name} in {duration_seconds} seconds"
        else:
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            return f"Completed intensive {operation_name} in {minutes}m {seconds}s"
    
    def _get_duration_category(self, duration_ms: float) -> str:
        """Categorize operation duration for metrics."""
        if duration_ms < 5000:
            return "fast"
        elif duration_ms < 15000:
            return "medium"
        elif duration_ms < 60000:
            return "slow"
        else:
            return "very_slow"
    
    async def force_update(self, context: 'AgentExecutionContext', 
                          operation_name: str, status_message: str,
                          progress_percentage: float = None):
        """Force an immediate update for an operation (useful for key milestones)."""
        operation_id = f"{context.run_id}_{operation_name}"
        
        if operation_id in self.active_operations:
            op_data = self.active_operations[operation_id]
            current_time = time.time()
            elapsed_ms = (current_time - op_data["start_time"]) * 1000
            
            estimated_remaining_ms = None
            if op_data.get("expected_duration_ms"):
                estimated_remaining_ms = max(1000, op_data["expected_duration_ms"] - elapsed_ms)
            
            await self.websocket_notifier.send_agent_thinking(
                context, 
                status_message,
                step_number=-1,  # Special step for forced updates
                progress_percentage=progress_percentage
            )
            
            op_data["last_update_time"] = current_time
            op_data["update_count"] += 1
    
    async def shutdown(self):
        """Shutdown the update manager and cancel all tasks."""
        self._shutdown = True
        
        # Cancel all update tasks
        for task in self.update_tasks.values():
            task.cancel()
        
        # Wait for tasks to complete
        if self.update_tasks:
            await asyncio.gather(*self.update_tasks.values(), return_exceptions=True)
        
        # Clear state
        self.active_operations.clear()
        self.update_tasks.clear()
    
    def get_active_operations(self) -> Set[str]:
        """Get set of currently active operation IDs."""
        return set(self.active_operations.keys())
    
    def get_operation_status(self, context: 'AgentExecutionContext', 
                           operation_name: str) -> Optional[Dict]:
        """Get status of a specific operation."""
        operation_id = f"{context.run_id}_{operation_name}"
        return self.active_operations.get(operation_id)