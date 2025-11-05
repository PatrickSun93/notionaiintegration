# Deployment Guide - Notion AI Integration System

This guide covers deployment options for the Notion AI Integration System in both development and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Development Deployment](#development-deployment)
4. [Production Deployment](#production-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows
- **Memory**: Minimum 2GB RAM (4GB+ recommended for production)
- **Storage**: Minimum 1GB free space
- **Network**: Internet access for API calls

### Required API Keys

Before deployment, obtain the following API keys:

1. **Notion Integration Token** (Required)
   - Create at: https://www.notion.so/my-integrations
   - Format: `secret_...`

2. **AI Provider API Keys** (At least one required)
   - **OpenAI**: https://platform.openai.com/api-keys (Format: `sk-...`)
   - **Claude**: https://console.anthropic.com/ (Format: `sk-ant-...`)
   - **Deepseek**: https://platform.deepseek.com/ (Format: `sk-...`)
   - **Ollama**: Local installation (Endpoint: `http://localhost:11434`)

## Environment Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Required Configuration
NOTION_API_KEY=secret_your_notion_integration_token
SECRET_KEY=your-secret-key-for-flask-sessions

# AI Provider Configuration (configure at least one)
OPENAI_API_KEY=sk-your-openai-api-key
CLAUDE_API_KEY=sk-ant-your-claude-api-key
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
OLLAMA_ENDPOINT=http://localhost:11434

# Application Configuration
AI_PROVIDER=openai  # Default AI provider
BLOG_DATABASE_ID=your-notion-database-id-for-blog-posts

# Environment Settings
FLASK_ENV=production  # or development
LOG_LEVEL=INFO        # DEBUG, INFO, WARNING, ERROR
```

### Configuration Validation

Run the configuration validator:

```bash
python deploy.py --validate-only --environment production
```

## Development Deployment

### Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd notion-ai-integration
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Setup Development Environment**
   ```bash
   python -c "from config.development import setup_development_environment; setup_development_environment()"
   ```

5. **Run Application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

### Development Features

- **Debug Mode**: Enabled by default
- **Hot Reload**: Automatic restart on code changes
- **Detailed Logging**: Debug-level logging to console and file
- **Relaxed Security**: Permissive CORS and CSP for development

## Production Deployment

### Automated Deployment

Use the deployment script for automated setup:

```bash
# Run as root for system-level configuration
sudo python deploy.py --environment production
```

This will:
- Validate environment and dependencies
- Install Python packages
- Create required directories
- Setup logging configuration
- Create systemd service (Linux)
- Create nginx configuration
- Run health checks

### Manual Deployment

#### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv nginx redis-server -y

# Create application user
sudo useradd -r -s /bin/false notion-ai
sudo mkdir -p /opt/notion-ai
sudo chown notion-ai:notion-ai /opt/notion-ai
```

#### 2. Application Setup

```bash
# Switch to application directory
cd /opt/notion-ai

# Create virtual environment
sudo -u notion-ai python3 -m venv venv
sudo -u notion-ai venv/bin/pip install --upgrade pip

# Install application
sudo -u notion-ai git clone <repository-url> .
sudo -u notion-ai venv/bin/pip install -r requirements.txt
sudo -u notion-ai venv/bin/pip install gunicorn
```

#### 3. Configuration

```bash
# Create environment file
sudo -u notion-ai cp .env.example .env
sudo -u notion-ai nano .env  # Configure with your API keys

# Create log directories
sudo mkdir -p /var/log/notion-ai
sudo chown notion-ai:notion-ai /var/log/notion-ai
```

#### 4. Systemd Service

Create `/etc/systemd/system/notion-ai.service`:

```ini
[Unit]
Description=Notion AI Integration System
After=network.target

[Service]
Type=exec
User=notion-ai
Group=notion-ai
WorkingDirectory=/opt/notion-ai
Environment=PATH=/opt/notion-ai/venv/bin
Environment=FLASK_ENV=production
ExecStart=/opt/notion-ai/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable notion-ai
sudo systemctl start notion-ai
```

#### 5. Nginx Configuration

Create `/etc/nginx/sites-available/notion-ai`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /opt/notion-ai/static;
        expires 1y;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/notion-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Docker Deployment

### Quick Start with Docker Compose

1. **Prepare Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Check Status**
   ```bash
   docker-compose ps
   docker-compose logs -f notion-ai
   ```

### Production Docker Deployment

1. **Build Production Image**
   ```bash
   docker build -t notion-ai:latest .
   ```

2. **Run with Production Settings**
   ```bash
   docker run -d \
     --name notion-ai-prod \
     --restart unless-stopped \
     -p 5000:5000 \
     --env-file .env \
     -v $(pwd)/logs:/app/logs \
     -v $(pwd)/config/backups:/app/config/backups \
     notion-ai:latest
   ```

### Docker Compose Services

The Docker Compose setup includes:

- **notion-ai**: Main application container
- **redis**: Redis cache for rate limiting and sessions
- **nginx**: Reverse proxy and load balancer

## Monitoring and Maintenance

### Health Checks

The application provides several health check endpoints:

- **Basic Health Check**: `GET /health`
- **Detailed Health Check**: `GET /api/health`
- **System Information**: `GET /api/system/info`

### Monitoring Commands

```bash
# Check application status
systemctl status notion-ai

# View logs
journalctl -u notion-ai -f

# Check nginx status
systemctl status nginx

# View nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Check application health
curl http://localhost/health
```

### Log Files

- **Application Logs**: `/var/log/notion-ai/app.log`
- **Structured Logs**: `/var/log/notion-ai/app_structured.log`
- **Error Logs**: `/var/log/notion-ai/error.log`
- **Nginx Access**: `/var/log/nginx/access.log`
- **Nginx Error**: `/var/log/nginx/error.log`

### Backup and Recovery

#### Configuration Backup

```bash
# Manual backup
python -c "
from config.ai_config import get_config
from config.errors import ConfigurationRecovery
import json
config = get_config()
recovery = ConfigurationRecovery()
result = recovery.create_comprehensive_backup(config, 'config')
print(json.dumps(result, indent=2))
"
```

#### Database Backup (if using external database)

```bash
# Redis backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

### Updates and Maintenance

#### Application Updates

```bash
# Stop service
sudo systemctl stop notion-ai

# Update code
cd /opt/notion-ai
sudo -u notion-ai git pull

# Update dependencies
sudo -u notion-ai venv/bin/pip install -r requirements.txt

# Run health check
sudo -u notion-ai venv/bin/python deploy.py --health-check

# Start service
sudo systemctl start notion-ai
```

#### System Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Restart services if needed
sudo systemctl restart notion-ai nginx redis-server
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Check logs:**
```bash
journalctl -u notion-ai -n 50
```

**Common causes:**
- Missing environment variables
- Invalid API keys
- Port already in use
- Permission issues

#### 2. API Errors

**Check configuration:**
```bash
python deploy.py --validate-only
```

**Test API connectivity:**
```bash
curl -X POST http://localhost:5000/api/integration/test \
  -H "Content-Type: application/json" \
  -d '{"test_type": "comprehensive"}'
```

#### 3. Performance Issues

**Check resource usage:**
```bash
htop
df -h
free -h
```

**Optimize settings:**
- Increase worker processes in gunicorn
- Add Redis for caching
- Optimize nginx buffer sizes

#### 4. SSL/HTTPS Issues

**Check certificate:**
```bash
openssl x509 -in /path/to/certificate.crt -text -noout
```

**Test SSL configuration:**
```bash
nginx -t
systemctl reload nginx
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Set environment variable
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# Restart application
systemctl restart notion-ai
```

### Getting Help

1. **Check application logs** for specific error messages
2. **Run health checks** to identify configuration issues
3. **Validate environment** using the deployment script
4. **Test individual components** (Notion API, AI providers)
5. **Check system resources** (memory, disk space, network)

### Performance Tuning

#### Application Level

- **Worker Processes**: Adjust based on CPU cores
- **Timeout Settings**: Increase for long-running AI requests
- **Rate Limiting**: Adjust based on usage patterns

#### System Level

- **Memory**: Ensure adequate RAM for workers
- **File Descriptors**: Increase limits for high concurrency
- **Network**: Optimize TCP settings for API calls

#### Caching

- **Redis**: Use for session storage and rate limiting
- **Nginx**: Enable caching for static assets
- **Application**: Implement response caching for expensive operations

## Security Considerations

### Production Security Checklist

- [ ] Use strong, unique SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure firewall to restrict access
- [ ] Use non-root user for application
- [ ] Regularly update dependencies
- [ ] Monitor logs for suspicious activity
- [ ] Implement proper backup procedures
- [ ] Use environment variables for sensitive data
- [ ] Enable rate limiting
- [ ] Configure security headers

### API Key Security

- Store API keys in environment variables only
- Never commit API keys to version control
- Rotate API keys regularly
- Monitor API usage for anomalies
- Use least-privilege access for Notion integrations

This deployment guide provides comprehensive instructions for deploying the Notion AI Integration System in various environments. Choose the deployment method that best fits your infrastructure and requirements.