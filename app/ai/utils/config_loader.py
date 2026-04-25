import os
import re
import yaml

def load_config_with_env(path: str) -> dict:
    """Loads a YAML config file and replaces ${VAR} or $VAR with environment variables."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
        
    # Replace ${VAR} or $VAR with environment variables
    pattern = re.compile(r'\$\{(\w+)\}|\$(\w+)')
    def replace(match):
        var = match.group(1) or match.group(2)
        return os.getenv(var, match.group(0))
    
    content = pattern.sub(replace, content)
    return yaml.safe_load(content)
