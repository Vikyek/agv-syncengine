#!/usr/bin/env python3
import subprocess
import os
import sys
import shlex

VAULT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cmd(cmd, cwd=VAULT_DIR):
    """
    Executes a shell command safely without shell interpretation.

    @param cmd - The command to execute, either as a string or a list of arguments.
    @param cwd - The working directory to execute the command in (defaults to VAULT_DIR).
    @returns A tuple containing (return_code, stdout_string, stderr_string).
    @throws {Exception} implicitly caught and returned as (-1, "", error_string).
    """
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        res = subprocess.run(cmd, shell=False, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def main():
    if not os.path.exists(os.path.join(VAULT_DIR, ".git")):
        return

    # Fetch to check for remote changes
    run_cmd("git fetch")

    # Check for unstaged/uncommitted changes
    code, status, _ = run_cmd("git status --porcelain")
    if code != 0:
        return

    has_changes = len(status) > 0

    # Check if there are unpushed commits
    code, unpushed, _ = run_cmd("git log @{u}.. --oneline")
    has_unpushed = code == 0 and len(unpushed) > 0

    # Check if we are behind remote
    code, unpulled, _ = run_cmd("git log ..@{u} --oneline")
    has_unpulled = code == 0 and len(unpulled) > 0

    if not has_changes and not has_unpushed and not has_unpulled:
        # Nothing to do
        return

    print("🔄 [Auto Sync] Detecting configuration changes, unpushed, or unpulled commits...")

    if has_changes:
        # Add and commit changes
        run_cmd("git add -A")
        code, _, err = run_cmd(["git", "commit", "-m", "auto: synchronize vault config changes"])
        if code != 0:
            print(f"❌ [Auto Sync] Commit failed: {err}", file=sys.stderr)
            return

    # Track HEAD before pull
    _, head_before, _ = run_cmd("git rev-parse HEAD")

    # Run pull --rebase and push
    print("🔄 [Auto Sync] Syncing with remote repository...")
    pull_code, _, pull_err = run_cmd("git pull --rebase")
    if pull_code != 0:
        print(f"❌ [Auto Sync] Pull failed: {pull_err}", file=sys.stderr)
        return

    # Track HEAD after pull
    _, head_after, _ = run_cmd("git rev-parse HEAD")

    push_code, _, push_err = run_cmd("git push")
    if push_code != 0:
        print(f"❌ [Auto Sync] Push failed: {push_err}", file=sys.stderr)
    else:
        print("✅ [Auto Sync] Vault configurations successfully synchronized.")

    # Run Jules active listener pass
    jules_listener = os.path.join(VAULT_DIR, "scripts", "jules_listener.py")
    if os.path.exists(jules_listener):
        subprocess.run(["python3", jules_listener, "--once"], cwd=VAULT_DIR)

    # Apply setup if HEAD changed (we pulled something new)
    if head_before != head_after:
        print("🔄 [Auto Sync] New changes pulled. Applying setup...")
        apply_script = os.path.join(VAULT_DIR, "scripts", "apply_setup.sh")
        if os.path.exists(apply_script):
            subprocess.run(["bash", apply_script], cwd=VAULT_DIR)

if __name__ == "__main__":
    main()
