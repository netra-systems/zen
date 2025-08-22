#!/usr/bin/env python3
"""
Enhancement script for dev_launcher boundary monitoring.
Adds real-time boundary enforcement to the development environment.
"""

import os
import sys
from pathlib import Path


def enhance_launcher_config():
    """Add boundary monitoring configuration to LauncherConfig."""
    config_file = Path(__file__).parent.parent / "dev_launcher" / "config.py"
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Add boundary monitoring fields if not already present
    if "watch_boundaries" not in content:
        # Find the from_args method and add boundary config handling
        from_args_start = content.find("return cls(")
        from_args_end = content.find(")", from_args_start)
        
        if from_args_start != -1 and from_args_end != -1:
            existing_args = content[from_args_start:from_args_end]
            
            # Add boundary monitoring arguments
            boundary_args = """            watch_boundaries=getattr(args, 'watch_boundaries', False),
            boundary_check_interval=getattr(args, 'boundary_check_interval', 30),
            fail_on_boundary_violations=getattr(args, 'fail_on_boundary_violations', False),
            show_boundary_warnings=not getattr(args, 'no_boundary_warnings', False),"""
            
            # Insert before project_root
            project_root_line = "            project_root=find_project_root()"
            updated_args = existing_args.replace(
                project_root_line,
                boundary_args + "\n" + project_root_line
            )
            
            content = content.replace(existing_args, updated_args)
        
        # Add to to_dict method
        to_dict_start = content.find('"use_turbopack": self.use_turbopack,')
        if to_dict_start != -1:
            to_dict_line = '"use_turbopack": self.use_turbopack,'
            boundary_dict_fields = '''            "watch_boundaries": self.watch_boundaries,
            "boundary_check_interval": self.boundary_check_interval,
            "fail_on_boundary_violations": self.fail_on_boundary_violations,
            "show_boundary_warnings": self.show_boundary_warnings,'''
            
            content = content.replace(
                to_dict_line,
                to_dict_line + "\n" + boundary_dict_fields
            )
        
        with open(config_file, 'w') as f:
            f.write(content)
        
        print("Enhanced launcher config with boundary monitoring")

def enhance_launcher_args():
    """Add boundary monitoring arguments to argument parser."""
    main_file = Path(__file__).parent.parent / "dev_launcher" / "__main__.py"
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Add boundary monitoring arguments if not already present
    if "--watch-boundaries" not in content:
        # Find the return parser line and add boundary group before it
        return_parser_idx = content.find("return parser")
        
        if return_parser_idx != -1:
            boundary_group = '''
    # Boundary monitoring configuration
    boundary_group = parser.add_argument_group('Boundary Monitoring')
    boundary_group.add_argument(
        "--watch-boundaries",
        dest="watch_boundaries",
        action="store_true",
        help="Enable real-time boundary monitoring (450-line/25-line limits)"
    )
    boundary_group.add_argument(
        "--boundary-check-interval",
        dest="boundary_check_interval",
        type=int,
        default=30,
        help="Boundary check interval in seconds (default: 30)"
    )
    boundary_group.add_argument(
        "--fail-on-boundary-violations",
        dest="fail_on_boundary_violations",
        action="store_true",
        help="Stop dev server on critical boundary violations"
    )
    boundary_group.add_argument(
        "--no-boundary-warnings",
        dest="no_boundary_warnings",
        action="store_true",
        help="Disable boundary violation warning messages"
    )
    
'''
            
            content = content[:return_parser_idx] + boundary_group + "    " + content[return_parser_idx:]
        
        with open(main_file, 'w') as f:
            f.write(content)
        
        print("Enhanced argument parser with boundary monitoring flags")

