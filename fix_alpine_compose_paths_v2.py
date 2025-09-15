#!/usr/bin/env python3
"""
Fix path references in docker-compose.alpine-dev.yml
Replace Alpine Dockerfile references with regular Dockerfile references
"""
import os

def fix_compose_file():
    # Use absolute Windows path
    file_path = r"C:\netra-apex\docker\docker-compose.alpine-dev.yml"

    print(f"Checking file path: {file_path}")
    print(f"File exists: {os.path.exists(file_path)}")

    # Read the original file
    with open(file_path, 'r') as f:
        content = f.read()

    # Fix the three broken path references
    content = content.replace("docker/backend.alpine.Dockerfile", "dockerfiles/backend.Dockerfile")
    content = content.replace("docker/auth.alpine.Dockerfile", "dockerfiles/auth.Dockerfile")
    content = content.replace("docker/frontend.alpine.Dockerfile", "dockerfiles/frontend.Dockerfile")

    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)

    print("✅ Fixed 3 broken path references in docker-compose.alpine-dev.yml")
    print("   - docker/backend.alpine.Dockerfile → dockerfiles/backend.Dockerfile")
    print("   - docker/auth.alpine.Dockerfile → dockerfiles/auth.Dockerfile")
    print("   - docker/frontend.alpine.Dockerfile → dockerfiles/frontend.Dockerfile")

if __name__ == "__main__":
    fix_compose_file()