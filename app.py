"""
Flask Application - Notion AI Integration System

Main web application providing routes for dashboard, chat, editor, and settings
with comprehensive error handling and API endpoints.
"""

import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.exceptions import HTTPException
import traceback
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Import our services
from ai_service import get_ai_service, get_available_providers, validate_provider_config
from notion_service import NotionService
from config.ai_config import get_config, update_config, validate_api_keys, get_configuration_status
from config.errors import NotionServiceError, ConfigurationError, ErrorSeverity, ErrorCategory, handle_configuration_error
from config.security import (
    rate_limit, csrf_protect, security_headers, validate_content_type, validate_request_size,
    validate_json_input, generate_csrf_token, ValidationError, SecurityError,
    CHAT_VALIDATION_RULES, CREATE_PAGE_VALIDATION_RULES, UPDATE_PAGE_VALIDATION_RULES, CONFIG_VALIDATION_RULES,
    clean_rate_limit_storage
)
import time
import functools
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure structured logging
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'context'):
            log_entry['context'] = record.context
        
        return json.dumps(log_entry)

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', mode='a')
    ]
)

# Create structured logger for JSON logs
structured_logger = logging.getLogger('structured')
structured_handler = logging.FileHandler('app_structured.log', mode='a')
structured_handler.setFormatter(StructuredFormatter())
structured_logger.addHandler(structured_handler)
structured_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # Change this in production

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BACKOFF_MULTIPLIER = 2

def retry_on_failure(max_retries=MAX_RETRIES, delay=RETRY_DELAY, backoff=BACKOFF_MULTIPLIER, 
                    exceptions=(RequestException, ConnectionError, Timeout)):
    """
    Decorator for retrying functions on transient failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to retry on
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {current_delay}s...")
                        structured_logger.info("Retry attempt", extra={
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'delay': current_delay,
                            'error': str(e),
                            'error_type': type(e).__name__
                        })
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} retry attempts failed for {func.__name__}: {str(e)}")
                        structured_logger.error("Retry exhausted", extra={
                            'function': func.__name__,
                            'max_retries': max_retries,
                            'final_error': str(e),
                            'error_type': type(e).__name__
                        })
                except Exception as e:
                    # Don't retry on non-transient errors
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
            
            # If we get here, all retries failed
            raise last_exception
        return wrapper
    return decorator

def log_error_with_context(error, context, severity=ErrorSeverity.MEDIUM, category=ErrorCategory.SYSTEM, 
                          request_id=None, user_context=None):
    """
    Log error with structured context information.
    
    Args:
        error: Exception object
        context: Context where error occurred
        severity: Error severity level
        category: Error category
        request_id: Optional request ID for tracking
        user_context: Optional user context information
    """
    error_info = handle_configuration_error(error, context, severity, category)
    
    # Log to structured logger with additional context
    structured_logger.error("Application error", extra={
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context,
        'severity': severity.value,
        'category': category.value,
        'request_id': request_id,
        'user_context': user_context,
        'recovery_suggestions': error_info.get('recovery_suggestions', [])
    })
    
    return error_info

def render_error_template(error_type, error_title, error_message, error_code=None, 
                         recovery_suggestions=None, validation_errors=None, error_details=None):
    """
    Render appropriate error template based on error type.
    
    Args:
        error_type: Type of error (404, 500, configuration, etc.)
        error_title: Error title to display
        error_message: Error message to display
        error_code: HTTP error code
        recovery_suggestions: List of recovery suggestions
        validation_errors: List of validation errors
        error_details: Technical error details (for debug mode)
    
    Returns:
        Rendered template response
    """
    template_map = {
        404: 'error_404.html',
        500: 'error_500.html',
        'configuration': 'error_configuration.html'
    }
    
    template = template_map.get(error_type, 'error.html')
    
    context = {
        'error_title': error_title,
        'error_message': error_message,
        'error_code': error_code,
        'recovery_suggestions': recovery_suggestions or [],
        'validation_errors': validation_errors or [],
        'error_details': error_details if app.debug else None
    }
    
    return render_template(template, **context), error_code or 500

# Global error handlers with enhanced logging and recovery
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors with structured logging."""
    request_id = getattr(request, 'id', None)
    
    log_error_with_context(
        error, 
        f"404 error for URL: {request.url}",
        severity=ErrorSeverity.LOW,
        category=ErrorCategory.SYSTEM,
        request_id=request_id,
        user_context={'url': request.url, 'method': request.method}
    )
    
    return render_error_template(
        404,
        "Page Not Found",
        "The page you're looking for doesn't exist or has been moved.",
        error_code=404,
        recovery_suggestions=[
            "Check the URL for typos",
            "Go back to the dashboard and navigate from there",
            "Use the navigation menu to find what you're looking for",
            "Check if you have the necessary permissions"
        ]
    )

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors with structured logging."""
    request_id = getattr(request, 'id', None)
    
    log_error_with_context(
        error,
        "Internal server error",
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.SYSTEM,
        request_id=request_id,
        user_context={'url': request.url, 'method': request.method}
    )
    
    return render_error_template(
        500,
        "Internal Server Error",
        "An unexpected error occurred on the server. Our team has been notified.",
        error_code=500,
        recovery_suggestions=[
            "Wait a few minutes and try again",
            "Check your internet connection",
            "Verify your API keys in settings",
            "Try a different browser or clear your cache",
            "Contact support if the problem persists"
        ],
        error_details=traceback.format_exc() if app.debug else None
    )

@app.errorhandler(NotionServiceError)
def handle_notion_error(error):
    """Handle Notion service errors."""
    request_id = getattr(request, 'id', None)
    
    log_error_with_context(
        error,
        "Notion service error",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.CONNECTIVITY,
        request_id=request_id
    )
    
    return render_error_template(
        'configuration',
        "Notion Service Error",
        f"There was an issue connecting to Notion: {str(error)}",
        error_code=503,
        recovery_suggestions=[
            "Check your Notion API key in settings",
            "Verify your internet connection",
            "Ensure the Notion integration has proper permissions",
            "Try again in a few minutes"
        ]
    )

@app.errorhandler(ConfigurationError)
def handle_configuration_error_handler(error):
    """Handle configuration errors."""
    request_id = getattr(request, 'id', None)
    
    log_error_with_context(
        error,
        "Configuration error",
        severity=ErrorSeverity.MEDIUM,
        category=ErrorCategory.CONFIGURATION,
        request_id=request_id
    )
    
    return render_error_template(
        'configuration',
        "Configuration Error",
        f"There's an issue with your configuration: {str(error)}",
        error_code=400,
        recovery_suggestions=[
            "Go to Settings and check your configuration",
            "Verify all API keys are correctly entered",
            "Ensure you've selected a valid AI provider",
            "Test your API connections"
        ]
    )

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all other exceptions with comprehensive logging."""
    if isinstance(error, HTTPException):
        return error
    
    request_id = getattr(request, 'id', None)
    
    log_error_with_context(
        error,
        "Unhandled exception",
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.SYSTEM,
        request_id=request_id,
        user_context={'url': request.url, 'method': request.method}
    )
    
    return render_error_template(
        500,
        "Unexpected Error",
        "An unexpected error occurred. Please try again or contact support.",
        error_code=500,
        recovery_suggestions=[
            "Try refreshing the page",
            "Check your internet connection",
            "Clear your browser cache and cookies",
            "Try using a different browser",
            "Contact support if the problem persists"
        ],
        error_details=traceback.format_exc() if app.debug else None
    )

