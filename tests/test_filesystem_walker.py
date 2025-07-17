#!/usr/bin/env python3
"""
Unit tests for FileSystemWalker class - comprehensive directory traversal testing.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import os
import tempfile
import shutil
import sys

# Add current directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.filesystem_walker import FileSystemWalker
from src.error_manager import ErrorManager


class TestFileSystemWalker(unittest.TestCase):
    """Test cases for FileSystemWalker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_security_manager = Mock()
        self.mock_stats_tracker = Mock()
        self.mock_error_manager = Mock()
        
        # Create a proper mock context manager
        self.mock_context = Mock()
        self.mock_context.__enter__ = Mock(return_value=self.mock_context)
        self.mock_context.__exit__ = Mock(return_value=False)  # Don't suppress exceptions
        self.mock_error_manager.create_exception_context.return_value = self.mock_context
        
        # Create walker with error manager
        self.walker = FileSystemWalker(
            self.mock_security_manager, 
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Create temporary directory structure for testing
        self.test_dir = tempfile.mkdtemp()
        self.sub_dir = os.path.join(self.test_dir, "subdir")
        self.deep_dir = os.path.join(self.sub_dir, "deepdir")
        os.makedirs(self.deep_dir)
        
        # Create test files
        self.test_file1 = os.path.join(self.test_dir, "file1.txt")
        self.test_file2 = os.path.join(self.sub_dir, "file2.txt")
        self.test_file3 = os.path.join(self.deep_dir, "file3.txt")
        
        for file_path in [self.test_file1, self.test_file2, self.test_file3]:
            with open(file_path, 'w') as f:
                f.write("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_walker_initialization(self):
        """Test FileSystemWalker initialization."""
        self.assertEqual(self.walker.security_manager, self.mock_security_manager)
        self.assertEqual(self.walker.stats_tracker, self.mock_stats_tracker)
    
    def test_walk_filesystem_no_recursion_no_files(self):
        """Test filesystem walk without recursion and without file processing."""
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False
        )
        
        # Verify only root directory was processed
        self.mock_stats_tracker.increment_dirs_traversed.assert_called()
        self.mock_stats_tracker.increment_files_traversed.assert_not_called()
        
        # Should have called get_current_owner for root directory only
        self.assertEqual(self.mock_security_manager.get_current_owner.call_count, 1)
        self.mock_security_manager.get_current_owner.assert_called_with(self.test_dir)
    
    def test_walk_filesystem_with_recursion(self):
        """Test filesystem walk with recursion enabled."""
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem with recursion
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=True,
            process_files=False,
            execute=False
        )
        
        # Should process all directories (root, sub, deep)
        self.assertEqual(self.mock_stats_tracker.increment_dirs_traversed.call_count, 3)
        self.mock_stats_tracker.increment_files_traversed.assert_not_called()
        
        # Should have called get_current_owner for all directories (root, sub, deep)
        self.assertEqual(self.mock_security_manager.get_current_owner.call_count, 3)
    
    def test_walk_filesystem_with_files(self):
        """Test filesystem walk with file processing enabled."""
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem with file processing
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=True,
            process_files=True,
            execute=False
        )
        
        # Should process directories and files
        self.assertEqual(self.mock_stats_tracker.increment_dirs_traversed.call_count, 3)
        self.assertEqual(self.mock_stats_tracker.increment_files_traversed.call_count, 3)
    
    def test_walk_filesystem_with_invalid_sid(self):
        """Test filesystem walk with invalid SID that needs ownership change."""
        # Mock security manager responses - invalid SID
        self.mock_security_manager.get_current_owner.return_value = (None, "invalid_sid")
        self.mock_security_manager.is_sid_valid.return_value = False
        
        mock_owner_sid = Mock()
        
        # Walk filesystem in execute mode
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=True
        )
        
        # Should have attempted to set owner
        self.mock_security_manager.set_owner.assert_called_with(self.test_dir, mock_owner_sid)
        self.mock_stats_tracker.increment_dirs_changed.assert_called()
    
    def test_walk_filesystem_dry_run_mode(self):
        """Test filesystem walk in dry run mode."""
        # Mock security manager responses - invalid SID
        self.mock_security_manager.get_current_owner.return_value = (None, "invalid_sid")
        self.mock_security_manager.is_sid_valid.return_value = False
        
        mock_owner_sid = Mock()
        
        # Walk filesystem in dry run mode
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False
        )
        
        # Should NOT have attempted to set owner
        self.mock_security_manager.set_owner.assert_not_called()
        # But should still track the change
        self.mock_stats_tracker.increment_dirs_changed.assert_called()
    
    def test_walk_filesystem_with_exception_handling(self):
        """Test filesystem walk with exception handling."""
        # Mock security manager to raise exception
        self.mock_security_manager.get_current_owner.side_effect = Exception("Test exception")
        
        # Mock context manager to suppress exceptions (return True)
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=True)  # Suppress exceptions
        self.mock_error_manager.create_exception_context.return_value = mock_context
        
        mock_owner_sid = Mock()
        mock_output_manager = Mock()
        
        # Walk filesystem - should not raise exception due to context manager
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False,
            output_manager=mock_output_manager
        )
        
        # Should have created exception context
        self.mock_error_manager.create_exception_context.assert_called()
    
    def test_walk_filesystem_with_timeout(self):
        """Test filesystem walk with timeout manager."""
        mock_timeout_manager = Mock()
        mock_timeout_manager.is_timeout_reached.return_value = True
        mock_output_manager = Mock()
        
        mock_owner_sid = Mock()
        
        # Walk filesystem with timeout reached
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False,
            output_manager=mock_output_manager,
            timeout_manager=mock_timeout_manager
        )
        
        # Should have printed timeout warning
        mock_output_manager.print_timeout_warning.assert_called()
    
    def test_walk_filesystem_deep_recursion(self):
        """Test filesystem walk with deep directory structure."""
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem with full recursion
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=True,
            process_files=True,
            execute=False
        )
        
        # Should process all 3 directories (root, sub, deep)
        self.assertEqual(self.mock_stats_tracker.increment_dirs_traversed.call_count, 3)
        # Should process all 3 files
        self.assertEqual(self.mock_stats_tracker.increment_files_traversed.call_count, 3)
    
    def test_walk_filesystem_mixed_valid_invalid_sids(self):
        """Test filesystem walk with mix of valid and invalid SIDs."""
        # Mock security manager to return different results for different paths
        def mock_get_owner(path):
            if "subdir" in path:
                return (None, "invalid_sid")  # Invalid SID
            else:
                return ("ValidUser", "valid_sid")  # Valid SID
        
        def mock_is_valid(sid):
            return str(sid) != "invalid_sid"
        
        self.mock_security_manager.get_current_owner.side_effect = mock_get_owner
        self.mock_security_manager.is_sid_valid.side_effect = mock_is_valid
        
        mock_owner_sid = Mock()
        
        # Walk filesystem in execute mode
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=True,
            process_files=False,
            execute=True
        )
        
        # Should have changed ownership for subdirectories with invalid SIDs
        # The exact number depends on directory structure, but should be > 0
        self.mock_stats_tracker.increment_dirs_changed.assert_called()
        self.mock_security_manager.set_owner.assert_called()
    
    def test_walk_filesystem_with_error_manager_context(self):
        """Test filesystem walk with ErrorManager context handling."""
        # Create a mock context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)  # Don't suppress exceptions
        
        self.mock_error_manager.create_exception_context.return_value = mock_context
        
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False
        )
        
        # Should have created exception context
        self.mock_error_manager.create_exception_context.assert_called()
    
    def test_walk_filesystem_keyboard_interrupt(self):
        """Test filesystem walk handling of KeyboardInterrupt."""
        # Mock security manager to raise KeyboardInterrupt
        self.mock_security_manager.get_current_owner.side_effect = KeyboardInterrupt()
        
        mock_owner_sid = Mock()
        mock_output_manager = Mock()
        
        # Walk filesystem - should re-raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.walker.walk_filesystem(
                root_path=self.test_dir,
                owner_sid=mock_owner_sid,
                recurse=False,
                process_files=False,
                execute=False,
                output_manager=mock_output_manager
            )
    
    def test_process_directory_ownership_change(self):
        """Test directory ownership processing logic."""
        # Mock invalid SID that needs change
        self.mock_security_manager.get_current_owner.return_value = (None, "invalid_sid")
        self.mock_security_manager.is_sid_valid.return_value = False
        
        mock_owner_sid = Mock()
        mock_output_manager = Mock()
        
        # Process directory directly
        self.walker._process_directory(
            self.test_dir, mock_owner_sid, True, mock_output_manager
        )
        
        # Verify ownership change was attempted
        self.mock_security_manager.set_owner.assert_called_with(self.test_dir, mock_owner_sid)
        self.mock_stats_tracker.increment_dirs_changed.assert_called()
        mock_output_manager.print_ownership_change.assert_called()
    
    def test_process_file_ownership_change(self):
        """Test file ownership processing logic."""
        # Mock invalid SID that needs change
        self.mock_security_manager.get_current_owner.return_value = (None, "invalid_sid")
        self.mock_security_manager.is_sid_valid.return_value = False
        
        mock_owner_sid = Mock()
        mock_output_manager = Mock()
        
        # Process file directly
        self.walker._process_file(
            self.test_file1, mock_owner_sid, True, mock_output_manager
        )
        
        # Verify ownership change was attempted
        self.mock_security_manager.set_owner.assert_called_with(self.test_file1, mock_owner_sid)
        self.mock_stats_tracker.increment_files_changed.assert_called()
        mock_output_manager.print_ownership_change.assert_called()
    
    def test_walk_filesystem_timeout_during_file_processing(self):
        """Test timeout occurring during file processing."""
        mock_timeout_manager = Mock()
        # Timeout reached during file processing
        mock_timeout_manager.is_timeout_reached.side_effect = [False, True]  # First call False, second True
        mock_output_manager = Mock()
        
        # Mock security manager responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        
        mock_owner_sid = Mock()
        
        # Walk filesystem with file processing and timeout
        self.walker.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=True,
            execute=False,
            output_manager=mock_output_manager,
            timeout_manager=mock_timeout_manager
        )
        
        # Should have printed timeout warning
        mock_output_manager.print_timeout_warning.assert_called()
    
    def test_walker_without_error_manager(self):
        """Test FileSystemWalker without ErrorManager (fallback behavior)."""
        # Create walker without error manager
        walker_no_error = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            error_manager=None
        )
        
        # Mock security manager to raise exception
        self.mock_security_manager.get_current_owner.side_effect = Exception("Test exception")
        
        mock_owner_sid = Mock()
        mock_output_manager = Mock()
        
        # Walk filesystem - should handle exception with fallback logic
        walker_no_error.walk_filesystem(
            root_path=self.test_dir,
            owner_sid=mock_owner_sid,
            recurse=False,
            process_files=False,
            execute=False,
            output_manager=mock_output_manager
        )
        
        # Should have incremented exception counter (fallback behavior)
        self.mock_stats_tracker.increment_exceptions.assert_called()
        mock_output_manager.print_error.assert_called()


def run_filesystem_walker_tests():
    """Run all FileSystemWalker tests."""
    print("Running FileSystemWalker tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFileSystemWalker)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_filesystem_walker_tests())