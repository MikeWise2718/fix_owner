"""
OutputManager - Centralized output control and verbose logging for the fix-owner script.

This module provides comprehensive output management with support for different
verbosity levels, consistent formatting, and proper stream handling. It ensures
that all output throughout the application follows consistent patterns and
respects user preferences for verbosity.

Key Features:
- Multiple output levels (Quiet, Normal, Verbose)
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


class OutputLevel(Enum):
    """Output verbosity levels."""
    QUIET = 0      # No output at all
    NORMAL = 1     # Standard output with final statistics
    VERBOSE = 2    # Detailed output with path examination info


@dataclass
class OutputConfig:
    """Configuration for output behavior."""
    level: OutputLevel = OutputLevel.NORMAL
    output_stream: TextIO = sys.stdout
    error_stream: TextIO = sys.stderr


class OutputManager:
    """
    Manages all output for the fix-owner script with support for verbose and quiet modes.
    
    This class provides centralized output control that handles:
    - Verbose output showing current paths being examined
    - Quiet mode that suppresses all output including statistics
    - Consistent formatting for all messages and statistics
    - Proper output control throughout all components
    """
    
    def __init__(self, verbose: bool = False, quiet: bool = False, 
                 output_stream: TextIO = sys.stdout, error_stream: TextIO = sys.stderr):
        """
        Initialize OutputManager with specified output behavior.
        
        Args:
            verbose: Enable verbose output showing detailed processing info
            quiet: Enable quiet mode suppressing all output including statistics
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        # Quiet mode takes precedence over verbose
        if quiet:
            self.level = OutputLevel.QUIET
        elif verbose:
            self.level = OutputLevel.VERBOSE
        else:
            self.level = OutputLevel.NORMAL
            
        self.config = OutputConfig(
            level=self.level,
            output_stream=output_stream,
            error_stream=error_stream
        )
    
    def is_quiet(self) -> bool:
        """Check if quiet mode is enabled."""
        return self.config.level == OutputLevel.QUIET
    
    def is_verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self.config.level == OutputLevel.VERBOSE
    
    def is_normal(self) -> bool:
        """Check if normal output mode is enabled."""
        return self.config.level == OutputLevel.NORMAL
    
    def print_examining_path(self, path: str, is_directory: bool = True) -> None:
        """
        Print path examination message in verbose mode.
        
        Args:
            path: Path being examined
            is_directory: True if path is a directory, False if file
        """
        if self.config.level == OutputLevel.VERBOSE:
            path_type = "directory" if is_directory else "file"
            self._write_output(f"Examining {path_type}: {path}")
    
    def print_ownership_change(self, path: str, is_directory: bool = True, 
                             dry_run: bool = False) -> None:
        """
        Print ownership change message in verbose mode.
        
        Args:
            path: Path where ownership was changed
            is_directory: True if path is a directory, False if file
            dry_run: True if this is a dry run (no actual changes made)
        """
        if self.config.level == OutputLevel.VERBOSE:
            path_type = "directory" if is_directory else "file"
            action = "Would change" if dry_run else "Changed"
            self._write_output(f"{action} owner for {path_type}: {path}")
    
    def print_error(self, path: str, error: Exception, is_directory: bool = True) -> None:
        """
        Print error message in verbose mode.
        
        Args:
            path: Path where error occurred
            error: Exception that occurred
            is_directory: True if path is a directory, False if file
        """
        if self.config.level == OutputLevel.VERBOSE:
            path_type = "directory" if is_directory else "file"
            self._write_error(f"Error processing {path_type} {path}: {error}")
    
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
        if self.config.level == OutputLevel.VERBOSE:
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