"""
OutputManager - Centralized output control and verbose logging for the fix-owner script.

This module provides comprehensive output management with support for different
verbosity levels, consistent formatting, colored output, and proper stream handling. 
It ensures that all output throughout the application follows consistent patterns and
respects user preferences for verbosity.

Key Features:
- Multiple verbose levels (0: statistics only, 1: directory progress, 2: detailed examination)
- Colored output using colorama for better visual tracking
- Consistent message formatting across all components
- Proper stream separation (stdout for normal output, stderr for errors)
- Integration with statistics reporting
- Context-aware output (dry-run vs execute mode indicators)
- Error message categorization and formatting

The OutputManager serves as the central point for all user-facing output,
ensuring consistency and proper handling of different output scenarios.

Classes:
    OutputLevel: Enumeration of output verbosity levels
    OutputConfig: Configuration data structure for output behavior
    OutputManager: Main output coordination and formatting
    StatsReporter: Specialized statistics reporting with consistent formatting
"""

import sys
from typing import Optional, TextIO
from dataclasses import dataclass
from enum import Enum

# Import colorama for cross-platform colored output
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # Automatically reset colors after each print
    COLORAMA_AVAILABLE = True
except ImportError:
    # Fallback if colorama is not available
    COLORAMA_AVAILABLE = False
    class _MockColor:
        def __getattr__(self, name): return ""
    Fore = Back = Style = _MockColor()


class OutputLevel(Enum):
    """Output verbosity levels with detailed descriptions."""
    QUIET = -1     # No output at all (quiet mode)
    LEVEL_0 = 0    # Only final statistics
    LEVEL_1 = 1    # Top-level directory status + statistics
    LEVEL_2 = 2    # Directory progress + statistics
    LEVEL_3 = 3    # Detailed file/directory examination + all above


@dataclass
class OutputConfig:
    """Configuration for output behavior."""
    level: OutputLevel = OutputLevel.LEVEL_0
    output_stream: TextIO = sys.stdout
    error_stream: TextIO = sys.stderr


