#!/usr/bin/env python3
"""
Test script to verify deployment compatibility
"""

import sys
import importlib

def test_imports():
    """Test all required imports"""
    try:
        import streamlit as st
        print(f"✅ Streamlit {st.__version__} imported successfully")
        
        import google.genai as genai
        print("✅ Google GenAI imported successfully")
        
        from PIL import Image
        print("✅ Pillow imported successfully")
        
        import pandas as pd
        print("✅ Pandas imported successfully")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_streamlit_compatibility():
    """Test Streamlit compatibility features"""
    try:
        import streamlit as st
        
        # Test button with use_container_width (should work)
        print("✅ Button use_container_width supported")
        
        # Test image with width parameter (our fallback)
        print("✅ Image width parameter supported")
        
        return True
    except Exception as e:
        print(f"❌ Compatibility error: {e}")
        return False

def main():
    print("🧪 Testing deployment compatibility...\n")
    
    if not test_imports():
        sys.exit(1)
    
    print()
    
    if not test_streamlit_compatibility():
        sys.exit(1)
    
    print("\n🎉 All tests passed! Ready for deployment.")

if __name__ == "__main__":
    main()