"""
SidTracker - SID tracking and reporting functionality for the fix-owner script.

This module provides comprehensive SID (Security Identifier) tracking capabilities
that record and analyze ownership patterns encountered during filesystem processing.
It helps administrators understand the distribution of ownership across their
filesystem and identify patterns in orphaned SIDs.

Key Features:
- Track SID occurrences for both files and directories separately
- Resolve SIDs to human-readable account names when possible
- Generate formatted reports showing SID distribution
- Support for both valid and orphaned SID tracking
- Integration with existing output management system

Classes:
    SidTracker: Main SID tracking and reporting coordinator
"""

from typing import Dict, Tuple, Optional
from collections import defaultdict

# Import common utilities and constants
try:
    from .common import (
        section_clr, error_clr, warn_clr, ok_clr, reset_clr, COLORAMA_AVAILABLE,
        WIN32SECURITY_AVAILABLE, REPORT_BAR_WIDTH
    )
except ImportError:
    # Fall back to absolute imports (when run as a script)
    from common import (
        section_clr, error_clr, warn_clr, ok_clr, reset_clr, COLORAMA_AVAILABLE,
        WIN32SECURITY_AVAILABLE, REPORT_BAR_WIDTH
    )

# Windows security imports (availability checked in common)
if WIN32SECURITY_AVAILABLE:
    import win32security