class OutputManager:
    """
    Manages all output for the fix-owner script with support for multiple verbose levels and colors.
    
    This class provides centralized output control that handles:
    - Level 0: Only final statistics
    - Level 1: Top-level directory status + statistics  
    - Level 2: Directory progress + statistics
    - Level 3: Detailed file/directory examination + all above
    - Quiet mode that suppresses all output
    - Colored output for better visual tracking
    - Consistent formatting for all messages and statistics
    """
    
    def __init__(self, verbose_level: int = 0, quiet: bool = False, 
                 output_stream: TextIO = sys.stdout, error_stream: TextIO = sys.stderr):
        """
        Initialize OutputManager with specified verbose level.
        
        Args:
            verbose_level: Verbosity level (0=stats only, 1=directory progress, 2=detailed)
            quiet: Enable quiet mode suppressing all output
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        # Quiet mode takes precedence over verbose levels
        if quiet:
            self.level = OutputLevel.QUIET
        elif verbose_level >= 3:
            self.level = OutputLevel.LEVEL_3
        elif verbose_level >= 2:
            self.level = OutputLevel.LEVEL_2
        elif verbose_level >= 1:
            self.level = OutputLevel.LEVEL_1
        else:
            self.level = OutputLevel.LEVEL_0
            
        self.config = OutputConfig(
            level=self.level,
            output_stream=output_stream,
            error_stream=error_stream
        )
        
        # Track directory processing for level 1 output
        self.current_directory = None
        self.dirs_needing_change = 0
        self.files_needing_change = 0
        self.total_dirs_processed = 0
        self.total_files_processed = 0
    
    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self.config.level == OutputLevel.QUIET
    
    def is_level_0(self) -> bool:
        """Check if level 0 (statistics only) is enabled."""
        return self.config.level == OutputLevel.LEVEL_0
    
    def is_level_1(self) -> bool:
        """Check if level 1 (directory progress) is enabled."""
        return self.config.level == OutputLevel.LEVEL_1
    
    def is_level_2(self) -> bool:
        """Check if level 2 (directory progress) is enabled."""
        return self.config.level == OutputLevel.LEVEL_2
    
    def is_level_3(self) -> bool:
        """Check if level 3 (detailed examination) is enabled."""
        return self.config.level == OutputLevel.LEVEL_3
    
    def get_verbose_level(self) -> int:
        """Get current verbose level as integer."""
        if self.config.level == OutputLevel.QUIET:
            return -1
        elif self.config.level == OutputLevel.LEVEL_0:
            return 0
        elif self.config.level == OutputLevel.LEVEL_1:
            return 1
        elif self.config.level == OutputLevel.LEVEL_2:
            return 2
        elif self.config.level == OutputLevel.LEVEL_3:
            return 3
        return 0
    
    def print_entering_directory(self, path: str, is_root: bool = False, is_top_level: bool = False, progress: tuple = None) -> None:
        """
        Print message when entering a new directory.
        Level 1: Root directory and top-level directories (immediate children of root)
        Level 2+: All directories
        
        Args:
            path: Directory path being entered
            is_root: True if this is the root directory being processed
            is_top_level: True if this is a top-level directory (immediate child of root)
            progress: Optional tuple of (current, total) for progress tracking
        """
        # Reset counters for new directory
        self.current_directory = path
        self.dirs_needing_change = 0
        self.files_needing_change = 0
        self.total_dirs_processed = 0
        self.total_files_processed = 0
        
        # Level 1: Show root directory and top-level directories
        if self.config.level == OutputLevel.LEVEL_1 and (is_root or is_top_level):
            color = Fore.CYAN + Style.BRIGHT if COLORAMA_AVAILABLE else ""
            path_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
            if is_root:
                self._write_output(f"{color}→ Processing root directory: {path_color}{path}")
            else:
                # Show progress counter for top-level directories if available
                if progress:
                    current, total = progress
                    self._write_output(f"{color}→ Processing top-level directory {current}/{total}: {path_color}{path}")
                else:
                    self._write_output(f"{color}→ Processing top-level directory: {path_color}{path}")
        # Level 2+: Show all directories
        elif self.config.level.value >= OutputLevel.LEVEL_2.value:
            color = Fore.CYAN + Style.BRIGHT if COLORAMA_AVAILABLE else ""
            self._write_output(f"{color}→ Entering directory: {path}")
    
    def print_directory_summary(self, path: str, is_root: bool = False, is_top_level: bool = False, progress: tuple = None) -> None:
        """
        Print summary when finishing a directory.
        Level 1: Root directory and top-level directories (immediate children of root)
        Level 2+: All directories
        
        Args:
            path: Directory path that was processed
            is_root: True if this is the root directory being processed
            is_top_level: True if this is a top-level directory (immediate child of root)
            progress: Optional tuple of (current, total) for progress tracking
        """
        color = Fore.GREEN if COLORAMA_AVAILABLE else ""
        path_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
        total_changes = self.dirs_needing_change + self.files_needing_change
        
        # Level 1: Show root directory and top-level directory summaries
        if self.config.level == OutputLevel.LEVEL_1 and (is_root or is_top_level):
            if total_changes > 0:
                if is_root:
                    self._write_output(f"{color}✓ Root directory completed: {total_changes} ownership changes needed "
                                     f"({self.dirs_needing_change}/{self.total_dirs_processed} dirs, {self.files_needing_change}/{self.total_files_processed} files)")
                else:
                    # Show progress counter for top-level directories if available
                    if progress:
                        current, total = progress
                        self._write_output(f"{color}✓ Top-level directory {current}/{total} completed - {total_changes} ownership changes needed "
                                         f"({self.dirs_needing_change}/{self.total_dirs_processed} dirs, {self.files_needing_change}/{self.total_files_processed} files)")
                    else:
                        self._write_output(f"{color}✓ Top-level directory completed - {total_changes} ownership changes needed "
                                         f"({self.dirs_needing_change}/{self.total_dirs_processed} dirs, {self.files_needing_change}/{self.total_files_processed} files)")
            else:
                if is_root:
                    self._write_output(f"{color}✓ Root directory completed: No ownership changes needed "
                                     f"({self.total_dirs_processed} dirs, {self.total_files_processed} files processed)")
                else:
                    # Show progress counter for top-level directories if available
                    if progress:
                        current, total = progress
                        self._write_output(f"{color}✓ Top-level directory {current}/{total} completed - No ownership changes needed "
                                         f"({self.total_dirs_processed} dirs, {self.total_files_processed} files processed)")
                    else:
                        self._write_output(f"{color}✓ Top-level directory completed - No ownership changes needed "
                                         f"({self.total_dirs_processed} dirs, {self.total_files_processed} files processed)")
        # Level 2+: Show all directory summaries
        elif self.config.level.value >= OutputLevel.LEVEL_2.value:
            if total_changes > 0:
                self._write_output(f"{color}✓ Completed {path}: {total_changes} ownership changes needed "
                                 f"({self.dirs_needing_change}/{self.total_dirs_processed} dirs, {self.files_needing_change}/{self.total_files_processed} files)")
            else:
                self._write_output(f"{color}✓ Completed {path}: No ownership changes needed "
                                 f"({self.total_dirs_processed} dirs, {self.total_files_processed} files processed)")
    
    def print_examining_path(self, path: str, is_directory: bool = True, 
                           current_owner: str = None, is_valid_owner: bool = True) -> None:
        """
        Print path examination message.
        Level 1: Only orphaned items that need changes (for tracking)
        Level 2: Basic directory/file processing
        Level 3: Detailed examination with ownership info
        
        Args:
            path: Path being examined
            is_directory: True if path is a directory, False if file
            current_owner: Current owner of the path
            is_valid_owner: True if current owner is valid, False if orphaned
        """
        # Track items for directory summaries
        if is_directory:
            self.total_dirs_processed += 1
            if not is_valid_owner:
                self.dirs_needing_change += 1
        else:
            self.total_files_processed += 1
            if not is_valid_owner:
                self.files_needing_change += 1
        
        if self.config.level.value >= OutputLevel.LEVEL_2.value:
            path_type = "DIR " if is_directory else "FILE"
            
            # Choose colors based on ownership status
            if is_valid_owner:
                path_color = Fore.GREEN if COLORAMA_AVAILABLE else ""
                owner_color = Fore.BLUE if COLORAMA_AVAILABLE else ""
                status = "VALID"
            else:
                path_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
                owner_color = Fore.RED if COLORAMA_AVAILABLE else ""
                status = "ORPHANED"
            
            # Level 3: Show detailed examination with ownership info
            if self.config.level == OutputLevel.LEVEL_3:
                owner_display = current_owner if current_owner else "UNKNOWN"
                self._write_output(f"  {path_color}{path_type} {path} {owner_color}[{owner_display}] {status}")
            # Level 2: Show basic processing progress
            elif self.config.level == OutputLevel.LEVEL_2:
                if is_directory:
                    self._write_output(f"  {path_color}Processing directory: {path}")
                # Only show files if they need changes or in detailed mode
                elif not is_valid_owner:
                    self._write_output(f"  {path_color}Processing file: {path} {owner_color}[ORPHANED]")
    
    def print_ownership_change(self, path: str, is_directory: bool = True, 
                             dry_run: bool = False, new_owner: str = None) -> None:
        """
        Print ownership change message (Level 1+).
        
        Args:
            path: Path where ownership was changed
            is_directory: True if path is a directory, False if file
            dry_run: True if this is a dry run (no actual changes made)
            new_owner: New owner account name
        """
        if self.config.level.value >= OutputLevel.LEVEL_2.value:
            path_type = "directory" if is_directory else "file"
            
            if dry_run:
                action_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
                action = "WOULD CHANGE"
            else:
                action_color = Fore.GREEN + Style.BRIGHT if COLORAMA_AVAILABLE else ""
                action = "CHANGED"
            
            path_color = Fore.CYAN if COLORAMA_AVAILABLE else ""
            owner_color = Fore.BLUE if COLORAMA_AVAILABLE else ""
            
            owner_text = f" → {new_owner}" if new_owner else ""
            
            if self.config.level == OutputLevel.LEVEL_3:
                # Detailed output for level 3
                self._write_output(f"    {action_color}{action} {path_color}{path_type}: {path}{owner_color}{owner_text}")
            else:
                # Compact output for level 2
                self._write_output(f"  {action_color}{action} {path_type}: {path_color}{path}{owner_color}{owner_text}")
    
    def print_error(self, path: str, error: Exception, is_directory: bool = True) -> None:
        """
        Print error message (Level 1+).
        
        Args:
            path: Path where error occurred
            error: Exception that occurred
            is_directory: True if path is a directory, False if file
        """
        if self.config.level.value >= OutputLevel.LEVEL_1.value:
            path_type = "directory" if is_directory else "file"
            error_color = Fore.RED + Style.BRIGHT if COLORAMA_AVAILABLE else ""
            path_color = Fore.YELLOW if COLORAMA_AVAILABLE else ""
            
            self._write_error(f"{error_color}ERROR processing {path_type} {path_color}{path}: {error}")
    
    def print_timeout_warning(self, elapsed_time: float, timeout_seconds: int) -> None:
        """
        Print timeout warning message.
        
        Args:
            elapsed_time: Time elapsed when timeout occurred
            timeout_seconds: Configured timeout limit
        """
        if self.config.level != OutputLevel.QUIET:
            self._write_output(f"Timeout reached after {elapsed_time:.1f} seconds "
                             f"(limit: {timeout_seconds} seconds)")
    
    def print_statistics_header(self) -> None:
        """Print statistics section header."""
        if self.config.level != OutputLevel.QUIET:
            self._write_output("--- Ownership Change Statistics ---")
    
    def print_statistic(self, label: str, value: int) -> None:
        """
        Print individual statistic line.
        
        Args:
            label: Description of the statistic
            value: Numeric value of the statistic
        """
        if self.config.level != OutputLevel.QUIET:
            self._write_output(f"{label}: {value}")
    
    def print_duration_statistic(self, duration_seconds: float) -> None:
        """
        Print execution duration statistic.
        
        Args:
            duration_seconds: Total execution time in seconds
        """
        if self.config.level != OutputLevel.QUIET:
            self._write_output(f"Total duration: {duration_seconds:.1f} seconds")
    
    def print_dry_run_notice(self) -> None:
        """Print notice that this is a dry run."""
        if self.config.level != OutputLevel.QUIET:
            self._write_output("DRY RUN MODE: No actual changes will be made")
    
    def print_execution_mode_notice(self) -> None:
        """Print notice that changes will be applied."""
        if self.config.level != OutputLevel.QUIET:
            self._write_output("EXECUTE MODE: Ownership changes will be applied")
    
    def print_startup_info(self, root_path: str, owner_account: str, 
                          recurse: bool, include_files: bool) -> None:
        """
        Print startup information about the operation.
        
        Args:
            root_path: Root path being processed
            owner_account: Target owner account
            recurse: Whether recursion is enabled
            include_files: Whether files are included
        """
        if self.config.level == OutputLevel.LEVEL_3:
            self._write_output(f"Starting ownership fix operation:")
            self._write_output(f"  Root path: {root_path}")
            self._write_output(f"  Target owner: {owner_account}")
            self._write_output(f"  Recurse subdirectories: {'Yes' if recurse else 'No'}")
            self._write_output(f"  Include files: {'Yes' if include_files else 'No'}")
    
    def print_completion_message(self) -> None:
        """Print operation completion message."""
        if self.config.level != OutputLevel.QUIET:
            self._write_output("Ownership fix operation completed")
    
    def print_invalid_owner_error(self, owner_account: str, error: Exception) -> None:
        """
        Print error message for invalid owner account.
        
        Args:
            owner_account: Invalid owner account name
            error: Exception that occurred during validation
        """
        # Always print critical errors, even in quiet mode
        self._write_error(f"Invalid owner account '{owner_account}': {error}")
    
    def print_privilege_warning(self) -> None:
        """Print warning about Administrator privileges requirement."""
        if self.config.level != OutputLevel.QUIET:
            self._write_output("Warning: This script requires Administrator privileges "
                             "for ownership changes")
    
    def print_general_message(self, message: str) -> None:
        """
        Print general informational message.
        
        Args:
            message: Message to print
        """
        if self.config.level != OutputLevel.QUIET:
            self._write_output(message)
    
    def print_general_error(self, message: str) -> None:
        """
        Print general error message.
        
        Args:
            message: Error message to print
        """
        # Always print general errors, even in quiet mode for critical issues
        self._write_error(message)
    
    def _write_output(self, message: str) -> None:
        """
        Write message to output stream.
        
        Args:
            message: Message to write
        """
        try:
            print(message, file=self.config.output_stream)
            self.config.output_stream.flush()
        except Exception:
            # Fallback to stderr if stdout fails
            try:
                print(message, file=sys.stderr)
                sys.stderr.flush()
            except Exception:
                pass  # Silently ignore if both streams fail
    
    def _write_error(self, message: str) -> None:
        """
        Write error message to error stream.
        
        Args:
            message: Error message to write
        """
        try:
            print(message, file=self.config.error_stream)
            self.config.error_stream.flush()
        except Exception:
            # Fallback to stdout if stderr fails
            try:
                print(message, file=sys.stdout)
                sys.stdout.flush()
            except Exception:
                pass  # Silently ignore if both streams fail
    
    def create_stats_reporter(self):
        """
        Create a statistics reporter that respects output settings.
        
        Returns:
            StatsReporter instance configured with this output manager
        """
        return StatsReporter(self)


class StatsReporter:
    """
    Helper class for reporting statistics with consistent formatting.
    """
    
    def __init__(self, output_manager: OutputManager):
        """
        Initialize StatsReporter with output manager.
        
        Args:
            output_manager: OutputManager instance for output control
        """
        self.output = output_manager
    
    def print_full_report(self, dirs_traversed: int, files_traversed: int,
                         dirs_changed: int, files_changed: int,
                         exceptions: int, duration_seconds: float) -> None:
        """
        Print complete statistics report.
        
        Args:
            dirs_traversed: Number of directories examined
            files_traversed: Number of files examined
            dirs_changed: Number of directory ownerships changed
            files_changed: Number of file ownerships changed
            exceptions: Number of exceptions encountered
            duration_seconds: Total execution time
        """
        if self.output.is_quiet():
            return
            
        self.output.print_statistics_header()
        self.output.print_statistic("Directories traversed", dirs_traversed)
        self.output.print_statistic("Files traversed", files_traversed)
        self.output.print_statistic("Directory ownerships changed", dirs_changed)
        self.output.print_statistic("File ownerships changed", files_changed)
        self.output.print_statistic("Exceptions encountered", exceptions)
        self.output.print_duration_statistic(duration_seconds)