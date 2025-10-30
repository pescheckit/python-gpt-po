"""
Configuration loader for gpt-po-translator.
Loads configuration from pyproject.toml files.
"""
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


class ConfigLoader:
    """Loads and manages configuration from pyproject.toml files."""
    DEFAULT_CONFIG = {
        # File scanning
        'respect_gitignore': True,
        'ignore_patterns': [
            "*.pyc",
            "__pycache__/",
            "*.egg-info/",
            ".pytest_cache/",
            ".coverage",
            ".tox/",
            ".mypy_cache/",
            "htmlcov/",
        ],
        'default_ignore_patterns': [
            ".git/",
            ".venv/",
            "venv/",
            "env/",
            ".env/",
            "node_modules/",
            ".cache/",
            "build/",
            "dist/",
            "*.egg-info/",
            "__pycache__/",
            ".pytest_cache/",
            ".tox/",
            ".mypy_cache/",
        ],
        # Translation behavior
        'default_verbosity': 1,
        'default_batch_size': 50,
        'default_bulk_mode': False,
        'mark_ai_generated': True,
        'folder_language_detection': False,
        'fix_fuzzy_entries': False,
        'default_context': None,
        # Provider defaults
        'default_models': {
            'openai': 'gpt-4o-mini',
            'anthropic': 'claude-3-5-sonnet-20241022'
        },
        # Performance
        'max_retries': 3,
        'request_timeout': 120,
        # Output
        'skip_translated_files': True,
        'show_progress': True,
        'show_summary': True,
    }

    @classmethod
    def load_config(cls, start_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from pyproject.toml files.
        Searches upward from start_path (or current directory) for pyproject.toml files
        and merges the [tool.gpt-po-translator] sections.
        For Docker compatibility, also checks for configuration in mounted volumes.
        Args:
            start_path: Directory to start searching from (defaults to current directory)
        Returns:
            Merged configuration dictionary
        """
        if tomllib is None:
            logging.debug("tomllib not available, using default configuration")
            return cls.DEFAULT_CONFIG.copy()
        config = cls.DEFAULT_CONFIG.copy()
        config_found = False
        # Start from the given path or current directory
        current_path = Path(start_path or os.getcwd()).resolve()
        # Search paths in order of priority:
        # 1. Direct search upward from the target directory (highest priority)
        # 2. Docker compatibility: if running in container and has mounted volumes
        search_paths = [current_path] + list(current_path.parents)
        # Docker compatibility: Check if we're in a container and add volume-specific paths
        if cls._is_running_in_docker():
            # Add common Docker volume mount points
            docker_paths = [
                Path("/data"),        # Common mount point
                Path("/workspace"),   # Another common mount point
                Path("/app"),         # Our container working directory
            ]
            # Only add paths that exist and are different from our current search
            for docker_path in docker_paths:
                if docker_path.exists() and docker_path not in search_paths:
                    search_paths.insert(-1, docker_path)  # Insert before root
        # Search for pyproject.toml files
        for path in search_paths:
            pyproject_path = path / "pyproject.toml"
            if not pyproject_path.exists():
                continue
            tool_config = cls._load_tool_config(pyproject_path)
            if not tool_config:
                continue
            logging.debug("Found configuration in %s", pyproject_path)
            # Merge configuration (closer files override if not already found)
            for key, value in tool_config.items():
                # Only override if this is the first config found or key wasn't set
                if not config_found or key not in config or config[key] == cls.DEFAULT_CONFIG.get(key):
                    config[key] = value
            config_found = True
            # For Docker compatibility, if we found config in a mounted volume,
            # continue searching to allow project-local configs to override
            if not cls._is_docker_volume_path(path):
                break
        logging.debug("Final configuration: %s", config)
        return config

    @classmethod
    def _is_running_in_docker(cls) -> bool:
        """Check if we're running inside a Docker container."""
        try:
            # Check for Docker environment indicators
            has_dockerenv = os.path.exists("/.dockerenv")
            if has_dockerenv:
                return True
            has_cgroup = os.path.exists("/proc/1/cgroup")
            if has_cgroup:
                with open("/proc/1/cgroup", encoding="utf-8") as f:
                    return any("docker" in line for line in f.readlines())
            return False
        except Exception:
            return False

    @classmethod
    def _load_tool_config(cls, pyproject_path: Path) -> dict:
        """Load gpt-po-translator configuration from a pyproject.toml file."""
        try:
            with open(pyproject_path, "rb") as f:
                toml_data = tomllib.load(f)
            return toml_data.get("tool", {}).get("gpt-po-translator", {})
        except Exception as e:
            logging.debug("Error reading %s: %s", pyproject_path, e)
            return {}

    @classmethod
    def _is_docker_volume_path(cls, path: Path) -> bool:
        """Check if a path is likely a Docker volume mount point."""
        # Common Docker volume mount patterns
        docker_volume_patterns = ["/data", "/workspace", "/input", "/output", "/locales", "/translations"]
        return any(str(path).startswith(pattern) for pattern in docker_volume_patterns)

    @classmethod
    def get_ignore_patterns(cls, start_path: Optional[str] = None) -> List[str]:
        """
        Get all ignore patterns from configuration.
        Args:
            start_path: Directory to start searching from
        Returns:
            List of all ignore patterns to use
        """
        config = cls.load_config(start_path)
        patterns = []
        # Add default patterns (always included unless explicitly set to empty)
        default_patterns = config.get('default_ignore_patterns', [])
        if default_patterns:
            patterns.extend(default_patterns)
        # Add additional patterns
        additional_patterns = config.get('ignore_patterns', [])
        if additional_patterns:
            patterns.extend(additional_patterns)
        return patterns

    @classmethod
    def should_respect_gitignore(cls, start_path: Optional[str] = None, override: Optional[bool] = None) -> bool:
        """
        Check if .gitignore files should be respected.
        Args:
            start_path: Directory to start searching from
            override: Optional boolean to override config (e.g., from CLI)
        Returns:
            True if gitignore should be respected
        """
        if override is not None:
            return override
        config = cls.load_config(start_path)
        return config.get('respect_gitignore', True)

    @classmethod
    def get_default_model(cls, provider: str, start_path: Optional[str] = None) -> Optional[str]:
        """
        Get default model for a specific provider.
        Args:
            provider: Provider name (e.g., 'openai', 'anthropic', 'ollama')
            start_path: Directory to start searching from
        Returns:
            Default model string or None
        """
        config = cls.load_config(start_path)
        # First check provider-specific config
        provider_config = config.get('provider', {}).get(provider, {})
        if 'model' in provider_config:
            return provider_config['model']
        # Fall back to default_models (legacy)
        default_models = config.get('default_models', {})
        return default_models.get(provider)

    @classmethod
    def get_provider_setting(cls, provider: str, setting: str, default: Any = None,
                             start_path: Optional[str] = None) -> Any:
        """
        Get a specific setting for any provider from config.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic', 'ollama')
            setting: Setting name (e.g., 'base_url', 'timeout', 'model')
            default: Default value if not found
            start_path: Directory to start searching from

        Returns:
            Setting value or default
        """
        config = cls.load_config(start_path)
        provider_config = config.get('provider', {}).get(provider, {})
        return provider_config.get(setting, default)

    @classmethod
    def get_default_context(cls, start_path: Optional[str] = None) -> Optional[str]:
        """
        Get default translation context from configuration.

        Args:
            start_path: Directory to start searching from

        Returns:
            Default context string or None
        """
        config = cls.load_config(start_path)
        return config.get('default_context')
