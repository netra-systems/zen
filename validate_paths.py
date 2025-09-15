#!/usr/bin/env python3
"""
Simple Dockerfile Path Validation for Issue #782
"""
import os
from pathlib import Path

def validate_dockerfile_paths():
    """Validate dockerfile paths exist"""
    print("=== Issue #782 Dockerfile Path Validation ===")

    # Check if root dockerfiles directory exists
    root_dockerfiles = Path("dockerfiles")
    print(f"Root dockerfiles directory exists: {root_dockerfiles.exists()}")

    if root_dockerfiles.exists():
        alpine_files = list(root_dockerfiles.glob("*.alpine.Dockerfile"))
        print(f"Found {len(alpine_files)} Alpine Dockerfiles in root:")
        for f in alpine_files:
            print(f"  - {f.name}")

    # Check if docker/dockerfiles exists (expected by current config)
    docker_dockerfiles = Path("docker/dockerfiles")
    print(f"Docker/dockerfiles directory exists: {docker_dockerfiles.exists()}")

    # Test paths from docker directory context
    docker_dir = Path("docker")
    print(f"\nTesting paths from docker directory:")

    required_files = [
        "dockerfiles/migration.alpine.Dockerfile",
        "dockerfiles/backend.alpine.Dockerfile",
        "dockerfiles/auth.alpine.Dockerfile",
        "dockerfiles/frontend.alpine.Dockerfile"
    ]

    print("\nCurrent paths (relative to docker/):")
    current_working = 0
    for file_path in required_files:
        full_path = docker_dir / file_path
        exists = full_path.exists()
        print(f"  {file_path}: {'EXISTS' if exists else 'MISSING'}")
        if exists:
            current_working += 1

    print("\nProposed fix paths (../dockerfiles/):")
    fixed_working = 0
    for file_path in required_files:
        fixed_path = file_path.replace("dockerfiles/", "../dockerfiles/")
        full_path = docker_dir / fixed_path
        exists = full_path.exists()
        print(f"  {fixed_path}: {'EXISTS' if exists else 'MISSING'}")
        if exists:
            fixed_working += 1

    print(f"\n=== RESULTS ===")
    print(f"Current config working files: {current_working}/{len(required_files)}")
    print(f"Proposed fix working files: {fixed_working}/{len(required_files)}")

    if current_working == 0 and fixed_working == len(required_files):
        print("RESOLUTION: Update paths from dockerfiles/ to ../dockerfiles/")
        return True
    elif current_working == len(required_files):
        print("STATUS: Already working")
        return True
    else:
        print("ISSUE: Neither current nor proposed fix works")
        return False

if __name__ == "__main__":
    validate_dockerfile_paths()