"""
ErrorManager - Comprehensive error handling and exception management for the fix-owner script.

This module provides sophisticated error handling capabilities that categorize exceptions,
provide appropriate responses, and ensure the script can continue processing even when
individual operations fail. It integrates with other components to provide consistent
error reporting and statistics tracking.

Key Features:
- Exception categorization (Security, Filesystem, Configuration, etc.)
- Standardized error handling across all components
- Integration with statistics tracking for error counting
- Context managers for operation-specific error handling
- Administrator privilege validation
- Comprehensive error reporting with suggested solutions

Classes:
    ErrorCategory: Enumeration of error types
    ErrorInfo: Data structure for error information
    ErrorManager: Main error handling coordinator
    ExceptionContext: Context manager for operation-specific error handling
"""

import sys
import traceback
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import ctypes


class ErrorCategory(Enum):
    """Categories of errors that can occur during script execution."""
    SECURITY = "security"           # Windows security API errors
    FILESYSTEM = "filesystem"       # File system access errors
    CONFIGURATION = "configuration" # Configuration and validation errors
    TIMEOUT = "timeout"            # Timeout-related errors
    PRIVILEGE = "privilege"        # Administrator privilege errors
    CRITICAL = "critical"          # Critical errors that should terminate execution


@dataclass
class ErrorInfo:
    """Information about an error that occurred."""
    category: ErrorCategory
    path: Optional[str]
    message: str
    original_exception: Exception
    is_critical: bool = False
    should_terminate: bool = False


