#!/usr/bin/env python3
"""
Test suite for failed files logging functionality in fix-owner script.

This module tests the ability to collect and log files that failed during
processing to the output directory for later analysis.

Test Coverage:
- Failed files collection during processing
- Failed directories collection during processing
- Output directory logging of failures
- Integration with ErrorManager
- Failure log format and content
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import the modules to test
from filesystem_walker import FileSystemWalker
from error_manager import ErrorManager
from stats_tracker import StatsTracker
from security_manager import SecurityManager


class TestFailedFilesLogging(unittest.TestCase):
    """Test failed files logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_security_manager = Mock(spec=SecurityManager)
        self.mock_stats_tracker = Mock(spec=StatsTracker)
        self.mock_error_manager = Mock(spec=ErrorManager)
        self.mock_output_manager = Mock()
        
        # Create FileSystemWalker instance
        self.walker = FileSystemWalker(
            security_manager=self.mock_security_manager,
            stats_tracker=self.mock_stats_tracker,
            error_manager=self.mock_error_manager
        )
    
    def test_failed_files_initialization(self):
        """Test that failed files lists are initialized."""
        self.assertEqual(self.walker.failed_files, [])
        self.assertEqual(self.walker.failed_directories, [])
    
    def test_failed_directory_collection_without_error_manager(self):
        """Test failed directory collection when ErrorManager is not available."""
        # Create walker without error manager
        walker = FileSystemWalker(
            security_manager=self.mock_security_manager,
            stats_tracker=self.mock_stats_tracker,
            error_manager=None
        )
        
        # Mock the directory processing to raise an exception
        with patch.object(walker, '_process_directory_ownership', side_effect=Exception("Test error")):
            # This should collect the failure
            walker._process_directory(
                dir_path="/test/dir",
                owner_sid="test_sid",
                execute=False,
                output_manager=self.mock_output_manager
            )
        
        # Verify the failure was collected
        self.assertEqual(len(walker.failed_directories), 1)
        self.assertEqual(walker.failed_directories[0]['path'], "/test/dir")
        self.assertEqual(walker.failed_directories[0]['error'], "Test error")
        self.assertEqual(walker.failed_directories[0]['exception_type'], "Exception")
    
    def test_failed_file_collection_without_error_manager(self):
        """Test failed file collection when ErrorManager is not available."""
        # Create walker without error manager
        walker = FileSystemWalker(
            security_manager=self.mock_security_manager,
            stats_tracker=self.mock_stats_tracker,
            error_manager=None
        )
        
        # Mock the file processing to raise an exception
        with patch.object(walker, '_process_file_ownership', side_effect=Exception("File error")):
            # This should collect the failure
            walker._process_file(
                file_path="/test/file.txt",
                owner_sid="test_sid",
                execute=False,
                output_manager=self.mock_output_manager
            )
        
        # Verify the failure was collected
        self.assertEqual(len(walker.failed_files), 1)
        self.assertEqual(walker.failed_files[0]['path'], "/test/file.txt")
        self.assertEqual(walker.failed_files[0]['error'], "File error")
        self.assertEqual(walker.failed_files[0]['exception_type'], "Exception")
    
    def test_failed_directory_collection_with_error_manager(self):
        """Test failed directory collection when ErrorManager is available."""
        # Mock the error manager context to raise an exception
        context_mock = Mock()
        context_mock.__enter__ = Mock(return_value=context_mock)
        context_mock.__exit__ = Mock(side_effect=Exception("Context error"))
        self.mock_error_manager.create_exception_context.return_value = context_mock
        
        # Mock the directory processing
        with patch.object(self.walker, '_process_directory_ownership'):
            try:
                # This should collect the failure and re-raise
                self.walker._process_directory(
                    dir_path="/test/context_dir",
                    owner_sid="test_sid",
                    execute=False,
                    output_manager=self.mock_output_manager
                )
            except Exception:
                pass  # Expected to be re-raised
        
        # Verify the failure was collected
        self.assertEqual(len(self.walker.failed_directories), 1)
        self.assertEqual(self.walker.failed_directories[0]['path'], "/test/context_dir")
        self.assertEqual(self.walker.failed_directories[0]['error'], "Context error")
        self.assertEqual(self.walker.failed_directories[0]['exception_type'], "Exception")
    
    def test_failed_file_collection_with_error_manager(self):
        """Test failed file collection when ErrorManager is available."""
        # Mock the error manager context to raise an exception
        context_mock = Mock()
        context_mock.__enter__ = Mock(return_value=context_mock)
        context_mock.__exit__ = Mock(side_effect=Exception("File context error"))
        self.mock_error_manager.create_exception_context.return_value = context_mock
        
        # Mock the file processing
        with patch.object(self.walker, '_process_file_ownership'):
            try:
                # This should collect the failure and re-raise
                self.walker._process_file(
                    file_path="/test/context_file.txt",
                    owner_sid="test_sid",
                    execute=False,
                    output_manager=self.mock_output_manager
                )
            except Exception:
                pass  # Expected to be re-raised
        
        # Verify the failure was collected
        self.assertEqual(len(self.walker.failed_files), 1)
        self.assertEqual(self.walker.failed_files[0]['path'], "/test/context_file.txt")
        self.assertEqual(self.walker.failed_files[0]['error'], "File context error")
        self.assertEqual(self.walker.failed_files[0]['exception_type'], "Exception")
    
    def test_write_failed_files_log_no_failures(self):
        """Test write_failed_files_log when there are no failures."""
        # Should not call error manager when no failures
        self.walker.write_failed_files_log()
        
        # Verify error manager was not called
        self.mock_error_manager.log_operation_failures.assert_not_called()
    
    def test_write_failed_files_log_no_error_manager(self):
        """Test write_failed_files_log when ErrorManager is not available."""
        # Create walker without error manager
        walker = FileSystemWalker(
            security_manager=self.mock_security_manager,
            stats_tracker=self.mock_stats_tracker,
            error_manager=None
        )
        
        # Add some failures
        walker.failed_files.append({
            'path': '/test/file.txt',
            'error': 'Test error',
            'exception_type': 'Exception'
        })
        
        # Should not crash when no error manager
        walker.write_failed_files_log()
    
    def test_write_failed_files_log_with_failures(self):
        """Test write_failed_files_log with both file and directory failures."""
        # Add some failures
        self.walker.failed_files.append({
            'path': '/test/file1.txt',
            'error': 'Access denied',
            'exception_type': 'PermissionError'
        })
        self.walker.failed_files.append({
            'path': '/test/file2.txt',
            'error': 'File not found',
            'exception_type': 'FileNotFoundError'
        })
        self.walker.failed_directories.append({
            'path': '/test/dir1',
            'error': 'Access denied',
            'exception_type': 'PermissionError'
        })
        
        # Call the method
        self.walker.write_failed_files_log()
        
        # Verify error manager was called
        self.mock_error_manager.log_operation_failures.assert_called_once()
        
        # Get the call arguments
        call_args = self.mock_error_manager.log_operation_failures.call_args
        operation = call_args[1]['operation']
        failures = call_args[1]['failures']
        summary = call_args[1]['summary']
        
        # Verify the operation name
        self.assertEqual(operation, "filesystem_processing")
        
        # Verify the number of failures
        self.assertEqual(len(failures), 3)  # 2 files + 1 directory
        
        # Verify the summary contains the counts
        self.assertIn("Total Failed Files: 2", summary)
        self.assertIn("Total Failed Directories: 1", summary)
        self.assertIn("Total Failures: 3", summary)
        
        # Verify failures are formatted correctly
        self.assertIn("Directory: /test/dir1", failures[0])  # Should be sorted first
        self.assertIn("File: /test/file1.txt", failures[1])
        self.assertIn("File: /test/file2.txt", failures[2])
    
    def test_failure_sorting(self):
        """Test that failures are sorted by path."""
        # Add failures in non-alphabetical order
        self.walker.failed_files.append({
            'path': '/test/z_file.txt',
            'error': 'Error Z',
            'exception_type': 'Exception'
        })
        self.walker.failed_files.append({
            'path': '/test/a_file.txt',
            'error': 'Error A',
            'exception_type': 'Exception'
        })
        self.walker.failed_directories.append({
            'path': '/test/m_dir',
            'error': 'Error M',
            'exception_type': 'Exception'
        })
        
        # Call the method
        self.walker.write_failed_files_log()
        
        # Get the failures from the call
        call_args = self.mock_error_manager.log_operation_failures.call_args
        failures = call_args[1]['failures']
        
        # Verify they are sorted alphabetically
        self.assertIn("/test/a_file.txt", failures[0])
        self.assertIn("/test/m_dir", failures[1])
        self.assertIn("/test/z_file.txt", failures[2])
    
    def test_failure_format(self):
        """Test the format of individual failure entries."""
        # Add a failure
        self.walker.failed_files.append({
            'path': '/test/sample.txt',
            'error': 'Sample error message',
            'exception_type': 'SampleException'
        })
        
        # Call the method
        self.walker.write_failed_files_log()
        
        # Get the failures from the call
        call_args = self.mock_error_manager.log_operation_failures.call_args
        failures = call_args[1]['failures']
        
        # Verify the format
        failure_text = failures[0]
        self.assertIn("File: /test/sample.txt", failure_text)
        self.assertIn("Error: Sample error message", failure_text)
        self.assertIn("Exception: SampleException", failure_text)


