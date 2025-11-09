"""
Advanced configuration validation and error handling for Notion AI Integration System.

This module provides comprehensive validation for API keys, configuration migration,
and detailed error handling with user-friendly error messages.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse
from datetime import datetime
import requests
from requests.exceptions import RequestException, Timeout

logger = logging.getLogger(__name__)

# Configuration version for migration system
CURRENT_CONFIG_VERSION = "1.0"

# API key validation patterns with enhanced format checking
API_KEY_PATTERNS = {
    "notion": {
        "pattern": r"^secret_[A-Za-z0-9]{43,}$",
        "description": "Notion integration token (starts with 'secret_')",
        "min_length": 50,
        "max_length": 100,
        "required_prefix": "secret_",
        "validation_rules": [
            "Must start with 'secret_'",
            "Must be at least 50 characters long",
            "Must contain only alphanumeric characters after prefix"
        ]
    },
    "openai": {
        "pattern": r"^sk-[A-Za-z0-9]{48,}$",
        "description": "OpenAI API key (starts with 'sk-')",
        "min_length": 51,
        "max_length": 60,
        "required_prefix": "sk-",
        "validation_rules": [
            "Must start with 'sk-'",
            "Must be exactly 51 characters long",
            "Must contain only alphanumeric characters after prefix"
        ]
    },
    "claude": {
        "pattern": r"^sk-ant-[A-Za-z0-9\-_]{95,}$",
        "description": "Claude API key (starts with 'sk-ant-')",
        "min_length": 103,
        "max_length": 120,
        "required_prefix": "sk-ant-",
        "validation_rules": [
            "Must start with 'sk-ant-'",
            "Must be at least 103 characters long",
            "Must contain only alphanumeric characters, hyphens, and underscores after prefix"
        ]
    },
    "deepseek": {
        "pattern": r"^sk-[A-Za-z0-9]{40,}$",
        "description": "Deepseek API key (starts with 'sk-')",
        "min_length": 43,
        "max_length": 60,
        "required_prefix": "sk-",
        "validation_rules": [
            "Must start with 'sk-'",
            "Must be at least 43 characters long",
            "Must contain only alphanumeric characters after prefix"
        ]
    }
}

# Configuration validation rules
VALIDATION_RULES = {
    "provider": {
        "required": True,
        "type": str,
        "allowed_values": ["openai", "claude", "deepseek", "ollama"],
        "description": "AI provider selection"
    },
    "notion_api_key": {
        "required": True,
        "type": str,
        "min_length": 50,
        "description": "Notion integration API key"
    },
    "openai_api_key": {
        "required": False,
        "type": str,
        "min_length": 40,
        "description": "OpenAI API key"
    },
    "claude_api_key": {
        "required": False,
        "type": str,
        "min_length": 40,
        "description": "Claude API key"
    },
    "deepseek_api_key": {
        "required": False,
        "type": str,
        "min_length": 40,
        "description": "Deepseek API key"
    },
    "ollama_endpoint": {
        "required": False,
        "type": str,
        "min_length": 10,
        "description": "Ollama server endpoint URL"
    },
    "blog_database_id": {
        "required": False,
        "type": str,
        "min_length": 32,
        "description": "Notion database ID for blog posts"
    }
}


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, error_code: Optional[str] = None):
        self.message = message
        self.field = field
        self.error_code = error_code
        super().__init__(self.message)


class ValidationResult:
    """Container for validation results with detailed error information."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
    
    def add_error(self, field: str, message: str, error_code: str = "VALIDATION_ERROR"):
        """Add a validation error."""
        self.is_valid = False
        self.errors.append({
            "field": field,
            "message": message,
            "error_code": error_code
        })
    
    def add_warning(self, field: str, message: str, warning_code: str = "VALIDATION_WARNING"):
        """Add a validation warning."""
        self.warnings.append({
            "field": field,
            "message": message,
            "warning_code": warning_code
        })
    
    def get_error_summary(self) -> str:
        """Get a human-readable summary of all errors."""
        if not self.errors:
            return "No validation errors"
        
        error_messages = [f"• {error['field']}: {error['message']}" for error in self.errors]
        return "Configuration validation failed:\n" + "\n".join(error_messages)


