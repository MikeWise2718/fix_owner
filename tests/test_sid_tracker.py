#!/usr/bin/env python3
"""
Test suite for SidTracker functionality.

This module provides comprehensive testing for the SID tracking and reporting
functionality, including SID resolution, tracking accuracy, and report generation.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sid_tracker import SidTracker


class TestSidTracker(unittest.TestCase):
    """Test cases for SidTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_security_manager = Mock()
        self.sid_tracker = SidTracker(security_manager=self.mock_security_manager)
        
        # Mock SID objects
        self.mock_valid_sid = Mock()
        self.mock_valid_sid.__str__ = Mock(return_value="S-1-5-21-1234567890-1234567890-1234567890-1001")
        
        self.mock_orphaned_sid = Mock()
        self.mock_orphaned_sid.__str__ = Mock(return_value="S-1-5-21-9876543210-9876543210-9876543210-2001")
        
        self.mock_unknown_sid = Mock()
        self.mock_unknown_sid.__str__ = Mock(return_value="S-1-5-21-5555555555-5555555555-5555555555-3001")
    
    def test_initialization(self):
        """Test SidTracker initialization."""
        tracker = SidTracker()
        self.assertIsNone(tracker.security_manager)
        self.assertEqual(tracker.total_files_tracked, 0)
        self.assertEqual(tracker.total_dirs_tracked, 0)
        self.assertEqual(tracker.unique_sids_found, 0)
        self.assertEqual(tracker.valid_sids_count, 0)
        self.assertEqual(tracker.orphaned_sids_count, 0)
        
        tracker_with_sm = SidTracker(security_manager=self.mock_security_manager)
        self.assertEqual(tracker_with_sm.security_manager, self.mock_security_manager)
    
    @patch('sid_tracker.win32security')
    def test_track_file_sid_valid(self, mock_win32security):
        """Test tracking a valid SID for a file."""
        # Setup mocks
        self.mock_security_manager.is_sid_valid.return_value = True
        mock_win32security.LookupAccountSid.return_value = ("TestUser", "DOMAIN", 1)
        
        # Track the SID
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        
        # Verify tracking
        self.assertEqual(self.sid_tracker.total_files_tracked, 1)
        self.assertEqual(self.sid_tracker.total_dirs_tracked, 0)
        self.assertEqual(self.sid_tracker.unique_sids_found, 1)
        self.assertEqual(self.sid_tracker.valid_sids_count, 1)
        self.assertEqual(self.sid_tracker.orphaned_sids_count, 0)
        
        # Verify SID data
        sid_string = str(self.mock_valid_sid)
        self.assertIn(sid_string, self.sid_tracker._sid_data)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['file_count'], 1)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['dir_count'], 0)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['account_name'], "DOMAIN\\TestUser")
        self.assertTrue(self.sid_tracker._sid_data[sid_string]['is_valid'])
    
    def test_track_directory_sid_orphaned(self):
        """Test tracking an orphaned SID for a directory."""
        # Setup mocks
        self.mock_security_manager.is_sid_valid.return_value = False
        
        # Track the SID
        self.sid_tracker.track_directory_sid("/test/dir", self.mock_orphaned_sid)
        
        # Verify tracking
        self.assertEqual(self.sid_tracker.total_files_tracked, 0)
        self.assertEqual(self.sid_tracker.total_dirs_tracked, 1)
        self.assertEqual(self.sid_tracker.unique_sids_found, 1)
        self.assertEqual(self.sid_tracker.valid_sids_count, 0)
        self.assertEqual(self.sid_tracker.orphaned_sids_count, 1)
        
        # Verify SID data
        sid_string = str(self.mock_orphaned_sid)
        self.assertIn(sid_string, self.sid_tracker._sid_data)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['file_count'], 0)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['dir_count'], 1)
        self.assertIn("Orphaned SID", self.sid_tracker._sid_data[sid_string]['account_name'])
        self.assertFalse(self.sid_tracker._sid_data[sid_string]['is_valid'])
    
    def test_track_multiple_occurrences_same_sid(self):
        """Test tracking multiple occurrences of the same SID."""
        # Setup mocks
        self.mock_security_manager.is_sid_valid.return_value = True
        
        # Track the same SID multiple times
        self.sid_tracker.track_file_sid("/test/file1.txt", self.mock_valid_sid)
        self.sid_tracker.track_file_sid("/test/file2.txt", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir1", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir2", self.mock_valid_sid)
        
        # Verify tracking
        self.assertEqual(self.sid_tracker.total_files_tracked, 2)
        self.assertEqual(self.sid_tracker.total_dirs_tracked, 2)
        self.assertEqual(self.sid_tracker.unique_sids_found, 1)  # Only one unique SID
        
        # Verify SID data
        sid_string = str(self.mock_valid_sid)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['file_count'], 2)
        self.assertEqual(self.sid_tracker._sid_data[sid_string]['dir_count'], 2)
    
    def test_track_multiple_different_sids(self):
        """Test tracking multiple different SIDs."""
        # Setup mocks
        self.mock_security_manager.is_sid_valid.side_effect = [True, False]
        
        # Track different SIDs
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir", self.mock_orphaned_sid)
        
        # Verify tracking
        self.assertEqual(self.sid_tracker.total_files_tracked, 1)
        self.assertEqual(self.sid_tracker.total_dirs_tracked, 1)
        self.assertEqual(self.sid_tracker.unique_sids_found, 2)
        self.assertEqual(self.sid_tracker.valid_sids_count, 1)
        self.assertEqual(self.sid_tracker.orphaned_sids_count, 1)
    
    def test_track_sid_error_handling(self):
        """Test error handling during SID tracking."""
        # Setup mock to raise exception
        self.mock_valid_sid.__str__.side_effect = Exception("SID conversion error")
        
        # Create output manager mock for error reporting
        mock_output = Mock()
        self.sid_tracker._output_manager = mock_output
        
        # Track SID that will cause error
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        
        # Verify error was handled gracefully
        self.assertEqual(self.sid_tracker.total_files_tracked, 0)  # Should not increment on error
        mock_output.print_general_error.assert_called_once()
    
    def test_generate_report_no_data(self):
        """Test report generation with no SID data."""
        # Capture output
        with patch('builtins.print') as mock_print:
            self.sid_tracker.generate_report()
            mock_print.assert_called_with("No SID data collected.")
    
    @patch('sid_tracker.win32security')
    def test_generate_report_with_data(self, mock_win32security):
        """Test report generation with SID data."""
        # Setup mocks
        self.mock_security_manager.is_sid_valid.side_effect = [True, False]
        mock_win32security.LookupAccountSid.return_value = ("Administrator", "BUILTIN", 1)
        
        # Add some test data
        self.sid_tracker.track_file_sid("/test/file1.txt", self.mock_valid_sid)
        self.sid_tracker.track_file_sid("/test/file2.txt", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir1", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir2", self.mock_orphaned_sid)
        
        # Capture output
        output_lines = []
        def capture_print(*args, **kwargs):
            output_lines.append(str(args[0]) if args else "")
        
        with patch('builtins.print', side_effect=capture_print):
            self.sid_tracker.generate_report()
        
        # Verify report content
        report_text = "\n".join(output_lines)
        self.assertIn("SID OWNERSHIP ANALYSIS REPORT", report_text)
        self.assertIn("Total files analyzed: 2", report_text)
        self.assertIn("Total directories analyzed: 2", report_text)
        self.assertIn("Unique SIDs found: 2", report_text)
        self.assertIn("Valid SIDs: 1", report_text)
        self.assertIn("Orphaned SIDs: 1", report_text)
        self.assertIn("BUILTIN\\Administrator", report_text)
        self.assertIn("Orphaned SID", report_text)
    
    def test_generate_report_with_output_manager(self):
        """Test report generation with OutputManager."""
        # Setup mock output manager
        mock_output = Mock()
        
        # Add some test data
        self.mock_security_manager.is_sid_valid.return_value = True
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        
        # Generate report
        self.sid_tracker.generate_report(output_manager=mock_output)
        
        # Verify OutputManager was used
        self.assertTrue(mock_output.print_general_message.called)
        # Should have multiple calls for different parts of the report
        self.assertGreater(mock_output.print_general_message.call_count, 5)
    
    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        # Add some test data
        self.mock_security_manager.is_sid_valid.side_effect = [True, False]
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        self.sid_tracker.track_directory_sid("/test/dir", self.mock_orphaned_sid)
        
        # Get summary stats
        stats = self.sid_tracker.get_summary_stats()
        
        # Verify stats
        expected_stats = {
            'total_files_tracked': 1,
            'total_dirs_tracked': 1,
            'unique_sids_found': 2,
            'valid_sids_count': 1,
            'orphaned_sids_count': 1
        }
        self.assertEqual(stats, expected_stats)
    
    def test_sid_resolution_without_security_manager(self):
        """Test SID resolution when no SecurityManager is available."""
        # Create tracker without security manager
        tracker = SidTracker()
        
        # Track a SID
        tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        
        # Verify limited functionality
        self.assertEqual(tracker.total_files_tracked, 1)
        self.assertEqual(tracker.unique_sids_found, 1)
        self.assertEqual(tracker.valid_sids_count, 0)  # Can't determine validity
        self.assertEqual(tracker.orphaned_sids_count, 0)
        
        # Verify SID data has limited info
        sid_string = str(self.mock_valid_sid)
        self.assertIn(sid_string, tracker._sid_data)
        self.assertIsNone(tracker._sid_data[sid_string]['is_valid'])
        self.assertIn("SID:", tracker._sid_data[sid_string]['account_name'])
    
    @patch('sid_tracker.win32security')
    def test_sid_resolution_name_lookup_failure(self, mock_win32security):
        """Test SID resolution when name lookup fails but SID is valid."""
        # Setup mocks - SID is valid but name lookup fails
        self.mock_security_manager.is_sid_valid.return_value = True
        mock_win32security.LookupAccountSid.side_effect = Exception("Name lookup failed")
        
        # Track the SID
        self.sid_tracker.track_file_sid("/test/file.txt", self.mock_valid_sid)
        
        # Verify SID is tracked as valid but with fallback name
        self.assertEqual(self.sid_tracker.valid_sids_count, 1)
        sid_string = str(self.mock_valid_sid)
        self.assertTrue(self.sid_tracker._sid_data[sid_string]['is_valid'])
        self.assertIn("Valid SID:", self.sid_tracker._sid_data[sid_string]['account_name'])


