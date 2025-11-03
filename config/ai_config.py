"""
Configuration management service for Notion AI Integration System.

This module provides functions to manage AI provider configurations,
validate API keys, and handle configuration persistence with environment
variable support for production deployment.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if python-dotenv is not available
    def load_dotenv():
        pass

from .validation import validate_configuration, ValidationResult, ConfigurationError, test_api_key_connectivity, test_ollama_connectivity
from .migration import migrate_configuration, needs_migration, create_migration_backup, get_config_version

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Configuration file path
CONFIG_DIR = Path("config")
CONFIG_FILE = CONFIG_DIR / "settings.json"
CONFIG_BACKUP_FILE = CONFIG_DIR / "settings_backup.json"

# Current configuration version
CURRENT_CONFIG_VERSION = "1.0"

# Default configuration structure
DEFAULT_CONFIG = {
    "provider": "openai",
    "notion_api_key": "",
    "openai_api_key": "",
    "claude_api_key": "",
    "deepseek_api_key": "",
    "ollama_endpoint": "http://localhost:11434",
    "blog_database_id": ""
}

# Environment variable mappings for production deployment
ENV_VAR_MAPPING = {
    "notion_api_key": "NOTION_API_KEY",
    "openai_api_key": "OPENAI_API_KEY", 
    "claude_api_key": "CLAUDE_API_KEY",
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "ollama_endpoint": "OLLAMA_ENDPOINT",
    "blog_database_id": "BLOG_DATABASE_ID",
    "provider": "AI_PROVIDER"
}


def _ensure_config_directory() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(exist_ok=True)


def _load_from_file() -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded from file")
                return config
        else:
            logger.info("Configuration file not found, using defaults")
            return DEFAULT_CONFIG.copy()
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading configuration file: {e}")
        return DEFAULT_CONFIG.copy()


def _load_from_environment() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config = {}
    for config_key, env_var in ENV_VAR_MAPPING.items():
        env_value = os.getenv(env_var)
        if env_value:
            config[config_key] = env_value
            logger.debug(f"Loaded {config_key} from environment variable {env_var}")
    return config


def get_config() -> Dict[str, Any]:
    """
    Get the current configuration.
    
    Loads configuration from file and overrides with environment variables
    for production deployment support. Handles configuration migration if needed.
    
    Returns:
        Dict containing the current configuration
    """
    try:
        # Start with default configuration
        config = DEFAULT_CONFIG.copy()
        
        # Override with file configuration
        file_config = _load_from_file()
        config.update(file_config)
        
        # Check if migration is needed
        if needs_migration(config):
            logger.info("Configuration migration required")
            try:
                config = migrate_configuration(config)
                # Save migrated configuration
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config, f, indent=2)
                logger.info("Configuration migrated and saved")
            except Exception as e:
                logger.error(f"Configuration migration failed: {e}")
                # Continue with current config if migration fails
        
        # Override with environment variables (highest priority)
        env_config = _load_from_environment()
        config.update(env_config)
        
        logger.info("Configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG.copy()


def update_config(new_config: Dict[str, Any]) -> ValidationResult:
    """
    Update the configuration with new values using enhanced validation and backup.
    
    Args:
        new_config: Dictionary containing configuration updates
        
    Returns:
        ValidationResult: Detailed validation results and success status
    """
    try:
        from .errors import ConfigurationRecovery, handle_configuration_error, ErrorSeverity, ErrorCategory
        
        _ensure_config_directory()
        
        # Get current configuration
        current_config = get_config()
        
        # Update configuration with new values
        updated_config = current_config.copy()
        updated_config.update(new_config)
        
        # Enhanced validation with recovery suggestions
        from .validation import validate_configuration_with_recovery
        validation_result_enhanced = validate_configuration_with_recovery(updated_config)
        
        # Create ValidationResult object for compatibility
        validation_result = ValidationResult()
        if not validation_result_enhanced["is_valid"]:
            for error in validation_result_enhanced["errors"]:
                validation_result.add_error(error["field"], error["message"], error["error_code"])
            
            logger.error(f"Configuration validation failed: {validation_result.get_error_summary()}")
            return validation_result
        
        # Create comprehensive backup before saving
        current_version = get_config_version(current_config)
        recovery = ConfigurationRecovery()
        backup_result = recovery.create_comprehensive_backup(current_config, CONFIG_DIR)
        
        if backup_result["success"]:
            logger.info(f"Configuration backup created: {', '.join(backup_result['backup_files'])}")
        else:
            logger.warning(f"Backup creation had issues: {', '.join(backup_result['errors'])}")
        
        # Save to file with error handling
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(updated_config, f, indent=2)
        except Exception as save_error:
            # Attempt recovery if save fails
            error_info = handle_configuration_error(
                save_error, 
                "configuration_save", 
                ErrorSeverity.HIGH, 
                ErrorCategory.CONFIGURATION
            )
            
            validation_result.add_error("general", error_info["user_message"])
            return validation_result
        
        logger.info("Configuration updated successfully")
        return validation_result
        
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        result = ValidationResult()
        result.add_error("general", f"Failed to update configuration: {str(e)}")
        return result


def validate_api_keys(config: Optional[Dict[str, Any]] = None, test_connectivity: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Validate API keys for all configured providers.
    
    Args:
        config: Configuration dictionary (uses current config if None)
        test_connectivity: Whether to test actual API connectivity
        
    Returns:
        Dict mapping provider names to validation details
    """
    if config is None:
        config = get_config()
    
    validation_results = {}
    
    try:
        # Validate Notion API key
        notion_key = config.get("notion_api_key", "")
        notion_valid = _validate_notion_key(notion_key)
        notion_result = {"format_valid": notion_valid, "message": ""}
        
        if test_connectivity and notion_valid:
            conn_success, conn_message = test_api_key_connectivity("notion", notion_key)
            notion_result["connectivity"] = conn_success
            notion_result["message"] = conn_message
        
        validation_results["notion"] = notion_result
        
        # Validate OpenAI API key
        openai_key = config.get("openai_api_key", "")
        openai_valid = _validate_openai_key(openai_key)
        openai_result = {"format_valid": openai_valid, "message": ""}
        
        if test_connectivity and openai_valid:
            conn_success, conn_message = test_api_key_connectivity("openai", openai_key)
            openai_result["connectivity"] = conn_success
            openai_result["message"] = conn_message
        
        validation_results["openai"] = openai_result
        
        # Validate Claude API key
        claude_key = config.get("claude_api_key", "")
        claude_valid = _validate_claude_key(claude_key)
        claude_result = {"format_valid": claude_valid, "message": ""}
        
        if test_connectivity and claude_valid:
            conn_success, conn_message = test_api_key_connectivity("claude", claude_key)
            claude_result["connectivity"] = conn_success
            claude_result["message"] = conn_message
        
        validation_results["claude"] = claude_result
        
        # Validate Deepseek API key
        deepseek_key = config.get("deepseek_api_key", "")
        deepseek_valid = _validate_deepseek_key(deepseek_key)
        deepseek_result = {"format_valid": deepseek_valid, "message": ""}
        
        if test_connectivity and deepseek_valid:
            conn_success, conn_message = test_api_key_connectivity("deepseek", deepseek_key)
            deepseek_result["connectivity"] = conn_success
            deepseek_result["message"] = conn_message
        
        validation_results["deepseek"] = deepseek_result
        
        # Validate Ollama endpoint
        ollama_endpoint = config.get("ollama_endpoint", "")
        ollama_valid = _validate_ollama_endpoint(ollama_endpoint)
        ollama_result = {"format_valid": ollama_valid, "message": ""}
        
        if test_connectivity and ollama_valid:
            conn_success, conn_message = test_ollama_connectivity(ollama_endpoint)
            ollama_result["connectivity"] = conn_success
            ollama_result["message"] = conn_message
        
        validation_results["ollama"] = ollama_result
        
        logger.info("API key validation completed")
        return validation_results
        
    except Exception as e:
        logger.error(f"Error during API key validation: {e}")
        error_result = {"format_valid": False, "message": f"Validation error: {str(e)}"}
        return {provider: error_result for provider in ["notion", "openai", "claude", "deepseek", "ollama"]}


