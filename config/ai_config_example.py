# config/ai_config_example.py

AI_PROVIDER = "openai"  # Can be "openai", "claude", "deepseek", or "ollama"

# --- API Keys ---
NOTION_API_KEY = "YOUR_NOTION_API_KEY"
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
CLAUDE_API_KEY = "YOUR_CLAUDE_API_KEY"
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"

# --- Model Names ---
OPENAI_MODEL = "gpt-3.5-turbo"
CLAUDE_MODEL = "claude-2"
DEEPSEEK_MODEL = "deepseek-coder"
OLLAMA_MODEL = "llama2"

# --- Ollama Configuration ---
OLLAMA_BASE_URL = "http://localhost:11434"

# --- Notion Configuration ---
BLOG_DATABASE_ID = "YOUR_BLOG_DATABASE_ID"

def get_config():
    return {
        "provider": AI_PROVIDER,
        "notion_api_key": NOTION_API_KEY,
        "openai_api_key": OPENAI_API_KEY,
        "claude_api_key": CLAUDE_API_KEY,
        "deepseek_api_key": DEEPSEEK_API_KEY,
        "openai_model": OPENAI_MODEL,
        "claude_model": CLAUDE_MODEL,
        "deepseek_model": DEEPSEEK_MODEL,
        "ollama_model": OLLAMA_MODEL,
        "ollama_base_url": OLLAMA_BASE_URL,
        "blog_database_id": BLOG_DATABASE_ID,
    }
