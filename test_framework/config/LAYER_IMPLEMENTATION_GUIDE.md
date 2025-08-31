# Layered Test Execution System - Implementation Guide

## Overview

The Layered Test Execution System provides a comprehensive solution to eliminate timing confusion and dependency issues in the Netra Apex test suite. This system organizes tests into 4 logical layers with clear execution order, resource management, and dependency resolution.

## System Architecture

### Layer Structure

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4: E2E & Performance (Background, < 60 min)         │
│ ├─ cypress (1800s, 1 instance)                            │
│ ├─ e2e (1800s, 1 instance)                                │
│ └─ performance (1800s, 1 instance)                        │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: Service Integration (Parallel/Hybrid, < 20 min)   │
│ ├─ agent (600s, 2 instances)                              │
│ ├─ e2e_critical (300s, 2 instances)                       │
│ └─ frontend (300s, 3 instances)                           │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: Core Integration (Parallel, < 10 min)            │
│ ├─ database (300s, 2 instances)                           │
│ ├─ api (300s, 3 instances)                                │
│ ├─ websocket (300s, 2 instances)                          │
│ └─ integration (600s, 2 instances)                        │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: Fast Feedback (Sequential, < 2 min)              │
│ ├─ smoke (60s, 2 instances)                               │
│ └─ unit (120s, 4 instances)                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Benefits

1. **Predictable Timing**: Each layer has clear duration limits and execution modes
2. **Dependency Management**: Layers execute in dependency order with conflict resolution
3. **Resource Management**: Memory, CPU, and service resource allocation per layer
4. **Background Execution**: Long-running tests don't block development workflow
5. **Environment Flexibility**: Different configurations for dev, CI, and staging

## Integration Steps

### Step 1: Update Test Runner Integration

Modify `unified_test_runner.py` to support layered execution:

```python
# Add import
from test_framework.layer_system import LayerSystem, LayerExecutionMode

class UnifiedTestRunner:
    def __init__(self):
        # ... existing init ...
        
        # Add layer system
        self.layer_system = LayerSystem(self.project_root)
        self.use_layered_execution = False  # Feature flag
    
    def run(self, args: argparse.Namespace) -> int:
        # Check if layered execution is requested
        if hasattr(args, 'use_layers') and args.use_layers:
            return self._run_layered_execution(args)
        else:
            return self._run_legacy_execution(args)  # Current implementation
    
    def _run_layered_execution(self, args: argparse.Namespace) -> int:
        """Run tests using the layered execution system"""
        
        # Create execution plan
        selected_layers = self._determine_layers_from_categories(args.categories or [])
        plan = self.layer_system.create_execution_plan(selected_layers, args.env)
        
        # Show execution plan
        self._show_layered_execution_plan(plan, args)
        
        # Execute layers in sequence
        results = {}
        for phase in plan.execution_sequence:
            phase_results = self._execute_layer_phase(phase, args)
            results.update(phase_results)
            
            # Check for fail-fast conditions
            if self._should_stop_execution(phase_results, args):
                break
        
        # Generate layered report
        self._generate_layered_report(results, plan, args)
        
        return 0 if all(r["success"] for r in results.values()) else 1
```

### Step 2: Add Command Line Arguments

Add new arguments to support layered execution:

```python
# In main() function, add these arguments:
parser.add_argument(
    "--use-layers",
    action="store_true", 
    help="Use layered test execution system"
)

parser.add_argument(
    "--layers",
    nargs='+',
    help="Run specific layers (e.g., '--layers fast_feedback core_integration')"
)

parser.add_argument(
    "--show-layers",
    action="store_true",
    help="Show available layers and their configuration"
)

parser.add_argument(
    "--layer-config",
    help="Path to custom layer configuration file"
)
```

### Step 3: Layer-to-Category Mapping

Create mapping functions to maintain compatibility:

```python
def _determine_layers_from_categories(self, categories: List[str]) -> List[str]:
    """Map selected categories to appropriate layers"""
    category_to_layer = {
        'smoke': 'fast_feedback',
        'unit': 'fast_feedback', 
        'database': 'core_integration',
        'api': 'core_integration',
        'websocket': 'core_integration',
        'integration': 'core_integration',
        'agent': 'service_integration',
        'e2e_critical': 'service_integration',
        'frontend': 'service_integration',
        'cypress': 'e2e_performance',
        'e2e': 'e2e_performance',
        'performance': 'e2e_performance'
    }
    
    if not categories:
        # Default to first 3 layers for development
        return ['fast_feedback', 'core_integration', 'service_integration']
    
    selected_layers = set()
    for category in categories:
        layer = category_to_layer.get(category)
        if layer:
            selected_layers.add(layer)
    
    return list(selected_layers)
```

### Step 4: Service Management Integration

Integrate with existing service management:

```python
def _ensure_layer_services(self, layer_name: str, args: argparse.Namespace):
    """Ensure required services are running for a layer"""
    layer = self.layer_system.layers.get(layer_name)
    if not layer:
        return
    
    required_services = layer.required_services
    if not required_services:
        return
    
    # Use existing service availability checking
    self._check_service_availability_for_services(list(required_services), args)
    
    # Start missing services if possible
    if hasattr(self, 'port_discovery'):
        missing_services = self._get_missing_services(required_services)
        if missing_services:
            success, started = self.port_discovery.start_missing_services(missing_services)
            if success:
                print(f"[INFO] Started services for layer {layer_name}: {started}")
```

### Step 5: Progress Tracking Updates

Update progress tracking for layered execution:

