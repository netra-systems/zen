#!/usr/bin/env python3
"""Organize root directory files into appropriate folders."""

import os
import shutil
from pathlib import Path


def organize_files():
    """Move files from root directory to organized folders."""
    
    root_dir = Path(".")
    
    # Define file patterns and their target directories
    file_mappings = {
        "organized_root/test_reports": [
            "*TEST*.md",
            "*test*.py", 
            "*test*.json",
            "*test*.log",
            "*test*.txt",
            "*test*.db",
            "test_*.csv",
            "*_TEST_*.md",
            "TEST_*.md",
            "run_*test*.py",
            "validate_*.py",
            "debug_*.py",
            "demo_*.py"
        ],
        "organized_root/compliance_reports": [
            "*compliance*.json",
            "*violations*.json",
            "*_status.json",
            "agents_*.json",
            "actions_*.json",
            "analyze_*.py",
            "extract_*.py",
            "find_*.py",
            "fix_*.py",
            "check_*.py",
            "count_*.py",
            "process_*.py",
            "categorize_*.py"
        ],
        "organized_root/project_docs": [
            "*.md",
            "readme.md",
            "README.md",
            "claude_*.md",
            "LLM_MASTER_INDEX.md",
            "CLAUDE.md"
        ],
        "organized_root/utilities": [
            "*.py",
            "*.ps1",
            "*.bat",
            "*.exe"
        ],
        "organized_root/data_files": [
            "*.csv",
            "*.db",
            "*.log",
            "*.txt",
            "*.html",
            "nul"
        ]
    }
    
    # Files to keep in root
    keep_in_root = {
        ".env", ".env.example", ".env.local", ".env.development", 
        ".env.production", ".env.staging", ".env.test", ".env.testing",
        ".gitignore", ".gitattributes", ".gcloudignore",
        ".coveragerc", ".pre-commit-config.yaml",
        "requirements.txt", "requirements-dev.txt",
        "alembic.ini", "pytest.ini", "config.yaml",
        "package.json", "package-lock.json",
        ".actrc", ".dockerignore",
        "CLAUDE.md", "LLM_MASTER_INDEX.md", "readme.md"
    }
    
    moved_files = []
    errors = []
    
    # Process each mapping
    for target_dir, patterns in file_mappings.items():
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        for pattern in patterns:
            for file_path in root_dir.glob(pattern):
                # Skip directories
                if file_path.is_dir():
                    continue
                    
                # Skip files that should stay in root
                if file_path.name in keep_in_root:
                    continue
                    
                # Skip files already in organized folders
                if "organized_root" in str(file_path):
                    continue
                    
                # Skip if file was already moved
                if not file_path.exists():
                    continue
                
                try:
                    target_file = target_path / file_path.name
                    
                    # If file already exists in target, skip
                    if target_file.exists():
                        continue
                    
                    shutil.move(str(file_path), str(target_file))
                    moved_files.append(f"{file_path.name} -> {target_dir}")
                    
                except Exception as e:
                    errors.append(f"Error moving {file_path.name}: {e}")
    
    # Print summary
    print(f"\n=== File Organization Summary ===")
    print(f"Total files moved: {len(moved_files)}")
    
    if moved_files:
        print("\nMoved files:")
        for move in moved_files[:20]:  # Show first 20
            print(f"  - {move}")
        if len(moved_files) > 20:
            print(f"  ... and {len(moved_files) - 20} more files")
    
    if errors:
        print(f"\nErrors encountered: {len(errors)}")
        for error in errors[:5]:
            print(f"  - {error}")
    
    print("\n=== Organization Complete ===")

if __name__ == "__main__":
    organize_files()