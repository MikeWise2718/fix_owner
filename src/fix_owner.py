#!/usr/bin/env python3
"""
Fix Owner Script - Recursively take ownership of directories/files with orphaned SIDs.

This script provides comprehensive ownership management for Windows systems,
allowing administrators to fix orphaned SIDs after user deletions or system migrations.

OVERVIEW:
    When users are deleted from a Windows system or during system migrations,
    directories and files may be left with orphaned Security Identifiers (SIDs)
    that no longer correspond to valid user accounts. This script identifies
    such orphaned ownership and changes it to a specified valid account.

FEATURES:
    - Recursive directory traversal with optional file processing
    - Dry-run mode for safe testing before making changes
    - Comprehensive statistics and error reporting
    - Timeout support for large directory structures
    - Verbose and quiet output modes
    - Robust error handling that continues processing after failures

REQUIREMENTS:
    - Python 3.13+ (required for modern language features and type hints)
    - pywin32 module (pip install pywin32)
    - Administrator privileges for security operations
    - Windows 10/11 or Windows Server 2016+

USAGE:
    python fix_owner.py <root_path> [owner_account] [options]
    
    Arguments:
        root_path       Root directory to start processing from
        owner_account   Target owner account (default: current logged-in user)
    
    Options:
        -x, --execute   Apply ownership changes (default: dry run)
        -r, --recurse   Recurse into subdirectories
        -f, --files     Process files in addition to directories
        -v, --verbose LEVEL   Verbose output level: 0=statistics only, 1=top-level directory status, 2=directory progress, 3=detailed examination
        -q, --quiet     Suppress all output including statistics
        -to SECONDS     Timeout after specified seconds (0 = no timeout)
        -ts, --track-sids   Enable SID tracking and generate ownership analysis report

EXAMPLES:
    # Basic dry run to see what would be changed (safest first step)
    python fix_owner.py C:\\MyFolder Administrator
    
    # Dry run with verbose output to see detailed processing
    python fix_owner.py C:\\MyFolder -v Administrator
    
    # Actually apply changes with recursion and verbose output
    python fix_owner.py C:\\MyFolder -x -r -v Administrator
    
    # Process files in addition to directories with recursion
    python fix_owner.py D:\\Data -x -r -f Administrator
    
    # Large directory with timeout to prevent indefinite execution
    python fix_owner.py D:\\LargeArchive -x -r --timeout 300 Administrator
    
    # Quiet mode for scripted/automated execution
    python fix_owner.py E:\\Archive -x -r -q Administrator
    
    # Use current logged-in user as target owner (no account specified)
    python fix_owner.py C:\\MyFolder -x -r
    
    # Domain account as target owner
    python fix_owner.py C:\\MyFolder -x -r DOMAIN\\ServiceAccount
    
    # Process only root directory (no recursion)
    python fix_owner.py C:\\SingleDir -x Administrator
    
    # Comprehensive processing with all options
    python fix_owner.py C:\\CompleteRestore -x -r -f -v --timeout 1800 Administrator

COMMON SCENARIOS:
    
    1. AFTER USER DELETION:
       When a user account has been deleted but their files remain:
       python fix_owner.py C:\\Users\\DeletedUser -x -r -f Administrator
    
    2. SYSTEM MIGRATION:
       After migrating from one domain to another:
       python fix_owner.py D:\\SharedData -x -r NEWDOMAIN\\Administrator
    
    3. PERMISSION REPAIR:
       When permissions are broken after system restore:
       python fix_owner.py C:\\ProgramData\\MyApp -x -r -v Administrator
    
    4. BULK CLEANUP:
       Processing multiple directories with timeout for safety:
       python fix_owner.py E:\\Archive -x -r -f --timeout 3600 Administrator
    
    5. TESTING BEFORE CHANGES:
       Always test first with dry run and verbose output:
       python fix_owner.py C:\\ImportantData -r -v Administrator
       # Then apply changes:
       python fix_owner.py C:\\ImportantData -x -r Administrator

WORKFLOW RECOMMENDATIONS:
    
    1. Start with dry run: Test without -x flag first
    2. Use verbose mode: Add -v to see what's happening
    3. Test small scope: Start without -r to test single directory
    4. Add recursion: Use -r after testing single directory
    5. Include files: Add -f if file ownership also needs fixing
    6. Set timeout: Use --timeout for large directory structures
    7. Use quiet mode: Add -q for automated/scripted execution

SECURITY CONSIDERATIONS:
    - This script requires Administrator privileges to modify file ownership
    - Only orphaned/invalid SIDs are changed - valid ownership is preserved
    - All operations are logged and can be run in dry-run mode first
    - Target owner account is validated before processing begins

PERFORMANCE NOTES:
    - Uses efficient os.walk() for directory traversal
    - Processes items incrementally to minimize memory usage
    - Supports timeout to prevent indefinite execution on large structures
    - Exception handling allows processing to continue after individual failures

AUTHOR: System Administration Team
VERSION: 1.0.0
LICENSE: Internal Use Only
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# YAML support for remediation file reading
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Import common utilities and constants
try:
    from .common import (
        section_clr, error_clr, warn_clr, reset_clr, COLORAMA_AVAILABLE,
        SCRIPT_VERSION, MAX_PATH_LENGTH, EXIT_SUCCESS, EXIT_ERROR, EXIT_INTERRUPTED,
        PYWIN32_AVAILABLE, safe_exit, validate_path_exists, validate_path_is_directory,
        setup_module_path, get_execution_start_timestamp
    )
except ImportError:
    # Fall back to absolute imports (when run as a script)
    from common import (
        section_clr, error_clr, warn_clr, reset_clr, COLORAMA_AVAILABLE,
        SCRIPT_VERSION, MAX_PATH_LENGTH, EXIT_SUCCESS, EXIT_ERROR, EXIT_INTERRUPTED,
        PYWIN32_AVAILABLE, safe_exit, validate_path_exists, validate_path_is_directory,
        setup_module_path, get_execution_start_timestamp
    )

# Check for pywin32 availability (imported from common)
if not PYWIN32_AVAILABLE:
    safe_exit(EXIT_ERROR, "Error: pywin32 module is required. Install with: pip install pywin32")

# Import our custom components
try:
    # Try relative imports first (when imported as a module)
    from .timeout_manager import TimeoutManager
    from .output_manager import OutputManager
    from .filesystem_walker import FileSystemWalker
    from .error_manager import ErrorManager, ErrorCategory
    from .sid_tracker import SidTracker
    from .stats_tracker import StatsTracker
    from .security_manager import SecurityManager
except ImportError:
    # Fall back to absolute imports (when run as a script)
    setup_module_path()
    from timeout_manager import TimeoutManager
    from output_manager import OutputManager
    from filesystem_walker import FileSystemWalker
    from error_manager import ErrorManager, ErrorCategory
    from sid_tracker import SidTracker
    from stats_tracker import StatsTracker
    from security_manager import SecurityManager




@dataclass
class ExecutionOptions:
    """Configuration options for script execution."""
    execute: bool = False          # -x flag: Apply changes vs dry run
    recurse: bool = False          # -r flag: Recurse into subdirectories
    files: bool = False            # -f flag: Process files in addition to directories
    verbose: bool = False          # -v flag: Verbose output
    quiet: bool = False            # -q flag: Suppress all output
    timeout: int = 0               # -ts value: Timeout in seconds
    track_sids: bool = False       # -ts/--track-sids flag: Enable SID tracking
    yaml_remediation: str = ""     # -yr/--yaml-remediation: YAML remediation file
    root_path: str = ""            # Positional argument: Root path to process
    owner_account: str = ""        # Target owner account
    start_timestamp: float = 0.0   # Execution start timestamp
    start_timestamp_str: str = ""  # Formatted timestamp for filenames


@dataclass
class ExecutionStats:
    """Statistics tracking for script execution."""
    dirs_traversed: int = 0
    files_traversed: int = 0
    dirs_changed: int = 0
    files_changed: int = 0
    exceptions: int = 0
    start_time: float = field(default_factory=time.time)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start."""
        return time.time() - self.start_time



