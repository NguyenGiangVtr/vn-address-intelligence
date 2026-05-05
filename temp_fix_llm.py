#!/usr/bin/env python3
"""
Temporary fix for LLM 503 error - modify server to use smaller/faster model
"""

import os
from pathlib import Path

def create_optimized_server_patch():
    """Create a patch for server.py with optimized LLM settings."""
    
    # Read current server.py
    server_path = Path("app/api/server.py")
    
    if not server_path.exists():
        print("server.py not found")
        return False
    
    print("Creating optimized LLM configuration...")
    
    # Find and replace LLM loading line
    with open(server_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Look for current LLM initialization
    old_llm_line = 'llm = LLMQwen3(model_name="Qwen/Qwen2.5-1.5B-Instruct", use_quantization=False, device="auto")'
    
    # Replace with optimized version
    new_llm_line = '''llm = LLMQwen3(
            model_name="Qwen/Qwen2.5-0.5B-Instruct",  # Smaller model
            use_quantization=True,  # Enable quantization for speed
            max_new_tokens=128,  # Reduce output length
            device="cpu"  # Force CPU to avoid CUDA issues
        )'''
    
    if old_llm_line in content:
        content = content.replace(old_llm_line, new_llm_line)
        print("✅ Updated LLM configuration")
    else:
        # Try alternative pattern
        alt_pattern = 'model_name="Qwen/Qwen2.5-1.5B-Instruct"'
        if alt_pattern in content:
            content = content.replace(alt_pattern, 'model_name="Qwen/Qwen2.5-0.5B-Instruct"')
            content = content.replace('use_quantization=False', 'use_quantization=True')
            print("✅ Updated LLM configuration (alternative)")
        else:
            print("⚠️ Could not find LLM configuration to update")
    
    # Also increase timeout
    timeout_pattern = '_LLM_TIMEOUT_SEC = 55'
    new_timeout = '_LLM_TIMEOUT_SEC = 120  # Increased for CPU mode'
    
    if timeout_pattern in content:
        content = content.replace(timeout_pattern, new_timeout)
        print("✅ Increased LLM timeout")
    
    # Write back
    try:
        with open(server_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Server.py updated successfully")
        return True
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return False

def create_quick_test():
    """Create a quick test script for the LLM fix."""
    
    test_script = '''#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path.cwd()))

try:
    from app.ai.models.llm_model import LLMQwen3
    print("Testing optimized LLM...")
    
    llm = LLMQwen3(
        model_name="Qwen/Qwen2.5-0.5B-Instruct",
        use_quantization=True,
        max_new_tokens=128,
        device="cpu"
    )
    
    if llm.model:
        print("✅ Optimized LLM loaded successfully!")
        
        # Quick test
        result = llm.normalize("123 Nguyen Van Cu", ["Nguyen Van Cu, District 5"])
        print(f"✅ Test result: {result}")
    else:
        print("❌ LLM model failed to load")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
'''
    
    with open("test_optimized_llm.py", "w", encoding="utf-8") as f:
        f.write(test_script)
    
    print("✅ Created test_optimized_llm.py")

def main():
    print("🔧 VN Address Intelligence - LLM Optimization Fix")
    print()
    
    print("This script will:")
    print("1. Update server.py to use smaller, faster LLM model")
    print("2. Enable quantization for better CPU performance") 
    print("3. Increase timeout for CPU mode")
    print("4. Create a test script")
    print()
    
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return
    
    # Apply fixes
    if create_optimized_server_patch():
        create_quick_test()
        
        print()
        print("🎯 Next steps:")
        print("1. Restart the server: Ctrl+C and run 'python -m app.api.server'")
        print("2. Test the fix: 'python test_optimized_llm.py'")
        print("3. Try the API again: POST /api/parser/analyze?model=llm")
        print()
        print("💡 The optimized configuration should:")
        print("   - Use smaller model (0.5B vs 1.5B parameters)")
        print("   - Enable quantization (2x faster)")
        print("   - Work better on CPU")
        print("   - Have longer timeout (120s vs 55s)")
        
    else:
        print("❌ Fix failed. Manual steps:")
        print("1. Edit app/api/server.py")
        print("2. Find: Qwen/Qwen2.5-1.5B-Instruct")
        print("3. Replace with: Qwen/Qwen2.5-0.5B-Instruct") 
        print("4. Change use_quantization=False to use_quantization=True")
        print("5. Restart server")

if __name__ == "__main__":
    main()