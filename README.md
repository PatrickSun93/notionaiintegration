# Notion AI Integration System

A Flask-based web application that integrates Notion with multiple AI providers (OpenAI, Claude, Deepseek, and Ollama). Browse Notion pages, chat with AI using page context, create and edit pages, and manage configurations through an intuitive web interface.

## Features

- **Dashboard**: Browse accessible Notion pages and databases
- **AI Chat**: Interact with AI providers using Notion page content as context
- **Page Editor**: Create and update Notion pages with rich content
- **Multi-Provider Support**: OpenAI, Claude, Deepseek, and local Ollama
- **Configuration Management**: Web UI for managing API keys and settings
- **Security**: Rate limiting, CSRF protection, input validation
- **Monitoring**: Health checks, structured logging, error tracking

## Quick Start

Choose your preferred method to get started:

### Method 1: Python Virtual Environment (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd notion-ai-integration

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the application
python app.py
```

Access the application at `http://localhost:5000`

### Method 2: Conda Environment

```bash
# Clone the repository
git clone <repository-url>
cd notion-ai-integration

# Create conda environment
conda create -n notion-ai python=3.11 -y

# Activate environment
conda activate notion-ai

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the application
python app.py
```

### Method 3: Docker (Single Container)

```bash
# Clone the repository
git clone <repository-url>
cd notion-ai-integration

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Build Docker image
docker build -t notion-ai:latest .

# Run container
docker run -d \
  --name notion-ai \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  notion-ai:latest

# View logs
docker logs -f notion-ai
```

Access the application at `http://localhost:5000`

### Method 4: Docker Compose (Full Stack)

```bash
# Clone the repository
git clone <repository-url>
cd notion-ai-integration

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start all services (app + Redis + Nginx)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application at `http://localhost` (port 80)

### Method 5: Production Deployment (Linux)

```bash
# Run automated deployment script (as root)
sudo python deploy.py --environment production

# Or use the production startup script
sudo -u notion-ai /opt/notion-ai/start_production.sh start

# Check status
sudo -u notion-ai /opt/notion-ai/start_production.sh status

# View logs
sudo -u notion-ai /opt/notion-ai/start_production.sh logs
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production setup instructions.

### Method 6: Flask Development Server

```bash
# Set Flask app
export FLASK_APP=app.py
export FLASK_ENV=development

# Run with Flask CLI
flask run

# Or with custom host/port
flask run --host=0.0.0.0 --port=8080
```

### Method 7: Gunicorn (Production WSGI)

```bash
# Install gunicorn (if not already installed)
pip install gunicorn

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# With more options
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  app:app
```

## Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```bash
# Notion Integration (Required)
NOTION_API_KEY=secret_your_notion_integration_token

# AI Providers (Configure at least one)
OPENAI_API_KEY=sk-your_openai_api_key
CLAUDE_API_KEY=sk-ant-your_claude_api_key
DEEPSEEK_API_KEY=sk-your_deepseek_api_key
OLLAMA_ENDPOINT=http://localhost:11434

# Application Settings
AI_PROVIDER=openai                    # Default: openai
BLOG_DATABASE_ID=your_database_id     # Optional
SECRET_KEY=your-secret-key            # Change in production
FLASK_ENV=production                  # development or production
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR
```

### Getting API Keys

1. **Notion Integration Token**
   - Visit: https://www.notion.so/my-integrations
   - Create new integration
   - Copy the token (starts with `secret_`)
   - Share pages/databases with your integration

2. **OpenAI API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create new API key
   - Copy the key (starts with `sk-`)

3. **Claude API Key**
   - Visit: https://console.anthropic.com/
   - Create API key
   - Copy the key (starts with `sk-ant-`)

4. **Deepseek API Key**
   - Visit: https://platform.deepseek.com/
   - Create API key
   - Copy the key (starts with `sk-`)

5. **Ollama (Local)**
   - Install Ollama: https://ollama.ai/
   - Run: `ollama serve`
   - Default endpoint: `http://localhost:11434`

### Port Configuration

Override the default port (5000) using environment variables:

```bash
# Method 1: PORT variable
PORT=8080 python app.py

# Method 2: APP_PORT variable
APP_PORT=8080 python app.py

# Method 3: In .env file
echo "PORT=8080" >> .env
python app.py
```

## Project Structure

