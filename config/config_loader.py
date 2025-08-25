"""
Configuration loader for the agentic data product builder.
Loads and provides access to agent configurations from individual YAML files.
"""
import os
import yaml
import asyncio
import aiofiles
from typing import Dict, Any, Optional

class ConfigLoader:
    """Loads and manages configuration for all agents from individual files."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Path to the configuration directory. If None, uses default.
        """
        if config_dir is None:
            # Default to config/ directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = current_dir
        
        self.config_dir = config_dir
        self._config = None
        asyncio.create_task(self._load_all_configs())
    
    async def _load_all_configs(self):
        """Load all configuration files and combine them."""
        try:
            self._config = {}
            
            # List of agent configuration files
            agent_files = [
                "scoping_agent.yaml",
                "schema_contract_agent.yaml", 
                "policy_agent.yaml",
                "provisioning_agent.yaml",
                "docs_agent.yaml",
                "catalog_agent.yaml",
                "observability_agent.yaml"
            ]
            
            # Load each agent configuration
            for agent_file in agent_files:
                file_path = os.path.join(self.config_dir, agent_file)
                if os.path.exists(file_path):
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        agent_config = yaml.safe_load(content)
                        # Extract agent name from filename (e.g., scoping_agent.yaml -> scoping_agent)
                        agent_key = agent_file.replace('.yaml', '')
                        self._config[agent_key] = agent_config
                else:
                    print(f"Warning: Configuration file not found: {file_path}")
            
            # Load orchestrator configuration
            orch_file = os.path.join(self.config_dir, "orchestrator.yaml")
            if os.path.exists(orch_file):
                async with aiofiles.open(orch_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self._config["orchestrator"] = yaml.safe_load(content)
            else:
                print(f"Warning: Orchestrator configuration file not found: {orch_file}")
                self._config["orchestrator"] = {}
                
        except Exception as e:
            raise ValueError(f"Error loading configuration files: {e}")
    
    async def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'scoping')
            
        Returns:
            Dictionary containing the agent's configuration
        """
        if self._config is None:
            await self._load_all_configs()
        
        agent_key = f"{agent_name}_agent"
        if agent_key not in self._config:
            raise KeyError(f"Configuration for agent '{agent_name}' not found")
        
        return self._config[agent_key]
    
    async def get_orchestrator_config(self) -> Dict[str, Any]:
        """
        Get orchestrator configuration.
        
        Returns:
            Dictionary containing the orchestrator's configuration
        """
        if self._config is None:
            await self._load_all_configs()
        
        return self._config.get("orchestrator", {})
    
    async def get_all_config(self) -> Dict[str, Any]:
        """
        Get the complete configuration.
        
        Returns:
            Dictionary containing all configuration
        """
        if self._config is None:
            await self._load_all_configs()
        
        return self._config.copy()
    
    async def reload_config(self):
        """Reload configuration from files."""
        await self._load_all_configs()
    
    async def list_available_agents(self) -> list:
        """
        List all available agent configurations.
        
        Returns:
            List of agent names
        """
        if self._config is None:
            await self._load_all_configs()
        
        agents = []
        for key in self._config.keys():
            if key != "orchestrator":
                # Remove "_agent" suffix
                agent_name = key.replace("_agent", "")
                agents.append(agent_name)
        
        return agents

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
        Dictionary containing the agent's configuration
    """
    loader = get_config_loader(config_dir)
    return await loader.get_agent_config(agent_name)

async def get_orchestrator_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get orchestrator configuration.
    
    Args:
        config_dir: Path to configuration directory (only used on first call)
        
    Returns:
        Dictionary containing the orchestrator's configuration
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
