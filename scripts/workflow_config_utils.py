#!/usr/bin/env python3
"""
Workflow Configuration Utilities
Helper functions for workflow configuration display and validation
"""

from typing import Dict, List


class WorkflowConfigUtils:
    """Utilities for workflow configuration operations"""
    
    @staticmethod
    def show_config_display(config: dict, get_workflow_status_func):
        """Display current configuration"""
        print("\n[CONFIG] Current Workflow Configuration")
        print("=" * 50)
        WorkflowConfigUtils._show_features(config)
        WorkflowConfigUtils._show_workflows(get_workflow_status_func)
        WorkflowConfigUtils._show_cost_control(config)
        WorkflowConfigUtils._show_test_hierarchy(config)
        
    @staticmethod
    def _show_features(config: dict):
        """Display features configuration"""
        print("\n[FEATURES]:")
        features = config.get('features', {})
        for feature, enabled in features.items():
            status = "[ON]" if enabled else "[OFF]"
            print(f"  {status} {feature}: {enabled}")
            
    @staticmethod
    def _show_workflows(get_workflow_status_func):
        """Display workflows configuration"""
        print("\n[WORKFLOWS]:")
        status = get_workflow_status_func()
        for name, info in status.items():
            status_icon = "[ENABLED]" if info['enabled'] else "[DISABLED]"
            print(f"  {status_icon} {name} ({info['category']})")
            
    @staticmethod
    def _show_cost_control(config: dict):
        """Display cost control configuration"""
        print("\n[COST CONTROL]:")
        cost = config.get('cost_control', {})
        print(f"  Daily limit: ${cost.get('daily_limit', 'Not set')}")
        print(f"  Monthly budget: ${cost.get('monthly_budget', 'Not set')}")
        
    @staticmethod
    def _show_test_hierarchy(config: dict):
        """Display test hierarchy configuration"""
        print("\n[TEST HIERARCHY]:")
        hierarchy = config.get('test_hierarchy', {}).get('levels', [])
        for level in hierarchy:
            deps = level.get('depends_on', [])
            blocks = level.get('blocks', [])
            print(f"  {level['name']}:")
            if deps:
                print(f"    Depends on: {', '.join(deps)}")
            if blocks:
                print(f"    Blocks: {', '.join(blocks)}")
                
    @staticmethod
    def validate_config_issues(config: dict) -> bool:
        """Validate workflow configuration and return True if valid"""
        issues = []
        WorkflowConfigUtils._check_circular_dependencies(config, issues)
        WorkflowConfigUtils._check_cost_limits(config, issues)
        WorkflowConfigUtils._check_conflicting_settings(config, issues)
        return WorkflowConfigUtils._report_issues(issues)
        
    @staticmethod
    def _check_circular_dependencies(config: dict, issues: List[str]):
        """Check for circular dependencies in test hierarchy"""
        hierarchy = config.get('test_hierarchy', {}).get('levels', [])
        for level in hierarchy:
            name = level['name']
            depends = level.get('depends_on', [])
            for dep in depends:
                for other in hierarchy:
                    if other['name'] == dep and name in other.get('blocks', []):
                        issues.append(f"Circular dependency: {name} <-> {dep}")
                        
    @staticmethod
    def _check_cost_limits(config: dict, issues: List[str]):
        """Check cost limits for consistency"""
        cost = config.get('cost_control', {})
        daily = cost.get('daily_limit', 0)
        monthly = cost.get('monthly_budget', 0)
        if daily * 30 > monthly and daily > 0 and monthly > 0:
            issues.append(f"Daily limit (${daily}) * 30 exceeds monthly budget (${monthly})")
            
    @staticmethod
    def _check_conflicting_settings(config: dict, issues: List[str]):
        """Check for conflicting settings"""
        features = config.get('features', {})
        hierarchy = config.get('test_hierarchy', {}).get('levels', [])
        if features.get('hierarchical_testing') and not hierarchy:
            issues.append("Hierarchical testing enabled but no hierarchy defined")
            
    @staticmethod
    def _report_issues(issues: List[str]) -> bool:
        """Report validation issues and return True if valid"""
        if issues:
            print("[WARNING] Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("[OK] Configuration is valid")
            return True