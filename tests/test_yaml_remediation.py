#!/usr/bin/env python3
"""
Test suite for YAML remediation functionality in fix-owner script.

This module tests the ability to read remediation plans from YAML files
and use the new_owner_account parameter for ownership changes.

Test Coverage:
- YAML file reading and parsing
- new_owner_account extraction
- Integration with argument parsing
- Error handling for invalid YAML files
- Validation of argument combinations
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Import the modules to test
import fix_owner
from fix_owner import load_yaml_remediation, parse_arguments
from output_manager import OutputManager


class TestYAMLRemediation(unittest.TestCase):
    """Test YAML remediation file functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_output = Mock(spec=OutputManager)
        self.mock_output.get_verbose_level.return_value = 1
        self.mock_output.print_general_message = Mock()
        self.mock_output.print_info_pair = Mock()
        self.mock_output.print_general_error = Mock()
        
        # Sample YAML content for testing
        self.valid_yaml_content = """
orphaned_sids:
  - sid_info:
      sid: "S-1-5-21-1234567890-1234567890-1234567890-1001"
      account_name: "<Unknown SID: S-1-5-21-1234567890-1234567890-1234567890-1001>"
      status: "ORPHANED"
      description: "SID does not correspond to any existing account"
    impact_analysis:
      files_affected: 15
      directories_affected: 3
      total_items_affected: 18
      file_percentage: 83.33
      directory_percentage: 16.67
      remediation_priority: "HIGH"
    recommended_remediation:
      new_owner_account: "TestUser"
      action_required: "Change ownership to specified account"
      command_example: 'python fix_owner.py <path> -x -r -f "TestUser"'
      verification_steps:
        - "Run with dry-run mode first (without -x flag)"
        - "Verify the target account exists and is accessible"
        - "Apply changes with -x flag"
        - "Verify ownership changes were successful"
    additional_info:
      sid_type: "User Account"
      likely_cause: "User account was deleted"
      risk_assessment: "High risk - many files affected"
"""
    
    @unittest.skipUnless(YAML_AVAILABLE, "PyYAML not available")
    def test_load_yaml_remediation_success(self):
        """Test successful YAML remediation file loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.valid_yaml_content)
            yaml_file = f.name
        
        try:
            # Change to the directory containing the YAML file
            original_cwd = os.getcwd()
            yaml_dir = os.path.dirname(yaml_file)
            yaml_filename = os.path.basename(yaml_file)
            os.chdir(yaml_dir)
            
            result = load_yaml_remediation(yaml_filename, self.mock_output)
            
            self.assertEqual(result, "TestUser")
            self.mock_output.print_general_message.assert_called()
            self.mock_output.print_info_pair.assert_called()
            
        finally:
            os.chdir(original_cwd)
            os.unlink(yaml_file)
    
    @unittest.skipUnless(YAML_AVAILABLE, "PyYAML not available")
    def test_load_yaml_remediation_file_not_found(self):
        """Test YAML file not found error handling."""
        with patch('fix_owner.safe_exit') as mock_exit:
            load_yaml_remediation('nonexistent.yaml', self.mock_output)
            
            self.mock_output.print_general_error.assert_called_with(
                unittest.mock.ANY  # The error message will contain the full path
            )
            # safe_exit should be called at least once
            self.assertTrue(mock_exit.called)
    
    @unittest.skipUnless(YAML_AVAILABLE, "PyYAML not available")
    def test_load_yaml_remediation_invalid_yaml(self):
        """Test invalid YAML content error handling."""
        invalid_yaml = "invalid: yaml: content: ["
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            yaml_file = f.name
        
        try:
            original_cwd = os.getcwd()
            yaml_dir = os.path.dirname(yaml_file)
            yaml_filename = os.path.basename(yaml_file)
            os.chdir(yaml_dir)
            
            with patch('fix_owner.safe_exit') as mock_exit:
                load_yaml_remediation(yaml_filename, self.mock_output)
                
                self.mock_output.print_general_error.assert_called()
                mock_exit.assert_called_once()
                
        finally:
            os.chdir(original_cwd)
            os.unlink(yaml_file)
    
    @unittest.skipUnless(YAML_AVAILABLE, "PyYAML not available")
    def test_load_yaml_remediation_missing_new_owner_account(self):
        """Test YAML file missing new_owner_account."""
        yaml_without_owner = """
orphaned_sids:
  - sid_info:
      sid: "S-1-5-21-1234567890-1234567890-1234567890-1001"
    recommended_remediation:
      action_required: "Change ownership to specified account"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_without_owner)
            yaml_file = f.name
        
        try:
            original_cwd = os.getcwd()
            yaml_dir = os.path.dirname(yaml_file)
            yaml_filename = os.path.basename(yaml_file)
            os.chdir(yaml_dir)
            
            with patch('fix_owner.safe_exit') as mock_exit:
                load_yaml_remediation(yaml_filename, self.mock_output)
                
                self.mock_output.print_general_error.assert_called()
                mock_exit.assert_called_once()
                
        finally:
            os.chdir(original_cwd)
            os.unlink(yaml_file)
    
    @unittest.skipIf(YAML_AVAILABLE, "PyYAML is available")
    def test_load_yaml_remediation_no_yaml_library(self):
        """Test behavior when PyYAML is not available."""
        with patch('fix_owner.safe_exit') as mock_exit:
            load_yaml_remediation('test.yaml', self.mock_output)
            
            self.mock_output.print_general_error.assert_called_with(
                "PyYAML is not installed. Install with: pip install PyYAML"
            )
            mock_exit.assert_called_once()
    
    def test_load_yaml_remediation_quiet_mode(self):
        """Test YAML loading in quiet mode (no verbose output)."""
        self.mock_output.get_verbose_level.return_value = 0
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.valid_yaml_content)
            yaml_file = f.name
        
        try:
            original_cwd = os.getcwd()
            yaml_dir = os.path.dirname(yaml_file)
            yaml_filename = os.path.basename(yaml_file)
            os.chdir(yaml_dir)
            
            if YAML_AVAILABLE:
                result = load_yaml_remediation(yaml_filename, self.mock_output)
                self.assertEqual(result, "TestUser")
                # In quiet mode, should not call print methods for verbose output
                self.mock_output.print_general_message.assert_not_called()
                self.mock_output.print_info_pair.assert_not_called()
            
        finally:
            os.chdir(original_cwd)
            os.unlink(yaml_file)


