"""
StatsTracker - Execution statistics tracking and reporting for the fix-owner script.

This module provides comprehensive statistics tracking functionality that records
and reports on the execution of filesystem ownership operations. It tracks
directories and files processed, ownership changes made, exceptions encountered,
and execution timing.

Key Features:
- Track directories and files traversed during processing
- Count ownership changes made to directories and files
- Monitor exceptions encountered during execution
- Measure total execution time with high precision
- Generate formatted reports with colored output
- Integration with OutputManager for consistent formatting

Classes:
    StatsTracker: Main statistics tracking and reporting coordinator
"""

import time
from typing import Optional

# Import common utilities and constants
try:
    from .common import (
        section_clr, reset_clr, COLORAMA_AVAILABLE, SECTION_BAR_WIDTH,
        get_current_timestamp, format_elapsed_time, print_section_bar
    )
except ImportError:
    # Fall back to absolute imports (when run as a script)
    from common import (
        section_clr, reset_clr, COLORAMA_AVAILABLE, SECTION_BAR_WIDTH,
        get_current_timestamp, format_elapsed_time, print_section_bar
    )


class StatsTracker:
    """
    Tracks and reports execution statistics for the fix-owner script.
    
    This class provides counters for directories, files, changes, and exceptions,
    along with methods to increment each counter and generate formatted reports.
    The tracker automatically records the start time when initialized and can
    calculate elapsed time for performance monitoring.
    """
    
    def __init__(self):
        """Initialize the StatsTracker with zero counters and current timestamp."""
        self.dirs_traversed = 0
        self.files_traversed = 0
        self.dirs_changed = 0
        self.files_changed = 0
        self.exceptions = 0
        self.start_time = get_current_timestamp()
    
    def increment_dirs_traversed(self) -> None:
        """Increment the count of directories traversed."""
        self.dirs_traversed += 1
    
    def increment_files_traversed(self) -> None:
        """Increment the count of files traversed."""
        self.files_traversed += 1
    
    def increment_dirs_changed(self) -> None:
        """Increment the count of directory ownerships changed."""
        self.dirs_changed += 1
    
    def increment_files_changed(self) -> None:
        """Increment the count of file ownerships changed."""
        self.files_changed += 1
    
    def increment_exceptions(self) -> None:
        """Increment the count of exceptions encountered."""
        self.exceptions += 1
    
    def get_elapsed_time(self) -> float:
        """
        Get the elapsed time since tracking started.
        
        Returns:
            Elapsed time in seconds as a float with high precision
        """
        return format_elapsed_time(self.start_time)
    
    def print_report(self, quiet: bool = False, is_simulation: bool = False, output_manager=None) -> None:
        """
        Print a formatted statistics report with colored headers and consistent formatting.
        
        This method generates a comprehensive report showing all tracked statistics
        including directories and files processed, ownership changes made, exceptions
        encountered, and total execution time. The report uses colored formatting
        when available and integrates with OutputManager for consistent styling.
        
        Args:
            quiet: If True, suppress all output including statistics
            is_simulation: If True, show "SIMULATED EXECUTION STATISTICS" header
            output_manager: OutputManager instance for colored formatting (optional)
        """
        if quiet:
            return
        
        elapsed_time = self.get_elapsed_time()
        
        # Print section header
        print()  # Add newline
        print_section_bar(SECTION_BAR_WIDTH)
        if is_simulation:
            print(f"{section_clr}SIMULATED EXECUTION STATISTICS{reset_clr}")
        else:
            print(f"{section_clr}EXECUTION STATISTICS{reset_clr}")
        print_section_bar(SECTION_BAR_WIDTH)
        
        # Use OutputManager for formatted output if available
        if output_manager:
            output_manager.print_info_pair("Directories traversed", f"{self.dirs_traversed:,}")
            output_manager.print_info_pair("Files traversed", f"{self.files_traversed:,}")
            output_manager.print_info_pair("Directory ownerships changed", f"{self.dirs_changed:,}")
            output_manager.print_info_pair("File ownerships changed", f"{self.files_changed:,}")
            output_manager.print_info_pair("Exceptions encountered", f"{self.exceptions:,}")
            output_manager.print_info_pair("Total execution time", f"{elapsed_time:.2f} seconds")
        else:
            # Fallback to plain printing
            print(f"Directories traversed: {self.dirs_traversed:,}")
            print(f"Files traversed: {self.files_traversed:,}")
            print(f"Directory ownerships changed: {self.dirs_changed:,}")
            print(f"File ownerships changed: {self.files_changed:,}")
            print(f"Exceptions encountered: {self.exceptions:,}")
            print(f"Total execution time: {elapsed_time:.2f} seconds")
        
        print_section_bar(SECTION_BAR_WIDTH)
    
    def get_summary_stats(self) -> dict:
        """
        Get summary statistics as a dictionary for integration with other components.
        
        Returns:
            Dictionary containing all current statistics and elapsed time
        """
        return {
            'dirs_traversed': self.dirs_traversed,
            'files_traversed': self.files_traversed,
            'dirs_changed': self.dirs_changed,
            'files_changed': self.files_changed,
            'exceptions': self.exceptions,
            'elapsed_time': self.get_elapsed_time()
        }
    
    def reset_counters(self) -> None:
        """
        Reset all counters to zero and restart the timer.
        
        This method is useful for reusing the same StatsTracker instance
        for multiple operations or for testing purposes.
        """
        self.dirs_traversed = 0
        self.files_traversed = 0
        self.dirs_changed = 0
        self.files_changed = 0
        self.exceptions = 0
        self.start_time = get_current_timestamp()
    
    def has_changes(self) -> bool:
        """
        Check if any ownership changes were made.
        
        Returns:
            True if any directories or files had their ownership changed
        """
        return self.dirs_changed > 0 or self.files_changed > 0
    
    def has_errors(self) -> bool:
        """
        Check if any exceptions were encountered.
        
        Returns:
            True if any exceptions were recorded during processing
        """
        return self.exceptions > 0
    
    def get_total_items_processed(self) -> int:
        """
        Get the total number of items (directories + files) processed.
        
        Returns:
            Total count of directories and files traversed
        """
        return self.dirs_traversed + self.files_traversed
    
    def get_total_changes_made(self) -> int:
        """
        Get the total number of ownership changes made.
        
        Returns:
            Total count of directory and file ownership changes
        """
        return self.dirs_changed + self.files_changed