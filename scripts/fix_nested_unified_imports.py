"""Fix nested unified imports in all Python files."""

import os
import re
from pathlib import Path


def fix_nested_unified_imports(file_path: str) -> bool:
    """Fix nested unified imports in a single file."""
    
    import_mappings = {
        # Map old nested imports to new locations
        r"from netra_backend\.app\.websocket_core\.unified\.manager import UnifiedWebSocketManager": 
            "from netra_backend.app.websocket_core.manager import WebSocketManager as UnifiedWebSocketManager",
        
        r"from netra_backend\.app\.websocket_core\.unified\.types import WebSocketValidationError":
            "from netra_backend.app.core.exceptions_base import WebSocketValidationError",
        
        r"from netra_backend\.app\.websocket_core\.unified\.circuit_breaker import CircuitBreaker":
            "from netra_backend.app.core.circuit_breaker import CircuitBreaker",
        
        r"from netra_backend\.app\.websocket\.unified\.manager import UnifiedWebSocketManager":
            "from netra_backend.app.websocket_core.manager import WebSocketManager as UnifiedWebSocketManager",
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all mappings
        for old_import, new_import in import_mappings.items():
            content = re.sub(old_import, new_import, content)
        
        # Only write if something changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix all files."""
    
    fixed_count = 0
    
    # Find all Python files
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and git directories
        dirs[:] = [d for d in dirs if d not in ['venv', '.git', '__pycache__']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_nested_unified_imports(file_path):
                    print(f"Fixed: {file_path}")
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")


if __name__ == "__main__":
    main()