class Conf:
    # Agent configuration 
    MCP_SERVER = "http://env-stg.bdnd-ai-infra-default.service.prdv2-euw1-general.consul:8080"
    DOMAIN = "usage_ai"
    MODEL_NAME = "gpt-4o"
    MAX_RETRIES = 2
    TIMEOUT = 50
    STUDIO_ENABLED = False
    
    # Other configurations
    vault_config_key = "secret/bdnd/bedrock_agent"