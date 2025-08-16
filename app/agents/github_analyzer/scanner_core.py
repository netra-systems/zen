"""Repository Scanner Core Module.

Handles file discovery and filtering for AI analysis.
Implements intelligent scanning strategies based on repo size.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import os

from app.logging_config import central_logger as logger


class RepositoryScanner:
    """Scans repositories for relevant files."""
    
    def __init__(self):
        """Initialize scanner configuration."""
        self.priority_dirs = self._init_priority_dirs()
        self.ignore_patterns = self._init_ignore_patterns()
        self.max_file_size = 1024 * 1024  # 1MB
    
    def _init_priority_dirs(self) -> List[str]:
        """Initialize high-priority directories."""
        return [
            "agents", "agent", "ai", "llm", "ml",
            "src/agents", "src/ai", "src/llm",
            "lib/agents", "lib/ai", "lib/llm",
            "app/agents", "app/ai", "app/llm",
            "core/agents", "core/ai", "core/llm",
            "models", "prompts", "chains"
        ]
    
    def _init_ignore_patterns(self) -> Set[str]:
        """Initialize ignore patterns."""
        return {
            "__pycache__", ".git", "node_modules",
            ".venv", "venv", "env", ".env",
            "dist", "build", ".pytest_cache",
            "coverage", ".coverage", "htmlcov",
            "*.pyc", "*.pyo", "*.pyd",
            ".DS_Store", "Thumbs.db"
        }
    
    async def get_relevant_files(
        self, 
        repo_path: str
    ) -> List[Path]:
        """Get relevant files for analysis."""
        repo = Path(repo_path)
        if not repo.exists():
            raise ValueError(f"Repository path not found: {repo_path}")
        
        # Determine scanning strategy
        total_files = await self._count_files(repo)
        strategy = self._determine_strategy(total_files)
        
        logger.info(f"Scanning {total_files} files with {strategy} strategy")
        
        if strategy == "complete":
            return await self._complete_scan(repo)
        elif strategy == "targeted":
            return await self._targeted_scan(repo)
        else:
            return await self._sampling_scan(repo)
    
    async def _count_files(self, repo: Path) -> int:
        """Count total files in repository."""
        count = 0
        for root, dirs, files in os.walk(repo):
            dirs[:] = self._filter_dirs(dirs)
            count += len(files)
        return count
    
    def _filter_dirs(self, dirs: List[str]) -> List[str]:
        """Filter out ignored directories."""
        return [d for d in dirs if not self._should_ignore(d)]
    
    def _should_ignore(self, name: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in name:
                return True
        return False
    
    def _determine_strategy(self, file_count: int) -> str:
        """Determine scanning strategy."""
        if file_count < 100:
            return "complete"
        elif file_count < 1000:
            return "targeted"
        else:
            return "sampling"
    
    async def _complete_scan(self, repo: Path) -> List[Path]:
        """Perform complete repository scan."""
        files = []
        
        for root, dirs, filenames in os.walk(repo):
            dirs[:] = self._filter_dirs(dirs)
            
            for filename in filenames:
                if self._is_relevant_file(filename):
                    file_path = Path(root) / filename
                    if self._check_file_size(file_path):
                        files.append(file_path)
        
        return files
    
    async def _targeted_scan(self, repo: Path) -> List[Path]:
        """Perform targeted scan on priority directories."""
        files = []
        
        # First scan priority directories
        for priority_dir in self.priority_dirs:
            dir_path = repo / priority_dir
            if dir_path.exists():
                files.extend(await self._scan_directory(dir_path))
        
        # Then scan root level files
        for item in repo.iterdir():
            if item.is_file() and self._is_relevant_file(item.name):
                if self._check_file_size(item):
                    files.append(item)
        
        # Add configuration files
        config_files = await self._find_config_files(repo)
        files.extend(config_files)
        
        return files
    
    async def _sampling_scan(self, repo: Path) -> List[Path]:
        """Perform sampling scan for large repositories."""
        files = []
        sample_limit = 500
        
        # Priority directories first
        for priority_dir in self.priority_dirs:
            dir_path = repo / priority_dir
            if dir_path.exists():
                dir_files = await self._scan_directory(dir_path, limit=50)
                files.extend(dir_files)
                
                if len(files) >= sample_limit:
                    break
        
        # Sample from other directories if needed
        if len(files) < sample_limit:
            remaining = sample_limit - len(files)
            other_files = await self._sample_files(repo, remaining)
            files.extend(other_files)
        
        return files[:sample_limit]
    
    async def _scan_directory(
        self, 
        directory: Path, 
        limit: Optional[int] = None
    ) -> List[Path]:
        """Scan a specific directory."""
        files = []
        count = 0
        
        for root, dirs, filenames in os.walk(directory):
            dirs[:] = self._filter_dirs(dirs)
            
            for filename in filenames:
                if self._is_relevant_file(filename):
                    file_path = Path(root) / filename
                    if self._check_file_size(file_path):
                        files.append(file_path)
                        count += 1
                        
                        if limit and count >= limit:
                            return files
        
        return files
    
    async def _sample_files(
        self, 
        repo: Path, 
        limit: int
    ) -> List[Path]:
        """Sample files from repository."""
        all_files = []
        
        for root, dirs, filenames in os.walk(repo):
            dirs[:] = self._filter_dirs(dirs)
            
            for filename in filenames:
                if self._is_relevant_file(filename):
                    file_path = Path(root) / filename
                    if self._check_file_size(file_path):
                        all_files.append(file_path)
        
        # Return evenly distributed sample
        if len(all_files) <= limit:
            return all_files
        
        step = len(all_files) // limit
        return all_files[::step][:limit]
    
    async def _find_config_files(self, repo: Path) -> List[Path]:
        """Find configuration files."""
        config_patterns = [
            "*.env*", "*.yaml", "*.yml", "*.toml",
            "*.json", "requirements.txt", "package.json",
            "Pipfile", "pyproject.toml", "setup.py"
        ]
        
        config_files = []
        for pattern in config_patterns:
            for file_path in repo.glob(pattern):
                if file_path.is_file() and self._check_file_size(file_path):
                    config_files.append(file_path)
        
        return config_files
    
    def _is_relevant_file(self, filename: str) -> bool:
        """Check if file is relevant for analysis."""
        extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx",
            ".java", ".go", ".rs", ".rb", ".php",
            ".cs", ".cpp", ".c", ".yaml", ".yml",
            ".json", ".toml", ".env", ".txt", ".md"
        }
        
        return Path(filename).suffix.lower() in extensions
    
    def _check_file_size(self, file_path: Path) -> bool:
        """Check if file size is within limits."""
        try:
            return file_path.stat().st_size <= self.max_file_size
        except:
            return False