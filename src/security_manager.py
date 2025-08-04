"""
SecurityManager - Windows security operations for the fix-owner script.

This module provides comprehensive Windows security API integration for file and
directory ownership operations. It encapsulates all Windows security interactions
including SID validation, ownership retrieval, and ownership changes.

Key Features:
- Get current owner of files and directories with SID resolution
- Validate SIDs to identify orphaned/invalid ownership
- Set ownership of files and directories safely
- Resolve account names to SIDs for ownership operations
- Integration with ErrorManager for comprehensive error handling
- Support for both local and domain accounts

Classes:
    SecurityManager: Main Windows security operations coordinator
"""

from typing import Optional

# Import common utilities and constants
try:
    from .common import PYWIN32_AVAILABLE
except ImportError:
    # Fall back to absolute imports (when run as a script)
    from common import PYWIN32_AVAILABLE

# Windows security imports (availability checked in common)
if PYWIN32_AVAILABLE:
    import win32security
    import win32api
    import win32con


class SecurityManager:
    """
    Manages Windows security operations for file/directory ownership.
    
    This class encapsulates all Windows security API interactions including
    SID validation, ownership retrieval, and ownership changes. It provides
    a clean interface for the fix-owner script to perform ownership operations
    without directly dealing with Windows security APIs.
    
    The SecurityManager handles:
    - Retrieving current ownership information from files/directories
    - Validating SIDs to identify orphaned ownership
    - Setting new ownership on files/directories
    - Resolving account names to SIDs for ownership operations
    - Error handling and integration with ErrorManager
    """
    
    def __init__(self, error_manager=None):
        """
        Initialize the SecurityManager with optional error handling integration.
        
        Args:
            error_manager: Optional ErrorManager for comprehensive error handling
            
        Raises:
            ImportError: If pywin32 module is not available
        """
        if not PYWIN32_AVAILABLE:
            raise ImportError("pywin32 module is required for security operations")
        self.error_manager = error_manager
    
    def get_current_owner(self, path: str) -> tuple[Optional[str], object]:
        """
        Get current owner of a file or directory using Windows Security APIs.
        
        This method performs a two-step process:
        1. Retrieves the security descriptor and extracts the owner SID
        2. Attempts to resolve the SID to a human-readable account name
        
        The method is designed to identify orphaned SIDs - SIDs that exist in the
        security descriptor but no longer correspond to valid user accounts. This
        is the primary condition that the fix-owner script is designed to detect
        and remediate.
        
        Args:
            path: Path to examine (file or directory)
            
        Returns:
            Tuple of (owner_name, owner_sid). owner_name is None if SID is invalid/orphaned,
            otherwise it contains the resolved account name. owner_sid is always the SID object.
            
        Raises:
            Exception: If unable to get security information due to permissions or other errors
        """
        try:
            # Step 1: Get the security descriptor for the file/directory
            # OWNER_SECURITY_INFORMATION flag requests only owner information for efficiency
            sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
            
            # Extract the owner SID from the security descriptor
            # This SID uniquely identifies the owner account
            owner_sid = sd.GetSecurityDescriptorOwner()
            
            try:
                # Step 2: Attempt to resolve SID to account name
                # LookupAccountSid converts SID to human-readable name and domain
                name, domain, _ = win32security.LookupAccountSid(None, owner_sid)
                
                # Format as DOMAIN\\USERNAME or just USERNAME if no domain
                owner_name = f"{domain}\\{name}" if domain else name
                return owner_name, owner_sid
                
            except Exception:
                # SID resolution failed - this indicates an orphaned/invalid SID
                # The SID exists but doesn't correspond to any current account
                # This is exactly what we want to detect and fix
                return None, owner_sid
                
        except Exception as e:
            # Handle errors in getting security information
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, path=path, context="Getting current owner"
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to get owner information for '{path}': {e}")
    
    def is_sid_valid(self, sid: object) -> bool:
        """
        Check if a SID corresponds to a valid account using Windows Security APIs.
        
        This method attempts to resolve a SID to an account name. If the resolution
        succeeds, the SID is valid and corresponds to an existing account. If it fails,
        the SID is orphaned/invalid and represents ownership that should be changed.
        
        Args:
            sid: SID object to validate
            
        Returns:
            True if SID corresponds to an existing account, False if orphaned/invalid
        """
        try:
            # Attempt to resolve SID to account name
            # If this succeeds, the SID is valid and corresponds to an existing account
            win32security.LookupAccountSid(None, sid)
            return True
        except Exception:
            # LookupAccountSid failed - SID is orphaned/invalid
            # This is the condition we're looking for to identify ownership that needs fixing
            return False
    
    def set_owner(self, path: str, owner_sid: object) -> bool:
        """
        Set ownership of a file or directory using Windows Security APIs.
        
        This method performs a three-step process to change ownership:
        1. Retrieves the current security descriptor
        2. Modifies the owner SID in the security descriptor
        3. Applies the modified security descriptor back to the file/directory
        
        The operation requires appropriate privileges (typically Administrator) to succeed.
        The method preserves all other security information and only changes the owner.
        
        Args:
            path: Path to change ownership (file or directory)
            owner_sid: SID of new owner account
            
        Returns:
            True if ownership was successfully changed
            
        Raises:
            Exception: If unable to set ownership due to permissions or other errors
        """
        try:
            # Step 1: Get current security descriptor
            # We need the existing descriptor to modify only the owner portion
            sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
            
            # Step 2: Set the new owner SID in the security descriptor
            # The second parameter (False) indicates we're not setting a group owner
            sd.SetSecurityDescriptorOwner(owner_sid, False)
            
            # Step 3: Apply the modified security descriptor back to the file/directory
            # This is where the actual ownership change occurs
            win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
            
            return True
            
        except Exception as e:
            # Handle ownership change errors through ErrorManager if available
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, path=path, context="Setting ownership"
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to set owner for '{path}': {e}")
    
    def resolve_owner_account(self, account_name: Optional[str]) -> tuple[object, str]:
        """
        Convert account name to SID using Windows Security APIs.
        
        This method resolves either a specified account name or the current logged-in user
        to a Security Identifier (SID) that can be used for ownership operations.
        It handles both local and domain accounts properly and provides detailed
        account information for debugging purposes.
        
        Args:
            account_name: Account name to resolve (e.g., "Administrator", "DOMAIN\\\\User"), 
                         or None to use current logged-in user
            
        Returns:
            Tuple of (SID object, resolved account name with domain)
            
        Raises:
            Exception: If account cannot be resolved or doesn't exist
        """
        try:
            if account_name:
                # Use specified account name
                # LookupAccountName resolves the name to SID and provides domain info
                sid, domain, account_type = win32security.LookupAccountName(None, account_name)
                
                # Format the resolved name with domain for clarity
                resolved_name = f"{domain}\\{account_name}" if domain else account_name
                
                # Log the account type for debugging (User, Group, Domain, etc.)
                if self.error_manager and hasattr(self.error_manager, 'output_manager'):
                    output = self.error_manager.output_manager
                    if output and hasattr(output, 'get_verbose_level') and callable(output.get_verbose_level):
                        try:
                            if output.get_verbose_level() >= 1:
                                account_types = {
                                    1: "User", 2: "Group", 3: "Domain", 4: "Alias", 
                                    5: "WellKnownGroup", 6: "DeletedAccount", 7: "Invalid", 8: "Unknown"
                                }
                                type_name = account_types.get(account_type, f"Type{account_type}")
                                output.print_general_message(f"Resolved account type: {type_name}")
                        except (TypeError, AttributeError):
                            # Handle mock objects or other issues gracefully
                            pass
                        
            else:
                # Use current logged-in user - get the full username with domain
                current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)
                sid, domain, account_type = win32security.LookupAccountName(None, current_user)
                resolved_name = current_user
                
            return sid, resolved_name
            
        except Exception as e:
            # Handle account resolution errors
            account_display = account_name or "current logged-in user"
            if self.error_manager:
                error_info = self.error_manager.handle_exception(
                    e, context=f"Resolving account '{account_display}'", critical=True
                )
                if error_info.should_terminate:
                    raise
            raise Exception(f"Failed to resolve account '{account_display}': {e}")
    
    def get_account_info(self, account_name: str) -> dict:
        """
        Get detailed information about an account.
        
        This method provides additional account information that can be useful
        for debugging and validation purposes.
        
        Args:
            account_name: Account name to query
            
        Returns:
            Dictionary containing account information including SID, domain, and type
            
        Raises:
            Exception: If account cannot be found or queried
        """
        try:
            sid, domain, account_type = win32security.LookupAccountName(None, account_name)
            
            account_types = {
                1: "User", 2: "Group", 3: "Domain", 4: "Alias", 
                5: "WellKnownGroup", 6: "DeletedAccount", 7: "Invalid", 8: "Unknown"
            }
            
            return {
                'account_name': account_name,
                'sid': sid,
                'domain': domain,
                'account_type': account_type,
                'account_type_name': account_types.get(account_type, f"Type{account_type}"),
                'full_name': f"{domain}\\{account_name}" if domain else account_name
            }
            
        except Exception as e:
            raise Exception(f"Failed to get account information for '{account_name}': {e}")
    
    def is_pywin32_available(self) -> bool:
        """
        Check if pywin32 is available for security operations.
        
        Returns:
            True if pywin32 is available, False otherwise
        """
        return PYWIN32_AVAILABLE