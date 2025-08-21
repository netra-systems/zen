#!/usr/bin/env python3
"""
L3 Integration Tests for GitHub Workflow Management System
Tests manage_workflows.py with configuration management and presets
"""

import json
import os
import sys
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import pytest

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from manage_workflows import WorkflowManager


class TestWorkflowManagerBasics:
    """Test basic WorkflowManager functionality."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .github/workflows directory
            workflows_dir = Path(tmpdir) / ".github" / "workflows"
            workflows_dir.mkdir(parents=True)
            
            # Create sample workflow files
            (workflows_dir / "ci.yml").write_text("name: CI\non: push")
            (workflows_dir / "deploy.yml").write_text("name: Deploy\non: release")
            (workflows_dir / "test-unit.yml").write_text("name: Unit Tests\non: pull_request")
            (workflows_dir / "staging-deploy.yml").write_text("name: Staging Deploy\non: push")
            (workflows_dir / "ai-autofix.yml").write_text("name: AI Autofix\non: issue")
            (workflows_dir / "health-monitor.yml").write_text("name: Health Monitor\non: schedule")
            
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        return WorkflowManager(temp_repo)
    
    def test_init_without_config(self, temp_repo):
        """Test initializing WorkflowManager without existing config."""
        manager = WorkflowManager(temp_repo)
        
        assert manager.repo_path == temp_repo
        assert manager.config == {}
        assert manager.config_file == os.path.join(temp_repo, ".github", "workflow-config.yml")
        assert manager.workflows_dir == os.path.join(temp_repo, ".github", "workflows")
    
    def test_init_with_existing_config(self, temp_repo):
        """Test initializing WorkflowManager with existing config."""
        config_path = Path(temp_repo) / ".github" / "workflow-config.yml"
        config_data = {
            "features": {"auto_merge": True},
            "workflows": {
                "testing": {"ci": {"enabled": True}}
            }
        }
        config_path.write_text(yaml.dump(config_data))
        
        manager = WorkflowManager(temp_repo)
        
        assert manager.config == config_data
        assert manager.config["features"]["auto_merge"] is True
    
    def test_list_workflows(self, manager):
        """Test listing all workflow files."""
        workflows = manager.list_workflows()
        
        assert len(workflows) == 6
        assert "ci.yml" in workflows
        assert "deploy.yml" in workflows
        assert "test-unit.yml" in workflows
        assert "staging-deploy.yml" in workflows
        assert "ai-autofix.yml" in workflows
        assert "health-monitor.yml" in workflows
        assert workflows == sorted(workflows)  # Should be sorted
    
    def test_list_workflows_empty_dir(self, temp_repo):
        """Test listing workflows when directory doesn't exist."""
        manager = WorkflowManager(os.path.join(temp_repo, "nonexistent"))
        workflows = manager.list_workflows()
        
        assert workflows == []
    
    def test_get_workflow_category(self, manager):
        """Test workflow category determination."""
        assert manager._get_workflow_category("test-unit") == "testing"
        assert manager._get_workflow_category("smoke-tests") == "testing"
        assert manager._get_workflow_category("staging-deploy") == "deployment"
        assert manager._get_workflow_category("deploy-prod") == "deployment"
        assert manager._get_workflow_category("ai-review") == "ai"
        assert manager._get_workflow_category("gemini-analysis") == "ai"
        assert manager._get_workflow_category("autofix-issues") == "ai"
        assert manager._get_workflow_category("health-check") == "monitoring"
        assert manager._get_workflow_category("monitor-services") == "monitoring"
        assert manager._get_workflow_category("build") == "other"
        assert manager._get_workflow_category("random-workflow") == "other"


