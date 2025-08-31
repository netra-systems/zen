"""
Migration State Diagnostic and Recovery Script

This script helps diagnose and fix critical migration state issues, specifically:
- Databases with existing schema but no alembic_version table
- Corrupted or inconsistent migration tracking
- Recovery and repair of migration states

Usage:
    python scripts/diagnose_migration_state.py --diagnose
    python scripts/diagnose_migration_state.py --recover  
    python scripts/diagnose_migration_state.py --status

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide operational tools to prevent and fix migration failures  
- Value Impact: Eliminates manual intervention for migration state issues
- Strategic Impact: Enables reliable deployments and system recovery
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from netra_backend.app.db.alembic_state_recovery import (
    MigrationStateManager,
    MigrationStateAnalyzer,
    AlembicStateRecovery,
    ensure_migration_state_healthy,
    analyze_migration_state
)
from shared.isolated_environment import IsolatedEnvironment


class MigrationStateDiagnostic:
    """Command-line tool for migration state diagnosis and recovery."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.database_url = None
        
    async def initialize(self):
        """Initialize the diagnostic tool."""
        # Get database URL from environment
        await self.env.load_environment()
        self.database_url = await self.env.get_database_url()
        
        if not self.database_url:
            print("❌ ERROR: No database URL configured")
            print("   Set NETRA_DATABASE_URL environment variable")
            sys.exit(1)
            
        print(f"🔍 Using database: {self._mask_database_url(self.database_url)}")
    
    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive parts of database URL for display."""
        if "@" in url:
            scheme_user, host_db = url.split("@", 1)
            if ":" in scheme_user:
                scheme, user_pass = scheme_user.split("://", 1)
                if ":" in user_pass:
                    user, _ = user_pass.split(":", 1)
                    return f"{scheme}://{user}:***@{host_db}"
        return url
    
    async def diagnose(self, detailed: bool = False) -> Dict[str, Any]:
        """Diagnose current migration state."""
        print("🔍 Diagnosing migration state...")
        
        try:
            state = await analyze_migration_state(self.database_url)
            
            # Display diagnosis results
            self._display_diagnosis_results(state, detailed)
            
            return state
            
        except Exception as e:
            print(f"❌ ERROR: Failed to diagnose migration state: {e}")
            return {"error": str(e)}
    
    def _display_diagnosis_results(self, state: Dict[str, Any], detailed: bool):
        """Display diagnosis results in user-friendly format."""
        print("\n" + "="*60)
        print("📊 MIGRATION STATE DIAGNOSIS RESULTS")
        print("="*60)
        
        if "error" in state:
            print(f"❌ Analysis failed: {state['error']}")
            return
        
        # Basic state information
        print(f"📋 Schema exists: {'✅' if state.get('has_existing_schema') else '❌'}")
        print(f"📋 Alembic version table: {'✅' if state.get('has_alembic_version') else '❌'}")
        print(f"📋 Requires recovery: {'⚠️ YES' if state.get('requires_recovery') else '✅ NO'}")
        print(f"📋 Recovery strategy: {state.get('recovery_strategy', 'UNKNOWN')}")
        
        if state.get('current_revision'):
            print(f"📋 Current revision: {state['current_revision']}")
        
        # Existing tables
        if state.get('existing_tables'):
            print(f"\n📋 Existing tables ({len(state['existing_tables'])}):")
            for table in sorted(state['existing_tables']):
                print(f"   • {table}")
        
        # Missing tables (if any)
        if state.get('missing_expected_tables'):
            print(f"\n⚠️  Missing expected tables ({len(state['missing_expected_tables'])}):")
            for table in sorted(state['missing_expected_tables']):
                print(f"   • {table}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if state.get('requires_recovery'):
            strategy = state.get('recovery_strategy', '')
            
            if strategy == "INITIALIZE_ALEMBIC_VERSION":
                print("   🔧 Run: python scripts/diagnose_migration_state.py --recover")
                print("      This will initialize alembic_version table for existing schema")
                
            elif strategy == "COMPLETE_PARTIAL_MIGRATION":
                print("   🔧 Run migrations to complete partial schema")
                print("      python scripts/diagnose_migration_state.py --recover")
                
            elif strategy == "REPAIR_CORRUPTED_ALEMBIC":
                print("   🔧 Repair corrupted alembic_version table")
                print("      python scripts/diagnose_migration_state.py --recover")
                
            else:
                print("   🔧 Manual inspection may be required")
                print(f"      Strategy: {strategy}")
        else:
            print("   ✅ Migration state is healthy - no action needed")
        
        if detailed:
            print(f"\n🔍 DETAILED STATE INFORMATION:")
            print(json.dumps(state, indent=2, default=str))
    
    async def recover(self, dry_run: bool = False) -> bool:
        """Attempt to recover migration state."""
        if dry_run:
            print("🏃‍♂️ DRY RUN: Would attempt migration state recovery...")
        else:
            print("🔧 Attempting migration state recovery...")
        
        try:
            if dry_run:
                # Just analyze without making changes
                state = await analyze_migration_state(self.database_url)
                print(f"Would apply recovery strategy: {state.get('recovery_strategy')}")
                return True
            else:
                # Perform actual recovery
                success, recovery_info = await ensure_migration_state_healthy(self.database_url)
                
                if success:
                    print("✅ Migration state recovery completed successfully!")
                    print(f"Recovery info: {recovery_info.get('recovery_strategy', 'Unknown')}")
                    return True
                else:
                    print("❌ Migration state recovery failed")
                    print(f"Recovery info: {recovery_info}")
                    return False
                    
        except Exception as e:
            print(f"❌ ERROR: Recovery failed: {e}")
            return False
    
    async def status(self) -> Dict[str, Any]:
        """Get comprehensive migration status."""
        print("📊 Getting migration status...")
        
        try:
            manager = MigrationStateManager(self.database_url)
            report = await manager.get_migration_status_report()
            
            # Display status report
            self._display_status_report(report)
            
            return report
            
        except Exception as e:
            print(f"❌ ERROR: Failed to get status: {e}")
            return {"error": str(e)}
    
    def _display_status_report(self, report: Dict[str, Any]):
        """Display comprehensive status report."""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE MIGRATION STATUS REPORT")
        print("="*60)
        
        print(f"🔗 Database: {self._mask_database_url(report.get('database_url', 'Unknown'))}")
        print(f"💚 Health Status: {report.get('health_status', 'Unknown')}")
        print(f"🔧 Recommended Action: {report.get('recommended_action', 'Unknown')}")
        print(f"⏰ Report Time: {report.get('timestamp', 'Unknown')}")
        
        # Migration state details
        if 'migration_state' in report:
            state = report['migration_state']
            print(f"\n📋 MIGRATION STATE DETAILS:")
            print(f"   Schema Exists: {'Yes' if state.get('has_existing_schema') else 'No'}")
            print(f"   Alembic Tracking: {'Yes' if state.get('has_alembic_version') else 'No'}")
            print(f"   Current Revision: {state.get('current_revision', 'None')}")
            print(f"   Table Count: {len(state.get('existing_tables', []))}")
        
        print(f"\n📄 FULL REPORT:")
        print(json.dumps(report, indent=2, default=str))
    
    async def interactive_mode(self):
        """Run in interactive mode for step-by-step recovery."""
        print("🎛️  INTERACTIVE MIGRATION RECOVERY MODE")
        print("="*50)
        
        # Step 1: Diagnose
        state = await self.diagnose(detailed=False)
        
        if not state.get('requires_recovery'):
            print("\n✅ Migration state is healthy - no recovery needed!")
            return
        
        # Step 2: Ask for recovery
        print(f"\n⚠️  Recovery needed: {state.get('recovery_strategy')}")
        response = input("Would you like to proceed with recovery? (y/N): ").lower().strip()
        
        if response in ['y', 'yes']:
            print("\n🔧 Proceeding with recovery...")
            success = await self.recover(dry_run=False)
            
            if success:
                print("\n🎉 Recovery completed! Re-diagnosing...")
                await self.diagnose(detailed=False)
            else:
                print("\n❌ Recovery failed - manual intervention may be required")
        else:
            print("\n⏭️  Recovery skipped - you can run it later with --recover")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnose and recover database migration state issues"
    )
    parser.add_argument(
        "--diagnose", action="store_true", 
        help="Diagnose current migration state"
    )
    parser.add_argument(
        "--recover", action="store_true",
        help="Attempt to recover migration state"
    )
    parser.add_argument(
        "--status", action="store_true", 
        help="Get comprehensive migration status"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Run in interactive mode"
    )
    parser.add_argument(
        "--detailed", "-d", action="store_true",
        help="Show detailed information"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Create diagnostic tool
    diagnostic = MigrationStateDiagnostic()
    await diagnostic.initialize()
    
    # Execute requested operation
    if args.interactive:
        await diagnostic.interactive_mode()
    elif args.diagnose:
        await diagnostic.diagnose(detailed=args.detailed)
    elif args.recover:
        await diagnostic.recover(dry_run=args.dry_run)
    elif args.status:
        await diagnostic.status()
    else:
        # Default to interactive mode
        print("No specific action requested - running in interactive mode")
        await diagnostic.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())