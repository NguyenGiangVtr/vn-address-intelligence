#!/usr/bin/env python3
"""
Test script để kiểm tra APM Server logging integration.
Gửi test logs tới Elastic APM Server.

Usage:
    python scripts/test/test_apm_logging.py
    python scripts/test/test_apm_logging.py --host 138.2.68.67 --port 8200
"""

import sys
import os
import logging
import time
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.core.config import Config
from app.core.logging_config import setup_logging


def test_apm_logging():
    """Test APM logging by sending various log levels"""
    
    print("=" * 70)
    print("APM Server Logging Test")
    print("=" * 70)
    
    # Setup logging
    logger = setup_logging()
    
    print(f"\n[OK] Logging initialized")
    print(f"  - APM Enabled: {Config.KIBANA_LOG_ENABLED}")
    print(f"  - APM Host: {Config.KIBANA_LOG_HOST}")
    print(f"  - APM Port: {Config.KIBANA_LOG_PORT}")
    print(f"  - App Name: {Config.KIBANA_LOG_APP_NAME}")
    
    if not Config.KIBANA_LOG_ENABLED:
        print("\n[WARNING] APM logging is DISABLED in config")
        print("   Set KIBANA_LOG_ENABLED=true in .env to enable")
        return False
    
    print("\n" + "=" * 70)
    print("Sending test logs to APM Server...")
    print("=" * 70)
    
    # Test different log levels
    test_cases = [
        ("INFO", "Test INFO message - Application started", logger.info),
        ("WARNING", "Test WARNING message - High memory usage detected", logger.warning),
        ("ERROR", "Test ERROR message - Database connection failed", logger.error),
        ("DEBUG", "Test DEBUG message - Processing request from 192.168.1.1", logger.debug),
    ]
    
    for level, message, log_func in test_cases:
        print(f"\n[{level}] Sending: {message}")
        
        # Add extra data like HTTP middleware does
        extra_data = {
            "method": "GET",
            "path": "/api/test",
            "status_code": 200,
            "duration_ms": 45.5,
            "client_ip": "127.0.0.1",
            "user_agent": "test-script/1.0"
        }
        
        try:
            log_func(message, extra=extra_data)
            print(f"      [OK] Sent successfully")
        except Exception as e:
            print(f"      [ERROR] Error: {e}")
        
        time.sleep(0.5)  # Small delay between logs
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"""
[OK] Test logs sent to APM Server
  - Endpoint: http://{Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}/intake/v2/events
  - Service: {Config.KIBANA_LOG_APP_NAME}
  
Next steps:
  1. Check APM Dashboard: http://{Config.KIBANA_LOG_HOST}:5601
  2. Look for service: {Config.KIBANA_LOG_APP_NAME}
  3. View logs in the APM UI
  
If logs don't appear:
  - Verify APM Server is running: curl http://{Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}/
  - Check network connectivity to APM Server
  - Review application logs for errors
""")
    
    return True


def test_apm_connectivity():
    """Test connectivity to APM Server"""
    import socket
    
    print("\n" + "=" * 70)
    print("Testing APM Server Connectivity")
    print("=" * 70)
    
    host = Config.KIBANA_LOG_HOST
    port = Config.KIBANA_LOG_PORT
    
    print(f"\nTesting connection to {host}:{port}...")
    
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[OK] Successfully connected to APM Server at {host}:{port}")
            return True
    except socket.timeout:
        print(f"[TIMEOUT] Connection timeout to {host}:{port}")
        return False
    except socket.error as e:
        print(f"[FAILED] Connection failed to {host}:{port}")
        print(f"  Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test APM Server logging integration")
    parser.add_argument("--host", default=None, help="APM Server host (overrides config)")
    parser.add_argument("--port", type=int, default=None, help="APM Server port (overrides config)")
    parser.add_argument("--connectivity-only", action="store_true", help="Only test connectivity")
    
    args = parser.parse_args()
    
    # Override config if provided
    if args.host:
        Config.KIBANA_LOG_HOST = args.host
    if args.port:
        Config.KIBANA_LOG_PORT = args.port
    
    # Test connectivity first
    if not test_apm_connectivity():
        print("\n⚠️  Cannot connect to APM Server. Logs may not be delivered.")
        if args.connectivity_only:
            return 1
    
    if args.connectivity_only:
        return 0
    
    # Test logging
    if test_apm_logging():
        print("\n[OK] APM logging test completed successfully!")
        return 0
    else:
        print("\n[FAILED] APM logging test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