class TestWorkflowStatusManagement:
    """Test workflow status and configuration management."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager_with_config(self, temp_repo):
        """Create WorkflowManager with pre-configured state."""
        config_path = Path(temp_repo) / ".github" / "workflow-config.yml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_data = {
            "workflows": {
                "testing": {
                    "ci": {"enabled": True},
                    "test-unit": {"enabled": False}
                },
                "deployment": {
                    "deploy": {"enabled": True}
                }
            }
        }
        config_path.write_text(yaml.dump(config_data))
        
        # Create workflow files
        workflows_dir = Path(temp_repo) / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        (workflows_dir / "ci.yml").write_text("name: CI")
        (workflows_dir / "test-unit.yml").write_text("name: Unit Tests")
        (workflows_dir / "deploy.yml").write_text("name: Deploy")
        (workflows_dir / "staging-deploy.yml").write_text("name: Staging")
        
        return WorkflowManager(temp_repo)
    
    def test_get_workflow_status(self, manager_with_config):
        """Test getting status of all workflows."""
        status = manager_with_config.get_workflow_status()
        
        assert "ci" in status
        assert status["ci"]["enabled"] is True
        assert status["ci"]["category"] == "testing"
        assert status["ci"]["file"] == "ci.yml"
        
        assert "test-unit" in status
        assert status["test-unit"]["enabled"] is False
        assert status["test-unit"]["category"] == "testing"
        
        assert "deploy" in status
        assert status["deploy"]["enabled"] is True
        assert status["deploy"]["category"] == "deployment"
        
        # Workflow not in config should default to enabled
        assert "staging-deploy" in status
        assert status["staging-deploy"]["enabled"] is True
        assert status["staging-deploy"]["category"] == "deployment"
    
    def test_enable_workflow(self, manager_with_config):
        """Test enabling a workflow."""
        # Initially disabled
        assert manager_with_config.config["workflows"]["testing"]["test-unit"]["enabled"] is False
        
        manager_with_config.enable_workflow("test-unit")
        
        # Should now be enabled
        assert manager_with_config.config["workflows"]["testing"]["test-unit"]["enabled"] is True
        
        # Verify config was saved
        saved_config = yaml.safe_load(
            Path(manager_with_config.config_file).read_text()
        )
        assert saved_config["workflows"]["testing"]["test-unit"]["enabled"] is True
    
    def test_enable_new_workflow(self, manager_with_config):
        """Test enabling a workflow not in config."""
        manager_with_config.enable_workflow("staging-deploy")
        
        assert "deployment" in manager_with_config.config["workflows"]
        assert "staging-deploy" in manager_with_config.config["workflows"]["deployment"]
        assert manager_with_config.config["workflows"]["deployment"]["staging-deploy"]["enabled"] is True
    
    def test_disable_workflow(self, manager_with_config):
        """Test disabling a workflow."""
        # Initially enabled
        assert manager_with_config.config["workflows"]["testing"]["ci"]["enabled"] is True
        
        manager_with_config.disable_workflow("ci")
        
        # Should now be disabled
        assert manager_with_config.config["workflows"]["testing"]["ci"]["enabled"] is False
        
        # Verify config was saved
        saved_config = yaml.safe_load(
            Path(manager_with_config.config_file).read_text()
        )
        assert saved_config["workflows"]["testing"]["ci"]["enabled"] is False
    
    def test_disable_new_workflow(self, manager_with_config):
        """Test disabling a workflow not in config."""
        manager_with_config.disable_workflow("staging-deploy")
        
        assert "deployment" in manager_with_config.config["workflows"]
        assert "staging-deploy" in manager_with_config.config["workflows"]["deployment"]
        assert manager_with_config.config["workflows"]["deployment"]["staging-deploy"]["enabled"] is False


class TestFeatureManagement:
    """Test feature flag management."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    def test_set_feature_enable(self, manager):
        """Test enabling a feature."""
        manager.set_feature("auto_merge", True)
        
        assert "features" in manager.config
        assert manager.config["features"]["auto_merge"] is True
        
        # Verify saved
        saved_config = yaml.safe_load(Path(manager.config_file).read_text())
        assert saved_config["features"]["auto_merge"] is True
    
    def test_set_feature_disable(self, manager):
        """Test disabling a feature."""
        manager.set_feature("auto_deploy", False)
        
        assert manager.config["features"]["auto_deploy"] is False
        
        # Verify saved
        saved_config = yaml.safe_load(Path(manager.config_file).read_text())
        assert saved_config["features"]["auto_deploy"] is False
    
    def test_set_multiple_features(self, manager):
        """Test setting multiple features."""
        manager.set_feature("feature1", True)
        manager.set_feature("feature2", False)
        manager.set_feature("feature3", True)
        
        assert manager.config["features"]["feature1"] is True
        assert manager.config["features"]["feature2"] is False
        assert manager.config["features"]["feature3"] is True