# Template context processors
@app.context_processor
def inject_csrf_token():
    """Inject CSRF token into all templates."""
    return dict(csrf_token=generate_csrf_token)

# Request ID middleware for tracking
@app.before_request
def before_request():
    """Add request ID for tracking."""
    import uuid
    request.id = str(uuid.uuid4())[:8]
    
    # Log request start
    structured_logger.info("Request started", extra={
        'request_id': request.id,
        'method': request.method,
        'url': request.url,
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', '')
    })

@app.after_request
def after_request(response):
    """Log request completion."""
    request_id = getattr(request, 'id', 'unknown')
    
    structured_logger.info("Request completed", extra={
        'request_id': request_id,
        'status_code': response.status_code,
        'content_length': response.content_length
    })
    
    return response

# Dashboard and page serving routes
@app.route('/')
def dashboard():
    """
    Dashboard route with error handling for Notion API.
    
    Displays accessible pages and databases with navigation to other sections.
    Requirements: 1.5, 1.6, 6.3
    """
    try:
        # Get configuration status
        config_status = get_configuration_status()
        
        # Initialize context with basic info
        context = {
            'config_valid': config_status.get('config_valid', False),
            'current_provider': config_status.get('current_provider', ''),
            'configured_providers': config_status.get('configured_providers', []),
            'pages': [],
            'databases': [],
            'error_message': None,
            'warning_message': None
        }
        
        # Check if configuration is valid
        if not config_status.get('config_valid', False):
            context['warning_message'] = "Configuration incomplete. Please check settings."
            logger.warning("Dashboard accessed with invalid configuration")
            return render_template('index.html', **context)
        
        # Try to get Notion data with retry logic
        try:
            notion_service = NotionService()
            
            # Get accessible pages with retry
            @retry_on_failure(exceptions=(NotionServiceError, RequestException, ConnectionError, Timeout))
            def get_pages_with_retry():
                return notion_service.get_accessible_pages()
            
            @retry_on_failure(exceptions=(NotionServiceError, RequestException, ConnectionError, Timeout))
            def get_databases_with_retry():
                return notion_service.get_accessible_databases()
            
            pages = get_pages_with_retry()
            context['pages'] = pages[:20]  # Limit to first 20 for performance
            
            databases = get_databases_with_retry()
            context['databases'] = databases[:10]  # Limit to first 10 for performance
            
            logger.info(f"Dashboard loaded: {len(pages)} pages, {len(databases)} databases")
            structured_logger.info("Dashboard data loaded", extra={
                'pages_count': len(pages),
                'databases_count': len(databases),
                'request_id': getattr(request, 'id', None)
            })
            
        except NotionServiceError as e:
            context['error_message'] = f"Notion API Error: {str(e)}"
            log_error_with_context(e, "Dashboard Notion service error", 
                                 severity=ErrorSeverity.MEDIUM, 
                                 category=ErrorCategory.CONNECTIVITY,
                                 request_id=getattr(request, 'id', None))
        except ConfigurationError as e:
            context['error_message'] = f"Configuration Error: {str(e)}"
            log_error_with_context(e, "Dashboard configuration error",
                                 severity=ErrorSeverity.MEDIUM,
                                 category=ErrorCategory.CONFIGURATION,
                                 request_id=getattr(request, 'id', None))
        except Exception as e:
            context['error_message'] = f"Error loading Notion data: {str(e)}"
            log_error_with_context(e, "Dashboard unexpected error",
                                 severity=ErrorSeverity.HIGH,
                                 category=ErrorCategory.SYSTEM,
                                 request_id=getattr(request, 'id', None))
        
        return render_template('index.html', **context)
        
    except Exception as e:
        logger.error(f"Critical error in dashboard route: {str(e)}")
        return render_template('error.html',
                             error_title="Dashboard Error",
                             error_message="Unable to load dashboard. Please check configuration.",
                             error_code=500), 500

