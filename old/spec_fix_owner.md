# Take Ownership of Directories and Files with Orphaned SIDs (fix_ownwer.ps1)

## Overview

This documentation and script help you recursively take ownership of directories and files when the current owner is an **invalid or orphaned SID** (i.e., the user or group no longer exists on the system/domain).  
Useful after system migrations, user deletions, or when inherited permissions cause issues with directory access.
There is an option to recurse subdirectories.
There is an option to examine files as well.
By default nothing will be changed. Changes will only occur if an "excute options" is specified.
---

## Requirements

- **Operating System:**  
  Windows 10/11 or Windows Server

- **Python Version:**  
  Python 3.13 or higher
  
- Python Imported Modules
  - Win32Security 2.1.0
     - PyProject: https://pypi.org/project/Win32Security
     - Github Repo: https://github.com/LassaInora/Win32Security
  - os
     - Docs: https://docs.python.org/3/library/os.html

- **Privileges:**  
  Run script as **Administrator**. 

- **User/Group Ownership:**  
  Set ownership to a valid local or domain account (configured in the script).  
  Example: `BUILTIN\Administrators`, or your own user account.

- **Error Handling**
  - It should catch exceptions (errors) and continue, while printing out error information

- **Statistics:**  
  - It should not change the ownership if it is already set
  - It should keep track of how many times it changed the ownership
  - There should be a final statistics output at the end specifyinhg
     - How many directories were traversed
     - How many files were traversed
     - How many exceptions were caught
     - How many directory ownerships where changed
     - How many file ownerships where changed
     - How long the process took in seconds

- **Options**
  - It should have an option (-x) to actually make the changes
  - It should have an option (-r) to recurse subdirectories or not
  - It should have an option (-f) to examine and change file ownership as well
  - It should have verbose option (-v) to outputs the name of the current path being examined
  - It should have a quiet option (-q) that outputs absolutely nothing, not even the final statistics
  - It should have an option (-ts) to terminate after a specified number of seconds have elapsed
  - It should have a help option (-h) that prints out all these options and an example usage



- **Input:**  
- Folder root path (edit in script)
- Options controlling the program execution

- **Output:**  
- Reports directories whose ownership was changed or failed
- Reports statistics indicating what was done

---

## Usage Instructions

1. **Edit the script** below:  
 Set the `$rootPath` to your starting folder and choose a valid owner in the `$takeOwner` variable.

2. **Run as Administrator:**  
 Run from a Command or Powershell window with elevated privileges.

3. Execution command Command
  `python fix_specs.py`

---

## Notes

- This script only changes ownership for directories where the owner SID is invalid.
- Always test on a sample directory first, and ensure you have adequate backups for critical data.
- For strength against ACL corruption, consider using `icacls /reset` as a preliminary step.

---

## License

MIT License (or your preferred license).
```

