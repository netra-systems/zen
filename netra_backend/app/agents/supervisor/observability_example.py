"""Example usage of supervisor flow observability system.

Demonstrates how to use the supervisor observability features for tracking
TODO lists and flow states. This file serves as documentation and examples.
"""
from netra_backend.app.observability_helpers import (
    set_global_flow_logger, 
    log_todo_added, log_todo_started, log_todo_completed, log_todo_failed,
    log_flow_started, log_step_started, log_step_completed, log_decision_made
)
from netra_backend.app.flow_logger import SupervisorPipelineLogger


def example_direct_usage():
    """Example of direct usage with SupervisorPipelineLogger instance."""
    # Create logger instance
    logger = SupervisorPipelineLogger('correlation-123', 'run-456')
    
    # Track TODO items
    logger.log_todo_added('task-1', 'Initialize database', 'high', ['task-0'])
    logger.log_todo_started('task-1')
    logger.log_todo_completed('task-1')
    
    # Track flow progression
    logger.log_flow_started('flow-1', 3)
    logger.log_step_started('flow-1', 'validation', 'agent')
    logger.log_step_completed('flow-1', 'validation', 1.5)


def example_global_helper_usage():
    """Example using global helper functions."""
    # Initialize global logger
    set_global_flow_logger('correlation-456', 'run-789')
    
    # Use convenience functions
    log_todo_added('task-2', 'Process data', 'medium')
    log_todo_started('task-2')
    
    log_flow_started('flow-2', 5)
    log_step_started('flow-2', 'data_processing', 'parallel')
    log_decision_made('flow-2', 'retry_operation', 'Temporary service failure')
    
    log_step_completed('flow-2', 'data_processing', 3.2)
    log_todo_completed('task-2')


def example_error_handling():
    """Example of error handling and failure logging."""
    set_global_flow_logger('correlation-789', 'run-123')
    
    log_todo_added('task-3', 'External API call', 'low')
    log_todo_started('task-3')
    log_todo_failed('task-3', 'API timeout after 30 seconds')


if __name__ == "__main__":
    """Run all examples."""
    print("Running supervisor observability examples...")
    example_direct_usage()
    example_global_helper_usage()
    example_error_handling()
    print("All examples completed successfully!")