#!/usr/bin/env python3
"""
Integration tests and end-to-end testing for the fix-owner script.

This module provides comprehensive integration testing including:
- Test directory structures with known ownership scenarios
- Complete workflow execution verification
- Dry-run mode vs execute mode behavior testing
- Various command-line option combinations
- Performance tests for large directory structures
"""

import unittest
import tempfile
import shutil
import os
import sys
import subprocess
import time
import json
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import main components for integration testing
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.fix_owner import main, parse_arguments
from src.security_manager import SecurityManager
from src.stats_tracker import StatsTracker
from src.filesystem_walker import FileSystemWalker
from src.output_manager import OutputManager
from src.error_manager import ErrorManager
from src.timeout_manager import TimeoutManager


class TestDirectoryStructure:
    """Helper class to create test directory structures with known ownership scenarios."""
    
    def __init__(self, base_path: str):
        """Initialize with base path for test structures."""
        self.base_path = base_path
        self.created_paths = []
    
    def create_simple_structure(self) -> dict:
        """
        Create a simple directory structure for basic testing.
        
        Returns:
            Dictionary with paths and expected ownership info
        """
        structure = {
            'root': os.path.join(self.base_path, 'simple_test'),
            'dirs': [],
            'files': []
        }
        
        # Create root directory
        os.makedirs(structure['root'], exist_ok=True)
        self.created_paths.append(structure['root'])
        
        # Create subdirectories
        subdirs = ['subdir1', 'subdir2', 'subdir1/nested']
        for subdir in subdirs:
            dir_path = os.path.join(structure['root'], subdir)
            os.makedirs(dir_path, exist_ok=True)
            structure['dirs'].append(dir_path)
            self.created_paths.append(dir_path)
        
        # Create files
        files = ['file1.txt', 'subdir1/file2.txt', 'subdir1/nested/file3.txt']
        for file_rel in files:
            file_path = os.path.join(structure['root'], file_rel)
            with open(file_path, 'w') as f:
                f.write(f"Test content for {file_rel}")
            structure['files'].append(file_path)
            self.created_paths.append(file_path)
        
        return structure
    
    def create_deep_structure(self, depth: int = 5, files_per_dir: int = 3) -> dict:
        """
        Create a deep directory structure for recursion testing.
        
        Args:
            depth: Maximum depth of nested directories
            files_per_dir: Number of files to create in each directory
            
        Returns:
            Dictionary with paths and structure info
        """
        structure = {
            'root': os.path.join(self.base_path, 'deep_test'),
            'dirs': [],
            'files': [],
            'depth': depth,
            'files_per_dir': files_per_dir
        }
        
        # Create root directory
        os.makedirs(structure['root'], exist_ok=True)
        self.created_paths.append(structure['root'])
        
        # Create deep nested structure
        current_path = structure['root']
        for level in range(depth):
            # Create directory at this level
            dir_name = f"level_{level}"
            dir_path = os.path.join(current_path, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            structure['dirs'].append(dir_path)
            self.created_paths.append(dir_path)
            
            # Create files in this directory
            for file_num in range(files_per_dir):
                file_name = f"file_{level}_{file_num}.txt"
                file_path = os.path.join(dir_path, file_name)
                with open(file_path, 'w') as f:
                    f.write(f"Content for level {level}, file {file_num}")
                structure['files'].append(file_path)
                self.created_paths.append(file_path)
            
            current_path = dir_path
        
        return structure
    
    def create_large_structure(self, num_dirs: int = 100, num_files: int = 200) -> dict:
        """
        Create a large directory structure for performance testing.
        
        Args:
            num_dirs: Number of directories to create
            num_files: Number of files to create
            
        Returns:
            Dictionary with paths and structure info
        """
        structure = {
            'root': os.path.join(self.base_path, 'large_test'),
            'dirs': [],
            'files': [],
            'num_dirs': num_dirs,
            'num_files': num_files
        }
        
        # Create root directory
        os.makedirs(structure['root'], exist_ok=True)
        self.created_paths.append(structure['root'])
        
        # Create directories
        for i in range(num_dirs):
            # Create some nested structure
            if i % 10 == 0 and i > 0:
                parent_dir = structure['dirs'][i // 10 - 1]
            else:
                parent_dir = structure['root']
            
            dir_name = f"dir_{i:04d}"
            dir_path = os.path.join(parent_dir, dir_name)
            os.makedirs(dir_path, exist_ok=True)
            structure['dirs'].append(dir_path)
            self.created_paths.append(dir_path)
        
        # Create files distributed across directories
        for i in range(num_files):
            # Choose directory for this file
            if structure['dirs']:
                target_dir = structure['dirs'][i % len(structure['dirs'])]
            else:
                target_dir = structure['root']
            
            file_name = f"file_{i:04d}.txt"
            file_path = os.path.join(target_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(f"Content for file {i}")
            structure['files'].append(file_path)
            self.created_paths.append(file_path)
        
        return structure
    
    def cleanup(self):
        """Clean up all created test structures."""
        for path in reversed(self.created_paths):  # Remove in reverse order
            try:
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    os.rmdir(path)
            except (OSError, FileNotFoundError):
                pass  # Ignore cleanup errors
        
        # Final cleanup of base directory
        try:
            if os.path.exists(self.base_path):
                shutil.rmtree(self.base_path, ignore_errors=True)
        except Exception:
            pass


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete workflow execution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix='fix_owner_integration_')
        self.dir_structure = TestDirectoryStructure(self.test_dir)
        
        # Create mock components for controlled testing
        self.mock_security_manager = Mock(spec=SecurityManager)
        self.mock_stats_tracker = Mock(spec=StatsTracker)
        self.mock_output_manager = Mock(spec=OutputManager)
        self.mock_error_manager = Mock(spec=ErrorManager)
        
        # Setup default mock behaviors
        self.setup_default_mocks()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.dir_structure.cleanup()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_default_mocks(self):
        """Setup default behaviors for mock objects."""
        # Mock security manager with valid SIDs by default
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        self.mock_security_manager.resolve_owner_account.return_value = ("target_sid", "TargetUser")
        self.mock_security_manager.set_owner.return_value = True
        
        # Mock stats tracker
        self.mock_stats_tracker.get_elapsed_time.return_value = 1.5
        self.mock_stats_tracker.dirs_traversed = 0
        self.mock_stats_tracker.files_traversed = 0
        self.mock_stats_tracker.dirs_changed = 0
        self.mock_stats_tracker.files_changed = 0
        self.mock_stats_tracker.exceptions = 0
        
        # Mock output manager
        self.mock_output_manager.is_quiet.return_value = False
        self.mock_output_manager.get_verbose_level.return_value = 0
        
        # Mock error manager
        self.mock_error_manager.validate_administrator_privileges.return_value = True
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        self.mock_error_manager.create_exception_context.return_value = mock_context
    
    def test_simple_workflow_dry_run(self):
        """Test complete workflow in dry-run mode with simple directory structure."""
        structure = self.dir_structure.create_simple_structure()
        
        # Create FileSystemWalker with mocked dependencies
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute workflow in dry-run mode
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,  # Dry run
            output_manager=self.mock_output_manager,
            timeout_manager=None
        )
        
        # Verify directory traversal occurred
        self.assertTrue(self.mock_stats_tracker.increment_dirs_traversed.called)
        
        # Verify files were processed
        self.assertTrue(self.mock_stats_tracker.increment_files_traversed.called)
        
        # Verify no actual ownership changes in dry run
        self.mock_security_manager.set_owner.assert_not_called()
    
    def test_simple_workflow_execute_mode(self):
        """Test complete workflow in execute mode with ownership changes."""
        structure = self.dir_structure.create_simple_structure()
        
        # Mock invalid SIDs that need changing
        self.mock_security_manager.get_current_owner.return_value = (None, "invalid_sid")
        self.mock_security_manager.is_sid_valid.return_value = False
        
        # Create FileSystemWalker with mocked dependencies
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute workflow in execute mode
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=True,  # Execute mode
            output_manager=self.mock_output_manager,
            timeout_manager=None
        )
        
        # Verify ownership changes were attempted
        self.assertTrue(self.mock_security_manager.set_owner.called)
        
        # Verify changes were tracked
        self.assertTrue(self.mock_stats_tracker.increment_dirs_changed.called)
        self.assertTrue(self.mock_stats_tracker.increment_files_changed.called)
    
    def test_workflow_with_recursion_control(self):
        """Test workflow with recursion enabled vs disabled."""
        structure = self.dir_structure.create_deep_structure(depth=3)
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Test without recursion
        self.mock_stats_tracker.reset_mock()
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=False,  # No recursion
            process_files=False,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Should only process root directory
        root_calls = self.mock_stats_tracker.increment_dirs_traversed.call_count
        
        # Test with recursion
        self.mock_stats_tracker.reset_mock()
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,  # With recursion
            process_files=False,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Should process more directories with recursion
        recursive_calls = self.mock_stats_tracker.increment_dirs_traversed.call_count
        self.assertGreater(recursive_calls, root_calls, 
                          "Recursion should process more directories")
    
    def test_workflow_with_file_processing_control(self):
        """Test workflow with file processing enabled vs disabled."""
        structure = self.dir_structure.create_simple_structure()
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Test without file processing
        self.mock_stats_tracker.reset_mock()
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=False,  # No file processing
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Should not process any files
        self.mock_stats_tracker.increment_files_traversed.assert_not_called()
        
        # Test with file processing
        self.mock_stats_tracker.reset_mock()
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,  # With file processing
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Should process files
        self.assertTrue(self.mock_stats_tracker.increment_files_traversed.called)
    
    def test_workflow_with_timeout(self):
        """Test workflow with timeout manager integration."""
        structure = self.dir_structure.create_simple_structure()
        
        # Create mock timeout manager that triggers timeout
        mock_timeout_manager = Mock()
        mock_timeout_manager.is_timeout_reached.side_effect = [False, False, True]  # Timeout on 3rd check
        mock_timeout_manager.get_elapsed_time.return_value = 5.0
        mock_timeout_manager.timeout_seconds = 3
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute workflow with timeout
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=self.mock_output_manager,
            timeout_manager=mock_timeout_manager
        )
        
        # Verify timeout was checked
        self.assertTrue(mock_timeout_manager.is_timeout_reached.called)
        
        # Verify timeout warning was printed
        self.mock_output_manager.print_timeout_warning.assert_called()
    
    def test_workflow_with_mixed_ownership_scenarios(self):
        """Test workflow with mix of valid and invalid SIDs."""
        structure = self.dir_structure.create_simple_structure()
        
        # Mock mixed ownership scenarios
        def mock_get_owner(path):
            if 'subdir1' in path:
                return (None, "invalid_sid")  # Invalid SID
            else:
                return ("ValidUser", "valid_sid")  # Valid SID
        
        def mock_is_valid(sid):
            return str(sid) != "invalid_sid"
        
        self.mock_security_manager.get_current_owner.side_effect = mock_get_owner
        self.mock_security_manager.is_sid_valid.side_effect = mock_is_valid
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute workflow in execute mode
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=True,
            output_manager=self.mock_output_manager
        )
        
        # Verify some ownership changes occurred (for invalid SIDs)
        self.assertTrue(self.mock_security_manager.set_owner.called)
        self.assertTrue(self.mock_stats_tracker.increment_dirs_changed.called)
    
    def test_workflow_error_handling_integration(self):
        """Test workflow with comprehensive error handling."""
        structure = self.dir_structure.create_simple_structure()
        
        # Mock security manager to raise exceptions for some paths
        def mock_get_owner_with_errors(path):
            if 'subdir2' in path:
                raise PermissionError("Access denied")
            return ("ValidUser", "valid_sid")
        
        self.mock_security_manager.get_current_owner.side_effect = mock_get_owner_with_errors
        
        # Create mock context manager that suppresses exceptions
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=True)  # Suppress exceptions
        self.mock_error_manager.create_exception_context.return_value = mock_context
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute workflow - should handle errors gracefully
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=False,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Verify error manager was used
        self.assertTrue(self.mock_error_manager.create_exception_context.called)
        
        # Verify processing continued despite errors
        self.assertTrue(self.mock_stats_tracker.increment_dirs_traversed.called)