@app.route('/chat')
def chat():
    """
    Chat interface route.
    
    Provides chat interface with AI provider selection and page context.
    Requirements: 1.5, 1.6, 6.3
    """
    try:
        # Get configuration and available providers
        config = get_config()
        available_providers = get_available_providers()
        current_provider = config.get('provider', 'openai')
        
        # Get accessible pages for context selection
        pages = []
        try:
            notion_service = NotionService()
            pages = notion_service.get_accessible_pages()
        except Exception as e:
            logger.warning(f"Could not load pages for chat context: {str(e)}")
        
        context = {
            'current_provider': current_provider,
            'available_providers': available_providers,
            'pages': pages,
            'config_valid': bool(config.get('notion_api_key') and config.get(f'{current_provider}_api_key'))
        }
        
        return render_template('chat.html', **context)
        
    except Exception as e:
        logger.error(f"Error in chat route: {str(e)}")
        return render_template('error.html',
                             error_title="Chat Error",
                             error_message="Unable to load chat interface.",
                             error_code=500), 500

@app.route('/editor')
def editor():
    """
    Page editor interface route.
    
    Provides interface for creating and editing Notion pages.
    Requirements: 1.5, 1.6, 6.3
    """
    try:
        # Get accessible databases for page creation
        databases = []
        try:
            notion_service = NotionService()
            databases = notion_service.get_accessible_databases()
        except Exception as e:
            logger.warning(f"Could not load databases for editor: {str(e)}")
        
        context = {
            'databases': databases,
            'config_valid': bool(get_config().get('notion_api_key'))
        }
        
        return render_template('editor.html', **context)
        
    except Exception as e:
        logger.error(f"Error in editor route: {str(e)}")
        return render_template('error.html',
                             error_title="Editor Error", 
                             error_message="Unable to load page editor.",
                             error_code=500), 500

@app.route('/settings')
@security_headers
def settings():
    """
    Settings configuration interface route.
    
    Provides interface for configuring AI providers and API keys.
    Requirements: 1.5, 1.6, 6.3
    """
    try:
        # Get current configuration and status
        config = get_config()
        config_status = get_configuration_status()
        available_providers = get_available_providers()
        
        # Mask sensitive API keys for display
        display_config = config.copy()
        for key in display_config:
            if 'api_key' in key and display_config[key]:
                display_config[key] = '*' * 8 + display_config[key][-4:]
        
        context = {
            'config': display_config,
            'config_status': config_status,
            'available_providers': available_providers,
            'validation_errors': config_status.get('validation_errors', {}),
            'api_validation': config_status.get('api_validation', {}),
            'csrf_token': generate_csrf_token()
        }
        
        return render_template('settings.html', **context)
        
    except Exception as e:
        logger.error(f"Error in settings route: {str(e)}")
        return render_error_template(
            500,
            "Settings Error",
            "Unable to load settings interface.",
            error_code=500
        )