class TestCostBudgetManagement:
    """Test cost budget configuration."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    def test_set_daily_budget(self, manager):
        """Test setting daily budget limit."""
        manager.set_cost_budget(daily=50.0)
        
        assert "cost_control" in manager.config
        assert manager.config["cost_control"]["daily_limit"] == 50.0
        
        # Verify saved
        saved_config = yaml.safe_load(Path(manager.config_file).read_text())
        assert saved_config["cost_control"]["daily_limit"] == 50.0
    
    def test_set_monthly_budget(self, manager):
        """Test setting monthly budget limit."""
        manager.set_cost_budget(monthly=1500.0)
        
        assert "cost_control" in manager.config
        assert manager.config["cost_control"]["monthly_budget"] == 1500.0
        
        # Verify saved
        saved_config = yaml.safe_load(Path(manager.config_file).read_text())
        assert saved_config["cost_control"]["monthly_budget"] == 1500.0
    
    def test_set_both_budgets(self, manager):
        """Test setting both daily and monthly budgets."""
        manager.set_cost_budget(daily=75.0, monthly=2000.0)
        
        assert manager.config["cost_control"]["daily_limit"] == 75.0
        assert manager.config["cost_control"]["monthly_budget"] == 2000.0
    
    def test_update_existing_budget(self, manager):
        """Test updating existing budget values."""
        manager.set_cost_budget(daily=100.0, monthly=3000.0)
        manager.set_cost_budget(daily=150.0)  # Update only daily
        
        assert manager.config["cost_control"]["daily_limit"] == 150.0
        assert manager.config["cost_control"]["monthly_budget"] == 3000.0  # Unchanged


class TestPresetManagement:
    """Test configuration preset management."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    @patch('manage_workflows.WorkflowPresets.get_presets')
    @patch('manage_workflows.WorkflowPresets.validate_preset')
    def test_apply_minimal_preset(self, mock_validate, mock_get_presets, manager):
        """Test applying minimal preset."""
        mock_presets = {
            "minimal": {
                "features": {
                    "auto_merge": False,
                    "auto_deploy": False,
                    "ai_features": False
                },
                "cost_control": {
                    "daily_limit": 10.0,
                    "monthly_budget": 300.0
                }
            }
        }
        mock_get_presets.return_value = mock_presets
        mock_validate.return_value = True
        
        manager.apply_preset("minimal")
        
        assert manager.config["features"]["auto_merge"] is False
        assert manager.config["features"]["auto_deploy"] is False
        assert manager.config["features"]["ai_features"] is False
        assert manager.config["cost_control"]["daily_limit"] == 10.0
        assert manager.config["cost_control"]["monthly_budget"] == 300.0
    
    @patch('manage_workflows.WorkflowPresets.get_presets')
    @patch('manage_workflows.WorkflowPresets.validate_preset')
    def test_apply_standard_preset(self, mock_validate, mock_get_presets, manager):
        """Test applying standard preset."""
        mock_presets = {
            "standard": {
                "features": {
                    "auto_merge": True,
                    "auto_deploy": False,
                    "ai_features": True,
                    "monitoring": True
                },
                "cost_control": {
                    "daily_limit": 50.0,
                    "monthly_budget": 1500.0
                }
            }
        }
        mock_get_presets.return_value = mock_presets
        mock_validate.return_value = True
        
        manager.apply_preset("standard")
        
        assert manager.config["features"]["auto_merge"] is True
        assert manager.config["features"]["auto_deploy"] is False
        assert manager.config["features"]["ai_features"] is True
        assert manager.config["features"]["monitoring"] is True
    
    @patch('manage_workflows.WorkflowPresets.get_presets')
    @patch('manage_workflows.WorkflowPresets.validate_preset')
    def test_apply_invalid_preset(self, mock_validate, mock_get_presets, manager):
        """Test applying invalid preset."""
        mock_get_presets.return_value = {}
        mock_validate.return_value = False
        
        # Store original config
        original_config = manager.config.copy()
        
        manager.apply_preset("invalid_preset")
        
        # Config should remain unchanged
        assert manager.config == original_config
    
    @patch('manage_workflows.WorkflowPresets.get_presets')
    @patch('manage_workflows.WorkflowPresets.validate_preset')
    def test_preset_overwrites_existing(self, mock_validate, mock_get_presets, manager):
        """Test that preset overwrites existing configuration."""
        # Set initial config
        manager.set_feature("auto_merge", True)
        manager.set_cost_budget(daily=100.0)
        
        # Apply preset with different values
        mock_presets = {
            "cost_optimized": {
                "features": {
                    "auto_merge": False,
                    "expensive_features": False
                },
                "cost_control": {
                    "daily_limit": 5.0,
                    "monthly_budget": 150.0
                }
            }
        }
        mock_get_presets.return_value = mock_presets
        mock_validate.return_value = True
        
        manager.apply_preset("cost_optimized")
        
        # Values should be overwritten
        assert manager.config["features"]["auto_merge"] is False
        assert manager.config["cost_control"]["daily_limit"] == 5.0


