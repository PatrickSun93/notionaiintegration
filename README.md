# Notion AI Integration

This project connects Notion with AI providers to help you:

- Summarize the content of a Notion page
- Summarize the content of a selected Notion block
- Generate a blog post from a topic using a Notion template page
- Add AI-generated content back to Notion (as page/block comments or new pages in a database)

The code is intentionally minimal with clear separations:

- config/ai_config.py – local, ignored configuration (copy from ai_config_example.py)
- src/ai_service.py – AI provider abstraction and implementations
- src/notion_service.py – Notion API operations (fetch, comment, create page)
- src/app.py – Orchestrates commands and demonstrates usage

Note: Several parts are simplified stubs to illustrate the flow (e.g., fetching a full page’s content and template search). You can replace them with production-grade logic.

## Project Structure

- .gitignore
- config/
  - __init__.py
  - ai_config_example.py
- src/
  - __init__.py
  - ai_service.py
  - notion_service.py
  - app.py

## Requirements

- Python 3.9+ (3.10 or newer recommended)
- Install dependencies from requirements.txt:

```
pip install -r requirements.txt
```

Notes:
- The requirements file pins OpenAI to 0.28.1 to support the legacy Completions API (`openai.Completion.create` with `text-davinci-003`) used in `src/ai_service.py`.
- If you prefer OpenAI SDK >= 1.0, you’ll need to migrate `src/ai_service.py` to the Chat Completions API.

## Setup

1) Create and activate a virtual environment (optional but recommended)

```
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows PowerShell
```

Alternative: Create and activate a Conda environment

```
# Create a Conda environment with Python 3.10
conda create -n notionaiintegration python=3.10

# Activate the environment (macOS/Linux/Windows)
conda activate notionaiintegration
```

2) Install dependencies

```
pip install -r requirements.txt
```

3) Create your local config file

- Copy the example config:

```
cp config/ai_config_example.py config/ai_config.py
```

- Edit `config/ai_config.py` and fill in your keys:
  - AI_PROVIDER: set to "openai" for working functionality (other providers are placeholders)
  - NOTION_API_KEY: your Notion integration secret
  - OPENAI_API_KEY: your OpenAI API key
  - BLOG_DATABASE_ID: target Notion database ID for generated posts

The file `config/ai_config.py` is git-ignored to keep secrets out of version control.

4) Share your Notion content with the integration

- Create a Notion integration and obtain the secret (NOTION_API_KEY)
- Share the relevant pages or database with the integration so it has read/write access

## How to Run

This project is organized as a package inside `src/`, so the recommended way to run the demo is with the `-m` flag:

```
python -m src.app
```

This will execute several demo commands in sequence, showing how summaries and blog posts are generated and posted back to Notion.

## Usage (Programmatic)

You can call the command handler from code to simulate Notion slash commands:

```
from src.app import handle_slash_command

# Summarize a page
handle_slash_command("/customaisummary-page", page_id="<YOUR_PAGE_ID>")

# Summarize a block (assumes a paragraph block)
handle_slash_command("/customaisummary-block", block_id="<YOUR_BLOCK_ID>")

# Generate a blog post from a topic using a template page name
handle_slash_command("/autogenpost", topic="The Future of AI", template="My Tech Blog Template")
```

## Configuration Details

- AI provider selection happens in `src/ai_service.py:get_ai_service(config)`.
- Only the OpenAI provider is implemented end-to-end. Claude, Deepseek, and Ollama are placeholders.
- `src/notion_service.py` uses the Notion client to:
  - Retrieve a block’s content (assumes `paragraph` type for the demo)
  - Add comments to pages/blocks
  - Create pages in a database
- The functions `get_page_content` and `get_template_content` are simplified and should be replaced with full Notion queries for production use.

## Design Overview

- app.py: orchestrates commands and flows
- ai_service.py: Strategy pattern for AI providers (extensible)
- notion_service.py: Encapsulates Notion operations
- Separation of concerns keeps business logic readable and testable

## Limitations and Next Steps

- Content retrieval is simplified (no recursive block traversal for pages)
- Block retrieval assumes `paragraph` type; add type checks and fallbacks
- OpenAI usage relies on the legacy Completions API; migrate to Chat Completions
- Other providers (Claude/Deepseek/Ollama) need real implementations
- A `requirements.txt` is included; consider adding proper error handling/logging
- `app.py` mixes demo and command routing; you may split them for production use

## Tips for Production

- Add retries and rate limit handling for both Notion and AI APIs
- Replace string concatenation with more robust formatting for comments
- Validate Notion API responses and handle pagination for large pages
- Store configuration in environment variables or a secrets manager when deploying

## Troubleshooting

- ImportError when running `python src/app.py`:
  - Use `python -m src.app` because `src` is a package and `app.py` uses relative imports.
- OpenAI errors with missing `Completion`:
  - Ensure you installed dependencies via `pip install -r requirements.txt` (which pins OpenAI to a compatible version), or update the code to the new Chat Completions API.
- Notion API permission errors:
  - Confirm the integration has access to the pages/database (share them to the integration).