def enhance_launcher_main():
    """Add boundary monitoring integration to main launcher."""
    launcher_file = Path(__file__).parent.parent / "dev_launcher" / "launcher.py"
    
    with open(launcher_file, 'r') as f:
        content = f.read()
    
    # Add boundary monitor import
    if "boundary_monitor" not in content:
        health_monitor_import = "from .health_monitor import HealthMonitor, create_url_health_check, create_process_health_check"
        if health_monitor_import in content:
            content = content.replace(
                health_monitor_import,
                health_monitor_import + "\nfrom .boundary_monitor import BoundaryMonitorIntegration"
            )
    
    # Add boundary monitor initialization in __init__
    if "self.boundary_monitor" not in content:
        health_monitor_init = "self.health_monitor = HealthMonitor(check_interval=30)"
        if health_monitor_init in content:
            content = content.replace(
                health_monitor_init,
                health_monitor_init + "\n        self.boundary_monitor = BoundaryMonitorIntegration(config, self._print)"
            )
    
    # Add boundary monitoring setup in run method
    if "setup_monitoring" not in content:
        register_health_line = "self.register_health_monitoring()"
        if register_health_line in content:
            content = content.replace(
                register_health_line,
                "self.boundary_monitor.setup_monitoring()\n        " + register_health_line
            )
    
    # Add boundary monitoring cleanup in run method
    if "cleanup_monitoring" not in content:
        health_stop_line = "self.health_monitor.stop()"
        if health_stop_line in content:
            content = content.replace(
                health_stop_line,
                health_stop_line + "\n        self.boundary_monitor.cleanup_monitoring()"
            )
    
    # Show boundary monitoring in config display
    if "Boundary monitoring" not in content:
        turbopack_line = 'print(f"  • Turbopack: {\'YES\' if self.config.use_turbopack else \'NO\'}")'
        if turbopack_line in content:
            content = content.replace(
                turbopack_line,
                turbopack_line + '\n        print(f"  • Boundary monitoring: {\'YES\' if self.config.watch_boundaries else \'NO\'}")'
            )
    
    with open(launcher_file, 'w') as f:
        f.write(content)
    
    print("Enhanced main launcher with boundary monitoring integration")

def _get_vscode_settings_content() -> str:
    """Generate VS Code settings.json content for boundary monitoring."""
    return '''{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
        "--max-line-length=300",
        "--max-complexity=8",
        "--extend-ignore=E203,W503"
    ],
    "files.watcherExclude": {
        "**/node_modules/**": true,
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/logs/**": true,
        "**/__pycache__/**": true
    },
    "editor.rulers": [300],
    "python.analysis.extraPaths": [
        "./scripts"
    ],
    "files.associations": {
        "*.py": "python"
    },
    "workbench.colorCustomizations": {
        "editorRuler.foreground": "#ff0000"
    },
    "editor.tokenColorCustomizations": {
        "comments": "#888888"
    }
}'''

def _get_vscode_tasks_content() -> str:
    """Generate VS Code tasks.json content for boundary checking."""
    return '''{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Check Boundaries",
            "type": "shell",
            "command": "python",
            "args": ["scripts/boundary_enforcer.py", "--enforce"],
            "group": {
                "kind": "build",
                "isDefault": false
            },
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "Check Architecture Compliance",
            "type": "shell",
            "command": "python",
            "args": ["scripts/check_architecture_compliance.py"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "Split Large Files",
            "type": "shell",
            "command": "python",
            "args": ["scripts/split_large_files.py"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        }
    ]
}'''

def _write_vscode_file(file_path: Path, content: str) -> None:
    """Write content to VS Code configuration file."""
    with open(file_path, 'w') as f:
        f.write(content)

def _create_vscode_settings(vscode_dir: Path) -> None:
    """Create VS Code settings.json file."""
    settings_file = vscode_dir / "settings.json"
    settings_content = _get_vscode_settings_content()
    _write_vscode_file(settings_file, settings_content)

def _create_vscode_tasks(vscode_dir: Path) -> None:
    """Create VS Code tasks.json file."""
    tasks_file = vscode_dir / "tasks.json"
    tasks_content = _get_vscode_tasks_content()
    _write_vscode_file(tasks_file, tasks_content)

def create_vscode_config() -> None:
    """Create VS Code configuration for real-time boundary feedback."""
    vscode_dir = Path(__file__).parent.parent / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    
    _create_vscode_settings(vscode_dir)
    _create_vscode_tasks(vscode_dir)
    
    print("Created VS Code configuration for boundary monitoring")

def main():
    """Main enhancement script."""
    print("BOUNDARY ENFORCEMENT ENHANCEMENT")
    print("=" * 50)
    
    try:
        enhance_launcher_config()
        enhance_launcher_args()
        enhance_launcher_main()
        create_vscode_config()
        
        print("\n" + "=" * 50)
        print("ENHANCEMENT COMPLETE")
        print("=" * 50)
        print("\nBoundary monitoring features added:")
        print("  • Real-time boundary monitoring in dev launcher")
        print("  • --watch-boundaries flag for continuous monitoring")
        print("  • --fail-on-boundary-violations for strict enforcement")
        print("  • VS Code integration with rulers and tasks")
        print("  • Automated boundary violation alerts")
        print("\nUsage:")
        print("  python dev_launcher.py --watch-boundaries")
        print("  python dev_launcher.py --watch-boundaries --fail-on-boundary-violations")
        
    except Exception as e:
        print(f"Enhancement failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())