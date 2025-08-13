"""
Gitignore pattern matching utilities.
Implements .gitignore pattern matching for filtering files and directories.
"""
import logging
import os
import re
from pathlib import Path
from typing import Callable, List, Optional

from .config_loader import ConfigLoader


class GitignoreParser:
    """Parses and applies .gitignore patterns."""

    def __init__(self, root_path: str, respect_gitignore: Optional[bool] = None):
        """
        Initialize gitignore parser for a root directory.

        Args:
            root_path: Root directory to start parsing from
            respect_gitignore: Override for respecting .gitignore files
        """
        self.root_path = Path(root_path).resolve()
        self.patterns: List[tuple] = []  # (pattern, is_negation, is_directory_only, gitignore_file)
        self._respect_gitignore_override = respect_gitignore
        self._load_patterns()

    def _load_patterns(self):
        """Load all ignore patterns from configuration and .gitignore files."""
        # Load configuration patterns
        config_patterns = ConfigLoader.get_ignore_patterns(str(self.root_path))
        respect_gitignore = ConfigLoader.should_respect_gitignore(str(self.root_path), self._respect_gitignore_override)

        # Add configuration patterns
        for pattern in config_patterns:
            self._add_pattern(pattern, is_negation=False, source="config")

        if not respect_gitignore:
            logging.debug("Gitignore files disabled by configuration")
            return

        # Load .gitignore files
        self._load_gitignore_files()

    def _load_gitignore_files(self):
        """Load patterns from .gitignore files - only from the root directory."""
        # Only load root .gitignore file, not from subdirectories
        # This prevents issues with overly broad patterns in subdirectories like .ruff_cache/*
        root_gitignore = Path(self.root_path) / '.gitignore'
        if root_gitignore.exists():
            self._parse_gitignore_file(root_gitignore)
            logging.debug("Loaded patterns from %s", root_gitignore)
        else:
            logging.debug("No .gitignore file found in root directory %s", self.root_path)

    def _parse_gitignore_file(self, gitignore_path: Path):
        """Parse a single .gitignore file."""
        try:
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Handle negation (lines starting with !)
                    is_negation = line.startswith('!')
                    if is_negation:
                        line = line[1:]

                    # Skip if empty after removing negation
                    if not line:
                        continue

                    self._add_pattern(line, is_negation, source=str(gitignore_path))

        except Exception as e:
            logging.debug("Error reading %s: %s", gitignore_path, e)

    def _add_pattern(self, pattern: str, is_negation: bool, source: str):
        """Add a pattern to the pattern list."""
        # Check if pattern is directory-only (ends with /)
        is_directory_only = pattern.endswith('/')
        if is_directory_only:
            pattern = pattern[:-1]

        # Skip empty patterns
        if not pattern:
            return

        # Convert gitignore pattern to regex-compatible pattern
        regex_pattern = self._gitignore_to_regex(pattern)

        self.patterns.append((regex_pattern, is_negation, is_directory_only, source))
        logging.debug("Added pattern: %s (negation=%s, dir_only=%s, source=%s)",
                      pattern, is_negation, is_directory_only, source)

    def _gitignore_to_regex(self, pattern: str) -> str:
        """Convert a gitignore pattern to a regex pattern."""
        # Escape special regex characters except * and ?
        pattern = re.escape(pattern)

        # Convert gitignore wildcards to regex
        pattern = pattern.replace(r'\*\*', '__DOUBLE_STAR__')  # Temporary placeholder
        pattern = pattern.replace(r'\*', '[^/]*')              # * matches anything except /
        pattern = pattern.replace('__DOUBLE_STAR__', '.*')     # ** matches anything including /
        pattern = pattern.replace(r'\?', '[^/]')               # ? matches single char except /

        return pattern

    def should_ignore(self, file_path: str, is_directory: bool = None) -> bool:
        """
        Check if a file or directory should be ignored.

        Args:
            file_path: Absolute path to the file/directory
            is_directory: Whether the path is a directory (auto-detected if None)

        Returns:
            True if the path should be ignored
        """
        path = Path(file_path).resolve()

        # Auto-detect if it's a directory
        if is_directory is None:
            is_directory = path.is_dir()

        # Get relative path from root
        try:
            rel_path = path.relative_to(self.root_path)
        except ValueError:
            # Path is not under root_path
            return False

        rel_path_str = str(rel_path).replace(os.sep, '/')

        # Apply patterns in order (later patterns can override earlier ones)
        ignored = False

        for regex_pattern, is_negation, is_directory_only, source in self.patterns:
            # Skip directory-only patterns for files
            if is_directory_only and not is_directory:
                continue

            # Check if pattern matches
            if self._matches_pattern(rel_path_str, regex_pattern):
                if is_negation:
                    ignored = False
                    logging.debug("Path %s un-ignored by pattern %s from %s",
                                  rel_path_str, regex_pattern, source)
                else:
                    ignored = True
                    logging.debug("Path %s ignored by pattern %s from %s",
                                  rel_path_str, regex_pattern, source)

        return ignored

    def _matches_pattern(self, rel_path: str, regex_pattern: str) -> bool:
        """Check if a relative path matches a regex pattern."""
        # Try matching the full path
        if re.match(regex_pattern + '$', rel_path):
            return True

        # Try matching any parent directory (for patterns like "build")
        path_parts = rel_path.split('/')
        for i in range(len(path_parts)):
            partial_path = '/'.join(path_parts[:i + 1])
            if re.match(regex_pattern + '$', partial_path):
                return True

        # Try matching as a subdirectory pattern
        if re.search('/' + regex_pattern + '($|/)', '/' + rel_path):
            return True

        return False

    def get_filter_function(self) -> Callable[[str], bool]:
        """
        Get a filter function that can be used with os.walk or similar.

        Returns:
            Function that takes a path and returns True if it should be included
        """
        def should_include(path: str) -> bool:
            return not self.should_ignore(path)

        return should_include

    def filter_walk_results(self, root: str, dirs: List[str], files: List[str]) -> tuple:
        """
        Filter os.walk results in-place to respect ignore patterns.

        Args:
            root: Current directory being walked
            dirs: List of subdirectories (modified in-place)
            files: List of files

        Returns:
            Tuple of (filtered_dirs, filtered_files)
        """
        # Filter directories in-place (affects further recursion)
        dirs_to_remove = []
        for dirname in dirs:
            dir_path = os.path.join(root, dirname)
            if self.should_ignore(dir_path, is_directory=True):
                dirs_to_remove.append(dirname)

        for dirname in dirs_to_remove:
            dirs.remove(dirname)

        # Filter files
        filtered_files = []
        for filename in files:
            file_path = os.path.join(root, filename)
            if not self.should_ignore(file_path, is_directory=False):
                filtered_files.append(filename)

        return dirs, filtered_files


def create_gitignore_parser(root_path: str, respect_gitignore: Optional[bool] = None) -> GitignoreParser:
    """
    Create a gitignore parser for the given root path.

    Args:
        root_path: Root directory to create parser for
        respect_gitignore: Override for respecting .gitignore files

    Returns:
        GitignoreParser instance
    """
    return GitignoreParser(root_path, respect_gitignore)