class TestSidTrackerIntegration(unittest.TestCase):
    """Integration tests for SidTracker with other components."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.mock_security_manager = Mock()
        self.sid_tracker = SidTracker(security_manager=self.mock_security_manager)
    
    def test_integration_with_filesystem_walker(self):
        """Test SidTracker integration with FileSystemWalker workflow."""
        # This test simulates the workflow that would occur in FileSystemWalker
        
        # Setup mock SIDs for different scenarios
        valid_sid = Mock()
        valid_sid.__str__ = Mock(return_value="S-1-5-21-1111111111-1111111111-1111111111-1001")
        
        orphaned_sid = Mock()
        orphaned_sid.__str__ = Mock(return_value="S-1-5-21-2222222222-2222222222-2222222222-2001")
        
        # Setup security manager responses
        self.mock_security_manager.is_sid_valid.side_effect = [True, False, True, False]
        
        # Simulate filesystem processing
        self.sid_tracker.track_directory_sid("/root", valid_sid)
        self.sid_tracker.track_directory_sid("/root/orphaned_dir", orphaned_sid)
        self.sid_tracker.track_file_sid("/root/file1.txt", valid_sid)
        self.sid_tracker.track_file_sid("/root/orphaned_file.txt", orphaned_sid)
        
        # Verify comprehensive tracking
        self.assertEqual(self.sid_tracker.total_files_tracked, 2)
        self.assertEqual(self.sid_tracker.total_dirs_tracked, 2)
        self.assertEqual(self.sid_tracker.unique_sids_found, 2)
        self.assertEqual(self.sid_tracker.valid_sids_count, 1)
        self.assertEqual(self.sid_tracker.orphaned_sids_count, 1)
        
        # Verify individual SID tracking
        valid_sid_str = str(valid_sid)
        orphaned_sid_str = str(orphaned_sid)
        
        self.assertEqual(self.sid_tracker._sid_data[valid_sid_str]['file_count'], 1)
        self.assertEqual(self.sid_tracker._sid_data[valid_sid_str]['dir_count'], 1)
        self.assertEqual(self.sid_tracker._sid_data[orphaned_sid_str]['file_count'], 1)
        self.assertEqual(self.sid_tracker._sid_data[orphaned_sid_str]['dir_count'], 1)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)