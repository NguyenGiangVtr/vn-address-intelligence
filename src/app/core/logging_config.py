import logging
import sys
import os
from logstash_async.handler import AsynchronousLogstashHandler
from logstash_async.formatter import LogstashFormatter
from app.core.config import Config

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
    logging.getLogger('logstash_async').setLevel(logging.CRITICAL)
    import warnings
    from urllib3.exceptions import DependencyWarning
    warnings.filterwarnings("ignore", category=DependencyWarning)
    
    logger = logging.getLogger("VNAI")
    
    # Add Logstash handler if enabled
    if Config.KIBANA_LOG_ENABLED:
        # Quick check if Logstash is reachable to avoid noisy socket errors
        import socket
        is_reachable = False
        try:
            with socket.create_connection((Config.KIBANA_LOG_HOST, Config.KIBANA_LOG_PORT), timeout=1):
                is_reachable = True
        except:
            pass

        if not is_reachable:
            logger.warning(f"Kibana/Logstash server at {Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT} is unreachable. Kibana logging disabled for this session.")
        else:
            try:
                logstash_handler = AsynchronousLogstashHandler(
                    host=Config.KIBANA_LOG_HOST,
                    port=Config.KIBANA_LOG_PORT,
                    database_path=None,  # Use memory-based buffering
                )
                # Tạo Formatter riêng để định nghĩa metadata chuẩn JSON
                formatter = LogstashFormatter(
                    message_type='python-logstash',
                    extra_prefix='extra',
                    extra= {
                        "application": Config.KIBANA_LOG_APP_NAME,
                        "environment": os.getenv("ENVIRONMENT", "production")
                    }
                )
                logstash_handler.setFormatter(formatter)
                logging.getLogger().addHandler(logstash_handler)
                logger.info(f"Kibana logging integrated via Logstash at {Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}")
            except Exception as e:
                logger.error(f"Failed to initialize Logstash handler: {e}")
            
    return logger
