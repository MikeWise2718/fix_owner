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
        owner_account   Target owner account (default: current user)
    
    Options:
        -x, --execute   Apply ownership changes (default: dry run)
        -r, --recurse   Recurse into subdirectories
        -f, --files     Process files in addition to directories
        -v, --verbose   Show detailed processing information
        -q, --quiet     Suppress all output including statistics
        -ts SECONDS     Timeout after specified seconds (0 = no timeout)

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
    
    # Use current user as target owner (no account specified)
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

# Module-level constants and configuration
SCRIPT_VERSION = "1.0.0"
REQUIRED_PYTHON_VERSION = (3, 13)
DEFAULT_TIMEOUT_SECONDS = 0  # No timeout by default
MAX_PATH_LENGTH = 260  # Windows MAX_PATH limitation
CHUNK_SIZE = 1000  # Process items in chunks for memory efficiency

# Exit codes
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_INTERRUPTED = 2

# Windows security imports
try:
    import win32security
    import win32api
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    print("Error: pywin32 module is required. Install with: pip install pywin32")
    sys.exit(EXIT_ERROR)

# Import our custom components
try:
    # Try relative imports first (when imported as a module)
    from .timeout_manager import TimeoutManager
    from .output_manager import OutputManager
    from .filesystem_walker import FileSystemWalker
    from .error_manager import ErrorManager, ErrorCategory
except ImportError:
    # Fall back to absolute imports (when run as a script)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from timeout_manager import TimeoutManager
    from output_manager import OutputManager
    from filesystem_walker import FileSystemWalker
    from error_manager import ErrorManager, ErrorCategory


