#!/usr/bin/env python3
"""
WebSocket v2 Critical Services Migration Script

This script migrates critical production services from the deprecated singleton
`get_websocket_manager()` pattern to the new factory pattern `create_websocket_manager(user_context)`.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise)
- Business Goal: Eliminate critical WebSocket isolation vulnerabilities 
- Value Impact: Prevents user data cross-contamination and connection hijacking
- Revenue Impact: Prevents catastrophic security breaches that could destroy business trust

SECURITY CRITICAL: This migration addresses:
1. User isolation failures causing data leakage between users
2. Shared state mutations affecting all concurrent users
3. Connection hijacking and message misdirection
4. Race conditions in multi-user concurrent operations
5. Silent failures masking security violations

Usage:
    python scripts/migrate_websocket_v2_critical_services.py [--dry-run] [--backup-dir PATH]
    
    Options:
        --dry-run: Show what would be changed without making modifications
        --backup-dir: Custom directory for backup files (default: backups/websocket_v2_migration_TIMESTAMP)
        --force: Override safety checks and perform migration
        --validate-only: Only validate current state, don't migrate
        
Examples:
    # Dry run to see what would change
    python scripts/migrate_websocket_v2_critical_services.py --dry-run
    
    # Perform migration with default backup
    python scripts/migrate_websocket_v2_critical_services.py --force
    
    # Validate current state only
    python scripts/migrate_websocket_v2_critical_services.py --validate-only
"""

import argparse
import ast
import asyncio
import os
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MigrationConfig:
    """Configuration for the WebSocket v2 migration."""
    # Target services directory
    services_root: Path = Path("netra_backend/app/services")
    
    # Critical services that MUST be migrated
    critical_services: Set[str] = field(default_factory=lambda: {
        "agent_service_core.py",
        "agent_service_factory.py", 
        "message_handler_base.py",
        "message_handler_utils.py",
        "thread_service.py",
        "generation_job_manager.py",
        # WebSocket quality services
        "websocket/quality_manager.py",
        "websocket/quality_message_router.py",
        "websocket/quality_validation_handler.py",
        "websocket/quality_report_handler.py", 
        "websocket/quality_metrics_handler.py",
        "websocket/quality_alert_handler.py",
        "websocket/message_handler.py",
        "websocket/message_queue.py",
        # Additional critical services
        "corpus/clickhouse_operations.py",
        "memory_startup_integration.py",
        "websocket_event_router.py"
    })
    
    # Patterns to identify deprecated usage
    deprecated_patterns: List[str] = field(default_factory=lambda: [
        r"from\s+.*\s+import\s+.*get_websocket_manager",
        r"get_websocket_manager\s*\(\s*\)",
        r"websocket_manager\s*=\s*get_websocket_manager\s*\(\s*\)"
    ])
    
    # Import replacements
    import_replacements: Dict[str, str] = field(default_factory=lambda: {
        "from netra_backend.app.websocket_core import get_websocket_manager": 
            "from netra_backend.app.websocket_core import create_websocket_manager",
        "from netra_backend.app.websocket_core import get_websocket_manager, create_websocket_manager":
            "from netra_backend.app.websocket_core import create_websocket_manager",
        "from netra_backend.app.websocket_core.unified_manager import get_websocket_manager":
            "from netra_backend.app.websocket_core import create_websocket_manager"
    })

@dataclass 
class ServiceAnalysis:
    """Analysis results for a service file."""
    file_path: Path
    has_deprecated_usage: bool = False
    deprecated_imports: List[str] = field(default_factory=list)
    deprecated_calls: List[Tuple[int, str]] = field(default_factory=list)  # (line_number, line_content)
    user_context_available: bool = False
    user_context_sources: List[str] = field(default_factory=list)
    complexity_score: int = 0  # 1=simple, 5=very complex
    migration_notes: List[str] = field(default_factory=list)
    backup_created: bool = False
    migration_successful: bool = False
    
@dataclass
class MigrationReport:
    """Comprehensive migration report."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_services_analyzed: int = 0
    services_with_deprecated_usage: int = 0
    services_migrated_successfully: int = 0
    services_failed_migration: int = 0
    critical_issues_found: List[str] = field(default_factory=list)
    backup_directory: Optional[Path] = None
    detailed_results: Dict[str, ServiceAnalysis] = field(default_factory=dict)
    dry_run: bool = False
    
    def to_markdown(self) -> str:
        """Generate detailed markdown report."""
        duration = (self.end_time - self.start_time) if self.end_time else "N/A"
        
        report = f"""# WebSocket v2 Critical Services Migration Report

