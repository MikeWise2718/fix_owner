# Fix Owner Script

A Python utility for recursively taking ownership of directories and files with orphaned Security Identifiers (SIDs) on Windows systems. This tool is particularly useful after system migrations, user deletions, or when inherited permissions cause access issues.

## Features

- **Recursive Processing**: Traverse directory structures with optional file processing
- **Dry-Run Mode**: Test operations safely before making actual changes
- **Comprehensive Statistics**: Track directories, files, changes, and errors
- **Timeout Support**: Prevent indefinite execution on large directory structures
- **Flexible Output**: Verbose, standard, or quiet output modes
- **Robust Error Handling**: Continue processing after individual failures
- **Windows Security Integration**: Native Windows API integration via pywin32

## Requirements

- **Operating System**: Windows 10/11 or Windows Server
- **Python**: 3.13 or higher
- **Privileges**: Administrator privileges required for security operations
- **Dependencies**: pywin32 for Windows API access, colorama for colored output

## Installation

1. **Clone or download** the script files to your local system

2. **Install Python dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```cmd
   python src/fix_owner.py --help
   ```

## Usage

### Basic Syntax

```cmd
python src/fix_owner.py [OPTIONS] <root_path> [owner_account]
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `-x, --execute` | Execute changes (default is dry-run mode) |
| `-r, --recurse` | Recurse into subdirectories |
| `-f, --files` | Process files in addition to directories |
| `-v, --verbose LEVEL` | Verbose output level: 0=statistics only, 1=top-level directory status, 2=directory progress, 3=detailed examination |
| `-q, --quiet` | Suppress all output including statistics |
| `-ts, --timeout SECONDS` | Set execution timeout in seconds |
| `--help` | Show help message and exit |

### Parameters

- **root_path**: Starting directory for ownership examination (required)
- **owner_account**: Target owner account (optional, defaults to current user)

### Usage Examples

#### 1. Dry-Run Mode (Safe Testing)
```cmd
# Check what would be changed without making modifications
python src/fix_owner.py C:\ProblemDirectory
```

#### 2. Execute Changes
```cmd
# Actually change ownership of directories with orphaned SIDs
python src/fix_owner.py -x C:\ProblemDirectory Administrator
```

#### 3. Recursive Processing with Files
```cmd
# Process all subdirectories and files
python src/fix_owner.py -x -r -f C:\ProblemDirectory
```

#### 4. Verbose Output Levels
```cmd
# Level 1: Show top-level directory status only
python src/fix_owner.py -x -r -v 1 C:\ProblemDirectory

# Level 2: Show directory progress and summary
python src/fix_owner.py -x -r -v 2 C:\ProblemDirectory

# Level 3: Show detailed examination of each file/directory
python src/fix_owner.py -x -r -v 3 C:\ProblemDirectory
```

#### 5. With Timeout
```cmd
# Limit execution to 300 seconds (5 minutes)
python src/fix_owner.py -x -r -ts 300 C:\ProblemDirectory
```

#### 6. Quiet Mode
```cmd
# Run silently with no output
python src/fix_owner.py -x -r -q C:\ProblemDirectory
```

## How It Works

1. **SID Validation**: The script examines each directory/file to identify the current owner's SID
2. **Orphan Detection**: Checks if the SID corresponds to a valid, existing user account
3. **Ownership Change**: If the SID is orphaned/invalid, changes ownership to the specified account
4. **Statistics Tracking**: Counts processed items, changes made, and errors encountered
5. **Error Handling**: Continues processing even when individual operations fail

## Output Information

### Standard Output
- Final statistics showing directories/files processed
- Number of ownership changes made
- Total execution time
- Exception count

### Verbose Output (-v)
- Current path being examined
- Ownership change notifications
- All standard output information

### Quiet Mode (-q)
- No output whatsoever
- Useful for automated scripts

## Project Structure

```
fix-owner-script/
├── src/                          # Source code
│   ├── fix_owner.py             # Main script with all classes
│   ├── error_manager.py         # Error handling utilities
│   ├── filesystem_walker.py     # Directory traversal logic
│   ├── output_manager.py        # Output formatting and control
│   └── timeout_manager.py       # Execution timeout management
├── tests/                       # Test suite
│   ├── test_integration.py      # Integration tests
│   ├── test_argument_parsing.py # CLI argument tests
│   ├── test_security_manager.py # Security operation tests
│   ├── test_filesystem_walker.py# File system tests
│   ├── test_stats_tracker.py    # Statistics tests
│   ├── test_timeout_manager.py  # Timeout tests
│   ├── test_error_manager.py    # Error handling tests
│   ├── test_output_manager.py   # Output control tests
│   ├── test_all_core_functionality.py # Comprehensive test runner
│   └── test_error_integration.py# Error integration tests
├── old/                         # Legacy versions and examples
├── .kiro/                       # Kiro IDE specifications
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Modern Python packaging
└── README.md                   # This file
```

## Running Tests

### Prerequisites
Ensure you have the required dependencies installed:
```cmd
pip install -r requirements.txt
```

### Run All Tests
```cmd
# Run comprehensive test suite
python tests/test_all_core_functionality.py
```

### Run Individual Test Modules
```cmd
# Test argument parsing
python -m unittest tests.test_argument_parsing

# Test security manager
python -m unittest tests.test_security_manager

# Test file system walker
python -m unittest tests.test_filesystem_walker

# Test integration scenarios
python -m unittest tests.test_integration
```

### Run Tests with Coverage (if pytest is installed)
```cmd
pip install pytest pytest-cov
pytest tests/ --cov=src --cov-report=html
```

## Security Considerations

### Administrator Privileges
- **Required**: The script must run with Administrator privileges
- **Validation**: Privilege level is checked at startup
- **Error Handling**: Clear error messages for insufficient privileges

### SID Validation
- **Robust Checking**: Validates target owner account exists before processing
- **Domain Support**: Handles both local and domain accounts
- **Safety**: Prevents setting invalid or non-existent owners

### Audit Trail
- **Dry-Run Default**: Safe testing mode prevents accidental changes
- **Verbose Logging**: Optional detailed output for audit purposes
- **Statistics**: Comprehensive reporting of all operations

## Troubleshooting

### Common Issues

#### "Access Denied" Errors
- **Cause**: Insufficient privileges or file in use
- **Solution**: Run as Administrator, close applications using files

#### "Invalid Owner Account" Errors
- **Cause**: Specified owner account doesn't exist
- **Solution**: Verify account name, use domain\\username format if needed

#### "Module Not Found" Errors
- **Cause**: Missing pywin32 dependency
- **Solution**: Install with `pip install pywin32`

#### Performance Issues
- **Cause**: Large directory structures
- **Solution**: Use `-ts` timeout option, process in smaller batches

### Debug Mode
For additional debugging information, you can modify the script to enable debug output or use the verbose mode (`-v`) to see detailed processing information.

## Development

### Code Style
The project follows Python best practices:
- Type hints for better code documentation
- Comprehensive docstrings
- Modular design with clear separation of concerns
- Robust error handling

### Contributing
1. Follow the existing code style and structure
2. Add tests for new functionality
3. Update documentation as needed
4. Test on various Windows versions and scenarios

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please refer to the project repository or contact the system administrator team.