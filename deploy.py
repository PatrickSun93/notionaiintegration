#!/usr/bin/env python3
"""
Deployment script for Notion AI Integration System.

This script handles deployment tasks including environment setup,
configuration validation, and service management.
"""

import os
import sys
import subprocess
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """Manages deployment tasks for the Notion AI Integration System."""
    
    def __init__(self, environment: str = 'production'):
        self.environment = environment
        self.project_root = Path(__file__).parent
        self.config_dir = self.project_root / 'config'
        
    def validate_environment(self) -> Dict[str, Any]:
        """Validate deployment environment and requirements."""
        logger.info(f"Validating {self.environment} environment...")
        
        validation_result = {
            'environment': self.environment,
            'python_version': sys.version,
            'requirements_met': True,
            'issues': [],
            'warnings': []
        }
        
        # Check Python version
        if sys.version_info < (3, 8):
            validation_result['issues'].append("Python 3.8 or higher required")
            validation_result['requirements_met'] = False
        
        # Check required files
        required_files = [
            'app.py',
            'requirements.txt',
            'config/ai_config.py',
            'config/production.py' if self.environment == 'production' else 'config/development.py'
        ]
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                validation_result['issues'].append(f"Missing required file: {file_path}")
                validation_result['requirements_met'] = False
        
        # Check environment variables
        if self.environment == 'production':
            from config.production import validate_production_environment
            try:
                env_validation = validate_production_environment()
                validation_result['environment_validation'] = env_validation
            except EnvironmentError as e:
                validation_result['issues'].append(str(e))
                validation_result['requirements_met'] = False
        else:
            from config.development import validate_development_environment
            env_validation = validate_development_environment()
            validation_result['environment_validation'] = env_validation
            if not env_validation['validation_passed']:
                validation_result['warnings'].extend(env_validation['issues'])
        
        # Check dependencies
        try:
            import flask, openai, anthropic, requests
            validation_result['dependencies_installed'] = True
        except ImportError as e:
            validation_result['issues'].append(f"Missing dependencies: {e}")
            validation_result['requirements_met'] = False
        
        return validation_result
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        logger.info("Installing dependencies...")
        
        try:
            # Upgrade pip first
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True, capture_output=True)
            
            # Install requirements
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                         check=True, capture_output=True)
            
            logger.info("Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install dependencies: {e}")
            return False
    
    def setup_directories(self) -> bool:
        """Create required directories for the application."""
        logger.info("Setting up directories...")
        
        directories = [
            'logs',
            'config/backups',
            'static/uploads' if self.environment == 'production' else None,
            '/var/log/notion-ai' if self.environment == 'production' and os.geteuid() == 0 else None
        ]
        
        # Filter out None values
        directories = [d for d in directories if d is not None]
        
        try:
            for directory in directories:
                dir_path = Path(directory)
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            
            return True
            
        except PermissionError as e:
            logger.error(f"Permission denied creating directories: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            return False
    
    def setup_logging(self) -> bool:
        """Setup logging configuration for the environment."""
        logger.info("Setting up logging configuration...")
        
        try:
            if self.environment == 'production':
                from config.production import PRODUCTION_LOGGING_CONFIG
                logging_config = PRODUCTION_LOGGING_CONFIG
            else:
                from config.development import DEVELOPMENT_LOGGING_CONFIG
                logging_config = DEVELOPMENT_LOGGING_CONFIG
            
            # Create log directories
            for handler_name, handler_config in logging_config['handlers'].items():
                if 'filename' in handler_config:
                    log_file = Path(handler_config['filename'])
                    log_file.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info("Logging configuration setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup logging: {e}")
            return False
    
    def create_systemd_service(self) -> bool:
        """Create systemd service file for production deployment."""
        if self.environment != 'production':
            logger.info("Skipping systemd service creation (not production)")
            return True
        
        logger.info("Creating systemd service file...")
        
        service_content = f"""[Unit]
Description=Notion AI Integration System
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory={self.project_root}
Environment=PATH={self.project_root}/venv/bin
Environment=FLASK_ENV=production
ExecStart={self.project_root}/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        try:
            service_file = Path('/etc/systemd/system/notion-ai.service')
            if os.geteuid() == 0:  # Running as root
                with open(service_file, 'w') as f:
                    f.write(service_content)
                
                # Reload systemd and enable service
                subprocess.run(['systemctl', 'daemon-reload'], check=True)
                subprocess.run(['systemctl', 'enable', 'notion-ai'], check=True)
                
                logger.info("Systemd service created and enabled")
                return True
            else:
                logger.warning("Not running as root, cannot create systemd service")
                logger.info("Service file content:")
                logger.info(service_content)
                return False
                
        except Exception as e:
            logger.error(f"Failed to create systemd service: {e}")
            return False
    
    def create_nginx_config(self) -> bool:
        """Create nginx configuration for production deployment."""
        if self.environment != 'production':
            logger.info("Skipping nginx configuration (not production)")
            return True
        
        logger.info("Creating nginx configuration...")
        
        nginx_config = """server {
    listen 80;
    server_name your-domain.com;  # Change this to your domain
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # Change this to your domain
    
    # SSL configuration (update paths to your certificates)
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Static files
    location /static {
        alias """ + str(self.project_root / 'static') + """;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
        
        try:
            config_file = Path('/etc/nginx/sites-available/notion-ai')
            if os.geteuid() == 0:  # Running as root
                with open(config_file, 'w') as f:
                    f.write(nginx_config)
                
                # Create symlink to sites-enabled
                enabled_link = Path('/etc/nginx/sites-enabled/notion-ai')
                if not enabled_link.exists():
                    enabled_link.symlink_to(config_file)
                
                logger.info("Nginx configuration created")
                logger.warning("Remember to:")
                logger.warning("1. Update server_name with your domain")
                logger.warning("2. Update SSL certificate paths")
                logger.warning("3. Test nginx configuration: nginx -t")
                logger.warning("4. Reload nginx: systemctl reload nginx")
                return True
            else:
                logger.warning("Not running as root, cannot create nginx config")
                logger.info("Nginx configuration content:")
                logger.info(nginx_config)
                return False
                
        except Exception as e:
            logger.error(f"Failed to create nginx configuration: {e}")
            return False
    
    def run_health_check(self) -> bool:
        """Run application health check."""
        logger.info("Running health check...")
        
        try:
            # Import and run basic configuration validation
            sys.path.insert(0, str(self.project_root))
            
            from config.ai_config import get_configuration_status
            config_status = get_configuration_status()
            
            if config_status.get('config_valid', False):
                logger.info("Health check passed")
                return True
            else:
                logger.error("Health check failed: Configuration invalid")
                logger.error(f"Issues: {config_status.get('validation_errors', {})}")
                return False
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def deploy(self) -> bool:
        """Run complete deployment process."""
        logger.info(f"Starting {self.environment} deployment...")
        
        steps = [
            ("Validating environment", self.validate_environment),
            ("Installing dependencies", self.install_dependencies),
            ("Setting up directories", self.setup_directories),
            ("Setting up logging", self.setup_logging),
            ("Creating systemd service", self.create_systemd_service),
            ("Creating nginx config", self.create_nginx_config),
            ("Running health check", self.run_health_check)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            try:
                if callable(step_func):
                    result = step_func()
                else:
                    result = step_func
                
                if isinstance(result, dict):
                    # Handle validation result
                    if not result.get('requirements_met', True):
                        logger.error(f"Step failed: {step_name}")
                        logger.error(f"Issues: {result.get('issues', [])}")
                        return False
                    elif result.get('warnings'):
                        logger.warning(f"Warnings in {step_name}: {result.get('warnings', [])}")
                elif not result:
                    logger.error(f"Step failed: {step_name}")
                    return False
                
                logger.info(f"Step completed: {step_name}")
                
            except Exception as e:
                logger.error(f"Step failed with exception: {step_name} - {e}")
                return False
        
        logger.info(f"{self.environment.title()} deployment completed successfully!")
        
        if self.environment == 'production':
            logger.info("Next steps:")
            logger.info("1. Update nginx configuration with your domain and SSL certificates")
            logger.info("2. Start the service: systemctl start notion-ai")
            logger.info("3. Check service status: systemctl status notion-ai")
            logger.info("4. Monitor logs: journalctl -u notion-ai -f")
        
        return True


def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(description='Deploy Notion AI Integration System')
    parser.add_argument(
        '--environment', '-e',
        choices=['development', 'production'],
        default='production',
        help='Deployment environment'
    )
    parser.add_argument(
        '--validate-only', '-v',
        action='store_true',
        help='Only validate environment, do not deploy'
    )
    parser.add_argument(
        '--health-check', '-c',
        action='store_true',
        help='Run health check only'
    )
    
    args = parser.parse_args()
    
    deployment_manager = DeploymentManager(args.environment)
    
    if args.health_check:
        success = deployment_manager.run_health_check()
        sys.exit(0 if success else 1)
    
    if args.validate_only:
        validation_result = deployment_manager.validate_environment()
        print(json.dumps(validation_result, indent=2))
        sys.exit(0 if validation_result['requirements_met'] else 1)
    
    success = deployment_manager.deploy()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()