# Technology Stack

## Core Technologies
- **Python 3.13+**: Modern Python with type hints and latest language features
- **pywin32**: Windows API integration for security operations
- **colorama**: Cross-platform colored terminal output

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

# Run specific test module
python -m unittest tests.test_output_manager

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