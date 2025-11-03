"""
Error handling and recovery utilities for configuration management.

This module provides comprehensive error handling, recovery mechanisms,
and user-friendly error messages for configuration-related operations.
"""

import os
import logging
import traceback
from typing import Dict, Any, Optional, List
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    VALIDATION = "validation"
    CONNECTIVITY = "connectivity"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    MIGRATION = "migration"
    SYSTEM = "system"


class ConfigurationErrorHandler:
    """Centralized error handling for configuration operations."""
    
    def __init__(self):
        self.error_log: List[Dict[str, Any]] = []
    
    def handle_error(
        self,
        error: Exception,
        context: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Handle and log an error with context and recovery information.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            severity: Error severity level
            category: Error category
            user_message: User-friendly error message
            recovery_suggestions: List of recovery suggestions
            
        Returns:
            Dict containing error information
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "severity": severity.value,
            "category": category.value,
            "user_message": user_message or self._generate_user_message(error, category),
            "recovery_suggestions": recovery_suggestions or self._generate_recovery_suggestions(error, category),
            "traceback": traceback.format_exc() if logger.isEnabledFor(logging.DEBUG) else None
        }
        
        # Log error based on severity
        log_message = f"[{category.value.upper()}] {context}: {str(error)}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        # Store error for analysis
        self.error_log.append(error_info)
        
        return error_info
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """Generate user-friendly error message based on error type and category."""
        error_type = type(error).__name__
        
        user_messages = {
            ErrorCategory.VALIDATION: {
                "ValueError": "The configuration contains invalid values. Please check your settings.",
                "KeyError": "Required configuration field is missing. Please check your configuration.",
                "TypeError": "Configuration field has wrong data type. Please verify your settings.",
                "default": "Configuration validation failed. Please check your settings."
            },
            ErrorCategory.CONNECTIVITY: {
                "ConnectionError": "Unable to connect to the service. Please check your internet connection.",
                "TimeoutError": "Connection timed out. The service may be temporarily unavailable.",
                "RequestException": "Network request failed. Please check your connection and try again.",
                "default": "Connection failed. Please check your network settings and try again."
            },
            ErrorCategory.PERMISSION: {
                "PermissionError": "Permission denied. Please check file permissions or run with appropriate privileges.",
                "FileNotFoundError": "Configuration file not found. It may have been deleted or moved.",
                "default": "Permission or file access error. Please check file permissions."
            },
            ErrorCategory.CONFIGURATION: {
                "JSONDecodeError": "Configuration file is corrupted or contains invalid JSON. Please restore from backup.",
                "FileNotFoundError": "Configuration file not found. A new one will be created with default settings.",
                "default": "Configuration error occurred. Please check your configuration file."
            },
            ErrorCategory.MIGRATION: {
                "MigrationError": "Configuration migration failed. Please restore from backup or reset to defaults.",
                "default": "Configuration migration error. Please check migration logs."
            },
            ErrorCategory.SYSTEM: {
                "OSError": "System error occurred. Please check system resources and permissions.",
                "MemoryError": "Insufficient memory. Please close other applications and try again.",
                "default": "System error occurred. Please try again or contact support."
            }
        }
        
        category_messages = user_messages.get(category, user_messages[ErrorCategory.SYSTEM])
        return category_messages.get(error_type, category_messages["default"])
    
    def _generate_recovery_suggestions(self, error: Exception, category: ErrorCategory) -> List[str]:
        """Generate recovery suggestions based on error type and category."""
        error_type = type(error).__name__
        
        recovery_suggestions = {
            ErrorCategory.VALIDATION: [
                "Check configuration values for correct format",
                "Verify API keys are properly formatted",
                "Ensure all required fields are filled",
                "Reset configuration to defaults if needed"
            ],
            ErrorCategory.CONNECTIVITY: [
                "Check your internet connection",
                "Verify API endpoints are accessible",
                "Try again in a few minutes",
                "Check if services are experiencing downtime"
            ],
            ErrorCategory.PERMISSION: [
                "Check file and directory permissions",
                "Run the application with appropriate privileges",
                "Ensure configuration directory is writable",
                "Restore configuration file from backup"
            ],
            ErrorCategory.CONFIGURATION: [
                "Restore configuration from backup",
                "Reset configuration to defaults",
                "Manually edit configuration file",
                "Check configuration file syntax"
            ],
            ErrorCategory.MIGRATION: [
                "Restore configuration from backup",
                "Reset configuration to defaults",
                "Check migration logs for details",
                "Contact support if issue persists"
            ],
            ErrorCategory.SYSTEM: [
                "Restart the application",
                "Check system resources (disk space, memory)",
                "Check system logs for additional information",
                "Contact system administrator if needed"
            ]
        }
        
        return recovery_suggestions.get(category, recovery_suggestions[ErrorCategory.SYSTEM])
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered."""
        if not self.error_log:
            return {"total_errors": 0, "by_category": {}, "by_severity": {}}
        
        by_category = {}
        by_severity = {}
        
        for error in self.error_log:
            category = error["category"]
            severity = error["severity"]
            
            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": self.error_log[-5:]  # Last 5 errors
        }
    
    def clear_error_log(self) -> None:
        """Clear the error log."""
        self.error_log.clear()


# Global error handler instance
error_handler = ConfigurationErrorHandler()


def handle_configuration_error(
    error: Exception,
    context: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM
) -> Dict[str, Any]:
    """
    Convenience function to handle configuration errors.
    
    Args:
        error: The exception that occurred
        context: Context where the error occurred
        severity: Error severity level
        category: Error category
        
    Returns:
        Dict containing error information
    """
    return error_handler.handle_error(error, context, severity, category)


def get_user_friendly_error(error: Exception, context: str = "") -> str:
    """
    Get a user-friendly error message for an exception.
    
    Args:
        error: The exception
        context: Optional context
        
    Returns:
        User-friendly error message
    """
    error_info = error_handler.handle_error(error, context)
    return error_info["user_message"]


def suggest_recovery_actions(error: Exception, category: ErrorCategory) -> List[str]:
    """
    Get recovery suggestions for an error.
    
    Args:
        error: The exception
        category: Error category
        
    Returns:
        List of recovery suggestions
    """
    error_info = error_handler.handle_error(error, "recovery_suggestion", category=category)
    return error_info["recovery_suggestions"]


class ConfigurationRecovery:
    """Enhanced configuration recovery utilities with comprehensive backup management."""
    
    @staticmethod
    def attempt_auto_recovery(config_file: Path) -> Dict[str, Any]:
        """
        Attempt automatic recovery of configuration file with detailed results.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Dict containing recovery results and details
        """
        recovery_result = {
            "success": False,
            "method_used": None,
            "backup_restored": False,
            "default_created": False,
            "error": None,
            "recovery_steps": []
        }
        
        try:
            # Step 1: Try to restore from most recent backup
            backup_restored = ConfigurationRecovery._restore_from_latest_backup(config_file)
            recovery_result["recovery_steps"].append("Attempted backup restoration")
            
            if backup_restored:
                recovery_result["success"] = True
                recovery_result["method_used"] = "backup_restoration"
                recovery_result["backup_restored"] = True
                logger.info("Configuration successfully restored from backup")
                return recovery_result
            
            # Step 2: Try to restore from migration backup
            migration_backup_restored = ConfigurationRecovery._restore_from_migration_backup(config_file)
            recovery_result["recovery_steps"].append("Attempted migration backup restoration")
            
            if migration_backup_restored:
                recovery_result["success"] = True
                recovery_result["method_used"] = "migration_backup_restoration"
                recovery_result["backup_restored"] = True
                logger.info("Configuration successfully restored from migration backup")
                return recovery_result
            
            # Step 3: Create default configuration
            default_created = ConfigurationRecovery._create_default_config(config_file)
            recovery_result["recovery_steps"].append("Attempted default configuration creation")
            
            if default_created:
                recovery_result["success"] = True
                recovery_result["method_used"] = "default_creation"
                recovery_result["default_created"] = True
                logger.info("Default configuration successfully created")
                return recovery_result
            
            recovery_result["error"] = "All recovery methods failed"
            return recovery_result
            
        except Exception as e:
            logger.error(f"Auto-recovery failed: {e}")
            recovery_result["error"] = str(e)
            return recovery_result
    
    @staticmethod
    def _restore_from_latest_backup(config_file: Path) -> bool:
        """Restore from the most recent backup file."""
        try:
            backup_file = config_file.parent / "settings_backup.json"
            if backup_file.exists():
                # Validate backup before restoring
                with open(backup_file, 'r') as f:
                    import json
                    backup_config = json.load(f)
                
                # Basic validation
                if isinstance(backup_config, dict) and len(backup_config) > 0:
                    backup_file.replace(config_file)
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    @staticmethod
    def _restore_from_migration_backup(config_file: Path) -> bool:
        """Restore from migration backup files."""
        try:
            backup_dir = config_file.parent / "backups"
            if not backup_dir.exists():
                return False
            
            # Find the most recent migration backup
            backup_files = list(backup_dir.glob("config_backup_v*.json"))
            if not backup_files:
                return False
            
            # Sort by modification time (most recent first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files:
                try:
                    with open(backup_file, 'r') as f:
                        import json
                        backup_config = json.load(f)
                    
                    # Validate backup
                    if isinstance(backup_config, dict) and len(backup_config) > 0:
                        with open(config_file, 'w') as f:
                            json.dump(backup_config, f, indent=2)
                        return True
                except Exception as e:
                    logger.warning(f"Failed to restore from {backup_file}: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Failed to restore from migration backup: {e}")
            return False
    
    @staticmethod
    def _create_default_config(config_file: Path) -> bool:
        """Create default configuration file."""
        try:
            from .ai_config import DEFAULT_CONFIG, CURRENT_CONFIG_VERSION
            
            default_config = DEFAULT_CONFIG.copy()
            default_config["version"] = CURRENT_CONFIG_VERSION
            
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w') as f:
                import json
                json.dump(default_config, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Failed to create default config: {e}")
            return False
    
    @staticmethod
    def create_emergency_config() -> Dict[str, Any]:
        """
        Create emergency configuration with minimal settings.
        
        Returns:
            Dict containing emergency configuration
        """
        return {
            "version": "1.0",
            "provider": "openai",
            "notion_api_key": "",
            "openai_api_key": "",
            "claude_api_key": "",
            "deepseek_api_key": "",
            "ollama_endpoint": "http://localhost:11434",
            "blog_database_id": ""
        }
    
    @staticmethod
    def validate_recovery_options(config_dir: Path) -> Dict[str, Any]:
        """
        Check available recovery options with detailed information.
        
        Args:
            config_dir: Configuration directory path
            
        Returns:
            Dict containing recovery option details
        """
        backup_file = config_dir / "settings_backup.json"
        migration_history_file = config_dir / "migration_history.json"
        backup_dir = config_dir / "backups"
        
        # Check for migration backups
        migration_backups = []
        if backup_dir.exists():
            migration_backups = list(backup_dir.glob("config_backup_v*.json"))
            migration_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return {
            "backup_available": backup_file.exists(),
            "backup_file_size": backup_file.stat().st_size if backup_file.exists() else 0,
            "backup_modified": backup_file.stat().st_mtime if backup_file.exists() else None,
            "migration_history_available": migration_history_file.exists(),
            "migration_backups_count": len(migration_backups),
            "latest_migration_backup": str(migration_backups[0]) if migration_backups else None,
            "config_dir_exists": config_dir.exists(),
            "config_dir_writable": config_dir.exists() and os.access(config_dir, os.W_OK),
            "can_create_default": True,
            "recovery_methods": ConfigurationRecovery._get_available_recovery_methods(config_dir)
        }
    
    @staticmethod
    def _get_available_recovery_methods(config_dir: Path) -> List[Dict[str, Any]]:
        """Get list of available recovery methods with details."""
        methods = []
        
        # Backup restoration
        backup_file = config_dir / "settings_backup.json"
        if backup_file.exists():
            methods.append({
                "method": "backup_restoration",
                "description": "Restore from settings backup file",
                "available": True,
                "file_path": str(backup_file),
                "file_size": backup_file.stat().st_size,
                "last_modified": backup_file.stat().st_mtime
            })
        
        # Migration backup restoration
        backup_dir = config_dir / "backups"
        if backup_dir.exists():
            migration_backups = list(backup_dir.glob("config_backup_v*.json"))
            if migration_backups:
                latest_backup = max(migration_backups, key=lambda x: x.stat().st_mtime)
                methods.append({
                    "method": "migration_backup_restoration",
                    "description": "Restore from migration backup files",
                    "available": True,
                    "file_path": str(latest_backup),
                    "backup_count": len(migration_backups),
                    "last_modified": latest_backup.stat().st_mtime
                })
        
        # Default configuration creation
        methods.append({
            "method": "default_creation",
            "description": "Create new default configuration",
            "available": config_dir.exists() and os.access(config_dir, os.W_OK),
            "file_path": str(config_dir / "settings.json")
        })
        
        return methods
    
    @staticmethod
    def create_comprehensive_backup(config: Dict[str, Any], config_dir: Path) -> Dict[str, Any]:
        """
        Create comprehensive backup with metadata and validation.
        
        Args:
            config: Configuration to backup
            config_dir: Configuration directory
            
        Returns:
            Dict containing backup results
        """
        backup_result = {
            "success": False,
            "backup_files": [],
            "errors": [],
            "metadata": {}
        }
        
        try:
            import json
            from datetime import datetime
            
            timestamp = datetime.now()
            
            # Create main backup
            backup_file = config_dir / "settings_backup.json"
            try:
                with open(backup_file, 'w') as f:
                    json.dump(config, f, indent=2)
                backup_result["backup_files"].append(str(backup_file))
            except Exception as e:
                backup_result["errors"].append(f"Failed to create main backup: {e}")
            
            # Create timestamped backup
            timestamped_backup = config_dir / "backups" / f"settings_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            try:
                timestamped_backup.parent.mkdir(parents=True, exist_ok=True)
                with open(timestamped_backup, 'w') as f:
                    json.dump(config, f, indent=2)
                backup_result["backup_files"].append(str(timestamped_backup))
            except Exception as e:
                backup_result["errors"].append(f"Failed to create timestamped backup: {e}")
            
            # Create backup metadata
            metadata = {
                "backup_timestamp": timestamp.isoformat(),
                "config_version": config.get("version", "unknown"),
                "config_provider": config.get("provider", "unknown"),
                "backup_size": len(json.dumps(config)),
                "field_count": len(config),
                "has_api_keys": any(key.endswith("_api_key") and config.get(key) for key in config.keys())
            }
            
            metadata_file = config_dir / "backups" / f"backup_metadata_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                backup_result["backup_files"].append(str(metadata_file))
                backup_result["metadata"] = metadata
            except Exception as e:
                backup_result["errors"].append(f"Failed to create backup metadata: {e}")
            
            backup_result["success"] = len(backup_result["backup_files"]) > 0
            
        except Exception as e:
            backup_result["errors"].append(f"Backup operation failed: {e}")
        
        return backup_result