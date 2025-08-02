#!/usr/bin/env python3
"""
Unit tests for StatsTracker class - execution statistics tracking and reporting.
"""

import sys
import unittest
import time
import io
import os

# Import the StatsTracker from src/stats_tracker.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.stats_tracker import StatsTracker


class TestStatsTracker(unittest.TestCase):
    """Test cases for StatsTracker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stats = StatsTracker()
    
    def test_initial_state(self):
        """Test StatsTracker initial state."""
        self.assertEqual(self.stats.dirs_traversed, 0)
        self.assertEqual(self.stats.files_traversed, 0)
        self.assertEqual(self.stats.dirs_changed, 0)
        self.assertEqual(self.stats.files_changed, 0)
        self.assertEqual(self.stats.exceptions, 0)
        self.assertIsInstance(self.stats.start_time, float)
        self.assertGreater(self.stats.start_time, 0)
    
    def test_increment_dirs_traversed(self):
        """Test incrementing directories traversed counter."""
        initial_count = self.stats.dirs_traversed
        
        self.stats.increment_dirs_traversed()
        self.assertEqual(self.stats.dirs_traversed, initial_count + 1)
        
        self.stats.increment_dirs_traversed()
        self.assertEqual(self.stats.dirs_traversed, initial_count + 2)
    
    def test_increment_files_traversed(self):
        """Test incrementing files traversed counter."""
        initial_count = self.stats.files_traversed
        
        self.stats.increment_files_traversed()
        self.assertEqual(self.stats.files_traversed, initial_count + 1)
        
        self.stats.increment_files_traversed()
        self.assertEqual(self.stats.files_traversed, initial_count + 2)
    
    def test_increment_dirs_changed(self):
        """Test incrementing directories changed counter."""
        initial_count = self.stats.dirs_changed
        
        self.stats.increment_dirs_changed()
        self.assertEqual(self.stats.dirs_changed, initial_count + 1)
        
        self.stats.increment_dirs_changed()
        self.assertEqual(self.stats.dirs_changed, initial_count + 2)
    
    def test_increment_files_changed(self):
        """Test incrementing files changed counter."""
        initial_count = self.stats.files_changed
        
        self.stats.increment_files_changed()
        self.assertEqual(self.stats.files_changed, initial_count + 1)
        
        self.stats.increment_files_changed()
        self.assertEqual(self.stats.files_changed, initial_count + 2)
    
    def test_increment_exceptions(self):
        """Test incrementing exceptions counter."""
        initial_count = self.stats.exceptions
        
        self.stats.increment_exceptions()
        self.assertEqual(self.stats.exceptions, initial_count + 1)
        
        self.stats.increment_exceptions()
        self.assertEqual(self.stats.exceptions, initial_count + 2)
    
    def test_get_elapsed_time(self):
        """Test elapsed time calculation."""
        # Get initial elapsed time (should be very small)
        initial_elapsed = self.stats.get_elapsed_time()
        self.assertGreaterEqual(initial_elapsed, 0)
        self.assertLess(initial_elapsed, 1.0)  # Should be less than 1 second
        
        # Wait a bit and check elapsed time increased
        time.sleep(0.1)
        later_elapsed = self.stats.get_elapsed_time()
        self.assertGreater(later_elapsed, initial_elapsed)
        self.assertGreaterEqual(later_elapsed, 0.1)
    
    def test_print_report_normal_mode(self):
        """Test printing report in normal mode."""
        # Set up some statistics
        self.stats.dirs_traversed = 100
        self.stats.files_traversed = 500
        self.stats.dirs_changed = 10
        self.stats.files_changed = 25
        self.stats.exceptions = 2
        
        # Capture output
        output_buffer = io.StringIO()
        
        # Redirect stdout temporarily
        original_stdout = sys.stdout
        sys.stdout = output_buffer
        
        try:
            self.stats.print_report(quiet=False)
            output_content = output_buffer.getvalue()
            
            # Verify report content
            self.assertIn("EXECUTION STATISTICS", output_content)
            self.assertIn("Directories traversed: 100", output_content)
            self.assertIn("Files traversed: 500", output_content)
            self.assertIn("Directory ownerships changed: 10", output_content)
            self.assertIn("File ownerships changed: 25", output_content)
            self.assertIn("Exceptions encountered: 2", output_content)
            self.assertIn("Total execution time:", output_content)
            self.assertIn("seconds", output_content)
            
            # Check formatting
            self.assertIn("=" * 50, output_content)
            
        finally:
            sys.stdout = original_stdout
    
    def test_print_report_quiet_mode(self):
        """Test printing report in quiet mode."""
        # Set up some statistics
        self.stats.dirs_traversed = 100
        self.stats.files_traversed = 500
        
        # Capture output
        output_buffer = io.StringIO()
        
        # Redirect stdout temporarily
        original_stdout = sys.stdout
        sys.stdout = output_buffer
        
        try:
            self.stats.print_report(quiet=True)
            output_content = output_buffer.getvalue()
            
            # Should be empty in quiet mode
            self.assertEqual(output_content, "")
            
        finally:
            sys.stdout = original_stdout
    
    def test_print_report_with_large_numbers(self):
        """Test printing report with large numbers (comma formatting)."""
        # Set up large statistics
        self.stats.dirs_traversed = 1234567
        self.stats.files_traversed = 9876543
        self.stats.dirs_changed = 123456
        self.stats.files_changed = 654321
        self.stats.exceptions = 12345
        
        # Capture output
        output_buffer = io.StringIO()
        
        # Redirect stdout temporarily
        original_stdout = sys.stdout
        sys.stdout = output_buffer
        
        try:
            self.stats.print_report(quiet=False)
            output_content = output_buffer.getvalue()
            
            # Verify comma formatting for large numbers
            self.assertIn("Directories traversed: 1,234,567", output_content)
            self.assertIn("Files traversed: 9,876,543", output_content)
            self.assertIn("Directory ownerships changed: 123,456", output_content)
            self.assertIn("File ownerships changed: 654,321", output_content)
            self.assertIn("Exceptions encountered: 12,345", output_content)
            
        finally:
            sys.stdout = original_stdout
    
    def test_multiple_operations_simulation(self):
        """Test simulating multiple operations and verifying counters."""
        # Simulate processing 50 directories and 200 files
        for _ in range(50):
            self.stats.increment_dirs_traversed()
        
        for _ in range(200):
            self.stats.increment_files_traversed()
        
        # Simulate some ownership changes
        for _ in range(10):
            self.stats.increment_dirs_changed()
        
        for _ in range(30):
            self.stats.increment_files_changed()
        
        # Simulate some exceptions
        for _ in range(5):
            self.stats.increment_exceptions()
        
        # Verify final counts
        self.assertEqual(self.stats.dirs_traversed, 50)
        self.assertEqual(self.stats.files_traversed, 200)
        self.assertEqual(self.stats.dirs_changed, 10)
        self.assertEqual(self.stats.files_changed, 30)
        self.assertEqual(self.stats.exceptions, 5)
    
    def test_elapsed_time_precision(self):
        """Test elapsed time precision and consistency."""
        # Record start time
        start_time = time.time()
        
        # Wait a known amount of time
        time.sleep(0.2)
        
        # Get elapsed time from stats tracker
        elapsed = self.stats.get_elapsed_time()
        actual_elapsed = time.time() - start_time
        
        # Should be approximately the same (within reasonable tolerance)
        self.assertAlmostEqual(elapsed, actual_elapsed, delta=0.1)
        self.assertGreaterEqual(elapsed, 0.2)
    
    def test_stats_independence(self):
        """Test that different StatsTracker instances are independent."""
        stats1 = StatsTracker()
        stats2 = StatsTracker()
        
        # Modify stats1
        stats1.increment_dirs_traversed()
        stats1.increment_files_changed()
        
        # Verify stats2 is unaffected
        self.assertEqual(stats2.dirs_traversed, 0)
        self.assertEqual(stats2.files_changed, 0)
        
        # Verify stats1 has changes
        self.assertEqual(stats1.dirs_traversed, 1)
        self.assertEqual(stats1.files_changed, 1)


def run_stats_tracker_tests():
    """Run all StatsTracker tests."""
    print("Running StatsTracker tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStatsTracker)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_stats_tracker_tests())