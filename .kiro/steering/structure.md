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
- **fix_owner.py**: Main entry point and orchestration
- **output_manager.py**: Centralized output control and formatting
- **error_manager.py**: Exception handling and error categorization
- **filesystem_walker.py**: Directory traversal logic
- **timeout_manager.py**: Execution timeout management

### Design Patterns
- **Modular Design**: Clear separation of concerns across modules
- **Manager Pattern**: Specialized managers for output, errors, timeouts
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
- **Error Fallbacks**: Graceful degradation (colorama import handling)