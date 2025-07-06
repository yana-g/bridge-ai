from config import API_CONFIG

# Get the allowed agents list from the API config
ALLOWED_AGENTS = API_CONFIG.get("allowed_agents", [])

def verify_agent(agent_id: str) -> bool:
    """
    Verify if the agent ID is in the list of allowed agents.
    
    Args:
        agent_id (str): The agent ID to verify
        
    Returns:
        bool: True if the agent is allowed, False otherwise
    """
    return agent_id in ALLOWED_AGENTS
