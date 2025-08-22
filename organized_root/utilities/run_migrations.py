#!/usr/bin/env python3
"""
Staging Database Migration Script
Python equivalent of run-staging-migrations.ps1

Runs database migrations against the staging environment.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Configuration
PROJECT_ID = "netra-staging"

# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False, 
                env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        # Merge environment variables
        final_env = os.environ.copy()
        if env:
            final_env.update(env)
            
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            env=final_env
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in the system PATH."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            return result.returncode == 0
        else:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            return result.returncode == 0
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def get_database_url(project_id: str) -> Optional[str]:
    """Get database URL from Google Secret Manager."""
    print_colored("Retrieving database URL from Google Secret Manager...", Colors.YELLOW)
    
    try:
        result = run_command([
            "gcloud", "secrets", "versions", "access", "latest",
            "--secret", "database-url-staging",
            "--project", project_id
        ], capture_output=True)
        
        db_url = result.stdout.strip()
        if db_url:
            print_colored("  Database URL retrieved successfully", Colors.GREEN)
            return db_url
        else:
            print_colored("Failed to retrieve database URL from secrets", Colors.RED)
            return None
            
    except subprocess.CalledProcessError:
        print_colored("Failed to retrieve database URL from secrets", Colors.RED)
        return None
    except Exception as e:
        print_colored(f"Error retrieving database URL: {e}", Colors.RED)
        return None


def check_migration_status(db_url: str) -> bool:
    """Check current migration status."""
    print_colored("Checking current migration status...", Colors.YELLOW)
    
    env = {"DATABASE_URL": db_url}
    
    try:
        # Get current revision
        current_result = run_command([
            "python", "-m", "alembic", "-c", "config/alembic.ini", "current"
        ], capture_output=True, env=env)
        
        current_revision = current_result.stdout.strip()
        
        # Get head revision
        head_result = run_command([
            "python", "-m", "alembic", "-c", "config/alembic.ini", "heads"
        ], capture_output=True, env=env)
        
        head_revision = head_result.stdout.strip()
        
        print_colored(f"  Current revision: {current_revision}", Colors.CYAN)
        print_colored(f"  Head revision: {head_revision}", Colors.CYAN)
        
        # Check if migration is needed
        if "head" in current_revision:
            print_colored("  Database is up-to-date", Colors.GREEN)
            return True
        else:
            print_colored("  Migration needed", Colors.YELLOW)
            return False
            
    except subprocess.CalledProcessError:
        print_colored("Failed to check migration status", Colors.RED)
        return False


def run_migrations(db_url: str) -> bool:
    """Run database migrations."""
    print_colored("Running database migrations...", Colors.YELLOW)
    
    env = {"DATABASE_URL": db_url}
    
    try:
        # Run migrations to head
        result = run_command([
            "python", "-m", "alembic", "-c", "config/alembic.ini", "upgrade", "head"
        ], capture_output=True, env=env)
        
        print_colored("  Migrations completed successfully", Colors.GREEN)
        if result.stdout:
            print_colored(result.stdout, Colors.GRAY)
        return True
        
    except subprocess.CalledProcessError as e:
        print_colored("  Migration failed!", Colors.RED)
        if e.stdout:
            print_colored(e.stdout, Colors.RED)
        if e.stderr:
            print_colored(e.stderr, Colors.RED)
        return False


def check_prerequisites() -> bool:
    """Check if all required tools are available."""
    missing_tools = []
    
    if not check_command_exists("python"):
        missing_tools.append("python")
    
    if not check_command_exists("gcloud"):
        missing_tools.append("gcloud (Google Cloud SDK)")
    
    if missing_tools:
        print_colored(f"Error: Missing required tools: {', '.join(missing_tools)}", Colors.RED)
        return False
    
    # Check if alembic.ini exists
    if not Path("config/alembic.ini").exists():
        print_colored("Error: alembic.ini not found at config/alembic.ini", Colors.RED)
        print_colored("Please run this script from the project root directory", Colors.RED)
        return False
    
    return True


def main():
    """Main function to orchestrate the migration process."""
    parser = argparse.ArgumentParser(description="Netra Staging Database Migrations")
    parser.add_argument("--force-run", action="store_true", 
                       help="Force run migrations even if database appears up-to-date")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check migration status, don't run migrations")
    parser.add_argument("--project-id", default=PROJECT_ID,
                       help=f"GCP Project ID (default: {PROJECT_ID})")
    
    args = parser.parse_args()
    
    print_colored("=" * 48, Colors.BLUE)
    print_colored("    NETRA STAGING DATABASE MIGRATIONS", Colors.BLUE)
    print_colored("=" * 48, Colors.BLUE)
    print_colored("")
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Get database URL
    db_url = get_database_url(args.project_id)
    if not db_url:
        print_colored("Cannot proceed without database URL", Colors.RED)
        sys.exit(1)
    
    # Check migration status
    is_up_to_date = check_migration_status(db_url)
    
    if args.check_only:
        if is_up_to_date:
            print_colored("")
            print_colored("No migrations needed", Colors.GREEN)
            sys.exit(0)
        else:
            print_colored("")
            print_colored("Migrations are needed", Colors.YELLOW)
            sys.exit(0)
    
    # Run migrations if needed
    if is_up_to_date and not args.force_run:
        print_colored("")
        print_colored("No migrations needed", Colors.GREEN)
    else:
        if args.force_run:
            print_colored("")
            print_colored("Force running migrations...", Colors.YELLOW)
        
        success = run_migrations(db_url)
        
        if success:
            print_colored("")
            print_colored("Database migrations completed successfully!", Colors.GREEN)
            
            # Verify final status
            final_status = check_migration_status(db_url)
            if not final_status:
                print_colored("Warning: Database may still need migrations", Colors.YELLOW)
                sys.exit(1)
        else:
            print_colored("")
            print_colored("Migration failed! Please check the error messages above.", Colors.RED)
            sys.exit(1)
    
    print_colored("")
    print_colored("Migration process completed", Colors.GREEN)


if __name__ == "__main__":
    main()