"""
Security and input validation utilities for Notion AI Integration System.

This module provides comprehensive input validation, rate limiting, CSRF protection,
and other security measures to protect the application from common vulnerabilities.
"""

import re
import html
import logging
from typing import Dict, Any, List, Optional, Union
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import secrets
from flask import request, session, abort, jsonify
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMITS = {
    'api_chat': {'requests': 30, 'window': 60},  # 30 requests per minute
    'api_create_page': {'requests': 10, 'window': 60},  # 10 requests per minute
    'api_update_page': {'requests': 20, 'window': 60},  # 20 requests per minute
    'api_save_config': {'requests': 5, 'window': 60},   # 5 requests per minute
    'default': {'requests': 100, 'window': 60}          # 100 requests per minute default
}

# Input validation patterns
VALIDATION_PATTERNS = {
    'notion_page_id': r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
    'notion_database_id': r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
    'provider_name': r'^(openai|claude|deepseek|ollama)$',
    'api_key_openai': r'^sk-[A-Za-z0-9]{48,}$',
    'api_key_claude': r'^sk-ant-[A-Za-z0-9\-_]{95,}$',
    'api_key_deepseek': r'^sk-[A-Za-z0-9]{40,}$',
    'api_key_notion': r'^secret_[A-Za-z0-9]{43,}$',
    'url': r'^https?://[^\s/$.?#].[^\s]*$',
    'safe_string': r'^[a-zA-Z0-9\s\-_.,!?()]+$'
}

# Content length limits
CONTENT_LIMITS = {
    'chat_message': 10000,      # 10KB for chat messages
    'page_title': 200,          # 200 chars for page titles
    'page_content': 100000,     # 100KB for page content
    'api_key': 200,             # 200 chars for API keys
    'endpoint_url': 500,        # 500 chars for URLs
    'general_text': 1000        # 1KB for general text fields
}

