"""
TimeoutManager - Execution time limit management for the fix-owner script.

This module provides sophisticated timeout handling that allows the script to
gracefully terminate processing when execution time limits are reached. It's
particularly useful for large directory structures where processing could
take an indefinite amount of time.

Key Features:
- Configurable timeout limits with 0 meaning no timeout
- Thread-based timeout detection for non-blocking operation
- Graceful termination that allows current operations to complete
- Integration with filesystem processing for periodic timeout checks
- Context manager support for automatic cleanup
- Elapsed and remaining time tracking

The TimeoutManager integrates with the FileSystemWalker to provide periodic
timeout checks during directory traversal, ensuring that the script can
terminate gracefully even during long-running operations.

Classes:
    TimeoutManager: Main timeout coordination and detection
"""

import time
import threading
from typing import Optional


class TimeoutManager:
    """
    Manages execution timeout functionality for the fix-owner script.
    
    This class provides timeout checking mechanism that can interrupt processing
    and graceful termination when timeout is reached.
    """
    
    def __init__(self, timeout_seconds: int = 0):
        """
        Initialize TimeoutManager with specified timeout.
        
        Args:
            timeout_seconds: Maximum execution time in seconds. 0 means no timeout.
        """
        self.timeout_seconds = timeout_seconds
        self.start_time = time.time()
        self.timeout_reached = False
        self._timer: Optional[threading.Timer] = None
        
    def is_timeout_reached(self) -> bool:
        """
        Check if timeout has been reached.
        
        Returns:
            True if timeout has been reached, False otherwise.
        """
        if self.timeout_seconds <= 0:
            return False
            
        elapsed = time.time() - self.start_time
        if elapsed >= self.timeout_seconds:
            self.timeout_reached = True
            
        return self.timeout_reached
    
    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since timeout manager was created.
        
        Returns:
            Elapsed time in seconds.
        """
        return time.time() - self.start_time
    
    def get_remaining_time(self) -> float:
        """
        Get remaining time before timeout.
        
        Returns:
            Remaining time in seconds, or float('inf') if no timeout set.
        """
        if self.timeout_seconds <= 0:
            return float('inf')
            
        elapsed = self.get_elapsed_time()
        remaining = self.timeout_seconds - elapsed
        return max(0.0, remaining)
    
    def setup_timeout_handler(self, callback=None):
        """
        Setup timeout mechanism with optional callback.
        
        Args:
            callback: Optional function to call when timeout is reached.
        """
        if self.timeout_seconds <= 0:
            return
            
        def timeout_handler():
            self.timeout_reached = True
            if callback:
                callback()
        
        # Calculate remaining time from now
        elapsed = self.get_elapsed_time()
        remaining = self.timeout_seconds - elapsed
        
        if remaining > 0:
            self._timer = threading.Timer(remaining, timeout_handler)
            self._timer.daemon = True  # Don't prevent program exit
            self._timer.start()
    
    def cancel_timeout(self):
        """
        Cancel the timeout timer if it's active.
        """
        if self._timer and self._timer.is_alive():
            self._timer.cancel()
    
    def reset_timer(self):
        """
        Reset the timeout timer to start counting from now.
        """
        self.start_time = time.time()
        self.timeout_reached = False
        if self._timer:
            self._timer.cancel()
    
    def should_continue_processing(self) -> bool:
        """
        Check if processing should continue based on timeout status.
        
        Returns:
            True if processing should continue, False if timeout reached.
        """
        return not self.is_timeout_reached()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup timer."""
        self.cancel_timeout()