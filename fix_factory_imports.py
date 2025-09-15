#!/usr/bin/env python3
"""
Script to fix websocket_manager_factory imports after factory removal.
Updates all files to use canonical imports instead.
"""

import os
import re
import sys

def fix_imports_in_file(file_path):
    """Fix websocket_manager_factory imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace factory imports with canonical imports
        old_pattern = r'from netra_backend\.app\.websocket_core\.websocket_manager_factory import ([^\\n]*)'
        new_replacement = r'from netra_backend.app.websocket_core.canonical_imports import \1'
        
        content = re.sub(old_pattern, new_replacement, content)
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed imports in: {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all imports."""
    
    # Files that need import fixes
    files_to_fix = [
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/quality_validation_handler.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/quality_report_handler.py", 
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/quality_manager.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/quality_message_router.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/message_queue.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/websocket/quality_metrics_handler.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/handlers.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/unified_init.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/protocols.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/__init__.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/core/supervisor_factory.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/core/interfaces_data.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/synthetic_data_progress_tracker.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/agents/example_message_processor.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/utils.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/supervisor_factory.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/services/corpus/clickhouse_operations.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/routes/utils/thread_title_generator.py",
        "/Users/anthony/Desktop/netra-apex/netra_backend/app/core/startup_validation.py"
    ]
    
    print("🔧 Fixing websocket_manager_factory imports...")
    print(f"📁 Processing {len(files_to_fix)} files...")
    
    fixed_count = 0
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_imports_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\\n✅ Complete! Fixed imports in {fixed_count} files.")

if __name__ == "__main__":
    main()