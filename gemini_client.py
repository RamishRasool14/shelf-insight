"""
Google Gemini API client for product detection
"""

from google import genai
from google.genai import types
import json
from datetime import datetime
from PIL import Image
import streamlit as st
from config import GOOGLE_API_KEY, GEMINI_MODEL, DETECTION_PROMPT_TEMPLATE
from typing import Dict, Any, List, Union
import traceback


def calculate_cost(token_counts: Dict[str, int], 
                   input_price_per_million_usd: float, 
                   output_price_per_million_usd: float) -> Dict[str, Any]:
    """
    Calculate the cost of an API call based on token counts and model pricing.
    
    Args:
        token_counts: Dictionary containing token counts
        input_price_per_million_usd: Price per million tokens for input (prompt)
        output_price_per_million_usd: Price per million tokens for output (completion)
        
    Returns:
        Dictionary with cost calculation details
    """
    prompt_tokens = token_counts.get('prompt_token_count', 0)
    output_tokens = (token_counts.get('candidates_token_count') or 0) + (token_counts.get('thoughts_token_count') or 0)
    total_tokens = token_counts.get('total_token_count', 0)
    cached_content_tokens = token_counts.get('cached_content_token_count', 0)

    input_cost = (prompt_tokens / 1_000_000) * input_price_per_million_usd
    output_cost = (output_tokens / 1_000_000) * output_price_per_million_usd

    total_cost = input_cost + output_cost
    return {
        'cost': total_cost, 
        'prompt_tokens': prompt_tokens, 
        'output_tokens': output_tokens, 
        'thoughts_token_count': token_counts.get('thoughts_token_count', 0),
        'total_tokens': total_tokens, 
        'cached_content_tokens': cached_content_tokens
    }


class GeminiProductDetector:
    """Client for Google Gemini API to detect products in shelf images"""
    
    def __init__(self):
        """Initialize the Gemini client"""
        if not GOOGLE_API_KEY:
            raise ValueError("Google API key not found. Please check your .env file.")
        
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
    
    def detect_products(self, image: Image.Image, sku_items: List[Union[str, Dict[str, Any]]]) -> dict:
        """
        Detect products in the given image based on SKU items list
        
        Args:
            image: PIL Image object
            sku_items: List of SKU items to detect (strings or dicts with fields like SKU, ShelfNo, FacingTouching)
            
        Returns:
            dict: Detection results normalized to {"sku_names": [..]}
        """
        try:
            # Prepare the prompt with SKU items (accept list of strings or dicts with extra context)
            formatted_lines: List[str] = []
            for item in sku_items:
                try:
                    if isinstance(item, dict):
                        name = item.get('SKU') or item.get('sku') or item.get('name') or ''
                        shelf = item.get('ShelfNo')
                        touching = item.get('FacingTouching')
                        parts: List[str] = [str(name).strip()] if name else []
                        if shelf is not None and str(shelf).strip() != '':
                            parts.append(f"ShelfNo: {shelf}")
                        if touching is not None and str(touching).strip() != '':
                            parts.append(f"FacingTouching: {touching}")
                        if parts:
                            formatted_lines.append("- " + " | ".join(parts))
                    else:
                        formatted_lines.append(f"- {str(item)}")
                except Exception:
                    formatted_lines.append(f"- {str(item)}")
            sku_items_text = "\n".join(formatted_lines) if formatted_lines else ""
            prompt = DETECTION_PROMPT_TEMPLATE.format(sku_items=sku_items_text)
            
            # Convert PIL image to bytes for the new API
            import io
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Create image part using the new API
            image_part = types.Part.from_bytes(
                data=img_bytes.getvalue(),
                mime_type='image/png'
            )
            
            # Generate content using the new Gemini client
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt, image_part]
            )

            _ = calculate_cost(response.usage_metadata.model_dump(),
                               input_price_per_million_usd=1.25,
                               output_price_per_million_usd=10)
            
            # Parse the response
            result_text = response.text.strip()
            
            # Extract JSON from response (remove any markdown formatting)
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.rfind("```")
                json_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.rfind("```")
                json_text = result_text[json_start:json_end].strip()
            else:
                json_text = result_text
            
            # Parse and normalize JSON
            try:
                parsed = json.loads(json_text)
            except json.JSONDecodeError:
                return {
                    "sku_names": [],
                    "raw_response": result_text,
                    "error": "Failed to parse JSON response"
                }
            
            sku_names: List[str] = []
            if isinstance(parsed, dict):
                if isinstance(parsed.get("sku_names"), list):
                    sku_names = [str(s).strip() for s in parsed["sku_names"] if isinstance(s, (str, int, float)) and str(s).strip()]
                elif isinstance(parsed.get("detected_items"), list):
                    for it in parsed["detected_items"]:
                        if isinstance(it, dict):
                            name = it.get("item_name")
                            if name:
                                sku_names.append(str(name).strip())
            elif isinstance(parsed, list):
                # Sometimes the model may output just an array of names
                sku_names = [str(s).strip() for s in parsed if isinstance(s, (str, int, float)) and str(s).strip()]
            
            sku_names = sorted(set(sku_names))
            return {"sku_names": sku_names, "prompt": prompt}
            
        except Exception as e:
            print(traceback.format_exc())
            return {
                "sku_names": [],
                "error": f"Detection failed: {str(e)}"
            }
    
    def validate_api_key(self) -> bool:
        """
        Validate if the API key is working
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            # Try a simple request to validate the API key
            test_response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents="Hello"
            )
            return True
        except Exception:
            return False


def create_sample_detection_result():
    """Create a sample detection result for demo purposes"""
    return {
        "sku_names": [
            "Coca-Cola bottles",
            "Water bottles",
            "Chips/Crisps"
        ]
    }