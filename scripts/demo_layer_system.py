#!/usr/bin/env python3
"""
Layer System Demonstration
Shows how to use the layered test execution system
"""

import sys
import json
from pathlib import Path
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.layer_system import LayerSystem


def demonstrate_layer_system():
    """Demonstrate the layer system capabilities"""
    print("[U+1F680] Netra Apex Layered Test System Demonstration")
    print("=" * 60)
    
    # Initialize layer system
    project_root = Path(__file__).parent.parent
    layer_system = LayerSystem(project_root)
    
    print(f"[U+1F4C1] Project root: {project_root}")
    print(f"[U+2699][U+FE0F]  Configuration: {layer_system.config_path}")
    print()
    
    # Show system summary
    print(" CHART:  System Summary:")
    summary = layer_system.get_system_summary()
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for sub_key, sub_value in value.items():
                print(f"    {sub_key}: {sub_value}")
        else:
            print(f"  {key}: {value}")
    print()
    
    # Show available layers
    print("[U+1F5C2][U+FE0F]  Available Layers:")
    for i, (layer_name, layer) in enumerate(layer_system.layers.items(), 1):
        print(f"  {i}. {layer.name} ({layer_name})")
        print(f"     Priority: {layer.priority}, Order: {layer.execution_order}")
        mode_value = layer.execution_mode.value if hasattr(layer.execution_mode, 'value') else layer.execution_mode
        print(f"     Duration: {layer.max_duration_minutes}min, Mode: {mode_value}")
        print(f"     Categories: {[cat.name for cat in layer.categories]}")
        if layer.dependencies:
            print(f"     Dependencies: {list(layer.dependencies)}")
        if layer.required_services:
            print(f"     Services: {list(layer.required_services)}")
        print()
    
    # Create execution plan
    print("[U+1F4CB] Creating Execution Plan...")
    selected_layers = ["fast_feedback", "core_integration", "service_integration"]
    plan = layer_system.create_execution_plan(selected_layers, "dev")
    
    print(f"Selected layers: {selected_layers}")
    print(f"Execution sequence: {plan.execution_sequence}")
    print(f"Total estimated duration: {plan.total_estimated_duration}")
    print(f"Service startup order: {plan.service_startup_order}")
    print()
    
    # Show detailed execution plan
    print("[U+1F4DD] Detailed Execution Plan:")
    for phase_num, phase_layers in enumerate(plan.execution_sequence, 1):
        print(f"  Phase {phase_num}: {len(phase_layers)} layer(s)")
        for layer_name in phase_layers:
            layer = layer_system.layers[layer_name]
            print(f"    - {layer.name}")
            print(f"      Duration: {layer.max_duration_minutes}min")
            mode_value = layer.execution_mode.value if hasattr(layer.execution_mode, 'value') else layer.execution_mode
            print(f"      Mode: {mode_value}")
            print(f"      Categories: {len(layer.categories)}")
            print(f"      Resources: {layer.resource_limits.max_memory_mb}MB RAM, {layer.resource_limits.max_cpu_percent}% CPU")
    print()
    
    # Demonstrate category mapping
    print(" SEARCH:  Category-to-Layer Mapping:")
    all_categories = set()
    for layer_name, layer in layer_system.layers.items():
        for category in layer.categories:
            all_categories.add(category.name)
            print(f"  {category.name:15}  ->  {layer.name} (Layer {layer.execution_order})")
    print()
    
    # Show configuration validation
    print(" PASS:  Configuration Validation:")
    issues = layer_system.validate_configuration()
    if not issues:
        print("  Configuration is valid! [U+2713]")
    else:
        print("  Issues found:")
        for issue in issues:
            print(f"    - {issue}")
    print()
    
    # Export execution plan
    output_path = project_root / "test_reports" / "demo_execution_plan.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    layer_system.export_execution_plan(plan, output_path)
    print(f"[U+1F4C4] Execution plan exported to: {output_path}")
    print()
    
    # Show usage examples
    print(" IDEA:  Usage Examples:")
    print("  # Run with layered execution (development)")
    print("  python unified_test_runner.py --use-layers --env dev")
    print()
    print("  # Run specific layers")
    print("  python unified_test_runner.py --use-layers --layers fast_feedback core_integration")
    print()
    print("  # Show available layers")
    print("  python unified_test_runner.py --show-layers")
    print()
    print("  # Validate configuration")
    print("  python scripts/validate_layer_config.py")
    print()
    
    return layer_system, plan


