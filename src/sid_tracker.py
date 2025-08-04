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

import json
import time
from typing import Dict, Tuple, Optional
from collections import defaultdict

# YAML support with fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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
    
    def __init__(self, security_manager=None, start_timestamp_str=None, target_owner_account=None):
        """
        Initialize SidTracker with required dependencies.
        
        Args:
            security_manager: SecurityManager instance for SID resolution
            start_timestamp_str: Formatted timestamp string for export filenames
            target_owner_account: Target owner account for orphaned SID remediation
        """
        self.security_manager = security_manager
        self.start_timestamp_str = start_timestamp_str or "unknown_time"
        self.target_owner_account = target_owner_account or "UNKNOWN\\USER"
        
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
        Generate and display a comprehensive SID tracking report and export JSON data.
        
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
        
        # Generate console report sections
        self._print_report_header(output_manager)
        self._print_summary_statistics(output_manager)
        self._print_sid_details_table(output_manager)
        self._print_report_footer(output_manager)
        
        # Export data to JSON file
        json_filename = self.create_json_export_filename()
        json_success = self.export_to_json(output_manager)
        
        # Export orphaned SIDs to YAML file
        yaml_filename = self.create_yaml_export_filename()
        yaml_success = self.export_orphaned_sids_to_yaml(output_manager)
        
        # Report export status with filenames
        if json_success and output_manager:
            output_manager.print_general_message(f"\n{ok_clr}SID ownership data exported to JSON file: {json_filename}{reset_clr}")
        elif not json_success and output_manager:
            output_manager.print_general_error(f"Failed to export SID ownership data to JSON file: {json_filename}")
        
        if yaml_success and output_manager and YAML_AVAILABLE:
            orphaned_count = len([sid for sid, data in self._sid_data.items() if data['is_valid'] is False])
            if orphaned_count > 0:
                output_manager.print_general_message(f"{ok_clr}Orphaned SID remediation plan exported to YAML file: {yaml_filename}{reset_clr}")
        elif not yaml_success and output_manager and YAML_AVAILABLE:
            output_manager.print_general_error(f"Failed to export orphaned SID remediation data to YAML file: {yaml_filename}")
    
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
    
    def create_json_export_filename(self) -> str:
        """
        Create a timestamped filename for JSON export in the output directory.
        
        Returns:
            Full path to the JSON file in the output directory
        """
        # Import here to avoid circular imports
        try:
            from .common import get_output_file_path
        except ImportError:
            from common import get_output_file_path
        
        filename = f"sid_ownership_analysis_{self.start_timestamp_str}.json"
        return get_output_file_path(filename)
    
    def export_to_json(self, output_manager=None) -> bool:
        """
        Export SID ownership analysis data to a JSON file.
        
        Args:
            output_manager: Optional OutputManager for status reporting
            
        Returns:
            True if export successful, False if failed
        """
        if not self._sid_data:
            if output_manager:
                output_manager.print_general_message("No SID data to export.")
            return False
        
        filename = self.create_json_export_filename()
        
        try:
            # Prepare data for JSON export
            export_data = self._prepare_json_data()
            
            # Write JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            if output_manager and output_manager.get_verbose_level() >= 2:
                output_manager.print_general_message(f"SID ownership analysis exported to: {filename}")
            
            return True
            
        except Exception as e:
            if output_manager:
                output_manager.print_general_error(f"Failed to export SID data to JSON file {filename}: {e}")
            return False
    
    def _prepare_json_data(self) -> Dict:
        """
        Prepare SID data for JSON export with comprehensive information.
        
        Returns:
            Dictionary containing all SID data organized for JSON export
        """
        # Generate timestamp for the export
        export_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Prepare summary statistics
        summary = {
            'export_timestamp': export_timestamp,
            'execution_start_timestamp': self.start_timestamp_str.replace('_', ' at '),
            'total_files_analyzed': self.total_files_tracked,
            'total_directories_analyzed': self.total_dirs_tracked,
            'unique_sids_found': self.unique_sids_found,
            'valid_sids_count': self.valid_sids_count,
            'orphaned_sids_count': self.orphaned_sids_count,
            'total_items_analyzed': self.total_files_tracked + self.total_dirs_tracked
        }
        
        # Prepare detailed SID data ordered by SID string
        sids_data = {}
        for sid_string in sorted(self._sid_data.keys()):
            sid_info = self._sid_data[sid_string]
            
            # Calculate additional metrics
            total_occurrences = sid_info['file_count'] + sid_info['dir_count']
            file_percentage = (sid_info['file_count'] / self.total_files_tracked * 100) if self.total_files_tracked > 0 else 0
            dir_percentage = (sid_info['dir_count'] / self.total_dirs_tracked * 100) if self.total_dirs_tracked > 0 else 0
            total_percentage = (total_occurrences / (self.total_files_tracked + self.total_dirs_tracked) * 100) if (self.total_files_tracked + self.total_dirs_tracked) > 0 else 0
            
            # Determine status
            if sid_info['is_valid'] is True:
                status = "VALID"
                status_description = "SID corresponds to an existing account"
            elif sid_info['is_valid'] is False:
                status = "ORPHANED"
                status_description = "SID does not correspond to any existing account"
            else:
                status = "UNKNOWN"
                status_description = "SID validation could not be performed"
            
            sids_data[sid_string] = {
                'sid': sid_string,
                'account_name': sid_info['account_name'] or f"<SID: {sid_string}>",
                'status': status,
                'status_description': status_description,
                'is_valid': sid_info['is_valid'],
                'occurrences': {
                    'files': sid_info['file_count'],
                    'directories': sid_info['dir_count'],
                    'total': total_occurrences
                },
                'percentages': {
                    'files': round(file_percentage, 2),
                    'directories': round(dir_percentage, 2),
                    'total': round(total_percentage, 2)
                },
                'analysis': {
                    'is_most_common_for_files': sid_info['file_count'] == max((s['file_count'] for s in self._sid_data.values()), default=0),
                    'is_most_common_for_directories': sid_info['dir_count'] == max((s['dir_count'] for s in self._sid_data.values()), default=0),
                    'is_most_common_overall': total_occurrences == max((s['file_count'] + s['dir_count'] for s in self._sid_data.values()), default=0)
                }
            }
        
        # Prepare analysis insights
        insights = self._generate_analysis_insights()
        
        # Combine all data
        export_data = {
            'metadata': {
                'report_type': 'SID Ownership Analysis',
                'generated_by': 'fix_owner script',
                'format_version': '1.0'
            },
            'summary': summary,
            'sids': sids_data,
            'insights': insights
        }
        
        return export_data
    
    def _generate_analysis_insights(self) -> Dict:
        """
        Generate analytical insights from the SID data.
        
        Returns:
            Dictionary containing analysis insights
        """
        if not self._sid_data:
            return {}
        
        # Find most common SIDs
        most_common_files = max(self._sid_data.items(), key=lambda x: x[1]['file_count'], default=(None, {'file_count': 0}))
        most_common_dirs = max(self._sid_data.items(), key=lambda x: x[1]['dir_count'], default=(None, {'dir_count': 0}))
        most_common_overall = max(self._sid_data.items(), key=lambda x: x[1]['file_count'] + x[1]['dir_count'], default=(None, {'file_count': 0, 'dir_count': 0}))
        
        # Calculate distribution metrics
        valid_sids = [sid for sid, data in self._sid_data.items() if data['is_valid'] is True]
        orphaned_sids = [sid for sid, data in self._sid_data.items() if data['is_valid'] is False]
        
        insights = {
            'most_common_sids': {
                'files': {
                    'sid': most_common_files[0],
                    'account_name': most_common_files[1]['account_name'] if most_common_files[0] else None,
                    'count': most_common_files[1]['file_count']
                },
                'directories': {
                    'sid': most_common_dirs[0],
                    'account_name': most_common_dirs[1]['account_name'] if most_common_dirs[0] else None,
                    'count': most_common_dirs[1]['dir_count']
                },
                'overall': {
                    'sid': most_common_overall[0],
                    'account_name': most_common_overall[1]['account_name'] if most_common_overall[0] else None,
                    'total_count': most_common_overall[1]['file_count'] + most_common_overall[1]['dir_count']
                }
            },
            'distribution': {
                'valid_sids_list': valid_sids,
                'orphaned_sids_list': orphaned_sids,
                'valid_percentage': round((len(valid_sids) / len(self._sid_data) * 100), 2) if self._sid_data else 0,
                'orphaned_percentage': round((len(orphaned_sids) / len(self._sid_data) * 100), 2) if self._sid_data else 0
            },
            'recommendations': self._generate_recommendations()
        }
        
        return insights
    
    def _generate_recommendations(self) -> list:
        """
        Generate recommendations based on the SID analysis.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if self.orphaned_sids_count > 0:
            recommendations.append(f"Found {self.orphaned_sids_count} orphaned SID(s) that should be addressed")
            recommendations.append("Consider running the script with -x flag to fix orphaned ownership")
        
        if self.valid_sids_count > 0:
            recommendations.append(f"Found {self.valid_sids_count} valid SID(s) with proper ownership")
        
        if self.unique_sids_found > 10:
            recommendations.append("Large number of unique SIDs found - consider reviewing access patterns")
        
        if self.total_files_tracked == 0 and self.total_dirs_tracked > 0:
            recommendations.append("Only directories were analyzed - consider using -f flag to include files")
        
        return recommendations
    
    def create_yaml_export_filename(self) -> str:
        """
        Create a timestamped filename for YAML export in the output directory.
        
        Returns:
            Full path to the YAML file in the output directory
        """
        # Import here to avoid circular imports
        try:
            from .common import get_output_file_path
        except ImportError:
            from common import get_output_file_path
        
        filename = f"sid_orphaned_remediation_{self.start_timestamp_str}.yaml"
        return get_output_file_path(filename)
    
    def export_orphaned_sids_to_yaml(self, output_manager=None) -> bool:
        """
        Export orphaned SID remediation data to a YAML file.
        
        Args:
            output_manager: Optional OutputManager for status reporting
            
        Returns:
            True if export successful, False if failed
        """
        if not YAML_AVAILABLE:
            if output_manager:
                output_manager.print_general_error("YAML export not available - install PyYAML: pip install PyYAML")
            return False
        
        # Get orphaned SIDs
        orphaned_sids = [sid for sid, data in self._sid_data.items() if data['is_valid'] is False]
        
        if not orphaned_sids:
            if output_manager and output_manager.get_verbose_level() >= 1:
                output_manager.print_general_message("No orphaned SIDs found - YAML remediation file not needed.")
            return True  # Not an error condition
        
        filename = self.create_yaml_export_filename()
        
        try:
            # Prepare data for YAML export
            yaml_data = self._prepare_yaml_remediation_data(orphaned_sids)
            
            # Write YAML file
            with open(filename, 'w', encoding='utf-8') as f:
                yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            if output_manager and output_manager.get_verbose_level() >= 2:
                output_manager.print_general_message(f"Orphaned SID remediation data exported to: {filename}")
            
            return True
            
        except Exception as e:
            if output_manager:
                output_manager.print_general_error(f"Failed to export orphaned SID data to YAML file {filename}: {e}")
            return False
    
    def _prepare_yaml_remediation_data(self, orphaned_sids: list) -> Dict:
        """
        Prepare orphaned SID remediation data for YAML export.
        
        Args:
            orphaned_sids: List of orphaned SID strings
            
        Returns:
            Dictionary containing remediation data organized for YAML export
        """
        # Generate timestamp for the export
        export_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        
        # Prepare header information
        yaml_data = {
            'metadata': {
                'title': 'Orphaned SID Remediation Plan',
                'description': 'List of orphaned SIDs found during ownership analysis and their recommended replacements',
                'generated_by': 'fix_owner script',
                'export_timestamp': export_timestamp,
                'execution_start_timestamp': self.start_timestamp_str.replace('_', ' at '),
                'format_version': '1.0'
            },
            'remediation_info': {
                'target_owner_account': self.target_owner_account,
                'total_orphaned_sids': len(orphaned_sids),
                'remediation_command': f'python fix_owner.py <path> -x -r -f "{self.target_owner_account}"',
                'notes': [
                    'Run the remediation command to fix orphaned ownership',
                    'Use -x flag to apply changes (remove for dry-run)',
                    'Use -r flag to process subdirectories recursively',
                    'Use -f flag to process files in addition to directories',
                    'Always test with dry-run first before applying changes'
                ]
            },
            'orphaned_sids': {}
        }
        
        # Process each orphaned SID
        for sid_string in sorted(orphaned_sids):
            sid_info = self._sid_data[sid_string]
            
            # Calculate impact metrics
            total_occurrences = sid_info['file_count'] + sid_info['dir_count']
            file_percentage = (sid_info['file_count'] / self.total_files_tracked * 100) if self.total_files_tracked > 0 else 0
            dir_percentage = (sid_info['dir_count'] / self.total_dirs_tracked * 100) if self.total_dirs_tracked > 0 else 0
            
            # Determine priority based on occurrence count
            if total_occurrences >= 50:
                priority = 'HIGH'
            elif total_occurrences >= 10:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            # Create remediation entry
            yaml_data['orphaned_sids'][sid_string] = {
                'current_status': {
                    'sid': sid_string,
                    'account_name': sid_info['account_name'] or f"<Unknown SID: {sid_string}>",
                    'status': 'ORPHANED',
                    'description': 'SID does not correspond to any existing account'
                },
                'impact_analysis': {
                    'files_affected': sid_info['file_count'],
                    'directories_affected': sid_info['dir_count'],
                    'total_items_affected': total_occurrences,
                    'file_percentage': round(file_percentage, 2),
                    'directory_percentage': round(dir_percentage, 2),
                    'remediation_priority': priority
                },
                'recommended_remediation': {
                    'new_owner_account': self.target_owner_account,
                    'action_required': 'Change ownership to specified account',
                    'command_example': f'python fix_owner.py <path> -x -r -f "{self.target_owner_account}"',
                    'verification_steps': [
                        'Run with dry-run mode first (without -x flag)',
                        'Verify the target account exists and is accessible',
                        'Apply changes with -x flag',
                        'Verify ownership changes were successful'
                    ]
                },
                'additional_info': {
                    'sid_type': self._classify_sid_type(sid_string),
                    'likely_cause': self._determine_likely_cause(sid_string, sid_info),
                    'risk_assessment': self._assess_remediation_risk(total_occurrences, priority)
                }
            }
        
        return yaml_data
    
    def _classify_sid_type(self, sid_string: str) -> str:
        """
        Classify the type of SID based on its structure.
        
        Args:
            sid_string: SID string to classify
            
        Returns:
            String describing the SID type
        """
        if sid_string.startswith('S-1-5-21-'):
            return 'Domain/Local User or Group'
        elif sid_string.startswith('S-1-5-32-'):
            return 'Built-in Account'
        elif sid_string.startswith('S-1-5-'):
            return 'Well-known SID'
        elif sid_string.startswith('S-1-3-'):
            return 'Creator SID'
        else:
            return 'Unknown SID Type'
    
    def _determine_likely_cause(self, sid_string: str, sid_info: Dict) -> str:
        """
        Determine the likely cause of the orphaned SID.
        
        Args:
            sid_string: SID string
            sid_info: SID information dictionary
            
        Returns:
            String describing the likely cause
        """
        if sid_string.startswith('S-1-5-21-'):
            return 'User or group account was deleted from the domain/system'
        elif sid_string.startswith('S-1-5-32-'):
            return 'Built-in account corruption or system migration issue'
        else:
            return 'System migration, domain change, or account deletion'
    
    def _assess_remediation_risk(self, total_occurrences: int, priority: str) -> str:
        """
        Assess the risk level of remediation.
        
        Args:
            total_occurrences: Total number of items affected
            priority: Priority level (HIGH/MEDIUM/LOW)
            
        Returns:
            String describing the risk assessment
        """
        if priority == 'HIGH':
            return 'Low risk - High impact remediation recommended'
        elif priority == 'MEDIUM':
            return 'Low risk - Medium impact remediation recommended'
        else:
            return 'Very low risk - Low impact remediation optional'