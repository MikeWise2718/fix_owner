#!/usr/bin/env python3
"""
Test suite for output directory functionality.

This module tests the new output directory management features including
directory creation, file path generation, and integration with existing
export functionality.
"""

import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from common import ensure_output_directory, get_output_file_path
from error_manager import ErrorManager
from sid_tracker import SidTracker, YAML_AVAILABLE
from output_manager import OutputManager


class TestOutputDirectoryUtilities(unittest.TestCase):
    """Test cases for output directory utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_ensure_output_directory_creates_directory(self):
        """Test that ensure_output_directory creates the output directory."""
        # Ensure output directory doesn't exist initially
        self.assertFalse(os.path.exists("output"))
        
        # Call the function
        result = ensure_output_directory()
        
        # Verify directory was created
        self.assertEqual(result, "output")
        self.assertTrue(os.path.exists("output"))
        self.assertTrue(os.path.isdir("output"))
    
    def test_ensure_output_directory_existing_directory(self):
        """Test that ensure_output_directory works with existing directory."""
        # Create output directory first
        os.makedirs("output")
        self.assertTrue(os.path.exists("output"))
        
        # Call the function
        result = ensure_output_directory()
        
        # Verify it still works
        self.assertEqual(result, "output")
        self.assertTrue(os.path.exists("output"))
        self.assertTrue(os.path.isdir("output"))
    
    def test_get_output_file_path_basic(self):
        """Test basic file path generation."""
        filename = "test_file.txt"
        result = get_output_file_path(filename)
        
        expected = os.path.join("output", filename)
        self.assertEqual(result, expected)
        
        # Verify output directory was created
        self.assertTrue(os.path.exists("output"))
    
    def test_get_output_file_path_with_subdirectory(self):
        """Test file path generation with subdirectory in filename."""
        filename = os.path.join("subdir", "test_file.txt")
        result = get_output_file_path(filename)
        
        expected = os.path.join("output", "subdir", "test_file.txt")
        self.assertEqual(result, expected)
    
    def test_get_output_file_path_multiple_calls(self):
        """Test multiple calls to get_output_file_path."""
        filenames = ["file1.txt", "file2.json", "file3.yaml"]
        results = []
        
        for filename in filenames:
            result = get_output_file_path(filename)
            results.append(result)
            expected = os.path.join("output", filename)
            self.assertEqual(result, expected)
        
        # Verify all paths are different
        self.assertEqual(len(set(results)), len(filenames))
        
        # Verify output directory exists
        self.assertTrue(os.path.exists("output"))


class TestErrorManagerOutputDirectory(unittest.TestCase):
    """Test cases for ErrorManager output directory integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        self.output_manager = OutputManager(verbose_level=1, quiet=False)
        self.error_manager = ErrorManager(
            stats_tracker=None,
            output_manager=self.output_manager,
            start_timestamp_str="20250804_114500"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_create_failure_log_filename_includes_output_directory(self):
        """Test that failure log filenames include output directory."""
        operation = "test_operation"
        result = self.error_manager.create_failure_log_filename(operation)
        
        expected_filename = "fix_owner_test_operation_20250804_114500.log"
        expected_path = os.path.join("output", expected_filename)
        
        self.assertEqual(result, expected_path)
        self.assertTrue(result.startswith("output" + os.sep))
    
    def test_create_failure_log_filename_with_custom_extension(self):
        """Test failure log filename creation with custom extension."""
        operation = "security_errors"
        extension = "txt"
        result = self.error_manager.create_failure_log_filename(operation, extension)
        
        expected_filename = "fix_owner_security_errors_20250804_114500.txt"
        expected_path = os.path.join("output", expected_filename)
        
        self.assertEqual(result, expected_path)
    
    def test_create_failure_log_filename_sanitizes_operation_name(self):
        """Test that operation names are properly sanitized."""
        operation = "test operation with spaces & special chars!"
        result = self.error_manager.create_failure_log_filename(operation)
        
        # Should contain sanitized operation name (only alphanumeric, underscore, hyphen)
        self.assertIn("testoperationwithspacesspecialchars", result)
        self.assertTrue(result.startswith("output" + os.sep))
    
    def test_write_failure_log_creates_file_in_output_directory(self):
        """Test that failure logs are written to output directory."""
        filename = self.error_manager.create_failure_log_filename("test_write")
        content = "Test log content"
        
        success = self.error_manager.write_failure_log(filename, content, append=False)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(filename))
        self.assertTrue(filename.startswith("output" + os.sep))
        
        # Verify content
        with open(filename, 'r', encoding='utf-8') as f:
            written_content = f.read().strip()
        self.assertEqual(written_content, content)
    
    def test_write_failure_log_creates_output_directory(self):
        """Test that write_failure_log creates output directory if needed."""
        # Ensure output directory doesn't exist
        if os.path.exists("output"):
            shutil.rmtree("output")
        
        filename = self.error_manager.create_failure_log_filename("test_create_dir")
        content = "Test content"
        
        success = self.error_manager.write_failure_log(filename, content, append=False)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists("output"))
        self.assertTrue(os.path.exists(filename))


