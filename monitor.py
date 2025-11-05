#!/usr/bin/env python3
"""
Monitoring script for Notion AI Integration System.

This script provides monitoring capabilities including health checks,
performance metrics, and alerting for the production system.
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """System monitoring and health check utilities."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.timeout = 30
        
    def check_application_health(self) -> Dict[str, Any]:
        """Check application health via HTTP endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                return {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "details": health_data
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "response_time": response.elapsed.total_seconds()
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "status": "unreachable",
                "error": "Connection refused"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "timeout",
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information from API."""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json()
                }
            else:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "data": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process information
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if 'gunicorn' in proc.info['name'] or 'python' in proc.info['name']:
                        processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "processes": processes
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}
    
    def check_log_files(self, log_dir: str = "/var/log/notion-ai") -> Dict[str, Any]:
        """Check log files for errors and warnings."""
        log_path = Path(log_dir)
        
        if not log_path.exists():
            return {"error": f"Log directory not found: {log_dir}"}
        
        log_analysis = {
            "timestamp": datetime.now().isoformat(),
            "log_files": {},
            "recent_errors": [],
            "recent_warnings": []
        }
        
        # Analyze log files
        for log_file in log_path.glob("*.log"):
            try:
                file_stats = log_file.stat()
                
                log_analysis["log_files"][log_file.name] = {
                    "size": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "readable": os.access(log_file, os.R_OK)
                }
                
                # Read recent entries for errors/warnings
                if log_file.name in ["error.log", "app.log"] and os.access(log_file, os.R_OK):
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()[-100:]  # Last 100 lines
                            
                        for line in lines:
                            line = line.strip()
                            if 'ERROR' in line.upper():
                                log_analysis["recent_errors"].append({
                                    "file": log_file.name,
                                    "line": line,
                                    "timestamp": datetime.now().isoformat()
                                })
                            elif 'WARNING' in line.upper():
                                log_analysis["recent_warnings"].append({
                                    "file": log_file.name,
                                    "line": line,
                                    "timestamp": datetime.now().isoformat()
                                })
                                
                    except Exception as e:
                        log_analysis["log_files"][log_file.name]["read_error"] = str(e)
                        
            except Exception as e:
                log_analysis["log_files"][log_file.name] = {"error": str(e)}
        
        return log_analysis
    
    def run_integration_test(self) -> Dict[str, Any]:
        """Run integration test via API."""
        try:
            response = self.session.post(
                f"{self.base_url}/api/integration/test",
                json={"test_type": "basic"},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 207]:
                return {
                    "status": "success",
                    "results": response.json()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

class AlertManager:
    """Manages alerts and notifications for monitoring."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.alert_history = []
        
    def check_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against configured thresholds."""
        alerts = []
        
        # CPU threshold
        cpu_threshold = self.config.get('cpu_threshold', 80)
        if metrics.get('cpu', {}).get('percent', 0) > cpu_threshold:
            alerts.append({
                "type": "cpu_high",
                "severity": "warning",
                "message": f"CPU usage is {metrics['cpu']['percent']:.1f}% (threshold: {cpu_threshold}%)",
                "timestamp": datetime.now().isoformat()
            })
        
        # Memory threshold
        memory_threshold = self.config.get('memory_threshold', 85)
        if metrics.get('memory', {}).get('percent', 0) > memory_threshold:
            alerts.append({
                "type": "memory_high",
                "severity": "warning",
                "message": f"Memory usage is {metrics['memory']['percent']:.1f}% (threshold: {memory_threshold}%)",
                "timestamp": datetime.now().isoformat()
            })
        
        # Disk threshold
        disk_threshold = self.config.get('disk_threshold', 90)
        if metrics.get('disk', {}).get('percent', 0) > disk_threshold:
            alerts.append({
                "type": "disk_high",
                "severity": "critical",
                "message": f"Disk usage is {metrics['disk']['percent']:.1f}% (threshold: {disk_threshold}%)",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert notification (placeholder for actual implementation)."""
        # This is a placeholder - implement actual alerting (email, Slack, etc.)
        logger.warning(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")
        
        # Add to history
        self.alert_history.append(alert)
        
        # Keep only recent alerts
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.alert_history = [
            a for a in self.alert_history 
            if datetime.fromisoformat(a['timestamp']) > cutoff_time
        ]
        
        return True

def main():
    """Main monitoring script entry point."""
    parser = argparse.ArgumentParser(description='Monitor Notion AI Integration System')
    parser.add_argument(
        '--url', '-u',
        default='http://localhost:5000',
        help='Base URL of the application'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=60,
        help='Monitoring interval in seconds'
    )
    parser.add_argument(
        '--once', '-o',
        action='store_true',
        help='Run monitoring checks once and exit'
    )
    parser.add_argument(
        '--output', '-f',
        help='Output file for monitoring data (JSON format)'
    )
    parser.add_argument(
        '--log-dir',
        default='/var/log/notion-ai',
        help='Log directory to monitor'
    )
    
    args = parser.parse_args()
    
    # Initialize monitor and alert manager
    monitor = SystemMonitor(args.url)
    alert_config = {
        'cpu_threshold': 80,
        'memory_threshold': 85,
        'disk_threshold': 90
    }
    alert_manager = AlertManager(alert_config)
    
    def run_monitoring_cycle():
        """Run a single monitoring cycle."""
        monitoring_data = {
            "timestamp": datetime.now().isoformat(),
            "application_health": monitor.check_application_health(),
            "system_metrics": monitor.get_system_metrics(),
            "log_analysis": monitor.check_log_files(args.log_dir),
            "alerts": []
        }
        
        # Check for alerts
        if "error" not in monitoring_data["system_metrics"]:
            alerts = alert_manager.check_thresholds(monitoring_data["system_metrics"])
            monitoring_data["alerts"] = alerts
            
            # Send alerts
            for alert in alerts:
                alert_manager.send_alert(alert)
        
        # Get detailed health if basic health check passes
        if monitoring_data["application_health"]["status"] == "healthy":
            detailed_health = monitor.check_detailed_health()
            monitoring_data["detailed_health"] = detailed_health
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(monitoring_data, f, indent=2)
        else:
            # Print summary to console
            app_status = monitoring_data["application_health"]["status"]
            print(f"[{monitoring_data['timestamp']}] Application: {app_status.upper()}")
            
            if "system_metrics" in monitoring_data and "error" not in monitoring_data["system_metrics"]:
                metrics = monitoring_data["system_metrics"]
                print(f"  CPU: {metrics['cpu']['percent']:.1f}% | "
                      f"Memory: {metrics['memory']['percent']:.1f}% | "
                      f"Disk: {metrics['disk']['percent']:.1f}%")
            
            if monitoring_data["alerts"]:
                print(f"  Alerts: {len(monitoring_data['alerts'])} active")
                for alert in monitoring_data["alerts"]:
                    print(f"    - {alert['message']}")
        
        return monitoring_data
    
    # Run monitoring
    if args.once:
        run_monitoring_cycle()
    else:
        logger.info(f"Starting continuous monitoring (interval: {args.interval}s)")
        try:
            while True:
                run_monitoring_cycle()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()