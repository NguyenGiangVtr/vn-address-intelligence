import logging
import sys
import os
import json
from app.core.config import Config

class APMHandler(logging.Handler):
    """Custom handler để gửi logs tới Elastic APM Server qua HTTP"""
    def __init__(self, host, port, app_name):
        super().__init__()
        self.host = host
        self.port = port
        self.app_name = app_name
        self.url = f"http://{host}:{port}/intake/v2/events"
        
    def emit(self, record):
        try:
            import requests
            log_entry = self.format(record)
            
            # Tạo event theo định dạng Elastic APM
            event = {
                "metadata": {
                    "service": {
                        "name": self.app_name,
                        "environment": os.getenv("ENVIRONMENT", "production")
                    }
                },
                "log": {
                    "level": record.levelname,
                    "logger": record.name,
                    "message": log_entry,
                    "timestamp": int(record.created * 1000000),  # microseconds
                    "origin": {
                        "file": {
                            "name": record.filename,
                            "line": record.lineno
                        },
                        "function": record.funcName
                    }
                }
            }
            
            # Gửi tới APM Server
            requests.post(
                self.url,
                json=event,
                headers={"Content-Type": "application/x-ndjson"},
                timeout=2
            )
        except Exception as e:
            self.handleError(record)

def setup_logging():
    # Base logging format
    log_format = "%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s — %(message)s"
    date_format = "%H:%M:%S"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Silence internal warnings from noisy libraries
    import warnings
    from urllib3.exceptions import DependencyWarning
    warnings.filterwarnings("ignore", category=DependencyWarning)
    
    logger = logging.getLogger("VNAI")
    
    # Add APM handler if enabled
    if Config.KIBANA_LOG_ENABLED:
        # Quick check if APM Server is reachable
        import socket
        is_reachable = False
        try:
            with socket.create_connection((Config.KIBANA_LOG_HOST, Config.KIBANA_LOG_PORT), timeout=1):
                is_reachable = True
        except:
            pass

        if not is_reachable:
            logger.warning(f"APM Server at {Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT} is unreachable. APM logging disabled for this session.")
        else:
            try:
                apm_handler = APMHandler(
                    host=Config.KIBANA_LOG_HOST,
                    port=Config.KIBANA_LOG_PORT,
                    app_name=Config.KIBANA_LOG_APP_NAME
                )
                apm_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
                logging.getLogger().addHandler(apm_handler)
                logger.info(f"APM logging integrated via Elastic APM Server at {Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}")
            except Exception as e:
                logger.error(f"Failed to initialize APM handler: {e}")
            
    return logger
