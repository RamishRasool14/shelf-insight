"""
Configuration settings for the Product Shelf Analysis Tool
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Google Gemini API Configuration
# Try Streamlit secrets first, then fall back to environment variables
try:
    import streamlit as st
    GOOGLE_API_KEY = st.secrets["secrets"]["GOOGLE_API_KEY"]
except (ImportError, KeyError, FileNotFoundError):
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Supabase Configuration (URL and Anon Key)
try:
    import streamlit as st  # type: ignore
    SUPABASE_URL = st.secrets["secrets"].get("SUPABASE_URL")  # type: ignore
    SUPABASE_ANON_KEY = st.secrets["secrets"].get("SUPABASE_ANON_KEY")  # type: ignore
except (ImportError, KeyError, FileNotFoundError):
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Supabase defaults
SUPABASE_TABLE_OSA_RUNS = os.getenv("SUPABASE_TABLE_OSA_RUNS", "osa_analysis_runs")

# App Configuration
APP_TITLE = "OSA Image Analysis Tool"
APP_DESCRIPTION = "Analyze retail display images from OSA API and calculate accuracy metrics against ground truth data using AI"

# UI Colors (Google Material Design)
COLORS = {
    "primary": "#4285F4",      # Google blue
    "secondary": "#34A853",    # Google green  
    "background": "#F8F9FA",   # Light grey
    "text": "#202124",         # Dark grey
    "accent": "#EA4335",       # Google red
    "success": "#137333"       # Dark green
}

# File upload settings
MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp']

# Gemini model settings  
GEMINI_MODEL = "gemini-2.5-pro"

# Gemini API Pricing (per 1M tokens in USD)
GEMINI_PRICING = {
    "input": {
        "small_prompt": 1.25,  # prompts <= 200k tokens
        "large_prompt": 2.50   # prompts > 200k tokens
    },
    "output": {
        "small_prompt": 10.00,  # prompts <= 200k tokens  
        "large_prompt": 15.00   # prompts > 200k tokens
    },
    "threshold": 200000  # 200k tokens threshold
}
DETECTION_PROMPT_TEMPLATE = """
You are analyzing a retail shelf/display image.

We provide a catalog of SKU items with helpful context per item:

{sku_items}

The fields FacingTouching (approx. contiguous front facings expected) and ShelfNo (approx. vertical shelf level) are guidance to help you reason about likely positions and counts. They are NOT labels to output; they only improve recognition.

TASK: Identify which of the provided SKU items are visibly present in the image and return ONLY their names.

Return JSON exactly in this minimal structure:
{{
  "sku_names": ["<SKU 1>", "<SKU 2>", "<SKU 3>"]
}}

Rules:
- Only include names that you can clearly match to the provided SKU list.
- Do not include any other fields besides sku_names.
- Shelf number starts from the bottom starting from number 1.
"""