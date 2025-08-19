"""
Demo script for Phase 2 Silent Logging System.

Shows integration of LogBuffer, LogFilter, and ProgressIndicator.
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from log_buffer import LogBuffer, LogLevel
from log_filter_core import LogFilter, StartupMode
from progress_indicator import ProgressIndicator


def simulate_startup_logs():
    """Simulate typical startup logs."""
    return [
        ("webpack.Progress updated", LogLevel.INFO),
        ("npm WARN deprecated package", LogLevel.WARNING),
        ("Watching for file changes", LogLevel.INFO),
        ("Health check passed", LogLevel.INFO),
        ("Session middleware config: loaded", LogLevel.INFO),
        ("Backend service starting", LogLevel.INFO),
        ("Server started on port 8000", LogLevel.SUCCESS),
        ("Frontend ready", LogLevel.SUCCESS),
        ("System Ready", LogLevel.SUCCESS),
    ]


def demo_phase2():
    """Demonstrate Phase 2 components."""
    print("Phase 2 Silent Logging System Demo")
    print("=" * 40)
    
    # Initialize components
    log_buffer = LogBuffer(max_size=50)
    log_filter = LogFilter(StartupMode.MINIMAL)
    progress = ProgressIndicator()
    
    print("\n1. Starting progress indicator...")
    progress.start()
    
    # Simulate startup phases
    startup_logs = simulate_startup_logs()
    
    for i, (message, level) in enumerate(startup_logs):
        # Add to buffer
        log_buffer.add_message(message, level, "demo")
        
        # Filter and potentially show
        if log_filter.should_show(message, level.name):
            formatted = log_filter.format_message(message, level.name)
            if formatted:
                print(f"LOG: {formatted}")
        
        # Update progress
        if i < 5:
            progress.update_progress(f"Processing {message[:20]}...")
            time.sleep(0.5)
        elif i == 5:
            progress.next_phase()
            time.sleep(0.3)
        
    # Complete
    progress.complete()
    
    # Show buffer stats
    print(f"\n2. Buffer contains {len(log_buffer.buffer)} entries")
    print(f"   Hash tracking: {len(log_buffer.message_hashes)} unique messages")
    
    # Show filter stats
    stats = log_filter.get_filter_stats()
    print(f"\n3. Filter stats:")
    print(f"   Mode: {stats['mode']}")
    print(f"   Messages processed: {len(startup_logs)}")
    
    print("\n✓ Phase 2 components working together successfully!")


if __name__ == "__main__":
    demo_phase2()