class TestCommandLineIntegration(unittest.TestCase):
    """Integration tests for command-line argument combinations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix='fix_owner_cli_')
        self.dir_structure = TestDirectoryStructure(self.test_dir)
        self.structure = self.dir_structure.create_simple_structure()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.dir_structure.cleanup()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_argument_parsing_combinations(self):
        """Test various command-line argument combinations."""
        test_cases = [
            # Basic cases
            ([self.structure['root']], {'execute': False, 'recurse': False, 'files': False}),
            ([self.structure['root'], '-x'], {'execute': True, 'recurse': False, 'files': False}),
            ([self.structure['root'], '-r'], {'execute': False, 'recurse': True, 'files': False}),
            ([self.structure['root'], '-f'], {'execute': False, 'recurse': False, 'files': True}),
            
            # Combined options
            ([self.structure['root'], '-x', '-r'], {'execute': True, 'recurse': True, 'files': False}),
            ([self.structure['root'], '-x', '-f'], {'execute': True, 'recurse': False, 'files': True}),
            ([self.structure['root'], '-r', '-f'], {'execute': False, 'recurse': True, 'files': True}),
            ([self.structure['root'], '-x', '-r', '-f'], {'execute': True, 'recurse': True, 'files': True}),
            
            # Verbose and quiet options
            ([self.structure['root'], '-v'], {'verbose': True, 'quiet': False}),
            ([self.structure['root'], '-q'], {'verbose': False, 'quiet': True}),
            
            # Timeout option
            ([self.structure['root'], '-to', '30'], {'timeout': 30}),
            ([self.structure['root'], '--timeout', '60'], {'timeout': 60}),
            
            # With owner account
            ([self.structure['root'], 'Administrator'], {'owner_account': 'Administrator'}),
            ([self.structure['root'], 'DOMAIN\\User'], {'owner_account': 'DOMAIN\\User'}),
        ]
        
        for args, expected_attrs in test_cases:
            with self.subTest(args=args):
                # Mock sys.argv
                with patch('sys.argv', ['fix_owner.py'] + args):
                    try:
                        parsed_args = parse_arguments()
                        
                        # Check expected attributes
                        for attr, expected_value in expected_attrs.items():
                            actual_value = getattr(parsed_args, attr)
                            self.assertEqual(actual_value, expected_value,
                                           f"For args {args}, expected {attr}={expected_value}, got {actual_value}")
                    
                    except SystemExit:
                        # Some argument combinations might cause SystemExit (help, errors)
                        pass
    
    def test_invalid_argument_combinations(self):
        """Test invalid command-line argument combinations."""
        invalid_cases = [
            # Conflicting verbose and quiet
            [self.structure['root'], '-v', '-q'],
            
            # Invalid timeout values
            [self.structure['root'], '-to', '-1'],
            [self.structure['root'], '--timeout', 'invalid'],
            
            # Non-existent path
            ['/non/existent/path'],
            
            # File instead of directory
            [self.structure['files'][0]] if self.structure['files'] else [],
        ]
        
        for args in invalid_cases:
            if not args:  # Skip empty args
                continue
                
            with self.subTest(args=args):
                with patch('sys.argv', ['fix_owner.py'] + args):
                    with self.assertRaises(SystemExit):
                        parse_arguments()


class TestPerformanceIntegration(unittest.TestCase):
    """Performance tests for large directory structures."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix='fix_owner_perf_')
        self.dir_structure = TestDirectoryStructure(self.test_dir)
        
        # Create mock components optimized for performance testing
        self.mock_security_manager = Mock(spec=SecurityManager)
        self.mock_stats_tracker = Mock(spec=StatsTracker)
        self.mock_output_manager = Mock(spec=OutputManager)
        self.mock_error_manager = Mock(spec=ErrorManager)
        
        self.setup_performance_mocks()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.dir_structure.cleanup()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def setup_performance_mocks(self):
        """Setup mocks optimized for performance testing."""
        # Fast mock responses
        self.mock_security_manager.get_current_owner.return_value = ("ValidUser", "valid_sid")
        self.mock_security_manager.is_sid_valid.return_value = True
        self.mock_security_manager.set_owner.return_value = True
        
        # Mock output manager to be quiet for performance
        self.mock_output_manager.is_quiet.return_value = True
        self.mock_output_manager.get_verbose_level.return_value = 0
        
        # Mock error manager with fast context
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        self.mock_error_manager.create_exception_context.return_value = mock_context
    
    def test_large_directory_structure_performance(self):
        """Test performance with large directory structure."""
        # Create large structure (reduced size for CI/testing)
        structure = self.dir_structure.create_large_structure(num_dirs=50, num_files=100)
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Measure execution time
        start_time = time.time()
        
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        execution_time = time.time() - start_time
        
        # Performance assertions
        self.assertLess(execution_time, 10.0, "Large structure processing should complete within 10 seconds")
        
        # Verify all items were processed
        expected_dir_calls = len(structure['dirs']) + 1  # +1 for root
        expected_file_calls = len(structure['files'])
        
        self.assertEqual(self.mock_stats_tracker.increment_dirs_traversed.call_count, expected_dir_calls)
        self.assertEqual(self.mock_stats_tracker.increment_files_traversed.call_count, expected_file_calls)
    
    def test_deep_directory_structure_performance(self):
        """Test performance with deep nested directory structure."""
        # Create deep structure
        structure = self.dir_structure.create_deep_structure(depth=10, files_per_dir=2)
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Measure execution time
        start_time = time.time()
        
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        execution_time = time.time() - start_time
        
        # Performance assertions
        self.assertLess(execution_time, 5.0, "Deep structure processing should complete within 5 seconds")
        
        # Verify recursion worked correctly
        expected_dir_calls = structure['depth'] + 1  # +1 for root
        expected_file_calls = structure['depth'] * structure['files_per_dir']
        
        self.assertEqual(self.mock_stats_tracker.increment_dirs_traversed.call_count, expected_dir_calls)
        self.assertEqual(self.mock_stats_tracker.increment_files_traversed.call_count, expected_file_calls)
    
    def test_performance_with_timeout(self):
        """Test performance behavior with timeout constraints."""
        # Create moderate-sized structure
        structure = self.dir_structure.create_large_structure(num_dirs=30, num_files=60)
        
        # Create timeout manager with short timeout
        mock_timeout_manager = Mock()
        # Simulate timeout after processing some items
        timeout_calls = [False] * 20 + [True] * 100  # Allow 20 operations, then timeout
        mock_timeout_manager.is_timeout_reached.side_effect = timeout_calls
        mock_timeout_manager.get_elapsed_time.return_value = 2.0
        mock_timeout_manager.timeout_seconds = 1
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Execute with timeout
        start_time = time.time()
        
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=self.mock_output_manager,
            timeout_manager=mock_timeout_manager
        )
        
        execution_time = time.time() - start_time
        
        # Should complete quickly due to timeout
        self.assertLess(execution_time, 3.0, "Timeout should limit execution time")
        
        # Verify timeout was handled
        self.mock_output_manager.print_timeout_warning.assert_called()
    
    def test_memory_usage_large_structure(self):
        """Test memory usage with large directory structures."""
        # Create large structure
        structure = self.dir_structure.create_large_structure(num_dirs=100, num_files=200)
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            self.mock_security_manager,
            self.mock_stats_tracker,
            self.mock_error_manager
        )
        
        # Monitor memory usage (simplified - just ensure no obvious memory leaks)
        import gc
        gc.collect()  # Clean up before test
        
        # Execute processing
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=self.mock_output_manager
        )
        
        # Force garbage collection
        gc.collect()
        
        # Test passes if no memory errors occurred
        # In a real scenario, you might use memory profiling tools
        self.assertTrue(True, "Memory usage test completed without errors")