## Summary

**Migration Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration}
**Mode:** {"DRY RUN" if self.dry_run else "LIVE MIGRATION"}

### Statistics
- **Total Services Analyzed:** {self.total_services_analyzed}
- **Services with Deprecated Usage:** {self.services_with_deprecated_usage}
- **Services Successfully Migrated:** {self.services_migrated_successfully}
- **Services Failed Migration:** {self.services_failed_migration}
- **Success Rate:** {(self.services_migrated_successfully / max(1, self.services_with_deprecated_usage)) * 100:.1f}%

"""
        
        if self.backup_directory:
            report += f"**Backup Directory:** {self.backup_directory}\n\n"
            
        if self.critical_issues_found:
            report += "## 🚨 Critical Issues Found\n\n"
            for issue in self.critical_issues_found:
                report += f"- {issue}\n"
            report += "\n"
        
        # Detailed service results
        report += "## Detailed Service Analysis\n\n"
        
        for service_name, analysis in self.detailed_results.items():
            report += f"### {service_name}\n\n"
            
            if analysis.has_deprecated_usage:
                report += "**Status:** ⚠️ Needs Migration\n\n"
                
                if analysis.deprecated_imports:
                    report += "**Deprecated Imports:**\n"
                    for imp in analysis.deprecated_imports:
                        report += f"- `{imp}`\n"
                    report += "\n"
                
                if analysis.deprecated_calls:
                    report += "**Deprecated Calls:**\n"
                    for line_num, line_content in analysis.deprecated_calls:
                        report += f"- Line {line_num}: `{line_content.strip()}`\n"
                    report += "\n"
                
                if analysis.user_context_sources:
                    report += "**User Context Sources:**\n"
                    for source in analysis.user_context_sources:
                        report += f"- {source}\n"
                    report += "\n"
                else:
                    report += "**⚠️ No User Context Found - Manual intervention required**\n\n"
                
                report += f"**Complexity Score:** {analysis.complexity_score}/5\n\n"
                
                if analysis.migration_notes:
                    report += "**Migration Notes:**\n"
                    for note in analysis.migration_notes:
                        report += f"- {note}\n"
                    report += "\n"
                    
                if self.dry_run:
                    report += "**Status:** Will be migrated in live run\n\n"
                else:
                    status = "✅ Successfully Migrated" if analysis.migration_successful else "❌ Migration Failed"
                    report += f"**Status:** {status}\n\n"
            else:
                report += "**Status:** ✅ No migration needed\n\n"
                
        return report

class WebSocketV2Migrator:
    """Main migration class for WebSocket v2 factory pattern."""
    
    def __init__(self, config: MigrationConfig, backup_dir: Optional[Path] = None):
        """Initialize migrator with configuration."""
        self.config = config
        self.backup_dir = backup_dir or Path(f"backups/websocket_v2_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.report = MigrationReport(start_time=datetime.now())
        self.report.backup_directory = self.backup_dir
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Current working directory context
        self.project_root = Path.cwd()
        
    def analyze_service_file(self, file_path: Path) -> ServiceAnalysis:
        """Analyze a service file for deprecated WebSocket usage."""
        logger.info(f"Analyzing {file_path.relative_to(self.project_root)}")
        
        analysis = ServiceAnalysis(file_path=file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
                
            # Check for deprecated imports
            for pattern in [
                r"from\s+.*\s+import\s+.*get_websocket_manager",
                r"import\s+.*get_websocket_manager"
            ]:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                    analysis.deprecated_imports.append(line_content.strip())
                    analysis.has_deprecated_usage = True
            
            # Check for deprecated function calls
            pattern = r"get_websocket_manager\s*\(\s*\)"
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                analysis.deprecated_calls.append((line_num, line_content))
                analysis.has_deprecated_usage = True
            
            # Check for user context availability
            user_context_patterns = [
                r"UserExecutionContext",
                r"user_context\s*:",
                r"def\s+\w+.*user_context.*\)",
                r"self\.user_context",
                r"context\s*=.*user.*context"
            ]
            
            for pattern in user_context_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    analysis.user_context_available = True
                    # Find the specific line for context
                    matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        if line_num <= len(lines):
                            analysis.user_context_sources.append(f"Line {line_num}: {lines[line_num-1].strip()}")
                    break
            
            # Calculate complexity score
            analysis.complexity_score = self._calculate_complexity_score(content, analysis)
            
            # Add migration notes
            analysis.migration_notes = self._generate_migration_notes(analysis, content)
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            analysis.migration_notes.append(f"Analysis error: {e}")
            
        return analysis
    
    def _calculate_complexity_score(self, content: str, analysis: ServiceAnalysis) -> int:
        """Calculate migration complexity score (1-5)."""
        score = 1
        
        # Add complexity for each deprecated usage
        score += min(len(analysis.deprecated_calls), 2)
        
        # Add complexity if no user context is readily available
        if not analysis.user_context_available:
            score += 2
            
        # Add complexity for inheritance patterns
        if re.search(r"class\s+\w+.*\([^)]*Service[^)]*\)", content):
            score += 1
            
        # Add complexity for async patterns
        if content.count("async def") > 5:
            score += 1
            
        return min(score, 5)
    
    def _generate_migration_notes(self, analysis: ServiceAnalysis, content: str) -> List[str]:
        """Generate migration-specific notes for a service."""
        notes = []
        
        if not analysis.user_context_available:
            notes.append("⚠️ No UserExecutionContext found - manual context creation required")
            
            # Check if it's a message handler that might have context in methods
            if "message_handler" in str(analysis.file_path).lower():
                notes.append("💡 Message handlers typically receive context in handle_* methods")
            
            # Check if it's a service that might have context injected
            if any(pattern in content for pattern in ["def __init__", "class.*Service"]):
                notes.append("💡 Consider adding user_context parameter to constructor")
        
        if len(analysis.deprecated_calls) > 3:
            notes.append(f"⚠️ High usage count ({len(analysis.deprecated_calls)} calls) - requires careful review")
        
        # Check for WebSocket event emission patterns
        if re.search(r"emit_|send_.*event|websocket.*emit", content, re.IGNORECASE):
            notes.append("🎯 Service emits WebSocket events - ensure isolated manager is used")
        
        # Check for threading or async concerns
        if re.search(r"threading|asyncio\.create_task|concurrent\.futures", content):
            notes.append("⚠️ Threading/async usage detected - verify user context propagation")
        
        return notes
    
    def create_backup(self, file_path: Path) -> bool:
        """Create backup of a service file."""
        try:
            relative_path = file_path.relative_to(self.project_root)
            backup_path = self.backup_dir / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"✅ Backup created: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup for {file_path}: {e}")
            return False
    
    def migrate_service_file(self, analysis: ServiceAnalysis, dry_run: bool = False) -> bool:
        """Migrate a single service file to use factory pattern."""
        if not analysis.has_deprecated_usage:
            return True
            
        file_path = analysis.file_path
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migrating {file_path.relative_to(self.project_root)}")
        
        try:
            # Create backup first (even in dry run for validation)
            if not dry_run:
                analysis.backup_created = self.create_backup(file_path)
                if not analysis.backup_created:
                    return False
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Apply import replacements
            for old_import, new_import in self.config.import_replacements.items():
                content = content.replace(old_import, new_import)
            
            # Add UserExecutionContext import if needed and not present
            if not analysis.user_context_available and "UserExecutionContext" not in content:
                # Find existing imports to add new import
                import_lines = []
                other_lines = []
                
                lines = content.splitlines()
                in_imports = True
                
                for line in lines:
                    if (line.strip().startswith(('from ', 'import ')) or 
                        (line.strip() == '' and in_imports)):
                        import_lines.append(line)
                    else:
                        if in_imports and line.strip():
                            # Add UserExecutionContext import before first non-import
                            import_lines.append("from netra_backend.app.services.user_execution_context import UserExecutionContext")
                            in_imports = False
                        other_lines.append(line)
                
                content = '\n'.join(import_lines + other_lines)
            
            # Replace get_websocket_manager() calls with create_websocket_manager(user_context)
            # This is the critical transformation
            content = self._transform_websocket_calls(content, analysis)
            
            # Write changes if not dry run
            if not dry_run and content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"✅ Migration completed for {file_path.name}")
                analysis.migration_successful = True
                return True
            elif dry_run:
                # In dry run, show what would change
                if content != original_content:
                    logger.info(f"[DRY RUN] Would modify {file_path.name}")
                    # Show diff preview
                    self._show_diff_preview(original_content, content, file_path)
                return True
            else:
                logger.info(f"ℹ️ No changes needed for {file_path.name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Migration failed for {file_path}: {e}")
            analysis.migration_notes.append(f"Migration error: {e}")
            return False
    
    def _transform_websocket_calls(self, content: str, analysis: ServiceAnalysis) -> str:
        """Transform get_websocket_manager() calls to factory pattern."""
        
        # Pattern 1: Direct assignment - websocket_manager = get_websocket_manager()
        pattern1 = r"(\w+)\s*=\s*get_websocket_manager\s*\(\s*\)"
        
        def replace1(match):
            var_name = match.group(1)
            
            # Generate context creation based on available patterns
            if analysis.user_context_available:
                # Use existing context
                context_ref = "user_context"
                for source in analysis.user_context_sources:
                    if "self.user_context" in source:
                        context_ref = "self.user_context"
                        break
                    elif "context" in source.lower() and "=" in source:
                        # Try to extract variable name
                        parts = source.split("=")
                        if len(parts) >= 2:
                            potential_var = parts[0].split(":")[-1].strip()
                            if "context" in potential_var.lower():
                                context_ref = potential_var
                                break
                                
                return f"{var_name} = create_websocket_manager({context_ref})"
            else:
                # Need to create context - add a comment for manual review
                return f"""# TODO: Create UserExecutionContext for user isolation
        # user_context = UserExecutionContext(user_id=..., thread_id=..., run_id=..., request_id=...)
        {var_name} = create_websocket_manager(user_context)  # MANUAL REVIEW REQUIRED"""
        
        content = re.sub(pattern1, replace1, content)
        
        # Pattern 2: Direct method calls - get_websocket_manager().some_method()
        pattern2 = r"get_websocket_manager\s*\(\s*\)\.(\w+)"
        
        def replace2(match):
            method_name = match.group(1)
            
            if analysis.user_context_available:
                # Use existing context for method calls
                context_ref = "user_context"
                for source in analysis.user_context_sources:
                    if "self.user_context" in source:
                        context_ref = "self.user_context"
                        break
                        
                return f"create_websocket_manager({context_ref}).{method_name}"
            else:
                # Add comment for manual review
                return f"""# TODO: Add user context
        create_websocket_manager(user_context).{method_name}  # MANUAL REVIEW REQUIRED"""
        
        content = re.sub(pattern2, replace2, content)
        
        # Pattern 3: Function arguments - some_function(get_websocket_manager())
        pattern3 = r"(\w+\s*\(\s*[^)]*)get_websocket_manager\s*\(\s*\)([^)]*\))"
        
        def replace3(match):
            before = match.group(1)
            after = match.group(2)
            
            if analysis.user_context_available:
                context_ref = "user_context" 
                for source in analysis.user_context_sources:
                    if "self.user_context" in source:
                        context_ref = "self.user_context"
                        break
                        
                return f"{before}create_websocket_manager({context_ref}){after}"
            else:
                return f"{before}create_websocket_manager(user_context){after}  # MANUAL REVIEW REQUIRED"
        
        content = re.sub(pattern3, replace3, content)
        
        return content
    
    def _show_diff_preview(self, original: str, modified: str, file_path: Path) -> None:
        """Show a preview of changes that would be made."""
        original_lines = original.splitlines()
        modified_lines = modified.splitlines()
        
        # Simple diff showing key changes
        logger.info(f"\n--- {file_path.name} (original)")
        logger.info(f"+++ {file_path.name} (modified)")
        
        changes_shown = 0
        max_changes = 10  # Limit output
        
        for i, (orig_line, mod_line) in enumerate(zip(original_lines, modified_lines)):
            if orig_line != mod_line and changes_shown < max_changes:
                logger.info(f"@@ Line {i+1} @@")
                logger.info(f"- {orig_line}")
                logger.info(f"+ {mod_line}")
                changes_shown += 1
                
        if changes_shown >= max_changes:
            logger.info("... (showing first 10 changes)")
    
    def find_critical_services(self) -> List[Path]:
        """Find all critical services that need to be analyzed."""
        services = []
        
        services_root = self.project_root / self.config.services_root
        
        if not services_root.exists():
            logger.error(f"Services directory not found: {services_root}")
            return services
            
        # Find all specified critical services
        for service_name in self.config.critical_services:
            service_path = services_root / service_name
            
            if service_path.exists() and service_path.is_file():
                services.append(service_path)
                logger.debug(f"Found critical service: {service_path}")
            else:
                logger.warning(f"Critical service not found: {service_path}")
                self.report.critical_issues_found.append(f"Missing critical service: {service_name}")
        
        logger.info(f"Found {len(services)} critical services to analyze")
        return services
    
    def run_migration(self, dry_run: bool = False, validate_only: bool = False) -> MigrationReport:
        """Run the complete migration process."""
        self.report.dry_run = dry_run or validate_only
        
        logger.info(f"🚀 Starting WebSocket v2 Migration ({'DRY RUN' if dry_run else 'VALIDATION ONLY' if validate_only else 'LIVE MIGRATION'})")
        logger.info(f"Backup directory: {self.backup_dir}")
        
        # Find critical services
        critical_services = self.find_critical_services()
        
        if not critical_services:
            logger.error("❌ No critical services found to migrate")
            self.report.critical_issues_found.append("No critical services found")
            self.report.end_time = datetime.now()
            return self.report
        
        self.report.total_services_analyzed = len(critical_services)
        
        # Analyze each service
        for service_path in critical_services:
            try:
                analysis = self.analyze_service_file(service_path)
                service_name = service_path.relative_to(self.project_root / self.config.services_root)
                self.report.detailed_results[str(service_name)] = analysis
                
                if analysis.has_deprecated_usage:
                    self.report.services_with_deprecated_usage += 1
                    
                    if not validate_only:
                        # Perform migration
                        success = self.migrate_service_file(analysis, dry_run)
                        if success:
                            self.report.services_migrated_successfully += 1
                        else:
                            self.report.services_failed_migration += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing {service_path}: {e}")
                self.report.critical_issues_found.append(f"Error processing {service_path}: {e}")
        
        self.report.end_time = datetime.now()
        
        # Summary
        logger.info(f"\n🎯 Migration Summary:")
        logger.info(f"   Total Services: {self.report.total_services_analyzed}")
        logger.info(f"   Need Migration: {self.report.services_with_deprecated_usage}")
        
        if not validate_only:
            logger.info(f"   Successfully Migrated: {self.report.services_migrated_successfully}")
            logger.info(f"   Failed Migrations: {self.report.services_failed_migration}")
        
        if self.report.critical_issues_found:
            logger.warning(f"   Critical Issues: {len(self.report.critical_issues_found)}")
            
        return self.report
    
    def save_report(self, report_path: Optional[Path] = None) -> Path:
        """Save migration report to file."""
        if report_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.backup_dir / f"migration_report_{timestamp}.md"
        
        report_content = self.report.to_markdown()
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
            
        logger.info(f"📊 Migration report saved: {report_path}")
        return report_path

