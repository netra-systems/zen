#!/usr/bin/env python3
"""
L3 Integration Tests for Complete Workflow System
Tests integration between verify_workflow_status, manage_workflows, and workflow_introspection
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import httpx
import pytest
import yaml

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from manage_workflows import WorkflowManager
from verify_workflow_status import VerificationConfig, WorkflowStatusVerifier
from workflow_introspection import WorkflowIntrospector, WorkflowRun


class TestWorkflowSystemIntegration:
    """Test integration between workflow components."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create temporary repository structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .github structure
            github_dir = Path(tmpdir) / ".github"
            workflows_dir = github_dir / "workflows"
            workflows_dir.mkdir(parents=True)
            
            # Create workflow files
            workflows = {
                "ci.yml": "name: CI\non: [push, pull_request]",
                "deploy.yml": "name: Deploy\non: release",
                "tests.yml": "name: Tests\non: pull_request",
                "staging.yml": "name: Staging\non: push",
                "monitor.yml": "name: Monitor\non: schedule"
            }
            
            for filename, content in workflows.items():
                (workflows_dir / filename).write_text(content)
            
            # Create initial config
            config = {
                "features": {
                    "auto_merge": True,
                    "monitoring": True
                },
                "workflows": {
                    "testing": {
                        "ci": {"enabled": True},
                        "tests": {"enabled": True}
                    },
                    "deployment": {
                        "deploy": {"enabled": False},
                        "staging": {"enabled": True}
                    }
                }
            }
            
            config_file = github_dir / "workflow-config.yml"
            config_file.write_text(yaml.dump(config))
            
            yield tmpdir
    
    @pytest.fixture
    def workflow_manager(self, temp_repo):
        """Create WorkflowManager instance."""
        return WorkflowManager(temp_repo)
    
    @pytest.fixture
    def workflow_verifier(self):
        """Create WorkflowStatusVerifier instance."""
        config = VerificationConfig(
            repo="test-org/test-repo",
            workflow_name=None,
            run_id=None,
            token="test_token",
            timeout=300,
            poll_interval=5,
            max_retries=3
        )
        with patch('verify_workflow_status.httpx.Client'):
            return WorkflowStatusVerifier(config)
    
    @pytest.fixture
    def workflow_introspector(self):
        """Create WorkflowIntrospector instance."""
        return WorkflowIntrospector(repo="test-org/test-repo")
    
    def test_verify_enabled_workflows(self, workflow_manager, workflow_verifier):
        """Test verifying only enabled workflows."""
        # Get enabled workflows from manager
        status = workflow_manager.get_workflow_status()
        enabled_workflows = [
            name for name, info in status.items() 
            if info["enabled"]
        ]
        
        assert "ci" in enabled_workflows
        assert "tests" in enabled_workflows
        assert "staging" in enabled_workflows
        assert "deploy" not in enabled_workflows
        
        # Mock verification for enabled workflows
        mock_runs = []
        for workflow in enabled_workflows:
            workflow_verifier._api_request = Mock(return_value={
                "workflow_runs": [{
                    "id": hash(workflow) % 10000,
                    "status": "completed",
                    "conclusion": "success",
                    "name": workflow.upper(),
                    "head_branch": "main",
                    "head_sha": f"{workflow[:3]}123456",
                    "created_at": "2024-01-20T10:00:00Z",
                    "updated_at": "2024-01-20T10:05:00Z",
                    "html_url": f"https://github.com/test/repo/actions/runs/{hash(workflow) % 10000}"
                }]
            })
            
            runs = workflow_verifier.get_workflow_runs(workflow)
            assert len(runs) == 1
            assert runs[0].conclusion == "success"
            mock_runs.extend(runs)
        
        # Verify all enabled workflows passed
        assert all(
            workflow_verifier.verify_workflow_success(run) 
            for run in mock_runs
        )
    
    def test_manage_and_introspect_workflow(self, workflow_manager, workflow_introspector):
        """Test managing workflow and introspecting its status."""
        # Initially disable a workflow
        workflow_manager.disable_workflow("ci")
        assert not workflow_manager.get_workflow_status()["ci"]["enabled"]
        
        # Mock introspection showing workflow is inactive
        with patch('workflow_introspection.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout="CI\tdisabled\t123456\n"
            )
            
            workflows = workflow_introspector.list_workflows()
            ci_workflow = next(w for w in workflows if w["name"] == "CI")
            assert ci_workflow["state"] == "disabled"
        
        # Re-enable the workflow
        workflow_manager.enable_workflow("ci")
        assert workflow_manager.get_workflow_status()["ci"]["enabled"]
        
        # Mock introspection showing workflow is now active
        with patch('workflow_introspection.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout="CI\tactive\t123456\n"
            )
            
            workflows = workflow_introspector.list_workflows()
            ci_workflow = next(w for w in workflows if w["name"] == "CI")
            assert ci_workflow["state"] == "active"
    
    def test_verify_and_introspect_run_details(self, workflow_verifier, workflow_introspector):
        """Test verifying run and getting detailed information."""
        run_id = 999999
        
        # Mock verification showing run in progress
        workflow_verifier._api_request = Mock(return_value={
            "id": run_id,
            "status": "in_progress",
            "conclusion": None,
            "name": "Complex Pipeline",
            "head_branch": "feature",
            "head_sha": "abc123def456",
            "created_at": "2024-01-20T12:00:00Z",
            "updated_at": "2024-01-20T12:05:00Z",
            "html_url": f"https://github.com/test/repo/actions/runs/{run_id}"
        })
        
        run = workflow_verifier.get_workflow_run_by_id(run_id)
        assert run.status == "in_progress"
        assert not workflow_verifier.verify_workflow_success(run)
        
        # Mock introspection with detailed job information
        workflow_introspector._run_gh_command = Mock(return_value={
            "databaseId": run_id,
            "name": "Complex Pipeline",
            "workflowName": "pipeline.yml",
            "status": "in_progress",
            "conclusion": None,
            "headBranch": "feature",
            "headSha": "abc123de",
            "event": "push",
            "startedAt": "2024-01-20T12:00:00Z",
            "updatedAt": "2024-01-20T12:05:00Z",
            "url": f"https://github.com/test/repo/actions/runs/{run_id}",
            "jobs": [
                {
                    "name": "Build",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T12:00:00Z",
                    "completedAt": "2024-01-20T12:03:00Z",
                    "steps": []
                },
                {
                    "name": "Test",
                    "status": "in_progress",
                    "conclusion": None,
                    "startedAt": "2024-01-20T12:03:00Z",
                    "completedAt": None,
                    "steps": []
                }
            ]
        })
        
        detailed_run = workflow_introspector.get_run_details(run_id)
        assert detailed_run.status == "in_progress"
        assert len(detailed_run.jobs) == 2
        assert detailed_run.jobs[0].conclusion == "success"
        assert detailed_run.jobs[1].status == "in_progress"