class SecurityManager:
    """
    Manages Windows security operations for file/directory ownership.
    
    This class encapsulates all Windows security API interactions including
    SID validation, ownership retrieval, and ownership changes.
    """
    
    def __init__(self, error_manager: Optional[ErrorManager] = None):
        """
        Initialize the SecurityManager.
        
        Args:
            error_manager: Optional ErrorManager for comprehensive error handling
        """
        if not PYWIN32_AVAILABLE:
            raise ImportError("pywin32 module is required for security operations")
        self.error_manager = error_manager
    
    def get_current_owner(self, path: str) -> tuple[Optional[str], object]:
        """
        Get current owner of a file or directory using Windows Security APIs.
        
        This method performs a two-step process:
        1. Retrieves the security descriptor and extracts the owner SID
        2. Attempts to resolve the SID to a human-readable account name
        
        Args:
            path: Path to examine
            
        Returns:
            Tuple of (owner_name, owner_sid). owner_name is None if SID is invalid/orphaned.
            
        Raises:
            Exception: If unable to get security information
        """
        try:
            # Step 1: Get the security descriptor for the file/directory
            # OWNER_SECURITY_INFORMATION flag requests only owner information for efficiency
            sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
            
            # Extract the owner SID from the security descriptor
            # This SID uniquely identifies the owner account
            owner_sid = sd.GetSecurityDescriptorOwner()
            
            try:
                # Step 2: Attempt to resolve SID to account name
                # LookupAccountSid converts SID to human-readable name and domain
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                
                # Format as DOMAIN\USERNAME or just USERNAME if no domain
                owner_name = f"{domain}\\{name}" if domain else name
                return owner_name, owner_sid
                
            except Exception:
                # SID resolution failed - this indicates an orphaned/invalid SID
                # The SID exists but doesn't correspond to any current account
                # This is exactly what we want to detect and fix
                return None, owner_sid
                
        except Exception as e:
            # Handle errors in getting security information
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, path=path, context="Getting current owner"
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to get owner information for '{path}': {e}")
    
    def is_sid_valid(self, sid: object) -> bool:
        """
        Check if a SID corresponds to a valid account using Windows Security APIs.
        
        This method attempts to resolve a SID to an account name. If the resolution
        succeeds, the SID is valid. If it fails, the SID is orphaned/invalid.
        
        Args:
            sid: SID object to validate
            
        Returns:
            True if SID corresponds to an existing account, False if orphaned/invalid
        """
        try:
            # Attempt to resolve SID to account name
            # If this succeeds, the SID is valid and corresponds to an existing account
            win32security.LookupAccountSid(None, sid)
            return True
        except Exception:
            # LookupAccountSid failed - SID is orphaned/invalid
            # This is the condition we're looking for to identify ownership that needs fixing
            return False
    
    def set_owner(self, path: str, owner_sid: object) -> bool:
        """
        Set ownership of a file or directory using Windows Security APIs.
        
        This method performs a three-step process to change ownership:
        1. Retrieves the current security descriptor
        2. Modifies the owner SID in the security descriptor
        3. Applies the modified security descriptor back to the file/directory
        
        Args:
            path: Path to change ownership
            owner_sid: SID of new owner account
            
        Returns:
            True if ownership was successfully changed
            
        Raises:
            Exception: If unable to set ownership due to permissions or other errors
        """
        try:
            # Step 1: Get current security descriptor
            # We need the existing descriptor to modify only the owner portion
            sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
            
            # Step 2: Set the new owner SID in the security descriptor
            # The second parameter (False) indicates we're not setting a group owner
            sd.SetSecurityDescriptorOwner(owner_sid, False)
            
            # Step 3: Apply the modified security descriptor back to the file/directory
            # This is where the actual ownership change occurs
            win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
            
            return True
            
        except Exception as e:
            # Handle ownership change errors through ErrorManager if available
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, path=path, context="Setting ownership"
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to set owner for '{path}': {e}")
    
    def resolve_owner_account(self, account_name: Optional[str]) -> tuple[object, str]:
        """
        Convert account name to SID using Windows Security APIs.
        
        This method resolves either a specified account name or the current user
        to a Security Identifier (SID) that can be used for ownership operations.
        It handles both local and domain accounts properly.
        
        Args:
            account_name: Account name to resolve (e.g., "Administrator", "DOMAIN\\User"), 
                         or None to use current user
            
        Returns:
            Tuple of (SID object, resolved account name with domain)
            
        Raises:
            Exception: If account cannot be resolved or doesn't exist
        """
        try:
            if account_name:
                # Use specified account name
                # LookupAccountName resolves the name to SID and provides domain info
                sid, domain, account_type = win32security.LookupAccountName(None, account_name)
                
                # Format the resolved name with domain for clarity
                resolved_name = f"{domain}\\{account_name}" if domain else account_name
                
                # Log the account type for debugging (User, Group, Domain, etc.)
                if self.error_manager and hasattr(self.error_manager, 'output_manager'):
                    output = self.error_manager.output_manager
                    if output and output.is_verbose():
                        account_types = {
                            1: "User", 2: "Group", 3: "Domain", 4: "Alias", 
                            5: "WellKnownGroup", 6: "DeletedAccount", 7: "Invalid", 8: "Unknown"
                        }
                        type_name = account_types.get(account_type, f"Type{account_type}")
                        output.print_general_message(f"Resolved account type: {type_name}")
                        
            else:
                # Use current user - get the full username with domain
                current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
                sid, domain, account_type = win32security.LookupAccountName(None, current_user)
                resolved_name = current_user
                
            return sid, resolved_name
            
        except Exception as e:
            # Handle account resolution errors
            account_display = account_name or "current user"
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, context=f"Resolving account '{account_display}'", critical=True
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to resolve account '{account_display}': {e}")


@dataclass
class ExecutionOptions:
    """Configuration options for script execution."""
    execute: bool = False          # -x flag: Apply changes vs dry run
    recurse: bool = False          # -r flag: Recurse into subdirectories
    files: bool = False            # -f flag: Process files in addition to directories
    verbose: bool = False          # -v flag: Verbose output
    quiet: bool = False            # -q flag: Suppress all output
    timeout: int = 0               # -ts value: Timeout in seconds
    root_path: str = ""            # Positional argument: Root path to process
    owner_account: str = ""        # Target owner account


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


