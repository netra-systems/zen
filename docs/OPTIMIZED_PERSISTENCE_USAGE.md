# BatchedStatePersistence System Usage

This document describes how to use the newly implemented BatchedStatePersistence system for optimized agent state persistence.

## Overview

The BatchedStatePersistence system provides intelligent state persistence optimization through:
- **Deduplication**: Skips saving identical state data
- **Selective Persistence**: Uses optimized persistence for non-critical checkpoints
- **Fallback Safety**: Always falls back to standard persistence on error
- **Configurable Options**: Feature flags and tuning parameters

## Quick Start

### Enable Optimized Persistence

Set the environment variable to enable the feature:

```bash
export ENABLE_OPTIMIZED_PERSISTENCE=true
```

Or in your `.env` file:

```
ENABLE_OPTIMIZED_PERSISTENCE=true
```

### Disable Optimized Persistence (Default)

For safety, optimized persistence is disabled by default:

```bash
export ENABLE_OPTIMIZED_PERSISTENCE=false
```

## Configuration Options

The system supports several configuration options through environment variables:

```bash
# Main feature toggle (default: false for safety)
ENABLE_OPTIMIZED_PERSISTENCE=true

# Cache size for state deduplication (default: 1000)
OPTIMIZED_PERSISTENCE_CACHE_SIZE=1000

# Enable/disable deduplication (default: true)
OPTIMIZED_PERSISTENCE_DEDUPLICATION=true

# Enable/disable compression optimizations (default: true)
OPTIMIZED_PERSISTENCE_COMPRESSION=true
```

## Usage Examples

### Basic Usage (No Code Changes Required)

The optimized persistence system is integrated into the existing pipeline executor. No code changes are required:

```python
# Your existing code continues to work unchanged
from netra_backend.app.agents.supervisor.pipeline_executor import PipelineExecutor

# Pipeline executor automatically uses optimized persistence when enabled
executor = PipelineExecutor(engine, websocket_manager, db_session)

# All existing state persistence calls are automatically optimized
await executor.execute_pipeline(pipeline, state, run_id, context)
```

### Direct Usage of Optimized Service

If you need direct access to the optimized service:

```python
# SSOT CONSOLIDATION: Optimized features are now integrated into the main service
from netra_backend.app.services.state_persistence import state_persistence_service
# Enable optimizations
state_persistence_service.configure(enable_optimizations=True)
from netra_backend.app.schemas.agent_state import StatePersistenceRequest, CheckpointType, AgentPhase

# Create persistence request
request = StatePersistenceRequest(
    run_id="my-run-123",
    user_id="user-456",
    thread_id="thread-789",
    state_data={"key": "value", "status": "processing"},
    checkpoint_type=CheckpointType.AUTO,
    agent_phase=AgentPhase.DATA_ANALYSIS
)

# Save state with optimization
success, snapshot_id = await state_persistence_service.save_agent_state(request, db_session)
```

### Dynamic Configuration

You can configure the optimized service at runtime:

```python
# SSOT CONSOLIDATION: Optimized features are now integrated into the main service
from netra_backend.app.services.state_persistence import state_persistence_service
# Enable optimizations
state_persistence_service.configure(enable_optimizations=True)

# Configure optimization settings
state_persistence_service.configure(
    enable_deduplication=True,
    enable_compression=True,
    cache_max_size=500
)

# Get cache statistics
stats = state_persistence_service.get_cache_stats()
print(f"Cache size: {stats['cache_size']}")
print(f"Deduplication enabled: {stats['deduplication_enabled']}")
```

## How It Works

### 1. Feature Flag Check

The system first checks if optimized persistence is enabled via environment variable.

### 2. Optimization Decision

For each save operation, the system decides whether to apply optimizations:

- **Critical checkpoints** (MANUAL, RECOVERY) → Always use standard persistence
- **Recovery points** → Always use standard persistence
- **Non-critical checkpoints** (AUTO, INTERMEDIATE) → Use optimized persistence

### 3. Deduplication

For optimizable saves, the system:
1. Calculates a hash of the state data
2. Checks if identical data was recently persisted
3. Skips persistence if duplicate is detected
4. Updates cache with new state hash if persisting

### 4. Fallback Safety

If any error occurs during optimization:
- System automatically falls back to standard persistence
- Logs the error for monitoring
- Ensures no data loss

## Monitoring

### Cache Statistics

Get real-time cache statistics:

```python
# SSOT CONSOLIDATION: Optimized features are now integrated into the main service
from netra_backend.app.services.state_persistence import state_persistence_service
# Enable optimizations
state_persistence_service.configure(enable_optimizations=True)

stats = state_persistence_service.get_cache_stats()
print(f"""
Cache Statistics:
- Size: {stats['cache_size']}/{stats['cache_max_size']}
- Deduplication: {stats['deduplication_enabled']}
- Compression: {stats['compression_enabled']}
- Entries: {len(stats['cache_entries'])}
""")
```

### Clear Cache

For testing or troubleshooting:

```python
state_persistence_service.clear_cache()
```

## Performance Benefits

With optimized persistence enabled, you can expect:

### Reduced Database Load
- Eliminates redundant writes for duplicate states
- Reduces database connection pool pressure
- Lower storage requirements over time

### Improved Response Times
- Skipped saves complete in microseconds vs milliseconds
- Reduced serialization overhead for duplicate data
- Less database round-trip latency

### Better Resource Utilization
- Lower CPU usage from reduced JSON serialization
- Less memory pressure from avoided database operations
- Improved overall system throughput

## Safety Mechanisms

### 1. Disabled by Default
Optimized persistence is disabled by default to ensure system stability.

### 2. Critical Path Protection
Critical checkpoints and recovery points always use standard persistence.

### 3. Automatic Fallback
Any optimization error results in immediate fallback to standard persistence.

### 4. Backward Compatibility
All existing APIs continue to work without modification.

### 5. Full Interface Compatibility
The optimized service implements the complete standard service interface.

## Best Practices

### 1. Enable in Non-Production First
Test the feature in development/staging environments before production deployment.

### 2. Monitor Cache Hit Rates
Track cache statistics to understand optimization effectiveness.

### 3. Tune Cache Size
Adjust `OPTIMIZED_PERSISTENCE_CACHE_SIZE` based on your agent execution patterns.

### 4. Use Critical Checkpoints Appropriately
Mark important state saves as MANUAL or set `is_recovery_point=True` to bypass optimization.

### 5. Monitor Logs
Watch for fallback messages to identify potential optimization issues.

## Troubleshooting

### Problem: Optimized persistence not being used
**Solution**: Check that `ENABLE_OPTIMIZED_PERSISTENCE=true` is set in environment

### Problem: Too many duplicate skips
**Solution**: Reduce cache size or disable deduplication temporarily

### Problem: Memory usage concerns
**Solution**: Lower `OPTIMIZED_PERSISTENCE_CACHE_SIZE` value

### Problem: Performance not improved
**Solution**: Check if most saves are critical checkpoints (which bypass optimization)

## Implementation Details

The system is implemented as:

1. **OptimizedStatePersistence** class in `netra_backend/app/services/state_persistence_optimized.py`
2. **Feature flag integration** in `netra_backend/app/agents/supervisor/pipeline_executor.py`
3. **Environment configuration** in `netra_backend/app/core/isolated_environment.py`
4. **Comprehensive tests** in `netra_backend/tests/services/`

The implementation follows SSOT principles with a single canonical optimization service that wraps the standard persistence service for safe fallback behavior.