```
notion-ai-integration/
├── app.py                      # Main Flask application
├── ai_service.py              # AI provider implementations
├── notion_service.py          # Notion API wrapper
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Multi-container setup
├── start_production.sh       # Production startup script
├── deploy.py                 # Automated deployment
├── monitor.py                # System monitoring
├── nginx.conf                # Nginx configuration
├── DEPLOYMENT.md             # Detailed deployment guide
├── config/                   # Configuration modules
│   ├── ai_config.py         # AI provider config
│   ├── validation.py        # Input validation
│   ├── security.py          # Security features
│   ├── errors.py            # Error handling
│   ├── migration.py         # Config migration
│   ├── development.py       # Dev environment
│   └── production.py        # Prod environment
├── templates/               # HTML templates
│   ├── index.html          # Dashboard
│   ├── chat.html           # Chat interface
│   ├── editor.html         # Page editor
│   ├── settings.html       # Configuration UI
│   └── error*.html         # Error pages
└── static/                 # Frontend assets
    ├── css/style.css       # Styles
    └── js/                 # JavaScript
        ├── main.js
        ├── chat.js
        ├── editor.js
        └── settings.js
```

## Usage

### Web Interface

1. **Dashboard** (`/`)
   - View accessible Notion pages and databases
   - Quick navigation to other features
   - Configuration status overview

2. **Chat** (`/chat`)
   - Select AI provider
   - Choose Notion page for context (optional)
   - Send messages and receive AI responses

3. **Editor** (`/editor`)
   - Create new pages in Notion databases
   - Update existing page content
   - Manage page properties

4. **Settings** (`/settings`)
   - Configure AI provider API keys
   - Select default provider
   - Test API connectivity
   - Backup/restore configuration

### API Endpoints

#### Notion Operations

```bash
# Get accessible pages
curl http://localhost:5000/api/pages

# Get accessible databases
curl http://localhost:5000/api/databases

# Get page content
curl http://localhost:5000/api/page/{page_id}

# Create page
curl -X POST http://localhost:5000/api/create_page \
  -H "Content-Type: application/json" \
  -d '{
    "database_id": "your-database-id",
    "title": "My New Page",
    "content": "# Heading\n\nSome content here"
  }'

# Update page
curl -X POST http://localhost:5000/api/update_page \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "your-page-id",
    "content": "Updated content"
  }'
```

#### AI Chat

```bash
# Send chat message
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "provider": "openai"
  }'

# Chat with Notion page context
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Summarize this page",
    "provider": "openai",
    "page_id": "your-page-id"
  }'

# Get available providers
curl http://localhost:5000/api/chat/providers
```

#### Configuration

```bash
# Save configuration
curl -X POST http://localhost:5000/api/save_config \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "openai_api_key": "sk-...",
    "notion_api_key": "secret_..."
  }'

# Test configuration
curl -X POST http://localhost:5000/api/test_config \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai"}'

# Get configuration status
curl http://localhost:5000/api/config_status

# Backup configuration
curl -X POST http://localhost:5000/api/backup_config

# Restore configuration
curl -X POST http://localhost:5000/api/restore_config \
  -H "Content-Type: application/json" \
  -d '{"backup_file": "config_backup_20231201.json"}'
```

#### Health & Monitoring

```bash
# Basic health check
curl http://localhost:5000/health

# Detailed health check
curl http://localhost:5000/api/health

# System information
curl http://localhost:5000/api/system/info

# Security status
curl http://localhost:5000/api/security/status

# Integration test
curl -X POST http://localhost:5000/api/integration/test \
  -H "Content-Type: application/json" \
  -d '{"test_type": "comprehensive"}'
```

### Programmatic Usage

#### Using NotionService

```python
from notion_service import NotionService

# Initialize service (reads NOTION_API_KEY from config)
ns = NotionService()

# Get accessible pages
pages = ns.get_accessible_pages()
print(f"Found {len(pages)} pages")

# Get page content
content = ns.get_page_content(pages[0]['id'])
print(content)

# Create page in database
page_id = ns.create_page_in_database(
    database_id="your-database-id",
    title="My New Page",
    content="# Heading\n\nSome content here",
    properties={"Status": "In Progress"}
)
print(f"Created page: {page_id}")

# Update page content
ns.update_page_content(page_id, "Updated content")

# Get databases
databases = ns.get_accessible_databases()
```

#### Using AI Service

```python
from ai_service import get_ai_service
from config.ai_config import get_config

# Get configuration
config = get_config()

# Initialize AI service
ai = get_ai_service(config)

# Chat without context
response = ai.chat_with_context("Hello, how are you?", "")
print(response)

# Chat with context
context = "This is some context from a Notion page..."
response = ai.chat_with_context("Summarize this", context)
print(response)
```

#### Configuration Management

