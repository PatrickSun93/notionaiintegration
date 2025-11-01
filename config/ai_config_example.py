# config/ai_config.py

AI_PROVIDER = "deepseek"  # Can be "openai", "claude", "deepseek", or "ollama"

# --- API Keys ---
# Replace these with your actual API keys
NOTION_API_KEY = ""
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"

# You can add keys for other services here as well
CLAUDE_API_KEY = "YOUR_CLAUDE_API_KEY"
DEEPSEEK_API_KEY = "sk-"

# --- Notion Configuration ---
BLOG_DATABASE_ID = "YOUR_BLOG_DATABASE_ID"

def get_config():
    return {
        "provider": AI_PROVIDER,
        "notion_api_key": NOTION_API_KEY,
        "openai_api_key": OPENAI_API_KEY,
        "blog_database_id": BLOG_DATABASE_ID,
    }