def validate_configuration(config: Dict[str, Any]) -> ValidationResult:
    """
    Comprehensive configuration validation with detailed error reporting.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        ValidationResult: Detailed validation results
    """
    result = ValidationResult()
    
    try:
        # Validate configuration structure
        _validate_structure(config, result)
        
        # Validate individual fields
        _validate_fields(config, result)
        
        # Validate API key formats
        _validate_api_key_formats(config, result)
        
        # Validate provider-specific requirements
        _validate_provider_requirements(config, result)
        
        # Validate URLs and endpoints
        _validate_endpoints(config, result)
        
        logger.info(f"Configuration validation completed. Valid: {result.is_valid}")
        
    except Exception as e:
        logger.error(f"Unexpected error during validation: {e}")
        result.add_error("general", f"Validation failed due to unexpected error: {str(e)}")
    
    return result


def _validate_structure(config: Dict[str, Any], result: ValidationResult) -> None:
    """Validate basic configuration structure."""
    if not isinstance(config, dict):
        result.add_error("config", "Configuration must be a dictionary", "INVALID_TYPE")
        return
    
    # Check for required fields
    for field, rules in VALIDATION_RULES.items():
        if rules.get("required", False) and field not in config:
            result.add_error(field, f"Required field '{field}' is missing", "MISSING_FIELD")
    
    # Check for unknown fields
    known_fields = set(VALIDATION_RULES.keys()) | {"version"}
    unknown_fields = set(config.keys()) - known_fields
    for field in unknown_fields:
        result.add_warning(field, f"Unknown configuration field '{field}'", "UNKNOWN_FIELD")


def _validate_fields(config: Dict[str, Any], result: ValidationResult) -> None:
    """Validate individual configuration fields."""
    for field, value in config.items():
        if field not in VALIDATION_RULES:
            continue
        
        rules = VALIDATION_RULES[field]
        
        # Type validation
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            result.add_error(field, f"Field '{field}' must be of type {expected_type.__name__}", "INVALID_TYPE")
            continue
        
        # String length validation
        if isinstance(value, str):
            min_length = rules.get("min_length")
            if min_length and len(value.strip()) < min_length:
                result.add_error(field, f"Field '{field}' must be at least {min_length} characters", "TOO_SHORT")
        
        # Allowed values validation
        allowed_values = rules.get("allowed_values")
        if allowed_values and value not in allowed_values:
            result.add_error(field, f"Field '{field}' must be one of: {', '.join(allowed_values)}", "INVALID_VALUE")


def _validate_api_key_formats(config: Dict[str, Any], result: ValidationResult) -> None:
    """Validate API key formats using enhanced validation rules."""
    for provider, pattern_info in API_KEY_PATTERNS.items():
        key_field = f"{provider}_api_key"
        if key_field in config and config[key_field]:
            api_key = config[key_field].strip()
            
            # Comprehensive validation for each API key
            validation_errors = _validate_single_api_key(api_key, provider, pattern_info)
            
            for error in validation_errors:
                result.add_error(key_field, error["message"], error["code"])


