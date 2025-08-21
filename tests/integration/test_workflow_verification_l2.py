#!/usr/bin/env python3
"""
L2 Integration Tests for GitHub Workflow Verification System
Tests verify_workflow_status.py with mocked API responses
"""

import json
import os
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest
import httpx
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from verify_workflow_status import (
    WorkflowRun,
    VerificationConfig,
    GitHubAPIError,
    WorkflowStatusVerifier,
    CLIHandler,
    OutputFormatter,
    create_config_from_args
)


class TestWorkflowRun:
    """Test WorkflowRun dataclass."""
    
    def test_workflow_run_creation(self):
        """Test creating WorkflowRun instance."""
        run = WorkflowRun(
            id=123456,
            status="completed",
            conclusion="success",
            name="CI Pipeline",
            head_branch="main",
            head_sha="abc123def",
            created_at="2024-01-20T10:00:00Z",
            updated_at="2024-01-20T10:05:00Z",
            html_url="https://github.com/org/repo/actions/runs/123456"
        )
        
        assert run.id == 123456
        assert run.status == "completed"
        assert run.conclusion == "success"
        assert run.name == "CI Pipeline"
        assert run.head_branch == "main"
        assert run.head_sha == "abc123def"
    
    def test_workflow_run_optional_conclusion(self):
        """Test WorkflowRun with optional conclusion field."""
        run = WorkflowRun(
            id=789,
            status="in_progress",
            conclusion=None,
            name="Test Suite",
            head_branch="feature",
            head_sha="xyz789",
            created_at="2024-01-20T11:00:00Z",
            updated_at="2024-01-20T11:01:00Z",
            html_url="https://github.com/org/repo/actions/runs/789"
        )
        
        assert run.conclusion is None
        assert run.status == "in_progress"


class TestVerificationConfig:
    """Test VerificationConfig dataclass."""
    
    def test_config_creation(self):
        """Test creating VerificationConfig instance."""
        config = VerificationConfig(
            repo="owner/repo",
            workflow_name="ci.yml",
            run_id=123456,
            token="github_token_123",
            timeout=1800,
            poll_interval=30,
            max_retries=3
        )
        
        assert config.repo == "owner/repo"
        assert config.workflow_name == "ci.yml"
        assert config.run_id == 123456
        assert config.token == "github_token_123"
        assert config.timeout == 1800
        assert config.poll_interval == 30
        assert config.max_retries == 3
    
    def test_config_optional_fields(self):
        """Test VerificationConfig with optional fields."""
        config = VerificationConfig(
            repo="owner/repo",
            workflow_name=None,
            run_id=None,
            token="token",
            timeout=600,
            poll_interval=10,
            max_retries=5
        )
        
        assert config.workflow_name is None
        assert config.run_id is None


class TestGitHubAPIError:
    """Test GitHubAPIError exception."""
    
    def test_error_with_status_code(self):
        """Test GitHubAPIError with status code."""
        error = GitHubAPIError("API rate limit exceeded", status_code=429)
        
        assert str(error) == "API rate limit exceeded"
        assert error.status_code == 429
    
    def test_error_without_status_code(self):
        """Test GitHubAPIError without status code."""
        error = GitHubAPIError("Network error")
        
        assert str(error) == "Network error"
        assert error.status_code is None


