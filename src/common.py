"""
Common utilities and constants for the fix-owner script.

This module provides shared color definitions and utility functions
used across multiple modules in the fix-owner script.
"""

# Import colorama for colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)  # Automatically reset colors after each print
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not available
    COLORAMA_AVAILABLE = False
    class _MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = _MockColor()

# Common color definitions
if COLORAMA_AVAILABLE:
    info_lt_clr = Fore.WHITE + Style.BRIGHT      # Bright white for light info (values)
    info_dk_clr = Fore.LIGHTBLACK_EX             # Light gray for dark info (descriptions)
    section_clr = Fore.LIGHTCYAN_EX              # Light cyan for section headers
    error_clr = Fore.RED + Style.BRIGHT          # Red for errors
    warn_clr = Fore.YELLOW + Style.BRIGHT        # Yellow for warnings
    ok_clr = Fore.GREEN                          # Green for success/valid status
    reset_clr = Style.RESET_ALL                  # Reset color
else:
    # Empty strings when colorama is not available
    info_lt_clr = ""
    info_dk_clr = ""
    section_clr = ""
    error_clr = ""
    warn_clr = ""
    ok_clr = ""
    reset_clr = ""