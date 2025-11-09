"""
Development configuration settings for Notion AI Integration System.

This module contains development-specific configuration settings for
local development and testing.
"""

import os
from pathlib import Path

# Development Flask configuration
class DevelopmentConfig:
    """Development configuration class."""
    
    # Security settings (relaxed for development)
    SECRET_KEY = 'dev-secret-key-change-in-production'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Debug settings
    DEBUG = True
    TESTING = False
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_FILE = 'logs/app_dev.log'
    STRUCTURED_LOG_FILE = 'logs/app_structured_dev.log'
    
    # Performance settings (relaxed for development)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    
    # Rate limiting (development values - more permissive)
    RATE_LIMIT_STORAGE_URL = 'memory://'
    RATE_LIMIT_STRATEGY = 'fixed-window'
    
    # Security headers (relaxed for development)
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',  # More permissive for development
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: http:; "
            "connect-src 'self' https://api.openai.com https://api.anthropic.com "
            "https://api.deepseek.com https://api.notion.com http://localhost:*; "
            "font-src 'self' data:; "
            "object-src 'none'"
        )
    }
    
    # Health check configuration
    HEALTH_CHECK_TIMEOUT = 10  # seconds
    HEALTH_CHECK_INTERVAL = 30  # seconds
    
    # Monitoring and metrics (disabled in development)
    ENABLE_METRICS = False
    METRICS_PORT = 9090
    
    # Backup and recovery (minimal for development)
    BACKUP_RETENTION_DAYS = 7
    AUTO_BACKUP_ENABLED = False
    
    # External service timeouts (shorter for development)
    NOTION_API_TIMEOUT = 15
    AI_API_TIMEOUT = 30
    
    # Worker configuration (single process for development)
    WORKER_PROCESSES = 1
    WORKER_THREADS = 1
    WORKER_TIMEOUT = 60


# Environment-specific rate limits for development
DEVELOPMENT_RATE_LIMITS = {
    'api_chat': {'requests': 30, 'window': 60},  # 30 requests per minute
    'api_create_page': {'requests': 10, 'window': 60},  # 10 requests per minute
    'api_update_page': {'requests': 20, 'window': 60},  # 20 requests per minute
    'api_save_config': {'requests': 5, 'window': 60},   # 5 requests per minute
    'api_integration_test': {'requests': 10, 'window': 60},  # 10 requests per minute
    'default': {'requests': 100, 'window': 60}          # 100 requests per minute default
}

# Development logging configuration
DEVELOPMENT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(funcName)s() - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.FileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'logs/app_dev.log',
            'mode': 'a'
        }
    },
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'werkzeug': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

def get_development_config():
    """Get development configuration dictionary."""
    return {
        'flask': DevelopmentConfig,
        'rate_limits': DEVELOPMENT_RATE_LIMITS,
        'logging': DEVELOPMENT_LOGGING_CONFIG
    }

def setup_development_environment():
    """Set up development environment (create directories, etc.)."""
    # Create logs directory
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Create config backups directory
    backups_dir = Path('config/backups')
    backups_dir.mkdir(exist_ok=True)
    
    # Set development environment variables if not already set
    dev_env_vars = {
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': '1',
        'LOG_LEVEL': 'DEBUG'
    }
    
    for var, value in dev_env_vars.items():
        if not os.environ.get(var):
            os.environ[var] = value
    
    return {
        'directories_created': ['logs', 'config/backups'],
        'environment_variables_set': list(dev_env_vars.keys()),
        'setup_completed': True
    }

def validate_development_environment():
    """Validate development environment setup."""
    issues = []
    
    # Check if required directories exist
    required_dirs = ['logs', 'config', 'config/backups', 'static', 'templates']
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            issues.append(f"Missing directory: {dir_path}")
    
    # Check if .env.example exists for reference
    if not Path('.env.example').exists():
        issues.append("Missing .env.example file for configuration reference")
    
    # Check if at least one AI provider is configured
    ai_providers = ['OPENAI_API_KEY', 'CLAUDE_API_KEY', 'DEEPSEEK_API_KEY', 'OLLAMA_ENDPOINT']
    if not any(os.environ.get(var) for var in ai_providers):
        issues.append("No AI provider configured (set at least one API key)")
    
    # Check if Notion API key is configured
    if not os.environ.get('NOTION_API_KEY'):
        issues.append("Notion API key not configured")
    
    return {
        'validation_passed': len(issues) == 0,
        'issues': issues,
        'recommendations': [
            "Copy .env.example to .env and fill in your API keys",
            "Run 'python -c \"from config.development import setup_development_environment; setup_development_environment()\"' to create required directories",
            "Check the README.md for setup instructions"
        ] if issues else []
    }