"""
Configuration migration system for Notion AI Integration System.

This module handles configuration file migrations when the system is updated,
ensuring backward compatibility and smooth upgrades.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Migration history and version tracking
MIGRATION_HISTORY_FILE = Path("config/migration_history.json")
CURRENT_VERSION = "1.0"

# Migration definitions
MIGRATIONS = {
    "0.1": {
        "version": "0.1",
        "description": "Initial configuration format",
        "migration_function": None  # No migration needed for initial version
    },
    "1.0": {
        "version": "1.0", 
        "description": "Added provider validation and environment variable support",
        "migration_function": "migrate_to_1_0"
    }
}


class MigrationError(Exception):
    """Custom exception for migration-related errors."""
    pass


def get_config_version(config: Dict[str, Any]) -> str:
    """
    Get the version of a configuration dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        str: Configuration version (defaults to "0.1" if not specified)
    """
    return config.get("version", "0.1")


def needs_migration(config: Dict[str, Any]) -> bool:
    """
    Check if configuration needs migration to current version.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: True if migration is needed
    """
    current_version = get_config_version(config)
    return current_version != CURRENT_VERSION


def migrate_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate configuration to the current version.
    
    Args:
        config: Configuration dictionary to migrate
        
    Returns:
        Dict: Migrated configuration
        
    Raises:
        MigrationError: If migration fails
    """
    try:
        current_version = get_config_version(config)
        
        if current_version == CURRENT_VERSION:
            logger.info("Configuration is already at current version")
            return config
        
        logger.info(f"Migrating configuration from version {current_version} to {CURRENT_VERSION}")
        
        # Create migration chain
        migration_chain = _build_migration_chain(current_version, CURRENT_VERSION)
        
        # Apply migrations in sequence
        migrated_config = config.copy()
        for migration_version in migration_chain:
            migrated_config = _apply_migration(migrated_config, migration_version)
        
        # Update version in migrated config
        migrated_config["version"] = CURRENT_VERSION
        
        # Record migration in history
        _record_migration(current_version, CURRENT_VERSION)
        
        logger.info(f"Configuration successfully migrated to version {CURRENT_VERSION}")
        return migrated_config
        
    except Exception as e:
        logger.error(f"Configuration migration failed: {e}")
        raise MigrationError(f"Failed to migrate configuration: {str(e)}")


def _build_migration_chain(from_version: str, to_version: str) -> List[str]:
    """
    Build a chain of migrations needed to go from one version to another.
    
    Args:
        from_version: Starting version
        to_version: Target version
        
    Returns:
        List of migration versions to apply in order
    """
    # Get all available versions in order
    available_versions = sorted(MIGRATIONS.keys(), key=_version_sort_key)
    
    # Find start and end indices
    try:
        start_idx = available_versions.index(from_version)
        end_idx = available_versions.index(to_version)
    except ValueError as e:
        raise MigrationError(f"Unknown version in migration chain: {e}")
    
    if start_idx >= end_idx:
        return []  # No migration needed or downgrade not supported
    
    # Return versions between start and end (exclusive of start, inclusive of end)
    return available_versions[start_idx + 1:end_idx + 1]


def _version_sort_key(version: str) -> tuple:
    """Convert version string to tuple for sorting."""
    try:
        return tuple(map(int, version.split('.')))
    except ValueError:
        # Fallback for non-numeric versions
        return (0, 0)


def _apply_migration(config: Dict[str, Any], target_version: str) -> Dict[str, Any]:
    """
    Apply a specific migration to configuration.
    
    Args:
        config: Configuration to migrate
        target_version: Version to migrate to
        
    Returns:
        Dict: Migrated configuration
    """
    migration_info = MIGRATIONS.get(target_version)
    if not migration_info:
        raise MigrationError(f"No migration defined for version {target_version}")
    
    migration_function_name = migration_info.get("migration_function")
    if not migration_function_name:
        # No migration function needed
        return config
    
    # Get migration function
    migration_function = globals().get(migration_function_name)
    if not migration_function:
        raise MigrationError(f"Migration function {migration_function_name} not found")
    
    logger.info(f"Applying migration to version {target_version}: {migration_info['description']}")
    return migration_function(config)


