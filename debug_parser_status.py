#!/usr/bin/env python3
"""
Debug script để kiểm tra parser status và LLM model loading issue.
"""

import sys
import os
import traceback
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_llm_model():
    """Test LLM model loading directly."""
    logger.info("🧠 Testing LLM model loading...")
    
    try:
        # Add current directory to Python path
        sys.path.append(str(Path.cwd()))
        
        from app.ai.models.llm_model import LLMQwen3
        
        # Test với model nhỏ trước
        logger.info("🔄 Loading Qwen2.5-1.5B-Instruct (small model)...")
        llm = LLMQwen3(
            model_name="Qwen/Qwen2.5-1.5B-Instruct", 
            use_quantization=False,
            device="auto"
        )
        
        if llm.model is not None:
            logger.info("✅ LLM model loaded successfully!")
            
            # Test inference
            test_query = "268 Lý Thường Kiệt, Phường 14, Quận 10"
            candidates = ["Lý Thường Kiệt, Phường 14, Quận 10", "268 Lê Lợi, Phường Bến Thành"]
            
            logger.info("🔄 Testing inference...")
            result = llm.normalize(test_query, candidates)
            logger.info(f"✅ Inference result: {result}")
            
            return True
        else:
            logger.error("❌ LLM model is None after loading")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're running from project root directory")
        return False
    except Exception as e:
        logger.error(f"❌ LLM loading error: {e}")
        logger.error(traceback.format_exc())
        return False

def test_dependencies():
    """Test required dependencies."""
    logger.info("📦 Testing dependencies...")
    
    dependencies = [
        ('torch', 'PyTorch'),
        ('transformers', 'Hugging Face Transformers'),
        ('sentence_transformers', 'Sentence Transformers'),
    ]
    
    all_good = True
    
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            logger.info(f"✅ {display_name} - Available")
        except ImportError as e:
            logger.error(f"❌ {display_name} - Missing: {e}")
            all_good = False
    
    # Check CUDA availability
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"✅ CUDA - Available (Device: {torch.cuda.get_device_name()})")
        else:
            logger.info("⚠️ CUDA - Not available, using CPU")
    except:
        logger.error("❌ Cannot check CUDA status")
        all_good = False
    
    return all_good

def test_api_status():
    """Test current API parser status."""
    logger.info("🌐 Testing API parser status...")
    
    try:
        import requests
        
        # Test local API
        response = requests.get("http://localhost:8081/api/parser/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ API is responding")
            logger.info(f"📊 Status: {data.get('status')}")
            logger.info(f"📋 Loaded models: {data.get('loadedModels', [])}")
            logger.info(f"📋 Available models: {data.get('availableModels', [])}")
            logger.info(f"📏 Corpus size: {data.get('corpusSize', 0)}")
            
            errors = data.get('errors', {})
            if errors:
                logger.warning("⚠️ Model loading errors:")
                for model, error in errors.items():
                    logger.warning(f"   {model}: {error}")
            
            return data
        else:
            logger.error(f"❌ API returned {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to API - Server may not be running")
        return None
    except Exception as e:
        logger.error(f"❌ API test error: {e}")
        return None

def test_llm_api_call():
    """Test LLM API call specifically."""
    logger.info("🤖 Testing LLM API call...")
    
    try:
        import requests
        
        test_data = {
            "address": "268 Lý Thường Kiệt, Phường 14, Quận 10"
        }
        
        response = requests.post(
            "http://localhost:8081/api/parser/analyze?model=llm",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ LLM API call successful")
            data = response.json()
            logger.info(f"📊 Result: {data}")
            return True
        else:
            logger.error(f"❌ LLM API call failed: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ LLM API test error: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes for common issues."""
    logger.info("\n🔧 Suggested troubleshooting steps:")
    
    fixes = [
        "1. Check if server is running: python -m app.api.server",
        "2. Restart server to reload models: Ctrl+C and restart",
        "3. Clear model cache and reload via API: POST /api/parser/reload",
        "4. Check available memory (LLM models need ~2-4GB RAM)",
        "5. Try smaller model: Qwen/Qwen2.5-0.5B-Instruct",
        "6. Check logs for detailed error messages",
        "7. Verify all dependencies are installed: pip install -r requirements.txt"
    ]
    
    for fix in fixes:
        logger.info(f"   {fix}")
    
    logger.info("\n💡 Quick fixes to try:")
    logger.info("   - If memory issue: Set use_quantization=True")
    logger.info("   - If model not found: Check internet connection for downloads")
    logger.info("   - If 503 error: Check server logs for model loading errors")

def main():
    """Main diagnostic function."""
    logger.info("🚀 Starting VN Address Intelligence Parser Diagnostics\n")
    
    # Test 1: Dependencies
    deps_ok = test_dependencies()
    
    # Test 2: API Status
    api_status = test_api_status()
    
    # Test 3: Direct LLM loading
    if deps_ok:
        llm_ok = test_llm_model()
    else:
        logger.warning("⚠️ Skipping LLM test due to missing dependencies")
        llm_ok = False
    
    # Test 4: LLM API call (if API is up)
    if api_status:
        llm_api_ok = test_llm_api_call()
    else:
        logger.warning("⚠️ Skipping LLM API test - server not responding")
        llm_api_ok = False
    
    # Summary
    logger.info("\n📋 DIAGNOSTIC SUMMARY:")
    logger.info(f"   Dependencies: {'✅ OK' if deps_ok else '❌ ISSUES'}")
    logger.info(f"   API Status: {'✅ OK' if api_status else '❌ DOWN'}")
    logger.info(f"   LLM Direct: {'✅ OK' if llm_ok else '❌ FAILED'}")
    logger.info(f"   LLM API: {'✅ OK' if llm_api_ok else '❌ FAILED'}")
    
    if not llm_api_ok:
        suggest_fixes()
    else:
        logger.info("\n🎉 All tests passed! Parser should be working correctly.")

if __name__ == "__main__":
    main()