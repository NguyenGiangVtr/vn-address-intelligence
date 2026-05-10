#!/usr/bin/env python3
import sys
from pathlib import Path
_ops_dir = Path(__file__).resolve().parent
if str(_ops_dir) not in sys.path:
    sys.path.insert(0, str(_ops_dir))
import _repo_bootstrap  # noqa: E402
_repo_bootstrap.ensure_repo_root()

"""
Quick fix script for parser 503 Service Unavailable error.
"""

import requests
import time
import sys
import json

API_BASE = "http://localhost:8081/api"

def check_parser_status():
    """Check current parser status."""
    try:
        response = requests.get(f"{API_BASE}/parser/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Status: {data['status']}")
            print(f"📋 Loaded models: {data['loadedModels']}")
            print(f"❌ Errors: {data.get('errors', {})}")
            print(f"📊 Corpus size: {data.get('corpusSize', 0)}")
            return data
        else:
            print(f"❌ API error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None

def reload_parser_models():
    """Trigger model reload."""
    try:
        print("🔄 Triggering model reload...")
        response = requests.post(f"{API_BASE}/parser/reload", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Reload triggered: {data['message']}")
            return True
        else:
            print(f"❌ Reload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Reload error: {e}")
        return False

def wait_for_ready(max_wait=120):
    """Wait for models to be ready."""
    print(f"⏳ Waiting for models to load (max {max_wait}s)...")
    
    for i in range(max_wait):
        status = check_parser_status()
        
        if status and status['status'] == 'ready':
            print("✅ Models are ready!")
            return True
        elif status and status['status'] == 'error':
            print("❌ Models failed to load:")
            for model, error in status.get('errors', {}).items():
                print(f"   {model}: {error}")
            return False
            
        if i % 10 == 0:
            print(f"   Still loading... ({i}s elapsed)")
            
        time.sleep(1)
    
    print("⏰ Timeout waiting for models")
    return False

def test_llm_endpoint():
    """Test LLM endpoint specifically."""
    try:
        print("🤖 Testing LLM endpoint...")
        
        test_data = {
            "address": "268 Lý Thường Kiệt, Phường 14, Quận 10"
        }
        
        response = requests.post(
            f"{API_BASE}/parser/analyze?model=llm",
            json=test_data,
            timeout=60  # Longer timeout for LLM
        )
        
        if response.status_code == 200:
            print("✅ LLM endpoint working!")
            result = response.json()
            print(f"📊 Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return True
        else:
            print(f"❌ LLM endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ LLM request timed out - model may be too slow on CPU")
        return False
    except Exception as e:
        print(f"❌ LLM test error: {e}")
        return False

def suggest_optimizations():
    """Suggest optimizations for better performance."""
    print("\n🔧 Performance Optimization Suggestions:")
    print("1. Enable quantization for faster inference:")
    print("   - Edit server.py: use_quantization=True")
    print("2. Use smaller model:")
    print("   - Change to Qwen/Qwen2.5-0.5B-Instruct")
    print("3. Increase timeouts:")
    print("   - Edit server.py: _LLM_TIMEOUT_SEC = 120")
    print("4. For production:")
    print("   - Use GPU if available")
    print("   - Consider using optimized corpus for faster retrieval")

def main():
    """Main fix function."""
    print("🚀 VN Address Intelligence - Parser 503 Fix Tool\n")
    
    # Step 1: Check current status
    status = check_parser_status()
    
    if not status:
        print("❌ Cannot connect to API server")
        print("💡 Make sure server is running: python -m app.api.server")
        sys.exit(1)
    
    # Step 2: If loading, wait for completion
    if status['status'] == 'loading':
        if not wait_for_ready():
            print("\n🔄 Models failed to load automatically. Trying manual reload...")
            reload_parser_models()
            wait_for_ready(60)
    
    # Step 3: If still not ready, try reload
    elif status['status'] in ['idle', 'error']:
        reload_parser_models()
        wait_for_ready(60)
    
    # Step 4: Final test
    status = check_parser_status()
    if status and status['status'] == 'ready':
        print("\n🧪 Testing LLM endpoint...")
        success = test_llm_endpoint()
        
        if success:
            print("\n🎉 Parser is now working correctly!")
        else:
            print("\n⚠️ Models loaded but LLM endpoint still has issues")
            suggest_optimizations()
    else:
        print("\n❌ Models still not ready")
        suggest_optimizations()

if __name__ == "__main__":
    main()