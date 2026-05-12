"""
utils/config_loader.py
======================
Tải cấu hình từ YAML và thay thế các biến môi trường.

Ví dụ thực thi mẫu:
------------------
from app.paths import ai_config_yaml
from app.ai.utils.config_loader import load_config_with_env
config = load_config_with_env(str(ai_config_yaml()))
print(config)
"""
import os
import re
import yaml
from dotenv import load_dotenv

def load_config_with_env(path: str) -> dict:
    """Loads a YAML config file and replaces ${VAR} or $VAR with environment variables."""
    # Ensure .env is loaded from root
    load_dotenv()
    
    with open(path, encoding="utf-8") as f:
        content = f.read()
        
    # Replace ${VAR} or $VAR with environment variables
    pattern = re.compile(r'\$\{(\w+)\}|\$(\w+)')
    def replace(match):
        var = match.group(1) or match.group(2)
        return os.getenv(var, match.group(0))
    
    content = pattern.sub(replace, content)
    return yaml.safe_load(content)
