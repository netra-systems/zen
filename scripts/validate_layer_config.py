#!/usr/bin/env python3
"""
Layer Configuration Validator
Validates the test layer configuration against the schema and business rules
"""

import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass
import argparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_framework.layer_system import LayerSystem


@dataclass
class ValidationResult:
    """Result of configuration validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class LayerConfigValidator:
    """Comprehensive validator for layer configurations"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_path = project_root / "test_framework" / "config" / "test_layers.yaml"
        self.schema_path = project_root / "test_framework" / "config" / "layer_schema.yaml"
        self.errors = []
        self.warnings = []
        self.suggestions = []
    
    def validate_all(self) -> ValidationResult:
        """Run comprehensive validation"""
        print(" SEARCH:  Starting layer configuration validation...")
        
        # Load configurations
        if not self._load_configurations():
            return ValidationResult(False, self.errors, self.warnings, self.suggestions)
        
        # Run validation checks
        self._validate_schema_compliance()
        self._validate_business_rules()
        self._validate_dependencies()
        self._validate_resource_allocation()
        self._validate_timing_constraints()
        self._validate_service_requirements()
        self._validate_environment_consistency()
        
        # Generate suggestions
        self._generate_suggestions()
        
        is_valid = len(self.errors) == 0
        return ValidationResult(is_valid, self.errors, self.warnings, self.suggestions)
    
    def _load_configurations(self) -> bool:
        """Load and parse configuration files"""
        try:
            # Load layer configuration
            if not self.config_path.exists():
                self.errors.append(f"Layer configuration file not found: {self.config_path}")
                return False
            
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
            
            # Load schema if available
            self.schema = None
            if self.schema_path.exists():
                with open(self.schema_path) as f:
                    self.schema = yaml.safe_load(f)
            
            # Initialize layer system for additional validation
            self.layer_system = LayerSystem(self.project_root, self.config_path)
            
            print(" PASS:  Configuration files loaded successfully")
            return True
            
        except Exception as e:
            self.errors.append(f"Failed to load configuration: {e}")
            return False
    
    def _validate_schema_compliance(self):
        """Validate configuration against schema"""
        if not self.schema:
            self.warnings.append("Schema file not found, skipping schema validation")
            return
        
        print("[U+1F4CB] Validating schema compliance...")
        
        # Basic structure validation
        required_root_sections = ['metadata', 'layers', 'execution_config']
        for section in required_root_sections:
            if section not in self.config:
                self.errors.append(f"Missing required root section: {section}")
        
        # Validate layers section
        if 'layers' in self.config:
            layers = self.config['layers']
            if not isinstance(layers, dict):
                self.errors.append("'layers' section must be a dictionary")
            else:
                for layer_name, layer_config in layers.items():
                    self._validate_layer_schema(layer_name, layer_config)
        
        # Validate execution_config section
        if 'execution_config' in self.config:
            self._validate_execution_config_schema(self.config['execution_config'])
    
    def _validate_layer_schema(self, layer_name: str, layer_config: Dict[str, Any]):
        """Validate individual layer configuration"""
        required_fields = ['name', 'description', 'priority', 'execution_order', 
                          'max_duration_minutes', 'execution_mode', 'categories']
        
        for field in required_fields:
            if field not in layer_config:
                self.errors.append(f"Layer '{layer_name}' missing required field: {field}")
        
        # Validate field types and values
        if 'priority' in layer_config:
            priority = layer_config['priority']
            if not isinstance(priority, int) or not (1 <= priority <= 5):
                self.errors.append(f"Layer '{layer_name}' priority must be integer 1-5")
        
        if 'execution_order' in layer_config:
            order = layer_config['execution_order']
            if not isinstance(order, int) or order < 1:
                self.errors.append(f"Layer '{layer_name}' execution_order must be positive integer")
        
        if 'max_duration_minutes' in layer_config:
            duration = layer_config['max_duration_minutes']
            if not isinstance(duration, (int, float)) or duration <= 0:
                self.errors.append(f"Layer '{layer_name}' max_duration_minutes must be positive")
        
        if 'execution_mode' in layer_config:
            mode = layer_config['execution_mode']
            valid_modes = ['sequential', 'parallel', 'hybrid']
            if mode not in valid_modes:
                self.errors.append(f"Layer '{layer_name}' invalid execution_mode: {mode}")
        
        # Validate categories
        if 'categories' in layer_config:
            categories = layer_config['categories']
            if not isinstance(categories, list):
                self.errors.append(f"Layer '{layer_name}' categories must be a list")
            else:
                for i, category in enumerate(categories):
                    self._validate_category_schema(layer_name, i, category)
    
    def _validate_category_schema(self, layer_name: str, index: int, category: Dict[str, Any]):
        """Validate category configuration within layer"""
        required_fields = ['name', 'timeout_seconds', 'max_parallel_instances', 'priority_order']
        
        for field in required_fields:
            if field not in category:
                self.errors.append(f"Layer '{layer_name}' category {index} missing required field: {field}")
        
        if 'timeout_seconds' in category:
            timeout = category['timeout_seconds']
            if not isinstance(timeout, int) or timeout <= 0:
                self.errors.append(f"Layer '{layer_name}' category {index} timeout_seconds must be positive integer")
    
    def _validate_execution_config_schema(self, exec_config: Dict[str, Any]):
        """Validate global execution configuration"""
        required_fields = ['layer_execution_mode', 'global_timeout_minutes', 'max_global_parallel_tests']
        
        for field in required_fields:
            if field not in exec_config:
                self.errors.append(f"execution_config missing required field: {field}")
        
        if 'global_timeout_minutes' in exec_config:
            timeout = exec_config['global_timeout_minutes']
            if not isinstance(timeout, int) or timeout <= 0:
                self.errors.append("global_timeout_minutes must be positive integer")
        
        if 'max_global_parallel_tests' in exec_config:
            max_tests = exec_config['max_global_parallel_tests']
            if not isinstance(max_tests, int) or max_tests <= 0:
                self.errors.append("max_global_parallel_tests must be positive integer")
    
    def _validate_business_rules(self):
        """Validate business logic rules"""
        print("[U+1F527] Validating business rules...")
        
        # Check layer naming conventions
        layers = self.config.get('layers', {})
        for layer_name in layers.keys():
            if not layer_name.replace('_', '').isalnum():
                self.warnings.append(f"Layer name '{layer_name}' should contain only letters, numbers, and underscores")
        
        # Check execution order uniqueness
        execution_orders = []
        for layer_name, layer_config in layers.items():
            order = layer_config.get('execution_order')
            if order in execution_orders:
                self.errors.append(f"Duplicate execution_order {order} found (layer: {layer_name})")
            execution_orders.append(order)
        
        # Check priority distribution
        priorities = [layer.get('priority', 0) for layer in layers.values()]
        if priorities and max(priorities) - min(priorities) > 3:
            self.warnings.append("Large priority range may affect execution order optimization")
    
    def _validate_dependencies(self):
        """Validate layer dependencies and conflicts"""
        print("[U+1F517] Validating dependencies and conflicts...")
        
        layers = self.config.get('layers', {})
        layer_names = set(layers.keys())
        
        # Check dependency references
        for layer_name, layer_config in layers.items():
            dependencies = layer_config.get('dependencies', [])
            for dep in dependencies:
                if dep not in layer_names:
                    self.errors.append(f"Layer '{layer_name}' depends on non-existent layer: {dep}")
            
            conflicts = layer_config.get('conflicts', [])
            for conflict in conflicts:
                if conflict not in layer_names:
                    self.errors.append(f"Layer '{layer_name}' conflicts with non-existent layer: {conflict}")
        
        # Check for circular dependencies
        try:
            # Use layer system to detect cycles
            issues = self.layer_system.validate_configuration()
            for issue in issues:
                if "circular" in issue.lower() or "dependency" in issue.lower():
                    self.errors.append(issue)
                else:
                    self.warnings.append(issue)
        except Exception as e:
            self.errors.append(f"Dependency validation failed: {e}")
    
    def _validate_resource_allocation(self):
        """Validate resource limits and allocation"""
        print("[U+1F4BE] Validating resource allocation...")
        
        layers = self.config.get('layers', {})
        exec_config = self.config.get('execution_config', {})
        
        global_memory = exec_config.get('max_memory_usage_mb', 6144)
        global_cpu = exec_config.get('max_cpu_usage_percent', 90)
        
        total_layer_memory = 0
        total_layer_cpu = 0
        
        for layer_name, layer_config in layers.items():
            resource_limits = layer_config.get('resource_limits', {})
            
            layer_memory = resource_limits.get('max_memory_mb', 0)
            layer_cpu = resource_limits.get('max_cpu_percent', 0)
            
            total_layer_memory += layer_memory
            total_layer_cpu = max(total_layer_cpu, layer_cpu)  # Parallel execution
            
            # Check reasonable limits
            if layer_memory > global_memory:
                self.errors.append(f"Layer '{layer_name}' memory limit exceeds global limit")
            
            if layer_cpu > global_cpu:
                self.errors.append(f"Layer '{layer_name}' CPU limit exceeds global limit")
        
        # Check total allocation (assuming some parallel execution)
        if total_layer_memory > global_memory * 1.2:  # Allow some overhead
            self.warnings.append("Total layer memory allocation may exceed global limits during parallel execution")
    
    def _validate_timing_constraints(self):
        """Validate timing and duration constraints"""
        print("[U+23F1][U+FE0F]  Validating timing constraints...")
        
        layers = self.config.get('layers', {})
        exec_config = self.config.get('execution_config', {})
        
        global_timeout = exec_config.get('global_timeout_minutes', 90)
        total_sequential_time = 0
        
        for layer_name, layer_config in layers.items():
            layer_duration = layer_config.get('max_duration_minutes', 0)
            total_sequential_time += layer_duration
            
            # Check if layer duration is reasonable
            if layer_duration > global_timeout * 0.8:
                self.warnings.append(f"Layer '{layer_name}' duration ({layer_duration}m) is close to global timeout ({global_timeout}m)")
            
            # Check category timeouts within layer
            categories = layer_config.get('categories', [])
            for category in categories:
                category_timeout = category.get('timeout_seconds', 0)
                layer_timeout_seconds = layer_duration * 60
                
                if category_timeout > layer_timeout_seconds:
                    self.warnings.append(f"Category '{category.get('name')}' timeout exceeds layer '{layer_name}' duration")
        
        if total_sequential_time > global_timeout:
            self.errors.append(f"Total sequential execution time ({total_sequential_time}m) exceeds global timeout ({global_timeout}m)")
    
    def _validate_service_requirements(self):
        """Validate service requirements and dependencies"""
        print("[U+1F50C] Validating service requirements...")
        
        layers = self.config.get('layers', {})
        service_deps = self.config.get('service_dependencies', {})
        
        all_required_services = set()
        
        for layer_name, layer_config in layers.items():
            required_services = layer_config.get('required_services', [])
            all_required_services.update(required_services)
            
            # Check if required services are defined
            for service in required_services:
                if service not in service_deps:
                    self.warnings.append(f"Layer '{layer_name}' requires undefined service: {service}")
        
        # Check service dependency chains
        for service_name, service_config in service_deps.items():
            depends_on = service_config.get('depends_on', [])
            for dependency in depends_on:
                if dependency not in service_deps:
                    self.errors.append(f"Service '{service_name}' depends on undefined service: {dependency}")
    
    def _validate_environment_consistency(self):
        """Validate environment-specific configurations"""
        print("[U+1F30D] Validating environment consistency...")
        
        layers = self.config.get('layers', {})
        environments = self.config.get('environments', {})
        
        # Check environment overrides reference valid layers
        for env_name, env_config in environments.items():
            layer_overrides = env_config.get('layer_overrides', {})
            for layer_name in layer_overrides.keys():
                if layer_name not in layers:
                    self.errors.append(f"Environment '{env_name}' overrides non-existent layer: {layer_name}")
        
        # Check for environment-specific contradictions
        for layer_name, layer_config in layers.items():
            env_overrides = layer_config.get('environment_overrides', {})
            for env_name, overrides in env_overrides.items():
                # Check for conflicting settings
                if 'background_execution' in overrides and 'max_duration_minutes' in overrides:
                    if overrides['background_execution'] and overrides['max_duration_minutes'] < 5:
                        self.warnings.append(f"Layer '{layer_name}' env '{env_name}': short duration with background execution may be ineffective")
    
    def _generate_suggestions(self):
        """Generate optimization suggestions"""
        print(" IDEA:  Generating optimization suggestions...")
        
        layers = self.config.get('layers', {})
        
        # Suggest layer reordering based on duration
        layer_durations = [(name, config.get('max_duration_minutes', 0)) for name, config in layers.items()]
        layer_durations.sort(key=lambda x: x[1])
        
        if len(layer_durations) > 1:
            fastest = layer_durations[0][0]
            if fastest != list(layers.keys())[0]:
                self.suggestions.append(f"Consider putting fastest layer '{fastest}' first for better feedback")
        
        # Suggest resource optimization
        total_categories = sum(len(config.get('categories', [])) for config in layers.values())
        if total_categories > 15:
            self.suggestions.append("Consider splitting large layers or optimizing category distribution for better parallelization")
        
        # Suggest background execution
        long_layers = [name for name, config in layers.items() 
                      if config.get('max_duration_minutes', 0) > 15 
                      and not config.get('background_execution', False)]
        if long_layers:
            self.suggestions.append(f"Consider enabling background execution for long-running layers: {', '.join(long_layers)}")
    
    def print_results(self, result: ValidationResult):
        """Print validation results with formatting"""
        print(f"\n{'='*60}")
        print("LAYER CONFIGURATION VALIDATION RESULTS")
        print(f"{'='*60}")
        
        if result.is_valid:
            print(" PASS:  Configuration is VALID!")
        else:
            print(" FAIL:  Configuration has ERRORS!")
        
        if result.errors:
            print(f"\n ALERT:  ERRORS ({len(result.errors)}):")
            for i, error in enumerate(result.errors, 1):
                print(f"  {i:2d}. {error}")
        
        if result.warnings:
            print(f"\n WARNING: [U+FE0F]  WARNINGS ({len(result.warnings)}):")
            for i, warning in enumerate(result.warnings, 1):
                print(f"  {i:2d}. {warning}")
        
        if result.suggestions:
            print(f"\n IDEA:  SUGGESTIONS ({len(result.suggestions)}):")
            for i, suggestion in enumerate(result.suggestions, 1):
                print(f"  {i:2d}. {suggestion}")
        
        print(f"\n{'='*60}")
        
        return result.is_valid


def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(description="Validate test layer configuration")
    parser.add_argument("--config", help="Path to layer configuration file")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix common issues")
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path(__file__).parent.parent
    
    # Initialize validator
    validator = LayerConfigValidator(project_root)
    
    if args.config:
        validator.config_path = Path(args.config)
    
    # Run validation
    result = validator.validate_all()
    
    # Output results
    if args.json:
        output = {
            "valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "suggestions": result.suggestions
        }
        print(json.dumps(output, indent=2))
    else:
        is_valid = validator.print_results(result)
        
        # Exit with error code if validation failed
        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()