"""GitHub API Client Module.

Handles GitHub repository access and cloning.
Supports both public and private repositories.
"""

import os
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

from app.logging_config import central_logger as logger
from app.core.exceptions import NetraException


class GitHubAPIClient:
    """Client for GitHub repository operations."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.temp_dir = None
        self.github_token = os.environ.get("GITHUB_TOKEN")
    
    async def clone_repository(self, repo_url: str) -> str:
        """Clone or access repository."""
        # Parse repository URL
        parsed = self._parse_repo_url(repo_url)
        
        # Check if it's a local path
        if self._is_local_path(repo_url):
            return await self._handle_local_repo(repo_url)
        
        # Clone remote repository
        return await self._clone_remote_repo(parsed)
    
    def _parse_repo_url(self, url: str) -> Dict[str, str]:
        """Parse repository URL."""
        if url.startswith("http"):
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            
            if len(path_parts) >= 2:
                return {
                    "owner": path_parts[0],
                    "repo": path_parts[1].replace(".git", ""),
                    "host": parsed.netloc,
                    "full_url": url
                }
        
        # Handle git@github.com format
        if url.startswith("git@"):
            parts = url.replace("git@", "").replace(":", "/").split("/")
            if len(parts) >= 3:
                return {
                    "owner": parts[1],
                    "repo": parts[2].replace(".git", ""),
                    "host": parts[0],
                    "full_url": url
                }
        
        # Handle owner/repo format
        if "/" in url and not "\\" in url:
            parts = url.split("/")
            if len(parts) == 2:
                return {
                    "owner": parts[0],
                    "repo": parts[1],
                    "host": "github.com",
                    "full_url": f"https://github.com/{url}"
                }
        
        raise ValueError(f"Invalid repository URL format: {url}")
    
    def _is_local_path(self, path: str) -> bool:
        """Check if path is local."""
        return os.path.exists(path) or path.startswith("/") or path.startswith(".")
    
    async def _handle_local_repo(self, path: str) -> str:
        """Handle local repository."""
        repo_path = Path(path).resolve()
        
        if not repo_path.exists():
            raise NetraException(f"Local repository not found: {path}")
        
        if not repo_path.is_dir():
            raise NetraException(f"Path is not a directory: {path}")
        
        # Check if it's a git repository
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            logger.warning(f"Directory is not a git repository: {path}")
        
        return str(repo_path)
    
    async def _clone_remote_repo(self, parsed: Dict[str, str]) -> str:
        """Clone remote repository."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="github_analyzer_")
        repo_path = os.path.join(self.temp_dir, parsed["repo"])
        
        try:
            # Build clone command
            clone_url = self._build_clone_url(parsed)
            
            # Clone with limited depth for efficiency
            cmd = ["git", "clone", "--depth", "1", clone_url, repo_path]
            
            # Run clone command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise NetraException(f"Failed to clone repository: {error_msg}")
            
            logger.info(f"Successfully cloned repository to {repo_path}")
            return repo_path
            
        except Exception as e:
            # Clean up on error
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            raise NetraException(f"Repository clone failed: {str(e)}")
    
    def _build_clone_url(self, parsed: Dict[str, str]) -> str:
        """Build clone URL with authentication if needed."""
        base_url = parsed["full_url"]
        
        # Add token authentication for private repos
        if self.github_token and "github.com" in parsed["host"]:
            # Use token in URL for HTTPS cloning
            if base_url.startswith("https://"):
                return base_url.replace(
                    "https://",
                    f"https://{self.github_token}@"
                )
        
        return base_url
    
    async def get_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """Get repository information via API."""
        parsed = self._parse_repo_url(repo_url)
        
        # For now, return basic info
        # Could be extended to use GitHub API for more details
        return {
            "owner": parsed["owner"],
            "name": parsed["repo"],
            "url": parsed["full_url"],
            "host": parsed["host"]
        }
    
    async def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
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