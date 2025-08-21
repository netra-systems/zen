"""Repository Scanner Core Module.

Handles file discovery and filtering for AI analysis.
Implements intelligent scanning strategies based on repo size.
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import os

from netra_backend.app.logging_config import central_logger as logger


class RepositoryScanner:
    """Scans repositories for relevant files."""
    
    def __init__(self):
        """Initialize scanner configuration."""
        self.priority_dirs = self._init_priority_dirs()
        self.ignore_patterns = self._init_ignore_patterns()
        self.max_file_size = 1024 * 1024  # 1MB
    
    def _init_priority_dirs(self) -> List[str]:
        """Initialize high-priority directories."""
        base_dirs = ["agents", "agent", "ai", "llm", "ml"]
        prefixed_dirs = self._get_all_prefixed_dirs()
        misc_dirs = ["models", "prompts", "chains"]
        return base_dirs + prefixed_dirs + misc_dirs
    
    def _get_all_prefixed_dirs(self) -> List[str]:
        """Get all prefixed priority directories."""
        src_dirs = self._get_src_priority_dirs()
        lib_dirs = self._get_lib_priority_dirs()
        app_dirs = self._get_app_priority_dirs()
        core_dirs = self._get_core_priority_dirs()
        return src_dirs + lib_dirs + app_dirs + core_dirs
    
    def _get_src_priority_dirs(self) -> List[str]:
        """Get src-prefixed priority directories."""
        return ["src/agents", "src/ai", "src/llm"]
    
    def _get_lib_priority_dirs(self) -> List[str]:
        """Get lib-prefixed priority directories."""
        return ["lib/agents", "lib/ai", "lib/llm"]
    
    def _get_app_priority_dirs(self) -> List[str]:
        """Get app-prefixed priority directories."""
        return ["app/agents", "app/ai", "app/llm"]
    
    def _get_core_priority_dirs(self) -> List[str]:
        """Get core-prefixed priority directories."""
        return ["core/agents", "core/ai", "core/llm"]
    
    def _init_ignore_patterns(self) -> Set[str]:
        """Initialize ignore patterns."""
        cache_patterns = self._get_cache_patterns()
        env_patterns = self._get_env_patterns()
        build_patterns = self._get_build_patterns()
        python_patterns = self._get_python_patterns()
        os_patterns = self._get_os_patterns()
        return cache_patterns | env_patterns | build_patterns | python_patterns | os_patterns
    
    def _get_cache_patterns(self) -> Set[str]:
        """Get cache-related ignore patterns."""
        return {"__pycache__", ".pytest_cache"}
    
    def _get_env_patterns(self) -> Set[str]:
        """Get environment-related ignore patterns."""
        return {".venv", "venv", "env", ".env"}
    
    def _get_build_patterns(self) -> Set[str]:
        """Get build-related ignore patterns."""
        return {"dist", "build", ".git", "node_modules"}
    
    def _get_python_patterns(self) -> Set[str]:
        """Get Python-specific ignore patterns."""
        return {"*.pyc", "*.pyo", "*.pyd"}
    
    def _get_os_patterns(self) -> Set[str]:
        """Get OS-specific ignore patterns."""
        return {".DS_Store", "Thumbs.db", "coverage", ".coverage", "htmlcov"}
    
    async def get_relevant_files(
        self, 
        repo_path: str
    ) -> List[Path]:
        """Get relevant files for analysis."""
        repo = self._validate_repo_path(repo_path)
        total_files = await self._count_files(repo)
        strategy = self._determine_strategy(total_files)
        logger.info(f"Scanning {total_files} files with {strategy} strategy")
        return await self._execute_scan_strategy(repo, strategy)
    
    def _validate_repo_path(self, repo_path: str) -> Path:
        """Validate repository path exists."""
        repo = Path(repo_path)
        if not repo.exists():
            raise ValueError(f"Repository path not found: {repo_path}")
        return repo
    
    async def _execute_scan_strategy(self, repo: Path, strategy: str) -> List[Path]:
        """Execute scanning strategy based on type."""
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
        await self._scan_priority_dirs(repo, files)
        await self._scan_root_files(repo, files)
        config_files = await self._find_config_files(repo)
        files.extend(config_files)
        return files
    
    async def _scan_priority_dirs(self, repo: Path, files: List[Path]) -> None:
        """Scan priority directories."""
        for priority_dir in self.priority_dirs:
            dir_path = repo / priority_dir
            if dir_path.exists():
                files.extend(await self._scan_directory(dir_path))
    
    async def _scan_root_files(self, repo: Path, files: List[Path]) -> None:
        """Scan root level files."""
        for item in repo.iterdir():
            if item.is_file() and self._is_relevant_file(item.name):
                if self._check_file_size(item):
                    files.append(item)
    
    async def _sampling_scan(self, repo: Path) -> List[Path]:
        """Perform sampling scan for large repositories."""
        sample_limit = 500
        files = await self._collect_priority_samples(repo, sample_limit)
        files = await self._fill_remaining_samples(repo, files, sample_limit)
        return files[:sample_limit]
    
    async def _collect_priority_samples(self, repo: Path, limit: int) -> List[Path]:
        """Collect samples from priority directories."""
        files = []
        for priority_dir in self.priority_dirs:
            dir_path = repo / priority_dir
            if dir_path.exists():
                dir_files = await self._scan_directory(dir_path, limit=50)
                files.extend(dir_files)
                if len(files) >= limit:
                    break
        return files
    
    async def _fill_remaining_samples(
        self, repo: Path, files: List[Path], limit: int
    ) -> List[Path]:
        """Fill remaining sample slots if needed."""
        if len(files) < limit:
            remaining = limit - len(files)
            other_files = await self._sample_files(repo, remaining)
            files.extend(other_files)
        return files
    
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
            count = self._process_directory_files(root, filenames, files, count, limit)
            if limit and count >= limit:
                break
        return files
    
    def _process_directory_files(
        self, root: str, filenames: List[str], files: List[Path], count: int, limit: Optional[int]
    ) -> int:
        """Process files in a directory."""
        for filename in filenames:
            count = self._process_single_file(root, filename, files, count, limit)
            if limit and count >= limit: break
        return count
    
    def _process_single_file(
        self, root: str, filename: str, files: List[Path], 
        count: int, limit: Optional[int]
    ) -> int:
        """Process a single file."""
        if self._is_relevant_file(filename):
            count = self._add_file_if_valid(Path(root) / filename, files, count)
        return count
    
    def _add_file_if_valid(
        self, file_path: Path, files: List[Path], count: int
    ) -> int:
        """Add file if valid and increment count."""
        if self._check_file_size(file_path):
            files.append(file_path)
            count += 1
        return count
    
    async def _sample_files(
        self, 
        repo: Path, 
        limit: int
    ) -> List[Path]:
        """Sample files from repository."""
        all_files = await self._collect_all_files(repo)
        return self._create_distributed_sample(all_files, limit)
    
    async def _collect_all_files(self, repo: Path) -> List[Path]:
        """Collect all relevant files from repository."""
        all_files = []
        for root, dirs, filenames in os.walk(repo):
            dirs[:] = self._filter_dirs(dirs)
            self._add_relevant_files(root, filenames, all_files)
        return all_files
    
    def _add_relevant_files(
        self, root: str, filenames: List[str], all_files: List[Path]
    ) -> None:
        """Add relevant files to collection."""
        for filename in filenames:
            self._add_file_if_relevant(root, filename, all_files)
    
    def _add_file_if_relevant(
        self, root: str, filename: str, all_files: List[Path]
    ) -> None:
        """Add file to collection if relevant."""
        if self._is_relevant_file(filename):
            file_path = Path(root) / filename
            if self._check_file_size(file_path):
                all_files.append(file_path)
    
    def _create_distributed_sample(
        self, all_files: List[Path], limit: int
    ) -> List[Path]:
        """Create evenly distributed sample."""
        if len(all_files) <= limit:
            return all_files
        step = len(all_files) // limit
        return all_files[::step][:limit]
    
    async def _find_config_files(self, repo: Path) -> List[Path]:
        """Find configuration files."""
        config_patterns = self._get_config_patterns()
        config_files = []
        self._collect_config_files(repo, config_patterns, config_files)
        return config_files
    
    def _get_config_patterns(self) -> List[str]:
        """Get configuration file patterns."""
        env_patterns = ["*.env*"]
        format_patterns = ["*.yaml", "*.yml", "*.toml", "*.json"]
        python_patterns = ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"]
        js_patterns = ["package.json"]
        return env_patterns + format_patterns + python_patterns + js_patterns
    
    def _collect_config_files(
        self, repo: Path, patterns: List[str], config_files: List[Path]
    ) -> None:
        """Collect configuration files matching patterns."""
        for pattern in patterns:
            for file_path in repo.glob(pattern):
                if file_path.is_file() and self._check_file_size(file_path):
                    config_files.append(file_path)
    
    def _is_relevant_file(self, filename: str) -> bool:
        """Check if file is relevant for analysis."""
        extensions = self._get_relevant_extensions()
        return Path(filename).suffix.lower() in extensions
    
    def _get_relevant_extensions(self) -> set:
        """Get relevant file extensions for analysis."""
        code_exts = {".py", ".js", ".ts", ".jsx", ".tsx"}
        compiled_exts = {".java", ".go", ".rs", ".rb", ".php"}
        system_exts = {".cs", ".cpp", ".c"}
        config_exts = {".yaml", ".yml", ".json", ".toml", ".env"}
        doc_exts = {".txt", ".md"}
        return code_exts | compiled_exts | system_exts | config_exts | doc_exts
    
    def _check_file_size(self, file_path: Path) -> bool:
        """Check if file size is within limits."""
        try:
            return file_path.stat().st_size <= self.max_file_size
        except Exception:
            return False