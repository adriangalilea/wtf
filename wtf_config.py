"""Configuration for wtf launcher using Pydantic"""

import os
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator


class WtfConfig(BaseModel):
    """Configuration for WTF launcher"""

    # System paths to exclude by default
    system_paths: List[str] = Field(
        default=["/bin/", "/sbin/", "/usr/bin/", "/usr/sbin/", "/System/"],
        description="Paths containing pre-installed system commands",
    )

    # Extra paths to search for commands
    extra_search_paths: List[str] = Field(
        default=[
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "~/.cargo/bin",
            "~/.local/bin",
            "/opt/homebrew/sbin",
            "/usr/local/sbin",
        ],
        description="Additional paths to search for commands",
    )

    # Command categories
    categories: Dict[str, List[str]] = Field(
        default={
            "git": ["git", "tig", "gh", "hub", "glab"],
            "package_managers": ["brew", "npm", "yarn", "pip", "cargo", "gem", "go", "mix"],
            "editors": ["vim", "nvim", "emacs", "nano", "hx", "code", "subl", "atom"],
            "file_tools": [
                "ls",
                "fd",
                "find",
                "rg",
                "grep",
                "ack",
                "ag",
                "tree",
                "ranger",
                "nnn",
                "eza",
            ],
            "network": ["curl", "wget", "ssh", "scp", "rsync", "nc", "telnet", "ftp"],
            "dev_tools": ["make", "gcc", "clang", "python", "node", "ruby", "rust", "go"],
        },
        description="Command categorization rules",
    )

    # Commands to never execute in preview
    dangerous_commands: List[str] = Field(
        default=[
            "cd",
            "pushd",
            "popd",
            "z",
            "zi",
            "autojump",
            "j",
            "rm",
            "rmdir",
            "mv",
            "cp",
            "dd",
            "mkfs",
        ],
        description="Commands that should never be executed for preview",
    )

    # Commands to exclude from listing
    excluded_commands: List[str] = Field(
        default=[
            # Python stuff
            "2to3*",
            "pydoc*",
            "pip3.*",
            "python3.*",
            "idle3.*",
            "wheel*",
            # Compression utilities (keep only main ones like zstd, xz, lz4)
            "lzmainfo",
            "unzstd",
            "pzstd",
            "xzdec",
            "unxz",
            "unlzma",
            "zstdless",
            "xzegrep",
            "xzfgrep",
            "xzless",
            "xzmore",
            "xzcmp",
            "xzdiff",
            "lz4cat",
            "lz4c",
            "zstdgrep",
            "lzless",
            "lzcmp",
            "zstdcat",
            "lzcat",
            "unlz4",
            "zstdmt",
            "lzdiff",
            "lzmadec",
            "lzgrep",
            "lzmore",
            "lzfgrep",
            "xzgrep",
            "lzma",
            "lzegrep",
            "xzcat",
            # Build tools internal commands
            "msgconv",
            "msggrep",
            "msgcomm",
            "autopoint",
            "gettextize",
            "msgattrib",
            "msgcat",
            "msgcmp",
            "msgen",
            "msgexec",
            "msgfilter",
            "msgfmt",
            "msginit",
            "msgmerge",
            "msgunfmt",
            "msguniq",
            "ngettext",
            "xgettext",
            "gettext",
            "gettext.sh",
            "envsubst",
            # Config tools
            "*-config",
            "onig-config",
            "pcre2-config",
            # SSL/crypto utilities
            "c_rehash",
            # Test utilities
            "pcre2grep",
            "pcre2test",
            # Package manager internals
            "pip-*",
            "easy_install*",
            "corepack",
            # Git internals
            "git-receive-pack",
            "git-upload-*",
            "git-shell",
            "git-cvsserver",
            # Other noise
            "fish_indent",
            "fish_key_reader",
            "recode-sr-latin",
            # Docker/k8s internals
            "docker-credential-*",
            "kubectl.docker",
            "compose-bridge",
            "hub-tool",
            # Preview scripts
            "fzf-preview.sh",
            # Utilities I likely don't need
            "zipmerge",
            "ziptool",
            "zipcmp",
            "scalar",
            "gofmt",
            "git2",
        ],
        description="Commands to exclude from listing (supports wildcards)",
    )

    # Display preferences
    show_paths: bool = Field(default=True, description="Show paths in command list")
    preview_enabled: bool = Field(default=True, description="Enable preview pane by default")

    @field_validator("extra_search_paths")
    @classmethod
    def expand_paths(cls, paths: List[str]) -> List[str]:
        """Expand ~ in paths"""
        return [os.path.expanduser(p) for p in paths]

    def save(self, path: Path):
        """Save config to file"""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Path) -> "WtfConfig":
        """Load config from file or create default"""
        if path.exists():
            try:
                with open(path) as f:
                    return cls.model_validate_json(f.read())
            except Exception:
                # Invalid config, use defaults
                pass

        # Create default config
        config = cls()
        config.save(path)
        return config


# Global config instance
CONFIG_PATH = Path.home() / ".config" / "wtf" / "config.json"
config = WtfConfig.load(CONFIG_PATH)

