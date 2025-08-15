"""
Configuration management for the dev launcher.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any

@dataclass
class LauncherConfig:
    """Configuration for the development launcher."""
    
    # Port configuration
    backend_port: Optional[int] = None
    frontend_port: int = 3000
    dynamic_ports: bool = True  # Default to dynamic allocation
    
    # Reload configuration (uses native reload)
    backend_reload: bool = False  # Default to no reload for performance
    frontend_reload: bool = True  # Next.js always has reload
    
    # Secret management
    load_secrets: bool = True
    project_id: Optional[str] = None
    
    # UI configuration
    no_browser: bool = False
    verbose: bool = False
    non_interactive: bool = False  # Non-interactive mode for CI/automation
    
    # Build configuration
    use_turbopack: bool = False
    
    # Boundary monitoring configuration
    watch_boundaries: bool = False  # Real-time boundary monitoring
    boundary_check_interval: int = 30  # Check every 30 seconds
    fail_on_boundary_violations: bool = False  # Stop dev server on violations
    show_boundary_warnings: bool = True  # Show boundary warning messages
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path.cwd())
    log_dir: Optional[Path] = None
    
    # Environment variables
    env_overrides: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed fields."""
        if self.log_dir is None:
            self.log_dir = self.project_root / "logs"
        
        # Set project ID from environment if not provided
        if self.project_id is None:
            self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', "304612253870")
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        # Validate ports
        if self.backend_port and not (1 <= self.backend_port <= 65535):
            raise ValueError(f"Invalid backend port: {self.backend_port}. Must be between 1 and 65535.")
        
        if not (1 <= self.frontend_port <= 65535):
            raise ValueError(f"Invalid frontend port: {self.frontend_port}. Must be between 1 and 65535.")
        
        # Validate project root exists
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
        
        # Check for required directories
        backend_dir = self.project_root / "app"
        frontend_dir = self.project_root / "frontend"
        
        if not backend_dir.exists():
            raise ValueError(f"Backend directory not found: {backend_dir}\nAre you running from the correct directory?")
        
        if not frontend_dir.exists():
            raise ValueError(f"Frontend directory not found: {frontend_dir}\nAre you running from the correct directory?")
    
    @classmethod
    def from_args(cls, args) -> "LauncherConfig":
        """Create configuration from command-line arguments."""
        # Handle port configuration
        dynamic_ports = not args.static if hasattr(args, 'static') else True
        
        # Handle reload flags
        if hasattr(args, 'dev') and args.dev:
            # Development mode: enable all hot reload
            backend_reload = True
            frontend_reload = True
        elif hasattr(args, 'backend_reload') and args.backend_reload:
            # Explicit backend reload
            backend_reload = True
            frontend_reload = True
        elif args.no_reload:
            # No reload at all
            backend_reload = False
            frontend_reload = True  # Next.js always has reload
        else:
            # Default: no backend reload for performance
            backend_reload = False
            frontend_reload = True
        
        # Default to loading secrets unless --no-secrets is specified
        load_secrets = not args.no_secrets if hasattr(args, 'no_secrets') else True
        
        return cls(
            backend_port=args.backend_port,
            frontend_port=args.frontend_port,
            dynamic_ports=dynamic_ports,
            verbose=args.verbose,
            backend_reload=backend_reload,
            frontend_reload=frontend_reload,
            load_secrets=load_secrets,
            project_id=args.project_id if hasattr(args, 'project_id') else None,
            no_browser=args.no_browser,
            non_interactive=args.non_interactive if hasattr(args, 'non_interactive') else False,
            use_turbopack=not args.no_turbopack if hasattr(args, 'no_turbopack') else False,
            project_root=find_project_root()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "backend_port": self.backend_port,
            "frontend_port": self.frontend_port,
            "dynamic_ports": self.dynamic_ports,
            "backend_reload": self.backend_reload,
            "frontend_reload": self.frontend_reload,
            "load_secrets": self.load_secrets,
            "project_id": self.project_id,
            "no_browser": self.no_browser,
            "verbose": self.verbose,
            "non_interactive": self.non_interactive,
            "use_turbopack": self.use_turbopack,
            "project_root": str(self.project_root),
            "log_dir": str(self.log_dir),
        }


def find_project_root() -> Path:
    """Find the project root directory robustly."""
    current_file = Path(__file__).resolve()
    
    # Check if we're in dev_launcher directory
    if current_file.parent.name == 'dev_launcher':
        return current_file.parent.parent
    
    # Try to find project root by looking for key files/dirs
    for parent in current_file.parents:
        if (parent / 'frontend').exists() or (parent / 'app').exists() or (parent / 'requirements.txt').exists():
            return parent
    
    # Fallback to current working directory
    return Path.cwd()


def resolve_path(*parts, root: Optional[Path] = None, required: bool = False) -> Optional[Path]:
    """
    Resolve a path robustly, checking multiple locations.
    
    Args:
        *parts: Path components to join
        root: Root directory to search from
        required: Whether to raise an error if not found
    
    Returns:
        Resolved path or None if not found
    """
    if root is None:
        root = find_project_root()
    
    # Default search directories
    search_dirs = [
        Path.cwd(),  # Current working directory
        root,  # Project root
        Path(__file__).parent,  # Current directory
        Path(__file__).parent.parent,  # Parent directory
    ]
    
    # Try each search directory
    for base_dir in search_dirs:
        path = base_dir / Path(*parts)
        if path.exists():
            return path.resolve()
    
    # If required and not found, raise error
    if required:
        searched = ', '.join(str(d) for d in search_dirs)
        raise FileNotFoundError(f"Could not find {'/'.join(parts)} in any of: {searched}")
    
    # Return the path relative to root as fallback
    return root / Path(*parts)