def show_timing_analysis(layer_system: LayerSystem, plan):
    """Show timing analysis and optimization suggestions"""
    print("[U+23F1][U+FE0F]  Timing Analysis:")
    print("=" * 60)
    
    # Sequential vs parallel timing
    total_sequential = sum(layer.max_duration_minutes for layer in plan.layers)
    total_parallel = plan.total_estimated_duration.total_seconds() / 60
    
    print(f"Sequential execution: {total_sequential:.1f} minutes")
    print(f"Parallel execution:   {total_parallel:.1f} minutes")
    print(f"Time savings:         {total_sequential - total_parallel:.1f} minutes ({((total_sequential - total_parallel) / total_sequential * 100):.1f}%)")
    print()
    
    # Per-layer timing
    print("Layer Timing Breakdown:")
    for phase_num, phase_layers in enumerate(plan.execution_sequence, 1):
        phase_duration = max(layer_system.layers[name].max_duration_minutes for name in phase_layers)
        print(f"  Phase {phase_num}: {phase_duration:.1f}min")
        for layer_name in phase_layers:
            layer = layer_system.layers[layer_name]
            print(f"    {layer.name}: {layer.max_duration_minutes:.1f}min")
    print()
    
    # Resource utilization
    print("Resource Utilization:")
    max_memory = max(layer.resource_limits.max_memory_mb for layer in plan.layers)
    max_cpu = max(layer.resource_limits.max_cpu_percent for layer in plan.layers)
    total_instances = sum(layer.resource_limits.max_parallel_instances for layer in plan.layers)
    
    print(f"  Peak memory usage: {max_memory}MB")
    print(f"  Peak CPU usage:    {max_cpu}%")
    print(f"  Total instances:   {total_instances}")
    print()


def show_migration_strategy():
    """Show migration strategy from current system"""
    print(" CYCLE:  Migration Strategy:")
    print("=" * 60)
    
    current_categories = [
        "smoke", "unit", "integration", "database", "api", 
        "websocket", "agent", "frontend", "e2e_critical", 
        "cypress", "e2e", "performance"
    ]
    
    print("Current category system  ->  Layered system mapping:")
    print()
    
    category_to_layer = {
        'smoke': ('fast_feedback', 1, '< 2min'),
        'unit': ('fast_feedback', 1, '< 2min'),
        'database': ('core_integration', 2, '< 10min'),
        'api': ('core_integration', 2, '< 10min'),
        'websocket': ('core_integration', 2, '< 10min'),
        'integration': ('core_integration', 2, '< 10min'),
        'agent': ('service_integration', 3, '< 20min'),
        'e2e_critical': ('service_integration', 3, '< 20min'),
        'frontend': ('service_integration', 3, '< 20min'),
        'cypress': ('e2e_performance', 4, 'background'),
        'e2e': ('e2e_performance', 4, 'background'),
        'performance': ('e2e_performance', 4, 'background')
    }
    
    for category in current_categories:
        if category in category_to_layer:
            layer, order, timing = category_to_layer[category]
            print(f"  {category:15}  ->  Layer {order}: {layer:20} ({timing})")
    
    print()
    print("Migration steps:")
    print("  1. Enable layered execution with --use-layers flag")
    print("  2. Test layered execution in development environment")
    print("  3. Update CI/CD pipelines to use layered system")
    print("  4. Gradually migrate team workflows")
    print("  5. Remove legacy execution path")
    print()


def main():
    """Main demonstration function"""
    try:
        # Main demonstration
        layer_system, plan = demonstrate_layer_system()
        
        # Timing analysis
        show_timing_analysis(layer_system, plan)
        
        # Migration strategy
        show_migration_strategy()
        
        print("[U+2728] Layered Test System Demonstration Complete!")
        print("   Ready to revolutionize test execution timing and dependencies! [U+1F680]")
        
    except Exception as e:
        print(f" FAIL:  Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()