class TestConfigValidation:
    """Test configuration validation."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    @patch('manage_workflows.WorkflowConfigUtils.validate_config_issues')
    def test_validate_config_valid(self, mock_validate, manager):
        """Test validating valid configuration."""
        mock_validate.return_value = True
        
        result = manager.validate_config()
        
        assert result is True
        mock_validate.assert_called_once_with(manager.config)
    
    @patch('manage_workflows.WorkflowConfigUtils.validate_config_issues')
    def test_validate_config_invalid(self, mock_validate, manager):
        """Test validating invalid configuration."""
        mock_validate.return_value = False
        
        result = manager.validate_config()
        
        assert result is False
        mock_validate.assert_called_once_with(manager.config)


class TestConfigDisplay:
    """Test configuration display functionality."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    @patch('manage_workflows.WorkflowConfigUtils.show_config_display')
    def test_show_config(self, mock_show, manager):
        """Test showing configuration."""
        manager.config = {
            "features": {"test": True},
            "workflows": {"testing": {"ci": {"enabled": True}}}
        }
        
        manager.show_config()
        
        mock_show.assert_called_once()
        # First arg should be config, second should be callable
        call_args = mock_show.call_args[0]
        assert call_args[0] == manager.config
        assert callable(call_args[1])


class TestConfigPersistence:
    """Test configuration file persistence."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    def test_save_config_creates_file(self, manager):
        """Test saving configuration creates file."""
        config_path = Path(manager.config_file)
        assert not config_path.exists()
        
        manager.config = {"test": "value"}
        manager.save_config()
        
        assert config_path.exists()
        saved_data = yaml.safe_load(config_path.read_text())
        assert saved_data == {"test": "value"}
    
    def test_save_config_overwrites_existing(self, manager):
        """Test saving configuration overwrites existing file."""
        config_path = Path(manager.config_file)
        
        # Write initial config
        manager.config = {"initial": "config"}
        manager.save_config()
        
        # Update and save again
        manager.config = {"updated": "config", "new": "value"}
        manager.save_config()
        
        saved_data = yaml.safe_load(config_path.read_text())
        assert saved_data == {"updated": "config", "new": "value"}
        assert "initial" not in saved_data
    
    def test_save_config_preserves_order(self, manager):
        """Test that save_config preserves key order."""
        manager.config = {
            "workflows": {"test": {}},
            "features": {"feature1": True},
            "cost_control": {"daily_limit": 50}
        }
        manager.save_config()
        
        # Read raw text to check order
        config_text = Path(manager.config_file).read_text()
        workflows_pos = config_text.index("workflows:")
        features_pos = config_text.index("features:")
        cost_pos = config_text.index("cost_control:")
        
        assert workflows_pos < features_pos < cost_pos


class TestWorkflowManagerEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def manager(self, temp_repo):
        """Create WorkflowManager instance."""
        Path(temp_repo, ".github").mkdir(parents=True, exist_ok=True)
        return WorkflowManager(temp_repo)
    
    def test_handle_corrupted_config(self, temp_repo):
        """Test handling corrupted configuration file."""
        config_path = Path(temp_repo) / ".github" / "workflow-config.yml"
        config_path.write_text("invalid: yaml: content: [")
        
        # Should handle gracefully and use empty config
        manager = WorkflowManager(temp_repo)
        assert manager.config == {}
    
    def test_handle_missing_github_dir(self):
        """Test handling missing .github directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = WorkflowManager(tmpdir)
            
            # Should create directory when saving
            manager.set_feature("test", True)
            
            assert Path(tmpdir, ".github").exists()
            assert Path(tmpdir, ".github", "workflow-config.yml").exists()
    
    def test_workflow_names_with_special_chars(self, manager):
        """Test handling workflow names with special characters."""
        # Create workflows directory
        workflows_dir = Path(manager.workflows_dir)
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        # Create workflow with special characters
        (workflows_dir / "test-workflow_v2.1.yml").write_text("name: Test")
        
        workflows = manager.list_workflows()
        assert "test-workflow_v2.1.yml" in workflows
        
        # Test enable/disable with special name
        manager.enable_workflow("test-workflow_v2.1")
        status = manager.get_workflow_status()
        assert "test-workflow_v2.1" in status


