"""
Integration example showing how OutputManager works with other components
in the fix-owner script to provide comprehensive output control.
"""

import os
import time
from output_manager import OutputManager
from timeout_manager import TimeoutManager


class MockSecurityManager:
    """Mock SecurityManager for demonstration purposes."""
    
    def __init__(self, output_manager: OutputManager):
        self.output = output_manager
    
    def get_current_owner(self, path: str):
        """Mock method to get current owner."""
        # Simulate some paths having invalid SIDs
        if "invalid" in path.lower():
            return None, "S-1-5-21-invalid-sid"
        return "DOMAIN\\ValidUser", "S-1-5-21-valid-sid"
    
    def is_sid_valid(self, sid: str) -> bool:
        """Mock method to check SID validity."""
        return "invalid" not in sid
    
    def set_owner(self, path: str, owner_sid: str) -> bool:
        """Mock method to set owner."""
        # Simulate occasional failures
        if "error" in path.lower():
            raise Exception("Access denied")
        return True


class MockStatsTracker:
    """Mock StatsTracker for demonstration purposes."""
    
    def __init__(self):
        self.dirs_traversed = 0
        self.files_traversed = 0
        self.dirs_changed = 0
        self.files_changed = 0
        self.exceptions = 0
        self.start_time = time.time()
    
    def increment_dirs_traversed(self):
        self.dirs_traversed += 1
    
    def increment_files_traversed(self):
        self.files_traversed += 1
    
    def increment_dirs_changed(self):
        self.dirs_changed += 1
    
    def increment_files_changed(self):
        self.files_changed += 1
    
    def increment_exceptions(self):
        self.exceptions += 1
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time


def simulate_file_processing(root_path: str, options: dict, 
                           security_manager: MockSecurityManager,
                           stats_tracker: MockStatsTracker,
                           output_manager: OutputManager,
                           timeout_manager: TimeoutManager):
    """
    Simulate file processing with proper output control integration.
    
    This demonstrates how OutputManager integrates with all components
    to provide consistent output behavior throughout the application.
    """
    
    # Print startup information
    output_manager.print_startup_info(
        root_path=root_path,
        owner_account=options.get('owner_account', 'DOMAIN\\Administrator'),
        recurse=options.get('recurse', False),
        include_files=options.get('files', False)
    )
    
    # Print execution mode notice
    if options.get('execute', False):
        output_manager.print_execution_mode_notice()
    else:
        output_manager.print_dry_run_notice()
    
    # Simulate directory structure
    test_paths = [
        ("/test/root", True),
        ("/test/root/subdir1", True),
        ("/test/root/subdir1/file1.txt", False),
        ("/test/root/subdir2_invalid", True),  # Has invalid SID
        ("/test/root/subdir2_invalid/file2.txt", False),
        ("/test/root/error_dir", True),  # Will cause error
        ("/test/root/normal_file.txt", False),
    ]
    
    for path, is_directory in test_paths:
        # Check timeout
        if not timeout_manager.should_continue_processing():
            output_manager.print_timeout_warning(
                timeout_manager.get_elapsed_time(),
                timeout_manager.timeout_seconds
            )
            break
        
        # Print examination message (only in verbose mode)
        output_manager.print_examining_path(path, is_directory)
        
        # Update statistics
        if is_directory:
            stats_tracker.increment_dirs_traversed()
        else:
            stats_tracker.increment_files_traversed()
        
        try:
            # Check current owner
            owner_name, owner_sid = security_manager.get_current_owner(path)
            
            # Check if SID is valid
            if not security_manager.is_sid_valid(owner_sid):
                # Need to change ownership
                if options.get('execute', False):
                    security_manager.set_owner(path, "S-1-5-21-new-owner-sid")
                
                # Print ownership change message (only in verbose mode)
                output_manager.print_ownership_change(
                    path, is_directory, dry_run=not options.get('execute', False)
                )
                
                # Update change statistics
                if is_directory:
                    stats_tracker.increment_dirs_changed()
                else:
                    stats_tracker.increment_files_changed()
        
        except Exception as e:
            # Handle and report error
            stats_tracker.increment_exceptions()
            output_manager.print_error(path, e, is_directory)
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Skip files if not processing files
        if not is_directory and not options.get('files', False):
            continue
        
        # Skip subdirectories if not recursing
        if is_directory and "subdir" in path and not options.get('recurse', False):
            break
    
    # Print completion message
    output_manager.print_completion_message()