class ErrorManager:
    """
    Comprehensive error handling and exception management for the fix-owner script.
    
    This class provides:
    - Standardized exception handling across all components
    - Specific error messages for common failure scenarios
    - Error categorization for different types of exceptions
    - Exception counting and reporting integration with statistics
    - Administrator privilege validation
    """
    
    def __init__(self, stats_tracker=None, output_manager=None):
        """
        Initialize ErrorManager with optional dependencies.
        
        Args:
            stats_tracker: StatsTracker instance for counting exceptions
            output_manager: OutputManager instance for error reporting
        """
        self.stats_tracker = stats_tracker
        self.output_manager = output_manager
        self.error_handlers: Dict[ErrorCategory, Callable] = {
            ErrorCategory.SECURITY: self._handle_security_error,
            ErrorCategory.FILESYSTEM: self._handle_filesystem_error,
            ErrorCategory.CONFIGURATION: self._handle_configuration_error,
            ErrorCategory.TIMEOUT: self._handle_timeout_error,
            ErrorCategory.PRIVILEGE: self._handle_privilege_error,
            ErrorCategory.CRITICAL: self._handle_critical_error
        }
    
    def handle_exception(self, exception: Exception, path: Optional[str] = None, 
                        context: str = "", critical: bool = False) -> ErrorInfo:
        """
        Handle an exception with appropriate categorization and response.
        
        Args:
            exception: The exception that occurred
            path: Optional path where the error occurred
            context: Additional context about the operation
            critical: Whether this is a critical error that should terminate execution
            
        Returns:
            ErrorInfo object with details about the handled error
        """
        # Categorize the error
        category = self._categorize_exception(exception, path, context)
        
        # Create error info
        error_info = ErrorInfo(
            category=category,
            path=path,
            message=self._format_error_message(exception, path, context),
            original_exception=exception,
            is_critical=critical or category == ErrorCategory.CRITICAL,
            should_terminate=critical or category in [ErrorCategory.CRITICAL, ErrorCategory.PRIVILEGE]
        )
        
        # Handle the error based on category
        handler = self.error_handlers.get(category, self._handle_generic_error)
        handler(error_info)
        
        # Count the exception if stats tracker is available
        if self.stats_tracker:
            self.stats_tracker.increment_exceptions()
        
        return error_info
    
    def _categorize_exception(self, exception: Exception, path: Optional[str], context: str) -> ErrorCategory:
        """
        Categorize an exception based on its type and context.
        
        Args:
            exception: The exception to categorize
            path: Optional path where error occurred
            context: Context of the operation
            
        Returns:
            ErrorCategory for the exception
        """
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()
        
        # Security-related errors
        if any(keyword in exception_message for keyword in [
            'access denied', 'permission denied', 'privilege', 'security',
            'sid', 'owner', 'acl', 'security descriptor'
        ]) or 'pywintypes.error' in exception_type:
            return ErrorCategory.SECURITY
        
        # Filesystem-related errors
        if any(keyword in exception_message for keyword in [
            'file not found', 'path not found', 'directory not found',
            'file in use', 'sharing violation', 'network', 'drive'
        ]) or exception_type in ['FileNotFoundError', 'PermissionError', 'OSError']:
            return ErrorCategory.FILESYSTEM
        
        # Configuration-related errors
        if any(keyword in exception_message for keyword in [
            'invalid argument', 'invalid account', 'account not found',
            'invalid path', 'invalid option'
        ]) or exception_type in ['ValueError', 'TypeError']:
            return ErrorCategory.CONFIGURATION
        
        # Timeout-related errors
        if 'timeout' in exception_message or exception_type == 'TimeoutError':
            return ErrorCategory.TIMEOUT
        
        # Critical system errors
        if exception_type in ['SystemExit', 'KeyboardInterrupt', 'MemoryError']:
            return ErrorCategory.CRITICAL
        
        # Default to filesystem for most file operation errors
        return ErrorCategory.FILESYSTEM
    
    def _format_error_message(self, exception: Exception, path: Optional[str], context: str) -> str:
        """
        Format a comprehensive error message.
        
        Args:
            exception: The exception that occurred
            path: Optional path where error occurred
            context: Context of the operation
            
        Returns:
            Formatted error message
        """
        base_message = str(exception)
        
        # Add path information if available
        if path:
            base_message = f"Path '{path}': {base_message}"
        
        # Add context if provided
        if context:
            base_message = f"{context} - {base_message}"
        
        return base_message
    
    def _handle_security_error(self, error_info: ErrorInfo) -> None:
        """Handle security-related errors."""
        if self.output_manager:
            if error_info.path:
                self.output_manager.print_error(
                    error_info.path, 
                    error_info.original_exception,
                    is_directory=True  # Default assumption
                )
            else:
                self.output_manager.print_general_error(f"Security error: {error_info.message}")
    
    def _handle_filesystem_error(self, error_info: ErrorInfo) -> None:
        """Handle filesystem-related errors."""
        if self.output_manager:
            if error_info.path:
                self.output_manager.print_error(
                    error_info.path,
                    error_info.original_exception,
                    is_directory=True  # Default assumption
                )
            else:
                self.output_manager.print_general_error(f"Filesystem error: {error_info.message}")
    
    def _handle_configuration_error(self, error_info: ErrorInfo) -> None:
        """Handle configuration-related errors."""
        if self.output_manager:
            self.output_manager.print_general_error(f"Configuration error: {error_info.message}")
        
        # Configuration errors are often critical
        if error_info.is_critical:
            sys.exit(1)
    
    def _handle_timeout_error(self, error_info: ErrorInfo) -> None:
        """Handle timeout-related errors."""
        if self.output_manager:
            self.output_manager.print_general_message(f"Timeout: {error_info.message}")
    
    def _handle_privilege_error(self, error_info: ErrorInfo) -> None:
        """Handle privilege-related errors."""
        if self.output_manager:
            self.output_manager.print_privilege_warning()
            self.output_manager.print_general_error(f"Privilege error: {error_info.message}")
    
    def _handle_critical_error(self, error_info: ErrorInfo) -> None:
        """Handle critical errors that should terminate execution."""
        if self.output_manager:
            self.output_manager.print_general_error(f"Critical error: {error_info.message}")
        
        # Print stack trace for critical errors in verbose mode
        if self.output_manager and self.output_manager.is_verbose():
            traceback.print_exc()
        
        sys.exit(1)
    
    def _handle_generic_error(self, error_info: ErrorInfo) -> None:
        """Handle generic errors that don't fit other categories."""
        if self.output_manager:
            if error_info.path:
                self.output_manager.print_error(
                    error_info.path,
                    error_info.original_exception,
                    is_directory=True  # Default assumption
                )
            else:
                self.output_manager.print_general_error(f"Error: {error_info.message}")
    
    def validate_administrator_privileges(self) -> bool:
        """
        Validate that the script is running with Administrator privileges.
        
        Returns:
            True if running with Administrator privileges, False otherwise
            
        Raises:
            SystemExit: If privileges are insufficient and critical validation is enabled
        """
        try:
            # Check if running as Administrator
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            
            if not is_admin:
                error_info = ErrorInfo(
                    category=ErrorCategory.PRIVILEGE,
                    path=None,
                    message="Administrator privileges required for ownership changes",
                    original_exception=PermissionError("Insufficient privileges"),
                    is_critical=False,  # Warning, not critical by default
                    should_terminate=False
                )
                
                self._handle_privilege_error(error_info)
                return False
            
            return True
            
        except Exception as e:
            # If we can't check privileges, assume we don't have them
            self.handle_exception(
                e, 
                context="Privilege validation",
                critical=False
            )
            return False
    
    def create_exception_context(self, operation: str, path: Optional[str] = None):
        """
        Create a context manager for handling exceptions in a specific operation.
        
        Args:
            operation: Description of the operation being performed
            path: Optional path being operated on
            
        Returns:
            ExceptionContext instance
        """
        return ExceptionContext(self, operation, path)
    
    def get_common_error_solutions(self, error_category: ErrorCategory) -> list[str]:
        """
        Get common solutions for different error categories.
        
        Args:
            error_category: Category of error
            
        Returns:
            List of suggested solutions
        """
        solutions = {
            ErrorCategory.SECURITY: [
                "Ensure the script is running with Administrator privileges",
                "Check that the target account exists and is valid",
                "Verify that the path is accessible and not locked by another process"
            ],
            ErrorCategory.FILESYSTEM: [
                "Verify that the path exists and is accessible",
                "Check that files are not in use by other applications",
                "Ensure sufficient disk space is available",
                "Check network connectivity if accessing network paths"
            ],
            ErrorCategory.CONFIGURATION: [
                "Verify command-line arguments are correct",
                "Check that the target owner account name is valid",
                "Ensure the root path exists and is a directory"
            ],
            ErrorCategory.PRIVILEGE: [
                "Run the script as Administrator",
                "Right-click Command Prompt and select 'Run as administrator'",
                "Ensure your account has the necessary privileges"
            ],
            ErrorCategory.TIMEOUT: [
                "Increase the timeout value using -ts option",
                "Process smaller directory structures",
                "Check system performance and available resources"
            ]
        }
        
        return solutions.get(error_category, ["Contact system administrator for assistance"])


class ExceptionContext:
    """
    Context manager for handling exceptions in specific operations.
    """
    
    def __init__(self, error_manager: ErrorManager, operation: str, path: Optional[str] = None):
        """
        Initialize exception context.
        
        Args:
            error_manager: ErrorManager instance
            operation: Description of the operation
            path: Optional path being operated on
        """
        self.error_manager = error_manager
        self.operation = operation
        self.path = path
        self.error_occurred = False
    
    def __enter__(self):
        """Enter the context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context and handle any exception.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
            
        Returns:
            True to suppress the exception, False to re-raise
        """
        if exc_type is not None:
            self.error_occurred = True
            error_info = self.error_manager.handle_exception(
                exc_val,
                path=self.path,
                context=self.operation
            )
            
            # Suppress non-critical exceptions to continue processing
            return not error_info.should_terminate
        
        return False