class StatsTracker:
    """
    Tracks and reports execution statistics for the fix-owner script.
    
    This class provides counters for directories, files, changes, and exceptions,
    along with methods to increment each counter and generate formatted reports.
    """
    
    def __init__(self):
        """Initialize the StatsTracker with zero counters."""
        self.dirs_traversed = 0
        self.files_traversed = 0
        self.dirs_changed = 0
        self.files_changed = 0
        self.exceptions = 0
        self.start_time = time.time()
    
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
            Elapsed time in seconds as a float
        """
        return time.time() - self.start_time
    
    def print_report(self, quiet: bool = False) -> None:
        """
        Print a formatted statistics report.
        
        Args:
            quiet: If True, suppress all output including statistics
        """
        if quiet:
            return
        
        elapsed_time = self.get_elapsed_time()
        
        print("\n" + "=" * 50)
        print("EXECUTION STATISTICS")
        print("=" * 50)
        print(f"Directories traversed: {self.dirs_traversed:,}")
        print(f"Files traversed: {self.files_traversed:,}")
        print(f"Directory ownerships changed: {self.dirs_changed:,}")
        print(f"File ownerships changed: {self.files_changed:,}")
        print(f"Exceptions encountered: {self.exceptions:,}")
        print(f"Total execution time: {elapsed_time:.2f} seconds")
        print("=" * 50)


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
        epilog="Example: python fix_owner.py C:\\MyFolder -x -r -v Administrator"
    )
    
    # Positional arguments
    parser.add_argument(
        'root_path',
        help='Root directory path to start processing from'
    )
    parser.add_argument(
        'owner_account',
        nargs='?',
        help='Target owner account (default: current user)'
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
        action='store_true',
        help='Verbose output showing each path examined'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output including statistics'
    )
    parser.add_argument(
        '-ts', '--timeout',
        type=int,
        default=0,
        metavar='SECONDS',
        help='Terminate execution after specified seconds (0 = no timeout)'
    )
    
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.verbose and args.quiet:
        parser.error("Cannot specify both --verbose and --quiet options")
    
    if args.timeout < 0:
        parser.error("Timeout value must be non-negative")
    
    if not os.path.exists(args.root_path):
        parser.error(f"Root path does not exist: {args.root_path}")
    
    if not os.path.isdir(args.root_path):
        parser.error(f"Root path is not a directory: {args.root_path}")
    
    return args


def resolve_owner_account(account_name: Optional[str], output: OutputManager, security_manager: SecurityManager) -> object:
    """
    Resolve owner account name to SID using SecurityManager with comprehensive error handling.
    
    This function validates that the target owner account exists and can be used
    for ownership operations. It provides clear error messages if the account
    cannot be resolved, which is critical for preventing runtime failures.
    
    Args:
        account_name: Account name to resolve (e.g., "Administrator", "DOMAIN\\User"), 
                     or None for current user
        output: Output manager for user feedback and error reporting
        security_manager: SecurityManager instance for account resolution
        
    Returns:
        SID object for the resolved account that can be used in ownership operations
        
    Raises:
        SystemExit: If account cannot be resolved (critical error that prevents execution)
    """
    try:
        # Attempt to resolve the account name to a SID
        # This validates that the account exists and is accessible
        sid, resolved_name = security_manager.resolve_owner_account(account_name)
        
        # Inform user of the resolved account name (includes domain if applicable)
        output.print_general_message(f"Target owner account: {resolved_name}")
        
        # Log additional account information in verbose mode
        if output.is_verbose():
            output.print_general_message(f"Account resolution successful for: {account_name or 'current user'}")
        
        return sid
        
    except Exception as e:
        # Handle account resolution failure - this is a critical error
        account_display = account_name or "current user"
        
        # Provide detailed error information to help user resolve the issue
        output.print_invalid_owner_error(account_display, e)
        output.print_general_error("Failed to resolve target owner account")
        
        # Suggest common solutions in verbose mode
        if output.is_verbose():
            output.print_general_message("Common solutions:")
            output.print_general_message("- Verify the account name is spelled correctly")
            output.print_general_message("- For domain accounts, use DOMAIN\\Username format")
            output.print_general_message("- Ensure the account exists and is not disabled")
            output.print_general_message("- Check that you have permission to query the account")
        
        # Exit with error code since we cannot proceed without a valid target account
        sys.exit(EXIT_ERROR)



def process_filesystem(options: ExecutionOptions, owner_sid: object, 
                      stats: StatsTracker, output: OutputManager,
                      timeout_manager: TimeoutManager, security_manager: SecurityManager,
                      error_manager: ErrorManager) -> None:
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
    walker = FileSystemWalker(security_manager, stats, error_manager)
    
    # Log the start of filesystem processing in verbose mode
    if output.is_verbose():
        mode = "EXECUTE" if options.execute else "DRY RUN"
        output.print_general_message(f"Starting filesystem processing in {mode} mode")
        output.print_general_message(f"Processing {'files and directories' if options.files else 'directories only'}")
        output.print_general_message(f"Recursion: {'enabled' if options.recurse else 'disabled'}")
        if options.timeout > 0:
            output.print_general_message(f"Timeout: {options.timeout} seconds")
    
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
            root_path=args.root_path,      # Starting directory for processing
            owner_account=args.owner_account or ""  # Target owner account
        )
        
        # PHASE 2: Component initialization and dependency injection
        # Initialize statistics tracking to monitor performance and operations
        stats = StatsTracker()
        
        # Initialize output manager with user's verbosity preferences
        # This centralizes all output formatting and stream management
        output = OutputManager(
            verbose=options.verbose,
            quiet=options.quiet
        )
        
        # Initialize comprehensive error manager with dependencies
        # This provides centralized error handling, categorization, and recovery
        error_manager = ErrorManager(stats_tracker=stats, output_manager=output)
        
        # Initialize security manager with error handling integration
        # This handles all Windows security API operations with proper error handling
        security_manager = SecurityManager(error_manager=error_manager)
        
        # PHASE 3: Security validation and privilege checking
        # Validate that we have Administrator privileges required for ownership changes
        # This prevents runtime failures and provides clear error messages
        if not error_manager.validate_administrator_privileges():
            # Continue with warning - some operations may still work
            output.print_general_message("Warning: Limited functionality without Administrator privileges")
        
        # PHASE 4: Execution mode notification and user feedback
        # Clearly indicate whether this is a dry run or will make actual changes
        # This prevents accidental modifications and sets user expectations
        if options.execute:
            output.print_execution_mode_notice()
            if output.is_verbose():
                output.print_general_message("Changes will be applied to filesystem")
        else:
            output.print_dry_run_notice()
            if output.is_verbose():
                output.print_general_message("No changes will be made - this is a simulation")
        
        # PHASE 5: Target owner account resolution and validation
        # Resolve the target owner account to a SID and validate it exists
        # This is critical - we cannot proceed without a valid target account
        owner_sid = resolve_owner_account(options.owner_account, output, security_manager)
        
        # PHASE 6: Operation startup information and logging
        # Provide user with comprehensive information about what will be processed
        output.print_startup_info(
            options.root_path,
            options.owner_account or "current user",
            options.recurse,
            options.files
        )
        
        # Log additional configuration details in verbose mode
        if output.is_verbose():
            output.print_general_message(f"Python version: {sys.version}")
            output.print_general_message(f"Script version: {SCRIPT_VERSION}")
            output.print_general_message(f"Maximum path length: {MAX_PATH_LENGTH}")
            if options.timeout > 0:
                output.print_general_message(f"Execution will timeout after {options.timeout} seconds")
        
        # PHASE 7: Timeout configuration and setup
        # Initialize timeout manager for handling execution time limits
        timeout_manager = TimeoutManager(options.timeout)
        
        # Setup timeout handler if a timeout was specified
        # This ensures graceful termination for long-running operations
        if options.timeout > 0:
            timeout_manager.setup_timeout_handler()
            if output.is_verbose():
                output.print_general_message("Timeout handler configured")
        
        try:
            # PHASE 8: Main filesystem processing
            # This is where the actual work happens - traverse directories and fix ownership
            # All error handling and recovery is managed by the individual components
            if output.is_verbose():
                output.print_general_message("Beginning filesystem processing...")
            
            process_filesystem(options, owner_sid, stats, output, timeout_manager, security_manager, error_manager)
            
        finally:
            # PHASE 9: Cleanup and resource management
            # Always cleanup timeout resources, even if processing was interrupted
            timeout_manager.cancel_timeout()
            if output.is_verbose():
                output.print_general_message("Timeout handler cleaned up")
        
        # PHASE 10: Completion notification and final reporting
        # Notify user of successful completion
        output.print_completion_message()
        
        # Generate and display final statistics report
        # This provides comprehensive information about what was processed
        stats.print_report(quiet=options.quiet)
        
        # Log successful completion in verbose mode
        if output.is_verbose():
            output.print_general_message("Script execution completed successfully")
        
    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C) gracefully
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(EXIT_INTERRUPTED)
    except Exception as e:
        # Handle any unexpected critical errors
        print(f"Critical error: {e}", file=sys.stderr)
        
        # In verbose mode, provide additional debugging information
        if 'output' in locals() and output.is_verbose():
            import traceback
            print("Stack trace:", file=sys.stderr)
            traceback.print_exc()
        
        sys.exit(EXIT_ERROR)


if __name__ == "__main__":
    main()
