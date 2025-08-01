# Design Document

## Overview

The fix-owner script is a Python-based command-line utility that recursively takes ownership of directories and files with orphaned or invalid Security Identifiers (SIDs) on Windows systems. The script provides comprehensive options for execution control, error handling, and statistics reporting, making it suitable for system administrators dealing with permission issues after migrations or user deletions.

## Architecture

The script follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Command Line Interface                    │
│                      (argparse)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Main Controller                          │
│            (Orchestrates execution flow)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│   Security   │ │  File   │ │ Statistics  │
│   Manager    │ │ Walker  │ │   Tracker   │
│              │ │         │ │             │
└──────────────┘ └─────────┘ └─────────────┘
```

## Components and Interfaces

### 1. Command Line Interface (CLI)
**Purpose:** Parse and validate command-line arguments
**Key Functions:**
- `parse_arguments()`: Parse command-line options using argparse
- Validate required parameters and option combinations
- Provide help documentation

**Interface:**
```python
def parse_arguments() -> argparse.Namespace:
    """Parse and return command-line arguments"""
```

### 2. Security Manager
**Purpose:** Handle Windows security operations and SID validation
**Key Functions:**
- `get_current_owner(path)`: Retrieve current owner SID for a path
- `is_sid_valid(sid)`: Check if SID corresponds to valid account
- `set_owner(path, owner_sid)`: Change ownership of path to specified SID
- `resolve_owner_account(account_name)`: Convert account name to SID

**Interface:**
```python
class SecurityManager:
    def get_current_owner(self, path: str) -> tuple[str, object]:
        """Returns (owner_name, owner_sid) or (None, owner_sid) if invalid"""
    
    def is_sid_valid(self, sid: object) -> bool:
        """Check if SID corresponds to existing account"""
    
    def set_owner(self, path: str, owner_sid: object) -> bool:
        """Set ownership, returns True if changed"""
    
    def resolve_owner_account(self, account_name: str) -> object:
        """Convert account name to SID"""
```

### 3. File System Walker
**Purpose:** Traverse directory structure and coordinate ownership changes
**Key Functions:**
- `walk_filesystem(root_path, options)`: Main traversal logic
- Handle recursion control based on options
- Coordinate with SecurityManager for ownership operations

**Interface:**
```python
class FileSystemWalker:
    def __init__(self, security_manager: SecurityManager, stats_tracker: StatsTracker):
        pass
    
    def walk_filesystem(self, root_path: str, options: dict) -> None:
        """Traverse filesystem and process ownership"""
```

### 4. Statistics Tracker
**Purpose:** Track and report execution statistics
**Key Functions:**
- Track counts for directories, files, changes, and exceptions
- Measure execution time
- Generate final report

**Interface:**
```python
class StatsTracker:
    def __init__(self):
        self.dirs_traversed = 0
        self.files_traversed = 0
        self.dirs_changed = 0
        self.files_changed = 0
        self.exceptions = 0
        self.start_time = time.time()
    
    def increment_dirs_traversed(self) -> None
    def increment_files_traversed(self) -> None
    def increment_dirs_changed(self) -> None
    def increment_files_changed(self) -> None
    def increment_exceptions(self) -> None
    def get_elapsed_time(self) -> float
    def print_report(self, quiet: bool) -> None
```

### 5. Timeout Manager
**Purpose:** Handle execution time limits
**Key Functions:**
- Monitor execution time against specified timeout
- Provide graceful termination mechanism

**Interface:**
```python
class TimeoutManager:
    def __init__(self, timeout_seconds: int):
        pass
    
    def is_timeout_reached(self) -> bool:
        """Check if timeout has been reached"""
    
    def setup_timeout_handler(self) -> None:
        """Setup timeout mechanism"""
```

## Data Models

### Options Configuration
```python
@dataclass
class ExecutionOptions:
    execute: bool = False          # -x flag
    recurse: bool = False          # -r flag
    files: bool = False            # -f flag
    verbose: bool = False          # -v flag
    quiet: bool = False            # -q flag
    timeout: int = 0               # -to value
    root_path: str = ""            # positional argument
    owner_account: str = ""        # target owner account
```

### Statistics Data
```python
@dataclass
class ExecutionStats:
    dirs_traversed: int = 0
    files_traversed: int = 0
    dirs_changed: int = 0
    files_changed: int = 0
    exceptions: int = 0
    start_time: float = field(default_factory=time.time)
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
```

## Error Handling

### Exception Categories
1. **Security Exceptions**: Invalid SIDs, permission denied, access errors
2. **File System Exceptions**: Path not found, file in use, network errors
3. **Configuration Exceptions**: Invalid owner account, missing privileges
4. **Timeout Exceptions**: Execution time limit exceeded

### Error Handling Strategy
- **Catch and Continue**: Individual file/directory errors don't stop execution
- **Error Logging**: All exceptions are counted and optionally displayed
- **Graceful Degradation**: Script continues with remaining items when errors occur
- **Early Termination**: Critical errors (invalid owner account) cause immediate exit

### Error Reporting
```python
def handle_exception(self, path: str, exception: Exception, verbose: bool) -> None:
    """Standard exception handling with optional verbose output"""
    self.stats.increment_exceptions()
    if verbose:
        print(f"Error processing {path}: {exception}")
```

## Testing Strategy

### Unit Testing
- **SecurityManager Tests**: Mock pywin32 calls, test SID validation logic
- **FileSystemWalker Tests**: Mock file system operations, test recursion logic
- **StatsTracker Tests**: Verify counting and reporting accuracy
- **CLI Tests**: Test argument parsing and validation

### Integration Testing
- **End-to-End Tests**: Test complete workflow with test directory structures
- **Permission Tests**: Test with various permission scenarios
- **Error Scenario Tests**: Test behavior with invalid paths, permissions

### Test Data Setup
- Create test directory structures with known SID configurations
- Mock Windows security APIs for consistent testing
- Test timeout functionality with controlled delays

### Performance Testing
- **Large Directory Tests**: Test with directories containing thousands of items
- **Deep Recursion Tests**: Test with deeply nested directory structures
- **Memory Usage Tests**: Monitor memory consumption during large operations

## Security Considerations

### Privilege Requirements
- Script must run with Administrator privileges for security operations
- Validate privilege level at startup and provide clear error messages

### SID Validation
- Implement robust SID validation to prevent setting invalid owners
- Handle domain vs local account resolution properly
- Validate target owner account exists before processing

### Audit Trail
- Log all ownership changes when in execute mode
- Provide clear indication of dry-run vs actual execution
- Include original owner information in verbose output

## Performance Optimizations

### Efficient Traversal
- Use `os.walk()` for efficient directory traversal
- Implement early termination for timeout scenarios
- Minimize redundant security API calls

### Memory Management
- Process files incrementally rather than loading full directory lists
- Clean up security descriptors and handles properly
- Monitor memory usage for large directory structures

### Caching Strategy
- Cache resolved SIDs to avoid repeated lookups
- Cache security manager instances for reuse
- Implement owner account resolution caching

## Configuration and Deployment

### Dependencies
- **Python 3.13+**: Required for modern language features
- **pywin32**: Windows API access for security operations
- **Standard Library**: os, argparse, time, threading modules

### Installation Requirements
- Windows 10/11 or Windows Server
- Administrator privileges for execution
- Python environment with pywin32 installed

### Configuration Options
- Target owner account configurable via command line
- All execution options controlled via command-line flags
- No external configuration files required for simplicity