class TestWorkflowConfigurationSync:
    """Test synchronization between configuration and workflow states."""
    
    @pytest.fixture
    def integrated_system(self, temp_repo):
        """Create integrated workflow system."""
        manager = WorkflowManager(temp_repo)
        
        config = VerificationConfig(
            repo="test-org/test-repo",
            workflow_name=None,
            run_id=None,
            token="test_token",
            timeout=300,
            poll_interval=5,
            max_retries=3
        )
        
        with patch('verify_workflow_status.httpx.Client'):
            verifier = WorkflowStatusVerifier(config)
        
        introspector = WorkflowIntrospector(repo="test-org/test-repo")
        
        return {
            "manager": manager,
            "verifier": verifier,
            "introspector": introspector
        }
    
    def test_apply_preset_and_verify(self, integrated_system):
        """Test applying preset and verifying workflow states."""
        manager = integrated_system["manager"]
        verifier = integrated_system["verifier"]
        
        # Apply minimal preset
        with patch('manage_workflows.WorkflowPresets.get_presets') as mock_presets:
            mock_presets.return_value = {
                "minimal": {
                    "features": {
                        "auto_merge": False,
                        "monitoring": False
                    },
                    "workflows": {
                        "testing": {
                            "ci": {"enabled": False},
                            "tests": {"enabled": False}
                        },
                        "deployment": {
                            "deploy": {"enabled": False},
                            "staging": {"enabled": False}
                        }
                    }
                }
            }
            
            with patch('manage_workflows.WorkflowPresets.validate_preset', return_value=True):
                manager.apply_preset("minimal")
        
        # Verify all workflows are disabled
        status = manager.get_workflow_status()
        assert all(not info["enabled"] for info in status.values())
        
        # Mock verification should return no active runs
        verifier._api_request = Mock(return_value={"workflow_runs": []})
        
        for workflow in ["ci", "tests", "deploy", "staging"]:
            runs = verifier.get_workflow_runs(workflow)
            assert len(runs) == 0
    
    def test_cost_budget_impact_on_workflows(self, integrated_system):
        """Test cost budget settings impact on workflow execution."""
        manager = integrated_system["manager"]
        
        # Set restrictive budget
        manager.set_cost_budget(daily=10.0, monthly=300.0)
        
        # In a real system, this would trigger:
        # 1. Disable expensive workflows
        # 2. Reduce parallelism
        # 3. Skip optional steps
        
        assert manager.config["cost_control"]["daily_limit"] == 10.0
        assert manager.config["cost_control"]["monthly_budget"] == 300.0
        
        # Simulate disabling expensive workflows based on budget
        expensive_workflows = ["deploy", "staging"]
        for workflow in expensive_workflows:
            manager.disable_workflow(workflow)
        
        status = manager.get_workflow_status()
        for workflow in expensive_workflows:
            assert not status[workflow]["enabled"]