def _validate_config_structure(config: Dict[str, Any]) -> bool:
    """Validate that configuration has required structure."""
    required_keys = set(DEFAULT_CONFIG.keys())
    config_keys = set(config.keys())
    
    if not required_keys.issubset(config_keys):
        missing_keys = required_keys - config_keys
        logger.error(f"Missing required configuration keys: {missing_keys}")
        return False
    
    return True


def _validate_notion_key(api_key: str) -> bool:
    """Validate Notion API key format."""
    if not api_key:
        return False
    
    # Notion integration tokens start with "secret_" and are 50+ characters
    if api_key.startswith("secret_") and len(api_key) >= 50:
        return True
    
    logger.warning("Invalid Notion API key format")
    return False


def _validate_openai_key(api_key: str) -> bool:
    """Validate OpenAI API key format."""
    if not api_key:
        return False
    
    # OpenAI keys start with "sk-" and are typically 51 characters
    if api_key.startswith("sk-") and len(api_key) >= 40:
        return True
    
    logger.warning("Invalid OpenAI API key format")
    return False


def _validate_claude_key(api_key: str) -> bool:
    """Validate Claude API key format."""
    if not api_key:
        return False
    
    # Claude keys start with "sk-ant-" and are typically longer
    if api_key.startswith("sk-ant-") and len(api_key) >= 40:
        return True
    
    logger.warning("Invalid Claude API key format")
    return False


