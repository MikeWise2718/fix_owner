#!/usr/bin/env python3
"""
Test suite for common utilities and constants.

This module tests the shared utilities, constants, and helper functions
in common.py to increase coverage of the foundational components.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import time

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import common
from common import (
    get_current_timestamp, format_elapsed_time, setup_module_path,
    print_section_header, print_section_bar, safe_exit,
    validate_path_exists, validate_path_is_directory,
    try_import_with_fallback, COLORAMA_AVAILABLE, PYWIN32_AVAILABLE,
    EXIT_SUCCESS, EXIT_ERROR, EXIT_INTERRUPTED
)


class TestTimestampUtilities(unittest.TestCase):
    """Test cases for timestamp and time formatting utilities."""
    
    def test_get_current_timestamp(self):
        """Test getting current timestamp."""
        timestamp = get_current_timestamp()
        self.assertIsInstance(timestamp, float)
        self.assertGreater(timestamp, 0)
        
        # Test that consecutive calls return increasing timestamps
        timestamp2 = get_current_timestamp()
        self.assertGreaterEqual(timestamp2, timestamp)
    
    def test_format_elapsed_time(self):
        """Test elapsed time calculation."""
        start_time = time.time()
        time.sleep(0.01)  # Small delay
        elapsed = format_elapsed_time(start_time)
        
        self.assertIsInstance(elapsed, float)
        self.assertGreater(elapsed, 0)
        self.assertLess(elapsed, 1)  # Should be less than 1 second
    
    def test_format_elapsed_time_zero(self):
        """Test elapsed time with same timestamp."""
        current_time = time.time()
        elapsed = format_elapsed_time(current_time)
        
        self.assertIsInstance(elapsed, float)
        self.assertGreaterEqual(elapsed, 0)


class TestModuleSetup(unittest.TestCase):
    """Test cases for module setup utilities."""
    
    @patch('common.sys.path')
    @patch('common.os.path.dirname')
    @patch('common.os.path.abspath')
    def test_setup_module_path_new_path(self, mock_abspath, mock_dirname, mock_path):
        """Test adding new path to sys.path."""
        mock_abspath.return_value = "/fake/absolute/path"
        mock_dirname.return_value = "/fake/directory"
        mock_path.__contains__ = Mock(return_value=False)
        mock_path.insert = Mock()
        
        setup_module_path()
        
        mock_path.insert.assert_called_once_with(0, "/fake/directory")
    
    @patch('common.sys.path')
    @patch('common.os.path.dirname')
    @patch('common.os.path.abspath')
    def test_setup_module_path_existing_path(self, mock_abspath, mock_dirname, mock_path):
        """Test not adding existing path to sys.path."""
        mock_abspath.return_value = "/fake/absolute/path"
        mock_dirname.return_value = "/fake/directory"
        mock_path.__contains__ = Mock(return_value=True)
        mock_path.insert = Mock()
        
        setup_module_path()
        
        mock_path.insert.assert_not_called()


class TestFormattingUtilities(unittest.TestCase):
    """Test cases for formatting and display utilities."""
    
    @patch('builtins.print')
    def test_print_section_header_default_width(self, mock_print):
        """Test printing section header with default width."""
        print_section_header("Test Section")
        
        # Should print 3 lines: empty line, bar, title, bar
        self.assertEqual(mock_print.call_count, 3)
        
        # Check that bars are printed with correct width
        calls = mock_print.call_args_list
        self.assertIn("=" * 50, calls[0][0][0])  # First bar
        self.assertIn("Test Section", calls[1][0][0])  # Title
        self.assertIn("=" * 50, calls[2][0][0])  # Second bar
    
    @patch('builtins.print')
    def test_print_section_header_custom_width(self, mock_print):
        """Test printing section header with custom width."""
        print_section_header("Custom Section", width=30)
        
        self.assertEqual(mock_print.call_count, 3)
        
        # Check that bars are printed with custom width
        calls = mock_print.call_args_list
        self.assertIn("=" * 30, calls[0][0][0])
        self.assertIn("Custom Section", calls[1][0][0])
        self.assertIn("=" * 30, calls[2][0][0])
    
    @patch('builtins.print')
    def test_print_section_bar_default_width(self, mock_print):
        """Test printing section bar with default width."""
        print_section_bar()
        
        mock_print.assert_called_once()
        self.assertIn("=" * 50, mock_print.call_args[0][0])
    
    @patch('builtins.print')
    def test_print_section_bar_custom_width(self, mock_print):
        """Test printing section bar with custom width."""
        print_section_bar(width=25)
        
        mock_print.assert_called_once()
        self.assertIn("=" * 25, mock_print.call_args[0][0])


class TestSafeExit(unittest.TestCase):
    """Test cases for safe exit functionality."""
    
    @patch('common.sys.exit')
    @patch('builtins.print')
    def test_safe_exit_success_no_message(self, mock_print, mock_exit):
        """Test safe exit with success code and no message."""
        safe_exit(EXIT_SUCCESS)
        
        mock_print.assert_not_called()
        mock_exit.assert_called_once_with(EXIT_SUCCESS)
    
    @patch('common.sys.exit')
    @patch('builtins.print')
    def test_safe_exit_success_with_message(self, mock_print, mock_exit):
        """Test safe exit with success code and message."""
        safe_exit(EXIT_SUCCESS, "Success message")
        
        mock_print.assert_called_once_with("Success message")
        mock_exit.assert_called_once_with(EXIT_SUCCESS)
    
    @patch('common.sys.exit')
    @patch('builtins.print')
    def test_safe_exit_error_with_message(self, mock_print, mock_exit):
        """Test safe exit with error code and message."""
        safe_exit(EXIT_ERROR, "Error message")
        
        # Error messages should go to stderr
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        self.assertEqual(kwargs.get('file'), sys.stderr)
        mock_exit.assert_called_once_with(EXIT_ERROR)
    
    @patch('common.sys.exit')
    @patch('builtins.print')
    def test_safe_exit_interrupted_with_message(self, mock_print, mock_exit):
        """Test safe exit with interrupted code and message."""
        safe_exit(EXIT_INTERRUPTED, "Interrupted message")
        
        # Interrupted messages should go to stderr
        mock_print.assert_called_once()
        args, kwargs = mock_print.call_args
        self.assertEqual(kwargs.get('file'), sys.stderr)
        mock_exit.assert_called_once_with(EXIT_INTERRUPTED)


class TestPathValidation(unittest.TestCase):
    """Test cases for path validation utilities."""
    
    @patch('common.os.path.exists')
    def test_validate_path_exists_true(self, mock_exists):
        """Test path validation when path exists."""
        mock_exists.return_value = True
        
        result = validate_path_exists("/fake/path")
        
        self.assertTrue(result)
        mock_exists.assert_called_once_with("/fake/path")
    
    @patch('common.os.path.exists')
    def test_validate_path_exists_false(self, mock_exists):
        """Test path validation when path doesn't exist."""
        mock_exists.return_value = False
        
        result = validate_path_exists("/nonexistent/path")
        
        self.assertFalse(result)
        mock_exists.assert_called_once_with("/nonexistent/path")
    
    @patch('common.os.path.isdir')
    def test_validate_path_is_directory_true(self, mock_isdir):
        """Test directory validation when path is directory."""
        mock_isdir.return_value = True
        
        result = validate_path_is_directory("/fake/directory")
        
        self.assertTrue(result)
        mock_isdir.assert_called_once_with("/fake/directory")
    
    @patch('common.os.path.isdir')
    def test_validate_path_is_directory_false(self, mock_isdir):
        """Test directory validation when path is not directory."""
        mock_isdir.return_value = False
        
        result = validate_path_is_directory("/fake/file.txt")
        
        self.assertFalse(result)
        mock_isdir.assert_called_once_with("/fake/file.txt")