class SidTracker:
    """
    Tracks and reports SID occurrences during filesystem processing.
    
    This class provides comprehensive SID tracking functionality that records
    every SID encountered during filesystem traversal, categorizes them by
    validity (valid vs orphaned), and generates detailed reports showing
    the distribution of ownership across the processed filesystem.
    """
    
    def __init__(self, security_manager=None):
        """
        Initialize SidTracker with required dependencies.
        
        Args:
            security_manager: SecurityManager instance for SID resolution
        """
        self.security_manager = security_manager
        
        # Track SID occurrences: SID string -> (file_count, dir_count, account_name, is_valid)
        self._sid_data: Dict[str, Dict] = defaultdict(lambda: {
            'file_count': 0,
            'dir_count': 0,
            'account_name': None,
            'is_valid': None,
            'sid_object': None
        })
        
        # Track total counts for summary
        self.total_files_tracked = 0
        self.total_dirs_tracked = 0
        self.unique_sids_found = 0
        self.valid_sids_count = 0
        self.orphaned_sids_count = 0
    
    def track_file_sid(self, file_path: str, sid_object: object) -> None:
        """
        Track SID occurrence for a file.
        
        Args:
            file_path: Path to the file (for error reporting)
            sid_object: SID object encountered
        """
        try:
            # Convert SID object to string for consistent tracking
            sid_string = str(sid_object)
            
            # Initialize or update SID data
            if sid_string not in self._sid_data:
                self._resolve_sid_info(sid_string, sid_object)
                self.unique_sids_found += 1
            
            # Increment file count for this SID
            self._sid_data[sid_string]['file_count'] += 1
            self.total_files_tracked += 1
            
        except Exception as e:
            # Handle SID tracking errors gracefully - don't interrupt main processing
            if hasattr(self, '_output_manager') and self._output_manager:
                self._output_manager.print_general_error(
                    f"Error tracking SID for file {file_path}: {e}"
                )
    
    def track_directory_sid(self, dir_path: str, sid_object: object) -> None:
        """
        Track SID occurrence for a directory.
        
        Args:
            dir_path: Path to the directory (for error reporting)
            sid_object: SID object encountered
        """
        try:
            # Convert SID object to string for consistent tracking
            sid_string = str(sid_object)
            
            # Initialize or update SID data
            if sid_string not in self._sid_data:
                self._resolve_sid_info(sid_string, sid_object)
                self.unique_sids_found += 1
            
            # Increment directory count for this SID
            self._sid_data[sid_string]['dir_count'] += 1
            self.total_dirs_tracked += 1
            
        except Exception as e:
            # Handle SID tracking errors gracefully - don't interrupt main processing
            if hasattr(self, '_output_manager') and self._output_manager:
                self._output_manager.print_general_error(
                    f"Error tracking SID for directory {dir_path}: {e}"
                )
    
    def _resolve_sid_info(self, sid_string: str, sid_object: object) -> None:
        """
        Resolve SID information including account name and validity.
        
        Args:
            sid_string: String representation of SID
            sid_object: SID object for resolution
        """
        sid_data = self._sid_data[sid_string]
        sid_data['sid_object'] = sid_object
        
        if self.security_manager:
            try:
                # Check if SID is valid (corresponds to existing account)
                is_valid = self.security_manager.is_sid_valid(sid_object)
                sid_data['is_valid'] = is_valid
                
                if is_valid:
                    self.valid_sids_count += 1
                    # Try to get human-readable account name
                    try:
                        if WIN32SECURITY_AVAILABLE:
                            name, domain, _ = win32security.LookupAccountSid(None, sid_object)
                            account_name = f"{domain}\\{name}" if domain else name
                            sid_data['account_name'] = account_name
                        else:
                            sid_data['account_name'] = f"<Valid SID: {sid_string}>"
                    except Exception:
                        # SID is valid but name resolution failed
                        sid_data['account_name'] = f"<Valid SID: {sid_string}>"
                else:
                    self.orphaned_sids_count += 1
                    sid_data['account_name'] = f"<Orphaned SID: {sid_string}>"
                    
            except Exception:
                # Error in SID validation - treat as unknown
                sid_data['is_valid'] = None
                sid_data['account_name'] = f"<Unknown SID: {sid_string}>"
        else:
            # No SecurityManager available - limited functionality
            sid_data['is_valid'] = None
            sid_data['account_name'] = f"<SID: {sid_string}>"
    
    def generate_report(self, output_manager=None) -> None:
        """
        Generate and display a comprehensive SID tracking report.
        
        Args:
            output_manager: Optional OutputManager for formatted output
        """
        if not self._sid_data:
            if output_manager:
                output_manager.print_general_message("No SID data collected.")
            else:
                print("No SID data collected.")
            return
        
        # Store output manager reference for error reporting
        self._output_manager = output_manager
        
        # Generate report sections
        self._print_report_header(output_manager)
        self._print_summary_statistics(output_manager)
        self._print_sid_details_table(output_manager)
        self._print_report_footer(output_manager)
    
    def _print_report_header(self, output_manager=None) -> None:
        """Print report header section."""
        header = f"\n{section_clr}{'=' * REPORT_BAR_WIDTH}{reset_clr}"
        title_text = "SID OWNERSHIP ANALYSIS REPORT"
        title = f"{section_clr}{title_text.center(REPORT_BAR_WIDTH)}{reset_clr}"
        bottom_bar = f"{section_clr}{'=' * REPORT_BAR_WIDTH}{reset_clr}"
        
        header_lines = [header, title, bottom_bar]
        
        for line in header_lines:
            if output_manager:
                output_manager.print_general_message(line)
            else:
                print(line)
    
    def _print_summary_statistics(self, output_manager=None) -> None:
        """Print summary statistics section."""
        if output_manager:
            # Use OutputManager formatting for description: value pairs
            output_manager.print_info_pair("Total files analyzed", f"{self.total_files_tracked:,}")
            output_manager.print_info_pair("Total directories analyzed", f"{self.total_dirs_tracked:,}")
            output_manager.print_info_pair("Unique SIDs found", f"{self.unique_sids_found:,}")
            output_manager.print_info_pair("Valid SIDs", f"{self.valid_sids_count:,}")
            output_manager.print_info_pair("Orphaned SIDs", f"{self.orphaned_sids_count:,}")
            output_manager.print_general_message("")  # Empty line
        else:
            # Fallback to plain printing
            summary_lines = [
                f"Total files analyzed: {self.total_files_tracked:,}",
                f"Total directories analyzed: {self.total_dirs_tracked:,}",
                f"Unique SIDs found: {self.unique_sids_found:,}",
                f"Valid SIDs: {self.valid_sids_count:,}",
                f"Orphaned SIDs: {self.orphaned_sids_count:,}",
                ""
            ]
            
            for line in summary_lines:
                print(line)
    
    def _print_sid_details_table(self, output_manager=None) -> None:
        """Print detailed SID information table."""
        # Table header
        table_header = [
            "SID DETAILS:",
            "-" * REPORT_BAR_WIDTH,
            f"{'Files':<8} {'Dirs':<8} {'Status':<10} {'Account Name'}",
            "-" * REPORT_BAR_WIDTH
        ]
        
        for line in table_header:
            if output_manager:
                output_manager.print_general_message(line)
            else:
                print(line)
        
        # Sort SIDs by total count (files + directories) for most relevant first
        sorted_sids = sorted(
            self._sid_data.items(),
            key=lambda x: x[1]['file_count'] + x[1]['dir_count'],
            reverse=True
        )
        
        # Print each SID's details
        for sid_string, data in sorted_sids:
            account_name = data['account_name'] or f"<SID: {sid_string}>"
            file_count = data['file_count']
            dir_count = data['dir_count']
            
            # Determine status with appropriate color constant
            if data['is_valid'] is True:
                status = f"{ok_clr}Valid{reset_clr}"
            elif data['is_valid'] is False:
                status = f"{error_clr}Orphaned{reset_clr}"
            else:
                status = f"{warn_clr}Unknown{reset_clr}"
            
            # Build line with status using color constants
            # Note: We need to account for the color codes in the formatting
            line = f"{file_count:<8} {dir_count:<8} {status:<10} {account_name}"
            
            if output_manager:
                output_manager.print_general_message(line)
            else:
                print(line)
    
    def _print_report_footer(self, output_manager=None) -> None:
        """Print report footer section."""
        # Create legend lines using color constants
        valid_colored = f"{ok_clr}Valid{reset_clr}"
        orphaned_colored = f"{error_clr}Orphaned{reset_clr}"
        unknown_colored = f"{warn_clr}Unknown{reset_clr}"
        
        footer_lines = [
            "-" * REPORT_BAR_WIDTH,
            "Legend:",
            "  Files: Number of files owned by this SID",
            "  Dirs:  Number of directories owned by this SID", 
            f"  {valid_colored}: SID corresponds to an existing account",
            f"  {orphaned_colored}: SID does not correspond to any existing account",
            f"  {unknown_colored}: SID validation could not be performed",
            f"{section_clr}{'=' * REPORT_BAR_WIDTH}{reset_clr}"
        ]
        
        for line in footer_lines:
            if output_manager:
                output_manager.print_general_message(line)
            else:
                print(line)
    
    def get_summary_stats(self) -> Dict[str, int]:
        """
        Get summary statistics for integration with main statistics.
        
        Returns:
            Dictionary containing summary statistics
        """
        return {
            'total_files_tracked': self.total_files_tracked,
            'total_dirs_tracked': self.total_dirs_tracked,
            'unique_sids_found': self.unique_sids_found,
            'valid_sids_count': self.valid_sids_count,
            'orphaned_sids_count': self.orphaned_sids_count
        }