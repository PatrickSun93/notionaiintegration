# src/app.py

from . import notion_service
from . import ai_service
from config import ai_config

def handle_slash_command(command, **kwargs):
    """Handles incoming slash commands from Notion."""
    if command == "/customaisummary-page":
        page_id = kwargs.get("page_id")
        if page_id:
            summarize_page(page_id)
        else:
            print("Error: page_id not provided for /customaisummary-page")

    elif command == "/customaisummary-block":
        block_id = kwargs.get("block_id")
        if block_id:
            summarize_block(block_id)
        else:
            print("Error: block_id not provided for /customaisummary-block")

    elif command == "/autogenpost":
        topic = kwargs.get("topic")
        template = kwargs.get("template")
        if topic and template:
            generate_blog_post(topic, template)
        else:
            print("Error: topic or template not provided for /autogenpost")

    elif command == "/customaideas":
        print("Coming Soon: Generate new ideas feature is under development.")

    else:
        print(f"Unknown command: {command}")

def summarize_page(page_id):
    """Summarizes the content of a Notion page."""
    config = ai_config.get_config()
    ai = ai_service.get_ai_service(config)

    content = notion_service.get_page_content(page_id)
    summary = ai.generate_summary(content)

    notion_service.add_comment_to_page(page_id, summary)

def summarize_block(block_id):
    """Summarizes the content of a selected block."""
    config = ai_config.get_config()
    ai = ai_service.get_ai_service(config)

    content = notion_service.get_selected_block_content(block_id)
    summary = ai.generate_summary(content)

    notion_service.add_comment_to_block(block_id, summary)

def generate_blog_post(topic, template_name):
    """Generates a blog post on a given topic using a template."""
    config = ai_config.get_config()
    ai = ai_service.get_ai_service(config)

    template_content = notion_service.get_template_content(template_name)
    blog_post_content = ai.generate_blog_post(topic, template_content)

    notion_service.create_page_in_database(config["blog_database_id"], topic, blog_post_content)

if __name__ == '__main__':
    # Simulate slash command invocations for testing
    print("--- Testing Page Summarization ---")
    handle_slash_command("/customaisummary-page", page_id="page123")

    print("\n--- Testing Block Summarization ---")
    handle_slash_command("/customaisummary-block", block_id="block456")

    print("\n--- Testing Blog Post Generation ---")
    handle_slash_command("/autogenpost", topic="The Future of AI", template="My Tech Blog Template")

    print("\n--- Testing Placeholder Command ---")
    handle_slash_command("/customaideas")
