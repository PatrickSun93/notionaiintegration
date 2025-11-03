import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, request, jsonify
from src import ai_service
from src import notion_service
from src.database import init_db, get_db
from src import config_service
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"An error occurred: {e}")
    return "An unexpected error occurred. Please try again later.", 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    notion_page_id = data.get('notion_page_id')

    # Get config and AI service
    config = config_service.get_config()
    ai = ai_service.get_ai_service(config)

    # Get page content if a page is selected
    page_content = ""
    if notion_page_id:
        page_content = notion_service.get_page_content(notion_page_id)

    # Generate a response
    full_message = f"{page_content}\n\n{message}"
    response = ai.generate_summary(full_message) # Using generate_summary for now

    # Save to database
    db = get_db()
    cursor = db.cursor()
    session_id = request.remote_addr
    cursor.execute(
        "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, 'user', message)
    )
    cursor.execute(
        "INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, 'ai', response)
    )
    db.commit()
    db.close()

    return jsonify({'response': response})

@app.route('/notion/pages', methods=['GET', 'POST'])
def notion_pages():
    if request.method == 'POST':
        data = request.json
        title = data.get('title')
        content = data.get('content')
        config = config_service.get_config()
        notion_service.create_page_in_database(config['blog_database_id'], title, content)
        return 'Page created!'

    pages = notion_service.get_all_pages()
    return jsonify(pages)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        config = config_service.get_config()
        for key in config:
            if key in request.form:
                config[key] = request.form[key]

        errors = ai_service.validate_api_keys(config)
        if errors:
            return render_template('settings.html', config=config, errors=errors)

        config_service.save_config(config)
        return 'Settings saved!'

    config = config_service.get_config()
    return render_template('settings.html', config=config)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, use_reloader=False)
