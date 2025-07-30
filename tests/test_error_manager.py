#!/usr/bin/env python3
"""
Test suite for ErrorManager class - comprehensive error handling and exception management.
"""

import sys
import io
import os
from unittest.mock import Mock, patch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.error_manager import ErrorManager, ErrorCategory, ErrorInfo, ExceptionContext


def test_error_categorization():
    """Test that exceptions are properly categorized."""
    print("Testing error categorization...")
    
    # Create ErrorManager instance
    error_manager = ErrorManager()
    
    # Test security errors
    security_error = Exception("Access denied")
    category = error_manager._categorize_exception(security_error, "/test/path", "test context")
    assert category == ErrorCategory.SECURITY, f"Expected SECURITY, got {category}"
    
    # Test filesystem errors
    fs_error = FileNotFoundError("File not found")
    category = error_manager._categorize_exception(fs_error, "/test/path", "test context")
    assert category == ErrorCategory.FILESYSTEM, f"Expected FILESYSTEM, got {category}"
    
    # Test configuration errors
    config_error = ValueError("Invalid argument")
    category = error_manager._categorize_exception(config_error, None, "test context")
    assert category == ErrorCategory.CONFIGURATION, f"Expected CONFIGURATION, got {category}"
    
    # Test timeout errors
    timeout_error = Exception("timeout occurred")
    category = error_manager._categorize_exception(timeout_error, None, "test context")
    assert category == ErrorCategory.TIMEOUT, f"Expected TIMEOUT, got {category}"
    
    # Test critical errors
    critical_error = KeyboardInterrupt()
    category = error_manager._categorize_exception(critical_error, None, "test context")
    assert category == ErrorCategory.CRITICAL, f"Expected CRITICAL, got {category}"
    
    print("✓ Error categorization test passed")


def test_error_message_formatting():
    """Test that error messages are properly formatted."""
    print("Testing error message formatting...")
    
    error_manager = ErrorManager()
    
    # Test with path and context
    exception = Exception("Test error")
    message = error_manager._format_error_message(exception, "/test/path", "Test operation")
    expected = "Test operation - Path '/test/path': Test error"
    assert message == expected, f"Expected '{expected}', got '{message}'"
    
    # Test with path only
    message = error_manager._format_error_message(exception, "/test/path", "")
    expected = "Path '/test/path': Test error"
    assert message == expected, f"Expected '{expected}', got '{message}'"
    
    # Test with context only
    message = error_manager._format_error_message(exception, None, "Test operation")
    expected = "Test operation - Test error"
    assert message == expected, f"Expected '{expected}', got '{message}'"
    
    # Test with neither
    message = error_manager._format_error_message(exception, None, "")
    expected = "Test error"
    assert message == expected, f"Expected '{expected}', got '{message}'"
    
    print("✓ Error message formatting test passed")


def test_exception_handling_with_stats():
    """Test that exceptions are properly counted in statistics."""
    print("Testing exception handling with statistics...")
    
    # Create mock stats tracker
    mock_stats = Mock()
    mock_stats.increment_exceptions = Mock()
    
    # Create mock output manager
    mock_output = Mock()
    
    # Create ErrorManager with mocked dependencies
    error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
    
    # Handle an exception
    test_exception = Exception("Test exception")
    error_info = error_manager.handle_exception(test_exception, "/test/path", "Test context")
    
    # Verify exception was counted
    mock_stats.increment_exceptions.assert_called_once()
    
    # Verify error info is correct
    assert error_info.category == ErrorCategory.FILESYSTEM  # Default for generic exceptions
    assert error_info.path == "/test/path"
    assert error_info.original_exception == test_exception
    assert "Test context" in error_info.message
    
    print("✓ Exception handling with statistics test passed")


def test_administrator_privilege_validation():
    """Test Administrator privilege validation."""
    print("Testing Administrator privilege validation...")
    
    # Create mock output manager
    mock_output = Mock()
    mock_output.print_privilege_warning = Mock()
    mock_output.print_general_error = Mock()
    
    error_manager = ErrorManager(output_manager=mock_output)
    
    # Test with mock that returns False (not admin)
    with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=False):
        result = error_manager.validate_administrator_privileges()
        assert result == False, "Should return False when not admin"
        mock_output.print_privilege_warning.assert_called()
    
    # Test with mock that returns True (is admin)
    with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=True):
        result = error_manager.validate_administrator_privileges()
        assert result == True, "Should return True when admin"
    
    print("✓ Administrator privilege validation test passed")


