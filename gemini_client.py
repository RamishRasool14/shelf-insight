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


class GeminiProductDetector:
    """Client for Google Gemini API to detect products in shelf images"""
    
    def __init__(self):
        """Initialize the Gemini client"""
        if not GOOGLE_API_KEY:
            raise ValueError("Google API key not found. Please check your .env file.")
        
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
    
    def detect_products(self, image: Image.Image, sku_items: list) -> dict:
        """
        Detect products in the given image based on SKU items list
        
        Args:
            image: PIL Image object
            sku_items: List of SKU items to detect
            
        Returns:
            dict: Detection results in JSON format
        """
        try:
            # Prepare the prompt with SKU items
            sku_items_text = "\n".join([f"- {item}" for item in sku_items])
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
            
            # Parse JSON
            try:
                detection_result = json.loads(json_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured response
                detection_result = {
                    "detected_items": [],
                    "total_items_detected": 0,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "raw_response": result_text,
                    "error": "Failed to parse JSON response"
                }
            
            # Add timestamp if not present
            if "analysis_timestamp" not in detection_result:
                detection_result["analysis_timestamp"] = datetime.now().isoformat()
            
            return detection_result
            
        except Exception as e:
            return {
                "detected_items": [],
                "total_items_detected": 0,
                "analysis_timestamp": datetime.now().isoformat(),
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
        "detected_items": [
            {
                "item_name": "Coca-Cola bottles",
                "quantity": 12,
                "location": "Top shelf, left section",
                "confidence": "high",
                "notes": "Classic red Coca-Cola bottles, clearly visible"
            },
            {
                "item_name": "Water bottles", 
                "quantity": 8,
                "location": "Middle shelf, center",
                "confidence": "high",
                "notes": "Clear plastic water bottles"
            },
            {
                "item_name": "Chips/Crisps",
                "quantity": 6,
                "location": "Bottom shelf, right section", 
                "confidence": "medium",
                "notes": "Various chip bags, partially visible"
            }
        ],
        "total_items_detected": 3,
        "analysis_timestamp": datetime.now().isoformat()
    }