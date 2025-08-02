# Technology Stack

## Core Technologies
- **Python 3.13+**: Modern Python with type hints and latest language features
- **pywin32**: Windows API integration for security operations (centralized availability checking)
- **colorama**: Cross-platform colored terminal output (centralized color constants)

## Build System
- **setuptools**: Modern Python packaging with pyproject.toml
- **pip**: Dependency management via requirements.txt

## Development Tools
- **pytest**: Testing framework with coverage support
- **black**: Code formatting (line length: 88)
- **flake8**: Linting and style checking
- **mypy**: Static type checking with strict configuration

## Common Commands

### Installation
```cmd
pip install -r requirements.txt
```

### Testing
```cmd
# Run all tests
python tests/test_all_core_functionality.py

# Run specific test modules
python tests/test_stats_tracker.py
python tests/test_security_manager.py
python tests/test_output_manager.py

# Run with coverage (if pytest installed)
pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```cmd
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Execution
```cmd
# Main script
python src/fix_owner.py [OPTIONS] <root_path> [owner_account]

# Help
python src/fix_owner.py --help
```

## Platform Requirements
- **OS**: Windows 10/11 or Windows Server 2016+
- **Privileges**: Administrator privileges required
- **Architecture**: Windows-specific (pywin32 dependency)

## Code Organization

### Centralized Utilities (common.py)
- **Color Constants**: All color formatting uses centralized constants
  - `info_lt_clr`, `info_dk_clr`: Information display colors
  - `section_clr`: Section headers and bars
  - `error_clr`, `warn_clr`, `ok_clr`: Status indication colors
  - `reset_clr`: Color reset functionality
- **Application Constants**: Version, exit codes, limits, formatting widths
- **Utility Functions**: Timestamp handling, path validation, safe exits
- **Availability Checks**: Windows API availability flags (PYWIN32_AVAILABLE)

### Module Architecture
- **Modular Design**: Each module has a single, clear responsibility
- **Manager Pattern**: Specialized managers for different concerns
- **Consistent Imports**: Standardized import patterns with fallbacks
- **Color Consistency**: All modules use color constants from common.py
- **Error Integration**: Comprehensive error handling across all modules

### Import Patterns
All modules follow consistent import patterns:
```python
# Try relative imports first (when imported as a module)
try:
    from .common import constants, utilities
except ImportError:
    # Fall back to absolute imports (when run as a script)
    from common import constants, utilities
```