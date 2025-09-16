"""Token budget visualization utilities."""

def render_progress_bar(used: int, total: int, width: int = 20) -> str:
    """Renders an ASCII progress bar."""
    if total == 0:
        return "[NO BUDGET SET]"

    percentage = min(used / total, 1.0)
    filled_width = int(percentage * width)

    # Use ASCII characters for Windows compatibility
    bar = '#' * filled_width + '-' * (width - filled_width)

    # Color coding (ANSI escape codes)
    color_start = '\033[92m'  # Green
    if percentage > 0.9:
        color_start = '\033[91m'  # Red
    elif percentage > 0.7:
        color_start = '\033[93m'  # Yellow
    color_end = '\033[0m'  # Reset

    return f"[{color_start}{bar}{color_end}] {percentage:.0%}"