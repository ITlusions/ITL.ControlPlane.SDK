#!/usr/bin/env python3
"""
Semantic Version Manager for ITL ControlPlane SDK

Handles version detection, bumping, and validation based on:
- Git tags (v1.0.0 format)
- Branch context (main, develop, feature/*)
- Conventional commits for semantic versioning
- Build metadata from GitHub Actions

Usage:
    python scripts/version.py --get-version
    python scripts/version.py --bump major|minor|patch
    python scripts/version.py --validate
    python scripts/version.py --set-pyproject <version>
"""

import argparse
import os
import re
import subprocess
import sys
import tomllib
import tomli_w
from pathlib import Path
from typing import Optional, Tuple


class SemanticVersion:
    """Semantic version handler (MAJOR.MINOR.PATCH)."""

    def __init__(self, major: int, minor: int, patch: int):
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """Parse semantic version from string like '1.2.3'."""
        match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def bump_major(self) -> "SemanticVersion":
        """Bump major version (1.0.0 -> 2.0.0)."""
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        """Bump minor version (1.0.0 -> 1.1.0)."""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        """Bump patch version (1.0.0 -> 1.0.1)."""
        return SemanticVersion(self.major, self.minor, self.patch + 1)


class VersionManager:
    """Manage versioning for ITL ControlPlane SDK."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path.cwd()
        self.pyproject_path = self.repo_root / "pyproject.toml"

    def get_latest_tag(self) -> Optional[str]:
        """Get latest git tag matching v*.*.* format."""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--match", "v[0-9]*", "--abbrev=0"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def get_current_branch(self) -> str:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_git_sha(self, short: bool = False) -> str:
        """Get current git commit SHA."""
        try:
            args = ["git", "rev-parse"]
            if short:
                args.append("--short")
            args.append("HEAD")
            result = subprocess.run(
                args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"

    def get_commit_count_since_tag(self, tag: str) -> int:
        """Get number of commits since a tag."""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{tag}..HEAD"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            return 0

    def get_pyproject_version(self) -> str:
        """Get version from pyproject.toml."""
        with open(self.pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]

    def set_pyproject_version(self, version: str) -> None:
        """Set version in pyproject.toml."""
        with open(self.pyproject_path, "rb") as f:
            data = tomllib.load(f)
        data["project"]["version"] = version
        with open(self.pyproject_path, "wb") as f:
            tomli_w.dump(data, f)
        print(f"✅ Set pyproject.toml version to {version}")

    def detect_version_context(self) -> dict:
        """Detect current version context from git state."""
        current_branch = self.get_current_branch()
        latest_tag = self.get_latest_tag()
        git_sha = self.get_git_sha(short=True)

        # Determine if we're on a release tag
        is_release_tag = current_branch.startswith("v") or os.getenv(
            "GITHUB_REF", ""
        ).startswith("refs/tags/v")

        # Parse base version
        if latest_tag:
            base_version = SemanticVersion.parse(latest_tag)
        else:
            base_version = SemanticVersion(1, 0, 0)

        # Calculate dev metadata
        commit_count = self.get_commit_count_since_tag(latest_tag) if latest_tag else 0

        return {
            "is_release": is_release_tag,
            "branch": current_branch,
            "base_version": str(base_version),
            "latest_tag": latest_tag,
            "git_sha": git_sha,
            "commit_count": commit_count,
        }

    def get_version_string(self) -> str:
        """
        Generate appropriate version string based on context.

        Returns:
        - Release tags (v1.0.0): "1.0.0"
        - Main branch: "1.0.0.dev{run_number}+{sha}"
        - Develop branch: "1.0.0.dev{run_number}+{sha}"
        - Feature branch: "1.0.0.dev{run_number}+feature.{branch_name}.{sha}"
        - Local dev: "1.0.0.dev0+{sha}"
        """
        context = self.detect_version_context()

        if context["is_release"]:
            # Release tag: use exact version
            return context["base_version"]

        # Development build
        base = context["base_version"]
        branch = context["branch"]
        sha = context["git_sha"]

        # Get run number from GitHub Actions or use 0 for local
        run_num = os.getenv("GITHUB_RUN_NUMBER", "0")

        if branch.startswith("feature/"):
            # Feature branch: include feature name
            feature_name = branch.replace("feature/", "").replace("/", "-")
            return f"{base}.dev{run_num}+{feature_name}.{sha}"
        elif branch == "main":
            # Main branch: standard dev version
            return f"{base}.dev{run_num}+main.{sha}"
        elif branch == "develop":
            # Develop branch: standard dev version
            return f"{base}.dev{run_num}+develop.{sha}"
        else:
            # Other branches: include branch name
            clean_branch = branch.replace("/", "-")
            return f"{base}.dev{run_num}+{clean_branch}.{sha}"

    def validate_version(self, version: str) -> Tuple[bool, str]:
        """Validate version string format."""
        # Allow semantic versions with dev and build metadata
        pattern = r"^\d+\.\d+\.\d+(?:\.dev\d+)?(?:\+[a-zA-Z0-9.-]+)?$"
        if re.match(pattern, version):
            return True, "Valid version"
        return False, f"Invalid version format: {version}"

    def create_release_tag(self, version: str, message: str = "") -> bool:
        """Create a git release tag."""
        if not message:
            message = f"Release version {version}"

        try:
            # Validate version
            valid, msg = self.validate_version(version)
            if not valid:
                print(f"❌ {msg}")
                return False

            # Create tag
            tag_name = f"v{version}" if not version.startswith("v") else version
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", message],
                cwd=self.repo_root,
                check=True,
                capture_output=True,
            )
            print(f"✅ Created tag: {tag_name}")
            print(f"   Push with: git push origin {tag_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create tag: {e}")
            return False

    def bump_version(self, bump_type: str) -> str:
        """Bump version and update pyproject.toml."""
        if bump_type not in ["major", "minor", "patch"]:
            raise ValueError(f"Invalid bump type: {bump_type}")

        current = SemanticVersion.parse(self.get_pyproject_version())

        if bump_type == "major":
            new_version = current.bump_major()
        elif bump_type == "minor":
            new_version = current.bump_minor()
        else:  # patch
            new_version = current.bump_patch()

        version_str = str(new_version)
        self.set_pyproject_version(version_str)
        return version_str


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Version Manager for ITL ControlPlane SDK"
    )
    parser.add_argument(
        "--get-version",
        action="store_true",
        help="Get current version string",
    )
    parser.add_argument(
        "--detect-context",
        action="store_true",
        help="Detect and display version context",
    )
    parser.add_argument(
        "--validate",
        metavar="VERSION",
        help="Validate version string format",
    )
    parser.add_argument(
        "--bump",
        metavar="TYPE",
        choices=["major", "minor", "patch"],
        help="Bump version (major, minor, or patch)",
    )
    parser.add_argument(
        "--set-pyproject",
        metavar="VERSION",
        help="Set version in pyproject.toml",
    )
    parser.add_argument(
        "--create-tag",
        metavar="VERSION",
        help="Create a git release tag",
    )
    parser.add_argument(
        "--message",
        metavar="MSG",
        help="Message for git tag",
    )
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Repository root path",
    )

    args = parser.parse_args()
    manager = VersionManager(Path(args.repo_root) if args.repo_root else None)

    try:
        if args.get_version:
            version = manager.get_version_string()
            print(version)
            return 0

        if args.detect_context:
            context = manager.detect_version_context()
            print("\n📊 Version Context:")
            print(f"  Branch: {context['branch']}")
            print(f"  Is Release: {context['is_release']}")
            print(f"  Base Version: {context['base_version']}")
            print(f"  Latest Tag: {context['latest_tag']}")
            print(f"  Git SHA: {context['git_sha']}")
            print(f"  Commits Since Tag: {context['commit_count']}")
            print(f"\n🔖 Full Version: {manager.get_version_string()}\n")
            return 0

        if args.validate:
            valid, msg = manager.validate_version(args.validate)
            print(msg)
            return 0 if valid else 1

        if args.bump:
            version = manager.bump_version(args.bump)
            print(f"✅ Bumped to version: {version}")
            return 0

        if args.set_pyproject:
            valid, msg = manager.validate_version(args.set_pyproject)
            if not valid:
                print(f"❌ {msg}")
                return 1
            manager.set_pyproject_version(args.set_pyproject)
            return 0

        if args.create_tag:
            if manager.create_release_tag(args.create_tag, args.message or ""):
                return 0
            else:
                return 1

        # Default: show current version
        version = manager.get_version_string()
        print(f"Current version: {version}")
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