class TestSidTrackerOutputDirectory(unittest.TestCase):
    """Test cases for SidTracker output directory integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        self.output_manager = OutputManager(verbose_level=1, quiet=False)
        self.sid_tracker = SidTracker(
            security_manager=None,
            start_timestamp_str="20250804_114500",
            target_owner_account="DOMAIN\\Administrator"
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_create_json_export_filename_includes_output_directory(self):
        """Test that JSON export filenames include output directory."""
        result = self.sid_tracker.create_json_export_filename()
        
        expected_filename = "sid_ownership_analysis_20250804_114500.json"
        expected_path = os.path.join("output", expected_filename)
        
        self.assertEqual(result, expected_path)
        self.assertTrue(result.startswith("output" + os.sep))
    
    def test_create_yaml_export_filename_includes_output_directory(self):
        """Test that YAML export filenames include output directory."""
        result = self.sid_tracker.create_yaml_export_filename()
        
        expected_filename = "sid_orphaned_remediation_20250804_114500.yaml"
        expected_path = os.path.join("output", expected_filename)
        
        self.assertEqual(result, expected_path)
        self.assertTrue(result.startswith("output" + os.sep))
    
    def test_export_to_json_creates_file_in_output_directory(self):
        """Test that JSON export creates file in output directory."""
        # Add some test data
        self.sid_tracker._sid_data["S-1-5-21-1234567890-1234567890-1234567890-1001"] = {
            'file_count': 15,
            'dir_count': 3,
            'account_name': 'TestUser',
            'is_valid': True,
            'sid_object': "S-1-5-21-1234567890-1234567890-1234567890-1001"
        }
        self.sid_tracker.total_files_tracked = 15
        self.sid_tracker.total_dirs_tracked = 3
        self.sid_tracker.unique_sids_found = 1
        self.sid_tracker.valid_sids_count = 1
        self.sid_tracker.orphaned_sids_count = 0
        
        success = self.sid_tracker.export_to_json(self.output_manager)
        
        self.assertTrue(success)
        
        json_filename = self.sid_tracker.create_json_export_filename()
        self.assertTrue(os.path.exists(json_filename))
        self.assertTrue(json_filename.startswith("output" + os.sep))
        
        # Verify it's valid JSON
        import json
        with open(json_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('summary', data)
        self.assertIn('sids', data)
    
    @unittest.skipIf(not YAML_AVAILABLE, "PyYAML not available")
    def test_export_orphaned_sids_to_yaml_creates_file_in_output_directory(self):
        """Test that YAML export creates file in output directory."""
        # Add orphaned SID data
        self.sid_tracker._sid_data["S-1-5-21-1234567890-1234567890-1234567890-1001"] = {
            'file_count': 15,
            'dir_count': 3,
            'account_name': None,
            'is_valid': False,  # Orphaned
            'sid_object': "S-1-5-21-1234567890-1234567890-1234567890-1001"
        }
        self.sid_tracker.total_files_tracked = 15
        self.sid_tracker.total_dirs_tracked = 3
        self.sid_tracker.unique_sids_found = 1
        self.sid_tracker.valid_sids_count = 0
        self.sid_tracker.orphaned_sids_count = 1
        
        success = self.sid_tracker.export_orphaned_sids_to_yaml(self.output_manager)
        
        self.assertTrue(success)
        
        yaml_filename = self.sid_tracker.create_yaml_export_filename()
        self.assertTrue(os.path.exists(yaml_filename))
        self.assertTrue(yaml_filename.startswith("output" + os.sep))
        
        # Verify it's valid YAML
        import yaml
        with open(yaml_filename, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        self.assertIn('metadata', data)
        self.assertIn('remediation_info', data)
        self.assertIn('orphaned_sids', data)
    
    def test_generate_report_creates_files_in_output_directory(self):
        """Test that generate_report creates files in output directory."""
        # Add test data
        self.sid_tracker._sid_data["S-1-5-21-1234567890-1234567890-1234567890-1001"] = {
            'file_count': 15,
            'dir_count': 3,
            'account_name': None,
            'is_valid': False,  # Orphaned
            'sid_object': "S-1-5-21-1234567890-1234567890-1234567890-1001"
        }
        self.sid_tracker.total_files_tracked = 15
        self.sid_tracker.total_dirs_tracked = 3
        self.sid_tracker.unique_sids_found = 1
        self.sid_tracker.valid_sids_count = 0
        self.sid_tracker.orphaned_sids_count = 1
        
        # Capture output to avoid cluttering test output
        with patch('sys.stdout', new_callable=StringIO):
            self.sid_tracker.generate_report(self.output_manager)
        
        # Verify JSON file was created
        json_filename = self.sid_tracker.create_json_export_filename()
        self.assertTrue(os.path.exists(json_filename))
        self.assertTrue(json_filename.startswith("output" + os.sep))
        
        # Verify YAML file was created (if YAML is available)
        if YAML_AVAILABLE:
            yaml_filename = self.sid_tracker.create_yaml_export_filename()
            self.assertTrue(os.path.exists(yaml_filename))
            self.assertTrue(yaml_filename.startswith("output" + os.sep))


class TestOutputDirectoryIntegration(unittest.TestCase):
    """Test cases for output directory integration across components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_multiple_components_use_same_output_directory(self):
        """Test that multiple components use the same output directory."""
        output_manager = OutputManager(verbose_level=1, quiet=False)
        
        # Create ErrorManager
        error_manager = ErrorManager(
            stats_tracker=None,
            output_manager=output_manager,
            start_timestamp_str="20250804_114500"
        )
        
        # Create SidTracker
        sid_tracker = SidTracker(
            security_manager=None,
            start_timestamp_str="20250804_114500",
            target_owner_account="DOMAIN\\Administrator"
        )
        
        # Get filenames from both components
        log_filename = error_manager.create_failure_log_filename("integration_test")
        json_filename = sid_tracker.create_json_export_filename()
        yaml_filename = sid_tracker.create_yaml_export_filename()
        
        # Verify all use the same output directory
        self.assertTrue(log_filename.startswith("output" + os.sep))
        self.assertTrue(json_filename.startswith("output" + os.sep))
        self.assertTrue(yaml_filename.startswith("output" + os.sep))
        
        # Verify output directory exists
        self.assertTrue(os.path.exists("output"))
    
    def test_output_directory_permissions(self):
        """Test that output directory has proper permissions."""
        output_dir = ensure_output_directory()
        
        # Verify directory is readable and writable
        self.assertTrue(os.access(output_dir, os.R_OK))
        self.assertTrue(os.access(output_dir, os.W_OK))
        
        # Test file creation
        test_file = get_output_file_path("permission_test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        self.assertTrue(os.path.exists(test_file))
    
    def test_output_directory_cleanup_behavior(self):
        """Test behavior when output directory is removed during execution."""
        # Create output directory and a file
        output_dir = ensure_output_directory()
        test_file = get_output_file_path("test_cleanup.txt")
        
        with open(test_file, 'w') as f:
            f.write("test content")
        
        self.assertTrue(os.path.exists(test_file))
        
        # Remove the entire output directory
        shutil.rmtree(output_dir)
        self.assertFalse(os.path.exists(output_dir))
        
        # Call ensure_output_directory again
        new_output_dir = ensure_output_directory()
        
        # Verify directory is recreated
        self.assertEqual(output_dir, new_output_dir)
        self.assertTrue(os.path.exists(output_dir))
        
        # Verify we can create files again
        new_test_file = get_output_file_path("test_recreate.txt")
        with open(new_test_file, 'w') as f:
            f.write("recreated content")
        
        self.assertTrue(os.path.exists(new_test_file))


class TestOutputDirectoryErrorHandling(unittest.TestCase):
    """Test cases for output directory error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('os.makedirs')
    def test_ensure_output_directory_handles_creation_failure(self, mock_makedirs):
        """Test handling of directory creation failure."""
        mock_makedirs.side_effect = OSError("Permission denied")
        
        # Should raise the exception
        with self.assertRaises(OSError):
            ensure_output_directory()
    
    def test_get_output_file_path_with_invalid_filename(self):
        """Test get_output_file_path with various filename inputs."""
        # Test with empty filename
        result = get_output_file_path("")
        expected = os.path.join("output", "")
        self.assertEqual(result, expected)
        
        # Test with filename containing path separators
        filename_with_sep = f"subdir{os.sep}file.txt"
        result = get_output_file_path(filename_with_sep)
        expected = os.path.join("output", filename_with_sep)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()