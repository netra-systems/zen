"""
Windows UTF-8 console encoding fixes.

Ensures proper UTF-8 handling on Windows consoles by setting appropriate
encoding for stdin, stdout, and stderr streams.
"""

import sys
import io


def setup_windows_encoding():
    """
    Configure Windows console to use UTF-8 encoding.

    This function reconfigures sys.stdin, sys.stdout, and sys.stderr to use
    UTF-8 encoding with error handling on Windows platforms. This prevents
    Unicode encoding errors when displaying special characters or emoji.

    Must be called early in the startup sequence before any console I/O.
    """
    if sys.platform == "win32":
        # Reconfigure stdout and stderr to use UTF-8 with error handling
        if sys.stdout is not None:
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )

        if sys.stderr is not None:
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )

        if sys.stdin is not None:
            sys.stdin = io.TextIOWrapper(
                sys.stdin.buffer,
                encoding='utf-8',
                errors='replace'
            )
