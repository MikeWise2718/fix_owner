# Fix Owner Script

A Python utility for recursively taking ownership of directories and files with orphaned Security Identifiers (SIDs) on Windows systems. This tool is particularly useful after system migrations, user deletions, or when inherited permissions cause access issues.

## Features

- **Recursive Processing**: Traverse directory structures with optional file processing
- **Dry-Run Mode**: Test operations safely before making actual changes
- **Comprehensive Statistics**: Track directories, files, changes, and errors
- **SID Analysis**: Detailed ownership analysis with valid/orphaned SID identification
- **Timeout Support**: Prevent indefinite execution on large directory structures
- **Flexible Output**: Verbose, standard, or quiet output modes
- **Robust Error Handling**: Continue processing after individual failures
- **Timestamped Failure Logging**: Automatic creation of failure logs with execution timestamps
- **Windows Security Integration**: Native Windows API integration via pywin32
- **Modular Architecture**: Clean separation of concerns across specialized modules
- **Consistent Output**: Centralized color management and formatting

## Requirements

- **Operating System**: Windows 10/11 or Windows Server
- **Python**: 3.13 or higher
- **Privileges**: Administrator privileges required for security operations
- **Dependencies**: 
  - pywin32 for Windows API access
  - colorama for colored output
  - PyYAML for YAML export functionality (optional - install with `pip install PyYAML`)

## Installation

1. **Clone or download** the script files to your local system

2. **Install Python dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```
   
   **Optional**: For YAML export functionality, install PyYAML:
   ```cmd
   pip install PyYAML
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
| `-to, --timeout SECONDS` | Set execution timeout in seconds |
| `-ts, --track-sids` | Enable SID tracking and generate ownership analysis report |
| `--help` | Show help message and exit |

### Parameters

- **root_path**: Starting directory for ownership examination (required)
- **owner_account**: Target owner account (optional, defaults to current logged-in user in DOMAIN\\username format)

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
python src/fix_owner.py -x -r -to 300 C:\ProblemDirectory
```

#### 6. Quiet Mode
```cmd
# Run silently with no output
python src/fix_owner.py -x -r -q C:\ProblemDirectory
```

#### 7. SID Tracking and Analysis
```cmd
# Generate detailed SID ownership analysis report
python src/fix_owner.py -x -r -ts C:\ProblemDirectory

