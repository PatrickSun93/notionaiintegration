# src/notion_service.py
import datetime
from notion_client import Client
from src import config_service

config = config_service.get_config()
notion = Client(auth=config["notion_api_key"])

def _get_text_from_rich_text(rich_text):
    return "".join([rt.get("plain_text", "") for rt in rich_text])

def _get_text_from_block(block):
    block_type = block.get("type")
    if not block_type:
        return ""

    text = ""
    if block_type in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "toggle", "quote"):
        text = _get_text_from_rich_text(block[block_type].get("rich_text", []))
    elif block_type == "to_do":
        text = _get_text_from_rich_text(block[block_type].get("rich_text", []))
        if block[block_type].get("checked"):
            text = f"[x] {text}"
        else:
            text = f"[ ] {text}"
    elif block_type == "child_page":
        text = block[block_type].get("title", "")
    elif block_type == "unsupported":
        return ""

    if block.get("has_children"):
        children_text = ""
        children = notion.blocks.children.list(block_id=block["id"]).get("results", [])
        for child in children:
            children_text += _get_text_from_block(child)
        text += "\n" + children_text

    return text + "\n"


def get_page_content(page_id):
    """Gets the content of a Notion page."""
    content = ""
    blocks = notion.blocks.children.list(block_id=page_id).get("results", [])
    for block in blocks:
        content += _get_text_from_block(block)
    return content

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

def get_all_pages():
    """Gets all pages accessible by the Notion integration."""
    pages = notion.search(filter={"property": "object", "value": "page"}).get("results", [])
    return [{"id": page["id"], "title": _get_text_from_rich_text(page["properties"]["title"]["title"])} for page in pages]
