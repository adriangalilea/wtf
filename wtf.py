#!/usr/bin/env python3
"""WTF - What The F*** Can I Run?

Fast command launcher. No bullshit.
"""

import fnmatch
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Import config
from wtf_config import config

# Config location - no XDG bullshit, just put it where it belongs
CONFIG_DIR = Path.home() / ".config" / "wtf"
HISTORY_FILE = CONFIG_DIR / "history.json"

# Create config dir if needed
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def find_executables() -> Dict[str, List[str]]:
    """Find all executables on the system. Fast."""
    commands = defaultdict(list)

    # Standard PATH locations
    path_dirs = os.environ.get("PATH", "").split(":")

    # Additional locations from config
    extra_dirs = config.extra_search_paths

    all_dirs = list(set(path_dirs + extra_dirs))

    for dir_path in all_dirs:
        if not os.path.exists(dir_path):
            continue

        try:
            for entry in os.scandir(dir_path):
                if entry.is_file() and os.access(entry.path, os.X_OK):
                    commands[entry.name].append(entry.path)
        except (PermissionError, OSError):
            pass

    # Homebrew casks (macOS apps)
    try:
        result = subprocess.run(
            ["brew", "list", "--cask"], capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0:
            for app in result.stdout.strip().split("\n"):
                if app:
                    commands[f"APP:{app}"] = [app]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return dict(commands)


def load_history() -> Dict[str, float]:
    """Load command usage history for frecency scoring."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_history(history: Dict[str, float]):
    """Save command usage history."""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


def update_history(command: str):
    """Update history with new command usage."""
    history = load_history()

    # Simple frecency: recent usage gets higher score
    now = time.time()
    if command in history:
        # Decay old score and add new usage
        old_score = history[command]
        history[command] = old_score * 0.9 + now / 1000000
    else:
        history[command] = now / 1000000

    save_history(history)


def categorize_command(cmd: str, path: str = "") -> str:
    """Categorize a command. Fast heuristics."""
    cmd_lower = cmd.lower()

    if cmd.startswith("APP:"):
        return "[Apps]"

    # Git tools
    if "git" in cmd_lower or cmd in ["tig", "gh", "hub", "glab"]:
        return "[Git]"

    # Package managers
    if cmd in ["brew", "npm", "yarn", "pip", "cargo", "gem", "go", "mix"]:
        return "[Package]"

    # Editors
    if cmd in ["vim", "nvim", "emacs", "nano", "hx", "code", "subl", "atom"]:
        return "[Editor]"

    # File tools
    if cmd in ["ls", "fd", "find", "rg", "grep", "ack", "ag", "tree", "ranger", "nnn"]:
        return "[Files]"

    # Network
    if cmd in ["curl", "wget", "ssh", "scp", "rsync", "nc", "telnet", "ftp"]:
        return "[Network]"

    # Dev tools
    if cmd in ["make", "gcc", "clang", "python", "node", "ruby", "rust", "go"]:
        return "[Dev]"

    return "[Cmd]"


def launch_fzf(items: List[Tuple[str, str, str]], show_all=False) -> str:
    """Launch fzf with items. Returns selected command or empty string."""
    # Check fzf exists
    if not subprocess.run(["which", "fzf"], capture_output=True).returncode == 0:
        print("Install fzf first: brew install fzf", file=sys.stderr)
        sys.exit(1)

    # Format items for fzf with tab delimiter
    fzf_input = []
    for category, cmd, path in items:
        # Format with padding for alignment
        cat_display = f"{category:<10}"
        cmd_display = f"{cmd:<20}"

        # Smart path shortening
        if path.startswith("/opt/homebrew/"):
            path_display = path.replace("/opt/homebrew/", "~brew/")
        elif path.startswith("/usr/local/"):
            path_display = path.replace("/usr/local/", "~local/")
        elif path.startswith("/Users/adrian/"):
            path_display = path.replace("/Users/adrian/", "~/")
        elif path.startswith("/System/"):
            path_display = path.replace("/System/", "~sys/")
        else:
            path_display = path

        # Further shorten if still too long
        if len(path_display) > 45:
            path_display = "..." + path_display[-42:]

        # Use tab as delimiter: category \t command \t path_display \t full_path
        line = f"{cat_display}\t{cmd_display}\t{path_display:<45}\t{path}"
        fzf_input.append(line)

    # Launch fzf with tab delimiter and preview
    try:
        # Use external preview script to avoid quote hell
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wtf_preview.sh")
        preview_cmd = f"{script_path} {{2}} {{4}}"

        # Force bash shell for preview
        env = os.environ.copy()
        env["SHELL"] = "/bin/bash"

        proc = subprocess.Popen(
            [
                "fzf",
                "--delimiter",
                "\t",
                "--with-nth",
                "1,2,3",  # Show category, command, and short path
                "--nth",
                "2",  # Search only in the command name (field 2)
                "--prompt",
                "WTF? > ",
                "--preview",
                preview_cmd,
                "--preview-window",
                "right:60%:wrap",
                "--bind",
                "ctrl-/:toggle-preview",
                "--height",
                "100%",
                "--layout",
                "reverse",
                "--info",
                "inline",
                "--header",
                f"{'ALL COMMANDS' if show_all else 'USER INSTALLED'} | Enter: select | Ctrl+/: toggle preview | Esc: cancel",
                "-i",
                "--ansi",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        stdout, stderr = proc.communicate(input="\n".join(fzf_input))

        if proc.returncode == 0 and stdout.strip():
            # Parse the selected line to get the full path (4th field)
            parts = stdout.strip().split("\t")
            if len(parts) >= 4:
                return parts[3]  # Return the full path from 4th field

    except Exception as e:
        print(f"fzf failed: {e}", file=sys.stderr)

    return ""


def get_all_commands(include_system=False) -> List[Tuple[str, str, str]]:
    """Get all available commands with categories."""
    commands = find_executables()
    history = load_history()

    # System paths from config
    system_paths = config.system_paths

    items = []
    seen = set()

    for cmd, paths in commands.items():
        # Use first path, they're usually the same command
        path = paths[0]

        # Get the actual command name (remove APP: prefix if present)
        actual_cmd = cmd[4:] if cmd.startswith("APP:") else cmd

        # Skip duplicates based on actual command name
        if actual_cmd in seen:
            continue
        seen.add(actual_cmd)

        # Check if command is excluded
        is_excluded = any(
            fnmatch.fnmatch(actual_cmd, pattern) for pattern in config.excluded_commands
        )
        if is_excluded:
            continue

        # Filter out system commands unless requested
        if not include_system:
            is_system = any(path.startswith(sp) for sp in system_paths)
            if is_system:
                continue

        category = categorize_command(cmd, path)

        # For apps, the cmd already has APP: prefix, so store it as the path
        if cmd.startswith("APP:"):
            items.append((category, actual_cmd, cmd))  # Remove APP: prefix for display
        else:
            items.append((category, cmd, path))

    # Sort by frecency if available, otherwise by name
    items.sort(key=lambda x: -history.get(x[1], 0))

    return items


def shell_init(shell: str):
    """Generate shell initialization code."""
    if shell == "fish":
        print("""
function wtf --description "What the f*** can I run?"
    command wtf | read -l cmd
    and commandline -r $cmd
end

bind \\ew 'wtf'
""")
    elif shell in ["bash", "zsh"]:
        print("""
wtf() {
    local cmd
    cmd=$(command wtf)
    if [ -n "$cmd" ]; then
        # Insert command into prompt without executing
        if [ -n "$ZSH_VERSION" ]; then
            print -z "$cmd"
        elif [ -n "$BASH_VERSION" ]; then
            READLINE_LINE="$cmd"
            READLINE_POINT=${#cmd}
        fi
    fi
}

# For zsh
if [ -n "$ZSH_VERSION" ]; then
    bindkey '^[w' 'wtf'
# For bash  
elif [ -n "$BASH_VERSION" ]; then
    bind -x '"\\ew": "wtf"'
fi
""")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            if len(sys.argv) > 2:
                shell_init(sys.argv[2])
            else:
                print("Usage: wtf init <shell>", file=sys.stderr)
                sys.exit(1)
        elif sys.argv[1] in ["--list", "-l"]:
            # List mode - print everything to stdout
            include_system = "--all" in sys.argv
            items = get_all_commands(include_system=include_system)

            print(f"Total commands found: {len(items)}")
            print(f"Mode: {'ALL commands' if include_system else 'User commands only'}")
            print("\nAll commands:")
            print("-" * 60)

            for category, cmd, path in items:
                print(f"{category:<10} {cmd:<25} {path}")

            sys.exit(0)
        elif sys.argv[1] == "config":
            # Edit configuration
            config_path = Path.home() / ".config" / "wtf" / "config.json"
            if not config_path.exists():
                # Create default config
                config.save(config_path)

            # Open in editor
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(config_path)])
            sys.exit(0)
        elif sys.argv[1] in ["--all", "-a"]:
            # Show all commands including system
            items = get_all_commands(include_system=True)
            selected = launch_fzf(items, show_all=True)

            if selected:
                # Update frecency tracking
                if selected.startswith("APP:"):
                    update_history(selected[4:])  # Just the app name
                    print(f"open -a '{selected[4:]}'")
                else:
                    update_history(os.path.basename(selected))  # Just the command name
                    print(os.path.basename(selected))  # Just the command name, not full path
            sys.exit(0)
        elif sys.argv[1] in ["-h", "--help"]:
            print("wtf - What The F*** Can I Run?")
            print("\nUsage:")
            print("  wtf              Show user-installed commands only")
            print("  wtf --all/-a     Show ALL commands (including system)")
            print("  wtf config       Edit configuration file")
            print("  wtf --list/-l    List all commands to stdout (for piping)")
            print("  wtf init <shell> Generate shell integration")
            print("\nConfig file: ~/.config/wtf/config.json")
            sys.exit(0)
    else:
        # Interactive mode - default to user-installed only
        items = get_all_commands(include_system=False)
        selected = launch_fzf(items)

        if selected:
            # Update frecency tracking
            if selected.startswith("APP:"):
                update_history(selected[4:])  # Just the app name
                print(f"open -a '{selected[4:]}'")
            else:
                update_history(os.path.basename(selected))  # Just the command name
                print(os.path.basename(selected))  # Just the command name, not full path


if __name__ == "__main__":
    main()

