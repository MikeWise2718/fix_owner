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
    output_mgr = OutputManager(verbose_level=0, quiet=True, output_stream=output_buffer, error_stream=error_buffer)
    
    # Try various output methods
    output_mgr.print_examining_path("/test/path", True, "DOMAIN\\User", True)
    output_mgr.print_ownership_change("/test/path", True, False, "Administrator")
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
    
    # Create verbose output manager (level 3 for detailed examination)
    output_mgr = OutputManager(verbose_level=3, output_stream=output_buffer, error_stream=error_buffer)
    
    # Test verbose output methods (level 3 shows detailed examination)
    output_mgr.print_examining_path("/test/dir", True, "DOMAIN\\User", True)
    output_mgr.print_examining_path("/test/file.txt", False, "ORPHANED_SID", False)
    output_mgr.print_ownership_change("/test/dir", True, False, "Administrator")
    output_mgr.print_ownership_change("/test/file.txt", False, True, "Administrator")
    output_mgr.print_error("/test/path", Exception("test error"), True)
    
    # Check output content (level 3 shows detailed file/directory examination)
    output_content = output_buffer.getvalue()
    # Remove ANSI color codes for easier testing
    import re
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output_content)
    
    assert "DIR  /test/dir" in clean_output
    assert "FILE /test/file.txt" in clean_output
    assert "VALID" in clean_output
    assert "ORPHANED" in clean_output
    assert "CHANGED" in clean_output or "WOULD CHANGE" in clean_output
    
    error_content = error_buffer.getvalue()
    assert "ERROR processing directory" in error_content and "/test/path" in error_content
    
    print("✓ Verbose mode test passed")


def test_normal_mode():
    """Test that normal mode shows statistics but not detailed output."""
    print("Testing normal mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    # Create normal output manager (level 0 - statistics only)
    output_mgr = OutputManager(verbose_level=0, quiet=False, output_stream=output_buffer, error_stream=error_buffer)
    
    # Test that verbose methods don't produce output (level 0 only shows statistics)
    output_mgr.print_examining_path("/test/path", True, "DOMAIN\\User", True)
    output_mgr.print_ownership_change("/test/path", True, False, "Administrator")
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
    # Remove ANSI color codes for easier testing
    import re
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output_content)
    assert "Test stat: 42" in clean_output
    assert "Total duration: 10.5 seconds" in clean_output
    
    print("✓ Normal mode test passed")


def test_stats_reporter():
    """Test StatsReporter functionality."""
    print("Testing StatsReporter...")
    
    # Capture output
    output_buffer = io.StringIO()
    
    # Create output manager and stats reporter
    output_mgr = OutputManager(verbose_level=0, quiet=False, output_stream=output_buffer)
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
    # Remove ANSI color codes for easier testing
    import re
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output_content)
    assert "Directories traversed: 100" in clean_output
    assert "Files traversed: 500" in clean_output
    assert "Directory ownerships changed: 10" in clean_output
    assert "File ownerships changed: 25" in clean_output
    assert "Exceptions encountered: 2" in clean_output
    assert "Total duration: 45.7 seconds" in clean_output
    
    print("✓ StatsReporter test passed")


def test_quiet_stats_reporter():
    """Test that StatsReporter respects quiet mode."""
    print("Testing StatsReporter in quiet mode...")
    
    # Capture output
    output_buffer = io.StringIO()
    
    # Create quiet output manager and stats reporter
    output_mgr = OutputManager(verbose_level=0, quiet=True, output_stream=output_buffer)
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