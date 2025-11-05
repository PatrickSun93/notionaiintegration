# Notion AI Integration System

This project is a Flask-based web application that integrates Notion with multiple AI providers (OpenAI, Claude, Deepseek, and optionally local Ollama). It provides a dashboard to browse Notion pages and databases, a chat interface that can use a Notion page as context, a simple page editor, and a settings screen to configure providers and API keys.

Key capabilities:
- Browse accessible Notion pages and databases in the dashboard
- Chat with an AI provider, optionally using a Notion page’s content as context
- Create and update Notion pages (title, basic content, simple properties)
- Configure providers, API keys, and defaults via UI or environment variables
- Basic security: rate limiting, CSRF protection, request size/content-type validation
- Structured logging with user-friendly error pages

Project layout:
- app.py: Flask application (routes, error handlers, security wrappers)
- ai_service.py: Provider-agnostic AI interface and implementations
- notion_service.py: Notion API wrapper (pages, databases, content, properties)
- config/: Configuration management, validation, migration, security
- templates/: HTML templates for dashboard, chat, editor, settings, and errors
- static/: Frontend JS/CSS assets
- requirements.txt: Python dependencies
- .env.example: Example environment variables
- DEPLOYMENT.md, docker-compose.yml, Dockerfile, start_production.sh: Deployment assets

Requirements:
- Python 3.9+
- Install dependencies from requirements.txt

Setup (virtualenv or Conda):
1) Create and activate a virtual environment (choose one)
   - Python venv:
     - python3 -m venv .venv
     - source .venv/bin/activate
   - Conda:
     - conda create -n notion-ai python=3.10 -y
     - conda activate notion-ai
2) Install dependencies:
   - pip install -r requirements.txt
3) Configure environment variables:
   - Copy .env.example to .env and fill in values
   - Or set them in your environment/host

Environment variables (can also be set via Settings UI):
- NOTION_API_KEY: Notion integration token (starts with secret_)
- OPENAI_API_KEY: OpenAI API key (starts with sk-)
- CLAUDE_API_KEY: Claude API key (starts with sk-ant-)
- DEEPSEEK_API_KEY: Deepseek API key (starts with sk-)
- OLLAMA_ENDPOINT: Ollama base URL (default http://localhost:11434)
- AI_PROVIDER: Default provider (openai, claude, deepseek, ollama)
- BLOG_DATABASE_ID: Optional Notion database ID for blog posts

Running the app (development):
- python app.py
  - Starts Flask on http://localhost:5000 in debug mode
  - You can override the port via environment variable:
    - PORT=5050 python app.py
    - or APP_PORT=5050 python app.py
- Alternatively:
  - FLASK_APP=app.py flask run

Core features in the UI:
- Dashboard (/):
  - Shows accessible Notion pages and databases
  - Warns if configuration is incomplete
- Chat (/chat and /api/chat):
  - Chat with configured AI provider
  - Optional page_id to load Notion page content as context
- Editor (/editor):
  - Create new Notion pages in a selected database
  - Update existing pages (content/properties)
- Settings (/settings):
  - Manage provider selection and API keys
  - Save and validate configuration

Important API endpoints:
- GET /api/pages: list accessible Notion pages
- GET /api/databases: list accessible Notion databases
- POST /api/create_page: create a page (requires database_id, title, optional content/properties)
- POST /api/update_page: update page content/properties
- POST /api/chat: send a chat message (provider validated; optional page_id for context)
- POST /api/save_config: persist provider settings and keys
- GET /api/validate_config: validate current keys and connectivity

Programmatic usage examples:
- Using NotionService to read and create content:
  - from notion_service import NotionService
  - ns = NotionService()  # reads NOTION_API_KEY from config/env
  - pages = ns.get_accessible_pages()
  - content = ns.get_page_content(pages[0]['id'])
  - page_id = ns.create_page_in_database(database_id, title="My Post", content="# Heading\nSome text")

- Using AI service with OpenAI:
  - from ai_service import get_ai_service
  - from config.ai_config import get_config
  - cfg = get_config()
  - ai = get_ai_service(cfg)
  - reply = ai.chat_with_context("Summarize this", context="Long text...")

Design highlights:
- ai_service.py:
  - Abstract AIProvider base class
  - OpenAIService uses the Chat Completions API via the OpenAI 1.x client
  - validate_provider_config ensures provider inputs look correct before use
- notion_service.py:
  - Retries on transient API errors
  - Read page content by traversing blocks and formatting text
  - Create/update pages with basic property formatting
  - Parse simple markdown-like content into Notion blocks (headers, paragraphs, callouts, lists)
- config/:
  - ai_config.py handles load/save, ENV var mapping, and configuration status
  - validation.py performs rigorous API key format checks and optional connectivity tests
  - security.py enforces rate limiting, CSRF, content-type, size, and JSON input validation rules

Limitations and notes:
- Notion content formatting is basic; some block types are rendered with placeholders
- Properties formatting covers common types; complex schemas may need manual adjustments
- Ensure API keys are valid and present; many routes gracefully degrade with warnings
- Ollama support requires a local server; only endpoint validation is performed here

Deployment:
- See DEPLOYMENT.md and docker-compose.yml/Dockerfile for production setup
- start_production.sh and nginx.conf are provided for a containerized deployment

Troubleshooting:
- Missing pages/databases: verify NOTION_API_KEY and Notion integration access
- Chat errors: verify provider API key and provider selection in Settings
- Create/update page failures: check database_id and property types
- Connectivity issues: review proxy/firewall and try the validation endpoints