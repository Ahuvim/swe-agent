import os

class Shared(object):
    DOMAIN = "usage_ai"
    MODEL_NAME = "gpt-4o"
    vault_config_key = "secret/bdnd/bedrock_agent"
    
    # API Keys
    OPEN_AI = os.environ.get("OPENAI_API_KEY", "")
    
    # Agent configuration
    MCP_SERVER = "http://localhost:8080"
    
    # LangGraph Studio configuration
    STUDIO_URL = "http://localhost:8000"
    STUDIO_API_KEY = "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"
    STUDIO_ENABLED = False
    
    # Other agent settings
    MAX_RETRIES = 2
    TIMEOUT = 50
    
    # Authentication settings
    DEBUG = True

