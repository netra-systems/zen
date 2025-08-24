#!/usr/bin/env python3
"""
L4 Integration Tests for GitHub Workflow Introspection System
Tests workflow_introspection.py with complex scenarios and gh CLI integration
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Add scripts directory to path

from workflow_introspection import (
    OutputFormatter,
    WorkflowIntrospector,
    WorkflowJob,
    WorkflowRun,
    WorkflowStep,
)


class TestWorkflowDataClasses:
    """Test workflow data classes."""
    
    def test_workflow_step_creation(self):
        """Test creating WorkflowStep instance."""
        step = WorkflowStep(
            name="Run tests",
            conclusion="success",
            started_at="2024-01-20T10:00:00Z",
            completed_at="2024-01-20T10:05:00Z"
        )
        
        assert step.name == "Run tests"
        assert step.conclusion == "success"
        assert step.started_at == "2024-01-20T10:00:00Z"
        assert step.completed_at == "2024-01-20T10:05:00Z"
    
    def test_workflow_step_optional_fields(self):
        """Test WorkflowStep with optional fields."""
        step = WorkflowStep(
            name="Pending step",
            conclusion=None,
            started_at=None,
            completed_at=None
        )
        
        assert step.name == "Pending step"
        assert step.conclusion is None
        assert step.started_at is None
        assert step.completed_at is None
    
    def test_workflow_job_creation(self):
        """Test creating WorkflowJob instance."""
        steps = [
            WorkflowStep("Setup", "success", "2024-01-20T10:00:00Z", "2024-01-20T10:01:00Z"),
            WorkflowStep("Build", "success", "2024-01-20T10:01:00Z", "2024-01-20T10:03:00Z"),
            WorkflowStep("Test", "failure", "2024-01-20T10:03:00Z", "2024-01-20T10:05:00Z")
        ]
        
        job = WorkflowJob(
            name="Build and Test",
            status="completed",
            conclusion="failure",
            started_at="2024-01-20T10:00:00Z",
            completed_at="2024-01-20T10:05:00Z",
            steps=steps
        )
        
        assert job.name == "Build and Test"
        assert job.status == "completed"
        assert job.conclusion == "failure"
        assert len(job.steps) == 3
        assert job.steps[0].name == "Setup"
        assert job.steps[2].conclusion == "failure"
    
    def test_workflow_run_creation(self):
        """Test creating WorkflowRun instance."""
        jobs = [
            WorkflowJob(
                name="Test Job",
                status="completed",
                conclusion="success",
                started_at="2024-01-20T10:00:00Z",
                completed_at="2024-01-20T10:05:00Z",
                steps=[]
            )
        ]
        
        run = WorkflowRun(
            id=123456,
            name="CI Pipeline",
            workflow_name="ci.yml",
            status="completed",
            conclusion="success",
            head_branch="main",
            head_sha="abc123def",
            event="push",
            started_at="2024-01-20T10:00:00Z",
            updated_at="2024-01-20T10:05:00Z",
            html_url="https://github.com/org/repo/actions/runs/123456",
            jobs=jobs
        )
        
        assert run.id == 123456
        assert run.name == "CI Pipeline"
        assert run.workflow_name == "ci.yml"
        assert run.event == "push"
        assert len(run.jobs) == 1
        assert run.jobs[0].name == "Test Job"


class TestWorkflowIntrospector:
    """Test WorkflowIntrospector class."""
    
    @pytest.fixture
    def introspector(self):
        """Create WorkflowIntrospector instance."""
        return WorkflowIntrospector(repo="test-org/test-repo")
    
    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for gh commands."""
        # Mock: Component isolation for testing without external dependencies
        with patch('workflow_introspection.subprocess.run') as mock_run:
            yield mock_run
    
    def test_init_with_repo(self):
        """Test initializing with repository."""
        introspector = WorkflowIntrospector(repo="owner/repo")
        assert introspector.repo == "owner/repo"
    
    def test_init_without_repo(self):
        """Test initializing without repository."""
        introspector = WorkflowIntrospector()
        assert introspector.repo is None
    
    def test_run_gh_command_success(self, introspector, mock_subprocess_run):
        """Test successful gh command execution."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = '{"test": "data"}'
        mock_subprocess_run.return_value = mock_result
        
        result = introspector._run_gh_command(["api", "test"])
        
        assert result == {"test": "data"}
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ["gh", "api", "test", "--repo", "test-org/test-repo"]
    
    def test_run_gh_command_error(self, introspector, mock_subprocess_run):
        """Test gh command execution with error."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            1, ["gh"], stderr="Error message"
        )
        
        result = introspector._run_gh_command(["api", "test"])
        
        assert result == {}
    
    def test_run_gh_command_invalid_json(self, introspector, mock_subprocess_run):
        """Test gh command with invalid JSON response."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = "Invalid JSON"
        mock_subprocess_run.return_value = mock_result
        
        result = introspector._run_gh_command(["api", "test"])
        
        assert result == {}
    
    def test_list_workflows(self, introspector, mock_subprocess_run):
        """Test listing available workflows."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = (
            "CI Pipeline\tactive\t123456\n"
            "Deploy\tdisabled\t789012\n"
            "Tests\tactive\t345678\n"
        )
        mock_subprocess_run.return_value = mock_result
        
        workflows = introspector.list_workflows(limit=10)
        
        assert len(workflows) == 3
        assert workflows[0] == {"name": "CI Pipeline", "state": "active", "id": "123456"}
        assert workflows[1] == {"name": "Deploy", "state": "disabled", "id": "789012"}
        assert workflows[2] == {"name": "Tests", "state": "active", "id": "345678"}
        
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ["gh", "workflow", "list", "--limit", "10"]
    
    def test_list_workflows_empty(self, introspector, mock_subprocess_run):
        """Test listing workflows with no results."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = ""
        mock_subprocess_run.return_value = mock_result
        
        workflows = introspector.list_workflows()
        
        assert workflows == []
    
    def test_get_recent_runs(self, introspector):
        """Test getting recent workflow runs."""
        mock_data = [
            {
                "databaseId": 111,
                "name": "CI Run 1",
                "workflowName": "CI",
                "status": "completed",
                "conclusion": "success",
                "headBranch": "main",
                "headSha": "abc123def456789",
                "event": "push",
                "startedAt": "2024-01-20T10:00:00Z",
                "updatedAt": "2024-01-20T10:05:00Z",
                "url": "https://github.com/test/repo/actions/runs/111"
            },
            {
                "databaseId": 222,
                "name": "CI Run 2",
                "workflowName": "CI",
                "status": "in_progress",
                "conclusion": None,
                "headBranch": "feature",
                "headSha": "def456ghi789012",
                "event": "pull_request",
                "startedAt": "2024-01-20T11:00:00Z",
                "updatedAt": "2024-01-20T11:01:00Z",
                "url": "https://github.com/test/repo/actions/runs/222"
            }
        ]
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        runs = introspector.get_recent_runs(limit=5, workflow="CI")
        
        assert len(runs) == 2
        assert runs[0].id == 111
        assert runs[0].status == "completed"
        assert runs[0].conclusion == "success"
        assert runs[0].head_sha == "abc123de"  # Should be truncated
        assert runs[1].id == 222
        assert runs[1].status == "in_progress"
        assert runs[1].conclusion is None
        
        introspector._run_gh_command.assert_called_once()
        call_args = introspector._run_gh_command.call_args[0][0]
        assert "--limit" in call_args
        assert "5" in call_args
        assert "--workflow" in call_args
        assert "CI" in call_args
    
    def test_get_run_details(self, introspector):
        """Test getting detailed run information."""
        mock_data = {
            "databaseId": 333,
            "name": "Full Pipeline",
            "workflowName": "pipeline.yml",
            "status": "completed",
            "conclusion": "success",
            "headBranch": "main",
            "headSha": "xyz789abc123def",
            "event": "push",
            "startedAt": "2024-01-20T12:00:00Z",
            "updatedAt": "2024-01-20T12:10:00Z",
            "url": "https://github.com/test/repo/actions/runs/333",
            "jobs": [
                {
                    "name": "Build",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T12:00:00Z",
                    "completedAt": "2024-01-20T12:03:00Z",
                    "steps": [
                        {
                            "name": "Checkout",
                            "conclusion": "success",
                            "startedAt": "2024-01-20T12:00:00Z",
                            "completedAt": "2024-01-20T12:00:30Z"
                        },
                        {
                            "name": "Build application",
                            "conclusion": "success",
                            "startedAt": "2024-01-20T12:00:30Z",
                            "completedAt": "2024-01-20T12:03:00Z"
                        }
                    ]
                },
                {
                    "name": "Test",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T12:03:00Z",
                    "completedAt": "2024-01-20T12:08:00Z",
                    "steps": [
                        {
                            "name": "Run unit tests",
                            "conclusion": "success",
                            "startedAt": "2024-01-20T12:03:00Z",
                            "completedAt": "2024-01-20T12:05:00Z"
                        },
                        {
                            "name": "Run integration tests",
                            "conclusion": "success",
                            "startedAt": "2024-01-20T12:05:00Z",
                            "completedAt": "2024-01-20T12:08:00Z"
                        }
                    ]
                }
            ]
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(333)
        
        assert run is not None
        assert run.id == 333
        assert run.name == "Full Pipeline"
        assert len(run.jobs) == 2
        
        # Check first job
        assert run.jobs[0].name == "Build"
        assert run.jobs[0].conclusion == "success"
        assert len(run.jobs[0].steps) == 2
        assert run.jobs[0].steps[0].name == "Checkout"
        
        # Check second job
        assert run.jobs[1].name == "Test"
        assert len(run.jobs[1].steps) == 2
        assert run.jobs[1].steps[1].name == "Run integration tests"
    
    def test_get_run_details_not_found(self, introspector):
        """Test getting details for non-existent run."""
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value={})
        
        run = introspector.get_run_details(999999)
        
        assert run is None
    
    def test_get_run_logs(self, introspector, mock_subprocess_run):
        """Test getting workflow run logs."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = "Log line 1\nLog line 2\nLog line 3"
        mock_subprocess_run.return_value = mock_result
        
        logs = introspector.get_run_logs(444)
        
        assert logs == "Log line 1\nLog line 2\nLog line 3"
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ["gh", "run", "view", "444", "--log"]
    
    def test_get_run_logs_for_job(self, introspector, mock_subprocess_run):
        """Test getting logs for specific job."""
        # Mock: Generic component isolation for controlled unit testing
        mock_result = Mock()
        mock_result.stdout = "Job specific logs"
        mock_subprocess_run.return_value = mock_result
        
        logs = introspector.get_run_logs(555, job_name="Build")
        
        assert logs == "Job specific logs"
        call_args = mock_subprocess_run.call_args[0][0]
        assert "--job" in call_args
        assert "Build" in call_args
    
    def test_get_workflow_outputs(self, introspector):
        """Test getting workflow outputs."""
        mock_data = {
            "outputs": {"version": "1.2.3", "artifact_url": "https://artifacts.url"},
            "artifacts_url": "https://api.github.com/repos/test/repo/actions/runs/666/artifacts",
            "logs_url": "https://api.github.com/repos/test/repo/actions/runs/666/logs",
            "check_suite_url": "https://api.github.com/repos/test/repo/check-suites/789"
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        outputs = introspector.get_workflow_outputs(666)
        
        assert outputs["outputs"] == {"version": "1.2.3", "artifact_url": "https://artifacts.url"}
        assert outputs["artifacts_url"] == mock_data["artifacts_url"]
        assert outputs["logs_url"] == mock_data["logs_url"]
        assert outputs["check_suite_url"] == mock_data["check_suite_url"]
    
    def test_watch_run(self, introspector, mock_subprocess_run):
        """Test watching a workflow run."""
        introspector.watch_run(777)
        
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args[0][0]
        assert call_args == ["gh", "run", "watch", "777"]


class TestOutputFormatter:
    """Test OutputFormatter class."""
    
    @pytest.fixture
    def formatter(self):
        """Create OutputFormatter instance."""
        from rich.console import Console
        console = Console()
        return OutputFormatter(console)
    
    def test_get_status_style(self, formatter):
        """Test getting status style."""
        assert formatter._get_status_style("completed", "success") == "green"
        assert formatter._get_status_style("completed", "failure") == "red"
        assert formatter._get_status_style("completed", "cancelled") == "yellow"
        assert formatter._get_status_style("completed", None) == "dim"
        assert formatter._get_status_style("in_progress", None) == "yellow"
        assert formatter._get_status_style("queued", None) == "blue"
        assert formatter._get_status_style("unknown", None) == "dim"
    
    def test_display_workflows_table(self, formatter, capsys):
        """Test displaying workflows table."""
        workflows = [
            {"name": "CI", "state": "active", "id": "111"},
            {"name": "Deploy", "state": "disabled", "id": "222"},
            {"name": "Tests", "state": "active", "id": "333"}
        ]
        
        formatter.display_workflows_table(workflows)
        
        captured = capsys.readouterr()
        assert "CI" in captured.out
        assert "Deploy" in captured.out
        assert "Tests" in captured.out
        assert "active" in captured.out
        assert "disabled" in captured.out
    
    def test_display_runs_table(self, formatter, capsys):
        """Test displaying runs table."""
        runs = [
            WorkflowRun(
                id=100,
                name="CI Run",
                workflow_name="Continuous Integration Pipeline",
                status="completed",
                conclusion="success",
                head_branch="main",
                head_sha="abc123",
                event="push",
                started_at="2024-01-20T10:00:00Z",
                updated_at="2024-01-20T10:05:00Z",
                html_url="https://test.url"
            ),
            WorkflowRun(
                id=200,
                name="Deploy Run",
                workflow_name="Deployment Pipeline",
                status="in_progress",
                conclusion=None,
                head_branch="release",
                head_sha="def456",
                event="workflow_dispatch",
                started_at="2024-01-20T11:00:00Z",
                updated_at="2024-01-20T11:01:00Z",
                html_url="https://test.url"
            )
        ]
        
        formatter.display_runs_table(runs)
        
        captured = capsys.readouterr()
        assert "100" in captured.out
        assert "200" in captured.out
        assert "push" in captured.out
        assert "workflow_dispatch" in captured.out
    
    def test_display_run_details(self, formatter, capsys):
        """Test displaying detailed run information."""
        jobs = [
            WorkflowJob(
                name="Build Job",
                status="completed",
                conclusion="success",
                started_at="2024-01-20T12:00:00Z",
                completed_at="2024-01-20T12:05:00Z",
                steps=[
                    WorkflowStep("Setup", "success", None, None),
                    WorkflowStep("Build", "success", None, None),
                    WorkflowStep("Package", "success", None, None)
                ]
            ),
            WorkflowJob(
                name="Test Job",
                status="completed",
                conclusion="failure",
                started_at="2024-01-20T12:05:00Z",
                completed_at="2024-01-20T12:10:00Z",
                steps=[
                    WorkflowStep("Setup", "success", None, None),
                    WorkflowStep("Unit Tests", "success", None, None),
                    WorkflowStep("Integration Tests", "failure", None, None)
                ]
            )
        ]
        
        run = WorkflowRun(
            id=300,
            name="Full Pipeline",
            workflow_name="pipeline.yml",
            status="completed",
            conclusion="failure",
            head_branch="feature",
            head_sha="xyz789",
            event="pull_request",
            started_at="2024-01-20T12:00:00Z",
            updated_at="2024-01-20T12:10:00Z",
            html_url="https://test.url/300",
            jobs=jobs
        )
        
        formatter.display_run_details(run)
        
        captured = capsys.readouterr()
        assert "300" in captured.out
        assert "Full Pipeline" in captured.out
        assert "Build Job" in captured.out
        assert "Test Job" in captured.out
        assert "Integration Tests" in captured.out
    
    def test_display_outputs(self, formatter, capsys):
        """Test displaying workflow outputs."""
        outputs = {
            "outputs": {"version": "1.2.3", "status": "deployed"},
            "artifacts_url": "https://artifacts.url",
            "logs_url": "https://logs.url"
        }
        
        formatter.display_outputs(outputs)
        
        captured = capsys.readouterr()
        assert "1.2.3" in captured.out
        assert "deployed" in captured.out
        assert "https://artifacts.url" in captured.out
        assert "https://logs.url" in captured.out
    
    def test_display_outputs_empty(self, formatter, capsys):
        """Test displaying empty outputs."""
        outputs = {}
        
        formatter.display_outputs(outputs)
        
        captured = capsys.readouterr()
        assert "No workflow outputs available" in captured.out


class TestComplexWorkflowScenarios:
    """Test complex real-world workflow scenarios."""
    
    @pytest.fixture
    def introspector(self):
        """Create introspector for complex scenarios."""
        return WorkflowIntrospector(repo="complex-org/complex-repo")
    
    def test_parallel_job_execution(self, introspector):
        """Test handling parallel job execution."""
        mock_data = {
            "databaseId": 1000,
            "name": "Parallel Pipeline",
            "workflowName": "parallel.yml",
            "status": "in_progress",
            "conclusion": None,
            "headBranch": "main",
            "headSha": "parallel123",
            "event": "push",
            "startedAt": "2024-01-20T13:00:00Z",
            "updatedAt": "2024-01-20T13:05:00Z",
            "url": "https://test.url",
            "jobs": [
                {
                    "name": "Linux Build",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T13:00:00Z",
                    "completedAt": "2024-01-20T13:03:00Z",
                    "steps": []
                },
                {
                    "name": "Windows Build",
                    "status": "in_progress",
                    "conclusion": None,
                    "startedAt": "2024-01-20T13:00:00Z",
                    "completedAt": None,
                    "steps": []
                },
                {
                    "name": "macOS Build",
                    "status": "completed",
                    "conclusion": "failure",
                    "startedAt": "2024-01-20T13:00:00Z",
                    "completedAt": "2024-01-20T13:04:00Z",
                    "steps": []
                }
            ]
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(1000)
        
        assert run.status == "in_progress"
        assert len(run.jobs) == 3
        
        # Check parallel job statuses
        linux_job = next(j for j in run.jobs if j.name == "Linux Build")
        assert linux_job.conclusion == "success"
        
        windows_job = next(j for j in run.jobs if j.name == "Windows Build")
        assert windows_job.status == "in_progress"
        assert windows_job.conclusion is None
        
        macos_job = next(j for j in run.jobs if j.name == "macOS Build")
        assert macos_job.conclusion == "failure"
    
    def test_matrix_strategy_jobs(self, introspector):
        """Test handling matrix strategy jobs."""
        mock_data = {
            "databaseId": 2000,
            "name": "Matrix Build",
            "workflowName": "matrix.yml",
            "status": "completed",
            "conclusion": "success",
            "headBranch": "main",
            "headSha": "matrix456",
            "event": "push",
            "startedAt": "2024-01-20T14:00:00Z",
            "updatedAt": "2024-01-20T14:15:00Z",
            "url": "https://test.url",
            "jobs": [
                {
                    "name": "test (ubuntu-latest, 3.8)",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T14:00:00Z",
                    "completedAt": "2024-01-20T14:05:00Z",
                    "steps": []
                },
                {
                    "name": "test (ubuntu-latest, 3.9)",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T14:00:00Z",
                    "completedAt": "2024-01-20T14:06:00Z",
                    "steps": []
                },
                {
                    "name": "test (windows-latest, 3.8)",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T14:00:00Z",
                    "completedAt": "2024-01-20T14:07:00Z",
                    "steps": []
                },
                {
                    "name": "test (windows-latest, 3.9)",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T14:00:00Z",
                    "completedAt": "2024-01-20T14:08:00Z",
                    "steps": []
                }
            ]
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(2000)
        
        assert len(run.jobs) == 4
        assert all(j.conclusion == "success" for j in run.jobs)
        
        # Check matrix combinations
        job_names = [j.name for j in run.jobs]
        assert "test (ubuntu-latest, 3.8)" in job_names
        assert "test (ubuntu-latest, 3.9)" in job_names
        assert "test (windows-latest, 3.8)" in job_names
        assert "test (windows-latest, 3.9)" in job_names
    
    def test_workflow_with_retries(self, introspector):
        """Test handling workflow with job retries."""
        mock_data = {
            "databaseId": 3000,
            "name": "Flaky Tests",
            "workflowName": "tests.yml",
            "status": "completed",
            "conclusion": "success",
            "headBranch": "main",
            "headSha": "retry789",
            "event": "push",
            "startedAt": "2024-01-20T15:00:00Z",
            "updatedAt": "2024-01-20T15:20:00Z",
            "url": "https://test.url",
            "jobs": [
                {
                    "name": "integration-tests",
                    "status": "completed",
                    "conclusion": "success",
                    "startedAt": "2024-01-20T15:10:00Z",  # Later start time indicates retry
                    "completedAt": "2024-01-20T15:15:00Z",
                    "steps": [
                        {
                            "name": "Run tests",
                            "conclusion": "success",
                            "startedAt": "2024-01-20T15:10:00Z",
                            "completedAt": "2024-01-20T15:15:00Z"
                        }
                    ]
                }
            ]
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(3000)
        
        # Check that retry succeeded
        assert run.conclusion == "success"
        assert run.jobs[0].conclusion == "success"
        
        # The job started 10 minutes after workflow (indicates retry)
        workflow_start = datetime.fromisoformat(run.started_at.replace('Z', '+00:00'))
        job_start = datetime.fromisoformat(run.jobs[0].started_at.replace('Z', '+00:00'))
        assert (job_start - workflow_start).total_seconds() == 600  # 10 minutes
    
    def test_large_workflow_with_many_steps(self, introspector):
        """Test handling large workflow with many steps."""
        # Create job with many steps
        steps = []
        for i in range(50):
            steps.append({
                "name": f"Step {i+1}",
                "conclusion": "success" if i < 49 else "failure",
                "startedAt": f"2024-01-20T16:{i:02d}:00Z",
                "completedAt": f"2024-01-20T16:{i:02d}:30Z"
            })
        
        mock_data = {
            "databaseId": 4000,
            "name": "Large Pipeline",
            "workflowName": "large.yml",
            "status": "completed",
            "conclusion": "failure",
            "headBranch": "main",
            "headSha": "large123",
            "event": "push",
            "startedAt": "2024-01-20T16:00:00Z",
            "updatedAt": "2024-01-20T16:50:00Z",
            "url": "https://test.url",
            "jobs": [
                {
                    "name": "Complex Job",
                    "status": "completed",
                    "conclusion": "failure",
                    "startedAt": "2024-01-20T16:00:00Z",
                    "completedAt": "2024-01-20T16:50:00Z",
                    "steps": steps
                }
            ]
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(4000)
        
        assert len(run.jobs[0].steps) == 50
        assert run.jobs[0].steps[48].conclusion == "success"
        assert run.jobs[0].steps[49].conclusion == "failure"
        assert run.conclusion == "failure"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def introspector(self):
        """Create introspector for error testing."""
        return WorkflowIntrospector()
    
    def test_handle_malformed_workflow_data(self, introspector):
        """Test handling malformed workflow data."""
        mock_data = [
            {
                "databaseId": 5000,
                "name": "Malformed",
                # Missing required fields
                "status": "completed"
            }
        ]
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        
        # Should handle gracefully with KeyError
        with pytest.raises(KeyError):
            introspector.get_recent_runs()
    
    def test_handle_empty_job_list(self, introspector):
        """Test handling workflow with no jobs."""
        mock_data = {
            "databaseId": 6000,
            "name": "No Jobs",
            "workflowName": "empty.yml",
            "status": "completed",
            "conclusion": "success",
            "headBranch": "main",
            "headSha": "empty123",
            "event": "push",
            "startedAt": "2024-01-20T17:00:00Z",
            "updatedAt": "2024-01-20T17:01:00Z",
            "url": "https://test.url",
            "jobs": []
        }
        
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(return_value=mock_data)
        run = introspector.get_run_details(6000)
        
        assert run is not None
        assert run.jobs == []
    
    def test_handle_network_timeout(self, introspector):
        """Test handling network timeout."""
        # Mock: Component isolation for controlled unit testing
        introspector._run_gh_command = Mock(side_effect=subprocess.TimeoutExpired(
            ["gh", "api"], timeout=30
        ))
        
        with pytest.raises(subprocess.TimeoutExpired):
            introspector.get_recent_runs()
    
    def test_handle_rate_limiting(self, introspector):
        """Test handling GitHub API rate limiting."""
        mock_error = subprocess.CalledProcessError(
            1,
            ["gh"],
            stderr="API rate limit exceeded"
        )
        
        # Mock: Component isolation for testing without external dependencies
        with patch('workflow_introspection.subprocess.run', side_effect=mock_error):
            result = introspector._run_gh_command(["api", "test"])
            assert result == {}
    
    def test_handle_authentication_error(self, introspector):
        """Test handling authentication errors."""
        mock_error = subprocess.CalledProcessError(
            1,
            ["gh"],
            stderr="Authentication required"
        )
        
        # Mock: Component isolation for testing without external dependencies
        with patch('workflow_introspection.subprocess.run', side_effect=mock_error):
            result = introspector._run_gh_command(["api", "test"])
            assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])