def test_exception_context_manager():
    """Test the ExceptionContext context manager."""
    print("Testing exception context manager...")
    
    # Create mock error manager
    mock_error_manager = Mock()
    mock_error_info = Mock()
    mock_error_info.should_terminate = False
    mock_error_manager.handle_exception.return_value = mock_error_info
    
    # Test successful operation (no exception)
    with ExceptionContext(mock_error_manager, "Test operation", "/test/path") as ctx:
        pass  # No exception
    
    assert not ctx.error_occurred, "Should not have error for successful operation"
    mock_error_manager.handle_exception.assert_not_called()
    
    # Test operation with exception
    test_exception = Exception("Test exception")
    with ExceptionContext(mock_error_manager, "Test operation", "/test/path") as ctx:
        raise test_exception
    
    assert ctx.error_occurred, "Should have error when exception occurs"
    mock_error_manager.handle_exception.assert_called_once_with(
        test_exception, path="/test/path", context="Test operation"
    )
    
    print("✓ Exception context manager test passed")


def test_error_handler_integration():
    """Test integration of different error handlers."""
    print("Testing error handler integration...")
    
    # Create output buffer to capture output
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    
    # Create mock output manager
    mock_output = Mock()
    mock_output.print_error = Mock()
    mock_output.print_general_error = Mock()
    mock_output.print_privilege_warning = Mock()
    mock_output.is_verbose = Mock(return_value=False)
    
    # Create mock stats tracker
    mock_stats = Mock()
    mock_stats.increment_exceptions = Mock()
    
    error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
    
    # Test security error handling
    security_error = Exception("Access denied")
    error_info = error_manager.handle_exception(security_error, "/test/path", "Security test")
    assert error_info.category == ErrorCategory.SECURITY
    mock_output.print_error.assert_called()
    
    # Test filesystem error handling
    fs_error = FileNotFoundError("File not found")
    error_info = error_manager.handle_exception(fs_error, "/test/file", "Filesystem test")
    assert error_info.category == ErrorCategory.FILESYSTEM
    
    # Test configuration error handling
    config_error = ValueError("Invalid configuration")
    error_info = error_manager.handle_exception(config_error, None, "Config test")
    assert error_info.category == ErrorCategory.CONFIGURATION
    mock_output.print_general_error.assert_called()
    
    print("✓ Error handler integration test passed")


def test_common_error_solutions():
    """Test that common error solutions are provided."""
    print("Testing common error solutions...")
    
    error_manager = ErrorManager()
    
    # Test security error solutions
    solutions = error_manager.get_common_error_solutions(ErrorCategory.SECURITY)
    assert len(solutions) > 0, "Should provide security error solutions"
    assert any("Administrator" in solution for solution in solutions), "Should mention Administrator privileges"
    
    # Test filesystem error solutions
    solutions = error_manager.get_common_error_solutions(ErrorCategory.FILESYSTEM)
    assert len(solutions) > 0, "Should provide filesystem error solutions"
    assert any("path" in solution.lower() for solution in solutions), "Should mention path issues"
    
    # Test configuration error solutions
    solutions = error_manager.get_common_error_solutions(ErrorCategory.CONFIGURATION)
    assert len(solutions) > 0, "Should provide configuration error solutions"
    assert any("argument" in solution.lower() for solution in solutions), "Should mention arguments"
    
    # Test privilege error solutions
    solutions = error_manager.get_common_error_solutions(ErrorCategory.PRIVILEGE)
    assert len(solutions) > 0, "Should provide privilege error solutions"
    assert any("Administrator" in solution for solution in solutions), "Should mention Administrator"
    
    # Test timeout error solutions
    solutions = error_manager.get_common_error_solutions(ErrorCategory.TIMEOUT)
    assert len(solutions) > 0, "Should provide timeout error solutions"
    assert any("timeout" in solution.lower() for solution in solutions), "Should mention timeout"
    
    print("✓ Common error solutions test passed")


def test_critical_error_handling():
    """Test that critical errors are handled properly."""
    print("Testing critical error handling...")
    
    # Create mock output manager
    mock_output = Mock()
    mock_output.print_general_error = Mock()
    mock_output.get_verbose_level = Mock(return_value=0)
    
    error_manager = ErrorManager(output_manager=mock_output)
    
    # Test critical error (should attempt to exit)
    critical_error = KeyboardInterrupt()
    
    # Mock sys.exit to prevent actual exit during testing
    with patch('sys.exit') as mock_exit:
        error_info = error_manager.handle_exception(critical_error, None, "Critical test", critical=True)
        
        # Verify it's marked as critical
        assert error_info.is_critical, "Should be marked as critical"
        assert error_info.should_terminate, "Should indicate termination needed"
        
        # Verify sys.exit was called
        mock_exit.assert_called_with(1)
    
    print("✓ Critical error handling test passed")


def run_all_tests():
    """Run all ErrorManager tests."""
    print("Running ErrorManager tests...\n")
    
    try:
        test_error_categorization()
        test_error_message_formatting()
        test_exception_handling_with_stats()
        test_administrator_privilege_validation()
        test_exception_context_manager()
        test_error_handler_integration()
        test_common_error_solutions()
        test_critical_error_handling()
        
        print("\n✅ All ErrorManager tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())