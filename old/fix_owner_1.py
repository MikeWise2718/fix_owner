import os
import argparse
import time
import signal
import threading

import win32security
import win32api
import win32con

# Globals for statistics
stats = {
    'dirs_traversed': 0,
    'files_traversed': 0,
    'dirs_changed': 0,
    'files_changed': 0,
    'exceptions': 0
}
terminate = False

def timeout_handler(signum, frame):
    global terminate
    terminate = True

def is_sid_valid(sid):
    try:
        win32security.LookupAccountSid(None, sid)
        return True
    except win32security.error:
        return False

def set_owner(path, owner_sid, verbose=False):
    try:
        sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
        current_sid = sd.GetSecurityDescriptorOwner()
        if current_sid == owner_sid:
            return False  # Already owned
        if not is_sid_valid(current_sid):
            sd.SetSecurityDescriptorOwner(owner_sid, False)
            win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
            if verbose:
                print(f"Changed owner: {path}")
            return True
    except Exception as e:
        stats['exceptions'] += 1
        if verbose:
            print(f"Error ({path}): {e}")
    return False

def process_directory(root, owner_sid, args):
    for dirpath, dirnames, filenames in os.walk(root):
        if terminate:
            break
        stats['dirs_traversed'] += 1
        if args.v:
            print(f"Examining directory: {dirpath}")
        try:
            # Attempt owner change on directory
            if args.x and set_owner(dirpath, owner_sid, args.v):
                stats['dirs_changed'] += 1
        except Exception as e:
            stats['exceptions'] += 1
            if args.v:
                print(f"Error ({dirpath}): {e}")

        if not args.r:
            # Don't recurse
            dirnames[:] = []

        if args.f:
            # Process files
            for filename in filenames:
                if terminate:
                    break
                path = os.path.join(dirpath, filename)
                stats['files_traversed'] += 1
                if args.v:
                    print(f"Examining file: {path}")
                try:
                    if args.x and set_owner(path, owner_sid, args.v):
                        stats['files_changed'] += 1
                except Exception as e:
                    stats['exceptions'] += 1
                    if args.v:
                        print(f"Error ({path}): {e}")

        if terminate:
            break

def main():
    parser = argparse.ArgumentParser(
        description="Recursively fix ownership of directories/files with orphaned SIDs"
    )
    parser.add_argument("root", help="Root directory to start from")
    parser.add_argument("-x", action="store_true", help="Actually make changes")
    parser.add_argument("-r", action="store_true", help="Recurse into subdirectories")
    parser.add_argument("-f", action="store_true", help="Examine and change file ownership as well")
    parser.add_argument("-v", action="store_true", help="Verbose output")
    parser.add_argument("-q", action="store_true", help="Quiet output, not even stats")
    parser.add_argument("-ts", type=int, help="Terminate after N seconds")
    parser.add_argument("-owner", type=str, help="Account to become owner. Default: your user.", default=None)
    args = parser.parse_args()

    if args.ts:
        # Set up signal timer to terminate process
        signal.signal(signal.SIGABRT, timeout_handler)

    start_time = time.time()
    # Get owner SID
    if args.owner:
        owner, domain, typ = win32security.LookupAccountName(None, args.owner)
    else:
        user = win32api.GetUserNameEx(win32con.NameSamCompatible)
        owner, domain, typ = win32security.LookupAccountName(None, user)
    owner_sid = owner

    try:
        process_directory(args.root, owner_sid, args)
    except KeyboardInterrupt:
        print("\nTerminated by user.")

    elapsed = time.time() - start_time

    if not args.q:
        print("--- Statistics ---")
        print(f"Directories traversed: {stats['dirs_traversed']}")
        print(f"Files traversed: {stats['files_traversed']}")
        print(f"Directory ownerships changed: {stats['dirs_changed']}")
        print(f"File ownerships changed: {stats['files_changed']}")
        print(f"Exceptions caught: {stats['exceptions']}")
        print(f"Elapsed time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()