def migrate_to_1_0(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate configuration from 0.1 to 1.0.
    
    Changes in 1.0:
    - Added version field
    - Standardized provider field values
    - Added validation for required fields
    - Added support for environment variables
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict: Migrated configuration
    """
    migrated = config.copy()
    
    # Ensure all required fields exist with defaults
    defaults = {
        "provider": "openai",
        "notion_api_key": "",
        "openai_api_key": "",
        "claude_api_key": "",
        "deepseek_api_key": "",
        "ollama_endpoint": "http://localhost:11434",
        "blog_database_id": ""
    }
    
    for key, default_value in defaults.items():
        if key not in migrated:
            migrated[key] = default_value
            logger.debug(f"Added missing field '{key}' with default value")
    
    # Normalize provider field
    provider = migrated.get("provider", "").lower()
    valid_providers = ["openai", "claude", "deepseek", "ollama"]
    
    if provider not in valid_providers:
        logger.warning(f"Invalid provider '{provider}', defaulting to 'openai'")
        migrated["provider"] = "openai"
    
    # Migrate old field names if they exist
    field_migrations = {
        "openai_key": "openai_api_key",
        "claude_key": "claude_api_key",
        "deepseek_key": "deepseek_api_key",
        "notion_key": "notion_api_key"
    }
    
    for old_field, new_field in field_migrations.items():
        if old_field in migrated:
            if not migrated.get(new_field):  # Only migrate if new field is empty
                migrated[new_field] = migrated[old_field]
                logger.info(f"Migrated field '{old_field}' to '{new_field}'")
            del migrated[old_field]
    
    # Clean up any unknown fields from older versions
    known_fields = set(defaults.keys()) | {"version"}
    unknown_fields = set(migrated.keys()) - known_fields
    
    for field in unknown_fields:
        logger.warning(f"Removing unknown field '{field}' during migration")
        del migrated[field]
    
    return migrated


def _record_migration(from_version: str, to_version: str) -> None:
    """
    Record migration in history file.
    
    Args:
        from_version: Version migrated from
        to_version: Version migrated to
    """
    try:
        # Load existing history
        history = []
        if MIGRATION_HISTORY_FILE.exists():
            with open(MIGRATION_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        # Add new migration record
        migration_record = {
            "from_version": from_version,
            "to_version": to_version,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        history.append(migration_record)
        
        # Ensure config directory exists
        MIGRATION_HISTORY_FILE.parent.mkdir(exist_ok=True)
        
        # Save updated history
        with open(MIGRATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        
        logger.debug(f"Recorded migration from {from_version} to {to_version}")
        
    except Exception as e:
        logger.warning(f"Failed to record migration history: {e}")


def get_migration_history() -> List[Dict[str, Any]]:
    """
    Get the migration history.
    
    Returns:
        List of migration records
    """
    try:
        if MIGRATION_HISTORY_FILE.exists():
            with open(MIGRATION_HISTORY_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Failed to load migration history: {e}")
        return []


def validate_migration_path(from_version: str, to_version: str) -> bool:
    """
    Validate that a migration path exists between two versions.
    
    Args:
        from_version: Starting version
        to_version: Target version
        
    Returns:
        bool: True if migration path exists
    """
    try:
        migration_chain = _build_migration_chain(from_version, to_version)
        return True
    except MigrationError:
        return False


def get_available_migrations() -> Dict[str, Dict[str, Any]]:
    """
    Get information about all available migrations.
    
    Returns:
        Dict mapping version to migration info
    """
    return MIGRATIONS.copy()


def create_migration_backup(config: Dict[str, Any], version: str) -> Optional[str]:
    """
    Create a comprehensive backup of configuration before migration.
    
    Args:
        config: Configuration to backup
        version: Current version
        
    Returns:
        Optional[str]: Backup file path if successful, None otherwise
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"config_backup_v{version}_{timestamp}.json"
        backup_path = Path("config") / "backups" / backup_filename
        
        # Ensure backup directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create comprehensive backup with metadata
        backup_data = {
            "config": config,
            "metadata": {
                "original_version": version,
                "backup_timestamp": datetime.now().isoformat(),
                "backup_reason": "pre_migration",
                "config_size": len(json.dumps(config)),
                "field_count": len(config),
                "checksum": _calculate_config_checksum(config)
            }
        }
        
        # Create backup
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        # Also create a simple backup for compatibility
        simple_backup_path = backup_path.with_suffix('.simple.json')
        with open(simple_backup_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration backup created: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Failed to create migration backup: {e}")
        return None


def _calculate_config_checksum(config: Dict[str, Any]) -> str:
    """Calculate a simple checksum for configuration validation."""
    import hashlib
    config_str = json.dumps(config, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()


def validate_backup_integrity(backup_path: str) -> Dict[str, Any]:
    """
    Validate the integrity of a backup file.
    
    Args:
        backup_path: Path to backup file
        
    Returns:
        Dict containing validation results
    """
    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
        "metadata": None,
        "config": None
    }
    
    try:
        backup_file = Path(backup_path)
        if not backup_file.exists():
            result["errors"].append("Backup file does not exist")
            return result
        
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)
        
        # Check if it's a comprehensive backup or simple backup
        if isinstance(backup_data, dict) and "config" in backup_data and "metadata" in backup_data:
            # Comprehensive backup
            config = backup_data["config"]
            metadata = backup_data["metadata"]
            
            # Validate checksum if available
            if "checksum" in metadata:
                calculated_checksum = _calculate_config_checksum(config)
                if calculated_checksum != metadata["checksum"]:
                    result["warnings"].append("Backup checksum mismatch - data may be corrupted")
            
            result["metadata"] = metadata
            result["config"] = config
        else:
            # Simple backup (just configuration)
            result["config"] = backup_data
            result["warnings"].append("Simple backup format - no metadata available")
        
        # Validate configuration structure
        if result["config"]:
            from .validation import validate_configuration
            validation_result = validate_configuration(result["config"])
            if not validation_result.is_valid:
                result["warnings"].append("Backup contains invalid configuration")
                result["errors"].extend([error["message"] for error in validation_result.errors])
        
        result["valid"] = len(result["errors"]) == 0
        
    except json.JSONDecodeError as e:
        result["errors"].append(f"Invalid JSON in backup file: {e}")
    except Exception as e:
        result["errors"].append(f"Error validating backup: {e}")
    
    return result


def restore_from_backup(backup_path: str, target_config_path: str) -> Dict[str, Any]:
    """
    Restore configuration from backup with validation.
    
    Args:
        backup_path: Path to backup file
        target_config_path: Path where to restore configuration
        
    Returns:
        Dict containing restoration results
    """
    result = {
        "success": False,
        "errors": [],
        "warnings": [],
        "restored_version": None
    }
    
    try:
        # Validate backup first
        validation_result = validate_backup_integrity(backup_path)
        if not validation_result["valid"]:
            result["errors"].extend(validation_result["errors"])
            return result
        
        config = validation_result["config"]
        if not config:
            result["errors"].append("No valid configuration found in backup")
            return result
        
        # Create backup of current configuration before restoring
        target_path = Path(target_config_path)
        if target_path.exists():
            current_backup_path = create_migration_backup(
                json.load(open(target_path)),
                "pre_restore"
            )
            if current_backup_path:
                result["warnings"].append(f"Current configuration backed up to: {current_backup_path}")
        
        # Restore configuration
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        result["success"] = True
        result["restored_version"] = config.get("version", "unknown")
        
        logger.info(f"Configuration restored from backup: {backup_path}")
        
    except Exception as e:
        result["errors"].append(f"Restoration failed: {e}")
        logger.error(f"Failed to restore from backup {backup_path}: {e}")
    
    return result


def cleanup_old_backups(max_backups: int = 10) -> Dict[str, Any]:
    """
    Clean up old backup files, keeping only the most recent ones.
    
    Args:
        max_backups: Maximum number of backups to keep
        
    Returns:
        Dict containing cleanup results
    """
    result = {
        "success": False,
        "deleted_files": [],
        "kept_files": [],
        "errors": []
    }
    
    try:
        backup_dir = Path("config") / "backups"
        if not backup_dir.exists():
            result["success"] = True
            return result
        
        # Get all backup files
        backup_files = list(backup_dir.glob("config_backup_v*.json"))
        backup_files.extend(backup_dir.glob("settings_backup_*.json"))
        
        if len(backup_files) <= max_backups:
            result["kept_files"] = [str(f) for f in backup_files]
            result["success"] = True
            return result
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Keep the most recent backups
        files_to_keep = backup_files[:max_backups]
        files_to_delete = backup_files[max_backups:]
        
        # Delete old backups
        for backup_file in files_to_delete:
            try:
                backup_file.unlink()
                result["deleted_files"].append(str(backup_file))
            except Exception as e:
                result["errors"].append(f"Failed to delete {backup_file}: {e}")
        
        result["kept_files"] = [str(f) for f in files_to_keep]
        result["success"] = len(result["errors"]) == 0
        
        logger.info(f"Backup cleanup completed. Deleted {len(result['deleted_files'])} files, kept {len(result['kept_files'])} files")
        
    except Exception as e:
        result["errors"].append(f"Backup cleanup failed: {e}")
        logger.error(f"Backup cleanup failed: {e}")
    
    return result