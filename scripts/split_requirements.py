#!/usr/bin/env python3
"""
Split requirements.txt into layers for optimized Docker caching.
This allows rarely-changing dependencies to be cached separately.
"""

import re
from pathlib import Path
from typing import Dict, List, Set

# Define dependency tiers by change frequency
DEPENDENCY_TIERS = {
    "core": {
        # Web framework core - very stable
        "fastapi", "uvicorn", "gunicorn", "starlette",
        # Database core - stable  
        "sqlalchemy", "asyncpg", "psycopg2-binary", "alembic",
        # Data validation - stable
        "pydantic", "email-validator",
        # Caching - stable
        "redis",
    },
    "infrastructure": {
        # Cloud services
        "cloud-sql-python-connector", "google-cloud-secret-manager",
        "google-cloud-storage", "google-cloud-logging",
        # Authentication
        "PyJWT", "passlib", "bcrypt", "authlib",
        # HTTP clients
        "httpx", "aiohttp", "requests",
    },
    "ai": {
        # AI/ML libraries
        "openai", "anthropic", "langchain", "langchain-community",
        "tiktoken", "faiss-cpu", "chromadb",
        # Data processing
        "numpy", "pandas", "scipy",
    },
    "analytics": {
        # Analytics and monitoring
        "clickhouse-connect", "lz4",
        "opentelemetry-api", "opentelemetry-sdk",
        "opentelemetry-instrumentation-fastapi",
        "sentry-sdk",
    },
    "app": {
        # Application specific - changes frequently
        # Everything else goes here
    }
}

def parse_requirement_name(line: str) -> str:
    """Extract package name from requirement line."""
    # Remove comments
    line = line.split("#")[0].strip()
    if not line:
        return ""
    
    # Extract package name (before any version specifier)
    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
    if match:
        return match.group(1).lower()
    
    # Handle packages with brackets like PyJWT[cryptography]
    match = re.match(r'^([a-zA-Z0-9_-]+)\[', line)
    if match:
        return match.group(1).lower()
    
    return ""

def categorize_requirements(requirements_path: Path) -> Dict[str, List[str]]:
    """Categorize requirements by tier."""
    categorized = {tier: [] for tier in DEPENDENCY_TIERS}
    categorized["app"] = []  # For uncategorized deps
    
    # Track which packages have been categorized
    categorized_packages: Set[str] = set()
    
    with open(requirements_path, 'r') as f:
        lines = f.readlines()
    
    # First pass: categorize known packages
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        pkg_name = parse_requirement_name(line)
        if not pkg_name:
            continue
        
        # Check each tier
        for tier, packages in DEPENDENCY_TIERS.items():
            if pkg_name in packages:
                categorized[tier].append(line)
                categorized_packages.add(pkg_name)
                break
    
    # Second pass: add uncategorized to app tier  
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        pkg_name = parse_requirement_name(line)
        if pkg_name and pkg_name not in categorized_packages:
            categorized["app"].append(line)
    
    return categorized

def write_tiered_requirements(categorized: Dict[str, List[str]], output_dir: Path):
    """Write separate requirements files for each tier."""
    output_dir.mkdir(exist_ok=True)
    
    for tier, requirements in categorized.items():
        if not requirements:
            continue
            
        output_file = output_dir / f"requirements-{tier}.txt"
        with open(output_file, 'w') as f:
            f.write(f"# {tier.upper()} tier dependencies\n")
            f.write(f"# Change frequency: {'Very Low' if tier == 'core' else 'Low' if tier == 'infrastructure' else 'Medium' if tier in ['ai', 'analytics'] else 'High'}\n\n")
            for req in sorted(requirements):
                f.write(f"{req}\n")
        
        print(f"Written {len(requirements)} packages to {output_file}")

def generate_dockerfile_snippet(categorized: Dict[str, List[str]]) -> str:
    """Generate optimized Dockerfile snippet for tiered installation."""
    snippet = """
# Optimized dependency installation with tiered caching
# Each RUN command creates a separate layer that can be cached independently

"""
    
    for i, tier in enumerate(["core", "infrastructure", "ai", "analytics", "app"]):
        if tier not in categorized or not categorized[tier]:
            continue
            
        snippet += f"""# Layer {i+1}: {tier.upper()} dependencies
COPY requirements-{tier}.txt .
RUN --mount=type=cache,target=/root/.cache/pip,id=pip-{tier} \\
    pip install --user -r requirements-{tier}.txt

"""
    
    return snippet

def main():
    """Main function to split requirements."""
    project_root = Path(__file__).parent.parent
    requirements_path = project_root / "requirements.txt"
    output_dir = project_root / "docker" / "requirements"
    
    if not requirements_path.exists():
        print(f"Error: {requirements_path} not found")
        return 1
    
    print(f"Analyzing {requirements_path}...")
    categorized = categorize_requirements(requirements_path)
    
    # Print summary
    print("\nDependency categorization summary:")
    for tier, deps in categorized.items():
        if deps:
            print(f"  {tier:15} : {len(deps)} packages")
    
    # Write tiered requirements
    write_tiered_requirements(categorized, output_dir)
    
    # Generate Dockerfile snippet
    snippet = generate_dockerfile_snippet(categorized)
    snippet_file = output_dir / "dockerfile-snippet.txt"
    with open(snippet_file, 'w') as f:
        f.write(snippet)
    print(f"\nDockerfile snippet written to {snippet_file}")
    
    print("\n PASS:  Requirements split successfully!")
    print(f"Files created in {output_dir}/")
    
    return 0

if __name__ == "__main__":
    exit(main())