def _validate_deepseek_key(api_key: str) -> bool:
    """Validate Deepseek API key format."""
    if not api_key:
        return False
    
    # Deepseek keys start with "sk-" and are typically 40+ characters
    if api_key.startswith("sk-") and len(api_key) >= 40:
        return True
    
    logger.warning("Invalid Deepseek API key format")
    return False


def _validate_ollama_endpoint(endpoint: str) -> bool:
    """Validate Ollama endpoint format."""
    if not endpoint:
        return False
    
    # Basic URL validation for Ollama endpoint
    if endpoint.startswith(("http://", "https://")) and len(endpoint) > 10:
        return True
    
    logger.warning("Invalid Ollama endpoint format")
    return False


def _create_backup(config: Dict[str, Any]) -> None:
    """Create a backup of the current configuration."""
    try:
        _ensure_config_directory()
        with open(CONFIG_BACKUP_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        logger.debug("Configuration backup created")
    except Exception as e:
        logger.warning(f"Failed to create configuration backup: {e}")


def restore_from_backup() -> bool:
    """
    Restore configuration from backup file.
    
    Returns:
        bool: True if restore was successful, False otherwise
    """
    try:
        if not CONFIG_BACKUP_FILE.exists():
            logger.error("No backup file found")
            return False
        
        with open(CONFIG_BACKUP_FILE, 'r') as f:
            backup_config = json.load(f)
        
        # Validate backup configuration
        if not _validate_config_structure(backup_config):
            logger.error("Backup configuration is invalid")
            return False
        
        # Restore configuration
        with open(CONFIG_FILE, 'w') as f:
            json.dump(backup_config, f, indent=2)
        
        logger.info("Configuration restored from backup")
        return True
        
    except Exception as e:
        logger.error(f"Error restoring configuration from backup: {e}")
        return False


def get_provider_config(provider_name: str) -> Dict[str, Any]:
    """
    Get configuration specific to a provider.
    
    Args:
        provider_name: Name of the AI provider
        
    Returns:
        Dict containing provider-specific configuration
    """
    config = get_config()
    
    provider_configs = {
        "openai": {
            "api_key": config.get("openai_api_key", ""),
            "provider": "openai"
        },
        "claude": {
            "api_key": config.get("claude_api_key", ""),
            "provider": "claude"
        },
        "deepseek": {
            "api_key": config.get("deepseek_api_key", ""),
            "provider": "deepseek"
        },
        "ollama": {
            "endpoint": config.get("ollama_endpoint", "http://localhost:11434"),
            "provider": "ollama"
        }
    }
    
    return provider_configs.get(provider_name, {})


def is_provider_configured(provider_name: str) -> bool:
    """
    Check if a specific provider is properly configured.
    
    Args:
        provider_name: Name of the AI provider
        
    Returns:
        bool: True if provider is configured, False otherwise
    """
    validation_results = validate_api_keys()
    return validation_results.get(provider_name, False)


def validate_and_save_config(new_config: Dict[str, Any]) -> ValidationResult:
    """
    Validate configuration and save if valid.
    
    Args:
        new_config: New configuration to validate and save
        
    Returns:
        ValidationResult: Validation results
    """
    try:
        # Validate configuration
        validation_result = validate_configuration(new_config)
        
        if validation_result.is_valid:
            # Save configuration if valid
            save_result = update_config(new_config)
            if not save_result.is_valid:
                return save_result
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating and saving configuration: {e}")
        result = ValidationResult()
        result.add_error("general", f"Failed to validate and save configuration: {str(e)}")
        return result


def get_configuration_status() -> Dict[str, Any]:
    """
    Get comprehensive configuration status including validation and connectivity.
    
    Returns:
        Dict containing configuration status information
    """
    try:
        config = get_config()
        
        # Basic configuration validation
        validation_result = validate_configuration(config)
        
        # API key validation (format only)
        api_validation = validate_api_keys(config, test_connectivity=False)
        
        # Check which providers are properly configured
        configured_providers = []
        for provider in ["openai", "claude", "deepseek", "ollama"]:
            if is_provider_configured(provider):
                configured_providers.append(provider)
        
        status = {
            "config_valid": validation_result.is_valid,
            "validation_errors": validation_result.errors,
            "validation_warnings": validation_result.warnings,
            "api_validation": api_validation,
            "configured_providers": configured_providers,
            "current_provider": config.get("provider", ""),
            "config_version": get_config_version(config),
            "migration_needed": needs_migration(config)
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting configuration status: {e}")
        return {
            "config_valid": False,
            "error": str(e),
            "configured_providers": [],
            "current_provider": "",
            "config_version": "unknown",
            "migration_needed": False
        }


def test_provider_connectivity(provider_name: str) -> Dict[str, Any]:
    """
    Test connectivity for a specific provider.
    
    Args:
        provider_name: Name of the provider to test
        
    Returns:
        Dict containing connectivity test results
    """
    try:
        config = get_config()
        
        if provider_name == "ollama":
            endpoint = config.get("ollama_endpoint", "")
            if not endpoint:
                return {"success": False, "message": "Ollama endpoint not configured"}
            
            success, message = test_ollama_connectivity(endpoint)
            return {"success": success, "message": message}
        
        else:
            api_key = config.get(f"{provider_name}_api_key", "")
            if not api_key:
                return {"success": False, "message": f"{provider_name.title()} API key not configured"}
            
            success, message = test_api_key_connectivity(provider_name, api_key)
            return {"success": success, "message": message}
    
    except Exception as e:
        logger.error(f"Error testing {provider_name} connectivity: {e}")
        return {"success": False, "message": f"Connectivity test failed: {str(e)}"}


def reset_configuration() -> bool:
    """
    Reset configuration to default values.
    
    Returns:
        bool: True if reset was successful
    """
    try:
        _ensure_config_directory()
        
        # Create backup of current configuration
        current_config = get_config()
        backup_path = create_migration_backup(current_config, get_config_version(current_config))
        if backup_path:
            logger.info(f"Configuration backup created before reset: {backup_path}")
        
        # Reset to default configuration with current version
        default_config = DEFAULT_CONFIG.copy()
        default_config["version"] = CURRENT_CONFIG_VERSION
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info("Configuration reset to defaults")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting configuration: {e}")
        return False


def export_configuration(include_sensitive: bool = False) -> Dict[str, Any]:
    """
    Export configuration for backup or sharing.
    
    Args:
        include_sensitive: Whether to include API keys in export
        
    Returns:
        Dict containing exportable configuration
    """
    try:
        config = get_config()
        export_config = config.copy()
        
        if not include_sensitive:
            # Remove sensitive information
            sensitive_fields = [
                "notion_api_key", "openai_api_key", "claude_api_key", 
                "deepseek_api_key"
            ]
            for field in sensitive_fields:
                if field in export_config:
                    export_config[field] = "***REDACTED***"
        
        return export_config
        
    except Exception as e:
        logger.error(f"Error exporting configuration: {e}")
        return {}


def import_configuration(imported_config: Dict[str, Any], merge: bool = True) -> ValidationResult:
    """
    Import configuration from external source.
    
    Args:
        imported_config: Configuration to import
        merge: Whether to merge with existing config or replace completely
        
    Returns:
        ValidationResult: Import validation results
    """
    try:
        if merge:
            current_config = get_config()
            # Merge imported config with current config
            merged_config = current_config.copy()
            merged_config.update(imported_config)
            return validate_and_save_config(merged_config)
        else:
            # Replace configuration completely
            return validate_and_save_config(imported_config)
        
    except Exception as e:
        logger.error(f"Error importing configuration: {e}")
        result = ValidationResult()
        result.add_error("general", f"Failed to import configuration: {str(e)}")
        return result


def recover_configuration() -> Dict[str, Any]:
    """
    Attempt to recover configuration using available recovery methods.
    
    Returns:
        Dict containing recovery results and status
    """
    try:
        from .errors import ConfigurationRecovery, ErrorCategory, ErrorSeverity
        
        recovery_result = {
            "success": False,
            "method_used": None,
            "message": "",
            "config_restored": False,
            "available_methods": []
        }
        
        # Check available recovery options
        recovery_options = ConfigurationRecovery.validate_recovery_options(CONFIG_DIR)
        recovery_result["available_methods"] = recovery_options["recovery_methods"]
        
        # Attempt automatic recovery
        auto_recovery_result = ConfigurationRecovery.attempt_auto_recovery(CONFIG_FILE)
        
        if auto_recovery_result["success"]:
            recovery_result["success"] = True
            recovery_result["method_used"] = auto_recovery_result["method_used"]
            recovery_result["config_restored"] = True
            
            if auto_recovery_result["backup_restored"]:
                recovery_result["message"] = "Configuration successfully restored from backup"
            elif auto_recovery_result["default_created"]:
                recovery_result["message"] = "Default configuration created successfully"
        else:
            recovery_result["message"] = auto_recovery_result.get("error", "Recovery failed")
        
        return recovery_result
        
    except Exception as e:
        logger.error(f"Configuration recovery failed: {e}")
        return {
            "success": False,
            "method_used": None,
            "message": f"Recovery process failed: {str(e)}",
            "config_restored": False,
            "available_methods": []
        }


def validate_and_fix_configuration(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate configuration and attempt automatic fixes where possible.
    
    Args:
        config: Configuration to validate (uses current config if None)
        
    Returns:
        Dict containing validation and fix results
    """
    try:
        from .validation import validate_configuration_with_recovery, auto_fix_configuration
        
        if config is None:
            config = get_config()
        
        # Validate configuration with recovery suggestions
        validation_result = validate_configuration_with_recovery(config)
        
        result = {
            "original_valid": validation_result["is_valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "recovery_suggestions": validation_result["recovery_suggestions"],
            "auto_fix_attempted": False,
            "auto_fix_successful": False,
            "fixes_applied": [],
            "final_config": config,
            "final_valid": validation_result["is_valid"]
        }
        
        # Attempt auto-fix if errors exist and auto-fix is available
        if not validation_result["is_valid"] and validation_result["auto_fix_available"]:
            fix_result = auto_fix_configuration(config)
            result["auto_fix_attempted"] = True
            result["auto_fix_successful"] = fix_result["success"]
            result["fixes_applied"] = fix_result["fixes_applied"]
            result["final_config"] = fix_result["updated_config"]
            
            # Re-validate after fixes
            if fix_result["success"]:
                final_validation = validate_configuration_with_recovery(fix_result["updated_config"])
                result["final_valid"] = final_validation["is_valid"]
                result["errors"] = final_validation["errors"]
        
        return result
        
    except Exception as e:
        logger.error(f"Configuration validation and fix failed: {e}")
        return {
            "original_valid": False,
            "errors": [{"field": "general", "message": f"Validation failed: {str(e)}", "error_code": "VALIDATION_ERROR"}],
            "warnings": [],
            "recovery_suggestions": ["Check configuration file manually", "Reset to default configuration"],
            "auto_fix_attempted": False,
            "auto_fix_successful": False,
            "fixes_applied": [],
            "final_config": config or {},
            "final_valid": False
        }


def get_configuration_health_report() -> Dict[str, Any]:
    """
    Generate a comprehensive health report for the configuration system.
    
    Returns:
        Dict containing health report
    """
    try:
        from .validation import get_validation_report
        from .errors import ConfigurationRecovery
        from .migration import get_migration_history, cleanup_old_backups
        
        config = get_config()
        
        # Basic health metrics
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "config_status": {},
            "validation_report": {},
            "recovery_status": {},
            "migration_status": {},
            "recommendations": []
        }
        
        # Configuration status
        health_report["config_status"] = {
            "file_exists": CONFIG_FILE.exists(),
            "file_readable": CONFIG_FILE.exists() and CONFIG_FILE.is_file(),
            "config_version": config.get("version", "unknown"),
            "provider_configured": bool(config.get("provider")),
            "has_api_keys": any(key.endswith("_api_key") and config.get(key) for key in config.keys())
        }
        
        # Validation report
        health_report["validation_report"] = get_validation_report(config)
        
        # Recovery status
        recovery_options = ConfigurationRecovery.validate_recovery_options(CONFIG_DIR)
        health_report["recovery_status"] = {
            "backup_available": recovery_options["backup_available"],
            "migration_backups_available": recovery_options["migration_backups_count"] > 0,
            "recovery_methods_count": len(recovery_options["recovery_methods"]),
            "config_dir_writable": recovery_options["config_dir_writable"]
        }
        
        # Migration status
        migration_history = get_migration_history()
        health_report["migration_status"] = {
            "migration_history_count": len(migration_history),
            "last_migration": migration_history[-1] if migration_history else None,
            "current_version": CURRENT_CONFIG_VERSION,
            "needs_migration": needs_migration(config)
        }
        
        # Determine overall health
        issues = []
        if not health_report["validation_report"]["validation_summary"]["is_valid"]:
            issues.append("Configuration validation failed")
        
        if not health_report["config_status"]["has_api_keys"]:
            issues.append("No API keys configured")
        
        if health_report["migration_status"]["needs_migration"]:
            issues.append("Configuration needs migration")
        
        if not health_report["recovery_status"]["config_dir_writable"]:
            issues.append("Configuration directory not writable")
        
        if len(issues) == 0:
            health_report["overall_health"] = "healthy"
        elif len(issues) <= 2:
            health_report["overall_health"] = "warning"
        else:
            health_report["overall_health"] = "critical"
        
        # Generate recommendations
        health_report["recommendations"] = issues
        if not health_report["recovery_status"]["backup_available"]:
            health_report["recommendations"].append("Create configuration backup")
        
        # Cleanup old backups
        cleanup_result = cleanup_old_backups()
        if cleanup_result["success"] and cleanup_result["deleted_files"]:
            health_report["recommendations"].append(f"Cleaned up {len(cleanup_result['deleted_files'])} old backup files")
        
        return health_report
        
    except Exception as e:
        logger.error(f"Health report generation failed: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "critical",
            "error": str(e),
            "recommendations": ["Check system logs", "Verify file permissions", "Reset configuration"]
        }