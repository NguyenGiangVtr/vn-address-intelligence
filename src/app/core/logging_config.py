import logging
import sys
import os
from app.core.config import Config

# Global APM client instance
apm_client = None

def setup_logging():
    """Setup logging với Elastic APM Python Client"""
    global apm_client
    
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
    
    # Add Elastic APM handler if enabled
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
                # Import Elastic APM
                from elasticapm import Client
                from elasticapm.handlers.logging import LoggingHandler
                import elasticapm
                
                # Khởi tạo APM Client
                apm_client = Client(
                    service_name=Config.KIBANA_LOG_APP_NAME,
                    server_url=f"http://{Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}",
                    environment=os.getenv("ENVIRONMENT", "production"),
                    compress_level=0,  # Tắt nén để tránh hụt dòng EOF khi đọc stream
                )
                
                # Đăng ký client vào hệ thống elasticapm toàn cục
                elasticapm.instrumentation.control.instrument()
                
                # Tự động gom toàn bộ log từ logging mặc định của Python đẩy vào APM
                apm_handler = LoggingHandler(client=apm_client)
                apm_handler.setLevel(logging.INFO)
                logging.getLogger().addHandler(apm_handler)
                
                logger.info(f"Elastic APM logging integrated at {Config.KIBANA_LOG_HOST}:{Config.KIBANA_LOG_PORT}")
            except ImportError:
                logger.error("elastic-apm package not installed. Install with: pip install elastic-apm")
            except Exception as e:
                logger.error(f"Failed to initialize Elastic APM handler: {e}")
            
    return logger