class TestComplexWorkflowScenarios:
    """Test complex real-world workflow scenarios."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def complex_manager(self, temp_repo):
        """Create manager with complex configuration."""
        config_path = Path(temp_repo) / ".github" / "workflow-config.yml"
        config_data = {
            "features": {
                "auto_merge": True,
                "auto_deploy": False,
                "ai_review": True,
                "security_scanning": True
            },
            "cost_control": {
                "daily_limit": 100.0,
                "monthly_budget": 3000.0,
                "alert_threshold": 0.8
            },
            "workflows": {
                "testing": {
                    "unit-tests": {"enabled": True, "priority": "high"},
                    "integration-tests": {"enabled": True, "priority": "medium"},
                    "smoke-tests": {"enabled": False, "priority": "low"}
                },
                "deployment": {
                    "staging-deploy": {"enabled": True, "auto_approve": False},
                    "prod-deploy": {"enabled": True, "requires_approval": True}
                },
                "ai": {
                    "ai-review": {"enabled": True, "model": "gpt-4"},
                    "auto-fix": {"enabled": False, "max_attempts": 3}
                }
            }
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.dump(config_data))
        
        # Create corresponding workflow files
        workflows_dir = Path(temp_repo) / ".github" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)
        
        for category in config_data["workflows"]:
            for workflow in config_data["workflows"][category]:
                (workflows_dir / f"{workflow}.yml").write_text(f"name: {workflow}")
        
        return WorkflowManager(temp_repo)
    
    def test_complex_workflow_status(self, complex_manager):
        """Test getting status with complex configuration."""
        status = complex_manager.get_workflow_status()
        
        # Verify all workflows are present with correct status
        assert status["unit-tests"]["enabled"] is True
        assert status["integration-tests"]["enabled"] is True
        assert status["smoke-tests"]["enabled"] is False
        assert status["staging-deploy"]["enabled"] is True
        assert status["prod-deploy"]["enabled"] is True
        assert status["ai-review"]["enabled"] is True
        assert status["auto-fix"]["enabled"] is False
    
    def test_bulk_workflow_operations(self, complex_manager):
        """Test bulk enable/disable operations."""
        # Disable all testing workflows
        for workflow in ["unit-tests", "integration-tests", "smoke-tests"]:
            complex_manager.disable_workflow(workflow)
        
        status = complex_manager.get_workflow_status()
        assert all(
            not status[w]["enabled"] 
            for w in ["unit-tests", "integration-tests", "smoke-tests"]
        )
        
        # Re-enable specific workflows
        complex_manager.enable_workflow("unit-tests")
        complex_manager.enable_workflow("integration-tests")
        
        status = complex_manager.get_workflow_status()
        assert status["unit-tests"]["enabled"] is True
        assert status["integration-tests"]["enabled"] is True
        assert status["smoke-tests"]["enabled"] is False
    
    def test_feature_impact_analysis(self, complex_manager):
        """Test analyzing feature changes impact."""
        # Disable AI features
        complex_manager.set_feature("ai_review", False)
        
        # This should logically affect AI workflows
        # (Note: actual implementation would need this logic)
        assert complex_manager.config["features"]["ai_review"] is False
        
        # Verify other features remain unchanged
        assert complex_manager.config["features"]["auto_merge"] is True
        assert complex_manager.config["features"]["security_scanning"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])