class TestWorkflowMonitoring:
    """Test monitoring workflow execution across components."""
    
    @pytest.fixture
    def monitoring_system(self):
        """Create monitoring-focused system."""
        config = VerificationConfig(
            repo="test-org/test-repo",
            workflow_name="monitor",
            run_id=None,
            token="test_token",
            timeout=600,
            poll_interval=10,
            max_retries=5
        )
        
        with patch('verify_workflow_status.httpx.Client'):
            verifier = WorkflowStatusVerifier(config)
        
        introspector = WorkflowIntrospector(repo="test-org/test-repo")
        
        return {
            "verifier": verifier,
            "introspector": introspector
        }
    
    def test_monitor_long_running_workflow(self, monitoring_system):
        """Test monitoring long-running workflow execution."""
        verifier = monitoring_system["verifier"]
        introspector = monitoring_system["introspector"]
        
        run_id = 111111
        
        # Simulate workflow progression
        states = [
            ("queued", None, []),
            ("in_progress", None, [
                {"name": "Setup", "status": "completed", "conclusion": "success"}
            ]),
            ("in_progress", None, [
                {"name": "Setup", "status": "completed", "conclusion": "success"},
                {"name": "Build", "status": "in_progress", "conclusion": None}
            ]),
            ("completed", "success", [
                {"name": "Setup", "status": "completed", "conclusion": "success"},
                {"name": "Build", "status": "completed", "conclusion": "success"},
                {"name": "Deploy", "status": "completed", "conclusion": "success"}
            ])
        ]
        
        for i, (status, conclusion, jobs) in enumerate(states):
            # Mock verification state
            verifier._api_request = Mock(return_value={
                "id": run_id,
                "status": status,
                "conclusion": conclusion,
                "name": "Long Pipeline",
                "head_branch": "main",
                "head_sha": "monitor123",
                "created_at": "2024-01-20T13:00:00Z",
                "updated_at": f"2024-01-20T13:{i*5:02d}:00Z",
                "html_url": f"https://github.com/test/repo/actions/runs/{run_id}"
            })
            
            run = verifier.get_workflow_run_by_id(run_id)
            assert run.status == status
            
            # Mock introspection state
            introspector._run_gh_command = Mock(return_value={
                "databaseId": run_id,
                "name": "Long Pipeline",
                "workflowName": "monitor.yml",
                "status": status,
                "conclusion": conclusion,
                "headBranch": "main",
                "headSha": "monitor1",
                "event": "schedule",
                "startedAt": "2024-01-20T13:00:00Z",
                "updatedAt": f"2024-01-20T13:{i*5:02d}:00Z",
                "url": f"https://github.com/test/repo/actions/runs/{run_id}",
                "jobs": [
                    {
                        "name": job["name"],
                        "status": job["status"],
                        "conclusion": job["conclusion"],
                        "startedAt": "2024-01-20T13:00:00Z",
                        "completedAt": f"2024-01-20T13:{i*5:02d}:00Z" if job["status"] == "completed" else None,
                        "steps": []
                    }
                    for job in jobs
                ]
            })
            
            detailed = introspector.get_run_details(run_id)
            assert detailed.status == status
            assert len(detailed.jobs) == len(jobs)
        
        # Final verification
        assert verifier.verify_workflow_success(run)
    
    def test_parallel_workflow_monitoring(self, monitoring_system):
        """Test monitoring multiple workflows in parallel."""
        verifier = monitoring_system["verifier"]
        introspector = monitoring_system["introspector"]
        
        workflow_runs = [
            {"id": 201, "workflow": "ci", "status": "completed", "conclusion": "success"},
            {"id": 202, "workflow": "tests", "status": "in_progress", "conclusion": None},
            {"id": 203, "workflow": "deploy", "status": "completed", "conclusion": "failure"},
            {"id": 204, "workflow": "staging", "status": "queued", "conclusion": None}
        ]
        
        # Mock recent runs
        introspector._run_gh_command = Mock(return_value=[
            {
                "databaseId": run["id"],
                "name": run["workflow"].upper(),
                "workflowName": f"{run['workflow']}.yml",
                "status": run["status"],
                "conclusion": run["conclusion"],
                "headBranch": "main",
                "headSha": f"{run['workflow'][:3]}123",
                "event": "push",
                "startedAt": "2024-01-20T14:00:00Z",
                "updatedAt": "2024-01-20T14:05:00Z",
                "url": f"https://github.com/test/repo/actions/runs/{run['id']}"
            }
            for run in workflow_runs
        ])
        
        runs = introspector.get_recent_runs(limit=10)
        assert len(runs) == 4
        
        # Verify status distribution
        statuses = {run.status for run in runs}
        assert "completed" in statuses
        assert "in_progress" in statuses
        assert "queued" in statuses
        
        # Check conclusions
        completed_runs = [r for r in runs if r.status == "completed"]
        assert any(r.conclusion == "success" for r in completed_runs)
        assert any(r.conclusion == "failure" for r in completed_runs)