class TestFailedFilesIntegration(unittest.TestCase):
    """Test integration of failed files logging with main execution flow."""
    
    @patch('fix_owner.FileSystemWalker')
    def test_failed_files_log_called_after_processing(self, mock_walker_class):
        """Test that write_failed_files_log is called after filesystem processing."""
        # Import here to avoid circular imports
        from fix_owner import process_filesystem, ExecutionOptions
        from output_manager import OutputManager
        from timeout_manager import TimeoutManager
        
        # Create mock instances
        mock_walker = Mock()
        mock_walker_class.return_value = mock_walker
        
        mock_options = Mock(spec=ExecutionOptions)
        mock_options.root_path = "/test/path"
        mock_options.recurse = True
        mock_options.files = True
        mock_options.execute = False
        mock_options.timeout = 0
        
        mock_owner_sid = Mock()
        mock_stats = Mock()
        mock_output = Mock(spec=OutputManager)
        mock_output.get_verbose_level.return_value = 0
        mock_timeout_manager = Mock(spec=TimeoutManager)
        mock_security_manager = Mock(spec=SecurityManager)
        mock_error_manager = Mock(spec=ErrorManager)
        
        # Call process_filesystem
        process_filesystem(
            options=mock_options,
            owner_sid=mock_owner_sid,
            stats=mock_stats,
            output=mock_output,
            timeout_manager=mock_timeout_manager,
            security_manager=mock_security_manager,
            error_manager=mock_error_manager
        )
        
        # Verify that the walker was created with the error manager
        mock_walker_class.assert_called_once_with(
            mock_security_manager, mock_stats, mock_error_manager, None
        )
        
        # Verify that walk_filesystem was called
        mock_walker.walk_filesystem.assert_called_once()
        
        # Verify that write_failed_files_log was called after processing
        mock_walker.write_failed_files_log.assert_called_once()


if __name__ == '__main__':
    print("🧪 Testing failed files logging functionality...")
    unittest.main(verbosity=2)