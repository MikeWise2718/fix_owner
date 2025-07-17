"""
Example demonstrating TimeoutManager integration into main processing loop.
This shows how the TimeoutManager would be used in the fix-owner script.
"""

import time
import sys
import os

# Add current directory to path to import timeout_manager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from timeout_manager import TimeoutManager


def simulate_file_processing(path: str, timeout_manager: TimeoutManager, verbose: bool = False):
    """
    Simulate processing a file/directory with timeout checking.
    
    Args:
        path: Path being processed
        timeout_manager: TimeoutManager instance
        verbose: Whether to show verbose output
    """
    if verbose:
        print(f"Processing: {path}")
    
    # Simulate some work
    time.sleep(0.1)
    
    # Check if we should continue processing
    if not timeout_manager.should_continue_processing():
        if verbose:
            print(f"Timeout reached while processing: {path}")
        return False
    
    return True


def simulate_directory_walk(root_path: str, timeout_seconds: int, verbose: bool = False):
    """
    Simulate directory walking with timeout management.
    
    Args:
        root_path: Root directory to process
        timeout_seconds: Timeout in seconds
        verbose: Whether to show verbose output
    """
    print(f"Starting directory walk with {timeout_seconds}s timeout...")
    
    # Create timeout manager
    with TimeoutManager(timeout_seconds) as timeout_manager:
        
        # Setup timeout handler for graceful termination
        def timeout_callback():
            print("\n⏰ Timeout reached - stopping processing gracefully")
        
        timeout_manager.setup_timeout_handler(timeout_callback)
        
        # Simulate processing multiple files/directories
        test_paths = [
            f"{root_path}\\dir1",
            f"{root_path}\\dir1\\file1.txt",
            f"{root_path}\\dir1\\file2.txt",
            f"{root_path}\\dir2",
            f"{root_path}\\dir2\\subdir1",
            f"{root_path}\\dir2\\subdir1\\file3.txt",
            f"{root_path}\\dir3",
            f"{root_path}\\dir3\\file4.txt",
        ]
        
        processed_count = 0
        
        for path in test_paths:
            # Main processing loop integration point
            if not timeout_manager.should_continue_processing():
                print(f"Stopping due to timeout after processing {processed_count} items")
                break
            
            if simulate_file_processing(path, timeout_manager, verbose):
                processed_count += 1
            else:
                print(f"Processing interrupted by timeout after {processed_count} items")
                break
        
        elapsed = timeout_manager.get_elapsed_time()
        remaining = timeout_manager.get_remaining_time()
        
        print(f"\nProcessing completed:")
        print(f"  Items processed: {processed_count}")
        print(f"  Elapsed time: {elapsed:.2f}s")
        print(f"  Remaining time: {remaining:.2f}s" if remaining != float('inf') else "  No timeout set")
        print(f"  Timeout reached: {'Yes' if timeout_manager.is_timeout_reached() else 'No'}")


def main():
    """Demonstrate timeout integration scenarios."""
    print("TimeoutManager Integration Examples\n")
    
    # Example 1: No timeout
    print("=" * 50)
    print("Example 1: No timeout (should process all items)")
    simulate_directory_walk("C:\\test", 0, verbose=True)
    
    print("\n" + "=" * 50)
    print("Example 2: Short timeout (should timeout during processing)")
    simulate_directory_walk("C:\\test", 1, verbose=True)
    
    print("\n" + "=" * 50)
    print("Example 3: Long timeout (should complete normally)")
    simulate_directory_walk("C:\\test", 5, verbose=True)


if __name__ == "__main__":
    main()