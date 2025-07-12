from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os
import json

class WorkflowAgentConfig(BaseSettings):
    risk_api_url: str = Field(default_factory=lambda: os.environ.get("RISK_API_URL", "http://localhost:8080"))
    player_agent_urls: List[str] = Field(default_factory=lambda: json.loads(os.environ.get("PLAYER_AGENT_URLS", '["http://localhost:8081/.well-known/agent.json","http://localhost:8082/.well-known/agent.json"]')))
    agent_name: str = Field(default_factory=lambda: os.environ.get("AGENT_NAME", "RiskWorkflowAgent"))
    max_players: int = Field(default=6)
    max_iterations: int = Field(default=500)

    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    } 