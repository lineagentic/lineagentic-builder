"""
Configuration module for the agentic data product builder.
Simplified configuration system that relies on instruction files.
"""

from .config_loader import (
    ConfigLoader,
    get_config_loader,
    get_agent_config,
    get_orchestrator_config,
    list_available_agents
)

__all__ = [
    'ConfigLoader',
    'get_config_loader', 
    'get_agent_config',
    'get_orchestrator_config',
    'list_available_agents'
]