# Chat API endpoints
@app.route('/api/chat', methods=['POST'])
@rate_limit('api_chat')
@validate_content_type(['application/json'])
@validate_request_size(1)  # 1MB limit for chat requests
@security_headers
def api_chat():
    """
    Chat API endpoint with message processing and security validation.
    
    Handles AI conversations with optional Notion page context integration.
    Requirements: 2.1, 2.2, 2.5, 6.2, 6.4, 6.5
    """
    try:
        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'error_code': 'MISSING_DATA'
            }), 400
        
        # Validate input using security module
        try:
            validated_data = validate_json_input(data, CHAT_VALIDATION_RULES)
            message = validated_data['message']
            provider = validated_data.get('provider', '')
            page_id = validated_data.get('page_id', '')
        except ValidationError as e:
            logger.warning(f"Chat input validation failed: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'field': e.field
            }), 400
        
        # Get current configuration
        config = get_config()
        
        # Use provider from request or fall back to config
        if provider:
            config['provider'] = provider
        else:
            provider = config.get('provider', 'openai')
        
        # Validate provider configuration
        validation_result = validate_provider_config(provider, config)
        if not validation_result.get('valid', False):
            return jsonify({
                'success': False,
                'error': f"Provider {provider} not properly configured: {validation_result.get('message', 'Unknown error')}"
            }), 400
        
        # Get page context if requested
        context = ""
        if page_id:
            try:
                notion_service = NotionService()
                context = notion_service.get_page_content(page_id)
                logger.info(f"Retrieved context from page {page_id} ({len(context)} characters)")
            except Exception as e:
                logger.warning(f"Could not retrieve page context for {page_id}: {str(e)}")
                # Continue without context rather than failing
        
        # Get AI service and process message
        try:
            ai_service = get_ai_service(config)
            response = ai_service.chat_with_context(message, context)
            
            logger.info(f"Chat response generated using {provider} (context: {bool(context)})")
            
            return jsonify({
                'success': True,
                'response': response,
                'provider': provider,
                'context_used': bool(context)
            })
            
        except Exception as e:
            error_msg = f"AI service error: {str(e)}"
            logger.error(f"AI service error in chat: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in chat API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/chat/providers', methods=['GET'])
def api_chat_providers():
    """
    Get available AI providers and their configuration status.
    
    Returns list of providers with validation status for provider switching.
    Requirements: 2.3, 6.2
    """
    try:
        config = get_config()
        providers_info = []
        
        for provider in get_available_providers():
            validation_result = validate_provider_config(provider, config)
            providers_info.append({
                'name': provider,
                'display_name': provider.title(),
                'configured': validation_result.get('valid', False),
                'message': validation_result.get('message', '')
            })
        
        return jsonify({
            'success': True,
            'providers': providers_info,
            'current_provider': config.get('provider', 'openai')
        })
        
    except Exception as e:
        logger.error(f"Error getting provider info: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get provider information'
        }), 500

