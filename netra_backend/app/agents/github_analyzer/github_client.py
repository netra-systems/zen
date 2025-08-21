"""GitHub API Client Module.

Handles GitHub repository access and cloning.
Supports both public and private repositories.
"""

import os
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.core.configuration import get_configuration


class GitHubAPIClient:
    """Client for GitHub repository operations."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.temp_dir = None
        config = get_configuration()
        self.github_token = getattr(config, 'github_token', None)
    
    async def clone_repository(self, repo_url: str) -> str:
        """Clone or access repository."""
        if self._is_local_path(repo_url):
            return await self._handle_local_repo(repo_url)
        parsed = self._parse_repo_url(repo_url)
        return await self._clone_remote_repo(parsed)
    
    def _parse_repo_url(self, url: str) -> Dict[str, str]:
        """Parse repository URL."""
        if url.startswith("http"):
            return self._parse_http_url(url)
        elif url.startswith("git@"):
            return self._parse_git_url(url)
        elif "/" in url and not "\\" in url:
            return self._parse_owner_repo_format(url)
        else:
            raise ValueError(f"Invalid repository URL format: {url}")
    
    def _parse_http_url(self, url: str) -> Dict[str, str]:
        """Parse HTTP/HTTPS repository URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            raise ValueError(f"Invalid HTTP URL format: {url}")
        return {
            "owner": path_parts[0],
            "repo": path_parts[1].replace(".git", ""),
            "host": parsed.netloc,
            "full_url": url
        }
    
    def _parse_git_url(self, url: str) -> Dict[str, str]:
        """Parse git@ format URL."""
        parts = url.replace("git@", "").replace(":", "/").split("/")
        if len(parts) < 3:
            raise ValueError(f"Invalid git URL format: {url}")
        return {
            "owner": parts[1],
            "repo": parts[2].replace(".git", ""),
            "host": parts[0],
            "full_url": url
        }
    
    def _parse_owner_repo_format(self, url: str) -> Dict[str, str]:
        """Parse owner/repo format."""
        parts = url.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid owner/repo format: {url}")
        return {
            "owner": parts[0],
            "repo": parts[1],
            "host": "github.com",
            "full_url": f"https://github.com/{url}"
        }
    
    def _is_local_path(self, path: str) -> bool:
        """Check if path is local."""
        return os.path.exists(path) or path.startswith("/") or path.startswith(".")
    
    async def _handle_local_repo(self, path: str) -> str:
        """Handle local repository."""
        repo_path = Path(path).resolve()
        self._validate_local_path(repo_path, path)
        self._check_git_repository(repo_path, path)
        return str(repo_path)
    
    def _validate_local_path(self, repo_path: Path, original_path: str) -> None:
        """Validate local repository path."""
        if not repo_path.exists():
            raise NetraException(f"Local repository not found: {original_path}")
        if not repo_path.is_dir():
            raise NetraException(f"Path is not a directory: {original_path}")
    
    def _check_git_repository(self, repo_path: Path, original_path: str) -> None:
        """Check if directory is a git repository."""
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            logger.warning(f"Directory is not a git repository: {original_path}")
    
    async def _clone_remote_repo(self, parsed: Dict[str, str]) -> str:
        """Clone remote repository."""
        self.temp_dir = tempfile.mkdtemp(prefix="github_analyzer_")
        repo_path = os.path.join(self.temp_dir, parsed["repo"])
        try:
            return await self._execute_clone(parsed, repo_path)
        except Exception as e:
            self._cleanup_on_error()
            raise NetraException(f"Repository clone failed: {str(e)}")
    
    async def _execute_clone(self, parsed: Dict[str, str], repo_path: str) -> str:
        """Execute git clone command."""
        clone_url = self._build_clone_url(parsed)
        cmd = ["git", "clone", "--depth", "1", clone_url, repo_path]
        process = await self._run_clone_process(cmd)
        await self._validate_clone_result(process, repo_path)
        return repo_path
    
    async def _run_clone_process(self, cmd: List[str]) -> asyncio.subprocess.Process:
        """Run the git clone process."""
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    
    async def _validate_clone_result(
        self, 
        process: asyncio.subprocess.Process, 
        repo_path: str
    ) -> None:
        """Validate clone operation result."""
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise NetraException(f"Failed to clone repository: {error_msg}")
        logger.info(f"Successfully cloned repository to {repo_path}")
    
    def _cleanup_on_error(self) -> None:
        """Clean up temporary directory on error."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _build_clone_url(self, parsed: Dict[str, str]) -> str:
        """Build clone URL with authentication if needed."""
        base_url = parsed["full_url"]
        if self._should_add_token(parsed):
            return self._add_token_to_url(base_url)
        return base_url
    
    def _should_add_token(self, parsed: Dict[str, str]) -> bool:
        """Check if token should be added to URL."""
        return (
            self.github_token and 
            "github.com" in parsed["host"] and 
            parsed["full_url"].startswith("https://")
        )
    
    def _add_token_to_url(self, url: str) -> str:
        """Add GitHub token to HTTPS URL."""
        return url.replace("https://", f"https://{self.github_token}@")
    
    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """Get repository information via API."""
        parsed = self._parse_repo_url(repo_url)
        return self._build_repo_info(parsed)
    
    def _build_repo_info(self, parsed: Dict[str, str]) -> Dict[str, Any]:
        """Build repository information dictionary."""
        return {
            "owner": parsed["owner"],
            "name": parsed["repo"],
            "url": parsed["full_url"],
            "host": parsed["host"]
        }
    
    async def cleanup(self):
        """Clean up temporary files."""
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp dir: {e}")
        finally:
            self.temp_dir = None
    
    def __del__(self):
        """Cleanup on deletion."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass