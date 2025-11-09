#!/bin/bash
# Production startup script for Notion AI Integration System

set -e

# Configuration
APP_DIR="/opt/notion-ai"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/notion-ai"
PID_FILE="/var/run/notion-ai.pid"
USER="notion-ai"
GROUP="notion-ai"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        error "Run as the application user: sudo -u $USER $0"
        exit 1
    fi
}

# Validate environment
validate_environment() {
    log "Validating production environment..."
    
    # Check if virtual environment exists
    if [[ ! -d "$VENV_DIR" ]]; then
        error "Virtual environment not found at $VENV_DIR"
        exit 1
    fi
    
    # Check if application files exist
    if [[ ! -f "$APP_DIR/app.py" ]]; then
        error "Application file not found at $APP_DIR/app.py"
        exit 1
    fi
    
    # Check if .env file exists
    if [[ ! -f "$APP_DIR/.env" ]]; then
        error "Environment file not found at $APP_DIR/.env"
        error "Copy .env.example to .env and configure your API keys"
        exit 1
    fi
    
    # Check log directory
    if [[ ! -d "$LOG_DIR" ]]; then
        warning "Log directory not found, creating $LOG_DIR"
        mkdir -p "$LOG_DIR"
    fi
    
    # Validate configuration using Python
    cd "$APP_DIR"
    if ! "$VENV_DIR/bin/python" deploy.py --validate-only --environment production > /dev/null 2>&1; then
        error "Configuration validation failed"
        "$VENV_DIR/bin/python" deploy.py --validate-only --environment production
        exit 1
    fi
    
    log "Environment validation passed"
}

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    log "Performing health check..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
            log "Health check passed"
            return 0
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            error "Health check failed after $max_attempts attempts"
            return 1
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying in 2 seconds..."
        sleep 2
        ((attempt++))
    done
}

# Start application
start_app() {
    log "Starting Notion AI Integration System..."
    
    cd "$APP_DIR"
    
    # Load environment variables
    source .env 2>/dev/null || true
    
    # Set production environment
    export FLASK_ENV=production
    export PYTHONPATH="$APP_DIR:$PYTHONPATH"
    
    # Start gunicorn with production settings
    exec "$VENV_DIR/bin/gunicorn" \
        --bind 0.0.0.0:5000 \
        --workers 4 \
        --worker-class sync \
        --worker-connections 1000 \
        --timeout 120 \
        --keepalive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --preload \
        --pid "$PID_FILE" \
        --access-logfile "$LOG_DIR/access.log" \
        --error-logfile "$LOG_DIR/error.log" \
        --log-level info \
        --capture-output \
        app:app
}

# Stop application
stop_app() {
    log "Stopping Notion AI Integration System..."
    
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
                sleep 1
                ((count++))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                warning "Graceful shutdown failed, force killing process"
                kill -KILL "$pid"
            fi
            
            rm -f "$PID_FILE"
            log "Application stopped"
        else
            warning "PID file exists but process not running"
            rm -f "$PID_FILE"
        fi
    else
        warning "PID file not found, attempting to find and stop process"
        pkill -f "gunicorn.*app:app" || true
    fi
}

# Restart application
restart_app() {
    stop_app
    sleep 2
    start_app
}

# Show status
show_status() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Application is running (PID: $pid)"
            
            # Show process info
            ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem
            
            # Test health endpoint
            if curl -f -s http://localhost:5000/health > /dev/null 2>&1; then
                log "Health check: PASSED"
            else
                warning "Health check: FAILED"
            fi
        else
            error "PID file exists but process not running"
            return 1
        fi
    else
        error "Application is not running"
        return 1
    fi
}

# Show logs
show_logs() {
    local lines=${1:-50}
    
    if [[ -f "$LOG_DIR/error.log" ]]; then
        log "Showing last $lines lines of error log:"
        tail -n "$lines" "$LOG_DIR/error.log"
    fi
    
    if [[ -f "$LOG_DIR/access.log" ]]; then
        log "Showing last $lines lines of access log:"
        tail -n "$lines" "$LOG_DIR/access.log"
    fi
}

# Main function
main() {
    case "${1:-start}" in
        start)
            check_root
            validate_environment
            start_app
            ;;
        stop)
            stop_app
            ;;
        restart)
            check_root
            validate_environment
            restart_app
            ;;
        status)
            show_status
            ;;
        health)
            health_check
            ;;
        logs)
            show_logs "${2:-50}"
            ;;
        validate)
            validate_environment
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|health|logs|validate}"
            echo ""
            echo "Commands:"
            echo "  start     - Start the application"
            echo "  stop      - Stop the application"
            echo "  restart   - Restart the application"
            echo "  status    - Show application status"
            echo "  health    - Perform health check"
            echo "  logs      - Show application logs (optional: number of lines)"
            echo "  validate  - Validate environment configuration"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"