class TestYAMLArgumentParsing(unittest.TestCase):
    """Test argument parsing with YAML remediation options."""
    
    def test_yaml_remediation_argument_parsing(self):
        """Test that YAML remediation argument is parsed correctly."""
        with patch('sys.argv', ['fix_owner.py', '/test/path', '--yaml-remediation', 'test.yaml']):
            with patch('fix_owner.validate_path_exists', return_value=True):
                with patch('fix_owner.validate_path_is_directory', return_value=True):
                    args = parse_arguments()
                    
                    self.assertEqual(args.yaml_remediation, 'test.yaml')
                    self.assertEqual(args.root_path, '/test/path')
                    self.assertIsNone(args.owner_account)
    
    def test_yaml_remediation_with_owner_account_error(self):
        """Test that specifying both YAML file and owner account raises error."""
        with patch('sys.argv', ['fix_owner.py', '/test/path', 'Administrator', '--yaml-remediation', 'test.yaml']):
            with patch('fix_owner.validate_path_exists', return_value=True):
                with patch('fix_owner.validate_path_is_directory', return_value=True):
                    with self.assertRaises(SystemExit):
                        parse_arguments()
    
    def test_yaml_remediation_short_option(self):
        """Test YAML remediation short option (-yr)."""
        with patch('sys.argv', ['fix_owner.py', '/test/path', '-yr', 'remediation.yaml']):
            with patch('fix_owner.validate_path_exists', return_value=True):
                with patch('fix_owner.validate_path_is_directory', return_value=True):
                    args = parse_arguments()
                    
                    self.assertEqual(args.yaml_remediation, 'remediation.yaml')
    
    def test_no_yaml_no_owner_allowed(self):
        """Test that neither YAML nor owner account is allowed (uses current user)."""
        with patch('sys.argv', ['fix_owner.py', '/test/path']):
            with patch('fix_owner.validate_path_exists', return_value=True):
                with patch('fix_owner.validate_path_is_directory', return_value=True):
                    args = parse_arguments()
                    
                    self.assertIsNone(args.owner_account)
                    self.assertIsNone(args.yaml_remediation)


class TestYAMLIntegration(unittest.TestCase):
    """Test integration of YAML remediation with main execution flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_yaml_content = """
orphaned_sids:
  - recommended_remediation:
      new_owner_account: "YAMLTestUser"
      action_required: "Change ownership to specified account"
    impact_analysis:
      total_items_affected: 5
      remediation_priority: "MEDIUM"
"""
    
    @unittest.skipUnless(YAML_AVAILABLE, "PyYAML not available")
    @patch('fix_owner.SecurityManager')
    @patch('fix_owner.OutputManager')
    @patch('fix_owner.StatsTracker')
    @patch('fix_owner.ErrorManager')
    @patch('fix_owner.TimeoutManager')
    @patch('fix_owner.process_filesystem')
    @patch('fix_owner.get_execution_start_timestamp')
    def test_yaml_integration_in_main(self, mock_timestamp, mock_process, mock_timeout, 
                                     mock_error, mock_stats, mock_output, mock_security):
        """Test that YAML remediation integrates properly with main execution."""
        # Setup mocks
        mock_timestamp.return_value = (1234567890.0, "20240101_120000")
        mock_output_instance = Mock()
        mock_output_instance.get_verbose_level.return_value = 1
        mock_output.return_value = mock_output_instance
        
        mock_security_instance = Mock()
        mock_security_instance.resolve_owner_account.return_value = ("SID", "YAMLTestUser")
        mock_security.return_value = mock_security_instance
        
        # Create temporary YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(self.valid_yaml_content)
            yaml_file = f.name
        
        try:
            original_cwd = os.getcwd()
            yaml_dir = os.path.dirname(yaml_file)
            yaml_filename = os.path.basename(yaml_file)
            os.chdir(yaml_dir)
            
            # Mock sys.argv to include YAML option
            with patch('sys.argv', ['fix_owner.py', '/test/path', '--yaml-remediation', yaml_filename]):
                with patch('fix_owner.validate_path_exists', return_value=True):
                    with patch('fix_owner.validate_path_is_directory', return_value=True):
                        with patch('fix_owner.PYWIN32_AVAILABLE', True):
                            # This should not raise an exception
                            fix_owner.main()
                            
                            # Verify that the security manager was called with the YAML-specified account
                            mock_security_instance.resolve_owner_account.assert_called_with("YAMLTestUser")
                            
        finally:
            os.chdir(original_cwd)
            os.unlink(yaml_file)


if __name__ == '__main__':
    print("🧪 Testing YAML remediation functionality...")
    unittest.main(verbosity=2)