```python
from config.ai_config import get_config, update_config, validate_api_keys

# Get current configuration
config = get_config()
print(f"Current provider: {config.get('provider')}")

# Update configuration
new_config = {
    "provider": "openai",
    "openai_api_key": "sk-...",
    "notion_api_key": "secret_..."
}
validation_result = update_config(new_config)

if validation_result.is_valid:
    print("Configuration updated successfully")
else:
    print(f"Validation errors: {validation_result.errors}")

# Validate API keys
validation_results = validate_api_keys(config, test_connectivity=True)
for provider, result in validation_results.items():
    print(f"{provider}: {result}")
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Development Mode

```bash
# Enable debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# Run with auto-reload
python app.py
```

### Code Structure

- **app.py**: Main Flask application with routes, error handlers, and middleware
- **ai_service.py**: Abstract AI provider interface with implementations for OpenAI, Claude, Deepseek, and Ollama
- **notion_service.py**: Notion API wrapper with retry logic and content parsing
- **config/**: Configuration management, validation, security, and error handling modules

### Key Design Patterns

1. **Provider Pattern**: Abstract `AIProvider` base class with concrete implementations
2. **Service Layer**: Separate services for AI and Notion operations
3. **Configuration Management**: Centralized config with validation and migration
4. **Error Handling**: Comprehensive error handling with recovery suggestions
5. **Security**: Rate limiting, CSRF protection, input validation, and security headers

## Deployment

### Docker Compose Services

The `docker-compose.yml` includes:

- **notion-ai**: Main Flask application
- **redis**: Cache and rate limiting storage
- **nginx**: Reverse proxy and load balancer

### Production Checklist

- [ ] Set strong `SECRET_KEY` in environment
- [ ] Configure valid SSL certificates
- [ ] Set `FLASK_ENV=production`
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Configure backup procedures
- [ ] Enable monitoring and alerts
- [ ] Review security headers
- [ ] Test health check endpoints
- [ ] Configure rate limiting thresholds

### Monitoring

```bash
# Check application status
systemctl status notion-ai

# View application logs
tail -f /var/log/notion-ai/app.log

# View structured logs
tail -f /var/log/notion-ai/app_structured.log

# Check health
curl http://localhost:5000/health

# View metrics
curl http://localhost:5000/api/health
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Use different port
   PORT=8080 python app.py
   ```

2. **Missing API Keys**
   ```bash
   # Check configuration
   python -c "from config.ai_config import get_configuration_status; import json; print(json.dumps(get_configuration_status(), indent=2))"
   ```

3. **Notion API Errors**
   - Verify API key is correct
   - Check integration has access to pages/databases
   - Ensure pages are shared with integration

4. **AI Provider Errors**
   - Verify API key format
   - Check API key has sufficient credits
   - Test connectivity: `curl -X POST http://localhost:5000/api/test_config`

5. **Docker Issues**
   ```bash
   # Rebuild containers
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   
   # Check logs
   docker-compose logs -f notion-ai
   ```

### Debug Mode

```bash
# Enable debug logging
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG
python app.py
```

### Validation

```bash
# Validate configuration
python deploy.py --validate-only --environment production

# Test all integrations
curl -X POST http://localhost:5000/api/integration/test \
  -H "Content-Type: application/json" \
  -d '{"test_type": "comprehensive"}'
```

## Security

### Best Practices

- Store API keys in environment variables or `.env` file (never commit to git)
- Use strong, unique `SECRET_KEY` in production
- Enable HTTPS with valid SSL certificates
- Configure rate limiting based on your usage patterns
- Regularly update dependencies
- Monitor logs for suspicious activity
- Use non-root user for application in production
- Configure firewall to restrict access

### Security Features

- **Rate Limiting**: Prevents abuse of API endpoints
- **CSRF Protection**: Protects against cross-site request forgery
- **Input Validation**: Validates and sanitizes all user inputs
- **Content-Type Validation**: Ensures correct content types
- **Request Size Limits**: Prevents large payload attacks
- **Security Headers**: Sets appropriate HTTP security headers
- **Structured Logging**: Tracks all security events

## Requirements

- Python 3.9 or higher
- Redis (optional, for rate limiting in production)
- Nginx (optional, for production deployment)
- Docker & Docker Compose (optional, for containerized deployment)

## Dependencies

See `requirements.txt` for complete list:

- Flask 2.3.3 - Web framework
- openai 1.3.5 - OpenAI API client
- anthropic 0.7.7 - Claude API client
- notion-client 2.2.1 - Notion API client
- gunicorn 21.2.0 - Production WSGI server
- redis 5.0.1 - Redis client
- requests 2.31.0 - HTTP library

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)

For issues and questions, please [open an issue](your-repo-url/issues)
