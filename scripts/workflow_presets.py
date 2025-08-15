#!/usr/bin/env python3
"""
Workflow Configuration Presets
Preset configurations for different workflow scenarios
"""

from typing import Dict


class WorkflowPresets:
    """Manage workflow configuration presets"""
    
    @staticmethod
    def get_presets() -> Dict[str, dict]:
        """Get available configuration presets"""
        return {
            'minimal': WorkflowPresets.get_minimal_preset(),
            'standard': WorkflowPresets.get_standard_preset(),
            'full': WorkflowPresets.get_full_preset(),
            'cost_optimized': WorkflowPresets.get_cost_optimized_preset()
        }
        
    @staticmethod
    def get_minimal_preset() -> dict:
        """Get minimal configuration preset"""
        return {
            'features': {
                'hierarchical_testing': False, 'smart_retry': False,
                'ai_assistance': False, 'cost_monitoring': True, 'auto_cleanup': True
            },
            'workflows': {
                'testing': {'smoke': {'enabled': True}, 'unit': {'enabled': False},
                          'integration': {'enabled': False}, 'comprehensive': {'enabled': False}},
                'ai': {'autofix': {'enabled': False}, 'pr_review': {'enabled': False}}
            }
        }
        
    @staticmethod
    def get_standard_preset() -> dict:
        """Get standard configuration preset"""
        return {
            'features': {
                'hierarchical_testing': True, 'smart_retry': True,
                'ai_assistance': False, 'cost_monitoring': True, 'auto_cleanup': True
            },
            'workflows': {
                'testing': {'smoke': {'enabled': True}, 'unit': {'enabled': True},
                          'integration': {'enabled': True}, 'comprehensive': {'enabled': False}},
                'ai': {'autofix': {'enabled': False}, 'pr_review': {'enabled': False}}
            }
        }
        
    @staticmethod
    def get_full_preset() -> dict:
        """Get full configuration preset"""
        return {
            'features': {
                'hierarchical_testing': True, 'smart_retry': True,
                'ai_assistance': True, 'cost_monitoring': True, 'auto_cleanup': True
            },
            'workflows': {
                'testing': {'smoke': {'enabled': True}, 'unit': {'enabled': True},
                          'integration': {'enabled': True}, 'comprehensive': {'enabled': True}},
                'ai': {'autofix': {'enabled': True}, 'pr_review': {'enabled': True}}
            }
        }
        
    @staticmethod
    def get_cost_optimized_preset() -> dict:
        """Get cost-optimized configuration preset"""
        return {
            'features': {
                'hierarchical_testing': True, 'smart_retry': False,
                'ai_assistance': False, 'cost_monitoring': True, 'auto_cleanup': True
            },
            'workflows': {
                'testing': {'smoke': {'enabled': True},
                          'unit': {'enabled': True, 'skip_on_draft_pr': True},
                          'integration': {'enabled': False}, 'comprehensive': {'enabled': False}}
            },
            'cost_control': {'daily_limit': 10, 'monthly_budget': 200}
        }
        
    @staticmethod
    def validate_preset(preset: str, presets: Dict[str, dict]) -> bool:
        """Validate preset exists and show error if not"""
        if preset not in presets:
            print(f"[ERROR] Unknown preset: {preset}")
            print(f"Available presets: {', '.join(presets.keys())}")
            return False
        return True