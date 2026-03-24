DEFAULT_CONFIG = {
    "llm": {
        "provider": "azure",
        "model": "gpt-4.1",
        "api_key_env": "AZURE_OPENAI_KEY",
        "azure_endpoint": "https://sw-qa-genai-oai01.openai.azure.com/",
        "azure_deployment": "gpt-4.1",
        "azure_api_version": "2025-01-01-preview",
        "temperature": 0.2,
        "max_tokens": 4096,
    },
    "execution": {
        "timeout": 60,
        "sandbox": True,
        "auto_backup": True,
        "confirm_before_write": True,
    },
    "ui": {
        "theme": "dark",
        "show_code": True,
        "show_tokens": True,
        "show_cost": True,
        "stream": True,
    },
    "logging": {
        "level": "INFO",
    },
    "account": {
        "sync_sessions": False,
        "key_source": "local",
        "telemetry": False,
    },
}
