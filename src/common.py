"""
Common utilities and constants for the fix-owner script.

This module provides shared color definitions, constants, utility functions,
and common patterns used across multiple modules in the fix-owner script.
"""

import os
import sys
import time
from typing import Optional

# Import colorama for terminal color support
try:
    from colorama import init, Fore, Style
    init(autoreset=True)  # Automatically reset color constants after each print
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not available
    COLORAMA_AVAILABLE = False
    class _MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = _MockColor()

# Common color constants
if COLORAMA_AVAILABLE:
    info_lt_clr = Fore.WHITE + Style.BRIGHT      # info_lt_clr: bright white for light info (values)
    info_dk_clr = Fore.LIGHTBLACK_EX             # info_dk_clr: light gray for dark info (descriptions)
    section_clr = Fore.LIGHTCYAN_EX              # section_clr: light cyan for section headers
    error_clr = Fore.RED + Style.BRIGHT          # error_clr: red for errors
    warn_clr = Fore.YELLOW + Style.BRIGHT        # warn_clr: yellow for warnings
    ok_clr = Fore.GREEN                          # ok_clr: green for success/valid status
    reset_clr = Style.RESET_ALL                  # reset_clr: reset color formatting
else:
    # Empty strings when colorama is not available
    info_lt_clr = ""
    info_dk_clr = ""
    section_clr = ""
    error_clr = ""
    warn_clr = ""
    ok_clr = ""
    reset_clr = ""

# Common constants used across modules
SCRIPT_VERSION = "1.0.0"
REQUIRED_PYTHON_VERSION = (3, 13)
DEFAULT_TIMEOUT_SECONDS = 0  # No timeout by default
MAX_PATH_LENGTH = 260  # Windows MAX_PATH limitation
CHUNK_SIZE = 1000  # Process items in chunks for memory efficiency

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 2

# Common formatting constants
SECTION_BAR_WIDTH = 50
REPORT_BAR_WIDTH = 110

# Windows security availability flags
try:
    import win32security
    import win32api
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

try:
    import win32security
    WIN32SECURITY_AVAILABLE = True
except ImportError:
    WIN32SECURITY_AVAILABLE = False


def get_current_timestamp() -> float:
    """
    Get current timestamp with high precision.
    
    Returns:
        Current time as float timestamp
    """
    return time.time()


def format_elapsed_time(start_time: float) -> float:
    """
    Calculate elapsed time from a start timestamp.
    
    Args:
        start_time: Starting timestamp
        
    Returns:
        Elapsed time in seconds as float
    """
    return time.time() - start_time


def setup_module_path() -> None:
    """
    Set up module path for script execution.
    
    This function adds the current directory to sys.path to enable
    absolute imports when running as a script.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)


def print_section_header(title: str, width: int = SECTION_BAR_WIDTH) -> None:
    """
    Print a formatted section header with colored bars.
    
    Args:
        title: Section title to display
        width: Width of the header bars (default: 50)
    """
    print(f"\n{section_clr}{'=' * width}{reset_clr}")
    print(f"{section_clr}{title}{reset_clr}")
    print(f"{section_clr}{'=' * width}{reset_clr}")


def print_section_bar(width: int = SECTION_BAR_WIDTH) -> None:
    """
    Print a colored section separator bar.
    
    Args:
        width: Width of the bar (default: 50)
    """
    print(f"{section_clr}{'=' * width}{reset_clr}")


def safe_exit(exit_code: int, message: Optional[str] = None) -> None:
    """
    Safely exit the application with proper error handling.
    
    Args:
        exit_code: Exit code to use (EXIT_SUCCESS, EXIT_ERROR, or EXIT_INTERRUPTED)
        message: Optional message to print before exiting
    """
    if message:
        if exit_code == EXIT_ERROR:
            print(f"{error_clr}{message}{reset_clr}", file=sys.stderr)
        elif exit_code == EXIT_INTERRUPTED:
            print(f"{warn_clr}{message}{reset_clr}", file=sys.stderr)
        else:
            print(message)
    
    sys.exit(exit_code)


def validate_path_exists(path: str) -> bool:
    """
    Validate that a path exists.
    
    Args:
        path: Path to validate
        
    Returns:
        True if path exists, False otherwise
    """
    return os.path.exists(path)


def validate_path_is_directory(path: str) -> bool:
    """
    Validate that a path is a directory.
    
    Args:
        path: Path to validate
        
    Returns:
        True if path is a directory, False otherwise
    """
    return os.path.isdir(path)


def try_import_with_fallback(relative_module: str, absolute_module: str, items: list):
    """
    Try importing with relative imports first, then fall back to absolute imports.
    
    Args:
        relative_module: Relative module name (e.g., '.common')
        absolute_module: Absolute module name (e.g., 'common')
        items: List of items to import
        
    Returns:
        Dictionary of imported items
    """
    try:
        # Try relative import first
        module = __import__(relative_module, fromlist=items, level=1)
        return {item: getattr(module, item) for item in items}
    except ImportError:
        # Fall back to absolute import
        module = __import__(absolute_module, fromlist=items)
        return {item: getattr(module, item) for item in items}