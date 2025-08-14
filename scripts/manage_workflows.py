#!/usr/bin/env python3
"""
GitHub Workflows Management Script
Manage workflow configurations, enable/disable features, and monitor health
"""

import argparse
import json
import os
import subprocess
import sys
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class WorkflowManager:
    """Manage GitHub workflow configurations and settings"""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.config_file = os.path.join(repo_path, ".github", "workflow-config.yml")
        self.workflows_dir = os.path.join(repo_path, ".github", "workflows")
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """Load workflow configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}
        
    def save_config(self):
        """Save workflow configuration"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
    def list_workflows(self) -> List[str]:
        """List all workflow files"""
        workflows = []
        if os.path.exists(self.workflows_dir):
            for file in os.listdir(self.workflows_dir):
                if file.endswith('.yml') or file.endswith('.yaml'):
                    workflows.append(file)
        return sorted(workflows)
        
    def get_workflow_status(self) -> Dict[str, dict]:
        """Get status of all workflows"""
        status = {}
        workflows = self.list_workflows()
        
        for workflow_file in workflows:
            workflow_name = workflow_file.replace('.yml', '').replace('.yaml', '')
            
            # Check if enabled in config
            enabled = True
            if 'workflows' in self.config:
                for category in self.config['workflows'].values():
                    if isinstance(category, dict) and workflow_name in category:
                        enabled = category[workflow_name].get('enabled', True)
                        break
                        
            status[workflow_name] = {
                'file': workflow_file,
                'enabled': enabled,
                'category': self._get_workflow_category(workflow_name)
            }
            
        return status
        
    def _get_workflow_category(self, workflow_name: str) -> str:
        """Determine workflow category"""
        if 'test' in workflow_name or 'smoke' in workflow_name or 'unit' in workflow_name:
            return 'testing'
        elif 'staging' in workflow_name or 'deploy' in workflow_name:
            return 'deployment'
        elif 'ai' in workflow_name or 'gemini' in workflow_name or 'autofix' in workflow_name:
            return 'ai'
        elif 'monitor' in workflow_name or 'health' in workflow_name:
            return 'monitoring'
        else:
            return 'other'
            
    def enable_workflow(self, workflow_name: str):
        """Enable a specific workflow"""
        category = self._get_workflow_category(workflow_name)
        
        if 'workflows' not in self.config:
            self.config['workflows'] = {}
        if category not in self.config['workflows']:
            self.config['workflows'][category] = {}
        if workflow_name not in self.config['workflows'][category]:
            self.config['workflows'][category][workflow_name] = {}
            
        self.config['workflows'][category][workflow_name]['enabled'] = True
        self.save_config()
        print(f"[ENABLED] Workflow: {workflow_name}")
        
    def disable_workflow(self, workflow_name: str):
        """Disable a specific workflow"""
        category = self._get_workflow_category(workflow_name)
        
        if 'workflows' not in self.config:
            self.config['workflows'] = {}
        if category not in self.config['workflows']:
            self.config['workflows'][category] = {}
        if workflow_name not in self.config['workflows'][category]:
            self.config['workflows'][category][workflow_name] = {}
            
        self.config['workflows'][category][workflow_name]['enabled'] = False
        self.save_config()
        print(f"[DISABLED] Workflow: {workflow_name}")
        
    def set_feature(self, feature: str, value: bool):
        """Enable or disable a feature flag"""
        if 'features' not in self.config:
            self.config['features'] = {}
            
        self.config['features'][feature] = value
        self.save_config()
        status = "enabled" if value else "disabled"
        print(f"[{'ON' if value else 'OFF'}] Feature '{feature}' {status}")
        
    def set_cost_budget(self, daily: Optional[float] = None, monthly: Optional[float] = None):
        """Set cost budget limits"""
        if 'cost_control' not in self.config:
            self.config['cost_control'] = {}
            
        if daily is not None:
            self.config['cost_control']['daily_limit'] = daily
            print(f"[BUDGET] Set daily budget: ${daily}")
            
        if monthly is not None:
            self.config['cost_control']['monthly_budget'] = monthly
            print(f"[BUDGET] Set monthly budget: ${monthly}")
            
        self.save_config()
        
    def show_config(self):
        """Display current configuration"""
        print("\n[CONFIG] Current Workflow Configuration")
        print("=" * 50)
        
        # Features
        print("\n[FEATURES]:")
        features = self.config.get('features', {})
        for feature, enabled in features.items():
            status = "[ON]" if enabled else "[OFF]"
            print(f"  {status} {feature}: {enabled}")
            
        # Workflows
        print("\n[WORKFLOWS]:")
        status = self.get_workflow_status()
        for name, info in status.items():
            status_icon = "[ENABLED]" if info['enabled'] else "[DISABLED]"
            print(f"  {status_icon} {name} ({info['category']})")
            
        # Cost Control
        print("\n[COST CONTROL]:")
        cost = self.config.get('cost_control', {})
        print(f"  Daily limit: ${cost.get('daily_limit', 'Not set')}")
        print(f"  Monthly budget: ${cost.get('monthly_budget', 'Not set')}")
        
        # Test Hierarchy
        print("\n[TEST HIERARCHY]:")
        hierarchy = self.config.get('test_hierarchy', {}).get('levels', [])
        for level in hierarchy:
            deps = level.get('depends_on', [])
            blocks = level.get('blocks', [])
            print(f"  {level['name']}:")
            if deps:
                print(f"    Depends on: {', '.join(deps)}")
            if blocks:
                print(f"    Blocks: {', '.join(blocks)}")
                
    def apply_preset(self, preset: str):
        """Apply a configuration preset"""
        presets = {
            'minimal': {
                'features': {
                    'hierarchical_testing': False,
                    'smart_retry': False,
                    'ai_assistance': False,
                    'cost_monitoring': True,
                    'auto_cleanup': True
                },
                'workflows': {
                    'testing': {
                        'smoke': {'enabled': True},
                        'unit': {'enabled': False},
                        'integration': {'enabled': False},
                        'comprehensive': {'enabled': False}
                    },
                    'ai': {
                        'autofix': {'enabled': False},
                        'pr_review': {'enabled': False}
                    }
                }
            },
            'standard': {
                'features': {
                    'hierarchical_testing': True,
                    'smart_retry': True,
                    'ai_assistance': False,
                    'cost_monitoring': True,
                    'auto_cleanup': True
                },
                'workflows': {
                    'testing': {
                        'smoke': {'enabled': True},
                        'unit': {'enabled': True},
                        'integration': {'enabled': True},
                        'comprehensive': {'enabled': False}
                    },
                    'ai': {
                        'autofix': {'enabled': False},
                        'pr_review': {'enabled': False}
                    }
                }
            },
            'full': {
                'features': {
                    'hierarchical_testing': True,
                    'smart_retry': True,
                    'ai_assistance': True,
                    'cost_monitoring': True,
                    'auto_cleanup': True
                },
                'workflows': {
                    'testing': {
                        'smoke': {'enabled': True},
                        'unit': {'enabled': True},
                        'integration': {'enabled': True},
                        'comprehensive': {'enabled': True}
                    },
                    'ai': {
                        'autofix': {'enabled': True},
                        'pr_review': {'enabled': True}
                    }
                }
            },
            'cost_optimized': {
                'features': {
                    'hierarchical_testing': True,
                    'smart_retry': False,
                    'ai_assistance': False,
                    'cost_monitoring': True,
                    'auto_cleanup': True
                },
                'workflows': {
                    'testing': {
                        'smoke': {'enabled': True},
                        'unit': {'enabled': True, 'skip_on_draft_pr': True},
                        'integration': {'enabled': False},
                        'comprehensive': {'enabled': False}
                    }
                },
                'cost_control': {
                    'daily_limit': 10,
                    'monthly_budget': 200
                }
            }
        }
        
        if preset not in presets:
            print(f"[ERROR] Unknown preset: {preset}")
            print(f"Available presets: {', '.join(presets.keys())}")
            return
            
        # Apply preset
        preset_config = presets[preset]
        self.config.update(preset_config)
        self.save_config()
        print(f"[SUCCESS] Applied preset: {preset}")
        
    def validate_config(self):
        """Validate workflow configuration"""
        issues = []
        
        # Check for circular dependencies in test hierarchy
        hierarchy = self.config.get('test_hierarchy', {}).get('levels', [])
        for level in hierarchy:
            name = level['name']
            depends = level.get('depends_on', [])
            blocks = level.get('blocks', [])
            
            # Check if any dependency also blocks this level
            for dep in depends:
                for other in hierarchy:
                    if other['name'] == dep and name in other.get('blocks', []):
                        issues.append(f"Circular dependency: {name} <-> {dep}")
                        
        # Check cost limits
        cost = self.config.get('cost_control', {})
        daily = cost.get('daily_limit', 0)
        monthly = cost.get('monthly_budget', 0)
        
        if daily * 30 > monthly and daily > 0 and monthly > 0:
            issues.append(f"Daily limit (${daily}) * 30 exceeds monthly budget (${monthly})")
            
        # Check for conflicting settings
        features = self.config.get('features', {})
        if features.get('hierarchical_testing') and not hierarchy:
            issues.append("Hierarchical testing enabled but no hierarchy defined")
            
        if issues:
            print("[WARNING] Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("[OK] Configuration is valid")
            return True


def main():
    parser = argparse.ArgumentParser(description='Manage GitHub Workflows')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List command
    subparsers.add_parser('list', help='List all workflows and their status')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a workflow')
    enable_parser.add_argument('workflow', help='Workflow name')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a workflow')
    disable_parser.add_argument('workflow', help='Workflow name')
    
    # Feature command
    feature_parser = subparsers.add_parser('feature', help='Enable/disable a feature')
    feature_parser.add_argument('name', help='Feature name')
    feature_parser.add_argument('--enable', action='store_true', help='Enable feature')
    feature_parser.add_argument('--disable', action='store_true', help='Disable feature')
    
    # Budget command
    budget_parser = subparsers.add_parser('budget', help='Set cost budget')
    budget_parser.add_argument('--daily', type=float, help='Daily budget limit')
    budget_parser.add_argument('--monthly', type=float, help='Monthly budget limit')
    
    # Preset command
    preset_parser = subparsers.add_parser('preset', help='Apply configuration preset')
    preset_parser.add_argument('name', choices=['minimal', 'standard', 'full', 'cost_optimized'],
                              help='Preset name')
    
    # Show command
    subparsers.add_parser('show', help='Show current configuration')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate configuration')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = WorkflowManager()
    
    # Execute command
    if args.command == 'list':
        status = manager.get_workflow_status()
        print("\n[WORKFLOWS] Status")
        print("=" * 50)
        for name, info in status.items():
            status_icon = "[ON]" if info['enabled'] else "[OFF]"
            print(f"{status_icon} {name:<30} [{info['category']}]")
            
    elif args.command == 'enable':
        manager.enable_workflow(args.workflow)
        
    elif args.command == 'disable':
        manager.disable_workflow(args.workflow)
        
    elif args.command == 'feature':
        if args.enable:
            manager.set_feature(args.name, True)
        elif args.disable:
            manager.set_feature(args.name, False)
        else:
            print("[ERROR] Please specify --enable or --disable")
            
    elif args.command == 'budget':
        manager.set_cost_budget(daily=args.daily, monthly=args.monthly)
        
    elif args.command == 'preset':
        manager.apply_preset(args.name)
        
    elif args.command == 'show':
        manager.show_config()
        
    elif args.command == 'validate':
        manager.validate_config()
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()