class TestImportUtilities(unittest.TestCase):
    """Test cases for import utilities."""
    
    def test_try_import_with_fallback_relative_success(self):
        """Test successful relative import."""
        # Mock a module with test attributes
        mock_module = Mock()
        mock_module.test_attr1 = "value1"
        mock_module.test_attr2 = "value2"
        
        with patch('builtins.__import__', return_value=mock_module) as mock_import:
            result = try_import_with_fallback('.test_module', 'test_module', ['test_attr1', 'test_attr2'])
            
            self.assertEqual(result, {'test_attr1': 'value1', 'test_attr2': 'value2'})
            mock_import.assert_called_once_with('.test_module', fromlist=['test_attr1', 'test_attr2'], level=1)
    
    def test_try_import_with_fallback_absolute_fallback(self):
        """Test fallback to absolute import when relative fails."""
        mock_module = Mock()
        mock_module.test_attr = "fallback_value"
        
        def import_side_effect(name, fromlist=None, level=0):
            if level == 1:  # Relative import
                raise ImportError("Relative import failed")
            return mock_module
        
        with patch('builtins.__import__', side_effect=import_side_effect) as mock_import:
            result = try_import_with_fallback('.test_module', 'test_module', ['test_attr'])
            
            self.assertEqual(result, {'test_attr': 'fallback_value'})
            # Should be called twice: once for relative, once for absolute
            self.assertEqual(mock_import.call_count, 2)