class TestWorkflowStatusVerifier:
    """Test WorkflowStatusVerifier class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return VerificationConfig(
            repo="test-org/test-repo",
            workflow_name="test-workflow",
            run_id=None,
            token="test_token_123",
            timeout=300,
            poll_interval=5,
            max_retries=3
        )
    
    @pytest.fixture
    def verifier(self, mock_config):
        """Create WorkflowStatusVerifier instance."""
        with patch('verify_workflow_status.httpx.Client'):
            return WorkflowStatusVerifier(mock_config)
    
    def test_create_client(self, mock_config):
        """Test HTTP client creation with proper headers."""
        with patch('verify_workflow_status.httpx.Client') as mock_client:
            verifier = WorkflowStatusVerifier(mock_config)
            
            mock_client.assert_called_once()
            call_args = mock_client.call_args
            
            assert call_args[1]['base_url'] == "https://api.github.com"
            assert call_args[1]['headers']['Authorization'] == "token test_token_123"
            assert call_args[1]['headers']['Accept'] == "application/vnd.github.v3+json"
            assert call_args[1]['timeout'] == 30.0
    
    def test_api_request_success(self, verifier):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        verifier.client.get.return_value = mock_response
        
        result = verifier._api_request("/repos/test/endpoint")
        
        assert result == {"status": "success"}
        verifier.client.get.assert_called_once_with("/repos/test/endpoint")
    
    def test_api_request_http_error(self, verifier):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        # Mock the _api_request method directly to bypass retry logic
        with patch.object(verifier, '_api_request') as mock_api:
            mock_api.side_effect = GitHubAPIError(
                "API request failed: 404 Not Found",
                status_code=404
            )
            
            with pytest.raises(GitHubAPIError) as exc_info:
                verifier._api_request("/invalid/endpoint")
            
            assert exc_info.value.status_code == 404
            assert "404" in str(exc_info.value)
    
    def test_get_workflow_runs(self, verifier):
        """Test getting workflow runs by name."""
        mock_data = {
            "workflow_runs": [
                {
                    "id": 12345,
                    "status": "completed",
                    "conclusion": "success",
                    "name": "CI",
                    "head_branch": "main",
                    "head_sha": "abc123def456",
                    "created_at": "2024-01-20T10:00:00Z",
                    "updated_at": "2024-01-20T10:05:00Z",
                    "html_url": "https://github.com/test/repo/actions/runs/12345"
                },
                {
                    "id": 67890,
                    "status": "in_progress",
                    "conclusion": None,
                    "name": "CI",
                    "head_branch": "feature",
                    "head_sha": "def456ghi789",
                    "created_at": "2024-01-20T11:00:00Z",
                    "updated_at": "2024-01-20T11:01:00Z",
                    "html_url": "https://github.com/test/repo/actions/runs/67890"
                }
            ]
        }
        
        verifier._api_request = Mock(return_value=mock_data)
        runs = verifier.get_workflow_runs("ci")
        
        assert len(runs) == 2
        assert runs[0].id == 12345
        assert runs[0].status == "completed"
        assert runs[0].conclusion == "success"
        assert runs[1].id == 67890
        assert runs[1].status == "in_progress"
        assert runs[1].conclusion is None
    
    def test_get_workflow_run_by_id(self, verifier):
        """Test getting specific workflow run by ID."""
        mock_data = {
            "id": 99999,
            "status": "completed",
            "conclusion": "failure",
            "name": "Deploy",
            "head_branch": "release",
            "head_sha": "xyz789abc123",
            "created_at": "2024-01-20T12:00:00Z",
            "updated_at": "2024-01-20T12:10:00Z",
            "html_url": "https://github.com/test/repo/actions/runs/99999"
        }
        
        verifier._api_request = Mock(return_value=mock_data)
        run = verifier.get_workflow_run_by_id(99999)
        
        assert run.id == 99999
        assert run.status == "completed"
        assert run.conclusion == "failure"
        assert run.name == "Deploy"
        assert run.head_sha == "xyz789ab"  # Should be truncated to 8 chars
    
    def test_wait_for_completion_success(self, verifier):
        """Test waiting for workflow completion - success case."""
        initial_run = WorkflowRun(
            id=111,
            status="in_progress",
            conclusion=None,
            name="Test",
            head_branch="main",
            head_sha="abc123",
            created_at="2024-01-20T13:00:00Z",
            updated_at="2024-01-20T13:01:00Z",
            html_url="https://test.url"
        )
        
        completed_run = WorkflowRun(
            id=111,
            status="completed",
            conclusion="success",
            name="Test",
            head_branch="main",
            head_sha="abc123",
            created_at="2024-01-20T13:00:00Z",
            updated_at="2024-01-20T13:05:00Z",
            html_url="https://test.url"
        )
        
        verifier.get_workflow_run_by_id = Mock(
            side_effect=[initial_run, initial_run, completed_run]
        )
        
        result = verifier.wait_for_completion(initial_run)
        
        assert result.status == "completed"
        assert result.conclusion == "success"
        assert verifier.get_workflow_run_by_id.call_count == 3
    
    def test_wait_for_completion_timeout(self, verifier):
        """Test waiting for workflow completion - timeout case."""
        verifier.config.timeout = 0.1  # Very short timeout
        
        running_run = WorkflowRun(
            id=222,
            status="in_progress",
            conclusion=None,
            name="LongTest",
            head_branch="main",
            head_sha="def456",
            created_at="2024-01-20T14:00:00Z",
            updated_at="2024-01-20T14:01:00Z",
            html_url="https://test.url"
        )
        
        verifier.get_workflow_run_by_id = Mock(return_value=running_run)
        
        with pytest.raises(GitHubAPIError) as exc_info:
            verifier.wait_for_completion(running_run)
        
        assert "timeout" in str(exc_info.value).lower()
    
    def test_verify_workflow_success(self, verifier):
        """Test verifying workflow success."""
        success_run = WorkflowRun(
            id=333,
            status="completed",
            conclusion="success",
            name="CI",
            head_branch="main",
            head_sha="ghi789",
            created_at="2024-01-20T15:00:00Z",
            updated_at="2024-01-20T15:05:00Z",
            html_url="https://test.url"
        )
        
        failure_run = WorkflowRun(
            id=444,
            status="completed",
            conclusion="failure",
            name="CI",
            head_branch="main",
            head_sha="jkl012",
            created_at="2024-01-20T16:00:00Z",
            updated_at="2024-01-20T16:05:00Z",
            html_url="https://test.url"
        )
        
        in_progress_run = WorkflowRun(
            id=555,
            status="in_progress",
            conclusion=None,
            name="CI",
            head_branch="main",
            head_sha="mno345",
            created_at="2024-01-20T17:00:00Z",
            updated_at="2024-01-20T17:01:00Z",
            html_url="https://test.url"
        )
        
        assert verifier.verify_workflow_success(success_run) is True
        assert verifier.verify_workflow_success(failure_run) is False
        assert verifier.verify_workflow_success(in_progress_run) is False


class TestCLIHandler:
    """Test CLIHandler class."""
    
    @pytest.fixture
    def cli_handler(self):
        """Create CLIHandler instance."""
        return CLIHandler()
    
    def test_parse_args_basic(self, cli_handler):
        """Test parsing basic command-line arguments."""
        test_args = [
            "--repo", "owner/repo",
            "--run-id", "123456"
        ]
        
        with patch('sys.argv', ['verify_workflow_status.py'] + test_args):
            args = cli_handler.parse_args()
        
        assert args.repo == "owner/repo"
        assert args.run_id == 123456
        assert args.workflow_name is None
        assert args.wait_for_completion is False
    
    def test_parse_args_with_workflow(self, cli_handler):
        """Test parsing arguments with workflow name."""
        test_args = [
            "--repo", "test/repo",
            "--workflow-name", "deploy",
            "--wait-for-completion",
            "--timeout", "600",
            "--poll-interval", "10"
        ]
        
        with patch('sys.argv', ['verify_workflow_status.py'] + test_args):
            args = cli_handler.parse_args()
        
        assert args.repo == "test/repo"
        assert args.workflow_name == "deploy"
        assert args.wait_for_completion is True
        assert args.timeout == 600
        assert args.poll_interval == 10
    
    def test_validate_args_valid(self, cli_handler):
        """Test validating valid arguments."""
        args = Mock()
        args.run_id = 123
        args.workflow_name = None
        args.wait_for_completion = False
        
        # Should not raise
        cli_handler.validate_args(args)
    
    def test_validate_args_missing_identifier(self, cli_handler):
        """Test validating arguments with missing identifier."""
        args = Mock()
        args.run_id = None
        args.workflow_name = None
        args.wait_for_completion = False
        
        with pytest.raises(ValueError) as exc_info:
            cli_handler.validate_args(args)
        
        assert "run-id or --workflow-name" in str(exc_info.value)
    
    def test_validate_args_wait_without_workflow(self, cli_handler):
        """Test validating wait flag without workflow name."""
        args = Mock()
        args.run_id = 123
        args.workflow_name = None
        args.wait_for_completion = True
        
        with pytest.raises(ValueError) as exc_info:
            cli_handler.validate_args(args)
        
        assert "wait-for-completion requires --workflow-name" in str(exc_info.value)
    
    def test_get_github_token_from_arg(self, cli_handler):
        """Test getting GitHub token from argument."""
        token = cli_handler.get_github_token("my_token_123")
        assert token == "my_token_123"
    
    def test_get_github_token_from_env(self, cli_handler):
        """Test getting GitHub token from environment."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_456"}):
            token = cli_handler.get_github_token(None)
            assert token == "env_token_456"
    
    def test_get_github_token_missing(self, cli_handler):
        """Test missing GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                cli_handler.get_github_token(None)
            
            assert "GitHub token required" in str(exc_info.value)


class TestOutputFormatter:
    """Test OutputFormatter class."""
    
    @pytest.fixture
    def formatter(self):
        """Create OutputFormatter instance."""
        from rich.console import Console
        console = Console()
        return OutputFormatter(console)
    
    @pytest.fixture
    def sample_runs(self):
        """Create sample workflow runs."""
        return [
            WorkflowRun(
                id=100,
                status="completed",
                conclusion="success",
                name="CI",
                head_branch="main",
                head_sha="abc123",
                created_at="2024-01-20T10:00:00Z",
                updated_at="2024-01-20T10:05:00Z",
                html_url="https://test.url/100"
            ),
            WorkflowRun(
                id=200,
                status="completed",
                conclusion="failure",
                name="Deploy",
                head_branch="release",
                head_sha="def456",
                created_at="2024-01-20T11:00:00Z",
                updated_at="2024-01-20T11:10:00Z",
                html_url="https://test.url/200"
            ),
            WorkflowRun(
                id=300,
                status="in_progress",
                conclusion=None,
                name="Test",
                head_branch="feature",
                head_sha="ghi789",
                created_at="2024-01-20T12:00:00Z",
                updated_at="2024-01-20T12:01:00Z",
                html_url="https://test.url/300"
            )
        ]
    
    def test_get_status_style(self, formatter):
        """Test getting style for status display."""
        assert formatter._get_status_style("completed", "success") == "green"
        assert formatter._get_status_style("completed", "failure") == "red"
        assert formatter._get_status_style("completed", None) == "red"
        assert formatter._get_status_style("in_progress", None) == "yellow"
        assert formatter._get_status_style("queued", None) == "yellow"
    
    def test_display_table(self, formatter, sample_runs, capsys):
        """Test displaying workflow runs in table format."""
        formatter.display_table(sample_runs, title="Test Runs")
        
        captured = capsys.readouterr()
        # Table should contain run IDs and statuses
        assert "100" in captured.out
        assert "200" in captured.out
        assert "300" in captured.out
    
    def test_display_json(self, formatter, sample_runs, capsys):
        """Test displaying workflow runs in JSON format."""
        formatter.display_json(sample_runs)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        
        assert len(data) == 3
        assert data[0]["id"] == 100
        assert data[0]["status"] == "completed"
        assert data[0]["conclusion"] == "success"
        assert data[1]["id"] == 200
        assert data[2]["status"] == "in_progress"
    
    def test_display_success_summary(self, formatter, capsys):
        """Test displaying success summary."""
        run = WorkflowRun(
            id=999,
            status="completed",
            conclusion="success",
            name="Build",
            head_branch="main",
            head_sha="xyz999",
            created_at="2024-01-20T18:00:00Z",
            updated_at="2024-01-20T18:05:00Z",
            html_url="https://test.url/999"
        )
        
        formatter.display_success_summary(run)
        
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert "Build" in captured.out
        assert "999" in captured.out
        assert "https://test.url/999" in captured.out
    
    def test_display_failure_summary(self, formatter, capsys):
        """Test displaying failure summary."""
        run = WorkflowRun(
            id=888,
            status="completed",
            conclusion="failure",
            name="Deploy",
            head_branch="release",
            head_sha="abc888",
            created_at="2024-01-20T19:00:00Z",
            updated_at="2024-01-20T19:10:00Z",
            html_url="https://test.url/888"
        )
        
        formatter.display_failure_summary(run)
        
        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        assert "Deploy" in captured.out
        assert "failure" in captured.out
        assert "https://test.url/888" in captured.out


class TestConfigCreation:
    """Test configuration creation from arguments."""
    
    def test_create_config_from_args(self):
        """Test creating configuration from parsed arguments."""
        args = Mock()
        args.repo = "test/repo"
        args.workflow_name = "ci.yml"
        args.run_id = 12345
        args.token = "test_token"
        args.timeout = 900
        args.poll_interval = 15
        
        with patch('verify_workflow_status.CLIHandler') as mock_cli:
            mock_handler = Mock()
            mock_handler.get_github_token.return_value = "test_token"
            mock_cli.return_value = mock_handler
            
            config = create_config_from_args(args)
        
        assert config.repo == "test/repo"
        assert config.workflow_name == "ci.yml"
        assert config.run_id == 12345
        assert config.token == "test_token"
        assert config.timeout == 900
        assert config.poll_interval == 15
        assert config.max_retries == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])