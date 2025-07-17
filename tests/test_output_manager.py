"""
Test script for OutputManager functionality.
"""

import io
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.output_manager import OutputManager, OutputLevel, StatsReporter


def test_quiet_mode():
    """Test that quiet mode suppresses all output."""
    print("Testing quiet mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    # Create quiet output manager
    output_mgr = OutputManager(quiet=True, output_stream=output_buffer, error_stream=error_buffer)
    
    # Try various output methods
    output_mgr.print_examining_path("/test/path", True)
    output_mgr.print_ownership_change("/test/path", True, False)
    output_mgr.print_statistics_header()
    output_mgr.print_statistic("Test stat", 42)
    output_mgr.print_duration_statistic(10.5)
    output_mgr.print_general_message("General message")
    
    # Check that nothing was written to output
    output_content = output_buffer.getvalue()
    assert output_content == "", f"Expected no output in quiet mode, got: '{output_content}'"
    
    # Critical errors should still be written to error stream
    output_mgr.print_invalid_owner_error("baduser", Exception("test error"))
    error_content = error_buffer.getvalue()
    assert "Invalid owner account" in error_content, "Critical errors should still be shown in quiet mode"
    
    print("✓ Quiet mode test passed")


def test_verbose_mode():
    """Test that verbose mode shows detailed output."""
    print("Testing verbose mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    # Create verbose output manager
    output_mgr = OutputManager(verbose=True, output_stream=output_buffer, error_stream=error_buffer)
    
    # Test verbose output methods
    output_mgr.print_examining_path("/test/dir", True)
    output_mgr.print_examining_path("/test/file.txt", False)
    output_mgr.print_ownership_change("/test/dir", True, False)
    output_mgr.print_ownership_change("/test/file.txt", False, True)
    output_mgr.print_error("/test/path", Exception("test error"), True)
    
    # Check output content
    output_content = output_buffer.getvalue()
    assert "Examining directory: /test/dir" in output_content
    assert "Examining file: /test/file.txt" in output_content
    assert "Changed owner for directory: /test/dir" in output_content
    assert "Would change owner for file: /test/file.txt" in output_content
    
    error_content = error_buffer.getvalue()
    assert "Error processing directory /test/path: test error" in error_content
    
    print("✓ Verbose mode test passed")


def test_normal_mode():
    """Test that normal mode shows statistics but not detailed output."""
    print("Testing normal mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    # Create normal output manager
    output_mgr = OutputManager(verbose=False, quiet=False, output_stream=output_buffer, error_stream=error_buffer)
    
    # Test that verbose methods don't produce output
    output_mgr.print_examining_path("/test/path", True)
    output_mgr.print_ownership_change("/test/path", True, False)
    output_mgr.print_error("/test/path", Exception("test error"), True)
    
    # Test that statistics methods do produce output
    output_mgr.print_statistics_header()
    output_mgr.print_statistic("Test stat", 42)
    output_mgr.print_duration_statistic(10.5)
    
    output_content = output_buffer.getvalue()
    
    # Should not contain verbose messages
    assert "Examining" not in output_content
    assert "Changed owner" not in output_content
    
    # Should contain statistics
    assert "--- Ownership Change Statistics ---" in output_content
    assert "Test stat: 42" in output_content
    assert "Total duration: 10.5 seconds" in output_content
    
    print("✓ Normal mode test passed")


def test_stats_reporter():
    """Test StatsReporter functionality."""
    print("Testing StatsReporter...")
    
    # Capture output
    output_buffer = io.StringIO()
    
    # Create output manager and stats reporter
    output_mgr = OutputManager(verbose=False, quiet=False, output_stream=output_buffer)
    stats_reporter = output_mgr.create_stats_reporter()
    
    # Test full report
    stats_reporter.print_full_report(
        dirs_traversed=100,
        files_traversed=500,
        dirs_changed=10,
        files_changed=25,
        exceptions=2,
        duration_seconds=45.7
    )
    
    output_content = output_buffer.getvalue()
    
    # Check all statistics are present
    assert "--- Ownership Change Statistics ---" in output_content
    assert "Directories traversed: 100" in output_content
    assert "Files traversed: 500" in output_content
    assert "Directory ownerships changed: 10" in output_content
    assert "File ownerships changed: 25" in output_content
    assert "Exceptions encountered: 2" in output_content
    assert "Total duration: 45.7 seconds" in output_content
    
    print("✓ StatsReporter test passed")


def test_quiet_stats_reporter():
    """Test that StatsReporter respects quiet mode."""
    print("Testing StatsReporter in quiet mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    
    # Create quiet output manager and stats reporter
    output_mgr = OutputManager(quiet=True, output_stream=output_buffer)
    stats_reporter = output_mgr.create_stats_reporter()
    
    # Test full report in quiet mode
    stats_reporter.print_full_report(
        dirs_traversed=100,
        files_traversed=500,
        dirs_changed=10,
        files_changed=25,
        exceptions=2,
        duration_seconds=45.7
    )
    
    output_content = output_buffer.getvalue()
    
    # Should be empty in quiet mode
    assert output_content == "", f"Expected no output in quiet mode, got: '{output_content}'"
    
    print("✓ Quiet StatsReporter test passed")


def main():
    """Run all tests."""
    print("Running OutputManager tests...\n")
    
    try:
        test_quiet_mode()
        test_verbose_mode()
        test_normal_mode()
        test_stats_reporter()
        test_quiet_stats_reporter()
        
        print("\n✅ All OutputManager tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()