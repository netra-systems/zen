"""
Example showing how to integrate agent monitoring with existing agents.
This demonstrates the usage patterns for the new monitoring system.
"""

import asyncio
from typing import Any, Dict
from datetime import datetime

from app.agents.base import BaseSubAgent
from app.agents.state import DeepAgentState
from app.middleware.metrics_middleware import (
    track_operation, track_with_timeout, track_execution,
    AgentMetricsContextManager, agent_metrics_middleware
)
from app.services.metrics.agent_metrics import FailureType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MonitoredExampleAgent(BaseSubAgent):
    """Example agent with comprehensive monitoring integration."""
    
    def __init__(self):
        super().__init__(name="MonitoredExampleAgent", description="Example with monitoring")
        self.enable_monitoring = True
    
    @track_execution  # Automatically track execution metrics
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:
        """Execute agent with automatic monitoring."""
        logger.info(f"Starting execution for run_id: {run_id}")
        
        # Perform agent work
        await self._perform_analysis(state)
        await self._generate_response(state)
        await self._validate_output(state)
    
    @track_operation(operation_type="analysis", include_performance=True)
    async def _perform_analysis(self, state: DeepAgentState) -> Dict[str, Any]:
        """Perform analysis with performance tracking."""
        # Simulate analysis work
        await asyncio.sleep(0.5)  # Simulate processing time
        
        analysis_result = {
            "insights": ["insight1", "insight2"],
            "confidence": 0.85,
            "processed_items": 42
        }
        
        logger.debug("Analysis completed successfully")
        return analysis_result
    
    @track_with_timeout(timeout=10.0)  # 10 second timeout
    async def _generate_response(self, state: DeepAgentState) -> str:
        """Generate response with timeout monitoring."""
        # Simulate response generation
        await asyncio.sleep(1.0)
        
        response = "Generated response based on analysis"
        logger.debug("Response generation completed")
        return response
    
    @track_operation(operation_type="validation")
    async def _validate_output(self, state: DeepAgentState) -> bool:
        """Validate output with error tracking."""
        # Simulate validation logic
        if not hasattr(state, 'processed_data'):
            raise ValueError("Missing required processed_data in state")
        
        # Simulate validation checks
        is_valid = True
        logger.debug("Output validation completed")
        return is_valid
    
    async def perform_batch_operation(self, items: list) -> Dict[str, Any]:
        """Example of batch operation monitoring."""
        return await agent_metrics_middleware.track_batch_operation(
            agent_name=self.name,
            operation_type="batch_processing",
            batch_size=len(items),
            operation_func=self._process_batch_items,
            items=items
        )
    
    async def _process_batch_items(self, items: list) -> Dict[str, Any]:
        """Process batch items."""
        successful = 0
        failed = 0
        
        for item in items:
            try:
                # Simulate item processing
                await asyncio.sleep(0.1)
                successful += 1
            except Exception:
                failed += 1
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(items)
        }
    
    async def example_with_context_manager(self) -> None:
        """Example using context manager for operation tracking."""
        async with AgentMetricsContextManager(
            agent_name=self.name,
            operation_type="context_example"
        ) as ctx:
            # Perform operation
            await asyncio.sleep(0.3)
            logger.debug("Context manager operation completed")


class LegacyAgentAdapter:
    """Adapter to add monitoring to existing agents without modification."""
    
    def __init__(self, original_agent):
        self.original_agent = original_agent
        self.name = getattr(original_agent, 'name', 'LegacyAgent')
    
    async def execute_with_monitoring(self, *args, **kwargs):
        """Execute original agent with monitoring wrapper."""
        async with AgentMetricsContextManager(
            agent_name=self.name,
            operation_type="legacy_execution"
        ):
            return await self.original_agent.execute(*args, **kwargs)


async def monitoring_integration_demo():
    """Demonstrate monitoring integration patterns."""
    logger.info("Starting monitoring integration demo")
    
    # Create monitored agent
    agent = MonitoredExampleAgent()
    
    # Demo 1: Basic execution with automatic monitoring
    state = DeepAgentState()
    state.processed_data = {"sample": "data"}
    
    try:
        await agent.execute(state, "demo_run_1", stream_updates=False)
        logger.info("Demo 1: Basic execution completed successfully")
    except Exception as e:
        logger.error(f"Demo 1 failed: {e}")
    
    # Demo 2: Batch operation monitoring
    try:
        batch_items = [f"item_{i}" for i in range(10)]
        batch_result = await agent.perform_batch_operation(batch_items)
        logger.info(f"Demo 2: Batch operation completed: {batch_result}")
    except Exception as e:
        logger.error(f"Demo 2 failed: {e}")
    
    # Demo 3: Context manager usage
    try:
        await agent.example_with_context_manager()
        logger.info("Demo 3: Context manager usage completed")
    except Exception as e:
        logger.error(f"Demo 3 failed: {e}")
    
    # Demo 4: Error scenarios for testing monitoring
    try:
        # This will trigger a timeout
        @track_with_timeout(timeout=0.1)
        async def timeout_demo():
            await asyncio.sleep(0.5)  # Will timeout
        
        await timeout_demo()
    except asyncio.TimeoutError:
        logger.info("Demo 4: Timeout monitoring working correctly")
    
    logger.info("Monitoring integration demo completed")


async def get_monitoring_status():
    """Get current monitoring system status."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    from app.monitoring.alert_manager import alert_manager
    from app.core.system_health_monitor_enhanced import enhanced_system_health_monitor
    
    # Get system overview
    system_overview = await agent_metrics_collector.get_system_overview()
    
    # Get alert summary
    alert_summary = alert_manager.get_alert_summary()
    
    # Get comprehensive health report
    health_report = await enhanced_system_health_monitor.get_comprehensive_health_report()
    
    return {
        "metrics_overview": system_overview,
        "alert_status": alert_summary,
        "health_summary": {
            "components": health_report.get("system_health", {}),
            "agent_health": health_report.get("agent_health", {})
        }
    }


# Example of how to start monitoring for the entire system
async def initialize_system_monitoring():
    """Initialize comprehensive system monitoring."""
    from app.monitoring.alert_manager import alert_manager
    from app.core.system_health_monitor_enhanced import enhanced_system_health_monitor
    
    logger.info("Initializing system monitoring...")
    
    # Start alert manager
    await alert_manager.start_monitoring()
    
    # Start enhanced health monitoring
    await enhanced_system_health_monitor.start_monitoring()
    
    logger.info("System monitoring initialized successfully")


# Example of how to stop monitoring gracefully
async def shutdown_system_monitoring():
    """Shutdown system monitoring gracefully."""
    from app.monitoring.alert_manager import alert_manager
    from app.core.system_health_monitor_enhanced import enhanced_system_health_monitor
    
    logger.info("Shutting down system monitoring...")
    
    # Stop monitoring services
    await alert_manager.stop_monitoring()
    await enhanced_system_health_monitor.stop_monitoring()
    
    logger.info("System monitoring shutdown completed")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(monitoring_integration_demo())