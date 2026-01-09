"""Environment path helpers - locate config files by environment."""

from pathlib import Path
from typing import Optional

from basec.inventory import get_inventory_path


def get_envs_base_path() -> Path:
    """Get the base path for environments."""
    inventory_path = get_inventory_path()
    # inventory.yaml is in infra/, envs/ is also in infra/
    return inventory_path.parent / "envs"


def get_env_path(env: str = "production") -> Path:
    """Get path to environment directory.
    
    Args:
        env: Environment name (production, development, staging, etc.)
    
    Returns:
        Path to envs/<env>/
    """
    return get_envs_base_path() / env


def get_edge_path(env: str = "production") -> Path:
    """Get path to edge configuration.
    
    Args:
        env: Environment name
    
    Returns:
        Path to envs/<env>/edge/
    """
    return get_env_path(env) / "edge"


def get_platform_path(env: str = "production") -> Path:
    """Get path to platform configuration.
    
    Args:
        env: Environment name
    
    Returns:
        Path to envs/<env>/platform/
    """
    return get_env_path(env) / "platform"


def get_vertical_path(vertical: str, env: str = "production") -> Path:
    """Get path to vertical configuration.
    
    Args:
        vertical: Vertical name (e.g., 'construction')
        env: Environment name
    
    Returns:
        Path to envs/<env>/verticals/<vertical>/
    """
    return get_env_path(env) / "verticals" / vertical


def validate_env_path(env: str = "production") -> bool:
    """Validate that environment path exists.
    
    Args:
        env: Environment name
    
    Returns:
        True if path exists, False otherwise
    """
    return get_env_path(env).exists()


