"""
Agent Management and Verification Module

This module provides functionality for managing and verifying AI agents in the BRIDGE system.
It handles agent verification against a whitelist of allowed agents defined in the API configuration.

Key Features:
- Agent verification against allowed list
- Centralized agent management
- Simple interface for agent validation

Dependencies:
    config.API_CONFIG: Configuration dictionary containing allowed agents list
"""

from config import API_CONFIG

# Get the allowed agents list from the API config
ALLOWED_AGENTS = API_CONFIG.get("allowed_agents", [])

def verify_agent(agent_id: str) -> bool:
    """
    Verify if the specified agent ID is in the list of allowed agents.
    
    This function checks if the provided agent ID exists in the ALLOWED_AGENTS list
    which is loaded from the API configuration. This serves as a simple whitelist
    mechanism for agent authentication.
    
    Args:
        agent_id (str): The unique identifier of the agent to verify
        
    Returns:
        bool: 
            - True if the agent is in the allowed list
            - False if the agent is not found in the allowed list
            
    Example:
        >>> verify_agent("agent123")
        True
        >>> verify_agent("unauthorized_agent")
        False
    """
    return agent_id in ALLOWED_AGENTS
