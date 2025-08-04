#!/usr/bin/env python3
"""
Comprehensive test runner for all core functionality unit tests.

This script runs all unit tests for the fix-owner script core components:
- SecurityManager (Windows security operations with mocked pywin32 calls)
- StatsTracker (counting and reporting accuracy)
- Command-line argument parsing and validation
- FileSystemWalker (recursion and file processing logic)
- TimeoutManager (timeout detection and handling)
- ErrorManager (comprehensive error handling)
- OutputManager (output control and verbose logging)
"""

import sys
import os
import unittest
import time
from io import StringIO

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Import all test modules
try:
    from test_security_manager import TestSecurityManager
    from test_stats_tracker import TestStatsTracker
    from test_argument_parsing import TestArgumentParsing
    from test_filesystem_walker import TestFileSystemWalker
    from test_timeout_manager import TestTimeoutManager
    from test_error_manager import run_all_tests as run_error_manager_tests
    from test_output_manager import main as run_output_manager_tests
except ImportError as e:
    print(f"Error importing test modules: {e}")
    print("Make sure all test files are present in the current directory.")
    sys.exit(1)


class ResultsTracker:
    """Container for test results and statistics."""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.skipped_tests = 0
        self.test_results = {}
        self.start_time = time.time()
    
    def add_result(self, test_name, result):
        """Add a test result."""
        self.test_results[test_name] = result
        self.total_tests += result.testsRun
        self.failed_tests += len(result.failures)
        self.error_tests += len(result.errors)
        self.skipped_tests += len(result.skipped)
        self.passed_tests += (result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped))
    
    def get_elapsed_time(self):
        """Get elapsed time since start."""
        return time.time() - self.start_time
    
    def print_summary(self):
        """Print comprehensive test summary."""
        elapsed = self.get_elapsed_time()
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total tests run: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Errors: {self.error_tests}")
        print(f"Skipped: {self.skipped_tests}")
        print(f"Total execution time: {elapsed:.2f} seconds")
        print()
        
        # Print individual test suite results
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result.wasSuccessful() else "❌ FAILED"
            print(f"{test_name}: {status} ({result.testsRun} tests)")
            
            if result.failures:
                print(f"  Failures: {len(result.failures)}")
            if result.errors:
                print(f"  Errors: {len(result.errors)}")
            if result.skipped:
                print(f"  Skipped: {len(result.skipped)}")
        
        print("=" * 80)
        
        if self.failed_tests == 0 and self.error_tests == 0:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("💥 SOME TESTS FAILED!")
            return False


def run_unittest_suite(test_class, test_name):
    """
    Run a unittest test suite and return results.
    
    Args:
        test_class: The test class to run
        test_name: Name of the test for reporting
        
    Returns:
        unittest.TestResult object
    """
    print(f"\n{'='*60}")
    print(f"Running {test_name} tests...")
    print('='*60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    
    # Create test runner with custom stream to capture output
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    
    # Run tests
    result = runner.run(suite)
    
    # Print captured output
    output = stream.getvalue()
    if output:
        print(output)
    
    # Print summary for this test suite
    if result.wasSuccessful():
        print(f"✅ {test_name} tests: ALL PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ {test_name} tests: {len(result.failures)} failures, {len(result.errors)} errors")
        
        # Print failure details
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result


def run_legacy_test_function(test_function, test_name):
    """
    Run a legacy test function and return mock result.
    
    Args:
        test_function: Function to run
        test_name: Name of the test for reporting
        
    Returns:
        Mock result object with success status
    """
    print(f"\n{'='*60}")
    print(f"Running {test_name} tests...")
    print('='*60)
    
    try:
        exit_code = test_function()
        success = (exit_code == 0)
        
        # Create mock result object
        class MockResult:
            def __init__(self, success):
                self.testsRun = 8  # Approximate number of tests in legacy suites
                self.failures = [] if success else [("Legacy test", "Test failed")]
                self.errors = []
                self.skipped = []
            
            def wasSuccessful(self):
                return len(self.failures) == 0 and len(self.errors) == 0
        
        result = MockResult(success)
        return result
        
    except Exception as e:
        print(f"❌ {test_name} tests: ERROR - {e}")
        
        class MockResult:
            def __init__(self):
                self.testsRun = 1
                self.failures = []
                self.errors = [("Legacy test", str(e))]
                self.skipped = []
            
            def wasSuccessful(self):
                return False
        
        return MockResult()


def main():
    """Run all core functionality tests."""
    print("🚀 Starting comprehensive unit tests for fix-owner script core functionality")
    print("This will test all components with mocked dependencies for reliable testing")
    
    results = ResultsTracker()
    
    # Run unittest-based test suites
    unittest_tests = [
        (TestSecurityManager, "SecurityManager"),
        (TestStatsTracker, "StatsTracker"),
        (TestArgumentParsing, "Argument Parsing"),
        (TestFileSystemWalker, "FileSystemWalker"),
        (TestTimeoutManager, "TimeoutManager"),
    ]
    
    for test_class, test_name in unittest_tests:
        try:
            result = run_unittest_suite(test_class, test_name)
            results.add_result(test_name, result)
        except Exception as e:
            print(f"❌ Error running {test_name} tests: {e}")
            # Create mock failed result
            class MockResult:
                def __init__(self):
                    self.testsRun = 1
                    self.failures = []
                    self.errors = [("Test execution", str(e))]
                    self.skipped = []
                def wasSuccessful(self):
                    return False
            results.add_result(test_name, MockResult())
    
    # Run legacy test functions
    legacy_tests = [
        (run_error_manager_tests, "ErrorManager"),
        (run_output_manager_tests, "OutputManager"),
    ]
    
    # Add integration tests
    try:
        from test_integration import run_integration_tests
        legacy_tests.append((run_integration_tests, "Integration Tests"))
    except ImportError:
        print("⚠️  Integration tests not available - test_integration.py not found")
    
    for test_function, test_name in legacy_tests:
        try:
            result = run_legacy_test_function(test_function, test_name)
            results.add_result(test_name, result)
        except Exception as e:
            print(f"❌ Error running {test_name} tests: {e}")
            # Create mock failed result
            class MockResult:
                def __init__(self):
                    self.testsRun = 1
                    self.failures = []
                    self.errors = [("Test execution", str(e))]
                    self.skipped = []
                def wasSuccessful(self):
                    return False
            results.add_result(test_name, MockResult())
    
    # Print comprehensive summary
    success = results.print_summary()
    
    if success:
        print("\n🎯 All core functionality tests completed successfully!")
        print("The fix-owner script components are ready for integration testing.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the failures above.")
        print("Fix the issues before proceeding to integration testing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())