```python
def _execute_layer_phase(self, phase_layers: List[str], args: argparse.Namespace) -> Dict:
    """Execute a phase of layers"""
    results = {}
    
    for layer_name in phase_layers:
        print(f"\n{'='*60}")
        print(f"EXECUTING LAYER: {layer_name.upper()}")
        print(f"{'='*60}")
        
        # Start layer timing
        start_time = time.time()
        
        # Ensure services are available
        self._ensure_layer_services(layer_name, args)
        
        # Get categories for this layer
        categories = self.layer_system.get_layer_categories(layer_name)
        
        # Execute categories within the layer
        layer_results = {}
        for category_name in categories:
            category_result = self._execute_single_category(category_name, args)
            layer_results[category_name] = category_result
        
        # Calculate layer result
        layer_success = all(r["success"] for r in layer_results.values())
        layer_duration = time.time() - start_time
        
        results[layer_name] = {
            "success": layer_success,
            "duration": layer_duration,
            "categories": layer_results
        }
        
        print(f"Layer {layer_name} completed: {'SUCCESS' if layer_success else 'FAILED'} ({layer_duration:.1f}s)")
    
    return results
```

## Configuration Management

### Environment-Specific Configurations

Create environment-specific override files:

#### `test_framework/config/environments/dev.yaml`
```yaml
layer_overrides:
  fast_feedback:
    max_duration_minutes: 3
    execution_mode: "parallel"
  e2e_performance:
    background_execution: true
    skip_performance_tests: true
```

#### `test_framework/config/environments/ci.yaml`
```yaml
layer_overrides:
  fast_feedback:
    max_duration_minutes: 1
    max_parallel_instances: 4
  core_integration:
    max_duration_minutes: 8
  e2e_performance:
    background_execution: true
    max_duration_minutes: 30
```

### Custom Layer Configurations

Users can create custom layer configurations:

```yaml
# custom_layers.yaml
layers:
  quick_validation:
    name: "Quick Validation"
    description: "Ultra-fast validation for pre-commit"
    priority: 1
    execution_order: 1
    max_duration_minutes: 1
    execution_mode: "parallel"
    categories:
      - name: "smoke"
        timeout_seconds: 30
        filters:
          include_patterns: ["**/test_smoke_*.py"]
```

## Usage Examples

### Basic Layered Execution
```bash
# Run with layered execution (default layers)
python unified_test_runner.py --use-layers

# Run specific layers
python unified_test_runner.py --use-layers --layers fast_feedback core_integration

# Show available layers
python unified_test_runner.py --show-layers
```

### Environment-Specific Execution
```bash
# Development environment (optimized for speed)
python unified_test_runner.py --use-layers --env dev

# CI environment (comprehensive but time-limited)
python unified_test_runner.py --use-layers --env ci --layers fast_feedback core_integration service_integration

# Staging environment (full validation)
python unified_test_runner.py --use-layers --env staging
```

### Background Execution
```bash
# Run with background E2E tests
python unified_test_runner.py --use-layers --background-e2e

# Check background test status
python scripts/check_background_tests.py
```

## Migration Strategy

### Phase 1: Parallel Implementation (Week 1)
1. Implement `LayerSystem` class ✅
2. Create default layer configurations ✅
3. Add command line arguments
4. Implement basic layer-to-category mapping

### Phase 2: Integration (Week 2)
1. Update `unified_test_runner.py` with layered execution
2. Integrate service management
3. Update progress tracking
4. Add environment-specific configurations

### Phase 3: Testing & Refinement (Week 3)
1. Test layered execution in development
2. Refine timing and resource limits
3. Add comprehensive error handling
4. Create documentation and examples

### Phase 4: Rollout (Week 4)
1. Enable layered execution in CI
2. Train team on new system
3. Migrate existing workflows
4. Monitor performance and adjust

## Backward Compatibility

The system maintains full backward compatibility:

- Existing `--category` and `--categories` arguments continue to work
- Legacy execution path remains unchanged by default
- Gradual migration with feature flags
- All existing test configurations preserved

## Monitoring and Metrics

### Key Metrics to Track
- **Layer execution times** vs. estimates
- **Resource utilization** per layer
- **Success rates** by layer and environment
- **Background execution** completion rates
- **Service startup times** and reliability

### Reporting Enhancements
- Layer-specific test reports
- Resource usage analysis
- Dependency relationship visualization
- Timing analysis and optimization suggestions

## Troubleshooting

### Common Issues

1. **Layer Dependencies Not Met**
   - Check `test_layers.yaml` for correct dependency configuration
   - Verify all prerequisite services are available

2. **Resource Conflicts**
   - Review `resource_limits` in layer configuration
   - Check global resource limits in `execution_config`

3. **Service Startup Failures**
   - Verify `service_dependencies` configuration
   - Check Docker/service availability
   - Review startup timeout settings

4. **Background Execution Issues**
   - Ensure background layers are properly configured
   - Check system resources for background processes
   - Monitor background execution logs

### Debug Commands
```bash
# Validate layer configuration
python -c "from test_framework.layer_system import LayerSystem; ls = LayerSystem('.'); print(ls.validate_configuration())"

# Show execution plan without running tests
python unified_test_runner.py --show-layers --layers fast_feedback core_integration

# Test service dependencies
python scripts/test_service_dependencies.py --layer core_integration
```

## Future Enhancements

1. **Dynamic Layer Scaling**: Adjust layer resources based on system load
2. **Smart Dependency Detection**: Automatic dependency discovery from test code
3. **Predictive Timing**: ML-based duration estimation and optimization
4. **Cross-Environment Sync**: Synchronized layer execution across environments
5. **Visual Layer Management**: Web UI for layer configuration and monitoring

This layered system provides a robust foundation for scalable, predictable test execution that grows with the Netra Apex platform while maintaining developer productivity and system reliability.