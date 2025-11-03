import json
import os

CONFIG_PATH = 'config.json'

DEFAULT_CONFIG = {
    "provider": "openai",
    "notion_api_key": "",
    "openai_api_key": "",
    "claude_api_key": "",
    "deepseek_api_key": "",
    "openai_model": "gpt-3.5-turbo",
    "claude_model": "claude-2",
    "deepseek_model": "deepseek-coder",
    "ollama_model": "llama2",
    "ollama_base_url": "http://localhost:11434",
    "blog_database_id": "",
}

def get_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG

    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

PROMPTS_PATH = 'config/prompts.json'

def get_prompts():
    with open(PROMPTS_PATH, 'r') as f:
        return json.load(f)