def _validate_single_api_key(api_key: str, provider: str, pattern_info: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Perform comprehensive validation on a single API key.
    
    Args:
        api_key: The API key to validate
        provider: Provider name
        pattern_info: Validation pattern information
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check if key is empty
    if not api_key:
        errors.append({
            "message": f"{provider.title()} API key cannot be empty",
            "code": "EMPTY_KEY"
        })
        return errors
    
    # Check prefix
    required_prefix = pattern_info.get("required_prefix", "")
    if required_prefix and not api_key.startswith(required_prefix):
        errors.append({
            "message": f"{provider.title()} API key must start with '{required_prefix}'",
            "code": "INVALID_PREFIX"
        })
    
    # Check length
    min_length = pattern_info.get("min_length", 0)
    max_length = pattern_info.get("max_length", float('inf'))
    
    if len(api_key) < min_length:
        errors.append({
            "message": f"{provider.title()} API key must be at least {min_length} characters long",
            "code": "TOO_SHORT"
        })
    
    if len(api_key) > max_length:
        errors.append({
            "message": f"{provider.title()} API key must not exceed {max_length} characters",
            "code": "TOO_LONG"
        })
    
    # Check pattern
    pattern = pattern_info["pattern"]
    if not re.match(pattern, api_key):
        errors.append({
            "message": f"Invalid {pattern_info['description']} format. {' '.join(pattern_info.get('validation_rules', []))}",
            "code": "INVALID_FORMAT"
        })
    
    # Check for common issues
    if " " in api_key:
        errors.append({
            "message": f"{provider.title()} API key cannot contain spaces",
            "code": "CONTAINS_SPACES"
        })
    
    # Check for suspicious patterns
    if api_key.count(api_key[0]) > len(api_key) * 0.8:  # More than 80% same character
        errors.append({
            "message": f"{provider.title()} API key appears to be invalid (too many repeated characters)",
            "code": "SUSPICIOUS_PATTERN"
        })
    
    return errors


def _validate_provider_requirements(config: Dict[str, Any], result: ValidationResult) -> None:
    """Validate that selected provider has required configuration."""
    provider = config.get("provider")
    if not provider:
        return
    
    # Check if selected provider has required API key
    if provider in ["openai", "claude", "deepseek"]:
        key_field = f"{provider}_api_key"
        if not config.get(key_field):
            result.add_error(
                key_field,
                f"API key required for selected provider '{provider}'",
                "MISSING_PROVIDER_KEY"
            )
    elif provider == "ollama":
        endpoint = config.get("ollama_endpoint")
        if not endpoint:
            result.add_error(
                "ollama_endpoint",
                "Ollama endpoint required for Ollama provider",
                "MISSING_ENDPOINT"
            )


def _validate_endpoints(config: Dict[str, Any], result: ValidationResult) -> None:
    """Validate URL endpoints."""
    ollama_endpoint = config.get("ollama_endpoint")
    if ollama_endpoint:
        if not _is_valid_url(ollama_endpoint):
            result.add_error(
                "ollama_endpoint",
                "Invalid URL format for Ollama endpoint",
                "INVALID_URL"
            )


def _is_valid_url(url: str) -> bool:
    """Check if URL has valid format."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def test_api_key_connectivity(provider: str, api_key: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Test API key connectivity by making a simple API call.
    
    Args:
        provider: AI provider name
        api_key: API key to test
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (success, message)
    """
    try:
        if provider == "openai":
            return _test_openai_key(api_key, timeout)
        elif provider == "claude":
            return _test_claude_key(api_key, timeout)
        elif provider == "deepseek":
            return _test_deepseek_key(api_key, timeout)
        elif provider == "notion":
            return _test_notion_key(api_key, timeout)
        else:
            return False, f"Connectivity testing not supported for provider: {provider}"
    
    except Exception as e:
        logger.error(f"Error testing {provider} API key: {e}")
        return False, f"Connection test failed: {str(e)}"


def _test_openai_key(api_key: str, timeout: int) -> Tuple[bool, str]:
    """Test OpenAI API key connectivity."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Simple API call to list models
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return True, "OpenAI API key is valid and working"
        elif response.status_code == 401:
            return False, "OpenAI API key is invalid or expired"
        else:
            return False, f"OpenAI API returned status code: {response.status_code}"
    
    except Timeout:
        return False, "OpenAI API request timed out"
    except RequestException as e:
        return False, f"OpenAI API connection failed: {str(e)}"


def _test_claude_key(api_key: str, timeout: int) -> Tuple[bool, str]:
    """Test Claude API key connectivity."""
    try:
        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Simple API call to test authentication
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "Hi"}]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return True, "Claude API key is valid and working"
        elif response.status_code == 401:
            return False, "Claude API key is invalid or expired"
        else:
            return False, f"Claude API returned status code: {response.status_code}"
    
    except Timeout:
        return False, "Claude API request timed out"
    except RequestException as e:
        return False, f"Claude API connection failed: {str(e)}"


def _test_deepseek_key(api_key: str, timeout: int) -> Tuple[bool, str]:
    """Test Deepseek API key connectivity."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Simple API call to test authentication
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1
        }
        
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return True, "Deepseek API key is valid and working"
        elif response.status_code == 401:
            return False, "Deepseek API key is invalid or expired"
        else:
            return False, f"Deepseek API returned status code: {response.status_code}"
    
    except Timeout:
        return False, "Deepseek API request timed out"
    except RequestException as e:
        return False, f"Deepseek API connection failed: {str(e)}"