class TestWorkflowErrorRecovery:
    """Test error recovery across workflow components."""
    
    @pytest.fixture
    def recovery_system(self, temp_repo):
        """Create system for testing error recovery."""
        manager = WorkflowManager(temp_repo)
        
        config = VerificationConfig(
            repo="test-org/test-repo",
            workflow_name=None,
            run_id=None,
            token="test_token",
            timeout=60,
            poll_interval=5,
            max_retries=3
        )
        
        with patch('verify_workflow_status.httpx.Client'):
            verifier = WorkflowStatusVerifier(config)
        
        introspector = WorkflowIntrospector(repo="test-org/test-repo")
        
        return {
            "manager": manager,
            "verifier": verifier,
            "introspector": introspector
        }
    
    def test_handle_api_failures(self, recovery_system):
        """Test handling API failures across components."""
        verifier = recovery_system["verifier"]
        introspector = recovery_system["introspector"]
        
        # Test verifier handling API error
        verifier.client.get.side_effect = httpx.HTTPStatusError(
            "Rate limited",
            request=Mock(),
            response=Mock(status_code=429, text="API rate limit exceeded")
        )
        
        with pytest.raises(Exception):  # Should raise after retries
            verifier.get_workflow_runs("ci")
        
        # Test introspector handling subprocess error
        with patch('workflow_introspection.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["gh"], stderr="Authentication failed"
            )
            
            result = introspector._run_gh_command(["api", "test"])
            assert result == {}  # Should return empty dict on error
    
    def test_recover_from_corrupted_config(self, recovery_system):
        """Test recovering from corrupted configuration."""
        manager = recovery_system["manager"]
        
        # Corrupt the config file
        config_path = Path(manager.config_file)
        config_path.write_text("invalid: yaml: [[[")
        
        # Create new manager instance - should handle corrupted config
        new_manager = WorkflowManager(manager.repo_path)
        assert new_manager.config == {}
        
        # Should be able to set new config
        new_manager.set_feature("recovery_test", True)
        assert new_manager.config["features"]["recovery_test"] is True
        
        # Verify config is now valid
        saved_config = yaml.safe_load(config_path.read_text())
        assert saved_config["features"]["recovery_test"] is True
    
    def test_timeout_recovery(self, recovery_system):
        """Test recovery from timeout scenarios."""
        verifier = recovery_system["verifier"]
        
        # Create a run that will timeout
        run = WorkflowRun(
            id=666,
            status="in_progress",
            conclusion=None,
            name="Stuck Pipeline",
            head_branch="main",
            head_sha="timeout1",
            created_at="2024-01-20T15:00:00Z",
            updated_at="2024-01-20T15:01:00Z",
            html_url="https://test.url"
        )
        
        # Mock to always return in_progress
        verifier.get_workflow_run_by_id = Mock(return_value=run)
        verifier.config.timeout = 0.1  # Very short timeout
        
        with pytest.raises(Exception) as exc_info:
            verifier.wait_for_completion(run)
        
        assert "timeout" in str(exc_info.value).lower()