def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate critical services from deprecated WebSocket singleton to factory pattern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show what would be changed (safe)
  python scripts/migrate_websocket_v2_critical_services.py --dry-run
  
  # Validate current state only
  python scripts/migrate_websocket_v2_critical_services.py --validate-only
  
  # Perform actual migration (requires --force)
  python scripts/migrate_websocket_v2_critical_services.py --force
  
  # Use custom backup directory
  python scripts/migrate_websocket_v2_critical_services.py --dry-run --backup-dir ./my_backups
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without making modifications'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Actually perform the migration (required for live migration)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true', 
        help='Only validate current state, do not migrate'
    )
    
    parser.add_argument(
        '--backup-dir',
        type=Path,
        help='Custom directory for backup files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if not args.dry_run and not args.force and not args.validate_only:
        print("❌ Error: Must specify --dry-run, --validate-only, or --force")
        print("   Use --dry-run first to see what would be changed")
        sys.exit(1)
    
    # Validate we're in the right directory
    if not Path("netra_backend/app/services").exists():
        print("❌ Error: Must run from project root directory")
        print("   Expected to find: netra_backend/app/services")
        sys.exit(1)
    
    try:
        # Create migrator
        config = MigrationConfig()
        migrator = WebSocketV2Migrator(config, args.backup_dir)
        
        # Run migration
        report = migrator.run_migration(
            dry_run=args.dry_run,
            validate_only=args.validate_only
        )
        
        # Save report
        report_path = migrator.save_report()
        
        # Exit with appropriate code
        if report.critical_issues_found or report.services_failed_migration > 0:
            logger.error(f"❌ Migration completed with issues")
            if not args.dry_run and not args.validate_only:
                logger.error(f"   Check report at: {report_path}")
                logger.error(f"   Backups available at: {migrator.backup_dir}")
            sys.exit(1)
        else:
            logger.info(f"✅ Migration completed successfully")
            if args.dry_run:
                logger.info("   Use --force to perform actual migration")
            elif args.validate_only:
                logger.info("   Current state validated - ready for migration")
            else:
                logger.info(f"   Report: {report_path}")
                logger.info(f"   Backups: {migrator.backup_dir}")
            
    except KeyboardInterrupt:
        print("\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()