# Rate limiting storage (in production, use Redis or database)
rate_limit_storage = defaultdict(list)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, field: str, message: str, error_code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    
    def __init__(self, message: str, error_code: str = "SECURITY_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

def validate_input(field_name: str, value: Any, validation_type: str, 
                  required: bool = True, max_length: Optional[int] = None) -> str:
    """
    Validate and sanitize input values.
    
    Args:
        field_name: Name of the field being validated
        value: Value to validate
        validation_type: Type of validation to apply
        required: Whether the field is required
        max_length: Maximum allowed length
        
    Returns:
        Sanitized and validated value
        
    Raises:
        ValidationError: If validation fails
    """
    # Check if required field is present
    if required and (value is None or value == ""):
        raise ValidationError(field_name, f"Field '{field_name}' is required")
    
    # If not required and empty, return empty string
    if not required and (value is None or value == ""):
        return ""
    
    # Convert to string and strip whitespace
    str_value = str(value).strip()
    
    # Check length limits
    if max_length and len(str_value) > max_length:
        raise ValidationError(
            field_name, 
            f"Field '{field_name}' exceeds maximum length of {max_length} characters"
        )
    
    # Apply content-specific length limits
    if validation_type in CONTENT_LIMITS:
        limit = CONTENT_LIMITS[validation_type]
        if len(str_value) > limit:
            raise ValidationError(
                field_name,
                f"Field '{field_name}' exceeds maximum length of {limit} characters"
            )
    
    # Apply pattern validation
    if validation_type in VALIDATION_PATTERNS:
        pattern = VALIDATION_PATTERNS[validation_type]
        if not re.match(pattern, str_value):
            raise ValidationError(
                field_name,
                f"Field '{field_name}' has invalid format for {validation_type}"
            )
    
    # Sanitize based on validation type
    if validation_type == 'safe_string':
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', str_value)
        sanitized = html.escape(sanitized)
    elif validation_type in ['chat_message', 'page_content']:
        # Allow more characters but escape HTML
        sanitized = html.escape(str_value)
    elif validation_type == 'url':
        # Validate URL format and scheme
        parsed = urlparse(str_value)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(field_name, f"Invalid URL format for '{field_name}'")
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError(field_name, f"URL scheme must be http or https for '{field_name}'")
        sanitized = str_value
    else:
        # Default sanitization
        sanitized = html.escape(str_value)
    
    return sanitized

def validate_json_input(data: Dict[str, Any], validation_rules: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """
    Validate JSON input against validation rules.
    
    Args:
        data: Input data dictionary
        validation_rules: Dictionary of validation rules per field
        
    Returns:
        Dictionary of validated and sanitized values
        
    Raises:
        ValidationError: If validation fails
    """
    validated_data = {}
    
    for field_name, rules in validation_rules.items():
        value = data.get(field_name)
        
        validated_value = validate_input(
            field_name=field_name,
            value=value,
            validation_type=rules.get('type', 'safe_string'),
            required=rules.get('required', False),
            max_length=rules.get('max_length')
        )
        
        validated_data[field_name] = validated_value
    
    return validated_data

def rate_limit(endpoint: str = None, requests_per_window: int = None, window_seconds: int = None):
    """
    Rate limiting decorator.
    
    Args:
        endpoint: Endpoint name for rate limiting
        requests_per_window: Number of requests allowed per window
        window_seconds: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get client identifier
            client_id = get_client_identifier()
            
            # Get rate limit configuration
            endpoint_name = endpoint or func.__name__
            config = RATE_LIMITS.get(endpoint_name, RATE_LIMITS['default'])
            
            max_requests = requests_per_window or config['requests']
            window = window_seconds or config['window']
            
            # Check rate limit
            if is_rate_limited(client_id, endpoint_name, max_requests, window):
                logger.warning(f"Rate limit exceeded for {client_id} on {endpoint_name}")
                
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'Rate limit exceeded. Please try again later.',
                        'error_code': 'RATE_LIMIT_EXCEEDED'
                    }), 429
                else:
                    abort(429)
            
            # Record request
            record_request(client_id, endpoint_name)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_client_identifier() -> str:
    """Get unique identifier for the client."""
    # Use IP address and User-Agent for identification
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    # Create hash of IP + User-Agent for privacy
    identifier = hashlib.sha256(f"{ip_address}:{user_agent}".encode()).hexdigest()[:16]
    return identifier

def is_rate_limited(client_id: str, endpoint: str, max_requests: int, window_seconds: int) -> bool:
    """Check if client is rate limited."""
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)
    
    # Get request history for this client and endpoint
    key = f"{client_id}:{endpoint}"
    requests = rate_limit_storage[key]
    
    # Remove old requests outside the window
    rate_limit_storage[key] = [req_time for req_time in requests if req_time > window_start]
    
    # Check if limit exceeded
    return len(rate_limit_storage[key]) >= max_requests

def record_request(client_id: str, endpoint: str):
    """Record a request for rate limiting."""
    key = f"{client_id}:{endpoint}"
    rate_limit_storage[key].append(datetime.now())

def generate_csrf_token() -> str:
    """Generate CSRF token for form protection."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def validate_csrf_token(token: str) -> bool:
    """Validate CSRF token."""
    session_token = session.get('csrf_token')
    if not session_token or not token:
        return False
    
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(session_token, token)

def csrf_protect(func):
    """CSRF protection decorator for forms."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'POST':
            # Check for CSRF token in form data or headers
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            
            if not validate_csrf_token(token):
                logger.warning(f"CSRF token validation failed for {request.endpoint}")
                
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': 'CSRF token validation failed',
                        'error_code': 'CSRF_ERROR'
                    }), 403
                else:
                    abort(403)
        
        return func(*args, **kwargs)
    return wrapper

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = re.sub(r'\.\.', '', sanitized)  # Remove parent directory references
    sanitized = sanitized.strip('. ')  # Remove leading/trailing dots and spaces
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized[:255]  # Limit to 255 characters

def validate_content_type(allowed_types: List[str]):
    """Decorator to validate request content type."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            content_type = request.content_type
            
            if content_type not in allowed_types:
                logger.warning(f"Invalid content type {content_type} for {request.endpoint}")
                
                return jsonify({
                    'success': False,
                    'error': f'Content type must be one of: {", ".join(allowed_types)}',
                    'error_code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_request_size(max_size_mb: int = 10):
    """Decorator to validate request size."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            content_length = request.content_length
            max_size_bytes = max_size_mb * 1024 * 1024
            
            if content_length and content_length > max_size_bytes:
                logger.warning(f"Request size {content_length} exceeds limit {max_size_bytes}")
                
                return jsonify({
                    'success': False,
                    'error': f'Request size exceeds {max_size_mb}MB limit',
                    'error_code': 'REQUEST_TOO_LARGE'
                }), 413
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def security_headers(func):
    """Add security headers to response."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        
        # Add security headers
        if hasattr(response, 'headers'):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.openai.com https://api.anthropic.com https://api.deepseek.com https://api.notion.com"
            )
        
        return response
    return wrapper

# Validation rule sets for different endpoints
CHAT_VALIDATION_RULES = {
    'message': {'type': 'chat_message', 'required': True, 'max_length': 10000},
    'provider': {'type': 'provider_name', 'required': False},
    'page_id': {'type': 'notion_page_id', 'required': False}
}

CREATE_PAGE_VALIDATION_RULES = {
    'database_id': {'type': 'notion_database_id', 'required': True},
    'title': {'type': 'page_title', 'required': True, 'max_length': 200},
    'content': {'type': 'page_content', 'required': False, 'max_length': 100000}
}

UPDATE_PAGE_VALIDATION_RULES = {
    'page_id': {'type': 'notion_page_id', 'required': True},
    'content': {'type': 'page_content', 'required': False, 'max_length': 100000}
}

CONFIG_VALIDATION_RULES = {
    'provider': {'type': 'provider_name', 'required': True},
    'notion_api_key': {'type': 'api_key_notion', 'required': True},
    'openai_api_key': {'type': 'api_key_openai', 'required': False},
    'claude_api_key': {'type': 'api_key_claude', 'required': False},
    'deepseek_api_key': {'type': 'api_key_deepseek', 'required': False},
    'ollama_endpoint': {'type': 'url', 'required': False},
    'blog_database_id': {'type': 'notion_database_id', 'required': False}
}

def clean_rate_limit_storage():
    """Clean old entries from rate limit storage (call periodically)."""
    cutoff_time = datetime.now() - timedelta(hours=1)
    
    for key in list(rate_limit_storage.keys()):
        rate_limit_storage[key] = [
            req_time for req_time in rate_limit_storage[key] 
            if req_time > cutoff_time
        ]
        
        # Remove empty entries
        if not rate_limit_storage[key]:
            del rate_limit_storage[key]

def get_security_report() -> Dict[str, Any]:
    """Generate security status report."""
    now = datetime.now()
    
    # Count active rate limit entries
    active_clients = len(rate_limit_storage)
    total_requests = sum(len(requests) for requests in rate_limit_storage.values())
    
    # Calculate request rate
    recent_requests = 0
    cutoff_time = now - timedelta(minutes=5)
    
    for requests in rate_limit_storage.values():
        recent_requests += len([req for req in requests if req > cutoff_time])
    
    return {
        'timestamp': now.isoformat(),
        'active_clients': active_clients,
        'total_tracked_requests': total_requests,
        'recent_requests_5min': recent_requests,
        'rate_limits_configured': len(RATE_LIMITS),
        'validation_patterns': len(VALIDATION_PATTERNS),
        'content_limits': CONTENT_LIMITS,
        'security_features': [
            'Rate limiting',
            'Input validation',
            'CSRF protection',
            'Content sanitization',
            'Security headers',
            'Request size limits'
        ]
    }