# Page management API endpoints
@app.route('/api/create_page', methods=['POST'])
@rate_limit('api_create_page')
@validate_content_type(['application/json'])
@validate_request_size(5)  # 5MB limit for page creation
@security_headers
def api_create_page():
    """
    Create page API endpoint with comprehensive validation and security.
    
    Creates new pages in Notion databases with content validation.
    Requirements: 3.1, 3.2, 3.3, 3.5, 6.4, 6.5
    """
    try:
        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'error_code': 'MISSING_DATA'
            }), 400
        
        # Validate input using security module
        try:
            validated_data = validate_json_input(data, CREATE_PAGE_VALIDATION_RULES)
            database_id = validated_data['database_id']
            title = validated_data['title']
            content = validated_data.get('content', '')
            
            # Validate properties if provided
            properties = data.get('properties', {})
            if properties and not isinstance(properties, dict):
                raise ValidationError('properties', 'Properties must be a dictionary')
                
        except ValidationError as e:
            logger.warning(f"Create page input validation failed: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'field': e.field
            }), 400
        
        # Create page using Notion service
        try:
            notion_service = NotionService()
            page_id = notion_service.create_page_in_database(
                database_id=database_id,
                title=title,
                content=content,
                properties=properties
            )
            
            logger.info(f"Created page '{title}' in database {database_id}")
            
            return jsonify({
                'success': True,
                'page_id': page_id,
                'message': f"Page '{title}' created successfully"
            })
            
        except NotionServiceError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(f"Notion service error creating page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        except Exception as e:
            error_msg = f"Failed to create page: {str(e)}"
            logger.error(f"Unexpected error creating page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in create page API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/update_page', methods=['POST'])
def api_update_page():
    """
    Update page API endpoint with content synchronization.
    
    Updates existing Notion page content with validation.
    Requirements: 3.1, 3.2, 3.3, 3.5, 6.4
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        page_id = data.get('page_id', '').strip()
        content = data.get('content', '').strip()
        properties = data.get('properties', {})
        
        # Validate required fields
        if not page_id:
            return jsonify({
                'success': False,
                'error': 'Page ID is required'
            }), 400
        
        # Update page using Notion service
        try:
            notion_service = NotionService()
            
            # Update content if provided
            if content:
                notion_service.update_page_content(page_id, content)
            
            # Update properties if provided
            if properties:
                notion_service.update_page_properties(page_id, properties)
            
            logger.info(f"Updated page {page_id}")
            
            return jsonify({
                'success': True,
                'message': 'Page updated successfully'
            })
            
        except NotionServiceError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(f"Notion service error updating page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        except Exception as e:
            error_msg = f"Failed to update page: {str(e)}"
            logger.error(f"Unexpected error updating page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in update page API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/page/<page_id>', methods=['GET'])
def api_get_page(page_id: str):
    """
    Get page content API endpoint.
    
    Retrieves complete page content for editing or display.
    Requirements: 3.1, 3.2, 3.3, 3.5, 6.4
    """
    try:
        if not page_id or not page_id.strip():
            return jsonify({
                'success': False,
                'error': 'Page ID is required'
            }), 400
        
        # Get page content using Notion service
        try:
            notion_service = NotionService()
            content = notion_service.get_page_content(page_id.strip())
            
            logger.info(f"Retrieved content for page {page_id}")
            
            return jsonify({
                'success': True,
                'page_id': page_id,
                'content': content
            })
            
        except NotionServiceError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(f"Notion service error getting page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 404
        except Exception as e:
            error_msg = f"Failed to retrieve page: {str(e)}"
            logger.error(f"Unexpected error getting page: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get page API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/pages', methods=['GET'])
def api_get_pages():
    """
    Get accessible pages API endpoint.
    
    Returns list of accessible pages for selection in UI.
    Requirements: 1.2, 1.3, 6.4
    """
    try:
        # Get accessible pages using Notion service
        try:
            notion_service = NotionService()
            pages = notion_service.get_accessible_pages()
            
            logger.info(f"Retrieved {len(pages)} accessible pages")
            
            return jsonify({
                'success': True,
                'pages': pages
            })
            
        except NotionServiceError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(f"Notion service error getting pages: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        except Exception as e:
            error_msg = f"Failed to retrieve pages: {str(e)}"
            logger.error(f"Unexpected error getting pages: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get pages API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/databases', methods=['GET'])
def api_get_databases():
    """
    Get accessible databases API endpoint.
    
    Returns list of accessible databases for page creation.
    Requirements: 1.2, 1.3, 6.4
    """
    try:
        # Get accessible databases using Notion service
        try:
            notion_service = NotionService()
            databases = notion_service.get_accessible_databases()
            
            logger.info(f"Retrieved {len(databases)} accessible databases")
            
            return jsonify({
                'success': True,
                'databases': databases
            })
            
        except NotionServiceError as e:
            error_msg = f"Notion API error: {str(e)}"
            logger.error(f"Notion service error getting databases: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        except Exception as e:
            error_msg = f"Failed to retrieve databases: {str(e)}"
            logger.error(f"Unexpected error getting databases: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in get databases API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# Configuration management API
@app.route('/api/save_config', methods=['POST'])
@rate_limit('api_save_config')
@csrf_protect
@validate_content_type(['application/json'])
@validate_request_size(1)  # 1MB limit for config
@security_headers
def api_save_config():
    """
    Save configuration API endpoint with comprehensive validation and security.
    
    Updates system configuration with comprehensive validation.
    Requirements: 4.1, 4.2, 4.5, 6.4, 6.5
    """
    try:
        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'error_code': 'MISSING_DATA'
            }), 400
        
        # Validate input using security module
        try:
            validated_data = validate_json_input(data, CONFIG_VALIDATION_RULES)
        except ValidationError as e:
            logger.warning(f"Config input validation failed: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'field': e.field
            }), 400
        
        # Update configuration
        try:
            validation_result = update_config(data)
            
            if validation_result.is_valid:
                logger.info("Configuration updated successfully")
                return jsonify({
                    'success': True,
                    'message': 'Configuration saved successfully'
                })
            else:
                logger.warning(f"Configuration validation failed: {validation_result.get_error_summary()}")
                return jsonify({
                    'success': False,
                    'error': 'Configuration validation failed',
                    'validation_errors': validation_result.errors,
                    'validation_warnings': validation_result.warnings
                }), 400
                
        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            logger.error(f"Configuration save error: {str(e)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in save config API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/test_config', methods=['POST'])
def api_test_config():
    """
    Test configuration API endpoint.
    
    Tests API connectivity for configured providers.
    Requirements: 4.1, 4.2, 4.5
    """
    try:
        # Get request data
        data = request.get_json()
        provider = data.get('provider', '') if data else ''
        
        # Get current configuration
        config = get_config()
        
        # Test specific provider or all providers
        if provider:
            # Test single provider
            try:
                from config.ai_config import test_provider_connectivity
                result = test_provider_connectivity(provider)
                
                return jsonify({
                    'success': True,
                    'provider': provider,
                    'test_result': result
                })
                
            except Exception as e:
                logger.error(f"Error testing {provider} connectivity: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f"Failed to test {provider}: {str(e)}"
                }), 500
        else:
            # Test all configured providers
            try:
                validation_results = validate_api_keys(config, test_connectivity=True)
                
                return jsonify({
                    'success': True,
                    'test_results': validation_results
                })
                
            except Exception as e:
                logger.error(f"Error testing API keys: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f"Failed to test configuration: {str(e)}"
                }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in test config API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/config_status', methods=['GET'])
def api_config_status():
    """
    Get configuration status API endpoint.
    
    Returns comprehensive configuration status and validation results.
    Requirements: 4.1, 4.2, 4.5
    """
    try:
        # Get configuration status
        try:
            config_status = get_configuration_status()
            
            return jsonify({
                'success': True,
                'status': config_status
            })
            
        except Exception as e:
            logger.error(f"Error getting configuration status: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Failed to get configuration status: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in config status API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/backup_config', methods=['POST'])
def api_backup_config():
    """
    Create configuration backup API endpoint.
    
    Creates backup of current configuration for recovery.
    Requirements: 4.1, 4.2, 4.5
    """
    try:
        # Create configuration backup
        try:
            from config.errors import ConfigurationRecovery
            from config.ai_config import CONFIG_DIR
            
            config = get_config()
            recovery = ConfigurationRecovery()
            backup_result = recovery.create_comprehensive_backup(config, CONFIG_DIR)
            
            if backup_result['success']:
                logger.info(f"Configuration backup created: {', '.join(backup_result['backup_files'])}")
                return jsonify({
                    'success': True,
                    'message': 'Configuration backup created successfully',
                    'backup_files': backup_result['backup_files']
                })
            else:
                logger.warning(f"Backup creation had issues: {', '.join(backup_result['errors'])}")
                return jsonify({
                    'success': False,
                    'error': 'Backup creation failed',
                    'errors': backup_result['errors']
                }), 500
                
        except Exception as e:
            logger.error(f"Error creating configuration backup: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Failed to create backup: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in backup config API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/restore_config', methods=['POST'])
def api_restore_config():
    """
    Restore configuration from backup API endpoint.
    
    Restores configuration from available backups.
    Requirements: 4.1, 4.2, 4.5
    """
    try:
        # Get request data
        data = request.get_json()
        backup_file = data.get('backup_file', '') if data else ''
        
        # Restore configuration
        try:
            if backup_file:
                # Restore from specific backup file
                from config.errors import ConfigurationRecovery
                recovery = ConfigurationRecovery()
                restore_result = recovery.restore_from_backup(backup_file)
                
                if restore_result['success']:
                    logger.info(f"Configuration restored from {backup_file}")
                    return jsonify({
                        'success': True,
                        'message': f'Configuration restored from {backup_file}'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': restore_result.get('error', 'Restore failed')
                    }), 500
            else:
                # Restore from default backup
                from config.ai_config import restore_from_backup
                success = restore_from_backup()
                
                if success:
                    logger.info("Configuration restored from default backup")
                    return jsonify({
                        'success': True,
                        'message': 'Configuration restored from backup'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'No backup file found or restore failed'
                    }), 500
                    
        except Exception as e:
            logger.error(f"Error restoring configuration: {str(e)}")
            return jsonify({
                'success': False,
                'error': f"Failed to restore configuration: {str(e)}"
            }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in restore config API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

# Security monitoring and cleanup
@app.route('/api/security/status', methods=['GET'])
@security_headers
def api_security_status():
    """
    Get security status and monitoring information.
    
    Returns security metrics and system status.
    Requirements: 6.1, 6.2
    """
    try:
        from config.security import get_security_report
        
        security_report = get_security_report()
        
        return jsonify({
            'success': True,
            'security_report': security_report
        })
        
    except Exception as e:
        logger.error(f"Error getting security status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get security status'
        }), 500

# Health check endpoint for monitoring
@app.route('/health', methods=['GET', 'HEAD'])
@security_headers
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns system health status and basic metrics.
    Requirements: 6.1, 6.2
    """
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {}
        }
        
        # Check configuration
        try:
            config_status = get_configuration_status()
            health_status["checks"]["configuration"] = {
                "status": "healthy" if config_status.get("config_valid", False) else "warning",
                "message": "Configuration loaded successfully" if config_status.get("config_valid", False) else "Configuration issues detected"
            }
        except Exception as e:
            health_status["checks"]["configuration"] = {
                "status": "unhealthy",
                "message": f"Configuration check failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"
        
        # Check Notion connectivity (if configured)
        try:
            config = get_config()
            if config.get("notion_api_key"):
                notion_service = NotionService()
                # Quick test - just try to get user info
                notion_service.client.users.me()
                health_status["checks"]["notion"] = {
                    "status": "healthy",
                    "message": "Notion API accessible"
                }
            else:
                health_status["checks"]["notion"] = {
                    "status": "warning",
                    "message": "Notion API key not configured"
                }
        except Exception as e:
            health_status["checks"]["notion"] = {
                "status": "unhealthy",
                "message": f"Notion API check failed: {str(e)}"
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        
        # Check AI provider (current provider only)
        try:
            config = get_config()
            current_provider = config.get("provider", "openai")
            if config.get(f"{current_provider}_api_key") or current_provider == "ollama":
                ai_service = get_ai_service(config)
                # Quick test - just initialize the service
                health_status["checks"]["ai_provider"] = {
                    "status": "healthy",
                    "message": f"{current_provider.title()} service initialized"
                }
            else:
                health_status["checks"]["ai_provider"] = {
                    "status": "warning",
                    "message": f"{current_provider.title()} not configured"
                }
        except Exception as e:
            health_status["checks"]["ai_provider"] = {
                "status": "unhealthy",
                "message": f"AI provider check failed: {str(e)}"
            }
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"
        
        # Determine overall status
        check_statuses = [check["status"] for check in health_status["checks"].values()]
        if "unhealthy" in check_statuses:
            health_status["status"] = "unhealthy"
            status_code = 503
        elif "warning" in check_statuses:
            health_status["status"] = "degraded"
            status_code = 200
        else:
            status_code = 200
        
        # For HEAD requests, just return status
        if request.method == 'HEAD':
            return '', status_code
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        error_response = {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Health check system failure"
        }
        
        if request.method == 'HEAD':
            return '', 503
        
        return jsonify(error_response), 503

@app.route('/api/health', methods=['GET'])
@security_headers
def api_health_detailed():
    """
    Detailed health check API endpoint with comprehensive system status.
    
    Returns detailed health information for monitoring systems.
    Requirements: 6.1, 6.2
    """
    try:
        from config.ai_config import get_configuration_health_report
        
        # Get comprehensive health report
        health_report = get_configuration_health_report()
        
        # Add runtime information
        health_report["runtime"] = {
            "uptime_seconds": time.time() - app.start_time if hasattr(app, 'start_time') else 0,
            "active_rate_limit_clients": len(rate_limit_storage),
            "total_requests_tracked": sum(len(requests) for requests in rate_limit_storage.values())
        }
        
        # Determine HTTP status based on health
        overall_health = health_report.get("overall_health", "unknown")
        if overall_health == "critical":
            status_code = 503
        elif overall_health == "warning":
            status_code = 200
        elif overall_health == "healthy":
            status_code = 200
        else:
            status_code = 503
        
        return jsonify(health_report), status_code
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return jsonify({
            "overall_health": "critical",
            "error": "Health check system failure",
            "timestamp": datetime.utcnow().isoformat()
        }), 503

# System information endpoint
@app.route('/api/system/info', methods=['GET'])
@security_headers
def api_system_info():
    """
    System information endpoint for debugging and monitoring.
    
    Returns system configuration and status information.
    Requirements: 6.1, 6.2
    """
    try:
        import platform
        import sys
        
        system_info = {
            "application": {
                "name": "Notion AI Integration System",
                "version": "1.0.0",
                "debug_mode": app.debug
            },
            "system": {
                "platform": platform.platform(),
                "python_version": sys.version,
                "architecture": platform.architecture()[0]
            },
            "configuration": {
                "providers_available": get_available_providers(),
                "current_provider": get_config().get("provider", "unknown"),
                "config_valid": get_configuration_status().get("config_valid", False)
            },
            "security": get_security_report()
        }
        
        return jsonify(system_info)
        
    except Exception as e:
        logger.error(f"System info endpoint failed: {str(e)}")
        return jsonify({
            "error": "System information unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/api/integration/test', methods=['POST'])
@rate_limit('api_integration_test')
@validate_content_type(['application/json'])
@security_headers
def api_integration_test():
    """
    Integration test endpoint to verify all components work together.
    
    Tests the complete workflow from configuration to AI interaction.
    Requirements: All requirements (integration test)
    """
    try:
        data = request.get_json() or {}
        test_type = data.get('test_type', 'basic')
        
        test_results = {
            "test_type": test_type,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_success": False,
            "tests": {}
        }
        
        # Test 1: Configuration validation
        try:
            config = get_config()
            config_status = get_configuration_status()
            test_results["tests"]["configuration"] = {
                "success": config_status.get("config_valid", False),
                "message": "Configuration loaded and validated",
                "details": {
                    "provider": config.get("provider", "unknown"),
                    "has_notion_key": bool(config.get("notion_api_key")),
                    "configured_providers": config_status.get("configured_providers", [])
                }
            }
        except Exception as e:
            test_results["tests"]["configuration"] = {
                "success": False,
                "message": f"Configuration test failed: {str(e)}"
            }
        
        # Test 2: Notion service integration
        try:
            if config.get("notion_api_key"):
                notion_service = NotionService()
                pages = notion_service.get_accessible_pages()
                test_results["tests"]["notion_service"] = {
                    "success": True,
                    "message": f"Successfully retrieved {len(pages)} pages",
                    "details": {"page_count": len(pages)}
                }
            else:
                test_results["tests"]["notion_service"] = {
                    "success": False,
                    "message": "Notion API key not configured"
                }
        except Exception as e:
            test_results["tests"]["notion_service"] = {
                "success": False,
                "message": f"Notion service test failed: {str(e)}"
            }
        
        # Test 3: AI service integration
        try:
            current_provider = config.get("provider", "openai")
            if config.get(f"{current_provider}_api_key") or current_provider == "ollama":
                ai_service = get_ai_service(config)
                # Test with a simple message
                response = ai_service.chat_with_context("Hello, this is a test message.", "")
                test_results["tests"]["ai_service"] = {
                    "success": True,
                    "message": f"AI service ({current_provider}) responded successfully",
                    "details": {
                        "provider": current_provider,
                        "response_length": len(response)
                    }
                }
            else:
                test_results["tests"]["ai_service"] = {
                    "success": False,
                    "message": f"AI provider {current_provider} not configured"
                }
        except Exception as e:
            test_results["tests"]["ai_service"] = {
                "success": False,
                "message": f"AI service test failed: {str(e)}"
            }
        
        # Test 4: Security and validation
        try:
            # Test input validation
            test_input = {"message": "test", "provider": "openai"}
            validated = validate_json_input(test_input, CHAT_VALIDATION_RULES)
            
            # Test rate limiting (check if storage is working)
            client_id = get_client_identifier()
            
            test_results["tests"]["security"] = {
                "success": True,
                "message": "Security systems operational",
                "details": {
                    "validation_working": bool(validated),
                    "rate_limiting_active": bool(rate_limit_storage),
                    "client_id_generated": bool(client_id)
                }
            }
        except Exception as e:
            test_results["tests"]["security"] = {
                "success": False,
                "message": f"Security test failed: {str(e)}"
            }
        
        # Test 5: Error handling (if requested)
        if test_type == "comprehensive":
            try:
                # Test error handling by triggering a controlled error
                error_info = handle_configuration_error(
                    ValueError("Test error"), 
                    "integration_test",
                    ErrorSeverity.LOW,
                    ErrorCategory.SYSTEM
                )
                
                test_results["tests"]["error_handling"] = {
                    "success": True,
                    "message": "Error handling system working",
                    "details": {
                        "error_logged": bool(error_info),
                        "user_message_generated": bool(error_info.get("user_message")),
                        "recovery_suggestions": len(error_info.get("recovery_suggestions", []))
                    }
                }
            except Exception as e:
                test_results["tests"]["error_handling"] = {
                    "success": False,
                    "message": f"Error handling test failed: {str(e)}"
                }
        
        # Determine overall success
        test_successes = [test["success"] for test in test_results["tests"].values()]
        test_results["overall_success"] = all(test_successes)
        test_results["success_rate"] = sum(test_successes) / len(test_successes) if test_successes else 0
        
        # Log integration test results
        logger.info(f"Integration test completed: {test_results['success_rate']:.2%} success rate")
        
        status_code = 200 if test_results["overall_success"] else 207  # 207 Multi-Status for partial success
        return jsonify(test_results), status_code
        
    except Exception as e:
        logger.error(f"Integration test failed: {str(e)}")
        return jsonify({
            "test_type": test_type,
            "timestamp": datetime.utcnow().isoformat(),
            "overall_success": False,
            "error": f"Integration test system failure: {str(e)}"
        }), 500

# Periodic cleanup task (in production, use a proper task scheduler)
import threading
import time as time_module

def periodic_cleanup():
    """Periodic cleanup of rate limit storage and logs."""
    while True:
        try:
            clean_rate_limit_storage()
            logger.info("Performed periodic security cleanup")
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}")
        
        # Sleep for 1 hour
        time_module.sleep(3600)

# Initialize application startup time
app.start_time = time.time()

# Start cleanup thread in production
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    # Development server configuration
    logger.info("Starting Notion AI Integration System with enhanced security")
    # Allow overriding port via environment variable for local conflicts
    # Use default 5000 if PORT not set
    import os
    try:
        port = int(os.getenv('PORT', os.getenv('APP_PORT', '5000')))
    except ValueError:
        # Fallback to 5000 if an invalid port is provided
        port = 5000
    app.run(debug=True, host='0.0.0.0', port=port)