class TestConstants(unittest.TestCase):
    """Test cases for constants and availability flags."""
    
    def test_exit_codes(self):
        """Test that exit codes are defined correctly."""
        self.assertEqual(EXIT_SUCCESS, 0)
        self.assertEqual(EXIT_ERROR, 1)
        self.assertEqual(EXIT_INTERRUPTED, 2)
    
    def test_colorama_availability_flag(self):
        """Test that COLORAMA_AVAILABLE flag is boolean."""
        self.assertIsInstance(COLORAMA_AVAILABLE, bool)
    
    def test_pywin32_availability_flag(self):
        """Test that PYWIN32_AVAILABLE flag is boolean."""
        self.assertIsInstance(PYWIN32_AVAILABLE, bool)
    
    def test_color_constants_exist(self):
        """Test that color constants are defined."""
        # These should be strings (either color codes or empty strings)
        self.assertIsInstance(common.info_lt_clr, str)
        self.assertIsInstance(common.info_dk_clr, str)
        self.assertIsInstance(common.section_clr, str)
        self.assertIsInstance(common.error_clr, str)
        self.assertIsInstance(common.warn_clr, str)
        self.assertIsInstance(common.ok_clr, str)
        self.assertIsInstance(common.reset_clr, str)
    
    def test_formatting_constants(self):
        """Test that formatting constants are defined correctly."""
        self.assertIsInstance(common.SECTION_BAR_WIDTH, int)
        self.assertIsInstance(common.REPORT_BAR_WIDTH, int)
        self.assertGreater(common.SECTION_BAR_WIDTH, 0)
        self.assertGreater(common.REPORT_BAR_WIDTH, 0)
    
    def test_script_version(self):
        """Test that script version is defined."""
        self.assertIsInstance(common.SCRIPT_VERSION, str)
        self.assertGreater(len(common.SCRIPT_VERSION), 0)
    
    def test_path_constants(self):
        """Test that path-related constants are defined."""
        self.assertIsInstance(common.MAX_PATH_LENGTH, int)
        self.assertGreater(common.MAX_PATH_LENGTH, 0)
        self.assertIsInstance(common.CHUNK_SIZE, int)
        self.assertGreater(common.CHUNK_SIZE, 0)


# Removed TestColoramaFallback class as it was testing implementation details
# that don't provide meaningful coverage or logic validation


if __name__ == '__main__':
    unittest.main()