"""
FileSystemWalker - Efficient directory traversal and ownership processing for the fix-owner script.

This module provides the core filesystem traversal functionality that coordinates
between security operations, statistics tracking, and error handling to process
directory structures efficiently and safely.

Key Features:
- Efficient directory traversal using os.walk() with recursion control
- Integration with SecurityManager for ownership operations
- Comprehensive error handling that continues processing after failures
- File and directory processing with configurable options
- Timeout support for large directory structures
- Statistics tracking for all operations

The FileSystemWalker serves as the main coordinator between:
- SecurityManager: For Windows security operations
- StatsTracker: For counting operations and measuring performance
- ErrorManager: For comprehensive error handling and recovery
- OutputManager: For user feedback and verbose logging
- TimeoutManager: For handling execution time limits

Classes:
    FileSystemWalker: Main filesystem traversal coordinator
"""

import os
from typing import Optional


class FileSystemWalker:
    """
    Handles filesystem traversal and coordinates ownership changes.
    
    This class provides efficient directory traversal using os.walk() with
    support for recursion control, file processing, and proper exception
    handling that continues processing after errors.
    """
    
    def __init__(self, security_manager, stats_tracker, error_manager=None, sid_tracker=None):
        """
        Initialize FileSystemWalker with required dependencies.
        
        Args:
            security_manager: SecurityManager instance for ownership operations
            stats_tracker: StatsTracker instance for counting operations
            error_manager: Optional ErrorManager for comprehensive error handling
            sid_tracker: Optional SidTracker for SID analysis and reporting
        """
        self.security_manager = security_manager
        self.stats_tracker = stats_tracker
        self.error_manager = error_manager
        self.sid_tracker = sid_tracker
        
        # Track failed files and directories for output directory logging
        self.failed_files = []
        self.failed_directories = []
    
    def walk_filesystem(self, root_path: str, owner_sid: object, 
                       recurse: bool = False, process_files: bool = False,
                       execute: bool = False, output_manager=None, 
                       timeout_manager=None) -> None:
        """
        Traverse filesystem and process ownership changes with comprehensive error handling.
        
        This method serves as the main coordinator for filesystem traversal, using
        Python's efficient os.walk() function to traverse directory structures while
        providing comprehensive error handling, timeout support, and integration
        with all other system components.
        
        Key Features:
        - Efficient directory traversal using os.walk() with minimal memory usage
        - Recursion control based on user preferences (-r option)
        - Optional file processing in addition to directories (-f option)
        - Comprehensive exception handling that continues processing after errors
        - Timeout checking to prevent indefinite execution on large structures
        - Integration with SecurityManager for Windows security operations
        - Statistics tracking for all operations and errors
        - Verbose output support for detailed processing information
        
        Processing Flow:
        1. Use os.walk() to traverse directory structure efficiently
        2. For each directory: check timeout, process ownership, update statistics
        3. If file processing enabled: process each file in current directory
        4. Control recursion based on user preferences
        5. Handle all exceptions gracefully to continue processing
        
        Args:
            root_path: Root directory path to start traversal from
            owner_sid: Target owner SID object for ownership changes
            recurse: Whether to recurse into subdirectories (controls os.walk behavior)
            process_files: Whether to process files in addition to directories
            execute: Whether to apply changes (True) or perform dry run (False)
            output_manager: Optional OutputManager for user feedback and verbose logging
            timeout_manager: Optional TimeoutManager for execution time limit checking
        """
        try:
            # PROGRESS TRACKING: Count total top-level directories for progress display
            # This is only needed for verbosity level 1 to show "Processing top-level directory X/Y"
            top_level_dirs_total = 0
            top_level_dirs_current = 0
            
            if output_manager and output_manager.is_level_1() and recurse:
                # Count top-level directories by examining immediate children of root
                try:
                    for item in os.listdir(root_path):
                        item_path = os.path.join(root_path, item)
                        if os.path.isdir(item_path):
                            top_level_dirs_total += 1
                except (OSError, PermissionError):
                    # If we can't list the directory, we'll just proceed without progress counters
                    top_level_dirs_total = 0
            
            # Use os.walk() for efficient directory traversal
            # os.walk() yields (dirpath, dirnames, filenames) tuples for each directory
            # This approach is memory-efficient as it processes one directory at a time
            for dirpath, dirnames, filenames in os.walk(root_path):
                
                # TIMEOUT CHECK: Verify we haven't exceeded the execution time limit
                # This check occurs at the directory level to provide reasonable granularity
                # without excessive overhead from checking on every single file
                if timeout_manager and timeout_manager.is_timeout_reached():
                    if output_manager:
                        output_manager.print_timeout_warning(
                            timeout_manager.get_elapsed_time(),
                            timeout_manager.timeout_seconds
                        )
                    # Break from the main loop to terminate processing gracefully
                    break
                
                # DIRECTORY ENTRY: Announce entering directory for level 1+ verbosity
                # Level 1 shows root and top-level directories, level 2+ shows all directories
                is_root_dir = (dirpath == root_path)
                is_top_level_dir = self._is_top_level_directory(dirpath, root_path)
                
                # PROGRESS TRACKING: Update counter for top-level directories
                if is_top_level_dir and top_level_dirs_total > 0:
                    top_level_dirs_current += 1
                
                if output_manager:
                    # Pass progress information for top-level directories
                    progress_info = None
                    if is_top_level_dir and top_level_dirs_total > 0:
                        progress_info = (top_level_dirs_current, top_level_dirs_total)
                    
                    output_manager.print_entering_directory(
                        dirpath, 
                        is_root=is_root_dir, 
                        is_top_level=is_top_level_dir,
                        progress=progress_info
                    )
                
                # DIRECTORY PROCESSING: Handle ownership for the current directory
                # This processes the directory itself, not its contents
                # Each directory is processed regardless of recursion settings
                self._process_directory(dirpath, owner_sid, execute, output_manager)
                
                # FILE PROCESSING: Handle files in current directory if requested
                # This only occurs when the -f/--files option is specified
                # Files are processed after their containing directory
                if process_files:
                    for filename in filenames:
                        # TIMEOUT CHECK: Also check timeout for individual files
                        # This is important for directories with many files
                        # Provides more responsive timeout handling in file-heavy directories
                        if timeout_manager and timeout_manager.is_timeout_reached():
                            if output_manager:
                                output_manager.print_timeout_warning(
                                    timeout_manager.get_elapsed_time(),
                                    timeout_manager.timeout_seconds
                                )
                            # Return immediately to stop all processing
                            return
                        
                        # Construct full file path and process ownership
                        file_path = os.path.join(dirpath, filename)
                        self._process_file(file_path, owner_sid, execute, output_manager)
                
                # DIRECTORY SUMMARY: Show completion status for level 1+ verbosity
                # Level 1 shows root and top-level directories, level 2+ shows all directories
                if output_manager:
                    # Pass progress information for top-level directories
                    progress_info = None
                    if is_top_level_dir and top_level_dirs_total > 0:
                        progress_info = (top_level_dirs_current, top_level_dirs_total)
                    
                    output_manager.print_directory_summary(
                        dirpath, 
                        is_root=is_root_dir, 
                        is_top_level=is_top_level_dir,
                        progress=progress_info
                    )
                
                # RECURSION CONTROL: Manage subdirectory traversal
                # os.walk() uses the dirnames list to determine which subdirectories to enter
                # By clearing this list, we prevent os.walk() from descending into subdirectories
                # This is more efficient than checking recursion settings in each iteration
                if not recurse:
                    # Clear the dirnames list to prevent os.walk from recursing
                    # This must be done after processing the current directory
                    # but before os.walk moves to the next iteration
                    dirnames.clear()
                    
        except KeyboardInterrupt:
            # Handle user interruption (Ctrl+C) gracefully
            # Provide feedback and re-raise to allow higher-level handling
            if output_manager:
                output_manager.print_general_message("\nOperation interrupted by user")
            raise
        except Exception as e:
            # Handle unexpected critical errors during filesystem traversal
            # These are typically system-level issues that prevent continued processing
            if output_manager:
                output_manager.print_general_error(f"Critical error during filesystem processing: {e}")
            
            # Log the critical filesystem failure with timestamp
            if self.error_manager:
                from error_manager import ErrorInfo, ErrorCategory
                critical_error = ErrorInfo(
                    category=ErrorCategory.FILESYSTEM,
                    path=root_path,
                    message=f"Critical filesystem processing error: {e}",
                    original_exception=e,
                    is_critical=True,
                    should_terminate=True
                )
                self.error_manager.log_critical_failure(
                    critical_error, 
                    f"Failed during filesystem traversal of {root_path}"
                )
            
            raise
    
    def _process_directory(self, dir_path: str, owner_sid: object, 
                          execute: bool, output_manager=None) -> None:
        """
        Process a single directory for ownership changes with comprehensive error handling.
        
        This method handles the complete workflow for processing a directory:
        1. Updates statistics to track directories examined
        2. Provides verbose output if requested
        3. Delegates to ownership processing with proper error handling
        4. Ensures processing continues even if this directory fails
        
        Args:
            dir_path: Full path to the directory to process
            owner_sid: Target owner SID object for ownership changes
            execute: Whether to apply changes (True) or perform dry run (False)
            output_manager: Optional OutputManager for user feedback and verbose logging
        """
        # STATISTICS: Track that we've examined this directory
        # This count includes all directories, regardless of whether ownership changes
        self.stats_tracker.increment_dirs_traversed()
        
        # VERBOSE OUTPUT: Show current directory being examined
        # This helps users track progress in verbose mode
        # Note: We'll call this after SID validation to provide accurate ownership status
        
        # ERROR HANDLING: Use ErrorManager context if available for comprehensive handling
        # The context manager ensures exceptions are properly categorized and handled
        if self.error_manager:
            # Use ErrorManager's context manager for sophisticated error handling
            # This provides error categorization, recovery strategies, and consistent reporting
            try:
                with self.error_manager.create_exception_context("Processing directory", dir_path):
                    self._process_directory_ownership(dir_path, owner_sid, execute, output_manager)
            except Exception as e:
                # Collect failed directory for output directory logging even with ErrorManager
                self.failed_directories.append({
                    'path': dir_path,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                # Re-raise to let ErrorManager handle it properly
                raise
        else:
            # FALLBACK: Basic error handling when ErrorManager is not available
            # This ensures the script can still function with minimal error handling
            try:
                self._process_directory_ownership(dir_path, owner_sid, execute, output_manager)
            except Exception as e:
                # Handle exception but continue processing other directories
                # This is critical for robustness - one failed directory shouldn't stop everything
                self.stats_tracker.increment_exceptions()
                
                # Collect failed directory for output directory logging
                self.failed_directories.append({
                    'path': dir_path,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                
                if output_manager:
                    output_manager.print_error(dir_path, e, is_directory=True)
    
    def _process_directory_ownership(self, dir_path: str, owner_sid: object, 
                                   execute: bool, output_manager=None) -> None:
        """
        Process directory ownership change with comprehensive validation and error handling.
        
        This method implements the core logic for determining whether a directory's
        ownership needs to be changed and performing the change if necessary.
        It follows a three-step process:
        1. Retrieve current ownership information
        2. Validate whether the current owner SID is valid/orphaned
        3. Change ownership if needed and track the operation
        
        Args:
            dir_path: Full path to the directory to process
            owner_sid: Target owner SID object for ownership changes
            execute: Whether to apply changes (True) or perform dry run (False)
            output_manager: Optional OutputManager for user feedback and verbose logging
        """
        # STEP 1: OWNERSHIP RETRIEVAL
        # Get current owner information using SecurityManager
        # This returns both the human-readable name (if valid) and the SID object
        owner_name, current_owner_sid = self.security_manager.get_current_owner(dir_path)
        
        # SID TRACKING: Record SID occurrence if tracking is enabled
        # This tracks all SIDs encountered, not just orphaned ones
        if self.sid_tracker:
            self.sid_tracker.track_directory_sid(dir_path, current_owner_sid)
        
        # STEP 2: SID VALIDATION
        # Check if current owner SID is invalid/orphaned
        # Invalid SIDs are exactly what we're looking for - they indicate
        # ownership by accounts that no longer exist (deleted users, etc.)
        is_valid_owner = self.security_manager.is_sid_valid(current_owner_sid)
        
        # VERBOSE OUTPUT: Show current directory being examined with ownership status
        # This helps users track progress in verbose mode and shows accurate ownership info
        if output_manager:
            output_manager.print_examining_path(dir_path, is_directory=True, 
                                              current_owner=owner_name, 
                                              is_valid_owner=is_valid_owner)
        
        if not is_valid_owner:
            
            # STEP 3: OWNERSHIP CHANGE (if needed)
            # Only change ownership if we're in execute mode
            # In dry-run mode, we simulate the change for reporting purposes
            if execute:
                # Apply the actual ownership change using Windows Security APIs
                self.security_manager.set_owner(dir_path, owner_sid)
            
            # STATISTICS: Track that we changed (or would change) this directory's ownership
            # This count represents directories with orphaned ownership that were processed
            self.stats_tracker.increment_dirs_changed()
            
            # USER FEEDBACK: Report the ownership change to the user
            # This provides visibility into what the script is doing
            if output_manager:
                output_manager.print_ownership_change(
                    dir_path, 
                    is_directory=True, 
                    dry_run=not execute  # Indicate whether this was a simulation
                )
    
    def _process_file(self, file_path: str, owner_sid: object, 
                     execute: bool, output_manager=None) -> None:
        """
        Process a single file for ownership changes with comprehensive error handling.
        
        This method handles the complete workflow for processing a file:
        1. Updates statistics to track files examined
        2. Provides verbose output if requested
        3. Delegates to ownership processing with proper error handling
        4. Ensures processing continues even if this file fails
        
        Args:
            file_path: Full path to the file to process
            owner_sid: Target owner SID object for ownership changes
            execute: Whether to apply changes (True) or perform dry run (False)
            output_manager: Optional OutputManager for user feedback and verbose logging
        """
        # STATISTICS: Track that we've examined this file
        # This count includes all files, regardless of whether ownership changes
        self.stats_tracker.increment_files_traversed()
        
        # VERBOSE OUTPUT: Show current file being examined
        # This helps users track progress in verbose mode, especially for file-heavy directories
        # Note: We'll call this after SID validation to provide accurate ownership status
        
        # ERROR HANDLING: Use ErrorManager context if available for comprehensive handling
        # The context manager ensures exceptions are properly categorized and handled
        if self.error_manager:
            # Use ErrorManager's context manager for sophisticated error handling
            # This provides error categorization, recovery strategies, and consistent reporting
            try:
                with self.error_manager.create_exception_context("Processing file", file_path):
                    self._process_file_ownership(file_path, owner_sid, execute, output_manager)
            except Exception as e:
                # Collect failed file for output directory logging even with ErrorManager
                self.failed_files.append({
                    'path': file_path,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                # Re-raise to let ErrorManager handle it properly
                raise
        else:
            # FALLBACK: Basic error handling when ErrorManager is not available
            # This ensures the script can still function with minimal error handling
            try:
                self._process_file_ownership(file_path, owner_sid, execute, output_manager)
            except Exception as e:
                # Handle exception but continue processing other files
                # This is critical for robustness - one failed file shouldn't stop everything
                self.stats_tracker.increment_exceptions()
                
                # Collect failed file for output directory logging
                self.failed_files.append({
                    'path': file_path,
                    'error': str(e),
                    'exception_type': type(e).__name__
                })
                
                if output_manager:
                    output_manager.print_error(file_path, e, is_directory=False)
    
    def _process_file_ownership(self, file_path: str, owner_sid: object, 
                              execute: bool, output_manager=None) -> None:
        """
        Process file ownership change with comprehensive validation and error handling.
        
        This method implements the core logic for determining whether a file's
        ownership needs to be changed and performing the change if necessary.
        It follows the same three-step process as directory processing:
        1. Retrieve current ownership information
        2. Validate whether the current owner SID is valid/orphaned
        3. Change ownership if needed and track the operation
        
        Args:
            file_path: Full path to the file to process
            owner_sid: Target owner SID object for ownership changes
            execute: Whether to apply changes (True) or perform dry run (False)
            output_manager: Optional OutputManager for user feedback and verbose logging
        """
        # STEP 1: OWNERSHIP RETRIEVAL
        # Get current owner information using SecurityManager
        # This returns both the human-readable name (if valid) and the SID object
        owner_name, current_owner_sid = self.security_manager.get_current_owner(file_path)
        
        # SID TRACKING: Record SID occurrence if tracking is enabled
        # This tracks all SIDs encountered, not just orphaned ones
        if self.sid_tracker:
            self.sid_tracker.track_file_sid(file_path, current_owner_sid)
        
        # STEP 2: SID VALIDATION
        # Check if current owner SID is invalid/orphaned
        # Invalid SIDs are exactly what we're looking for - they indicate
        # ownership by accounts that no longer exist (deleted users, etc.)
        is_valid_owner = self.security_manager.is_sid_valid(current_owner_sid)
        
        # VERBOSE OUTPUT: Show current file being examined with ownership status
        # This helps users track progress in verbose mode and shows accurate ownership info
        if output_manager:
            output_manager.print_examining_path(file_path, is_directory=False, 
                                              current_owner=owner_name, 
                                              is_valid_owner=is_valid_owner)
        
        if not is_valid_owner:
            
            # STEP 3: OWNERSHIP CHANGE (if needed)
            # Only change ownership if we're in execute mode
            # In dry-run mode, we simulate the change for reporting purposes
            if execute:
                # Apply the actual ownership change using Windows Security APIs
                self.security_manager.set_owner(file_path, owner_sid)
            
            # STATISTICS: Track that we changed (or would change) this file's ownership
            # This count represents files with orphaned ownership that were processed
            self.stats_tracker.increment_files_changed()
            
            # USER FEEDBACK: Report the ownership change to the user
            # This provides visibility into what the script is doing
            if output_manager:
                output_manager.print_ownership_change(
                    file_path,
                    is_directory=False,
                    dry_run=not execute  # Indicate whether this was a simulation
                )
    
    def _is_top_level_directory(self, dir_path: str, root_path: str) -> bool:
        """
        Determine if a directory is a top-level directory (immediate child of root).
        
        Args:
            dir_path: Directory path to check
            root_path: Root directory path
            
        Returns:
            True if dir_path is an immediate child of root_path, False otherwise
        """
        # Normalize paths to handle different path separators
        normalized_root = os.path.normpath(root_path)
        normalized_dir = os.path.normpath(dir_path)
        
        # If it's the root directory itself, it's not a top-level directory
        if normalized_dir == normalized_root:
            return False
        
        # Get the parent directory of the current directory
        parent_dir = os.path.dirname(normalized_dir)
        
        # If the parent is the root, then this is a top-level directory
        return parent_dir == normalized_root
    
    def write_failed_files_log(self) -> None:
        """
        Write failed files and directories to the output directory.
        
        This method creates a comprehensive log of all files and directories
        that failed during processing, writing it to the output directory
        for later analysis and troubleshooting.
        """
        if not self.error_manager:
            return
        
        # Only write log if there are failures to report
        total_failures = len(self.failed_files) + len(self.failed_directories)
        if total_failures == 0:
            return
        
        # Prepare failure summary
        summary = f"""
FILESYSTEM PROCESSING FAILURES SUMMARY
======================================
Total Failed Files: {len(self.failed_files)}
Total Failed Directories: {len(self.failed_directories)}
Total Failures: {total_failures}

This log contains all files and directories that could not be processed
during the ownership change operation. Common causes include:
- Access denied (insufficient permissions)
- Files in use by other processes
- Network connectivity issues (for network paths)
- Corrupted file system entries
- Invalid or inaccessible paths

Review each failure to determine if manual intervention is required.
"""
        
        # Combine all failures into a single list for logging
        all_failures = []
        
        # Add directory failures
        for failure in self.failed_directories:
            all_failures.append({
                'type': 'Directory',
                'path': failure['path'],
                'error': failure['error'],
                'exception_type': failure['exception_type']
            })
        
        # Add file failures
        for failure in self.failed_files:
            all_failures.append({
                'type': 'File',
                'path': failure['path'],
                'error': failure['error'],
                'exception_type': failure['exception_type']
            })
        
        # Sort failures by path for easier review
        all_failures.sort(key=lambda x: x['path'])
        
        # Convert to formatted strings for the error manager
        formatted_failures = []
        for failure in all_failures:
            formatted_failures.append(
                f"{failure['type']}: {failure['path']}\n"
                f"  Error: {failure['error']}\n"
                f"  Exception: {failure['exception_type']}"
            )
        
        # Write the failures log using the error manager
        self.error_manager.log_operation_failures(
            operation="filesystem_processing",
            failures=formatted_failures,
            summary=summary
        )