def demonstrate_output_modes():
    """Demonstrate different output modes with the same processing."""
    
    print("=" * 60)
    print("DEMONSTRATION: OutputManager Integration")
    print("=" * 60)
    
    # Common options for all demonstrations
    base_options = {
        'execute': False,  # Dry run
        'recurse': True,
        'files': True,
        'owner_account': 'DOMAIN\\Administrator'
    }
    
    # Test scenarios
    scenarios = [
        ("QUIET MODE", {'verbose': False, 'quiet': True}),
        ("NORMAL MODE", {'verbose': False, 'quiet': False}),
        ("VERBOSE MODE", {'verbose': True, 'quiet': False}),
    ]
    
    for scenario_name, output_options in scenarios:
        print(f"\n{'-' * 20} {scenario_name} {'-' * 20}")
        
        # Create components with appropriate output settings
        output_manager = OutputManager(**output_options)
        security_manager = MockSecurityManager(output_manager)
        stats_tracker = MockStatsTracker()
        timeout_manager = TimeoutManager(timeout_seconds=0)  # No timeout
        
        # Combine options
        options = {**base_options, **output_options}
        
        # Run simulation
        simulate_file_processing(
            root_path="/test/root",
            options=options,
            security_manager=security_manager,
            stats_tracker=stats_tracker,
            output_manager=output_manager,
            timeout_manager=timeout_manager
        )
        
        # Print final statistics using StatsReporter
        stats_reporter = output_manager.create_stats_reporter()
        stats_reporter.print_full_report(
            dirs_traversed=stats_tracker.dirs_traversed,
            files_traversed=stats_tracker.files_traversed,
            dirs_changed=stats_tracker.dirs_changed,
            files_changed=stats_tracker.files_changed,
            exceptions=stats_tracker.exceptions,
            duration_seconds=stats_tracker.get_elapsed_time()
        )
        
        print()  # Add spacing between scenarios


def demonstrate_timeout_integration():
    """Demonstrate timeout integration with output control."""
    
    print("=" * 60)
    print("DEMONSTRATION: Timeout Integration with Output Control")
    print("=" * 60)
    
    # Create components with verbose output
    output_manager = OutputManager(verbose=True, quiet=False)
    security_manager = MockSecurityManager(output_manager)
    stats_tracker = MockStatsTracker()
    timeout_manager = TimeoutManager(timeout_seconds=1)  # 1 second timeout
    
    options = {
        'execute': True,
        'recurse': True,
        'files': True,
        'verbose': True,
        'quiet': False,
        'owner_account': 'DOMAIN\\Administrator'
    }
    
    print("\nRunning with 1-second timeout...")
    
    # Run simulation with timeout
    simulate_file_processing(
        root_path="/test/root",
        options=options,
        security_manager=security_manager,
        stats_tracker=stats_tracker,
        output_manager=output_manager,
        timeout_manager=timeout_manager
    )
    
    # Print final statistics
    stats_reporter = output_manager.create_stats_reporter()
    stats_reporter.print_full_report(
        dirs_traversed=stats_tracker.dirs_traversed,
        files_traversed=stats_tracker.files_traversed,
        dirs_changed=stats_tracker.dirs_changed,
        files_changed=stats_tracker.files_changed,
        exceptions=stats_tracker.exceptions,
        duration_seconds=stats_tracker.get_elapsed_time()
    )


def demonstrate_error_handling():
    """Demonstrate error handling with output control."""
    
    print("=" * 60)
    print("DEMONSTRATION: Error Handling with Output Control")
    print("=" * 60)
    
    # Test critical error handling
    output_manager = OutputManager(verbose=False, quiet=False)
    
    print("\nTesting critical error handling...")
    output_manager.print_invalid_owner_error("InvalidUser", Exception("User not found"))
    output_manager.print_privilege_warning()
    
    print("\nTesting critical error in quiet mode...")
    quiet_output_manager = OutputManager(verbose=False, quiet=True)
    quiet_output_manager.print_invalid_owner_error("InvalidUser", Exception("User not found"))
    # Note: Critical errors still show even in quiet mode


if __name__ == "__main__":
    demonstrate_output_modes()
    demonstrate_timeout_integration()
    demonstrate_error_handling()
    
    print("\n" + "=" * 60)
    print("Integration demonstration completed successfully!")
    print("=" * 60)