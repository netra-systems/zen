# SSOT Orchestration Modules Usage Examples

This document provides examples for using the new SSOT (Single Source of Truth) orchestration configuration and enums modules.

## Overview

Two new modules have been created to consolidate orchestration availability checks and eliminate SSOT violations:

- `test_framework/ssot/orchestration.py` - Centralized availability configuration
- `test_framework/ssot/orchestration_enums.py` - Unified enums and data classes

## Migration from Old Patterns

### Before (SSOT Violation)
```python
# ❌ OLD WAY - Multiple availability definitions
# In unified_test_runner.py:
try:
    from test_framework.orchestration.test_orchestrator_agent import TestOrchestratorAgent
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# In background_e2e_agent.py:
try:
    from test_framework.orchestration.test_orchestrator_agent import AgentCommunicationMessage
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

# Duplicated enum definitions across files
class BackgroundTaskStatus(Enum):  # In background_e2e_agent.py
    QUEUED = "queued"
    # ... other values

class BackgroundTaskStatus(Enum):  # In background_e2e_manager.py  
    QUEUED = "queued"
    # ... same values duplicated
```

### After (SSOT Compliant)
```python
# ✅ NEW WAY - Single source of truth
from test_framework.ssot.orchestration import orchestration_config
from test_framework.ssot.orchestration_enums import BackgroundTaskStatus, E2ETestCategory

# Check availability
if orchestration_config.orchestrator_available:
    # Use orchestrator features
    pass

# Use consolidated enums
task = BackgroundTaskStatus.RUNNING
category = E2ETestCategory.CYPRESS
```

## Usage Examples

### 1. Basic Availability Checking

```python
from test_framework.ssot.orchestration import (
    orchestration_config,
    is_orchestrator_available,
    is_all_orchestration_available
)

# Method 1: Using the singleton instance
config = orchestration_config
if config.master_orchestration_available:
    print("Master orchestration is available")

# Method 2: Using convenience functions
if is_orchestrator_available():
    print("Test orchestrator is available")

# Check all features
if is_all_orchestration_available():
    print("All orchestration features available")
else:
    unavailable = config.get_unavailable_features()
    print(f"Missing features: {unavailable}")
```

### 2. Getting Detailed Status

```python
from test_framework.ssot.orchestration import get_orchestration_status

# Get comprehensive status
status = get_orchestration_status()
print(f"Available features: {status['available_features']}")
print(f"Import errors: {status['import_errors']}")

# Check for configuration issues
from test_framework.ssot.orchestration import validate_global_orchestration_config
issues = validate_global_orchestration_config()
if issues:
    print("Configuration issues found:")
    for issue in issues:
        print(f"  - {issue}")
```

### 3. Using Unified Enums

```python
from test_framework.ssot.orchestration_enums import (
    BackgroundTaskStatus,
    E2ETestCategory,
    ExecutionStrategy,
    ProgressOutputMode,
    OrchestrationMode
)

# Background task management
def process_task(task_id: str, category: E2ETestCategory):
    status = BackgroundTaskStatus.STARTING
    print(f"Task {task_id} ({category.value}): {status.value}")
    
    # Process task...
    status = BackgroundTaskStatus.RUNNING
    # ... more processing
    status = BackgroundTaskStatus.COMPLETED

# Layer execution strategy
strategy = ExecutionStrategy.PARALLEL_LIMITED
print(f"Using execution strategy: {strategy.value}")

# Progress output configuration
output_mode = ProgressOutputMode.WEBSOCKET
print(f"Progress will be streamed via: {output_mode.value}")
```

### 4. Working with Data Classes

```python
from test_framework.ssot.orchestration_enums import (
    BackgroundTaskConfig,
    BackgroundTaskResult,
    LayerDefinition,
    LayerType
)

# Create background task configuration
config = BackgroundTaskConfig(
    category=E2ETestCategory.CYPRESS,
    environment="development",
    use_real_services=True,
    timeout_minutes=45,
    max_retries=2
)

# Serialize for storage or transmission
config_dict = config.to_dict()
print(f"Task config: {config_dict}")

# Work with layer definitions
from test_framework.ssot.orchestration_enums import get_standard_layer

fast_feedback_layer = get_standard_layer(LayerType.FAST_FEEDBACK)
print(f"Fast feedback categories: {fast_feedback_layer.categories}")
print(f"Timeout: {fast_feedback_layer.timeout_minutes} minutes")
```

### 5. Custom Layer Creation

