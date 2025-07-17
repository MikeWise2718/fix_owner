#!/usr/bin/env python3
"""
Unit tests for SecurityManager class - Windows security operations for file/directory ownership.
"""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Import the SecurityManager from src/fix_owner.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from src.fix_owner import SecurityManager
from src.error_manager import ErrorManager


class TestSecurityManager(unittest.TestCase):
    """Test cases for SecurityManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_error_manager = Mock()
        self.security_manager = SecurityManager(error_manager=self.mock_error_manager)
    
    @patch('src.fix_owner.win32security')
    def test_get_current_owner_valid_sid(self, mock_win32security):
        """Test getting current owner with valid SID."""
        # Mock security descriptor and SID
        mock_sd = Mock()
        mock_sid = Mock()
        mock_sd.GetSecurityDescriptorOwner.return_value = mock_sid
        mock_win32security.GetFileSecurity.return_value = mock_sd
        mock_win32security.LookupAccountSid.return_value = ("TestUser", "DOMAIN", 1)
        
        # Test getting current owner
        owner_name, owner_sid = self.security_manager.get_current_owner("/test/path")
        
        # Verify results
        self.assertEqual(owner_name, "DOMAIN\\TestUser")
        self.assertEqual(owner_sid, mock_sid)
        
        # Verify API calls
        mock_win32security.GetFileSecurity.assert_called_once_with(
            "/test/path", mock_win32security.OWNER_SECURITY_INFORMATION
        )
        mock_win32security.LookupAccountSid.assert_called_once_with(None, mock_sid)
    
    @patch('src.fix_owner.win32security')
    def test_get_current_owner_invalid_sid(self, mock_win32security):
        """Test getting current owner with invalid/orphaned SID."""
        # Mock security descriptor and SID
        mock_sd = Mock()
        mock_sid = Mock()
        mock_sd.GetSecurityDescriptorOwner.return_value = mock_sid
        mock_win32security.GetFileSecurity.return_value = mock_sd
        # LookupAccountSid raises exception for invalid SID
        mock_win32security.LookupAccountSid.side_effect = Exception("Invalid SID")
        
        # Test getting current owner
        owner_name, owner_sid = self.security_manager.get_current_owner("/test/path")
        
        # Verify results - name should be None for invalid SID
        self.assertIsNone(owner_name)
        self.assertEqual(owner_sid, mock_sid)
    
    @patch('src.fix_owner.win32security')
    def test_get_current_owner_access_denied(self, mock_win32security):
        """Test getting current owner when access is denied."""
        # Mock GetFileSecurity to raise exception
        mock_win32security.GetFileSecurity.side_effect = Exception("Access denied")
        
        # Test getting current owner - should raise exception
        with self.assertRaises(Exception) as context:
            self.security_manager.get_current_owner("/test/path")
        
        self.assertIn("Access denied", str(context.exception))
    
    @patch('src.fix_owner.win32security')
    def test_is_sid_valid_true(self, mock_win32security):
        """Test SID validation for valid SID."""
        mock_sid = Mock()
        mock_win32security.LookupAccountSid.return_value = ("TestUser", "DOMAIN", 1)
        
        result = self.security_manager.is_sid_valid(mock_sid)
        
        self.assertTrue(result)
        mock_win32security.LookupAccountSid.assert_called_once_with(None, mock_sid)
    
    @patch('src.fix_owner.win32security')
    def test_is_sid_valid_false(self, mock_win32security):
        """Test SID validation for invalid SID."""
        mock_sid = Mock()
        mock_win32security.LookupAccountSid.side_effect = Exception("Invalid SID")
        
        result = self.security_manager.is_sid_valid(mock_sid)
        
        self.assertFalse(result)
    
    @patch('src.fix_owner.win32security')
    def test_set_owner_success(self, mock_win32security):
        """Test setting ownership successfully."""
        # Mock security descriptor
        mock_sd = Mock()
        mock_owner_sid = Mock()
        mock_win32security.GetFileSecurity.return_value = mock_sd
        
        result = self.security_manager.set_owner("/test/path", mock_owner_sid)
        
        self.assertTrue(result)
        mock_win32security.GetFileSecurity.assert_called_once_with(
            "/test/path", mock_win32security.OWNER_SECURITY_INFORMATION
        )
        mock_sd.SetSecurityDescriptorOwner.assert_called_once_with(mock_owner_sid, False)
        mock_win32security.SetFileSecurity.assert_called_once_with(
            "/test/path", mock_win32security.OWNER_SECURITY_INFORMATION, mock_sd
        )
    
    @patch('src.fix_owner.win32security')
    def test_set_owner_failure(self, mock_win32security):
        """Test setting ownership failure."""
        mock_owner_sid = Mock()
        mock_win32security.GetFileSecurity.side_effect = Exception("Access denied")
        
        with self.assertRaises(Exception) as context:
            self.security_manager.set_owner("/test/path", mock_owner_sid)
        
        self.assertIn("Access denied", str(context.exception))
    
    @patch('src.fix_owner.win32api')
    @patch('src.fix_owner.win32security')
    def test_resolve_owner_account_specified(self, mock_win32security, mock_win32api):
        """Test resolving specified owner account."""
        mock_sid = Mock()
        mock_win32security.LookupAccountName.return_value = (mock_sid, "DOMAIN", 1)
        
        sid, resolved_name = self.security_manager.resolve_owner_account("TestUser")
        
        self.assertEqual(sid, mock_sid)
        self.assertEqual(resolved_name, "DOMAIN\\TestUser")
        mock_win32security.LookupAccountName.assert_called_once_with(None, "TestUser")
    
    @patch('src.fix_owner.win32api')
    @patch('src.fix_owner.win32security')
    @patch('src.fix_owner.win32con')
    def test_resolve_owner_account_current_user(self, mock_win32con, mock_win32security, mock_win32api):
        """Test resolving current user account."""
        mock_sid = Mock()
        mock_win32api.GetUserNameEx.return_value = "DOMAIN\\CurrentUser"
        mock_win32security.LookupAccountName.return_value = (mock_sid, "DOMAIN", 1)
        
        sid, resolved_name = self.security_manager.resolve_owner_account(None)
        
        self.assertEqual(sid, mock_sid)
        self.assertEqual(resolved_name, "DOMAIN\\CurrentUser")
        mock_win32api.GetUserNameEx.assert_called_once_with(mock_win32con.NameSamCompatible)
        mock_win32security.LookupAccountName.assert_called_once_with(None, "DOMAIN\\CurrentUser")
    
    @patch('src.fix_owner.win32security')
    def test_resolve_owner_account_invalid(self, mock_win32security):
        """Test resolving invalid owner account."""
        mock_win32security.LookupAccountName.side_effect = Exception("Account not found")
        
        with self.assertRaises(Exception) as context:
            self.security_manager.resolve_owner_account("InvalidUser")
        
        self.assertIn("Account not found", str(context.exception))
    
    def test_security_manager_without_pywin32(self):
        """Test SecurityManager initialization without pywin32."""
        with patch('src.fix_owner.PYWIN32_AVAILABLE', False):
            with self.assertRaises(ImportError):
                SecurityManager()
    
    def test_security_manager_with_error_manager_integration(self):
        """Test SecurityManager integration with ErrorManager."""
        # Create a real ErrorManager for integration testing
        mock_stats = Mock()
        mock_output = Mock()
        error_manager = ErrorManager(stats_tracker=mock_stats, output_manager=mock_output)
        
        security_manager = SecurityManager(error_manager=error_manager)
        
        # Verify error manager is set
        self.assertEqual(security_manager.error_manager, error_manager)


def run_security_manager_tests():
    """Run all SecurityManager tests."""
    print("Running SecurityManager tests...\n")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecurityManager)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_security_manager_tests())