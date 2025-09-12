#!/usr/bin/env python3
"""Run complete database regression test suite.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)
- Business Goal: Prevent database-related regressions that cause service outages
- Value Impact: Ensures database reliability and prevents customer-facing issues
- Strategic Impact: Maintains system stability and reduces incident response costs

This runner executes all database regression tests to verify:
1. SQLAlchemy session lifecycle management
2. Database schema consistency
3. Error handling and recovery
4. Concurrent operation safety
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from netra_backend.app.logging_config import central_logger as logger


class RegressionTestRunner:
    """Orchestrates database regression test execution."""
    
    def __init__(self):
        self.console = Console()
        self.results: Dict[str, Dict] = {}
        self.start_time = None
        self.end_time = None
    
    def run_tests(self, verbose: bool = False, specific_test: Optional[str] = None) -> int:
        """Run all regression tests or a specific test.
        
        Args:
            verbose: Enable verbose output
            specific_test: Run only a specific test file
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.start_time = time.time()
        
        self.console.print("\n[bold blue] SEARCH:  Database Regression Test Suite[/bold blue]\n")
        
        # Define test modules
        test_modules = [
            "test_session_lifecycle_regression.py",
            "test_schema_consistency_regression.py"
        ]
        
        if specific_test:
            test_modules = [t for t in test_modules if specific_test in t]
            if not test_modules:
                self.console.print(f"[red]Test '{specific_test}' not found[/red]")
                return 1
        
        # Run tests with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            
            overall_success = True
            
            for test_module in test_modules:
                task = progress.add_task(f"Running {test_module}...", total=None)
                
                # Run pytest for each module
                test_path = Path(__file__).parent / test_module
                
                args = [str(test_path), "--asyncio-mode=auto", "--tb=short"]
                if verbose:
                    args.append("-v")
                else:
                    args.append("-q")
                
                result = pytest.main(args)
                
                # Store results
                self.results[test_module] = {
                    "status": "PASSED" if result == 0 else "FAILED",
                    "exit_code": result
                }
                
                if result != 0:
                    overall_success = False
                
                progress.update(task, completed=True)
        
        self.end_time = time.time()
        
        # Display results
        self._display_results()
        
        return 0 if overall_success else 1
    
    def _display_results(self):
        """Display test results in a formatted table."""
        table = Table(title="Regression Test Results", show_header=True)
        table.add_column("Test Module", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Details")
        
        for module, result in self.results.items():
            status = result["status"]
            status_style = "green" if status == "PASSED" else "red"
            
            details = ""
            if result["exit_code"] != 0:
                details = f"Exit code: {result['exit_code']}"
            
            table.add_row(
                module,
                f"[{status_style}]{status}[/{status_style}]",
                details
            )
        
        self.console.print("\n")
        self.console.print(table)
        
        # Summary
        duration = self.end_time - self.start_time
        passed = sum(1 for r in self.results.values() if r["status"] == "PASSED")
        failed = sum(1 for r in self.results.values() if r["status"] == "FAILED")
        
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"  Total: {len(self.results)} test modules")
        self.console.print(f"  [green]Passed: {passed}[/green]")
        if failed > 0:
            self.console.print(f"  [red]Failed: {failed}[/red]")
        self.console.print(f"  Duration: {duration:.2f}s")
        
        if failed == 0:
            self.console.print("\n[bold green] PASS:  All regression tests passed![/bold green]")
        else:
            self.console.print("\n[bold red] FAIL:  Some regression tests failed![/bold red]")
    
    async def run_health_checks(self) -> bool:
        """Run pre-test health checks.
        
        Returns:
            True if all health checks pass
        """
        self.console.print("[yellow]Running pre-test health checks...[/yellow]")
        
        from netra_backend.app.db.database_manager import DatabaseManager
        
        try:
            # Test database connection
            engine = DatabaseManager.create_application_engine()
            success = await DatabaseManager.test_connection_with_retry(engine)
            
            if not success:
                self.console.print("[red] FAIL:  Database connection failed[/red]")
                return False
            
            self.console.print("[green][U+2713] Database connection successful[/green]")
            
            # Check for required tables
            from sqlalchemy import text
            async with engine.begin() as conn:
                result = await conn.execute(text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('threads', 'messages', 'assistants', 'runs')
                """))
                count = result.scalar()
                
                if count < 4:
                    self.console.print(f"[red] FAIL:  Missing required tables (found {count}/4)[/red]")
                    self.console.print("[yellow]Run migrations: python netra_backend/app/alembic/run_migrations.py[/yellow]")
                    return False
                
                self.console.print(f"[green][U+2713] Required tables exist ({count}/4)[/green]")
            
            await engine.dispose()
            return True
            
        except Exception as e:
            self.console.print(f"[red] FAIL:  Health check error: {e}[/red]")
            return False


async def main():
    """Main entry point for regression test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database regression test suite")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-t", "--test", help="Run specific test module")
    parser.add_argument("--skip-health", action="store_true", help="Skip health checks")
    
    args = parser.parse_args()
    
    runner = RegressionTestRunner()
    
    # Run health checks unless skipped
    if not args.skip_health:
        health_ok = await runner.run_health_checks()
        if not health_ok:
            runner.console.print("\n[red]Health checks failed. Fix issues before running tests.[/red]")
            return 1
    
    # Run tests
    exit_code = runner.run_tests(verbose=args.verbose, specific_test=args.test)
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[yellow]Test suite interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)