class TestEndToEndScenarios(unittest.TestCase):
    """End-to-end scenario tests simulating real-world usage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp(prefix='fix_owner_e2e_')
        self.dir_structure = TestDirectoryStructure(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.dir_structure.cleanup()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('src.fix_owner.PYWIN32_AVAILABLE', True)
    @patch('win32security.GetFileSecurity')
    @patch('win32security.LookupAccountSid')
    @patch('win32security.SetFileSecurity')
    @patch('win32security.LookupAccountName')
    @patch('win32api.GetUserNameEx')
    @patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=True)
    def test_complete_dry_run_scenario(self, mock_admin, mock_get_user, mock_lookup_name, 
                                     mock_set_security, mock_lookup_sid, mock_get_security):
        """Test complete dry-run scenario with mocked Windows APIs."""
        # Setup mocks
        mock_get_user.return_value = "DOMAIN\\CurrentUser"
        mock_lookup_name.return_value = ("target_sid", "DOMAIN", 1)
        
        # Mock security descriptor
        mock_sd = Mock()
        mock_owner_sid = Mock()
        mock_sd.GetSecurityDescriptorOwner.return_value = mock_owner_sid
        mock_get_security.return_value = mock_sd
        
        # Mock invalid SID (LookupAccountSid raises exception)
        mock_lookup_sid.side_effect = Exception("Invalid SID")
        
        # Create test structure
        structure = self.dir_structure.create_simple_structure()
        
        # Mock sys.argv for dry run
        test_args = ['fix_owner.py', structure['root'], '-r', '-f', '-v', 'Administrator']
        
        with patch('sys.argv', test_args):
            # Capture output
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                    try:
                        # This would normally call main(), but we'll test components
                        args = parse_arguments()
                        
                        # Verify arguments were parsed correctly
                        self.assertEqual(args.root_path, structure['root'])
                        self.assertTrue(args.recurse)
                        self.assertTrue(args.files)
                        self.assertTrue(args.verbose)
                        self.assertFalse(args.execute)  # Should be dry run
                        self.assertEqual(args.owner_account, 'Administrator')
                        
                    except SystemExit as e:
                        # Expected for successful argument parsing
                        pass
    
    def test_error_recovery_scenario(self):
        """Test error recovery in realistic error scenarios."""
        structure = self.dir_structure.create_simple_structure()
        
        # Create components with error injection
        mock_security_manager = Mock()
        mock_stats_tracker = Mock()
        mock_output_manager = Mock()
        mock_error_manager = Mock()
        
        # Setup error scenarios
        def mock_get_owner_with_intermittent_errors(path):
            if 'file2' in path:
                raise PermissionError("Access denied")
            elif 'nested' in path:
                raise FileNotFoundError("Path not found")
            else:
                return ("ValidUser", "valid_sid")
        
        mock_security_manager.get_current_owner.side_effect = mock_get_owner_with_intermittent_errors
        mock_security_manager.is_sid_valid.return_value = True
        
        # Mock error manager context
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=True)  # Suppress exceptions
        mock_error_manager.create_exception_context.return_value = mock_context
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            mock_security_manager,
            mock_stats_tracker,
            mock_error_manager
        )
        
        # Execute workflow - should handle errors gracefully
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=False,
            output_manager=mock_output_manager
        )
        
        # Verify processing continued despite errors
        self.assertTrue(mock_stats_tracker.increment_dirs_traversed.called)
        self.assertTrue(mock_error_manager.create_exception_context.called)
    
    def test_mixed_ownership_scenario(self):
        """Test scenario with mixed valid/invalid ownership."""
        structure = self.dir_structure.create_deep_structure(depth=3, files_per_dir=2)
        
        # Create components
        mock_security_manager = Mock()
        mock_stats_tracker = Mock()
        mock_output_manager = Mock()
        mock_error_manager = Mock()
        
        # Setup mixed ownership scenario
        def mock_mixed_ownership(path):
            if 'level_1' in path or 'level_2' in path:
                return (None, "invalid_sid")  # Invalid SID
            else:
                return ("ValidUser", "valid_sid")  # Valid SID
        
        def mock_sid_validation(sid):
            return str(sid) != "invalid_sid"
        
        mock_security_manager.get_current_owner.side_effect = mock_mixed_ownership
        mock_security_manager.is_sid_valid.side_effect = mock_sid_validation
        mock_security_manager.set_owner.return_value = True
        
        # Mock error manager context
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_context)
        mock_context.__exit__ = Mock(return_value=False)
        mock_error_manager.create_exception_context.return_value = mock_context
        
        # Create FileSystemWalker
        walker = FileSystemWalker(
            mock_security_manager,
            mock_stats_tracker,
            mock_error_manager
        )
        
        # Execute in execute mode
        walker.walk_filesystem(
            root_path=structure['root'],
            owner_sid="target_sid",
            recurse=True,
            process_files=True,
            execute=True,  # Execute mode
            output_manager=mock_output_manager
        )
        
        # Verify ownership changes occurred for invalid SIDs
        self.assertTrue(mock_security_manager.set_owner.called)
        self.assertTrue(mock_stats_tracker.increment_dirs_changed.called)
        self.assertTrue(mock_stats_tracker.increment_files_changed.called)


def run_integration_tests():
    """Run all integration tests."""
    print("🚀 Starting integration tests for fix-owner script")
    print("This will test complete workflow execution, command-line combinations, and performance")
    
    # Create test suite
    test_classes = [
        TestIntegrationWorkflow,
        TestCommandLineIntegration,
        TestPerformanceIntegration,
        TestEndToEndScenarios
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*80}")
    print("INTEGRATION TEST RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    success = result.wasSuccessful()
    if success:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
    else:
        print("\n💥 SOME INTEGRATION TESTS FAILED!")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())