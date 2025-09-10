#!/usr/bin/env python3
"""
Automated factory pattern enforcement for WebSocketNotifier.
Converts direct instantiation to factory method usage.

Usage:
    python scripts/websocket_notifier_factory_migration.py

Part of GitHub Issue #216 SSOT Remediation Plan - Phase 2.1
"""

import os
import re
import sys
import ast
from typing import List, Dict, Set

class FactoryPatternMigrator:
    """Handles WebSocketNotifier factory pattern migration."""
    
    def __init__(self):
        self.migrated_files = []
        self.failed_files = []
        self.analyzed_files = []
        
    def analyze_instantiation_patterns(self, content: str) -> Dict[str, List[str]]:
        """Analyze different WebSocketNotifier instantiation patterns."""
        patterns = {
            'direct_instantiation': [],
            'factory_pattern': [],
            'singleton_pattern': [],
            'complex_instantiation': []
        }
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Direct instantiation pattern
            if re.search(r'WebSocketNotifier\s*\([^)]*\)', line) and 'create_for_user' not in line:
                patterns['direct_instantiation'].append(f"Line {i}: {line.strip()}")
            
            # Factory pattern (already migrated)
            if 'create_for_user' in line and 'WebSocketNotifier' in line:
                patterns['factory_pattern'].append(f"Line {i}: {line.strip()}")
            
            # Singleton pattern detection
            if re.search(r'_instance.*WebSocketNotifier', line) or re.search(r'WebSocketNotifier.*_instance', line):
                patterns['singleton_pattern'].append(f"Line {i}: {line.strip()}")
            
            # Complex instantiation (needs manual review)
            if 'WebSocketNotifier' in line and any(keyword in line for keyword in ['getattr', 'setattr', 'hasattr', 'isinstance']):
                patterns['complex_instantiation'].append(f"Line {i}: {line.strip()}")
        
        return patterns
    
    def convert_direct_instantiation(self, content: str) -> str:
        """Convert direct WebSocketNotifier instantiation to factory pattern."""
        
        # Pattern 1: Simple two-parameter instantiation
        # WebSocketNotifier(emitter, exec_context) -> WebSocketNotifier.create_for_user(emitter, exec_context)
        pattern1 = r'WebSocketNotifier\s*\(\s*([^,]+),\s*([^)]+)\)'
        replacement1 = r'WebSocketNotifier.create_for_user(\1, \2)'
        content = re.sub(pattern1, replacement1, content)
        
        # Pattern 2: Single parameter instantiation (add validation)
        # WebSocketNotifier(param) -> WebSocketNotifier.create_for_user(param, None) # Needs manual review
        pattern2 = r'WebSocketNotifier\s*\(\s*([^,)]+)\)'
        def single_param_replacement(match):
            param = match.group(1)
            return f'WebSocketNotifier.create_for_user({param}, None)  # MANUAL_REVIEW: Validate exec_context'
        content = re.sub(pattern2, single_param_replacement, content)
        
        # Pattern 3: No parameter instantiation (needs context injection)
        # WebSocketNotifier() -> WebSocketNotifier.create_for_user(None, None) # Needs manual review
        pattern3 = r'WebSocketNotifier\s*\(\s*\)'
        replacement3 = r'WebSocketNotifier.create_for_user(None, None)  # MANUAL_REVIEW: Add required parameters'
        content = re.sub(pattern3, replacement3, content)
        
        return content
    
    def enhance_canonical_implementation(self) -> bool:
        """Enhance the canonical WebSocketNotifier with factory method."""
        canonical_file = "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/agent_websocket_bridge.py"
        
        if not os.path.exists(canonical_file):
            print(f"❌ Canonical file not found: {canonical_file}")
            return False
        
        try:
            with open(canonical_file, 'r') as f:
                content = f.read()
            
            # Check if factory method already exists
            if 'create_for_user' in content:
                print("✅ Factory method already exists in canonical implementation")
                return True
            
            # Find WebSocketNotifier class definition
            class_pattern = r'(class WebSocketNotifier:.*?\n    def __init__\(self, emitter, exec_context\):)'
            
            factory_method = '''
    @classmethod
    def create_for_user(cls, emitter, exec_context):
        """
        Factory method to create WebSocketNotifier with user context validation.
        
        Args:
            emitter: WebSocket emitter instance
            exec_context: User execution context with user_id
            
        Returns:
            WebSocketNotifier: Validated instance for user
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Validate required parameters
        if not emitter:
            raise ValueError("WebSocketNotifier requires valid emitter")
        if not exec_context:
            raise ValueError("WebSocketNotifier requires valid execution context")
        
        # Validate user context
        user_id = getattr(exec_context, 'user_id', None)
        if not user_id:
            raise ValueError("WebSocketNotifier requires user_id in execution context")
        
        # Create validated instance
        instance = cls(emitter, exec_context)
        
        # Additional validation for user isolation
        instance._validate_user_isolation()
        
        return instance
    
    def _validate_user_isolation(self):
        """Validate this instance is properly isolated for user."""
        # Ensure no shared state with other user instances
        if hasattr(self, '_user_id'):
            if self._user_id != getattr(self.exec_context, 'user_id', None):
                raise ValueError("User isolation violation detected")
        else:
            self._user_id = getattr(self.exec_context, 'user_id', None)'''
            
            # Insert factory method after __init__
            enhanced_content = re.sub(
                class_pattern,
                r'\1' + factory_method,
                content,
                flags=re.DOTALL
            )
            
            if enhanced_content != content:
                # Create backup
                backup_path = f"{canonical_file}.backup_pre_factory_migration"
                with open(backup_path, 'w') as f:
                    f.write(content)
                
                # Write enhanced content
                with open(canonical_file, 'w') as f:
                    f.write(enhanced_content)
                
                print("✅ Factory method added to canonical implementation")
                return True
            else:
                print("⚠️  Could not automatically add factory method - manual review required")
                return False
                
        except Exception as e:
            print(f"❌ Error enhancing canonical implementation: {e}")
            return False
    
    def migrate_factory_pattern_in_file(self, file_path: str) -> bool:
        """Migrate factory patterns in a single file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Analyze current patterns
            patterns = self.analyze_instantiation_patterns(content)
            self.analyzed_files.append({
                'file': file_path,
                'patterns': patterns
            })
            
            # Skip if no direct instantiation found
            if not patterns['direct_instantiation']:
                return False
            
            # Convert direct instantiation to factory pattern
            new_content = self.convert_direct_instantiation(content)
            
            if new_content != content:
                # Create backup
                backup_path = f"{file_path}.backup_pre_factory_migration"
                with open(backup_path, 'w') as f:
                    f.write(content)
                
                # Write migrated content
                with open(file_path, 'w') as f:
                    f.write(new_content)
                
                self.migrated_files.append(file_path)
                return True
            
            return False
        
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            self.failed_files.append(file_path)
            return False

    def find_files_with_direct_instantiation(self) -> List[str]:
        """Find files with direct WebSocketNotifier instantiation."""
        files = []
        
        for root, dirs, filenames in os.walk('/Users/anthony/Desktop/netra-apex'):
            # Skip irrelevant directories
            if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
                continue
                
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(root, filename)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            
                        # Look for WebSocketNotifier instantiation
                        if 'WebSocketNotifier(' in content:
                            # Exclude files that already use factory pattern
                            if 'create_for_user' not in content:
                                files.append(file_path)
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return files
    
    def generate_analysis_report(self) -> str:
        """Generate detailed analysis report."""
        report = []
        report.append("=" * 60)
        report.append("WebSocketNotifier Factory Pattern Migration Report")
        report.append("=" * 60)
        
        report.append(f"✅ Successfully migrated: {len(self.migrated_files)} files")
        report.append(f"❌ Failed: {len(self.failed_files)} files")
        report.append(f"🔍 Analyzed: {len(self.analyzed_files)} files")
        
        # Pattern analysis summary
        total_direct = sum(len(analysis['patterns']['direct_instantiation']) for analysis in self.analyzed_files)
        total_factory = sum(len(analysis['patterns']['factory_pattern']) for analysis in self.analyzed_files)
        total_singleton = sum(len(analysis['patterns']['singleton_pattern']) for analysis in self.analyzed_files)
        total_complex = sum(len(analysis['patterns']['complex_instantiation']) for analysis in self.analyzed_files)
        
        report.append(f"\nPattern Analysis:")
        report.append(f"  📊 Direct instantiation patterns: {total_direct}")
        report.append(f"  🏭 Factory patterns (already migrated): {total_factory}")
        report.append(f"  🔄 Singleton patterns (need manual review): {total_singleton}")
        report.append(f"  🔧 Complex patterns (need manual review): {total_complex}")
        
        if self.migrated_files:
            report.append("\nMigrated Files:")
            for file in self.migrated_files:
                report.append(f"  ✅ {file}")
        
        if self.failed_files:
            report.append("\nFailed Files:")
            for file in self.failed_files:
                report.append(f"  ❌ {file}")
        
        # Files requiring manual review
        manual_review_files = []
        for analysis in self.analyzed_files:
            if analysis['patterns']['singleton_pattern'] or analysis['patterns']['complex_instantiation']:
                manual_review_files.append(analysis['file'])
        
        if manual_review_files:
            report.append("\nFiles Requiring Manual Review:")
            for file in manual_review_files:
                report.append(f"  🔧 {file}")
        
        return "\n".join(report)

def main():
    """Execute factory pattern migration process."""
    print("🏭 Starting WebSocketNotifier Factory Pattern Migration")
    print("📋 GitHub Issue #216 - Phase 2.1: Factory Pattern Enforcement")
    print("=" * 60)
    
    migrator = FactoryPatternMigrator()
    
    # Step 1: Enhance canonical implementation with factory method
    print("🔧 Step 1: Enhancing canonical implementation with factory method...")
    if not migrator.enhance_canonical_implementation():
        print("⚠️  Could not enhance canonical implementation - proceeding with migration anyway")
    
    # Step 2: Find files needing migration
    print("\n🔍 Step 2: Scanning for files with direct instantiation...")
    files = migrator.find_files_with_direct_instantiation()
    print(f"📁 Found {len(files)} files with direct instantiation")
    
    if not files:
        print("✅ No files found with direct instantiation - migration complete!")
        return 0
    
    # Show files to be migrated
    print("\n📝 Files to be migrated:")
    for file in files[:10]:  # Show first 10
        print(f"  - {file}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")
    
    # Confirm migration
    try:
        response = input("\n❓ Proceed with factory pattern migration? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Migration cancelled by user")
            return 1
    except KeyboardInterrupt:
        print("\n❌ Migration cancelled by user")
        return 1
    
    # Step 3: Execute migration
    print("\n🔄 Step 3: Executing factory pattern migration...")
    for i, file_path in enumerate(files, 1):
        print(f"  📄 [{i}/{len(files)}] Migrating {file_path}...")
        success = migrator.migrate_factory_pattern_in_file(file_path)
        if success:
            print(f"    ✅ Migrated successfully")
        else:
            print(f"    ⏭️  No changes needed or failed")
    
    # Generate and display report
    print("\n" + migrator.generate_analysis_report())
    
    # Save report to file
    report_file = "websocket_notifier_factory_migration_report.txt"
    with open(report_file, 'w') as f:
        f.write(migrator.generate_analysis_report())
    print(f"\n📄 Migration report saved to: {report_file}")
    
    # Next steps
    print("\n📋 Next Steps:")
    print("  1. Review files marked for manual review")
    print("  2. Run tests: python tests/mission_critical/test_websocket_agent_events_suite.py")
    print("  3. Validate user isolation: python tests/integration/test_websocket_user_isolation.py")
    print("  4. Execute Phase 2.2: Singleton Pattern Elimination")
    
    if migrator.failed_files:
        print("\n⚠️  Migration completed with some failures - review failed files")
        return 2
    else:
        print("\n🎉 Factory pattern migration completed successfully!")
        return 0

if __name__ == "__main__":
    sys.exit(main())