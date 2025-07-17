"""
Unit tests for TimeoutManager class - comprehensive timeout handling and detection testing.
"""

import time
import sys
import os
import unittest
import threading
from unittest.mock import Mock, patch

# Add current directory to path to import timeout_manager
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.timeout_manager import TimeoutManager


class TestTimeoutManager(unittest.TestCase):
    """Test cases for TimeoutManager class."""
    
    def test_no_timeout_initialization(self):
        """Test TimeoutManager initialization with no timeout."""
        tm = TimeoutManager(0)
        
        self.assertEqual(tm.timeout_seconds, 0)
        self.assertFalse(tm.timeout_reached)
        self.assertIsInstance(tm.start_time, float)
        self.assertIsNone(tm._timer)
    
    def test_timeout_initialization(self):
        """Test TimeoutManager initialization with timeout."""
        tm = TimeoutManager(30)
        
        self.assertEqual(tm.timeout_seconds, 30)
        self.assertFalse(tm.timeout_reached)
        self.assertIsInstance(tm.start_time, float)
        self.assertIsNone(tm._timer)
    
    def test_no_timeout_behavior(self):
        """Test TimeoutManager with no timeout set."""
        tm = TimeoutManager(0)
        
        self.assertFalse(tm.is_timeout_reached())
        self.assertEqual(tm.get_remaining_time(), float('inf'))
        self.assertTrue(tm.should_continue_processing())
        
        # Even after some time, should not timeout
        time.sleep(0.1)
        self.assertFalse(tm.is_timeout_reached())
        self.assertTrue(tm.should_continue_processing())
    
    def test_timeout_not_reached(self):
        """Test TimeoutManager before timeout is reached."""
        tm = TimeoutManager(2)  # 2 second timeout
        
        self.assertFalse(tm.is_timeout_reached())
        self.assertGreater(tm.get_remaining_time(), 1.5)
        self.assertTrue(tm.should_continue_processing())
        
        # Wait a bit but not enough to timeout
        time.sleep(0.5)
        self.assertFalse(tm.is_timeout_reached())
        self.assertTrue(tm.should_continue_processing())
        self.assertGreater(tm.get_remaining_time(), 1.0)
    
    def test_timeout_reached(self):
        """Test TimeoutManager after timeout is reached."""
        tm = TimeoutManager(1)  # 1 second timeout
        
        # Wait for timeout to be reached
        time.sleep(1.1)
        
        self.assertTrue(tm.is_timeout_reached())
        self.assertEqual(tm.get_remaining_time(), 0.0)
        self.assertFalse(tm.should_continue_processing())
    
    def test_elapsed_time_accuracy(self):
        """Test elapsed time calculation accuracy."""
        tm = TimeoutManager(10)
        
        # Initial elapsed time should be very small
        initial_elapsed = tm.get_elapsed_time()
        self.assertGreaterEqual(initial_elapsed, 0)
        self.assertLess(initial_elapsed, 0.1)
        
        # Wait and check elapsed time increased
        time.sleep(0.2)
        later_elapsed = tm.get_elapsed_time()
        self.assertGreater(later_elapsed, initial_elapsed)
        self.assertGreaterEqual(later_elapsed, 0.2)
    
    def test_remaining_time_calculation(self):
        """Test remaining time calculation."""
        tm = TimeoutManager(5)
        
        # Initially should have close to full time remaining
        remaining = tm.get_remaining_time()
        self.assertGreater(remaining, 4.5)
        self.assertLessEqual(remaining, 5.0)
        
        # After some time, remaining should decrease
        time.sleep(0.5)
        remaining_after = tm.get_remaining_time()
        self.assertLess(remaining_after, remaining)
        self.assertGreater(remaining_after, 4.0)
    
    def test_timeout_handler_callback(self):
        """Test timeout handler with callback."""
        callback_called = [False]
        callback_args = []
        
        def timeout_callback():
            callback_called[0] = True
            callback_args.append("called")
        
        tm = TimeoutManager(1)  # 1 second timeout
        tm.setup_timeout_handler(timeout_callback)
        
        # Verify timer was created
        self.assertIsNotNone(tm._timer)
        self.assertTrue(tm._timer.daemon)
        
        # Wait for timeout
        time.sleep(1.2)
        
        # Verify timeout was reached and callback was called
        self.assertTrue(tm.is_timeout_reached())
        self.assertTrue(callback_called[0])
        self.assertEqual(callback_args, ["called"])
    
    def test_timeout_handler_without_callback(self):
        """Test timeout handler without callback."""
        tm = TimeoutManager(1)
        tm.setup_timeout_handler()  # No callback
        
        # Should still create timer
        self.assertIsNotNone(tm._timer)
        
        # Wait for timeout
        time.sleep(1.2)
        
        # Should still reach timeout
        self.assertTrue(tm.is_timeout_reached())
    
    def test_timeout_handler_no_timeout_set(self):
        """Test timeout handler when no timeout is set."""
        tm = TimeoutManager(0)  # No timeout
        tm.setup_timeout_handler()
        
        # Should not create timer
        self.assertIsNone(tm._timer)
        self.assertFalse(tm.is_timeout_reached())
    
    def test_cancel_timeout(self):
        """Test canceling timeout timer."""
        tm = TimeoutManager(5)
        tm.setup_timeout_handler()
        
        # Verify timer was created
        self.assertIsNotNone(tm._timer)
        
        # Cancel timeout
        tm.cancel_timeout()
        
        # Timer should be cancelled (we can't easily test if it's cancelled,
        # but we can verify the method doesn't raise an exception)
        self.assertIsNotNone(tm._timer)  # Timer object still exists
    
    def test_cancel_timeout_no_timer(self):
        """Test canceling timeout when no timer exists."""
        tm = TimeoutManager(0)
        
        # Should not raise exception
        tm.cancel_timeout()
        self.assertIsNone(tm._timer)
    
    def test_reset_timer(self):
        """Test timer reset functionality."""
        tm = TimeoutManager(5)
        
        # Wait a bit
        time.sleep(0.5)
        elapsed_before = tm.get_elapsed_time()
        
        # Reset timer
        tm.reset_timer()
        elapsed_after = tm.get_elapsed_time()
        
        # Elapsed time should be reset
        self.assertLess(elapsed_after, elapsed_before)
        self.assertLess(elapsed_after, 0.1)
        self.assertFalse(tm.timeout_reached)
    
    def test_reset_timer_with_active_timer(self):
        """Test resetting timer when active timer exists."""
        tm = TimeoutManager(2)
        tm.setup_timeout_handler()
        
        # Wait a bit
        time.sleep(0.5)
        
        # Reset timer
        tm.reset_timer()
        
        # Should reset timeout status
        self.assertFalse(tm.timeout_reached)
        self.assertLess(tm.get_elapsed_time(), 0.1)
    
    def test_context_manager_entry_exit(self):
        """Test TimeoutManager as context manager."""
        with TimeoutManager(2) as tm:
            self.assertIsInstance(tm, TimeoutManager)
            self.assertEqual(tm.timeout_seconds, 2)
            self.assertFalse(tm.is_timeout_reached())
            self.assertTrue(tm.should_continue_processing())
        
        # After exiting context, timeout should be cancelled
        # (We can't easily verify this, but the method should complete without error)
    
    def test_context_manager_with_timeout_handler(self):
        """Test context manager with timeout handler."""
        callback_called = [False]
        
        def timeout_callback():
            callback_called[0] = True
        
        with TimeoutManager(1) as tm:
            tm.setup_timeout_handler(timeout_callback)
            self.assertIsNotNone(tm._timer)
            
            # Don't wait for timeout in context
            self.assertFalse(tm.is_timeout_reached())
        
        # Timer should be cleaned up after context exit
    
    def test_multiple_timeout_managers(self):
        """Test multiple independent TimeoutManager instances."""
        tm1 = TimeoutManager(2)
        tm2 = TimeoutManager(3)
        
        # Should be independent
        self.assertNotEqual(tm1.start_time, tm2.start_time)
        self.assertEqual(tm1.timeout_seconds, 2)
        self.assertEqual(tm2.timeout_seconds, 3)
        
        # Wait and check they behave independently
        time.sleep(0.5)
        
        elapsed1 = tm1.get_elapsed_time()
        elapsed2 = tm2.get_elapsed_time()
        
        # Should be approximately the same elapsed time
        self.assertAlmostEqual(elapsed1, elapsed2, delta=0.1)
        
        # But different remaining times
        remaining1 = tm1.get_remaining_time()
        remaining2 = tm2.get_remaining_time()
        self.assertLess(remaining1, remaining2)
    
    def test_timeout_edge_cases(self):
        """Test timeout edge cases."""
        # Negative timeout (should behave like no timeout)
        tm_negative = TimeoutManager(-1)
        self.assertFalse(tm_negative.is_timeout_reached())
        self.assertEqual(tm_negative.get_remaining_time(), float('inf'))
        
        # Very small timeout
        tm_small = TimeoutManager(0.1)
        time.sleep(0.15)
        self.assertTrue(tm_small.is_timeout_reached())
        self.assertEqual(tm_small.get_remaining_time(), 0.0)


def run_timeout_manager_tests():
    """Run all TimeoutManager tests."""
    print("Running TimeoutManager tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTimeoutManager)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_timeout_manager_tests())