# Combine with verbose output for comprehensive reporting
python src/fix_owner.py -x -r -v 2 -ts C:\ProblemDirectory
```

## How It Works

1. **SID Validation**: The script examines each directory/file to identify the current owner's SID
2. **Orphan Detection**: Checks if the SID corresponds to a valid, existing user account
3. **Ownership Change**: If the SID is orphaned/invalid, changes ownership to the specified account
4. **Statistics Tracking**: Counts processed items, changes made, and errors encountered
5. **SID Analysis**: Optionally tracks all SIDs encountered and generates detailed ownership reports
6. **Error Handling**: Continues processing even when individual operations fail
7. **Comprehensive Reporting**: Provides detailed statistics and optional SID ownership analysis

## Output Information

### Standard Output
- Final statistics showing directories/files processed
- Number of ownership changes made
- Total execution time
- Exception count

### Verbose Output (-v)
- **Level 1**: Top-level directory status and statistics
- **Level 2**: Directory progress and processing summaries
- **Level 3**: Detailed examination of each file/directory
- Current path being examined
- Ownership change notifications
- All standard output information

### SID Tracking Output (-ts)
- Comprehensive SID ownership analysis report
- Valid vs orphaned SID identification
- File and directory counts per SID
- Account name resolution for valid SIDs
- Detailed legend and statistics
- **JSON Export**: Automatic export to timestamped JSON file (`output/sid_ownership_analysis_YYYYMMDD_HHMMSS.json`)
- **YAML Remediation Plan**: Automatic export of orphaned SID remediation plan (`output/sid_orphaned_remediation_YYYYMMDD_HHMMSS.yaml`)

### Quiet Mode (-q)
- No output whatsoever
- Useful for automated scripts

### Failure Logging (NEW)
The script now automatically creates timestamped failure logs when critical errors occur:

- **Automatic Timestamping**: All failure logs include the execution start time in the filename
- **Critical Failure Logs**: `output/fix_owner_critical_failures_YYYYMMDD_HHMMSS.log`
- **Operation Failure Logs**: `output/fix_owner_filesystem_failures_YYYYMMDD_HHMMSS.log`
- **Detailed Context**: Each log includes full exception details, stack traces, and operation context
- **Verbose Integration**: Log file creation is reported in verbose mode (level 2+)

Example failure log filename: `output/fix_owner_critical_failures_20250804_114459.log`

The logs contain:
- Timestamp of the failure
- Error category and path (if applicable)
- Complete exception details and stack trace
- Additional context about the operation that failed
- Suggestions for resolution

**Note**: The `output` directory is automatically created if it doesn't exist.

### SID Ownership Data Export (NEW)
When SID tracking is enabled (`-ts` flag), the script automatically exports comprehensive ownership data in two formats:

#### JSON Analysis Export
- **Automatic JSON Export**: `output/sid_ownership_analysis_YYYYMMDD_HHMMSS.json`
- **Complete Data**: All SID information, statistics, and analysis insights
- **Structured Format**: Organized by SID with detailed metrics and percentages
- **Analysis Insights**: Most common SIDs, distribution patterns, and recommendations
- **Machine Readable**: Perfect for further analysis, reporting, or integration

Example JSON export filename: `output/sid_ownership_analysis_20250804_114459.json`

#### YAML Remediation Plan Export
- **Automatic YAML Export**: `output/sid_orphaned_remediation_YYYYMMDD_HHMMSS.yaml`
- **Orphaned SIDs Only**: Focuses specifically on SIDs that need remediation
- **Remediation Instructions**: Detailed steps and commands for fixing each orphaned SID
- **Target Owner Mapping**: Maps each orphaned SID to the specified target owner account
- **Priority Assessment**: Risk analysis and priority levels for remediation
- **Human Readable**: Easy-to-read format for administrators and documentation

Example YAML export filename: `output/sid_orphaned_remediation_20250804_114459.yaml`

#### JSON File Contents:
- **Metadata**: Report type, generation timestamp, format version
- **Summary**: Total counts, percentages, and execution information
- **SID Details**: Complete information for each encountered SID including:
  - Account name resolution
  - File and directory counts
  - Validity status (VALID/ORPHANED/UNKNOWN)
  - Percentage distributions
  - Comparative analysis flags
- **Insights**: Most common SIDs, distribution analysis, and actionable recommendations

#### YAML File Contents:
- **Metadata**: Remediation plan information and generation details
- **Remediation Info**: Target owner account and command examples
- **Orphaned SIDs**: For each orphaned SID:
  - Current status and description
  - Impact analysis (files/directories affected, percentages, priority)
  - Recommended remediation steps and commands
  - Additional info (SID type, likely cause, risk assessment)

Example JSON structure:
```json
{
  "metadata": {
    "report_type": "SID Ownership Analysis",
    "generated_by": "fix_owner script",
    "format_version": "1.0"
  },
  "summary": {
    "export_timestamp": "2025-08-04 11:45:00",
    "execution_start_timestamp": "20250804 at 114500",
    "total_files_analyzed": 150,
    "total_directories_analyzed": 25,
    "unique_sids_found": 3,
    "valid_sids_count": 2,
    "orphaned_sids_count": 1
  },
  "sids": {
    "S-1-5-21-123...": {
      "account_name": "DOMAIN\\User1",
      "status": "VALID",
      "occurrences": {"files": 120, "directories": 15, "total": 135},
      "percentages": {"files": 80.0, "directories": 60.0, "total": 77.14},
      "analysis": {"is_most_common_overall": true}
    }
  },
  "insights": {
    "most_common_sids": {...},
    "distribution": {...},
    "recommendations": [...]
  }
}
```

Example YAML structure:
```yaml
metadata:
  title: Orphaned SID Remediation Plan
  description: List of orphaned SIDs found during ownership analysis and their recommended replacements
  generated_by: fix_owner script
  export_timestamp: "2025-08-04 11:45:00"

remediation_info:
  target_owner_account: "DOMAIN\\Administrator"
  total_orphaned_sids: 2
  remediation_command: 'python fix_owner.py <path> -x -r -f "DOMAIN\\Administrator"'

orphaned_sids:
  S-1-5-21-123456789-123456789-123456789-1001:
    current_status:
      sid: S-1-5-21-123456789-123456789-123456789-1001
      account_name: "<Unknown SID>"
      status: ORPHANED
    impact_analysis:
      files_affected: 45
      directories_affected: 8
      total_items_affected: 53
      remediation_priority: HIGH
    recommended_remediation:
      new_owner_account: "DOMAIN\\Administrator"
      action_required: "Change ownership to specified account"
      command_example: 'python fix_owner.py <path> -x -r -f "DOMAIN\\Administrator"'
