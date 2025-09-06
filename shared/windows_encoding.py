"""
SSOT for Windows encoding and Unicode handling.

This module provides a single source of truth for fixing Windows-specific
encoding issues that affect Python scripts, subprocess calls, and console output.

Usage:
    # At the very start of any script that may run on Windows
    from shared.windows_encoding import setup_windows_encoding
    setup_windows_encoding()

For more control:
    from shared.windows_encoding import WindowsEncodingManager
    manager = WindowsEncodingManager()
    manager.setup_console()
    manager.setup_subprocess_env()
"""

import os
import sys
import io
from typing import Optional, Dict, Any

# Lazy import of logging to avoid circular dependencies
def _log(level, message):
    """Log a message if logging is available."""
    try:
        import logging
        logger = logging.getLogger(__name__)
        if level == "debug":
            logger.debug(message)
        elif level == "warning":
            logger.warning(message)
    except:
        # If logging is not available, silently skip
        pass


class WindowsEncodingManager:
    """Centralized manager for Windows encoding configuration."""
    
    def __init__(self):
        """Initialize the Windows encoding manager."""
        self.is_windows = sys.platform == "win32"
        self.original_stdout = None
        self.original_stderr = None
        self.encoding_setup_complete = False
        
    def setup_console(self) -> bool:
        """
        Set up Windows console for UTF-8 encoding.
        
        Returns:
            bool: True if setup was successful or not needed, False otherwise
        """
        if not self.is_windows:
            return True
            
        try:
            # Set console code pages to UTF-8
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            # SetConsoleCP (input)
            kernel32.SetConsoleCP(65001)
            # SetConsoleOutputCP (output)
            kernel32.SetConsoleOutputCP(65001)
            
            _log("debug", "Windows console code pages set to UTF-8 (65001)")
            return True
            
        except Exception as e:
            _log("warning", f"Failed to set Windows console encoding: {e}")
            return False
    
    def setup_python_io(self) -> bool:
        """
        Reconfigure Python stdout/stderr for UTF-8 encoding.
        
        Returns:
            bool: True if setup was successful or not needed, False otherwise
        """
        if not self.is_windows:
            return True
            
        try:
            # Store originals for potential restoration
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # Reconfigure stdout/stderr with UTF-8 encoding
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer, 
                encoding='utf-8', 
                errors='replace',
                line_buffering=True
            )
            
            _log("debug", "Python stdout/stderr reconfigured for UTF-8")
            return True
            
        except Exception as e:
            _log("warning", f"Failed to reconfigure Python I/O encoding: {e}")
            return False
    
    def setup_subprocess_env(self) -> Dict[str, str]:
        """
        Set up environment variables for subprocess UTF-8 encoding.
        
        Returns:
            Dict[str, str]: Environment variables that should be used for subprocesses
        """
        env = os.environ.copy()
        
        if self.is_windows:
            # Force UTF-8 for Python subprocesses
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # Set locale for better Unicode support
            env['LANG'] = 'C.UTF-8'
            env['LC_ALL'] = 'C.UTF-8'
            
            _log("debug", "Subprocess environment configured for UTF-8")
        
        return env
    
    def setup_git_encoding(self) -> bool:
        """
        Configure git for proper Unicode handling on Windows.
        
        Returns:
            bool: True if setup was successful or not needed, False otherwise
        """
        if not self.is_windows:
            return True
            
        try:
            import subprocess
            env = self.setup_subprocess_env()
            
            # Configure git for UTF-8
            commands = [
                ['git', 'config', '--global', 'core.quotepath', 'false'],
                ['git', 'config', '--global', 'i18n.commitencoding', 'utf-8'],
                ['git', 'config', '--global', 'i18n.logoutputencoding', 'utf-8']
            ]
            
            for cmd in commands:
                subprocess.run(
                    cmd, 
                    env=env, 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8'
                )
            
            _log("debug", "Git configured for UTF-8 encoding")
            return True
            
        except Exception as e:
            _log("warning", f"Failed to configure git encoding: {e}")
            return False
    
    def setup_all(self) -> bool:
        """
        Perform complete Windows encoding setup.
        
        Returns:
            bool: True if all setup steps succeeded or Windows not detected
        """
        if not self.is_windows:
            return True
            
        if self.encoding_setup_complete:
            return True
        
        success = True
        
        # Set environment variables first (affects child processes)
        env = self.setup_subprocess_env()
        for key, value in env.items():
            if key.startswith('PYTHON') or key.startswith('L'):
                os.environ[key] = value
        
        # Setup console
        if not self.setup_console():
            success = False
        
        # Setup Python I/O
        if not self.setup_python_io():
            success = False
        
        # Git is optional, don't fail if it's not available
        self.setup_git_encoding()
        
        self.encoding_setup_complete = success
        return success
    
    def get_safe_env(self, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment variables with Windows encoding fixes applied.
        
        Args:
            base_env: Base environment to extend (defaults to os.environ)
            
        Returns:
            Dict[str, str]: Environment with encoding variables set
        """
        if base_env is None:
            base_env = os.environ.copy()
        else:
            base_env = base_env.copy()
        
        if self.is_windows:
            base_env.update(self.setup_subprocess_env())
        
        return base_env
    
    def restore_io(self) -> None:
        """Restore original stdout/stderr if they were modified."""
        if self.original_stdout:
            sys.stdout = self.original_stdout
            self.original_stdout = None
        
        if self.original_stderr:
            sys.stderr = self.original_stderr
            self.original_stderr = None


# Global singleton instance
_manager: Optional[WindowsEncodingManager] = None


def get_manager() -> WindowsEncodingManager:
    """Get or create the global Windows encoding manager."""
    global _manager
    if _manager is None:
        _manager = WindowsEncodingManager()
    return _manager


def setup_windows_encoding() -> bool:
    """
    Convenience function to perform complete Windows encoding setup.
    
    This should be called at the start of any script that may run on Windows.
    It's safe to call multiple times - subsequent calls are no-ops.
    
    Returns:
        bool: True if setup succeeded or not on Windows
    """
    return get_manager().setup_all()


def get_subprocess_env(base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get environment variables suitable for subprocess calls with encoding fixes.
    
    Args:
        base_env: Base environment to extend (defaults to os.environ)
        
    Returns:
        Dict[str, str]: Environment with encoding variables set
    """
    return get_manager().get_safe_env(base_env)


def ensure_utf8_file_operations():
    """
    Context manager or decorator to ensure UTF-8 for file operations.
    
    This is primarily for documentation - Python file operations should
    always explicitly specify encoding='utf-8'.
    """
    import locale
    if sys.platform == "win32":
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_ALL, '')
            except:
                pass


# Auto-setup on import if running as main script
if __name__ == "__main__":
    # Add parent directory to path for standalone testing
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Test the setup
    manager = WindowsEncodingManager()
    success = manager.setup_all()
    
    if success:
        print("✅ Windows encoding setup successful")
        print("Testing Unicode output: 🚀 🔧 ✨")
    else:
        print("[OK] Windows encoding setup completed with warnings")
        print("Testing Unicode output: [ROCKET] [GEAR] [SPARKLES]")