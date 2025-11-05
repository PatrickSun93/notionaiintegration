"""
Production configuration settings for Notion AI Integration System.

This module contains production-specific configuration settings including
security, performance, and deployment configurations.
"""

import os
from pathlib import Path

# Production Flask configuration
class ProductionConfig:
    """Production configuration class."""
    
    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Database and caching (if using external services)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', '/var/log/notion-ai/app.log')
    STRUCTURED_LOG_FILE = os.environ.get('STRUCTURED_LOG_FILE', '/var/log/notion-ai/app_structured.log')
    
    # Performance settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year cache for static files
    
    # Rate limiting (production values)
    RATE_LIMIT_STORAGE_URL = os.environ.get('RATE_LIMIT_STORAGE_URL', REDIS_URL)
    RATE_LIMIT_STRATEGY = 'fixed-window-elastic-expiry'
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.openai.com https://api.anthropic.com "
            "https://api.deepseek.com https://api.notion.com; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    }
    
    # Health check configuration
    HEALTH_CHECK_TIMEOUT = 30  # seconds
    HEALTH_CHECK_INTERVAL = 60  # seconds
    
    # Monitoring and metrics
    ENABLE_METRICS = os.environ.get('ENABLE_METRICS', 'true').lower() == 'true'
    METRICS_PORT = int(os.environ.get('METRICS_PORT', '9090'))
    
    # Backup and recovery
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'true').lower() == 'true'
    BACKUP_SCHEDULE = os.environ.get('BACKUP_SCHEDULE', '0 2 * * *')  # Daily at 2 AM
    
    # External service timeouts
    NOTION_API_TIMEOUT = int(os.environ.get('NOTION_API_TIMEOUT', '30'))
    AI_API_TIMEOUT = int(os.environ.get('AI_API_TIMEOUT', '60'))
    
    # Worker configuration (for async processing)
    WORKER_PROCESSES = int(os.environ.get('WORKER_PROCESSES', '4'))
    WORKER_THREADS = int(os.environ.get('WORKER_THREADS', '2'))
    WORKER_TIMEOUT = int(os.environ.get('WORKER_TIMEOUT', '120'))


# Environment-specific rate limits for production
PRODUCTION_RATE_LIMITS = {
    'api_chat': {'requests': 100, 'window': 60},  # 100 requests per minute
    'api_create_page': {'requests': 50, 'window': 60},  # 50 requests per minute
    'api_update_page': {'requests': 100, 'window': 60},  # 100 requests per minute
    'api_save_config': {'requests': 10, 'window': 60},   # 10 requests per minute
    'api_integration_test': {'requests': 5, 'window': 300},  # 5 requests per 5 minutes
    'default': {'requests': 200, 'window': 60}          # 200 requests per minute default
}

# Production logging configuration
PRODUCTION_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': '/var/log/notion-ai/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'json_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': '/var/log/notion-ai/app_structured.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': '/var/log/notion-ai/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file', 'json_file', 'error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'werkzeug': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        },
        'urllib3': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}

def get_production_config():
    """Get production configuration dictionary."""
    return {
        'flask': ProductionConfig,
        'rate_limits': PRODUCTION_RATE_LIMITS,
        'logging': PRODUCTION_LOGGING_CONFIG
    }

def validate_production_environment():
    """Validate that all required production environment variables are set."""
    required_vars = [
        'SECRET_KEY',
        'NOTION_API_KEY',
        'OPENAI_API_KEY',  # At least one AI provider should be configured
    ]
    
    optional_vars = [
        'CLAUDE_API_KEY',
        'DEEPSEEK_API_KEY',
        'OLLAMA_ENDPOINT',
        'REDIS_URL',
        'LOG_LEVEL',
        'WORKER_PROCESSES'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    # Log configured optional variables
    configured_optional = []
    for var in optional_vars:
        if os.environ.get(var):
            configured_optional.append(var)
    
    return {
        'required_vars_set': len(required_vars),
        'optional_vars_set': configured_optional,
        'validation_passed': True
    }