# Project Structure

## Directory Organization

```
fix-owner-script/
├── src/                    # Source code modules
├── tests/                  # Test suite
├── old/                    # Legacy versions and examples
├── .kiro/                  # Kiro IDE specifications and steering
├── htmlcov/               # Coverage reports (generated)
└── [config files]         # Project configuration
```

## Source Code Architecture (`src/`)

### Core Modules
- **fix_owner.py**: Main entry point and orchestration (26,060 bytes)
- **output_manager.py**: Centralized output control and formatting (25,201 bytes)
- **filesystem_walker.py**: Directory traversal and file processing logic (24,612 bytes)
- **error_manager.py**: Exception handling and error categorization (15,996 bytes)
- **security_manager.py**: Windows security operations and SID management (13,596 bytes)
- **sid_tracker.py**: SID tracking and ownership analysis reporting (13,281 bytes)
- **stats_tracker.py**: Execution statistics tracking and reporting (7,801 bytes)
- **common.py**: Shared utilities, constants, and color definitions (5,747 bytes)
- **timeout_manager.py**: Execution timeout management (4,909 bytes)

### Module Responsibilities

#### **common.py** - Shared Foundation
- **Color Constants**: Centralized color definitions (info_lt_clr, error_clr, warn_clr, etc.)
- **Application Constants**: Version, exit codes, path limits, formatting widths
- **Utility Functions**: Timestamp handling, path validation, safe exit, module setup
- **Availability Flags**: Windows API availability checks (PYWIN32_AVAILABLE, WIN32SECURITY_AVAILABLE)
- **Formatting Helpers**: Section headers, bars, consistent output formatting

#### **fix_owner.py** - Main Orchestration
- **Entry Point**: Command-line interface and argument parsing
- **Workflow Coordination**: Manages execution phases and component integration
- **Configuration Management**: ExecutionOptions and ExecutionStats dataclasses
- **Error Handling**: Top-level exception handling and graceful exits
- **Component Integration**: Coordinates all managers and trackers

#### **security_manager.py** - Windows Security Operations
- **SID Operations**: Get current owner, validate SIDs, set ownership
- **Account Resolution**: Convert account names to SIDs, handle domain accounts
- **Windows API Integration**: Comprehensive pywin32 wrapper functionality
- **Error Integration**: Works with ErrorManager for comprehensive error handling

#### **output_manager.py** - Output Control
- **Verbosity Management**: Multiple output levels (0-3) and quiet mode
- **Formatted Output**: Consistent message formatting with color constants
- **Stream Management**: Separate stdout/stderr handling with fallbacks
- **Progress Reporting**: Directory processing progress and summaries

#### **filesystem_walker.py** - File System Processing
- **Directory Traversal**: Recursive directory walking with os.walk()
- **Ownership Processing**: File and directory ownership examination and changes
- **Progress Tracking**: Integration with OutputManager for progress reporting
- **SID Integration**: Works with SidTracker for ownership analysis

#### **stats_tracker.py** - Statistics Management
- **Counter Management**: Tracks directories, files, changes, exceptions
- **Timing Operations**: High-precision execution timing
- **Report Generation**: Formatted statistics reports with color constants
- **Data Export**: Summary statistics for integration with other components

#### **sid_tracker.py** - SID Analysis
- **SID Collection**: Tracks all SIDs encountered during processing
- **Validity Checking**: Identifies valid vs orphaned SIDs
- **Report Generation**: Comprehensive ownership analysis reports
- **Account Resolution**: Resolves SIDs to human-readable account names

#### **error_manager.py** - Error Handling
- **Exception Categorization**: Classifies errors by type and severity
- **Error Recovery**: Provides recovery suggestions and solutions
- **Statistics Integration**: Tracks error counts and patterns
- **Context Management**: Provides error context for debugging

#### **timeout_manager.py** - Execution Control
- **Timeout Management**: Prevents indefinite execution on large structures
- **Timer Operations**: Threading-based timeout implementation
- **Context Manager**: Safe resource cleanup and timeout handling
- **Progress Monitoring**: Integration with main execution flow

### Design Patterns
- **Modular Design**: Clear separation of concerns across modules
- **Manager Pattern**: Specialized managers for output, errors, timeouts, security
- **Centralized Utilities**: Common functionality factored into common.py
- **Color Consistency**: All color formatting uses constants from common.py
- **Enum-Based Configuration**: Type-safe configuration using Python enums
- **Dataclass Structures**: Structured data with type hints
- **Context Managers**: Safe resource handling and error contexts

## Test Structure (`tests/`)

### Test Categories
- **Unit Tests**: Individual component testing (`test_*_manager.py`)
- **Integration Tests**: Cross-component functionality (`test_integration.py`)
- **Comprehensive Suite**: All functionality (`test_all_core_functionality.py`)
- **Argument Parsing**: CLI interface testing (`test_argument_parsing.py`)

### Test Patterns
- **Mocking**: Windows API calls and file system operations
- **Buffer Capture**: Output stream testing with io.StringIO
- **Exception Testing**: Error handling validation
- **Path Insertion**: `sys.path.insert(0, ...)` for module imports

## Code Style Conventions

### Python Standards
- **Type Hints**: Comprehensive typing throughout codebase
- **Docstrings**: Detailed module and function documentation
- **Error Handling**: Robust exception management with categorization
- **Logging**: Structured output through OutputManager

### Naming Conventions
- **Classes**: PascalCase (OutputManager, ErrorCategory)
- **Functions/Variables**: snake_case (print_examining_path)
- **Constants**: UPPER_SNAKE_CASE (COLORAMA_AVAILABLE)
- **Enums**: PascalCase with descriptive values

### File Organization
- **Single Responsibility**: Each module handles one major concern
- **Import Structure**: Standard library, third-party, local imports
- **Common Utilities**: Shared functionality centralized in common.py
- **Color Management**: All color formatting uses constants from common.py
- **Error Fallbacks**: Graceful degradation with fallback imports
- **Consistent Patterns**: Standardized import patterns and utility usage

### Code Factorization
- **common.py Integration**: All modules import shared utilities and constants
- **Color Centralization**: Single source of truth for all color definitions
- **Utility Standardization**: Common functions for timing, formatting, validation
- **Constant Management**: Application-wide constants defined once
- **Import Patterns**: Consistent relative/absolute import fallback patterns