def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments with comprehensive validation.
    
    This function sets up the argument parser with all supported options,
    validates argument combinations, and ensures the root path exists and
    is accessible before proceeding with execution.
    
    Returns:
        Parsed arguments namespace containing all validated options
        
    Raises:
        SystemExit: If arguments are invalid, help is requested, or validation fails
    """
    parser = argparse.ArgumentParser(
        description="Recursively take ownership of directories/files with orphaned SIDs.",
        epilog="Examples: python fix_owner.py C:\\MyFolder -x -r -v Administrator\n          python fix_owner.py C:\\MyFolder -x -r --yaml-remediation remediation.yaml"
    )
    
    # Positional arguments
    parser.add_argument(
        'root_path',
        help='Root directory path to start processing from'
    )
    parser.add_argument(
        'owner_account',
        nargs='?',
        help='Target owner account (default: current logged-in user)'
    )
    
    # Optional flags
    parser.add_argument(
        '-x', '--execute',
        action='store_true',
        help='Apply ownership changes (default: dry run mode)'
    )
    parser.add_argument(
        '-r', '--recurse',
        action='store_true',
        help='Recurse into subdirectories'
    )
    parser.add_argument(
        '-f', '--files',
        action='store_true',
        help='Examine files as well as directories'
    )
    parser.add_argument(
        '-v', '--verbose',
        type=int,
        default=0,
        metavar='LEVEL',
        help='Verbose output level: 0=statistics only, 1=top-level directory status, 2=directory progress, 3=detailed examination'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output including statistics'
    )
    parser.add_argument(
        '-to', '--timeout',
        type=int,
        default=0,
        metavar='SECONDS',
        help='Terminate execution after specified seconds (0 = no timeout)'
    )
    parser.add_argument(
        '-ts', '--track-sids',
        action='store_true',
        help='Enable SID tracking and generate ownership analysis report'
    )
    parser.add_argument(
        '-yr', '--yaml-remediation',
        type=str,
        metavar='FILENAME',
        help='Read remediation plan from YAML file in current directory (uses new_owner_account for ownership changes)'
    )
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.verbose and args.quiet:
        parser.error("Cannot specify both --verbose and --quiet options")
    
    if args.timeout < 0:
        parser.error("Timeout value must be non-negative")
    
    # Validate YAML remediation and owner account combination
    if args.yaml_remediation and args.owner_account:
        parser.error("Cannot specify both owner_account and --yaml-remediation options (YAML file provides the owner account)")
    
    if not args.yaml_remediation and not args.owner_account:
        # This is allowed - will use current user as default
        pass
    
    if not validate_path_exists(args.root_path):
        parser.error(f"Root path does not exist: {args.root_path}")
    
    if not validate_path_is_directory(args.root_path):
        parser.error(f"Root path is not a directory: {args.root_path}")
    
    return args


def resolve_owner_account(account_name: Optional[str], output: OutputManager, security_manager: SecurityManager) -> tuple[object, str]:
    """
    Resolve owner account name to SID using SecurityManager with comprehensive error handling.
    
    This function validates that the target owner account exists and can be used
    for ownership operations. It provides clear error messages if the account
    cannot be resolved, which is critical for preventing runtime failures.
    
    Args:
        account_name: Account name to resolve (e.g., "Administrator", "DOMAIN\\User"), 
                     or None for current logged-in user
        output: Output manager for user feedback and error reporting
        security_manager: SecurityManager instance for account resolution
        
    Returns:
        Tuple of (SID object, resolved account name) for the resolved account
        
    Raises:
        SystemExit: If account cannot be resolved (critical error that prevents execution)
    """
    try:
        # Attempt to resolve the account name to a SID
        # This validates that the account exists and is accessible
        sid, resolved_name = security_manager.resolve_owner_account(account_name)
        
        # Inform user of the resolved account name (includes domain if applicable)
        output.print_info_pair("Target owner account", resolved_name)
        
        # Log additional account information in verbose mode
        if output.get_verbose_level() >= 1:
            output.print_general_message(f"Account resolution successful for: {resolved_name}")
        
        return sid, resolved_name
        
    except Exception as e:
        # Handle account resolution failure - this is a critical error
        account_display = account_name or "current logged-in user"
        
        # Provide detailed error information to help user resolve the issue
        output.print_invalid_owner_error(account_display, e)
        output.print_general_error("Failed to resolve target owner account")
        
        # Suggest common solutions in verbose mode
        if output.get_verbose_level() >= 1:
            output.print_general_message("Common solutions:")
            output.print_general_message("- Verify the account name is spelled correctly")
            output.print_general_message("- For domain accounts, use DOMAIN\\Username format")
            output.print_general_message("- Ensure the account exists and is not disabled")
            output.print_general_message("- Check that you have permission to query the account")
        
        # Exit with error code since we cannot proceed without a valid target account
        safe_exit(EXIT_ERROR)


def load_yaml_remediation(yaml_filename: str, output: OutputManager) -> Optional[str]:
    """
    Load remediation plan from YAML file and extract new_owner_account.
    
    This function reads a YAML remediation file (typically generated by a previous
    run with --track-sids) and extracts the recommended new_owner_account from
    the remediation plan. This allows for automated remediation based on previous
    analysis.
    
    Args:
        yaml_filename: Name of YAML file in current working directory
        output: Output manager for user feedback and error reporting
        
    Returns:
        The new_owner_account string from the remediation plan, or None if not found
        
    Raises:
        SystemExit: If YAML file cannot be read or parsed (critical error)
    """
    if not YAML_AVAILABLE:
        output.print_general_error("PyYAML is not installed. Install with: pip install PyYAML")
        safe_exit(EXIT_ERROR)
    
    yaml_path = os.path.join(os.getcwd(), yaml_filename)
    
    if not os.path.exists(yaml_path):
        output.print_general_error(f"YAML remediation file not found: {yaml_path}")
        safe_exit(EXIT_ERROR)
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
        
        if not yaml_data:
            output.print_general_error(f"YAML file is empty or invalid: {yaml_filename}")
            safe_exit(EXIT_ERROR)
        
        # Extract new_owner_account from the first orphaned SID entry
        # The YAML structure is: orphaned_sids -> [list] -> recommended_remediation -> new_owner_account
        if 'orphaned_sids' in yaml_data and yaml_data['orphaned_sids']:
            first_sid = yaml_data['orphaned_sids'][0]
            if 'recommended_remediation' in first_sid:
                remediation = first_sid['recommended_remediation']
                if 'new_owner_account' in remediation:
                    new_owner = remediation['new_owner_account']
                    
                    # Display loaded remediation information
                    if output.get_verbose_level() >= 1:
                        output.print_general_message(f"Loaded YAML remediation file: {yaml_filename}")
                        output.print_info_pair("  New owner account", new_owner)
                        
                        # Show additional remediation details if available
                        if 'action_required' in remediation:
                            output.print_info_pair("  Action required", remediation['action_required'])
                        
                        # Show impact analysis if available
                        if 'impact_analysis' in first_sid:
                            impact = first_sid['impact_analysis']
                            if 'total_items_affected' in impact:
                                output.print_info_pair("  Items affected", str(impact['total_items_affected']))
                            if 'remediation_priority' in impact:
                                output.print_info_pair("  Priority", impact['remediation_priority'])
                    
                    return new_owner
        
        output.print_general_error(f"No new_owner_account found in YAML file: {yaml_filename}")
        output.print_general_message("Expected structure: orphaned_sids[0].recommended_remediation.new_owner_account")
        safe_exit(EXIT_ERROR)
        
    except yaml.YAMLError as e:
        output.print_general_error(f"Error parsing YAML file {yaml_filename}: {e}")
        safe_exit(EXIT_ERROR)
    except Exception as e:
        output.print_general_error(f"Error reading YAML file {yaml_filename}: {e}")
        safe_exit(EXIT_ERROR)


def process_filesystem(options: ExecutionOptions, owner_sid: object, 
                      stats: StatsTracker, output: OutputManager,
                      timeout_manager: TimeoutManager, security_manager: SecurityManager,
                      error_manager: ErrorManager, sid_tracker=None) -> None:
    """
    Process filesystem starting from root path using FileSystemWalker with comprehensive coordination.
    
    This function serves as the main coordinator for filesystem processing, creating
    and configuring the FileSystemWalker with all necessary dependencies and then
    delegating the actual traversal and ownership processing to it.
    
    The function ensures proper integration between all components:
    - SecurityManager for ownership operations
    - StatsTracker for counting operations and errors
    - ErrorManager for comprehensive error handling
    - OutputManager for user feedback
    - TimeoutManager for execution time limits
    
    Args:
        options: ExecutionOptions containing all user-specified configuration
        owner_sid: Target owner SID object for ownership changes
        stats: StatsTracker instance for counting operations and measuring performance
        output: OutputManager instance for user feedback and verbose logging
        timeout_manager: TimeoutManager instance for handling execution time limits
        security_manager: SecurityManager instance for Windows security operations
        error_manager: ErrorManager instance for comprehensive error handling and recovery
    """
    # Create FileSystemWalker instance with all required dependencies
    # The walker coordinates between security operations, statistics tracking, and error handling
    walker = FileSystemWalker(security_manager, stats, error_manager, sid_tracker)
    
    # Log the start of filesystem processing in verbose mode
    if output.get_verbose_level() >= 1:
        mode = "EXECUTE" if options.execute else "DRY RUN"
        output.print_info_pair("Processing mode", mode)
        output.print_info_pair("Processing scope", 'files and directories' if options.files else 'directories only')
        output.print_info_pair("Recursion", 'enabled' if options.recurse else 'disabled')
        if options.timeout > 0:
            output.print_info_pair("Timeout", f"{options.timeout} seconds")
    
    # Delegate filesystem processing to the FileSystemWalker
    # This is where the actual traversal and ownership changes occur
    walker.walk_filesystem(
        root_path=options.root_path,
        owner_sid=owner_sid,
        recurse=options.recurse,
        process_files=options.files,
        execute=options.execute,
        output_manager=output,
        timeout_manager=timeout_manager
    )
    
    # Write failed files log to output directory after processing completes
    # This provides a comprehensive record of any files that could not be processed
    walker.write_failed_files_log()


def main() -> None:
    """
    Main execution flow orchestrating all components with comprehensive error handling.
    
    This function serves as the primary entry point and coordinator for the entire
    fix-owner script execution. It follows a structured workflow:
    
    1. Command-line argument parsing and validation
    2. Component initialization (output, stats, error handling, security)
    3. Administrator privilege validation
    4. Target owner account resolution and validation
    5. Timeout configuration and setup
    6. Filesystem processing coordination
    7. Final statistics reporting and cleanup
    
    The function implements comprehensive error handling at each stage, ensuring
    that critical errors are reported clearly and the script exits gracefully.
    Non-critical errors during filesystem processing are handled by individual
    components and allow processing to continue.
    
    Exit Codes:
        0 (EXIT_SUCCESS): Normal completion
        1 (EXIT_ERROR): Critical error that prevented execution
        2 (EXIT_INTERRUPTED): User interruption (Ctrl+C)
    """
    try:
        # PHASE 0: Record execution start time for logging and failure tracking
        # This timestamp will be used for constructing failure log filenames
        start_timestamp, start_timestamp_str = get_execution_start_timestamp()
        
        # PHASE 1: Command-line argument parsing and validation
        # Parse and validate all command-line arguments, ensuring required parameters
        # are present and option combinations are valid
        args = parse_arguments()
        
        # Create structured execution options from parsed arguments
        # This centralizes all configuration in a single data structure
        options = ExecutionOptions(
            execute=args.execute,          # Whether to apply changes or dry run
            recurse=args.recurse,          # Whether to process subdirectories
            files=args.files,              # Whether to process files in addition to directories
            verbose=args.verbose,          # Whether to show detailed processing info
            quiet=args.quiet,              # Whether to suppress all output
            timeout=args.timeout,          # Maximum execution time in seconds
            track_sids=args.track_sids,    # Whether to enable SID tracking
            yaml_remediation=args.yaml_remediation or "",  # YAML remediation file
            root_path=args.root_path,      # Starting directory for processing
            owner_account=args.owner_account or "",  # Target owner account
            start_timestamp=start_timestamp,         # Execution start timestamp
            start_timestamp_str=start_timestamp_str  # Formatted timestamp for filenames
        )
        
        # PHASE 2: Component initialization and dependency injection
        # Initialize statistics tracking to monitor performance and operations
        stats = StatsTracker()
        
        # Initialize output manager with user's verbosity preferences
        # This centralizes all output formatting and stream management
        output = OutputManager(
            verbose_level=args.verbose,
            quiet=args.quiet
        )
        
        # Print opening information
        output.print_general_message("fix_owner - a utility to change the owner on sets of Windows 11 files")
        output.print_info_pair("Script version", SCRIPT_VERSION)
        output.print_info_pair("Python version", sys.version)
        output.print_info_pair("Execution started", options.start_timestamp_str.replace("_", " at "))
        
        # Initialize comprehensive error manager with dependencies
        # This provides centralized error handling, categorization, and recovery
        error_manager = ErrorManager(
            stats_tracker=stats, 
            output_manager=output, 
            start_timestamp_str=options.start_timestamp_str
        )
        
        # Initialize security manager with error handling integration
        # This handles all Windows security API operations with proper error handling
        security_manager = SecurityManager(error_manager=error_manager)
        
        # PHASE 3: Security validation and privilege checking
        # Validate that we have Administrator privileges required for ownership changes
        # This prevents runtime failures and provides clear error messages
        error_manager.validate_administrator_privileges()
        
        # PHASE 4: Execution mode notification and user feedback
        # Clearly indicate whether this is a dry run or will make actual changes
        # This prevents accidental modifications and sets user expectations
        if options.execute:
            output.print_execution_mode_notice()
            if output.get_verbose_level() >= 1:
                output.print_general_message("Changes will be applied to filesystem")
        else:
            output.print_dry_run_notice()
        
        # PHASE 5: YAML remediation file processing (if specified)
        # Load remediation plan from YAML file and override owner account
        if options.yaml_remediation:
            yaml_owner_account = load_yaml_remediation(options.yaml_remediation, output)
            if yaml_owner_account:
                # Override the owner account with the one from YAML file
                original_owner = options.owner_account
                options.owner_account = yaml_owner_account
                
                if output.get_verbose_level() >= 1:
                    if original_owner:
                        output.print_general_message(f"Owner account overridden by YAML remediation:")
                        output.print_info_pair("  Original", original_owner)
                        output.print_info_pair("  From YAML", yaml_owner_account)
                    else:
                        output.print_general_message(f"Owner account set from YAML remediation: {yaml_owner_account}")
        
        # PHASE 6: Target owner account resolution and validation
        # Resolve the target owner account to a SID and validate it exists
        # This is critical - we cannot proceed without a valid target account
        owner_sid, resolved_owner_name = resolve_owner_account(options.owner_account, output, security_manager)
        
        # Initialize SID tracker if requested (after account resolution)
        # This provides comprehensive SID tracking and reporting functionality
        sid_tracker = None
        if options.track_sids:
            sid_tracker = SidTracker(
                security_manager=security_manager,
                start_timestamp_str=options.start_timestamp_str,
                target_owner_account=resolved_owner_name
            )
            if output.get_verbose_level() >= 1:
                output.print_general_message("SID tracking enabled - ownership analysis will be generated")
        
        # PHASE 7: Operation startup information and logging
        # Provide user with comprehensive information about what will be processed
        output.print_startup_info(
            options.root_path,
            resolved_owner_name,
            options.recurse,
            options.files
        )
        
        # Log additional configuration details in verbose mode
        if output.get_verbose_level() >= 1:
            output.print_info_pair("Maximum path length", str(MAX_PATH_LENGTH))
            if options.timeout > 0:
                output.print_info_pair("Execution timeout", f"{options.timeout} seconds")
        
        # PHASE 8: Timeout configuration and setup
        # Initialize timeout manager for handling execution time limits
        timeout_manager = TimeoutManager(options.timeout)
        
        # Setup timeout handler if a timeout was specified
        # This ensures graceful termination for long-running operations
        if options.timeout > 0:
            timeout_manager.setup_timeout_handler()
            if output.get_verbose_level() >= 1:
                output.print_general_message("Timeout handler configured")
        
        try:
            # PHASE 9: Main filesystem processing
            # This is where the actual work happens - traverse directories and fix ownership
            # All error handling and recovery is managed by the individual components
            if output.get_verbose_level() >= 1:
                output.print_general_message(f"\n{section_clr}{'=' * 50}{reset_clr}")
                output.print_general_message(f"{section_clr}BEGINNING FILESYSTEM PROCESSING{reset_clr}")
                output.print_general_message(f"{section_clr}{'=' * 50}{reset_clr}")
            
            process_filesystem(options, owner_sid, stats, output, timeout_manager, security_manager, error_manager, sid_tracker)
            
            # Print terminating bars after filesystem processing
            if output.get_verbose_level() >= 1:
                output.print_general_message(f"{section_clr}{'=' * 50}{reset_clr}")
            
        finally:
            # PHASE 10: Cleanup and resource management
            # Always cleanup timeout resources, even if processing was interrupted
            timeout_manager.cancel_timeout()
            if output.get_verbose_level() >= 1:
                output.print_general_message("Timeout handler cleaned up")
        
        # PHASE 10: Completion notification and final reporting
        # Notify user of successful completion
        output.print_completion_message()
        
        # Generate and display final statistics report
        # This provides comprehensive information about what was processed
        stats.print_report(quiet=options.quiet, is_simulation=not options.execute, output_manager=output)
        
        # Generate SID tracking report if enabled
        # This provides detailed ownership analysis and SID distribution
        if sid_tracker and not options.quiet:
            sid_tracker.generate_report(output)
        
        # Log successful completion in verbose mode
        if output.get_verbose_level() >= 1:
            output.print_general_message("Script execution completed successfully")
        
    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C) gracefully
        safe_exit(EXIT_INTERRUPTED, "\nOperation cancelled by user")
    except Exception as e:
        # Handle any unexpected critical errors
        error_message = f"Critical error: {e}"
        
        # Log critical failure to timestamped file if error_manager is available
        if 'error_manager' in locals():
            from error_manager import ErrorInfo, ErrorCategory
            critical_error = ErrorInfo(
                category=ErrorCategory.CRITICAL,
                path=None,
                message=error_message,
                original_exception=e,
                is_critical=True,
                should_terminate=True
            )
            error_manager.log_critical_failure(critical_error, "Unhandled exception in main execution")
        
        # In verbose mode, provide additional debugging information
        if 'output' in locals() and output.get_verbose_level() >= 1:
            import traceback
            print("Stack trace:", file=sys.stderr)
            traceback.print_exc()
        
        safe_exit(EXIT_ERROR, error_message)


if __name__ == "__main__":
    main()
