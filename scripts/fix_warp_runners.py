#!/usr/bin/env python3
"""Emergency script to switch from offline Warp runners to GitHub-hosted runners."""

import os
import re
from pathlib import Path

def update_runners(workflow_dir=".github/workflows"):
    """Update all workflow files to use GitHub-hosted runners."""
    
    workflow_path = Path(workflow_dir)
    updated_files = []
    
    # Pattern to match warp-custom-default runner
    pattern = re.compile(r'runs-on:\s*warp-custom-default')
    replacement = 'runs-on: warp-custom-default  # Temporary: Using GitHub-hosted while Warp runners are offline'
    
    # Process all YAML files
    for yaml_file in workflow_path.rglob("*.yml"):
        content = yaml_file.read_text(encoding='utf-8')
        
        if 'warp-custom-default' in content:
            # Replace the runner
            new_content = pattern.sub(replacement, content)
            
            # Write back
            yaml_file.write_text(new_content, encoding='utf-8')
            updated_files.append(str(yaml_file))
            print(f"[OK] Updated: {yaml_file}")
    
    return updated_files

def main():
    print("[INFO] Switching from Warp runners to GitHub-hosted runners...")
    print("-" * 50)
    
    updated = update_runners()
    
    print("-" * 50)
    print(f"[DONE] Updated {len(updated)} workflow files")
    print("\n[WARNING] IMPORTANT: This is a temporary fix!")
    print("Once Warp runners are back online, revert with:")
    print("  git checkout -- .github/workflows/")
    
    if updated:
        print("\nUpdated files:")
        for f in updated:
            print(f"  - {f}")

if __name__ == "__main__":
    main()