def _test_notion_key(api_key: str, timeout: int) -> Tuple[bool, str]:
    """Test Notion API key connectivity."""
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Simple API call to list users (requires minimal permissions)
        response = requests.get(
            "https://api.notion.com/v1/users/me",
            headers=headers,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return True, "Notion API key is valid and working"
        elif response.status_code == 401:
            return False, "Notion API key is invalid or expired"
        else:
            return False, f"Notion API returned status code: {response.status_code}"
    
    except Timeout:
        return False, "Notion API request timed out"
    except RequestException as e:
        return False, f"Notion API connection failed: {str(e)}"


def test_ollama_connectivity(endpoint: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Test Ollama server connectivity.
    
    Args:
        endpoint: Ollama server endpoint URL
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Test basic connectivity to Ollama server
        response = requests.get(
            f"{endpoint.rstrip('/')}/api/tags",
            timeout=timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_count = len(models)
            return True, f"Ollama server is running with {model_count} models available"
        else:
            return False, f"Ollama server returned status code: {response.status_code}"
    
    except Timeout:
        return False, "Ollama server request timed out"
    except RequestException as e:
        return False, f"Ollama server connection failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error testing Ollama: {str(e)}"


def validate_configuration_with_recovery(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate configuration and provide recovery suggestions.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Dict containing validation results and recovery suggestions
    """
    validation_result = validate_configuration(config)
    
    result = {
        "is_valid": validation_result.is_valid,
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
        "recovery_suggestions": [],
        "auto_fix_available": False
    }
    
    # Generate recovery suggestions based on errors
    for error in validation_result.errors:
        field = error["field"]
        error_code = error["error_code"]
        
        suggestions = _get_recovery_suggestions_for_error(field, error_code)
        result["recovery_suggestions"].extend(suggestions)
    
    # Check if auto-fix is available
    result["auto_fix_available"] = _can_auto_fix_errors(validation_result.errors)
    
    return result


def _get_recovery_suggestions_for_error(field: str, error_code: str) -> List[str]:
    """Get specific recovery suggestions for validation errors."""
    suggestions = []
    
    if error_code == "MISSING_FIELD":
        suggestions.append(f"Add the required field '{field}' to your configuration")
        if field.endswith("_api_key"):
            provider = field.replace("_api_key", "")
            suggestions.append(f"Obtain a valid API key from {provider.title()} and add it to the configuration")
    
    elif error_code == "INVALID_FORMAT":
        if field.endswith("_api_key"):
            provider = field.replace("_api_key", "")
            pattern_info = API_KEY_PATTERNS.get(provider, {})
            rules = pattern_info.get("validation_rules", [])
            suggestions.extend([f"Ensure your {provider.title()} API key follows these rules: {rule}" for rule in rules])
    
    elif error_code == "INVALID_PREFIX":
        if field.endswith("_api_key"):
            provider = field.replace("_api_key", "")
            pattern_info = API_KEY_PATTERNS.get(provider, {})
            prefix = pattern_info.get("required_prefix", "")
            suggestions.append(f"Ensure your {provider.title()} API key starts with '{prefix}'")
    
    elif error_code == "TOO_SHORT" or error_code == "TOO_LONG":
        if field.endswith("_api_key"):
            provider = field.replace("_api_key", "")
            pattern_info = API_KEY_PATTERNS.get(provider, {})
            min_len = pattern_info.get("min_length", 0)
            max_len = pattern_info.get("max_length", float('inf'))
            suggestions.append(f"Ensure your {provider.title()} API key is between {min_len} and {max_len} characters")
    
    elif error_code == "INVALID_VALUE":
        if field == "provider":
            suggestions.append("Select a valid AI provider: openai, claude, deepseek, or ollama")
    
    elif error_code == "INVALID_URL":
        if field == "ollama_endpoint":
            suggestions.append("Ensure the Ollama endpoint is a valid URL (e.g., http://localhost:11434)")
    
    return suggestions


def _can_auto_fix_errors(errors: List[Dict[str, Any]]) -> bool:
    """Check if validation errors can be automatically fixed."""
    auto_fixable_codes = ["MISSING_FIELD", "INVALID_VALUE"]
    
    for error in errors:
        if error["error_code"] not in auto_fixable_codes:
            return False
    
    return True


def auto_fix_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempt to automatically fix common configuration issues.
    
    Args:
        config: Configuration dictionary to fix
        
    Returns:
        Dict containing fix results and updated configuration
    """
    result = {
        "success": False,
        "fixes_applied": [],
        "remaining_errors": [],
        "updated_config": config.copy()
    }
    
    try:
        updated_config = config.copy()
        
        # Fix missing fields with defaults
        from .ai_config import DEFAULT_CONFIG
        for key, default_value in DEFAULT_CONFIG.items():
            if key not in updated_config:
                updated_config[key] = default_value
                result["fixes_applied"].append(f"Added missing field '{key}' with default value")
        
        # Fix invalid provider
        if updated_config.get("provider") not in ["openai", "claude", "deepseek", "ollama"]:
            updated_config["provider"] = "openai"
            result["fixes_applied"].append("Reset invalid provider to 'openai'")
        
        # Fix invalid Ollama endpoint
        ollama_endpoint = updated_config.get("ollama_endpoint", "")
        if ollama_endpoint and not _is_valid_url(ollama_endpoint):
            updated_config["ollama_endpoint"] = "http://localhost:11434"
            result["fixes_applied"].append("Reset invalid Ollama endpoint to default")
        
        # Add version if missing
        if "version" not in updated_config:
            updated_config["version"] = CURRENT_CONFIG_VERSION
            result["fixes_applied"].append("Added missing version field")
        
        result["updated_config"] = updated_config
        
        # Validate the fixed configuration
        validation_result = validate_configuration(updated_config)
        result["remaining_errors"] = validation_result.errors
        result["success"] = len(result["fixes_applied"]) > 0
        
    except Exception as e:
        result["remaining_errors"].append({
            "field": "general",
            "message": f"Auto-fix failed: {str(e)}",
            "error_code": "AUTO_FIX_ERROR"
        })
    
    return result


def get_validation_report(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive validation report for configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict containing comprehensive validation report
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "config_version": config.get("version", "unknown"),
        "validation_summary": {},
        "field_analysis": {},
        "security_analysis": {},
        "recommendations": []
    }
    
    try:
        # Basic validation
        validation_result = validate_configuration(config)
        report["validation_summary"] = {
            "is_valid": validation_result.is_valid,
            "error_count": len(validation_result.errors),
            "warning_count": len(validation_result.warnings),
            "errors": validation_result.errors,
            "warnings": validation_result.warnings
        }
        
        # Field-by-field analysis
        for field, value in config.items():
            field_analysis = {
                "present": True,
                "type": type(value).__name__,
                "length": len(str(value)) if value else 0,
                "empty": not bool(value),
                "issues": []
            }
            
            if field.endswith("_api_key") and value:
                # API key analysis
                provider = field.replace("_api_key", "")
                if provider in API_KEY_PATTERNS:
                    pattern_info = API_KEY_PATTERNS[provider]
                    key_errors = _validate_single_api_key(value, provider, pattern_info)
                    field_analysis["issues"] = [error["message"] for error in key_errors]
                    field_analysis["format_valid"] = len(key_errors) == 0
            
            report["field_analysis"][field] = field_analysis
        
        # Security analysis
        report["security_analysis"] = {
            "has_api_keys": any(key.endswith("_api_key") and config.get(key) for key in config.keys()),
            "empty_api_keys": [key for key in config.keys() if key.endswith("_api_key") and not config.get(key)],
            "potentially_invalid_keys": [],
            "security_score": 0
        }
        
        # Calculate security score
        total_providers = 4  # openai, claude, deepseek, ollama
        configured_providers = sum(1 for key in config.keys() if key.endswith("_api_key") and config.get(key))
        report["security_analysis"]["security_score"] = (configured_providers / total_providers) * 100
        
        # Generate recommendations
        if not validation_result.is_valid:
            report["recommendations"].append("Fix validation errors before using the system")
        
        if report["security_analysis"]["empty_api_keys"]:
            report["recommendations"].append("Configure API keys for the providers you want to use")
        
        if config.get("provider") not in ["openai", "claude", "deepseek", "ollama"]:
            report["recommendations"].append("Select a valid AI provider")
        
        # Check for outdated configuration
        if config.get("version", "0.1") != CURRENT_CONFIG_VERSION:
            report["recommendations"].append("Update configuration to the latest version")
        
    except Exception as e:
        report["validation_summary"]["error"] = f"Report generation failed: {str(e)}"
    
    return report