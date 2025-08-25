"""
Configuration utilities for the agentic data product builder.
Simplified configuration system that relies on instruction files instead of YAML configs.
"""
import os
from typing import Dict, Any, Optional

class ConfigLoader:
    """Simplified config loader that doesn't load YAML files."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Path to the configuration directory (kept for compatibility)
        """
        self.config_dir = config_dir
        self._config = {}
    
    async def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'scoping')
            
        Returns:
            Empty dictionary since configs are now in instruction files
        """
        # Return empty config since agents now use instruction files
        return {}
    
    async def get_orchestrator_config(self) -> Dict[str, Any]:
        """
        Get orchestrator configuration.
        
        Returns:
            Empty dictionary since orchestrator config is not needed
        """
        return {}
    
    async def get_all_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration.
        
        Returns:
            Empty dictionary since configs are now in instruction files
        """
        return {}
    
    async def reload_config(self):
        """Reload configuration from files."""
        # No-op since we don't load YAML files anymore
        pass
    
    async def list_available_agents(self) -> list:
        """
        List all available agent configurations.
        
        Returns:
            List of agent names based on instruction files
        """
        # Return list of agents that have instruction files
        return [
            "scoping",
            "data_contract", 
            "policy",
            "provisioning",
            "docs",
            "catalog",
            "observability",
            "routing"
        ]

# Global config loader instance
_config_loader = None

def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Get the global configuration loader instance.
    
    Args:
        config_dir: Path to configuration directory (only used on first call)
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader

async def get_agent_config(agent_name: str, config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get agent configuration.
    
    Args:
        agent_name: Name of the agent
        config_dir: Path to configuration directory (only used on first call)
        
    Returns:
        Empty dictionary since configs are now in instruction files
    """
    loader = get_config_loader(config_dir)
    return await loader.get_agent_config(agent_name)

async def get_orchestrator_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get orchestrator configuration.
    
    Args:
        config_dir: Path to configuration directory (only used on first call)
        
    Returns:
        Empty dictionary since orchestrator config is not needed
    """
    loader = get_config_loader(config_dir)
    return await loader.get_orchestrator_config()

async def list_available_agents(config_dir: Optional[str] = None) -> list:
    """
    Convenience function to list available agents.
    
    Args:
        config_dir: Path to configuration directory (only used on first call)
        
    Returns:
        List of available agent names
    """
    loader = get_config_loader(config_dir)
    return await loader.list_available_agents()