```python
from test_framework.ssot.orchestration_enums import (
    create_custom_layer,
    validate_layer_definition,
    ExecutionStrategy
)

# Create a custom test layer
custom_layer = create_custom_layer(
    name="security_focus",
    categories={"security", "authentication", "authorization"},
    execution_strategy=ExecutionStrategy.SEQUENTIAL,
    timeout_minutes=20,
    requires_real_services=True,
    service_dependencies={"postgres", "redis", "backend"}
)

# Validate the layer
issues = validate_layer_definition(custom_layer)
if not issues:
    print("Custom layer is valid")
    layer_dict = custom_layer.to_dict()
    # Use the layer...
else:
    print(f"Layer validation issues: {issues}")
```

### 6. Environment Override Configuration

```python
# Set environment variables to override availability
import os
os.environ["ORCHESTRATION_ORCHESTRATOR_AVAILABLE"] = "false"
os.environ["ORCHESTRATION_MASTER_ORCHESTRATION_AVAILABLE"] = "true"

# Refresh configuration to pick up changes
from test_framework.ssot.orchestration import refresh_global_orchestration_config
refresh_global_orchestration_config(force=True)

# Check status with overrides
from test_framework.ssot.orchestration import get_orchestration_status
status = get_orchestration_status()
print(f"Environment overrides: {status['environment_overrides']}")
```

### 7. Integration with Existing Code

```python
# Replace old availability checks in unified_test_runner.py
from test_framework.ssot.orchestration import orchestration_config

def main(args):
    # OLD: if ORCHESTRATOR_AVAILABLE:
    # NEW:
    if orchestration_config.orchestrator_available:
        # Add orchestrator arguments
        pass
    
    # OLD: if MASTER_ORCHESTRATION_AVAILABLE:
    # NEW:
    if orchestration_config.master_orchestration_available:
        # Execute with master orchestration
        pass
    
    # OLD: if BACKGROUND_E2E_AVAILABLE:
    # NEW:
    if orchestration_config.background_e2e_available:
        # Handle background E2E commands
        pass
```

### 8. Progress Event Streaming

```python
from test_framework.ssot.orchestration_enums import (
    ProgressEvent,
    ProgressEventType,
    ProgressOutputMode
)
from datetime import datetime

# Create progress events
event = ProgressEvent(
    event_type=ProgressEventType.LAYER_STARTED,
    timestamp=datetime.now(),
    layer_name="fast_feedback",
    message="Starting fast feedback layer execution",
    data={"categories": ["smoke", "unit"], "timeout": 300}
)

# Serialize for streaming
event_dict = event.to_dict()
print(f"Event: {event_dict}")

# Stream via different modes
if orchestration_config.master_orchestration_available:
    # Stream via WebSocket, JSON, console, etc.
    output_mode = ProgressOutputMode.WEBSOCKET
    # Use the event with the streaming system...
```

## Best Practices

### 1. Always Use SSOT Modules
- Import availability checks from `test_framework.ssot.orchestration`
- Import enums from `test_framework.ssot.orchestration_enums`
- Never create duplicate availability constants

### 2. Handle Unavailable Features Gracefully
```python
from test_framework.ssot.orchestration import orchestration_config

if orchestration_config.background_e2e_available:
    # Use background E2E features
    pass
else:
    # Fall back to alternative or skip
    print("Background E2E not available, using legacy mode")
```

### 3. Validate Configuration Early
```python
from test_framework.ssot.orchestration import validate_global_orchestration_config

# At application startup
issues = validate_global_orchestration_config()
if issues:
    for issue in issues:
        logger.warning(f"Orchestration config issue: {issue}")
```

### 4. Use Type Hints
```python
from test_framework.ssot.orchestration_enums import (
    BackgroundTaskStatus,
    E2ETestCategory,
    ExecutionStrategy
)

def execute_background_task(
    category: E2ETestCategory,
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
) -> BackgroundTaskStatus:
    # Implementation with proper type safety
    return BackgroundTaskStatus.COMPLETED
```

## Migration Checklist

When migrating existing code to use SSOT modules:

- [ ] Replace availability constants with `orchestration_config` properties
- [ ] Import enums from `test_framework.ssot.orchestration_enums`
- [ ] Remove duplicate enum/constant definitions
- [ ] Update import statements throughout codebase
- [ ] Test that all orchestration functionality still works
- [ ] Update documentation and examples

## Compatibility

The SSOT modules are designed to be fully compatible with existing orchestration code. They provide the same availability information and enum values, just from a centralized location.

All existing orchestration functionality should continue to work without changes to business logic - only import statements need to be updated.