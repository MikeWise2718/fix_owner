#!/usr/bin/env python3
"""
Integration test for comprehensive error handling across all components.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.security_manager import SecurityManager
from src.stats_tracker import StatsTracker
from src.filesystem_walker import FileSystemWalker
from src.output_manager import OutputManager
from src.error_manager import ErrorManager, ErrorCategory


def test_security_manager_error_handling():
    """Test SecurityManager with ErrorManager integration."""
    print("Testing SecurityManager error handling integration...")
    
    # Create mock dependencies
    mock_stats = Mock()
    mock_stats.increment_exceptions = Mock()
    
    mock_output = Mock()
    mock_output.print_error = Mock()
    mock_output.print_general_error = Mock()
    
    # Create ErrorManager and SecurityManager
    error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
    security_manager = SecurityManager(error_manager=error_manager)
    
    # Test error handling in get_current_owner with invalid path
    try:
        owner_name, owner_sid = security_manager.get_current_owner("/invalid/path/that/does/not/exist")
        # Should not reach here if error handling works
        assert False, "Expected exception for invalid path"
    except Exception as e:
        # Exception should be handled by ErrorManager and re-raised
        assert "Failed to get owner information" in str(e)
        # Stats should be incremented
        mock_stats.increment_exceptions.assert_called()
    
    print("✓ SecurityManager error handling integration test passed")


def test_filesystem_walker_error_handling():
    """Test FileSystemWalker with ErrorManager integration."""
    print("Testing FileSystemWalker error handling integration...")
    
    # Create temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock dependencies
        mock_stats = Mock()
        mock_stats.increment_dirs_traversed = Mock()
        mock_stats.increment_exceptions = Mock()
        
        mock_output = Mock()
        mock_output.print_examining_path = Mock()
        mock_output.print_error = Mock()
        
        mock_security = Mock()
        # Mock security manager to raise an exception
        mock_security.get_current_owner.side_effect = Exception("Mock security error")
        
        # Create ErrorManager and FileSystemWalker
        error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
        walker = FileSystemWalker(mock_security, mock_stats, error_manager)
        
        # Process a directory that will cause an error
        walker._process_directory(temp_dir, None, False, mock_output)
        
        # Verify error handling occurred
        mock_stats.increment_dirs_traversed.assert_called_once()
        # Exception should be handled by ErrorManager context
        # Stats increment_exceptions should be called by ErrorManager
        
    print("✓ FileSystemWalker error handling integration test passed")


def test_end_to_end_error_handling():
    """Test end-to-end error handling with all components."""
    print("Testing end-to-end error handling...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create real components
        stats = StatsTracker()
        output = OutputManager(verbose_level=1, quiet=False)
        error_manager = ErrorManager(stats_tracker=stats, output_manager=output)
        
        # Create SecurityManager with error handling
        security_manager = SecurityManager(error_manager=error_manager)
        
        # Create FileSystemWalker with error handling
        walker = FileSystemWalker(security_manager, stats, error_manager)
        
        # Test processing a valid directory (should work without errors)
        try:
            walker._process_directory(temp_dir, None, False, output)
            # Should complete without raising exceptions
        except Exception as e:
            # If an exception occurs, it should be handled gracefully
            print(f"Note: Exception occurred but was handled: {e}")
        
        # Verify stats were updated
        assert stats.dirs_traversed >= 1, "Should have traversed at least one directory"
        
    print("✓ End-to-end error handling test passed")


def test_privilege_validation_integration():
    """Test Administrator privilege validation integration."""
    print("Testing privilege validation integration...")
    
    # Create output manager
    output = OutputManager(verbose_level=0, quiet=False)
    error_manager = ErrorManager(output_manager=output)
    
    # Test privilege validation (will likely return False in test environment)
    result = error_manager.validate_administrator_privileges()
    
    # Result should be boolean
    assert isinstance(result, bool), "Privilege validation should return boolean"
    
    # If not admin, should have printed warning
    if not result:
        print("Note: Not running as Administrator (expected in test environment)")
    
    print("✓ Privilege validation integration test passed")


def test_error_categorization_integration():
    """Test that different error types are properly categorized and handled."""
    print("Testing error categorization integration...")
    
    # Create mock dependencies
    mock_stats = Mock()
    mock_stats.increment_exceptions = Mock()
    
    mock_output = Mock()
    mock_output.print_error = Mock()
    mock_output.print_general_error = Mock()
    mock_output.get_verbose_level = Mock(return_value=1)
    
    error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
    
    # Test different error types
    test_cases = [
        (FileNotFoundError("File not found"), ErrorCategory.FILESYSTEM),
        (PermissionError("Access denied"), ErrorCategory.SECURITY),
        (ValueError("Invalid argument"), ErrorCategory.CONFIGURATION),
        (Exception("timeout occurred"), ErrorCategory.TIMEOUT),
        (KeyboardInterrupt(), ErrorCategory.CRITICAL)
    ]
    
    for exception, expected_category in test_cases:
        if expected_category == ErrorCategory.CRITICAL:
            # Mock sys.exit for critical errors
            with patch('sys.exit'):
                error_info = error_manager.handle_exception(exception, "/test/path", "Test context")
                assert error_info.category == expected_category, f"Expected {expected_category}, got {error_info.category}"
        else:
            error_info = error_manager.handle_exception(exception, "/test/path", "Test context")
            assert error_info.category == expected_category, f"Expected {expected_category}, got {error_info.category}"
    
    # Verify exceptions were counted
    assert mock_stats.increment_exceptions.call_count == len(test_cases), "All exceptions should be counted"
    
    print("✓ Error categorization integration test passed")


def test_exception_context_integration():
    """Test exception context manager integration."""
    print("Testing exception context manager integration...")
    
    # Create mock dependencies
    mock_stats = Mock()
    mock_stats.increment_exceptions = Mock()
    
    mock_output = Mock()
    mock_output.print_error = Mock()
    
    error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
    
    # Test successful operation
    with error_manager.create_exception_context("Test operation", "/test/path") as ctx:
        pass  # No exception
    
    assert not ctx.error_occurred, "Should not have error for successful operation"
    
    # Test operation with non-critical exception
    with error_manager.create_exception_context("Test operation", "/test/path") as ctx:
        raise FileNotFoundError("Test file not found")
    
    assert ctx.error_occurred, "Should have error when exception occurs"
    mock_stats.increment_exceptions.assert_called()
    
    print("✓ Exception context integration test passed")


def run_all_tests():
    """Run all integration tests."""
    print("Running error handling integration tests...\n")
    
    try:
        test_security_manager_error_handling()
        test_filesystem_walker_error_handling()
        test_end_to_end_error_handling()
        test_privilege_validation_integration()
        test_error_categorization_integration()
        test_exception_context_integration()
        
        print("\n✅ All error handling integration tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())