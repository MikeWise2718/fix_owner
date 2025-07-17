#!/usr/bin/env python3
"""
Unit tests for command-line argument parsing and validation.
"""

import sys
import unittest
import tempfile
import os
import shutil
from unittest.mock import patch

# Import the parse_arguments function from src/fix_owner.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.fix_owner import parse_arguments


class TestArgumentParsing(unittest.TestCase):
    """Test cases for command-line argument parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "testfile.txt")
        with open(self.test_file, 'w') as f:
            f.write("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_minimal_arguments(self):
        """Test parsing with minimal required arguments."""
        test_args = [self.test_dir]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            self.assertEqual(args.root_path, self.test_dir)
            self.assertIsNone(args.owner_account)
            self.assertFalse(args.execute)
            self.assertFalse(args.recurse)
            self.assertFalse(args.files)
            self.assertFalse(args.verbose)
            self.assertFalse(args.quiet)
            self.assertEqual(args.timeout, 0)
    
    def test_all_arguments(self):
        """Test parsing with all arguments specified."""
        test_args = [
            self.test_dir, 'Administrator',
            '-x', '-r', '-f', '-v', '-ts', '300'
        ]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            self.assertEqual(args.root_path, self.test_dir)
            self.assertEqual(args.owner_account, 'Administrator')
            self.assertTrue(args.execute)
            self.assertTrue(args.recurse)
            self.assertTrue(args.files)
            self.assertTrue(args.verbose)
            self.assertFalse(args.quiet)
            self.assertEqual(args.timeout, 300)
    
    def test_long_form_arguments(self):
        """Test parsing with long-form arguments."""
        test_args = [
            self.test_dir, 'TestUser',
            '--execute', '--recurse', '--files', '--verbose', '--timeout', '600'
        ]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            self.assertEqual(args.root_path, self.test_dir)
            self.assertEqual(args.owner_account, 'TestUser')
            self.assertTrue(args.execute)
            self.assertTrue(args.recurse)
            self.assertTrue(args.files)
            self.assertTrue(args.verbose)
            self.assertEqual(args.timeout, 600)
    
    def test_quiet_mode(self):
        """Test parsing with quiet mode."""
        test_args = [self.test_dir, '-q']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            self.assertTrue(args.quiet)
            self.assertFalse(args.verbose)
    
    def test_verbose_and_quiet_conflict(self):
        """Test that verbose and quiet options conflict."""
        test_args = [self.test_dir, '-v', '-q']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_negative_timeout(self):
        """Test that negative timeout values are rejected."""
        test_args = [self.test_dir, '-ts', '-10']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_nonexistent_path(self):
        """Test that nonexistent paths are rejected."""
        nonexistent_path = "/this/path/does/not/exist"
        test_args = [nonexistent_path]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_file_instead_of_directory(self):
        """Test that files are rejected when directory is expected."""
        test_args = [self.test_file]  # Use file instead of directory
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_zero_timeout(self):
        """Test that zero timeout is valid (no timeout)."""
        test_args = [self.test_dir, '-ts', '0']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            self.assertEqual(args.timeout, 0)
    
    def test_help_option(self):
        """Test that help option exits gracefully."""
        test_args = ['--help']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit) as context:
                parse_arguments()
            # Help should exit with code 0
            self.assertEqual(context.exception.code, 0)
    
    def test_missing_required_argument(self):
        """Test that missing required root_path argument is rejected."""
        test_args = []  # No arguments
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_timeout_with_string_value(self):
        """Test timeout parsing with string values."""
        test_args = [self.test_dir, '-ts', '120']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            self.assertEqual(args.timeout, 120)
            self.assertIsInstance(args.timeout, int)
    
    def test_invalid_timeout_value(self):
        """Test that invalid timeout values are rejected."""
        test_args = [self.test_dir, '-ts', 'invalid']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    def test_owner_account_optional(self):
        """Test that owner account is optional."""
        test_args = [self.test_dir, '-x']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            self.assertIsNone(args.owner_account)
            self.assertTrue(args.execute)
    
    def test_owner_account_with_spaces(self):
        """Test owner account names with spaces."""
        test_args = [self.test_dir, 'Domain User', '-x']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            self.assertEqual(args.owner_account, 'Domain User')
    
    def test_argument_order_independence(self):
        """Test that argument order doesn't matter."""
        test_args1 = [self.test_dir, 'TestUser', '-x', '-r', '-f']
        test_args2 = ['-x', '-r', '-f', self.test_dir, 'TestUser']
        
        with patch('sys.argv', ['fix_owner.py'] + test_args1):
            args1 = parse_arguments()
        
        with patch('sys.argv', ['fix_owner.py'] + test_args2):
            args2 = parse_arguments()
        
        # Should parse the same regardless of order
        self.assertEqual(args1.root_path, args2.root_path)
        self.assertEqual(args1.owner_account, args2.owner_account)
        self.assertEqual(args1.execute, args2.execute)
        self.assertEqual(args1.recurse, args2.recurse)
        self.assertEqual(args1.files, args2.files)
    
    def test_boolean_flag_defaults(self):
        """Test that boolean flags default to False."""
        test_args = [self.test_dir]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            # All boolean flags should default to False
            self.assertFalse(args.execute)
            self.assertFalse(args.recurse)
            self.assertFalse(args.files)
            self.assertFalse(args.verbose)
            self.assertFalse(args.quiet)
    
    def test_mixed_short_and_long_options(self):
        """Test mixing short and long option forms."""
        test_args = [
            self.test_dir, 'TestUser',
            '-x', '--recurse', '-f', '--verbose', '--timeout', '180'
        ]
        
        with patch('sys.argv', ['fix_owner.py'] + test_args):
            args = parse_arguments()
            
            self.assertTrue(args.execute)
            self.assertTrue(args.recurse)
            self.assertTrue(args.files)
            self.assertTrue(args.verbose)
            self.assertEqual(args.timeout, 180)


def run_argument_parsing_tests():
    """Run all argument parsing tests."""
    print("Running argument parsing tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestArgumentParsing)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_argument_parsing_tests())