class TestWorkflowPerformanceOptimization:
    """Test performance optimization across workflow system."""
    
    def test_batch_workflow_operations(self, temp_repo):
        """Test batch operations for performance."""
        manager = WorkflowManager(temp_repo)
        
        # Batch enable multiple workflows
        workflows_to_enable = ["ci", "tests", "staging", "monitor"]
        
        start_time = datetime.now()
        for workflow in workflows_to_enable:
            manager.enable_workflow(workflow)
        batch_time = (datetime.now() - start_time).total_seconds()
        
        # Verify all enabled
        status = manager.get_workflow_status()
        for workflow in workflows_to_enable:
            assert status[workflow]["enabled"]
        
        # Batch operations should be fast
        assert batch_time < 1.0  # Should complete in under 1 second
    
    def test_cache_api_responses(self):
        """Test caching API responses for performance."""
        config = VerificationConfig(
            repo="test-org/test-repo",
            workflow_name="ci",
            run_id=None,
            token="test_token",
            timeout=300,
            poll_interval=5,
            max_retries=3
        )
        
        with patch('verify_workflow_status.httpx.Client') as mock_client:
            verifier = WorkflowStatusVerifier(config)
            
            # Mock API response
            mock_response = Mock()
            mock_response.json.return_value = {
                "workflow_runs": [{
                    "id": 777,
                    "status": "completed",
                    "conclusion": "success",
                    "name": "CI",
                    "head_branch": "main",
                    "head_sha": "cache123",
                    "created_at": "2024-01-20T16:00:00Z",
                    "updated_at": "2024-01-20T16:05:00Z",
                    "html_url": "https://test.url"
                }]
            }
            verifier.client.get.return_value = mock_response
            
            # Multiple calls to same endpoint
            for _ in range(3):
                runs = verifier.get_workflow_runs("ci")
                assert len(runs) == 1
            
            # In a real implementation, this would use caching
            # and make only one actual API call
            assert verifier.client.get.call_count == 3  # Without cache
    
    def test_parallel_introspection(self):
        """Test parallel workflow introspection."""
        introspector = WorkflowIntrospector(repo="test-org/test-repo")
        
        # Mock multiple workflow runs
        run_ids = [1001, 1002, 1003, 1004, 1005]
        
        with patch('workflow_introspection.subprocess.run') as mock_run:
            # Simulate parallel fetching
            start_time = datetime.now()
            
            for run_id in run_ids:
                mock_run.return_value = Mock(
                    stdout=json.dumps({
                        "databaseId": run_id,
                        "name": f"Run {run_id}",
                        "workflowName": "parallel.yml",
                        "status": "completed",
                        "conclusion": "success",
                        "headBranch": "main",
                        "headSha": f"parallel{run_id}",
                        "event": "push",
                        "startedAt": "2024-01-20T17:00:00Z",
                        "updatedAt": "2024-01-20T17:05:00Z",
                        "url": f"https://test.url/{run_id}",
                        "jobs": []
                    })
                )
                
                run = introspector.get_run_details(run_id)
                assert run.id == run_id
            
            fetch_time = (datetime.now() - start_time).total_seconds()
            
            # Should be fast even for multiple runs
            assert fetch_time < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])