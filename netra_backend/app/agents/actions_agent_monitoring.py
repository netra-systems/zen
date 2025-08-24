"""Monitoring service for ActionsToMeetGoalsSubAgent following SRP."""

from netra_backend.app.agents.base.interface import ExecutionContext


class ActionsAgentMonitoringService:
    """Handles status updates and monitoring for the Actions agent."""

    async def send_status_update(
        self, context: ExecutionContext, 
        status: str, message: str
    ) -> None:
        """Send status update via WebSocket."""
        if context.stream_updates:
            await self._process_and_send_status_update(
                context.run_id, status, message
            )

    async def send_execution_start_update(self, context: ExecutionContext) -> None:
        """Send execution start update."""
        await self.send_status_update(
            context, "executing", 
            "Creating action plan based on optimization strategies..."
        )

    async def send_completion_update(self, context: ExecutionContext) -> None:
        """Send completion update."""
        await self.send_status_update(
            context, "completed",
            "Action plan created successfully"
        )

    async def _process_and_send_status_update(
        self, run_id: str, status: str, message: str
    ) -> None:
        """Process and send status update."""
        mapped_status = self._map_status_to_websocket_format(status)
        await self._send_mapped_update(run_id, mapped_status, message)

    def _map_status_to_websocket_format(self, status: str) -> str:
        """Map internal status to websocket format."""
        status_map = {
            "executing": "processing",
            "completed": "processed",
            "failed": "error"
        }
        return status_map.get(status, status)

    async def _send_mapped_update(self, run_id: str, status: str, message: str) -> None:
        """Send the mapped status update."""
        await self._send_update(run_id, {
            "status": status,
            "message": message
        })

    async def _send_update(self, run_id: str, update_data: dict) -> None:
        """Send update via WebSocket - placeholder for actual implementation."""
        # This would connect to the actual WebSocket service
        # For now, it's a placeholder that needs to be connected to the real service
        pass

    def get_health_status(self) -> dict:
        """Get monitoring service health status."""
        return {
            "service": "monitoring",
            "status": "healthy"
        }