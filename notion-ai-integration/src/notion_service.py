# src/notion_service.py
import datetime
from notion_client import Client
from config.ai_config import get_config

config = get_config()
notion = Client(auth=config["notion_api_key"])

def get_page_content(page_id):
    """Gets the content of a Notion page."""
    # This is a simplified implementation. A real implementation would need to
    # recursively fetch all blocks and concatenate their content.
    return "This is the full content of the Notion page."

def get_selected_block_content(block_id):
    """Gets the content of a selected block."""
    response = notion.blocks.retrieve(block_id)
    return response["paragraph"]["rich_text"][0]["text"]["content"]

def add_comment_to_page(page_id, comment):
    """Adds a comment to a Notion page."""
    timestamp = datetime.datetime.now().isoformat()
    notion.comments.create(
        parent={"page_id": page_id},
        rich_text=[{"text": {"content": f"[{timestamp}] {comment}"}}]
    )

def add_comment_to_block(block_id, comment):
    """Adds a comment to a Notion block."""
    timestamp = datetime.datetime.now().isoformat()
    notion.comments.create(
        parent={"block_id": block_id},
        rich_text=[{"text": {"content": f"[{timestamp}] {comment}"}}]
    )

def get_template_content(template_name):
    """Gets the content of a Notion page to be used as a template."""
    # This is a simplified implementation. A real implementation would need to
    # search for the page by name and then fetch its content.
    return f"This is the template content for {template_name}."

def create_page_in_database(database_id, title, content):
    """Creates a new page in a Notion database."""
    notion.pages.create(
        parent={"database_id": database_id},
        properties={"title": [{"text": {"content": title}}]},
        children=[{"object": "block", "paragraph": {"rich_text": [{"text": {"content": content}}]}}]
    )