```

## Project Structure

```
fix-owner-script/
├── src/                          # Source code modules
│   ├── fix_owner.py             # Main entry point and orchestration (26,060 bytes)
│   ├── output_manager.py        # Centralized output control and formatting (25,201 bytes)
│   ├── filesystem_walker.py     # Directory traversal and file processing (24,612 bytes)
│   ├── error_manager.py         # Exception handling and error categorization (15,996 bytes)
│   ├── security_manager.py      # Windows security operations and SID management (13,596 bytes)
│   ├── sid_tracker.py           # SID tracking and ownership analysis reporting (13,281 bytes)
│   ├── stats_tracker.py         # Execution statistics tracking and reporting (7,801 bytes)
│   ├── common.py                # Shared utilities, constants, and color definitions (5,747 bytes)
│   └── timeout_manager.py       # Execution timeout management (4,909 bytes)
├── tests/                       # Comprehensive test suite
├── output/                      # Generated files directory (created automatically)
│   ├── test_integration.py      # Integration and end-to-end tests
│   ├── test_argument_parsing.py # CLI argument validation tests
│   ├── test_security_manager.py # Windows security operation tests
│   ├── test_filesystem_walker.py# File system traversal tests
│   ├── test_stats_tracker.py    # Statistics tracking tests
│   ├── test_sid_tracker.py      # SID analysis and reporting tests
│   ├── test_timeout_manager.py  # Timeout handling tests
│   ├── test_error_manager.py    # Error handling and categorization tests
│   ├── test_output_manager.py   # Output control and formatting tests
│   ├── test_all_core_functionality.py # Comprehensive test runner
│   └── test_error_integration.py# Error integration tests
├── .kiro/                       # Kiro IDE specifications and steering
│   └── steering/                # Project documentation and guidelines
├── old/                         # Legacy versions and examples
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Modern Python packaging configuration
├── README_TESTING.md           # Comprehensive testing documentation
└── README.md                   # This file
```

### Module Architecture

#### **common.py** - Shared Foundation
- **Color Constants**: Centralized color definitions for consistent output formatting
- **Application Constants**: Version, exit codes, path limits, formatting widths
- **Utility Functions**: Timestamp handling, path validation, safe exit, module setup
- **Timestamp Functions**: Execution start time recording and filename formatting for failure logs
- **Output Directory Management**: Automatic creation and path management for generated files
- **Availability Flags**: Windows API availability checks (PYWIN32_AVAILABLE, WIN32SECURITY_AVAILABLE)

#### **fix_owner.py** - Main Orchestration
- **Entry Point**: Command-line interface and argument parsing
- **Workflow Coordination**: Manages execution phases and component integration
- **Configuration Management**: ExecutionOptions and ExecutionStats dataclasses

#### **security_manager.py** - Windows Security Operations
- **SID Operations**: Get current owner, validate SIDs, set ownership
- **Account Resolution**: Convert account names to SIDs, handle domain accounts
- **Windows API Integration**: Comprehensive pywin32 wrapper functionality

#### **output_manager.py** - Output Control
- **Verbosity Management**: Multiple output levels (0-3) and quiet mode
- **Formatted Output**: Consistent message formatting with color constants
- **Stream Management**: Separate stdout/stderr handling with fallbacks

#### **filesystem_walker.py** - File System Processing
- **Directory Traversal**: Recursive directory walking with os.walk()
- **Ownership Processing**: File and directory ownership examination and changes
- **Progress Tracking**: Integration with OutputManager for progress reporting

#### **stats_tracker.py** - Statistics Management
- **Counter Management**: Tracks directories, files, changes, exceptions
- **Timing Operations**: High-precision execution timing
- **Report Generation**: Formatted statistics reports with color constants

#### **sid_tracker.py** - SID Analysis
- **SID Collection**: Tracks all SIDs encountered during processing
- **Validity Checking**: Identifies valid vs orphaned SIDs
- **Report Generation**: Comprehensive ownership analysis reports
- **JSON Export**: Timestamped export of complete SID ownership data with analysis insights
- **YAML Remediation Export**: Timestamped export of orphaned SID remediation plans with target owner mapping

#### **error_manager.py** - Error Handling
- **Exception Categorization**: Classifies errors by type and severity
- **Error Recovery**: Provides recovery suggestions and solutions
- **Statistics Integration**: Tracks error counts and patterns
- **Timestamped Failure Logging**: Creates detailed failure logs with execution timestamps

#### **timeout_manager.py** - Execution Control
- **Timeout Management**: Prevents indefinite execution on large structures
- **Timer Operations**: Threading-based timeout implementation
- **Context Manager**: Safe resource cleanup and timeout handling

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
# Test individual components
python tests/test_security_manager.py
python tests/test_stats_tracker.py
python tests/test_filesystem_walker.py
python tests/test_output_manager.py
python tests/test_sid_tracker.py

# Test argument parsing
python -m unittest tests.test_argument_parsing

# Test integration scenarios
python tests/test_integration.py
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
- **Solution**: Use `-to` timeout option, process in smaller batches

### Debug Mode
For additional debugging information, you can modify the script to enable debug output or use the verbose mode (`-v`) to see detailed processing information.

## Development

### Code Style
The project follows Python best practices:
- **Type hints** for better code documentation
- **Comprehensive docstrings** for all modules and functions
- **Modular design** with clear separation of concerns across 9 specialized modules
- **Centralized utilities** in common.py for shared functionality
- **Consistent color management** using centralized color constants
- **Robust error handling** with comprehensive error categorization
- **Standardized imports** with relative/absolute fallback patterns

### Contributing
1. Follow the existing code style and structure
2. Add tests for new functionality
3. Update documentation as needed
4. Test on various Windows versions and scenarios

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please refer to the project repository or contact the system administrator team.